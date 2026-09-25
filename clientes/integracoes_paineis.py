# -*- coding: utf-8 -*-
"""Integrações de renovação com painéis externos.

Regras deste módulo:
- nunca altera clientes ou créditos locais; apenas conversa com o painel externo;
- nunca registra token/senha em logs;
- toda identificação de conta é feita usando os dados ATUAIS do cliente;
- resultados ambíguos são bloqueados em vez de escolher o primeiro registro.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from dateutil import parser as date_parser
from django.utils import timezone

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except Exception:  # pragma: no cover - fallback para ambientes sem pycryptodome
    AES = None
    pad = unpad = None


class IntegracaoPainelErro(Exception):
    pass


class ContaNaoEncontrada(IntegracaoPainelErro):
    pass


class ContaAmbigua(IntegracaoPainelErro):
    pass


@dataclass
class ContaExterna:
    id: str
    usuario: str
    senha: str = ""
    nome: str = ""
    plano: str = ""
    pacote_id: str = ""
    servidor_id: str = ""
    servidor: str = ""
    conexoes: int = 1
    vencimento: Optional[datetime] = None
    status: str = ""
    bruto: Optional[Dict[str, Any]] = None


@dataclass
class PreviewRenovacao:
    conta: ContaExterna
    meses: int
    pacote_id: str
    pacote_nome: str
    creditos: Decimal
    conexoes: int
    dados: Dict[str, Any]


@dataclass
class ResultadoRenovacao:
    sucesso: bool
    conta: ContaExterna
    creditos: Decimal
    vencimento_novo: Optional[datetime]
    status_externo: str
    mensagem: str
    dados: Dict[str, Any]


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return _aware(value)
    try:
        return _aware(date_parser.parse(str(value)))
    except Exception:
        return None


def _safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        value = resp.json()
        return value if isinstance(value, dict) else {"data": value}
    except Exception:
        raise IntegracaoPainelErro(f"O painel respondeu HTTP {resp.status_code}, mas não retornou JSON válido.")


class BasePainelAdapter:
    timeout = 25

    def __init__(self, servico):
        self.servico = servico
        self.base_url = (servico.integracao_url or "").strip().rstrip("/")
        if not self.base_url:
            raise IntegracaoPainelErro("A URL da integração não foi configurada.")
        self.session = requests.Session()

    def testar_conexao(self) -> Dict[str, Any]:
        raise NotImplementedError

    def localizar_conta(self, usuario: str, senha: str = "") -> ContaExterna:
        raise NotImplementedError

    def preview_renovacao(self, usuario: str, senha: str, meses: int = 1) -> PreviewRenovacao:
        raise NotImplementedError

    def renovar(self, preview: PreviewRenovacao) -> ResultadoRenovacao:
        raise NotImplementedError

    def criar_teste(self, nome: str = "", whatsapp: str = "") -> ContaExterna:
        raise IntegracaoPainelErro("Este tipo de painel não possui criação de teste configurada.")


class SigmanAdapter(BasePainelAdapter):
    """Integração com a API utilizada pelo SIGMAN/Spark.

    O adaptador aceita URL terminando ou não em /api. Para token, tenta os formatos
    usuais de integração do painel quando a primeira tentativa retorna 401/403.
    """

    @property
    def official_mode(self) -> bool:
        # A tela salva explicitamente o modo para não obrigar o usuário a entender
        # detalhes de headers. Projetos antigos continuam compatíveis: se ainda não
        # houver sigman_modo, a presença da API Key preserva o comportamento anterior.
        modo = str((self.servico.integracao_config or {}).get('sigman_modo') or '').strip().lower()
        if modo in {'oficial', 'direto'}:
            return modo == 'oficial'
        return bool((self.servico.integracao_api_key or '').strip())

    def _api_base(self) -> str:
        """Normaliza a URL do painel SIGMAN para a base real /api.

        Aceita entradas comuns copiadas do navegador, por exemplo:
        - https://painel.com
        - https://painel.com/
        - https://painel.com/api
        - https://painel.com/api/servers
        - https://painel.com/#/dashboard
        """
        raw = (self.base_url or '').strip()
        if not raw.startswith(('http://', 'https://')):
            raw = 'https://' + raw.lstrip('/')
        parsed = urlsplit(raw)
        path = (parsed.path or '').rstrip('/')
        # Se o usuário colou um endpoint específico, volta para a raiz antes de /api.
        if '/api' in path:
            path = path.split('/api', 1)[0]
        elif path not in ('', '/'):
            # Rotas SPA como /dashboard não pertencem à API.
            path = ''
        root = urlunsplit((parsed.scheme or 'https', parsed.netloc, path, '', ''))
        return root.rstrip('/') + '/api'

    def _panel_root(self) -> str:
        api = self._api_base()
        return api[:-4] if api.endswith('/api') else api

    def _headers_variants(self) -> List[Dict[str, str]]:
        api_key = (self.servico.integracao_api_key or '').strip()
        token = (self.servico.integracao_token or '').strip()
        base = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'locale': 'pt',
            # O painel web envia esta versão nas chamadas internas. Não é segredo e
            # ajuda instalações que validam a versão do frontend.
            'x-app-version': '3.92',
            'Referer': self._panel_root() + '/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36',
        }

        if self.official_mode:
            if not token:
                raise IntegracaoPainelErro('Informe o x-painel-token do SIGMAN.')
            # Contrato documentado da API oficial.
            return [{**base, 'x-api-key': api_key, 'x-painel-token': token}]

        configured = (self.servico.integracao_config or {}).get('sigman_token_header', '').strip().lower()
        variants: List[Dict[str, str]] = []
        if token:
            # Tokens retornados pelo painel no formato "id|chave" são tokens de
            # sessão/API no padrão Bearer. No HAR o Chrome pode omitir o header
            # Authorization por segurança, por isso este formato deve ser tentado
            # primeiro no modo direto.
            if configured == 'token':
                variants.append({**base, 'token': token})
            elif configured == 'xpainel':
                variants.append({**base, 'x-painel-token': token})
            else:
                variants.append({**base, 'Authorization': f'Bearer {token}'})
            variants.extend([
                {**base, 'Authorization': f'Bearer {token}'},
                {**base, 'token': token},
                {**base, 'x-painel-token': token},
            ])
        else:
            variants.append(base)

        unique = []
        seen = set()
        for item in variants:
            key = tuple(sorted(item.items()))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _request_public(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Faz uma chamada sem credencial para validar URL/CDN antes da autenticação.

        O HAR do painel mostra /api/settings/public como endpoint público. Isso permite
        distinguir URL/IP bloqueado de token inválido, evitando culpar a credencial
        quando a própria VPS não consegue alcançar a API do painel.
        """
        url = self._api_base() + '/' + path.lstrip('/')
        headers = {
            'Accept': 'application/json',
            'locale': 'pt',
            'x-app-version': '3.92',
            'Referer': self._panel_root() + '/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36',
        }
        try:
            resp = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise IntegracaoPainelErro(f'Falha de comunicação com o SIGMAN: {exc}') from exc

        content_type = (resp.headers.get('content-type') or '').lower()
        try:
            value = resp.json()
            data = value if isinstance(value, dict) else {'data': value}
        except Exception:
            body = (resp.text or '').strip().replace('\n', ' ')[:180]
            if resp.status_code == 404:
                raise IntegracaoPainelErro(
                    'A URL parece correta, mas a VPS recebeu HTTP 404/HTML até em uma rota pública do painel. '
                    'Isso normalmente indica bloqueio do painel/Cloudflare ao IP da VPS, e não erro do token. '
                    f'Rota testada: {url}. Resposta: {body or "sem corpo"}'
                )
            raise IntegracaoPainelErro(
                f'O painel respondeu HTTP {resp.status_code} ({content_type or "sem content-type"}) e não retornou JSON válido.'
            )
        if resp.status_code >= 400:
            msg = data.get('message') or data.get('error') or data.get('detail') or f'HTTP {resp.status_code}'
            raise IntegracaoPainelErro(f'SIGMAN: {msg}')
        return data

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = self._api_base() + '/' + path.lstrip('/')
        last_error = None
        variants = self._headers_variants()
        for index, headers in enumerate(variants):
            try:
                resp = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                raise IntegracaoPainelErro(f"Falha de comunicação com o SIGMAN: {exc}") from exc

            # Alguns painéis escondem endpoints autenticados retornando 404 quando o
            # formato do token não confere. No modo direto tentamos os demais formatos
            # antes de concluir que a rota está errada.
            retry_auth = (not self.official_mode and resp.status_code in (401, 403, 404) and index < len(variants) - 1)
            if retry_auth:
                last_error = f"Acesso recusado pelo painel (HTTP {resp.status_code})."
                continue

            try:
                value = resp.json()
                data = value if isinstance(value, dict) else {'data': value}
            except Exception:
                if not self.official_mode and resp.status_code in (401, 403, 404) and index < len(variants) - 1:
                    last_error = f"Acesso recusado pelo painel (HTTP {resp.status_code})."
                    continue
                if resp.status_code == 404:
                    body = (resp.text or '').strip().replace('\n', ' ')[:180]
                    raise IntegracaoPainelErro(
                        f"SIGMAN respondeu HTTP 404 em {url}. A URL base já foi normalizada pelo gestor. "
                        f"Se o teste da rota pública funcionar, este 404 indica que o token foi recusado/expirou "
                        f"ou que o painel está ocultando a rota autenticada. Resposta: {body or 'sem corpo'}"
                    )
                raise IntegracaoPainelErro(f"O painel respondeu HTTP {resp.status_code}, mas não retornou JSON válido.")

            if resp.status_code >= 400:
                msg = data.get('message') or data.get('error') or data.get('detail') or f'HTTP {resp.status_code}'
                raise IntegracaoPainelErro(f"SIGMAN: {msg}")
            return data
        raise IntegracaoPainelErro(last_error or 'Não foi possível autenticar no SIGMAN.')

    def listar_servidores(self) -> List[Dict[str, Any]]:
        data = self._request('GET', '/servers')
        rows = data.get('data', data)
        if isinstance(rows, dict):
            rows = rows.get('data') or rows.get('servers') or rows.get('list') or []
        return rows if isinstance(rows, list) else []

    def testar_conexao(self) -> Dict[str, Any]:
        conta_painel = {}
        if not self.official_mode:
            # Primeiro testa uma rota PUBLICA registrada no HAR. Se ela falhar com
            # 404/HTML, o problema é acesso da VPS/CDN e não a credencial.
            self._request_public('GET', '/settings/public')

            # Depois valida de fato uma rota autenticada sem alterar nada. O endpoint
            # de clientes é usado pelo próprio painel e é suficiente para confirmar
            # que a credencial tem acesso à conta.
            self._request('GET', '/customers', params={'page': 1, 'perPage': 1})

            # /auth/me é útil para mostrar usuário/créditos, mas não deve derrubar o
            # teste caso uma instalação específica o esconda.
            try:
                conta_painel = self._request('GET', '/auth/me')
            except IntegracaoPainelErro:
                conta_painel = {}

        servidores = self.listar_servidores()
        pacotes = sum(len(s.get('packages') or []) for s in servidores)
        testes = sum(1 for s in servidores for p in (s.get('packages') or []) if str(p.get('is_trial')).upper() == 'YES')
        return {
            'ok': True,
            'usuario_painel': conta_painel.get('username') or '',
            'creditos_painel': conta_painel.get('credits'),
            'servidores': len(servidores),
            'pacotes': pacotes,
            'testes': testes,
        }

    def catalogo(self) -> Dict[str, Any]:
        servidores = self.listar_servidores()
        return {
            'servidores': [
                {
                    'id': str(s.get('id', '')),
                    'nome': s.get('name') or str(s.get('id', '')),
                    'pacotes': [
                        {
                            'id': str(p.get('id', '')),
                            'nome': p.get('name') or str(p.get('id', '')),
                            'trial': str(p.get('is_trial')).upper() == 'YES',
                            'creditos': p.get('credits', 0),
                            'duracao': p.get('duration'),
                            'unidade': p.get('duration_in'),
                            'conexoes': p.get('connections') or 1,
                        }
                        for p in (s.get('packages') or []) if p.get('status', 'ACTIVE') == 'ACTIVE'
                    ],
                }
                for s in servidores
            ]
        }

    def _lista_clientes(self, usuario: str) -> List[Dict[str, Any]]:
        if self.official_mode:
            params = {
                'userId': '',
                'page': 1,
                'connections': '',
                'isTrial': '',
                'status': '',
                'serverId': (self.servico.integracao_servidor_externo_id or ''),
                'packageId': '',
                'expiryFrom': '',
                'expiryTo': '',
                'perPage': 100,
                'username': usuario,
                'todos': 'true',
            }
            data = self._request('GET', '/users', params=params)
        else:
            data = self._request('GET', '/customers', params={'perPage': 100, 'username': usuario})

        rows = data.get('data', [])
        # A API pode paginar como {data:[...]}, {data:{data:[...]}},
        # {data:{list:[...]}} ou devolver a lista diretamente.
        if isinstance(rows, dict):
            rows = rows.get('data') or rows.get('list') or rows.get('users') or []
        return rows if isinstance(rows, list) else []

    def localizar_conta(self, usuario: str, senha: str = "") -> ContaExterna:
        usuario = (usuario or '').strip()
        if not usuario:
            raise ContaNaoEncontrada('O cliente não possui usuário IPTV para consultar no SIGMAN.')
        rows = self._lista_clientes(usuario)
        server_id = (self.servico.integracao_servidor_externo_id or '').strip()

        def field(row, *keys, default=''):
            for key in keys:
                if row.get(key) not in (None, ''):
                    return row.get(key)
            return default

        exatos = []
        mesmos_usuarios = []
        for r in rows:
            ruser = str(field(r, 'username', 'user', 'login')).strip()
            if ruser != usuario:
                continue
            rsid = str(field(r, 'server_id', 'serverId', default='')).strip()
            if server_id and rsid and rsid != server_id:
                continue
            mesmos_usuarios.append(r)
            rpass = str(field(r, 'password', 'pass', default='')).strip()
            # Algumas versões da API pública não devolvem a senha. Quando não
            # devolve, não inventamos divergência; a identificação continua por
            # servidor + username exato. Se devolve, ela precisa conferir.
            if senha and rpass and rpass != str(senha).strip():
                continue
            exatos.append(r)

        if not exatos:
            if mesmos_usuarios and senha:
                raise ContaNaoEncontrada('O usuário existe no SIGMAN, mas a senha retornada pelo painel não confere. Renovação bloqueada por segurança.')
            raise ContaNaoEncontrada(f'Usuário {usuario} não encontrado no SIGMAN deste servidor.')
        if len(exatos) > 1:
            raise ContaAmbigua(f'Foram encontradas {len(exatos)} contas iguais para {usuario}. Renovação automática bloqueada.')

        r = exatos[0]
        pacote = field(r, 'package', 'package_name', 'packageName', default='')
        if isinstance(pacote, dict):
            pacote_nome = pacote.get('name') or pacote.get('title') or ''
            pacote_id = pacote.get('id') or field(r, 'package_id', 'packageId', default='')
        else:
            pacote_nome = str(pacote or '')
            pacote_id = field(r, 'package_id', 'packageId', default='')
        servidor = field(r, 'server', 'server_name', 'serverName', default='')
        if isinstance(servidor, dict):
            servidor_nome = servidor.get('name') or servidor.get('title') or ''
            sid = servidor.get('id') or field(r, 'server_id', 'serverId', default='')
        else:
            servidor_nome = str(servidor or '')
            sid = field(r, 'server_id', 'serverId', default='')

        return ContaExterna(
            id=str(field(r, 'id', 'user_id', 'userId', default='')),
            usuario=str(field(r, 'username', 'user', 'login', default='')),
            senha=str(field(r, 'password', 'pass', default='')),
            nome=str(field(r, 'name', 'customer_name', default='')),
            plano=pacote_nome,
            pacote_id=str(pacote_id or ''),
            servidor_id=str(sid or ''),
            servidor=servidor_nome,
            conexoes=int(field(r, 'connections', 'max_connections', default=1) or 1),
            vencimento=_parse_dt(field(r, 'expires_at_tz', 'expires_at', 'expiration', 'expiry', default=None)),
            status=str(field(r, 'status', default='')),
            bruto=r,
        )

    @staticmethod
    def _duracao_meses(p: Dict[str, Any]) -> Optional[int]:
        unit = str(p.get('duration_in') or '').upper()
        try:
            value = int(p.get('duration') or 0)
        except Exception:
            return None
        if unit == 'MONTHS':
            return value
        if unit == 'YEARS':
            return value * 12
        return None

    def _resolver_pacote(self, conta: ContaExterna, meses: int, trial: bool = False) -> Dict[str, Any]:
        servidores = self.listar_servidores()
        sid = (self.servico.integracao_servidor_externo_id or conta.servidor_id or '').strip()
        servidor = next((s for s in servidores if str(s.get('id')) == sid), None) if sid else (servidores[0] if len(servidores) == 1 else None)
        if not servidor:
            raise IntegracaoPainelErro('Não foi possível determinar o servidor externo do SIGMAN. Configure-o em Abastecer Créditos.')
        packages = [p for p in (servidor.get('packages') or []) if p.get('status', 'ACTIVE') == 'ACTIVE']
        mapped = (self.servico.integracao_pacote_teste if trial else (self.servico.integracao_pacote_1_mes if meses == 1 else '')) or ''
        if mapped:
            pkg = next((p for p in packages if str(p.get('id')) == str(mapped)), None)
            if pkg:
                return pkg
            raise IntegracaoPainelErro('O pacote externo salvo não existe mais no SIGMAN. Use “Buscar planos” e selecione novamente.')
        if trial:
            matches = [p for p in packages if str(p.get('is_trial')).upper() == 'YES']
        else:
            matches = [
                p for p in packages
                if str(p.get('is_trial')).upper() != 'YES'
                and self._duracao_meses(p) == int(meses)
                and int(p.get('connections') or 1) == int(conta.conexoes or self.servico.integracao_conexoes or 1)
            ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise IntegracaoPainelErro(f'Nenhum pacote compatível com {meses} mês(es) e {conta.conexoes} tela(s). Configure o pacote no servidor.')
        raise IntegracaoPainelErro('Há mais de um pacote compatível. Configure explicitamente o pacote de 1 mês para evitar renovar no plano errado.')

    def preview_renovacao(self, usuario: str, senha: str, meses: int = 1) -> PreviewRenovacao:
        conta = self.localizar_conta(usuario, senha)
        pacote = self._resolver_pacote(conta, int(meses), trial=False)
        if self.official_mode:
            # A API pública documentada não possui endpoint de simulação. O custo
            # vem do pacote retornado por /servers e a operação real usa /user-renew.
            creditos = Decimal(str(pacote.get('credits', pacote.get('credit', 0)) or 0))
            calc = {'credits_required': str(creditos), 'package_name': pacote.get('name') or '', 'source': 'servers'}
        else:
            payload = {'package_id': pacote.get('id'), 'connections': conta.conexoes}
            calc = self._request('POST', f'/customers/{conta.id}/calculate-renew-credits', json=payload)
            creditos = Decimal(str(calc.get('credits_required', pacote.get('credits', 0)) or 0))
        return PreviewRenovacao(
            conta=conta,
            meses=int(meses),
            pacote_id=str(pacote.get('id')),
            pacote_nome=str(calc.get('package_name') or pacote.get('name') or ''),
            creditos=creditos,
            conexoes=int(calc.get('connections') or conta.conexoes or 1),
            dados={'calculo': calc, 'pacote': pacote, 'official_api': self.official_mode},
        )

    def renovar(self, preview: PreviewRenovacao) -> ResultadoRenovacao:
        if self.official_mode:
            data = self._request('POST', '/user-renew', json={
                'package_id': preview.pacote_id,
                'username': preview.conta.usuario,
            })
            # A chamada de renovação foi aceita. Uma consulta somente-leitura
            # tenta obter o vencimento atualizado, sem jamais repetir o POST.
            try:
                conta = self.localizar_conta(preview.conta.usuario, preview.conta.senha)
            except Exception:
                conta = preview.conta
            venc = conta.vencimento
            message = data.get('message') or 'Renovação confirmada pela API SIGMAN.'
            return ResultadoRenovacao(True, conta, preview.creditos, venc, 'concluida', message, data)

        payload = {
            'package_id': preview.pacote_id,
            'connections': preview.conexoes,
            'reference': '',
            'create_manual_customer_order': False,
            'manual_payment_total': None,
        }
        data = self._request('POST', f'/customers/{preview.conta.id}/renew', json=payload)
        row = data.get('data') if isinstance(data.get('data'), dict) else data
        venc = _parse_dt(row.get('expires_at_tz') or row.get('expires_at')) if isinstance(row, dict) else None
        conta = preview.conta
        if isinstance(row, dict):
            conta = ContaExterna(
                id=str(row.get('id') or conta.id), usuario=str(row.get('username') or conta.usuario),
                senha=str(row.get('password') or conta.senha), nome=str(row.get('name') or conta.nome),
                plano=str(row.get('package') or row.get('package_name') or preview.pacote_nome),
                pacote_id=str(row.get('package_id') or preview.pacote_id), servidor_id=str(row.get('server_id') or conta.servidor_id),
                servidor=str(row.get('server') or conta.servidor), conexoes=int(row.get('connections') or preview.conexoes),
                vencimento=venc, status=str(row.get('status') or conta.status), bruto=row,
            )
        return ResultadoRenovacao(True, conta, preview.creditos, venc, 'concluida', 'Renovação confirmada pelo SIGMAN.', data)

    def criar_teste(self, nome: str = "", whatsapp: str = "") -> ContaExterna:
        dummy = ContaExterna(id='', usuario='', conexoes=int(self.servico.integracao_conexoes or 1), servidor_id=self.servico.integracao_servidor_externo_id or '')
        pacote = self._resolver_pacote(dummy, 0, trial=True)
        sid = (self.servico.integracao_servidor_externo_id or pacote.get('server_id') or '').strip()

        if self.official_mode:
            data = self._request('POST', '/user', json={
                'package_id': pacote.get('id'),
                'caracteres': 9,
                'username': '',
                'password': '',
                'email': '',
                'name': nome or '',
                'notes': 'Teste criado pelo gestor',
                'plan_price': '',
                'telegram': '',
                'whatsapp': whatsapp or '',
            })
            row = data.get('data') if isinstance(data.get('data'), dict) else data
        else:
            if not sid:
                raise IntegracaoPainelErro('Servidor externo não configurado para criar teste.')
            trial_hours = int(pacote.get('duration') or 3) if str(pacote.get('duration_in')).upper() == 'HOURS' else 3
            payload = {
                'server_id': sid,
                'package_id': pacote.get('id'),
                'trial_hours': trial_hours,
                'connections': int(pacote.get('connections') or self.servico.integracao_conexoes or 1),
            }
            data = self._request('POST', '/customers', json=payload)
            row = data.get('data') if isinstance(data.get('data'), dict) else data

        if not isinstance(row, dict):
            raise IntegracaoPainelErro('O SIGMAN confirmou a criação, mas não retornou os dados do usuário de teste.')
        uid = row.get('id') or row.get('user_id') or row.get('userId')
        username = row.get('username') or row.get('user') or ''
        if not username:
            raise IntegracaoPainelErro('O SIGMAN não retornou o usuário gerado para o teste. A criação precisa ser conferida no painel antes de tentar novamente.')
        return ContaExterna(
            id=str(uid or ''), usuario=str(username),
            senha=str(row.get('password') or ''),
            nome=str(row.get('name') or nome or ''),
            plano=str(row.get('package') or row.get('package_name') or pacote.get('name') or ''),
            pacote_id=str(row.get('package_id') or row.get('packageId') or pacote.get('id') or ''),
            servidor_id=str(row.get('server_id') or row.get('serverId') or sid or ''),
            servidor=str(row.get('server') or ''),
            conexoes=int(row.get('connections') or pacote.get('connections') or 1),
            vencimento=_parse_dt(row.get('expires_at_tz') or row.get('expires_at') or row.get('expiration')),
            status=str(row.get('status') or ''),
            bruto=row,
        )


class UnitvAdapter(BasePainelAdapter):
    """Integração com panel-web.resell.media / UniTV.

    O frontend do próprio painel usa AES-CBC com chave/IV fixos para transportar JSON.
    A assinatura da renovação é MD5("dealer" + id + points_type + points).
    """

    AES_KEY = b'93403d3aa2ec48b4'
    AES_IV = b'7cf0127d190cb909'

    def _api_base(self) -> str:
        """Normaliza a URL do painel SIGMAN para a base real /api.

        Aceita entradas comuns copiadas do navegador, por exemplo:
        - https://painel.com
        - https://painel.com/
        - https://painel.com/api
        - https://painel.com/api/servers
        - https://painel.com/#/dashboard
        """
        raw = (self.base_url or '').strip()
        if not raw.startswith(('http://', 'https://')):
            raw = 'https://' + raw.lstrip('/')
        parsed = urlsplit(raw)
        path = (parsed.path or '').rstrip('/')
        # Se o usuário colou um endpoint específico, volta para a raiz antes de /api.
        if '/api' in path:
            path = path.split('/api', 1)[0]
        elif path not in ('', '/'):
            # Rotas SPA como /dashboard não pertencem à API.
            path = ''
        root = urlunsplit((parsed.scheme or 'https', parsed.netloc, path, '', ''))
        return root.rstrip('/') + '/api'

    def _panel_root(self) -> str:
        api = self._api_base()
        return api[:-4] if api.endswith('/api') else api

    @staticmethod
    def _encrypt_fallback(text: str) -> str:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7
        padder = PKCS7(128).padder()
        raw = padder.update(text.encode('utf-8')) + padder.finalize()
        enc = Cipher(algorithms.AES(UnitvAdapter.AES_KEY), modes.CBC(UnitvAdapter.AES_IV)).encryptor()
        return (enc.update(raw) + enc.finalize()).hex().upper()

    @staticmethod
    def _decrypt_fallback(value: str) -> str:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7
        dec = Cipher(algorithms.AES(UnitvAdapter.AES_KEY), modes.CBC(UnitvAdapter.AES_IV)).decryptor()
        raw = dec.update(bytes.fromhex(value)) + dec.finalize()
        unpadder = PKCS7(128).unpadder()
        return (unpadder.update(raw) + unpadder.finalize()).decode('utf-8')

    def _encrypt(self, payload: Dict[str, Any]) -> str:
        text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        if AES is None:
            return self._encrypt_fallback(text)
        return AES.new(self.AES_KEY, AES.MODE_CBC, self.AES_IV).encrypt(pad(text.encode('utf-8'), AES.block_size)).hex().upper()

    def _decrypt(self, value: str) -> Any:
        if not value:
            return None
        if AES is None:
            text = self._decrypt_fallback(value)
        else:
            raw = AES.new(self.AES_KEY, AES.MODE_CBC, self.AES_IV).decrypt(bytes.fromhex(value))
            text = unpad(raw, AES.block_size).decode('utf-8')
        try:
            return json.loads(text)
        except Exception:
            return text

    def _post(self, path: str, payload: Dict[str, Any]) -> Any:
        token = (self.servico.integracao_token or '').strip()
        dealer = (self.servico.integracao_usuario or '').strip()
        if not token:
            raise IntegracaoPainelErro('Token da UniTV não configurado.')
        if not dealer:
            raise IntegracaoPainelErro('Informe o usuário/identificador da revenda UniTV na configuração.')
        body = dict(payload or {})
        body.setdefault('dealer_token', token)
        body.setdefault('dealer_name', dealer)
        url = self._api_base() + '/' + path.lstrip('/')
        headers = {'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json', 'token': token}
        try:
            resp = self.session.post(url, data=self._encrypt(body), headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise IntegracaoPainelErro(f'Falha de comunicação com a UniTV: {exc}') from exc
        data = _safe_json(resp)
        if resp.status_code >= 400:
            raise IntegracaoPainelErro(f'UniTV respondeu HTTP {resp.status_code}.')
        if int(data.get('returnCode', -1)) != 0:
            raise IntegracaoPainelErro(data.get('errorMessage') or f"UniTV retornou código {data.get('returnCode')}")
        encrypted = data.get('data')
        decoded = self._decrypt(encrypted) if encrypted else None
        return {'decoded': decoded, 'meta': {k: v for k, v in data.items() if k != 'data'}}

    def listar_pacotes(self) -> List[Dict[str, Any]]:
        cfg = self.servico.integracao_config or {}
        customer = cfg.get('unitv_customer') or 'UniTV'
        res = self._post('/dealer-core/package/package-name', {'customer': customer, 'type': 2})
        return res['decoded'] if isinstance(res['decoded'], list) else []

    def catalogo(self) -> Dict[str, Any]:
        pacotes = self.listar_pacotes()
        return {
            'servidores': [{
                'id': 'unitv', 'nome': (self.servico.integracao_config or {}).get('unitv_customer') or 'UniTV',
                'pacotes': [
                    {
                        'id': str(p.get('id')),
                        'nome': p.get('package_name_pt') or p.get('package_name_en') or p.get('package_name') or str(p.get('id')),
                        'trial': False,
                        'creditos': p.get('moth_exchange_points', 0),
                        'duracao': 1,
                        'unidade': 'MONTHS',
                        'conexoes': 1,
                        'periodos': p.get('pre_auth_objs') or [],
                    } for p in pacotes
                ]
            }]
        }

    def testar_conexao(self) -> Dict[str, Any]:
        pacotes = self.listar_pacotes()
        return {'ok': True, 'servidores': 1, 'pacotes': len(pacotes), 'testes': 0}

    def _listar_contas(self) -> List[Dict[str, Any]]:
        package_id = int(self.servico.integracao_pacote_1_mes or (self.servico.integracao_config or {}).get('unitv_package_id') or 1)
        page = 1
        rows: List[Dict[str, Any]] = []
        while page <= 100:
            res = self._post('/account', {
                'package_id': package_id,
                'time_zone': 'America/Sao_Paulo',
                'page': page,
                'pageSize': 100,
            })
            data = res['decoded'] if isinstance(res['decoded'], dict) else {}
            rows.extend(data.get('list') or [])
            total_pages = int(data.get('total_page') or 1)
            if page >= total_pages:
                break
            page += 1
        return rows

    def localizar_conta(self, usuario: str, senha: str = "") -> ContaExterna:
        usuario = (usuario or '').strip()
        if not usuario:
            raise ContaNaoEncontrada('O cliente não possui usuário para consultar na UniTV.')
        rows = self._listar_contas()
        same_user = [r for r in rows if str(r.get('sn') or '').strip() == usuario]
        matches = [r for r in same_user if not senha or str(r.get('password') or '').strip() == str(senha).strip()]
        if not matches:
            if same_user and senha:
                raise ContaNaoEncontrada('O usuário existe na UniTV, mas a senha atual do gestor não confere. Renovação bloqueada.')
            raise ContaNaoEncontrada(f'Usuário {usuario} não encontrado na UniTV.')
        if len(matches) > 1:
            raise ContaAmbigua(f'Foram encontradas {len(matches)} contas com o usuário {usuario}. Renovação bloqueada.')
        r = matches[0]
        return ContaExterna(
            id=str(r.get('id')), usuario=str(r.get('sn') or ''), senha=str(r.get('password') or ''),
            nome=str(r.get('snName') or ''), plano=str(r.get('package_name') or ''), pacote_id=str(self.servico.integracao_pacote_1_mes or 1),
            servidor_id='unitv', servidor=(self.servico.integracao_config or {}).get('unitv_customer') or 'UniTV', conexoes=1,
            vencimento=_parse_dt(r.get('expireTime')), status=str(r.get('expstatusTitle') or r.get('statusTitle') or ''), bruto=r,
        )

    def _periodo(self, meses: int) -> Dict[str, Any]:
        pacotes = self.listar_pacotes()
        package_id = int(self.servico.integracao_pacote_1_mes or (self.servico.integracao_config or {}).get('unitv_package_id') or 1)
        package = next((p for p in pacotes if int(p.get('id')) == package_id), None)
        if not package:
            raise IntegracaoPainelErro('Pacote UniTV configurado não foi encontrado.')
        periods = package.get('pre_auth_objs') or []
        target = None
        points_type = 1
        for p in periods:
            unit = str(p.get('auth_unit'))
            cycle = int(p.get('auth_cycle') or 0)
            converted = cycle if unit == '1' else (cycle * 12 if unit == '4' else 0)
            if converted == int(meses):
                target = p
                points_type = 1 if unit == '1' else 2
                break
        if not target:
            raise IntegracaoPainelErro(f'A UniTV não oferece período de {meses} mês(es) neste pacote.')
        if points_type == 1:
            points = Decimal(str(target.get('auth_cycle') or 1)) * Decimal(str(package.get('moth_exchange_points') or 0))
        else:
            points = Decimal(str(target.get('auth_cycle') or 1)) * Decimal(str(package.get('year_exchange_points') or 0))
        return {'package': package, 'periodo': target, 'points_type': points_type, 'points': points}

    def preview_renovacao(self, usuario: str, senha: str, meses: int = 1) -> PreviewRenovacao:
        conta = self.localizar_conta(usuario, senha)
        info = self._periodo(int(meses))
        p = info['package']
        return PreviewRenovacao(
            conta=conta, meses=int(meses), pacote_id=str(p.get('id')),
            pacote_nome=p.get('package_name_pt') or p.get('package_name_en') or p.get('package_name') or 'UniTV',
            creditos=Decimal(info['points']), conexoes=1,
            dados={'periodo': info['periodo'], 'points_type': info['points_type'], 'package': p},
        )

    def renovar(self, preview: PreviewRenovacao) -> ResultadoRenovacao:
        periodo = preview.dados['periodo']
        points_type = int(preview.dados['points_type'])
        points = preview.creditos
        points_value: Any = int(points) if points == points.to_integral() else float(points)
        sign = hashlib.md5(f'dealer{preview.conta.id}{points_type}{points_value}'.encode('utf-8')).hexdigest()
        payload = {
            'package_id': int(preview.pacote_id),
            'points_type': points_type,
            'auth_cycle': int(periodo.get('auth_cycle') or 1),
            'points': points_value,
            'pre_auth_id': int(periodo.get('pre_auth_id')),
            'sn': preview.conta.usuario,
            'id': int(preview.conta.id),
            'sign': sign,
        }
        res = self._post('/account/renew', payload)
        # O painel informa que a efetivação pode levar até 5 minutos. Não fazemos
        # uma segunda renovação para "testar". O vencimento local previsto é
        # calculado pela camada de negócio e a operação fica auditada.
        msg = res.get('meta', {}).get('errorMessage') or 'Renovação aceita pela UniTV.'
        return ResultadoRenovacao(
            sucesso=True, conta=preview.conta, creditos=preview.creditos,
            vencimento_novo=None, status_externo='aceita', mensagem=msg,
            dados={'uuid': (res.get('decoded') or {}).get('uuid') if isinstance(res.get('decoded'), dict) else None, 'meta': res.get('meta', {})},
        )


def get_painel_adapter(servico) -> BasePainelAdapter:
    tipo = (getattr(servico, 'integracao_tipo', '') or '').lower()
    if not getattr(servico, 'integracao_ativa', False) or tipo in ('', 'nenhuma'):
        raise IntegracaoPainelErro('Este servidor não possui integração automática ativa.')
    if tipo == 'sigman':
        return SigmanAdapter(servico)
    if tipo == 'unitv':
        return UnitvAdapter(servico)
    raise IntegracaoPainelErro(f'Tipo de integração não suportado: {tipo}')
