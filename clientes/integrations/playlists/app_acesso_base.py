import time
from urllib.parse import urlparse

import requests

from .base import PlaylistProvider


class AppAcessoBase(PlaylistProvider):
    SITE_URL = ""
    BASE_URL = ""
    TIMEOUT = 30

    def _headers(self, json=True):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": self.SITE_URL,
            "Referer": f"{self.SITE_URL.rstrip('/')}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        }
        if json:
            headers["Content-Type"] = "application/json"
        return headers

    def _session(self):
        session = requests.Session()
        session.headers.update(self._headers())
        return session

    @staticmethod
    def _mac(valor):
        return str(valor or "").strip().lower()

    @staticmethod
    def _json(response):
        try:
            return response.json()
        except ValueError:
            return {
                "error": True,
                "message": response.text[:800],
                "status": response.status_code,
            }

    @staticmethod
    def _mensagem(data, padrao):
        if not isinstance(data, dict):
            return padrao
        mensagem = data.get("message")
        if isinstance(mensagem, dict):
            return str(
                mensagem.get("message")
                or mensagem.get("detail")
                or mensagem.get("error")
                or padrao
            )
        if isinstance(mensagem, list):
            return ", ".join(map(str, mensagem))
        return str(mensagem or data.get("detail") or data.get("error_message") or padrao)

    @staticmethod
    def normalizar_dns(dns):
        dns = str(dns or "").strip().rstrip("/")
        if not dns:
            return ""
        if not urlparse(dns).scheme:
            dns = f"http://{dns}"
        return dns.rstrip("/")

    @classmethod
    def montar_url_xtream(cls, dns, usuario, senha):
        dns = cls.normalizar_dns(dns)
        if not dns:
            return ""
        return (
            f"{dns}/get.php?username={usuario}&password={senha}"
            "&type=m3u_plus&output=ts"
        )

    def pesquisar_dispositivo(self):
        mac = self._mac(getattr(self.integracao, "mac_address", ""))
        if not mac:
            return {"success": False, "confirmed": False, "message": "Informe o MAC do dispositivo.", "status": "erro", "data": {}}

        try:
            response = requests.get(
                f"{self.BASE_URL}/validate_mac",
                params={"mac": mac},
                headers=self._headers(),
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            sucesso = response.status_code == 200 and isinstance(data, dict) and not data.get("error")
            dispositivo = data.get("message", {}) if sucesso else {}
            if not isinstance(dispositivo, dict):
                dispositivo = {}
            return {
                "success": sucesso,
                "confirmed": sucesso,
                "message": f"Dispositivo {self.nome} encontrado." if sucesso else self._mensagem(data, f"Dispositivo não encontrado no {self.nome}."),
                "status": "configurado" if sucesso else "erro",
                "data": dispositivo,
                "http_status": response.status_code,
            }
        except requests.Timeout:
            return {"success": False, "confirmed": False, "message": f"O {self.nome} demorou demais para responder.", "status": "erro", "data": {}}
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "message": f"Erro de conexão com {self.nome}: {erro}", "status": "erro", "data": {}}



    # app_acesso_base.py (classe AppAcessoBase)

    def _sanitizar_resultado(self, resultado):
        """Remove campos sensíveis antes de retornar para views/histórico."""
        if not isinstance(resultado, dict):
            return resultado
        dados = resultado.get("data")
        if isinstance(dados, dict):
            # Remove chaves sensíveis de forma profunda (senhas, PIN, tokens)
            chaves_sensiveis = {"password", "senha", "pin", "confirm_pin", "token", "access_token", "jwt"}
            for chave in list(dados.keys()):
                if chave.lower() in chaves_sensiveis:
                    dados[chave] = "***"
            # Se houver sub-dicionários como "cadastro", sanitiza também
            for subchave in ("cadastro", "playlist", "resposta", "validacao", "exclusao"):
                sub = dados.get(subchave)
                if isinstance(sub, dict):
                    for k in list(sub.keys()):
                        if k.lower() in chaves_sensiveis:
                            sub[k] = "***"
        return resultado

    def _validar_exclusao(self, remote_id, pin, session):
        """Usa a sessão autenticada para validar PIN antes da exclusão."""
        response = session.get(
            f"{self.BASE_URL}/protected_playlist",
            params={"id": int(remote_id), "pin": str(pin or "")},
            timeout=self.TIMEOUT,
        )
        data = self._json(response)
        sucesso = response.status_code == 200 and not data.get("error")
        return sucesso, response, data

    def excluir_playlist(self, remote_id="", pin="", **kwargs):
        remote_id = str(remote_id or "").strip()
        pin = str(pin or "").strip()

        if not remote_id.isdigit():
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "ID remoto da playlist inválido ou ausente.",
                "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None
            })

        if not pin:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Informe o PIN usado na playlist.",
                "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None
            })

        # 1. Autentica (obtém token)
        session = self._session()
        token, auth_data, auth_status = self._autenticar(session)

        if not token:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": self._mensagem(auth_data, "Falha na autenticação para exclusão."),
                "status": "erro", "remote_id": remote_id,
                "data": {"auth": auth_data}, "http_status": auth_status
            })

        try:
            # 2. Valida PIN/playlist usando sessão autenticada
            validou, response_validacao, data_validacao = self._validar_exclusao(
                remote_id, pin, session
            )
            status_validacao = getattr(response_validacao, "status_code", None)

            if not validou:
                mensagem = self._mensagem(data_validacao, "PIN incorreto ou playlist não encontrada.")
                return self._sanitizar_resultado({
                    "success": False, "confirmed": False,
                    "message": mensagem, "status": "erro", "remote_id": remote_id,
                    "data": {"validacao": data_validacao}, "http_status": status_validacao
                })

            # 3. Exclui usando a sessão autenticada
            # Endpoint corrigido (typo "palylist" -> "playlist")
            response = session.delete(
                f"{self.BASE_URL}/playlist_from_web",
                json={"id": int(remote_id), "pin": pin},
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            if not isinstance(data, dict):
                data = {"raw_response": str(data or "")}

            # Interpreta resposta
            sucesso_exclusao = (
                response.status_code in (200, 201, 204)
                and not data.get("error")
                and not data.get("erro")
            )
            if sucesso_exclusao:
                mensagem = "Playlist excluída com sucesso no {}.".format(self.nome)
                status_final = "excluido"
            else:
                mensagem = self._mensagem(data, "O aplicativo não confirmou a exclusão.")
                status_final = "erro"

            return self._sanitizar_resultado({
                "success": sucesso_exclusao,
                "confirmed": sucesso_exclusao,
                "message": mensagem,
                "status": status_final,
                "remote_id": remote_id,
                "data": {"validacao": data_validacao, "exclusao": data},
                "http_status": response.status_code
            })

        except requests.Timeout:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Tempo esgotado ao excluir a playlist.",
                "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None
            })
        except requests.RequestException as erro:
            resp = getattr(erro, "response", None)
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro", "remote_id": remote_id, "data": {},
                "http_status": getattr(resp, "status_code", None)
            })
        except Exception as erro:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro inesperado ao excluir: {erro}",
                "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None
            })