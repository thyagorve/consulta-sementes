import time
import requests
from .app_acesso_base import AppAcessoBase
import time
from urllib.parse import urlencode
import requests


class AppAcessoDualProvider(AppAcessoBase):
    campos = {
        "mac_address": {"mostrar": True, "obrigatorio": True, "label": "MAC Address"},
        "device_key": {"mostrar": True, "obrigatorio": False, "label": "Device Key"},
        "codigo": {"mostrar": True, "obrigatorio": False, "label": "Código do servidor"},
        "dns": {"mostrar": True, "obrigatorio": False, "label": "DNS do servidor"},
        "url_template": {"mostrar": True, "obrigatorio": False, "label": "URL completa da playlist"},
    }
    modos_envio = {
        "codigo": "Código do servidor",
        "url": "URL ou DNS",
    }

    # ---------- autenticação / listagem ----------
    def _autenticar(self, session):
        mac = self._mac(getattr(self.integracao, "mac_address", ""))
        key = str(getattr(self.integracao, "device_key", "") or "").strip()
        if not mac or not key:
            return None, {"error": True, "message": "MAC e Device Key são obrigatórios."}, 400
        resp = session.post(
            f"{self.BASE_URL}/login_by_mac",
            json={"mac": mac, "key": key},
            timeout=self.TIMEOUT,
        )
        data = self._json(resp)
        if resp.status_code != 200 or data.get("error"):
            return None, data, resp.status_code
        token = data.get("message", "")
        if isinstance(token, dict):
            token = token.get("token") or token.get("access_token") or token.get("jwt")
        token = str(token or "").strip()
        if not token:
            return None, data, resp.status_code
        session.headers.update({"Authorization": f"Bearer {token}"})
        return token, data, resp.status_code

    def _listar_playlists(self, session):
        resp = session.get(f"{self.BASE_URL}/device", timeout=self.TIMEOUT)
        data = self._json(resp)
        if resp.status_code != 200 or data.get("error"):
            return [], data, resp.status_code
        device = data.get("message", {})
        if not isinstance(device, dict):
            device = data.get("data", {})
        if not isinstance(device, dict):
            device = {}
        playlists = device.get("playlists") or device.get("playlist") or []
        if isinstance(playlists, dict):
            playlists = list(playlists.values())
        return playlists if isinstance(playlists, list) else [], data, resp.status_code

    # ---------- helpers para ID ----------
    @staticmethod
    def _extrair_id(item):
        if not isinstance(item, dict):
            return ""
        for campo in ("id", "playlist_id", "playlistId", "_id", "server_id"):
            val = str(item.get(campo, "") or "").strip()
            if val and val.lower() not in {"none", "null"}:
                return val
        return ""

    @staticmethod
    def _normalizar(valor):
        return str(valor or "").strip().casefold()

    def _campos_para_match(self, item):
        if not isinstance(item, dict):
            return set()
        campos = (
            item.get("name"), item.get("title"), item.get("playlist_name"),
            item.get("playlistName"), item.get("username"), item.get("user"),
            item.get("code"), item.get("server_code"),
        )
        return {self._normalizar(v) for v in campos if str(v or "").strip()}

    def _match_mac(self, item, mac_esperada):
        if not isinstance(item, dict):
            return False
        mac_item = self._mac(item.get("mac", "") or "")
        return mac_item == mac_esperada


    def _adicionar_por_url(self, *, nome_playlist, usuario, senha, dns, url_playlist, proteger, pin):
        import time
        from urllib.parse import urlencode

        mac = self._mac(getattr(self.integracao, "mac_address", ""))
        pin = str(pin or "").strip()
        proteger = bool(proteger)

        # Validações
        if not mac:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Informe o MAC Address.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })
        if not nome_playlist:
            nome_playlist = "Minha lista"
        if not usuario or not senha:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Informe usuário e senha IPTV.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })
        if proteger and not pin:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Informe o PIN de proteção.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })

        # Monta URL da playlist
        if url_playlist:
            url_final = url_playlist.strip()
        else:
            dns = dns.strip().rstrip("/")
            if not dns:
                return self._sanitizar_resultado({
                    "success": False, "confirmed": False,
                    "message": "Informe o DNS do servidor ou a URL completa.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
                })
            if not dns.startswith(("http://", "https://")):
                dns = f"http://{dns}"
            query = urlencode({
                "username": usuario,
                "password": senha,
                "type": "m3u_plus",
                "output": "ts",
            })
            url_final = f"{dns}/get.php?{query}"

        if not url_final:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Não foi possível determinar a URL da playlist.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })

        # Autenticação
        session = self._session()
        token, auth_data, auth_status = self._autenticar(session)
        if not token:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": self._mensagem(auth_data, "Falha na autenticação."),
                "status": "erro", "remote_id": "",
                "data": auth_data, "http_status": auth_status
            })

        # Remove Content-Type manual para que requests defina multipart/form-data
        session.headers.pop("Content-Type", None)
        # Ajusta User-Agent para compatibilidade com a API
        session.headers["User-Agent"] = (
            "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36"
        )

        try:
            multipart = {
                "name": (None, nome_playlist or usuario or "Minha lista"),
                "mac": (None, mac),
                "url": (None, url_final),
                "is_protected": (None, "true" if proteger else "false"),
                "pin": (None, pin if proteger else ""),
                "confirm_pin": (None, pin if proteger else ""),
            }

            response = session.post(
                f"{self.BASE_URL}/playlist_with_mac",
                files=multipart,
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            if not isinstance(data, dict):
                data = {"raw_response": str(data or "")}

            sucesso = (
                response.status_code in (200, 201)
                and not data.get("error")
            )
            if not sucesso:
                mensagem_erro = self._mensagem(data, f"Falha ao cadastrar no {self.nome}.")
                return self._sanitizar_resultado({
                    "success": False, "confirmed": False,
                    "message": mensagem_erro,
                    "status": "erro",
                    "remote_id": "",
                    "data": {"modo_envio": "url", "resposta": data},
                    "http_status": response.status_code
                })

            # Extrai ID remoto do campo 'message' > 'id'
            conteudo = data.get("message", {})
            if not isinstance(conteudo, dict):
                conteudo = {}
            remote_id = str(conteudo.get("id", "") or "").strip()

            # Se o ID não veio na resposta (raro), consulta /device
            if not remote_id:
                time.sleep(1.5)
                playlists, _, _ = self._listar_playlists(session)
                candidatas = [p for p in playlists if isinstance(p, dict) and p.get("added_by_web")]
                if candidatas:
                    remote_id = str(candidatas[-1].get("id", "") or "").strip()

            confirmado = bool(remote_id)
            mensagem = (
                f"Playlist cadastrada e identificada no {self.nome} por URL."
                if confirmado else
                f"Playlist enviada ao {self.nome}, mas o ID remoto não foi localizado."
            )
            status_final = "ativo" if confirmado else "confirmacao_pendente"

            # Sanitiza resposta antes de retornar
            resposta_sanitizada = data.copy()
            if isinstance(resposta_sanitizada.get("message"), dict):
                msg = resposta_sanitizada["message"].copy()
                if "url" in msg:
                    msg["url"] = "***"
                if "pin" in msg:
                    msg["pin"] = "***"
                resposta_sanitizada["message"] = msg

            return self._sanitizar_resultado({
                "success": True,
                "confirmed": confirmado,
                "message": mensagem,
                "status": status_final,
                "remote_id": remote_id,
                "data": {"modo_envio": "url", "cadastro": resposta_sanitizada},
                "http_status": response.status_code
            })

        except requests.Timeout:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"O {self.nome} demorou demais para responder. Verifique o DNS/URL e a conectividade.",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })
        except requests.RequestException as erro:
            resp = getattr(erro, "response", None)
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {},
                "http_status": getattr(resp, "status_code", None)
            })
        except Exception as erro:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro inesperado ao adicionar playlist no {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })


    def _adicionar_por_codigo(self, *, nome_playlist, usuario, senha, codigo, proteger, pin):
        import time

        mac = self._mac(getattr(self.integracao, "mac_address", ""))
        key = str(getattr(self.integracao, "device_key", "") or "").strip()
        pin = str(pin or "").strip()
        proteger = bool(proteger)

        # Validações
        faltantes = []
        if not mac: faltantes.append("MAC")
        if not key: faltantes.append("Device Key")
        if not codigo: faltantes.append("código do servidor")
        if not usuario: faltantes.append("usuário IPTV")
        if not senha: faltantes.append("senha IPTV")
        if proteger and not pin: faltantes.append("PIN")
        if faltantes:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Preencha: {', '.join(faltantes)}.",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })

        session = self._session()
        try:
            token, auth_data, auth_status = self._autenticar(session)
            if not token:
                return self._sanitizar_resultado({
                    "success": False, "confirmed": False,
                    "message": self._mensagem(auth_data, "MAC ou Device Key inválidos."),
                    "status": "erro", "remote_id": "",
                    "data": auth_data, "http_status": auth_status
                })

            # Verifica duplicata
            playlists_antes, _, _ = self._listar_playlists(session)
            ids_antes = {self._extrair_id(p) for p in playlists_antes if self._extrair_id(p)}
            usuario_norm = self._normalizar(usuario)
            nome_norm = self._normalizar(nome_playlist)
            codigo_norm = self._normalizar(codigo)
            valores_esperados = {usuario_norm, nome_norm, codigo_norm}

            for playlist in playlists_antes:
                pid = self._extrair_id(playlist)
                if not pid:
                    continue
                if self._match_mac(playlist, mac) or (self._campos_para_match(playlist) & valores_esperados):
                    return self._sanitizar_resultado({
                        "success": True, "confirmed": True,
                        "message": f"Playlist já está cadastrada no {self.nome}. ID remoto: {pid}.",
                        "status": "ativo", "remote_id": pid,
                        "data": {"modo_envio": "codigo", "playlist_existente": playlist},
                        "http_status": 200
                    })

            # Monta payload (sem PIN se não protegido)
            payload = {
                "mac": mac,
                "code": codigo,
                "username": usuario,
                "password": senha,
                "type": "admin_server",
            }
            if proteger:
                payload["is_protected"] = True
                payload["pin"] = pin
                payload["confirm_pin"] = pin
            else:
                payload["is_protected"] = False

            # Remove Content-Type manual para que requests defina application/json (padrão)
            session.headers.pop("Content-Type", None)
            # Ajusta User-Agent
            session.headers["User-Agent"] = (
                "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36"
            )

            resp = session.post(
                f"{self.BASE_URL}/playlist/code",
                json=payload,
                timeout=self.TIMEOUT,
            )
            data = self._json(resp)
            sucesso = resp.status_code in (200, 201) and not data.get("error") and not data.get("erro")
            if not sucesso:
                return self._sanitizar_resultado({
                    "success": False, "confirmed": False,
                    "message": self._mensagem(data, f"Falha ao cadastrar no {self.nome}."),
                    "status": "erro", "remote_id": "",
                    "data": {"modo_envio": "codigo", "cadastro": data, "playlists_antes": playlists_antes},
                    "http_status": resp.status_code
                })

            remote_id = self._extrair_id(data)
            if not remote_id:
                for chave in ("data", "playlist", "result", "server"):
                    conteudo = data.get(chave)
                    if isinstance(conteudo, dict):
                        remote_id = self._extrair_id(conteudo)
                        if remote_id:
                            break

            playlists_depois = []
            if not remote_id:
                intervalos = (0.5, 0.8, 1.2, 1.8, 2.5, 3.0)
                for intervalo in intervalos:
                    time.sleep(intervalo)
                    playlists_depois, _, _ = self._listar_playlists(session)
                    for playlist in playlists_depois:
                        pid = self._extrair_id(playlist)
                        if pid and pid not in ids_antes:
                            if self._match_mac(playlist, mac) or (self._campos_para_match(playlist) & valores_esperados):
                                remote_id = pid
                                break
                    if remote_id:
                        break

            confirmado = bool(remote_id)
            mensagem = (f"Playlist cadastrada e identificada no {self.nome}. ID remoto: {remote_id}."
                        if confirmado else
                        f"Playlist enviada ao {self.nome}, mas o ID remoto ainda não foi localizado.")
            return self._sanitizar_resultado({
                "success": True,
                "confirmed": confirmado,
                "message": mensagem,
                "status": "ativo" if confirmado else "confirmacao_pendente",
                "remote_id": remote_id,
                "data": {
                    "modo_envio": "codigo",
                    "cadastro": data,
                    "playlists_antes": playlists_antes,
                    "playlists": playlists_depois,
                },
                "http_status": resp.status_code,
            })

        except requests.Timeout:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"O {self.nome} demorou demais para responder.",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })
        except requests.RequestException as erro:
            response_erro = getattr(erro, "response", None)
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {},
                "http_status": getattr(response_erro, "status_code", None)
            })
        except Exception as erro:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro inesperado ao cadastrar a playlist no {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })



    def excluir_playlist(self, remote_id="", pin="", protegida=False, **kwargs):
        remote_id = str(remote_id or "").strip()
        pin = str(pin or "").strip()

        if not remote_id.isdigit():
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "ID remoto inválido.", "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })

        # Só exige PIN se a playlist for protegida E o PIN estiver vazio
        if protegida and not pin:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": "Informe o PIN usado na playlist.",
                "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None
            })

        # Autentica
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
            # Validação do PIN (apenas se protegida)
            if protegida:
                validou, response_validacao, data_validacao = self._validar_exclusao(
                    remote_id, pin, session
                )
                if not validou:
                    return self._sanitizar_resultado({
                        "success": False, "confirmed": False,
                        "message": self._mensagem(data_validacao, "PIN incorreto ou playlist não encontrada."),
                        "status": "erro", "remote_id": remote_id,
                        "data": {"validacao": data_validacao},
                        "http_status": getattr(response_validacao, "status_code", None)
                    })
            else:
                data_validacao = {}

            # Monta payload
            payload = {"id": int(remote_id)}
            if pin:                         # envia PIN apenas se houver (playlists protegidas)
                payload["pin"] = pin

            # Endpoint correto (grafia original "palylist")
            response = session.delete(
                f"{self.BASE_URL}/palylist_from_web",
                json=payload,
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            if not isinstance(data, dict):
                data = {"raw_response": str(data or "")}

            sucesso_exclusao = (
                response.status_code in (200, 201, 204)
                and not data.get("error")
                and not data.get("erro")
            )
            mensagem = (f"Playlist excluída com sucesso no {self.nome}."
                        if sucesso_exclusao else self._mensagem(data, "O aplicativo não confirmou a exclusão."))
            status_final = "excluido" if sucesso_exclusao else "erro"

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

    def adicionar_playlist(self, nome_playlist="", usuario="", senha="", dns="", url_playlist="",
                        codigo="", proteger=False, pin="", modo_envio="", **kwargs):
        modo = str(modo_envio or "").strip().lower()
        if modo not in self.modos_envio:
            modo = "url" if (url_playlist or dns) else "codigo"
        try:
            if modo == "codigo":
                return self._adicionar_por_codigo(
                    nome_playlist=nome_playlist, usuario=usuario, senha=senha,
                    codigo=codigo, proteger=proteger, pin=pin
                )
            else:
                return self._adicionar_por_url(
                    nome_playlist=nome_playlist, usuario=usuario, senha=senha,
                    dns=dns, url_playlist=url_playlist, proteger=proteger, pin=pin
                )
        except requests.Timeout:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"O {self.nome} demorou demais para responder.",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })
        except requests.RequestException as erro:
            response_erro = getattr(erro, "response", None)
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {},
                "http_status": getattr(response_erro, "status_code", None)
            })
        except Exception as erro:
            return self._sanitizar_resultado({
                "success": False, "confirmed": False,
                "message": f"Erro inesperado ao adicionar playlist no {self.nome}: {erro}",
                "status": "erro", "remote_id": "", "data": {}, "http_status": None
            })

        
    @staticmethod
    def _bool_remoto(valor):
        if isinstance(valor, bool):
            return valor
        return str(valor or "").strip().lower() in {
            "1", "true", "yes", "sim", "on"
        }

    def _normalizar_playlist_remota(self, item):
        if not isinstance(item, dict):
            return None

        remote_id = self._extrair_id(item)
        nome = str(
            item.get("name")
            or item.get("title")
            or item.get("playlist_name")
            or item.get("playlistName")
            or f"Playlist {remote_id or ''}"
        ).strip()

        protegida = self._bool_remoto(
            item.get("is_protected", item.get("protected", False))
        )

        return {
            "remote_id": remote_id,
            "nome": nome or "Minha lista",
            "protegida": protegida,
            "url": str(item.get("url") or item.get("playlist_url") or "").strip(),
            "usuario": str(item.get("username") or item.get("user") or "").strip(),
            "codigo": str(item.get("code") or item.get("server_code") or "").strip(),
            "raw": self._sanitizar_resultado(item),
        }

    def listar_playlists(self, **kwargs):
        session = self._session()

        try:
            token, auth_data, auth_status = self._autenticar(session)

            if not token:
                return self._sanitizar_resultado({
                    "success": False,
                    "confirmed": False,
                    "message": self._mensagem(
                        auth_data,
                        "MAC ou Device Key inválidos.",
                    ),
                    "status": "erro",
                    "playlists": [],
                    "data": auth_data,
                    "http_status": auth_status,
                })

            playlists, data, http_status = self._listar_playlists(
                session
            )

            if http_status != 200:
                return self._sanitizar_resultado({
                    "success": False,
                    "confirmed": False,
                    "message": self._mensagem(
                        data,
                        f"Não foi possível listar as playlists do {self.nome}.",
                    ),
                    "status": "erro",
                    "playlists": [],
                    "data": data,
                    "http_status": http_status,
                })

            playlists_normalizadas = []

            for item in playlists:
                if not isinstance(item, dict):
                    continue

                remote_id = str(
                    self._extrair_id(item) or ""
                ).strip()

                if not remote_id:
                    continue

                nome = str(
                    item.get("name")
                    or item.get("nome")
                    or item.get("title")
                    or item.get("playlist_name")
                    or item.get("username")
                    or f"Playlist {remote_id}"
                ).strip()

                url = str(
                    item.get("url")
                    or item.get("playlist_url")
                    or item.get("url_playlist")
                    or item.get("m3u_url")
                    or ""
                ).strip()

                usuario = str(
                    item.get("username")
                    or item.get("usuario")
                    or item.get("user")
                    or ""
                ).strip()

                senha = str(
                    item.get("password")
                    or item.get("senha")
                    or item.get("pass")
                    or ""
                ).strip()

                dns = str(
                    item.get("dns")
                    or item.get("host")
                    or item.get("server")
                    or item.get("domain")
                    or ""
                ).strip()

                codigo = str(
                    item.get("code")
                    or item.get("codigo")
                    or item.get("server_code")
                    or ""
                ).strip()

                protegida = bool(
                    item.get("is_protected")
                    or item.get("protected")
                    or item.get("protegida")
                )

                playlists_normalizadas.append({
                    "remote_id": remote_id,
                    "nome": nome,
                    "url": url,
                    "url_playlist": url,
                    "usuario": usuario,
                    "username": usuario,
                    "senha": senha,
                    "password": senha,
                    "dns": dns,
                    "codigo": codigo,
                    "code": codigo,
                    "protegida": protegida,
                    "raw": item,
                })

            return self._sanitizar_resultado({
                "success": True,
                "confirmed": True,
                "message": (
                    f"{len(playlists_normalizadas)} "
                    f"playlist(s) encontrada(s) no {self.nome}."
                ),
                "status": "ativo",
                "playlists": playlists_normalizadas,
                "data": {
                    "playlists": playlists_normalizadas,
                    "resposta_api": data,
                },
                "http_status": http_status,
            })

        except requests.Timeout:
            return self._sanitizar_resultado({
                "success": False,
                "confirmed": False,
                "message": (
                    f"O {self.nome} demorou demais para responder."
                ),
                "status": "erro",
                "playlists": [],
                "data": {},
                "http_status": None,
            })

        except requests.RequestException as erro:
            response = getattr(erro, "response", None)

            return self._sanitizar_resultado({
                "success": False,
                "confirmed": False,
                "message": f"Erro ao acessar {self.nome}: {erro}",
                "status": "erro",
                "playlists": [],
                "data": {},
                "http_status": getattr(
                    response,
                    "status_code",
                    None,
                ),
            })

        except Exception as erro:
            return self._sanitizar_resultado({
                "success": False,
                "confirmed": False,
                "message": (
                    f"Erro inesperado ao listar playlists "
                    f"do {self.nome}: {erro}"
                ),
                "status": "erro",
                "playlists": [],
                "data": {},
                "http_status": None,
            })