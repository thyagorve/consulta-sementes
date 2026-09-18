import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.http import HttpResponse
from django.conf import settings

from .models import (
    Armazem,
    Categoria,
    Cultivar,
    Endereco,
    Especie,
    Estoque,
    HistoricoMovimentacao,
    ItemEmpenho,
    LoteSyncEvento,
    LoteSyncState,
    Peneira,
    Produto,
    SyncConflict,
    SyncLog,
    SyncOperation,
    Tratamento,
)
from .serializers import OfflineTokenObtainPairSerializer, SyncBatchSerializer


OFFLINE_SESSION_HOURS = 5
REFERENCE_TTL_SECONDS = 30 * 60


def service_worker(request):
    """Serve o SW na raiz para que o escopo PWA cubra todo o sistema."""
    sw_path = settings.BASE_DIR / 'sapp' / 'static' / 'js' / 'service-worker.js'
    try:
        content = sw_path.read_text(encoding='utf-8')
    except OSError:
        return HttpResponse('// service worker indisponivel', content_type='application/javascript', status=404)
    response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


class OfflineTokenObtainPairView(TokenObtainPairView):
    serializer_class = OfflineTokenObtainPairSerializer


def _token_payload_for_user(user):
    agora = timezone.now()
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = user.pk
    refresh['username'] = user.get_username()
    refresh['login_em'] = int(agora.timestamp())
    access = refresh.access_token
    return {
        'access': str(access),
        'refresh': str(refresh),
        'user_id': user.pk,
        'username': user.get_username(),
        'login_em': agora.isoformat(),
        'expira_em': (agora + timedelta(hours=OFFLINE_SESSION_HOURS)).isoformat(),
    }


def _token_login_valido(request):
    token = getattr(request, 'auth', None)
    if token is None:
        return False
    try:
        login_em = int(token.get('login_em', 0))
    except (TypeError, ValueError):
        return False
    if not login_em:
        return False
    idade = timezone.now().timestamp() - login_em
    return 0 <= idade <= OFFLINE_SESSION_HOURS * 3600


class OfflineSessionView(APIView):
    """Converte a sessão Django online já autenticada em JWT para o PWA."""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Login online obrigatório.'}, status=401)
        return Response(_token_payload_for_user(request.user))


class OfflineReferenceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _token_login_valido(request):
            return Response({'code': 'SESSION_EXPIRED', 'detail': 'Sessão offline expirada.'}, status=401)

        estados = {
            x['lote']: x['versao']
            for x in LoteSyncState.objects.values('lote', 'versao')
        }
        estoques = []
        qs = (
            Estoque.objects
            .select_related('cultivar', 'peneira', 'categoria', 'tratamento', 'especie')
            .order_by('lote', 'endereco')
        )
        for item in qs.iterator(chunk_size=500):
            estoques.append({
                'id': item.id,
                'lote': item.lote,
                'produto': item.produto or '',
                'cultivar': item.cultivar.nome if item.cultivar else '',
                'peneira': item.peneira.nome if item.peneira else '',
                'categoria': item.categoria.nome if item.categoria else '',
                'tratamento': item.tratamento.nome if item.tratamento else '',
                'especie': item.especie.nome if item.especie else '',
                'endereco': item.endereco or '',
                'az': item.az or '',
                'embalagem': item.embalagem or '',
                'saldo': item.saldo,
                'empenhado': item.empenhado,
                'disponivel': item.disponivel,
                'cliente': item.cliente or '',
                'versao_lote': int(estados.get(item.lote, 0)),
            })

        agora = timezone.now()
        return Response({
            'gerado_em': agora.isoformat(),
            'validade_ate': (agora + timedelta(seconds=REFERENCE_TTL_SECONDS)).isoformat(),
            'ttl_segundos': REFERENCE_TTL_SECONDS,
            'estoques': estoques,
            'cadastros': {
                'cultivares': list(Cultivar.objects.values('id', 'nome')),
                'peneiras': list(Peneira.objects.values('id', 'nome')),
                'categorias': list(Categoria.objects.values('id', 'nome')),
                'tratamentos': list(Tratamento.objects.values('id', 'nome')),
                'especies': list(Especie.objects.values('id', 'nome')),
                'armazens': list(Armazem.objects.values('id', 'nome')),
                'enderecos': list(Endereco.objects.values('id', 'codigo', 'armazem_id')),
                'produtos': list(Produto.objects.values('id', 'codigo', 'descricao', 'cultivar_id')),
            },
        })


def _decimal_quantidade(valor):
    try:
        qtd = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Quantidade inválida.')
    if qtd <= 0:
        raise ValueError('Quantidade deve ser maior que zero.')
    if qtd != qtd.to_integral_value():
        raise ValueError('Este estoque trabalha com quantidade inteira de embalagens.')
    return int(qtd)


def _estoque_snapshot(estoque):
    return {
        'estoque_id': estoque.id,
        'lote': estoque.lote,
        'endereco': estoque.endereco,
        'saldo': estoque.saldo,
        'empenhado': estoque.empenhado,
        'disponivel': estoque.disponivel,
        'embalagem': estoque.embalagem,
        'cliente': estoque.cliente or '',
    }


def _eventos_externos(lote, base_versao, user):
    return list(
        LoteSyncEvento.objects
        .filter(lote__iexact=lote, versao__gt=base_versao)
        .exclude(usuario_id=user.id)
        .select_related('usuario', 'historico')
        .order_by('versao')[:30]
    )


def _contexto_conflito(lote, base_versao, user):
    state = LoteSyncState.objects.filter(lote__iexact=lote).first()
    eventos = _eventos_externos(lote, base_versao, user)
    estoques = Estoque.objects.filter(lote__iexact=lote).order_by('id')
    return {
        'lote': lote,
        'base_versao': int(base_versao or 0),
        'versao_atual': int(state.versao if state else 0),
        'movimentos_de_outros': [
            {
                'versao': e.versao,
                'usuario_id': e.usuario_id,
                'usuario': e.usuario.get_full_name() or e.usuario.username if e.usuario else 'Usuário removido',
                'tipo': e.tipo,
                'data': e.criado_em.isoformat(),
                'quantidade': e.historico.quantidade if e.historico else None,
            }
            for e in eventos
        ],
        'saldo_atual': [_estoque_snapshot(e) for e in estoques],
    }


def _normalizar_numero_carga_avulsa(valor):
    texto = str(valor or '').strip().upper()
    if not texto:
        return ''
    texto = texto.replace('-', ' ').replace(':', ' ')
    texto = ' '.join(texto.split())
    if texto.startswith('CARGA'):
        texto = texto[5:].strip()
    if not texto.isdigit():
        return ''
    return f"CARGA {texto.lstrip('0') or '0'}"


def _registrar_historico_saida(estoque, user, qtd, tipo, descricao, payload):
    origem = str(payload.get('origem_carga') or '').strip().upper()
    numero_bruto = str(payload.get('numero_carga') or '').strip()
    if origem == 'AVULSA':
        numero = _normalizar_numero_carga_avulsa(numero_bruto) if numero_bruto else ''
        if numero_bruto and not numero:
            raise ValueError('Nº da carga inválido. Informe apenas o número, por exemplo: 10.')
    else:
        numero = numero_bruto
    return HistoricoMovimentacao.objects.create(
        estoque=estoque,
        usuario=user,
        quantidade=qtd,
        tipo=tipo,
        descricao=descricao,
        numero_carga=(numero or None),
        motorista=(str(payload.get('motorista') or '').strip() or None),
        placa=(str(payload.get('placa') or '').strip().upper() or None),
        cliente=(str(payload.get('cliente') or '').strip() or None),
        origem_carga=('AVULSA' if origem == 'AVULSA' else ''),
        nome_carga_avulsa='',
    )


def _aplicar_operacao(op, user, ignorar_conflito=False):
    payload = dict(op.payload or {})
    tipo = str(op.tipo or '').upper().strip()

    # Movimentação de card gerado (transferir/expedir). Reutiliza a regra
    # oficial já existente no sistema, mas antes compara a versão de cada lote.
    if tipo == 'SOLICITACAO_CRIAR':
        entries = payload.get('form_entries') or []
        if not isinstance(entries, list):
            raise ValueError('Dados da solicitação offline inválidos.')

        from django.http import QueryDict
        from django.test.client import RequestFactory
        from django.contrib.messages.storage.cookie import CookieStorage
        from .views import _salvar_solicitacao_form
        from .models import Solicitacao

        q = QueryDict('', mutable=True)
        for par in entries:
            if not isinstance(par, (list, tuple)) or len(par) != 2:
                continue
            q.appendlist(str(par[0]), str(par[1]))

        rf = RequestFactory()
        req = rf.post('/solicitacoes/nova/')
        req._post = q
        req._files = {}
        req.user = user
        req.session = {}
        req._messages = CookieStorage(req)

        antes = set(Solicitacao.objects.filter(criador=user).values_list('id', flat=True))
        resposta = _salvar_solicitacao_form(req)
        nova = (
            Solicitacao.objects
            .filter(criador=user)
            .exclude(id__in=antes)
            .order_by('-id')
            .first()
        )
        if not nova:
            mensagens = [str(m.message) for m in list(req._messages)]
            raise ValueError(mensagens[-1] if mensagens else 'Não foi possível criar a solicitação offline.')
        return 'ACEITA', {
            'solicitacao_id': nova.id,
            'titulo': nova.titulo,
            'tipo_solicitacao': nova.tipo_solicitacao,
            'status': nova.status,
        }

    if tipo == 'SOLICITACAO_EMPENHAR':
        solicitacao_id = int(payload.get('solicitacao_id') or 0)
        adicionar = list(payload.get('adicionar') or [])
        remover = [int(x) for x in (payload.get('remover') or []) if str(x).isdigit()]
        if not solicitacao_id or (not adicionar and not remover):
            raise ValueError('Alterações do empenho não informadas.')

        # Todo lote afetado participa da regra de conflito, inclusive remoção
        # de reserva. Qualquer movimento de OUTRO usuário após a versão vista
        # pelo aparelho exige decisão do conferente.
        estoque_ids = {int(x.get('lote_id')) for x in adicionar if str(x.get('lote_id') or '').isdigit()}
        if remover:
            estoque_ids.update(
                ItemEmpenho.objects
                .filter(id__in=remover, empenho__solicitacao_id=solicitacao_id)
                .values_list('estoque_id', flat=True)
            )
        lotes = list(Estoque.objects.filter(id__in=estoque_ids).values('id', 'lote'))
        base_map = payload.get('base_lote_versoes') or {}
        if not ignorar_conflito:
            for row in lotes:
                lote_item = str(row.get('lote') or '').strip()
                if not lote_item:
                    continue
                base = int(base_map.get(lote_item, 0) or 0)
                eventos = _eventos_externos(lote_item, base, user)
                if eventos:
                    contexto = _contexto_conflito(lote_item, base, user)
                    conflito, _ = SyncConflict.objects.update_or_create(
                        operacao=op,
                        defaults={
                            'lote': lote_item,
                            'base_versao': base,
                            'versao_atual': contexto['versao_atual'],
                            'contexto_servidor': contexto,
                            'status': 'PENDENTE',
                        },
                    )
                    op.status = 'CONFLITO'
                    op.processado_em = timezone.now()
                    op.resultado = {'conflito_id': conflito.id, 'contexto': contexto}
                    op.save(update_fields=['status', 'processado_em', 'resultado'])
                    return 'CONFLITO', op.resultado

        import json as _json
        from django.test.client import RequestFactory
        from .views import api_remover_item_empenho, empenhar_na_solicitacao
        rf = RequestFactory()

        removidos = []
        for item_id in remover:
            req = rf.post(f'/api/solicitacoes/{solicitacao_id}/remover-item/{item_id}/')
            req.user = user
            resp = api_remover_item_empenho(req, solicitacao_id, item_id)
            conteudo = _json.loads(resp.content.decode('utf-8') or '{}')
            if resp.status_code >= 400 or not conteudo.get('success'):
                raise ValueError(conteudo.get('error') or f'Falha ao remover item {item_id}.')
            removidos.append(item_id)

        if adicionar:
            req = rf.post(
                f'/api/solicitacoes/{solicitacao_id}/empenhar/',
                data=_json.dumps({'itens': adicionar}),
                content_type='application/json',
            )
            req.user = user
            resp = empenhar_na_solicitacao(req, solicitacao_id)
            conteudo = _json.loads(resp.content.decode('utf-8') or '{}')
            if resp.status_code >= 400 or not conteudo.get('success'):
                raise ValueError(conteudo.get('error') or 'Falha ao salvar o empenho.')
        else:
            conteudo = {'success': True}

        return 'ACEITA', {
            'solicitacao_id': solicitacao_id,
            'adicionados': len(adicionar),
            'removidos': removidos,
            'resultado': conteudo,
        }

    if tipo == 'SOLICITACAO_MOVIMENTAR':
        solicitacao_id = int(payload.get('solicitacao_id') or 0)
        dados = dict(payload.get('dados') or {})
        itens_ids = [int(x) for x in (dados.get('itens_ids') or []) if str(x).isdigit()]
        if not solicitacao_id or not itens_ids:
            raise ValueError('Solicitação/itens não informados.')

        itens = list(
            ItemEmpenho.objects
            .select_related('estoque')
            .filter(id__in=itens_ids, empenho__solicitacao_id=solicitacao_id)
        )
        if not itens:
            raise ValueError('Itens da solicitação não estão mais disponíveis.')

        base_map = payload.get('base_lote_versoes') or {}
        if not ignorar_conflito:
            for item in itens:
                lote_item = str(item.estoque.lote if item.estoque else item.lote or '').strip()
                if not lote_item:
                    continue
                base = int(base_map.get(lote_item, 0) or 0)
                eventos = _eventos_externos(lote_item, base, user)
                if eventos:
                    contexto = _contexto_conflito(lote_item, base, user)
                    conflito, _ = SyncConflict.objects.update_or_create(
                        operacao=op,
                        defaults={
                            'lote': lote_item,
                            'base_versao': base,
                            'versao_atual': contexto['versao_atual'],
                            'contexto_servidor': contexto,
                            'status': 'PENDENTE',
                        },
                    )
                    op.status = 'CONFLITO'
                    op.processado_em = timezone.now()
                    op.resultado = {'conflito_id': conflito.id, 'contexto': contexto}
                    op.save(update_fields=['status', 'processado_em', 'resultado'])
                    return 'CONFLITO', op.resultado

        # Chama internamente a mesma view online. Idempotência é garantida pelo
        # SyncOperation.operacao_id antes de chegar aqui.
        import json as _json
        from django.test.client import RequestFactory
        from .views import api_movimentar_solicitacao

        req = RequestFactory().post(
            f'/api/solicitacoes/{solicitacao_id}/movimentar/',
            data=_json.dumps(dados),
            content_type='application/json',
        )
        req.user = user
        resposta = api_movimentar_solicitacao(req, solicitacao_id)
        conteudo = _json.loads(resposta.content.decode('utf-8') or '{}')
        if resposta.status_code >= 400 or not conteudo.get('success'):
            raise ValueError(conteudo.get('error') or f'Falha HTTP {resposta.status_code}.')
        return 'ACEITA', conteudo
    lote = str(op.lote or payload.get('lote') or '').strip()
    if not lote:
        raise ValueError('Lote não informado.')

    estoque_id = payload.get('estoque_id')
    if estoque_id is None:
        estoque_id = payload.get('item_id')
    estoque_qs = Estoque.objects.select_for_update().filter(lote__iexact=lote)
    if estoque_id:
        estoque_qs = estoque_qs.filter(pk=estoque_id)
    estoque = estoque_qs.order_by('id').first()
    if not estoque:
        raise ValueError(f'Lote {lote} não encontrado no estoque atual.')

    if not ignorar_conflito:
        eventos = _eventos_externos(lote, op.base_lote_versao, user)
        if eventos:
            contexto = _contexto_conflito(lote, op.base_lote_versao, user)
            conflito, _ = SyncConflict.objects.update_or_create(
                operacao=op,
                defaults={
                    'lote': lote,
                    'base_versao': op.base_lote_versao,
                    'versao_atual': contexto['versao_atual'],
                    'contexto_servidor': contexto,
                    'status': 'PENDENTE',
                },
            )
            op.status = 'CONFLITO'
            op.processado_em = timezone.now()
            op.resultado = {'conflito_id': conflito.id, 'contexto': contexto}
            op.save(update_fields=['status', 'processado_em', 'resultado'])
            return 'CONFLITO', op.resultado

    qtd = _decimal_quantidade(payload.get('quantidade'))

    if tipo in {'SAIDA', 'EXPEDICAO', 'EXPEDICAO_AVULSA', 'BENEFICIAMENTO'}:
        # Saídas avulsas/beneficiamento nunca podem consumir reserva de card.
        # A fila precisa obedecer exatamente a mesma regra da operação online.
        if tipo == 'EXPEDICAO_AVULSA':
            payload['origem_carga'] = 'AVULSA'
        disponivel = max(0, int(estoque.saldo or 0) - int(estoque.empenhado or 0))
        if qtd > disponivel:
            raise ValueError(
                f'Quantidade indisponível. Saldo físico: {estoque.saldo}; '
                f'empenhado: {estoque.empenhado}; disponível avulso: {disponivel} {estoque.embalagem}.'
            )
        estoque.saida = int(estoque.saida or 0) + qtd
        estoque.save()
        from .views import _validar_integridade_estoque
        _validar_integridade_estoque(estoque)
        numero_avulsa = str(payload.get('numero_carga') or '').strip()
        descricao = f'Operação offline sincronizada: saída de {qtd} {estoque.embalagem} do lote {lote}.'
        if tipo == 'EXPEDICAO_AVULSA' and numero_avulsa:
            numero_canonico = _normalizar_numero_carga_avulsa(numero_avulsa)
            if numero_canonico:
                descricao += f' {numero_canonico}.'
        _registrar_historico_saida(
            estoque,
            user,
            qtd,
            ('Beneficiamento (Saída)' if tipo == 'BENEFICIAMENTO' else ('Expedição' if tipo not in {'SAIDA'} else 'Saída')),
            descricao,
            payload,
        )
        return 'ACEITA', {'lote': lote, 'saldo': estoque.saldo, 'estoque_id': estoque.id}

    if tipo == 'TRANSFERENCIA':
        destino_endereco = str(payload.get('endereco_destino') or '').strip().upper()
        if not destino_endereco:
            raise ValueError('Endereço de destino não informado.')
        if str(estoque.endereco or '').strip().upper() == destino_endereco:
            raise ValueError('O endereço de destino deve ser diferente do endereço atual.')
        if estoque.saldo < qtd:
            raise ValueError(f'Saldo insuficiente. Saldo atual: {estoque.saldo} {estoque.embalagem}.')

        # Não mistura registros apenas porque lote/endereço são iguais. Os
        # atributos físicos/comerciais precisam representar o mesmo estoque.
        destino = (
            Estoque.objects.select_for_update(of=('self',))
            .filter(
                lote__iexact=estoque.lote,
                produto=estoque.produto,
                cultivar=estoque.cultivar,
                peneira=estoque.peneira,
                categoria=estoque.categoria,
                tratamento=estoque.tratamento,
                especie=estoque.especie,
                endereco__iexact=destino_endereco,
                empresa=estoque.empresa,
                embalagem=estoque.embalagem,
                cliente=estoque.cliente,
                peso_unitario=estoque.peso_unitario,
            )
            .order_by('id')
            .first()
        )
        if destino is None:
            destino = Estoque.objects.create(
                lote=estoque.lote,
                produto=estoque.produto,
                cultivar=estoque.cultivar,
                peneira=estoque.peneira,
                categoria=estoque.categoria,
                tratamento=estoque.tratamento,
                especie=estoque.especie,
                endereco=destino_endereco,
                entrada=qtd,
                saida=0,
                empenhado=0,
                conferente=user,
                origem_destino=estoque.endereco,
                empresa=estoque.empresa,
                embalagem=estoque.embalagem,
                peso_unitario=estoque.peso_unitario,
                az=str(payload.get('az_destino') or '').strip().upper(),
                cliente=estoque.cliente,
                observacao=estoque.observacao,
                status_sistemico=estoque.status_sistemico,
            )
        else:
            destino.entrada = int(destino.entrada or 0) + qtd
            destino.conferente = user
            destino.save()

        estoque.saida = int(estoque.saida or 0) + qtd
        estoque.conferente = user
        estoque.save()

        # Regra central: os livres saem primeiro; se a transferência ultrapassa
        # o livre, a fração empenhada viaja junto para o novo endereço.
        from .views import _realocar_empenho_apos_transferencia_avulsa, _validar_integridade_estoque
        reserva_realocada = _realocar_empenho_apos_transferencia_avulsa(estoque, destino)
        _validar_integridade_estoque(estoque, destino)

        HistoricoMovimentacao.objects.create(
            estoque=estoque,
            usuario=user,
            quantidade=qtd,
            tipo='Transferência (Saída)',
            descricao=(
                f'Operação da fila sincronizada: {qtd} de {estoque.endereco} para {destino_endereco}. '
                f'Reserva acompanhando o lote: {reserva_realocada}.'
            ),
        )
        HistoricoMovimentacao.objects.create(
            estoque=destino,
            usuario=user,
            quantidade=qtd,
            tipo='Transferência (Entrada)',
            descricao=f'Operação da fila sincronizada: {qtd} recebidos de {estoque.endereco}.',
        )
        estoque.refresh_from_db(fields=['saldo', 'empenhado'])
        destino.refresh_from_db(fields=['saldo', 'empenhado'])
        return 'ACEITA', {
            'lote': lote,
            'estoque_origem_id': estoque.id,
            'saldo_origem': estoque.saldo,
            'empenhado_origem': estoque.empenhado,
            'disponivel_origem': estoque.disponivel,
            'estoque_destino_id': destino.id,
            'saldo_destino': destino.saldo,
            'empenhado_destino': destino.empenhado,
            'disponivel_destino': destino.disponivel,
            'reserva_realocada': reserva_realocada,
        }

    raise ValueError(
        'Esta operação ainda exige conexão. Cadastros, anexos e operações estruturais não entram na fila offline.'
    )


class SyncView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _token_login_valido(request):
            return Response({'code': 'SESSION_EXPIRED', 'detail': 'Faça login online novamente para sincronizar.'}, status=401)

        serializer = SyncBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device_id = data['device_id']
        aceitos, rejeitados, conflitos = [], [], []

        for entrada in data['operacoes']:
            op_uuid = entrada['id']
            existente = SyncOperation.objects.filter(operacao_id=op_uuid).first()
            op = None
            if existente:
                item = {'id': str(op_uuid), 'resultado': existente.resultado}
                if existente.status == 'ACEITA':
                    aceitos.append(item)
                    continue
                if existente.status == 'CONFLITO':
                    conflitos.append(item)
                    continue
                if existente.status in {'REJEITADA', 'CANCELADA'}:
                    rejeitados.append({'id': str(op_uuid), 'motivo': existente.motivo or existente.status, 'resultado': existente.resultado})
                    continue
                # PENDENTE pode existir se o processo foi interrompido antes de
                # concluir o lote. É seguro tentar novamente porque a alteração
                # de negócio e o status final são gravados atomicamente abaixo.
                op = existente

            if op is None:
                payload = dict(entrada.get('payload') or {})
                if entrada.get('estoque_id') is not None:
                    payload.setdefault('estoque_id', entrada['estoque_id'])
                if entrada.get('quantidade') is not None:
                    payload.setdefault('quantidade', str(entrada['quantidade']))

                op = SyncOperation.objects.create(
                    operacao_id=op_uuid,
                    usuario=request.user,
                    device_id=device_id,
                    tipo=entrada['tipo'],
                    lote=entrada.get('lote', ''),
                    base_lote_versao=entrada.get('base_lote_versao', 0),
                    criado_local_em=entrada.get('criado_local_em'),
                    payload=payload,
                )

            try:
                with transaction.atomic():
                    resultado_status, resultado = _aplicar_operacao(op, request.user)
                    if resultado_status == 'CONFLITO':
                        conflitos.append({'id': str(op_uuid), **resultado})
                    else:
                        op.status = 'ACEITA'
                        op.processado_em = timezone.now()
                        op.resultado = resultado
                        op.save(update_fields=['status', 'processado_em', 'resultado'])
                        aceitos.append({'id': str(op_uuid), 'resultado': resultado})
            except Exception as exc:
                op.status = 'REJEITADA'
                op.processado_em = timezone.now()
                op.motivo = str(exc)
                op.resultado = {'motivo': str(exc)}
                op.save(update_fields=['status', 'processado_em', 'motivo', 'resultado'])
                rejeitados.append({'id': str(op_uuid), 'motivo': str(exc)})

        SyncLog.objects.create(
            usuario=request.user,
            device_id=device_id,
            payload=request.data,
            aceitos=aceitos,
            rejeitados=rejeitados,
            conflitos=conflitos,
        )
        return Response({'aceitos': aceitos, 'rejeitados': rejeitados, 'conflitos': conflitos})


class SyncCentralView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _token_login_valido(request):
            return Response({'code': 'SESSION_EXPIRED'}, status=401)
        device_id = request.query_params.get('device_id', '')
        # Pendências comuns ficam no dispositivo/usuário atual. Conflitos são
        # visíveis para qualquer conferente autenticado, conforme a regra operacional.
        qs_own = SyncOperation.objects.filter(usuario=request.user)
        if device_id:
            qs_own = qs_own.filter(device_id=device_id)
        qs = SyncOperation.objects.filter(
            Q(id__in=qs_own.values('id')) | Q(status='CONFLITO')
        ).distinct()
        ops = list(qs.select_related('conflito', 'usuario')[:250])
        return Response({
            'operacoes': [
                {
                    'id': str(op.operacao_id),
                    'db_id': op.id,
                    'tipo': op.tipo,
                    'lote': op.lote,
                    'usuario': op.usuario.get_full_name() or op.usuario.username,
                    'usuario_id': op.usuario_id,
                    'status': op.status,
                    'criado_local_em': op.criado_local_em.isoformat() if op.criado_local_em else None,
                    'recebido_em': op.recebido_em.isoformat(),
                    'motivo': op.motivo,
                    'resultado': op.resultado,
                    'conflito_id': getattr(getattr(op, 'conflito', None), 'id', None),
                    'contexto_conflito': (
                        getattr(op.conflito, 'contexto_servidor', {})
                        if hasattr(op, 'conflito') else {}
                    ),
                }
                for op in ops
            ],
            'contadores': {
                chave: qs.filter(status=chave).count()
                for chave in ['PENDENTE', 'CONFLITO', 'REJEITADA', 'ACEITA']
            },
        })


class SyncConflictResolveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, conflict_id):
        if not _token_login_valido(request):
            return Response({'code': 'SESSION_EXPIRED'}, status=401)
        acao = str(request.data.get('acao') or '').upper()
        if acao not in {'APLICAR', 'AJUSTAR', 'CANCELAR'}:
            return Response({'detail': 'Ação inválida.'}, status=400)

        with transaction.atomic():
            conflito = (
                SyncConflict.objects.select_for_update()
                .select_related('operacao')
                .filter(pk=conflict_id, status='PENDENTE')
                .first()
            )
            if not conflito:
                return Response({'detail': 'Conflito não encontrado ou já resolvido.'}, status=404)
            op = conflito.operacao

            if acao == 'CANCELAR':
                op.status = 'CANCELADA'
                op.processado_em = timezone.now()
                op.motivo = 'Cancelada durante resolução de conflito.'
                op.save(update_fields=['status', 'processado_em', 'motivo'])
                conflito.status = 'CANCELADA'
                conflito.resolucao = {'acao': 'CANCELAR'}
            else:
                if acao == 'AJUSTAR':
                    if op.tipo in {'SOLICITACAO_MOVIMENTAR', 'SOLICITACAO_EMPENHAR', 'SOLICITACAO_CRIAR'}:
                        return Response(
                            {'detail': 'Esta operação composta não permite ajuste simples de quantidade. Aplique ou cancele e refaça a operação.'},
                            status=400,
                        )
                    qtd = request.data.get('quantidade')
                    payload = dict(op.payload or {})
                    payload['quantidade'] = str(qtd)
                    op.payload = payload
                    op.save(update_fields=['payload'])
                try:
                    # A operação continua pertencendo a quem a criou. O conferente
                    # que decide fica registrado em resolvido_por, sem trocar autoria.
                    resultado_status, resultado = _aplicar_operacao(op, op.usuario, ignorar_conflito=True)
                except Exception as exc:
                    return Response({'detail': str(exc)}, status=409)
                op.status = 'ACEITA'
                op.processado_em = timezone.now()
                op.resultado = resultado
                op.motivo = ''
                op.save(update_fields=['status', 'processado_em', 'resultado', 'motivo'])
                conflito.status = 'AJUSTADA' if acao == 'AJUSTAR' else 'APLICADA'
                conflito.resolucao = {'acao': acao, 'resultado': resultado}

            conflito.resolvido_por = request.user
            conflito.resolvido_em = timezone.now()
            conflito.save(update_fields=['status', 'resolucao', 'resolvido_por', 'resolvido_em'])
            return Response({'ok': True, 'status': conflito.status, 'operacao': str(op.operacao_id)})
