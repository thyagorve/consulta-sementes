import requests

from .app_acesso_base import AppAcessoBase


class AppAcessoUrlProvider(AppAcessoBase):
    """Fluxo FocoX/Lazer: MAC + URL direta. Sem Device Key e sem código."""

    campos = {
        "mac_address": {"mostrar": True, "obrigatorio": True, "label": "MAC Address"},
        "device_key": {"mostrar": False, "obrigatorio": False, "label": "Device Key"},
        "codigo": {"mostrar": False, "obrigatorio": False, "label": "Código do servidor"},
        "dns": {"mostrar": True, "obrigatorio": False, "label": "DNS do servidor"},
        "url_template": {"mostrar": True, "obrigatorio": False, "label": "URL completa da playlist"},
    }

    def adicionar_playlist(
        self,
        nome_playlist="",
        usuario="",
        senha="",
        dns="",
        url_playlist="",
        codigo="",
        proteger=False,
        pin="",
        modo_envio="",
        **kwargs,
    ):
        nome_playlist = str(nome_playlist or "").strip()
        usuario = str(usuario or "").strip()
        senha = str(senha or "").strip()
        dns = str(dns or "").strip()
        url_playlist = str(url_playlist or "").strip()
        codigo = str(
            codigo
            or getattr(self.integracao, "codigo", "")
            or ""
        ).strip()
        pin = str(pin or "").strip()
        modo = str(modo_envio or "").strip().lower()

        if modo not in self.modos_envio:
            modo = "url" if url_playlist or dns else "codigo"

        if not nome_playlist:
            nome_playlist = "Minha lista"

        if not usuario:
            return {
                "success": False,
                "confirmed": False,
                "message": "Informe o usuário IPTV.",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

        if not senha:
            return {
                "success": False,
                "confirmed": False,
                "message": "Informe a senha IPTV.",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

        if modo == "codigo" and not codigo:
            return {
                "success": False,
                "confirmed": False,
                "message": "Informe o código do servidor.",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

        if modo == "url" and not dns and not url_playlist:
            return {
                "success": False,
                "confirmed": False,
                "message": "Informe o DNS ou a URL completa da playlist.",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

        try:
            if modo == "codigo":
                resultado = self._adicionar_por_codigo(
                    nome_playlist=nome_playlist,
                    usuario=usuario,
                    senha=senha,
                    codigo=codigo,
                    proteger=bool(proteger),
                    pin=pin,
                )
            else:
                resultado = self._adicionar_por_url(
                    nome_playlist=nome_playlist,
                    usuario=usuario,
                    senha=senha,
                    dns=dns,
                    url_playlist=url_playlist,
                    proteger=bool(proteger),
                    pin=pin,
                )

            if not isinstance(resultado, dict):
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        f"O {self.nome} retornou uma resposta inválida "
                        "ao adicionar a playlist."
                    ),
                    "status": "erro",
                    "remote_id": "",
                    "data": {
                        "resposta_original": str(resultado or ""),
                    },
                    "http_status": None,
                }

            sucesso = bool(resultado.get("success"))

            remote_id = str(
                resultado.get("remote_id")
                or resultado.get("playlist_remote_id")
                or ""
            ).strip()

            confirmado_original = bool(
                resultado.get("confirmed", sucesso)
            )

            # A existência de um ID remoto confirma que a playlist foi localizada.
            confirmado = bool(
                sucesso and (
                    confirmado_original
                    or remote_id
                )
            )

            mensagem = str(
                resultado.get("message")
                or resultado.get("mensagem")
                or ""
            ).strip()

            if sucesso and remote_id:
                resultado["success"] = True
                resultado["confirmed"] = True
                resultado["status"] = "ativo"
                resultado["remote_id"] = remote_id

                mensagem_normalizada = mensagem.lower()

                mensagens_contraditorias = (
                    "id remoto ainda não foi localizado",
                    "id remoto não foi localizado",
                    "id remoto nao foi localizado",
                    "confirmação pendente",
                    "confirmacao pendente",
                )

                if (
                    not mensagem
                    or any(
                        texto in mensagem_normalizada
                        for texto in mensagens_contraditorias
                    )
                ):
                    resultado["message"] = (
                        f"Playlist enviada e identificada no {self.nome}. "
                        f"ID remoto: {remote_id}."
                    )

                return resultado

            if sucesso and not confirmado:
                resultado["success"] = True
                resultado["confirmed"] = False
                resultado["status"] = "confirmacao_pendente"
                resultado["remote_id"] = ""

                if not mensagem:
                    resultado["message"] = (
                        f"Playlist enviada ao {self.nome}, "
                        "mas o ID remoto ainda não foi localizado."
                    )

                return resultado

            if sucesso and confirmado:
                resultado["success"] = True
                resultado["confirmed"] = True
                resultado["status"] = "ativo"
                resultado["remote_id"] = remote_id

                if not mensagem:
                    resultado["message"] = (
                        f"Playlist enviada com sucesso ao {self.nome}."
                    )

                return resultado

            resultado["success"] = False
            resultado["confirmed"] = False
            resultado["status"] = "erro"
            resultado["remote_id"] = remote_id

            if not mensagem:
                resultado["message"] = (
                    f"Não foi possível adicionar a playlist no {self.nome}."
                )

            return resultado

        except requests.Timeout:
            return {
                "success": False,
                "confirmed": False,
                "message": f"O {self.nome} demorou demais para responder.",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

        except requests.RequestException as erro:
            response = getattr(erro, "response", None)

            return {
                "success": False,
                "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": getattr(response, "status_code", None),
            }

        except Exception as erro:
            return {
                "success": False,
                "confirmed": False,
                "message": (
                    f"Erro inesperado ao adicionar a playlist "
                    f"no {self.nome}: {erro}"
                ),
                "status": "erro",
                "remote_id": "",
                "data": {},
                "http_status": None,
            }

 