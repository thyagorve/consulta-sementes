import time

import requests

from .base import PlaylistProvider


class FunPlaysProvider(PlaylistProvider):
    """
    Integração com o aplicativo Fun Plays.

    Endpoints confirmados:
    - GET    /validate_mac
    - POST   /login_by_mac
    - GET    /device
    - POST   /playlist/code
    - GET    /protected_playlist
    - DELETE /palylist_from_web

    Observação:
    o endpoint de exclusão usa "palylist" com essa grafia na própria API.
    """
    slug = "fun_plays"
    nome = "Fun Plays"

    campos = {
        "mac_address": {
            "mostrar": True,
            "obrigatorio": True,
            "label": "MAC Address",
            "placeholder": "Ex.: 00:1A:79:00:00:00",
        },
        "device_key": {
            "mostrar": True,
            "obrigatorio": True,
            "label": "Device Key",
            "placeholder": "Digite a Key exibida no Fun Plays",
        },
    }

    BASE_URL = "https://api.funplays.app/api"
    TIMEOUT = 30

    def _headers(self):
        """
        Cabeçalhos utilizados nas requisições para a API Fun Plays.
        """
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://funplays.app",
            "Referer": "https://funplays.app/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        }

    def _normalizar_mac(self, mac):
        """
        Normaliza o MAC para o formato esperado pela Fun Plays.
        """
        return str(mac or "").strip().lower()

    def _json_resposta(self, response):
        """
        Tenta converter a resposta da API para JSON.

        Caso a API devolva texto ou HTML, retorna uma estrutura
        padronizada para evitar quebra do provider.
        """
        try:
            return response.json()

        except ValueError:
            return {
                "error": True,
                "message": response.text[:500],
                "status": response.status_code,
            }

    def _extrair_mensagem(self, data, mensagem_padrao):
        """
        Extrai uma mensagem legível da resposta da API.
        """
        if not isinstance(data, dict):
            return mensagem_padrao

        mensagem = data.get("message")

        if isinstance(mensagem, dict):
            return (
                mensagem.get("message")
                or mensagem.get("error")
                or mensagem.get("detail")
                or str(mensagem)
            )

        if isinstance(mensagem, list):
            return ", ".join(str(item) for item in mensagem)

        if mensagem:
            return str(mensagem)

        return (
            data.get("detail")
            or data.get("error_message")
            or mensagem_padrao
        )

    # ==========================================================
    # MÉTODOS OBRIGATÓRIOS DA CLASSE ABSTRATA
    # ==========================================================

    def iniciar_autenticacao(self, *args, **kwargs):
        """
        Cumpre o contrato da classe base.

        A Fun Plays não exige uma autenticação separada antes da
        pesquisa do dispositivo. A validação principal ocorre pelo
        MAC Address no endpoint /validate_mac.
        """
        return {
            "success": True,
            "confirmed": True,
            "message": (
                "A Fun Plays não exige autenticação antecipada. "
                "O dispositivo será validado pelo MAC Address."
            ),
            "status": "configurado",
            "requires_captcha": False,
            "data": {},
        }

    def _criar_sessao(self):
        session = requests.Session()
        session.headers.update(self._headers())
        return session

    def _obter_device_key(self):
        return str(
            getattr(self.integracao, "device_key", "")
            or ""
        ).strip()

    def _autenticar_dispositivo(self, session):
        mac = self._normalizar_mac(
            getattr(self.integracao, "mac_address", "")
        )
        device_key = self._obter_device_key()

        if not mac:
            return {
                "success": False,
                "message": "Informe o MAC do dispositivo Fun Plays.",
                "data": {},
            }

        if not device_key:
            return {
                "success": False,
                "message": (
                    "Informe a Device Key do Fun Plays para localizar "
                    "e excluir playlists."
                ),
                "data": {},
            }

        response = session.post(
            f"{self.BASE_URL}/login_by_mac",
            json={
                "mac": mac,
                "key": device_key,
            },
            timeout=self.TIMEOUT,
        )

        data = self._json_resposta(response)

        if response.status_code != 200:
            return {
                "success": False,
                "message": self._extrair_mensagem(
                    data,
                    "Não foi possível autenticar no Fun Plays.",
                ),
                "data": data,
                "http_status": response.status_code,
            }

        if not isinstance(data, dict) or data.get("error") is True:
            return {
                "success": False,
                "message": self._extrair_mensagem(
                    data,
                    "MAC ou Device Key inválidos.",
                ),
                "data": data,
                "http_status": response.status_code,
            }

        token = data.get("message")

        if isinstance(token, dict):
            token = (
                token.get("token")
                or token.get("access_token")
                or token.get("jwt")
                or ""
            )

        token = str(token or "").strip()

        if not token:
            return {
                "success": False,
                "message": (
                    "O Fun Plays autenticou o dispositivo, mas não "
                    "retornou o token de acesso."
                ),
                "data": data,
                "http_status": response.status_code,
            }

        # O endpoint /device exige o JWT retornado pelo login.
        # Sem este cabeçalho, a API não entrega as playlists.
        session.headers.update({
            "Authorization": f"Bearer {token}",
        })

        return {
            "success": True,
            "token": token,
            "data": data,
            "http_status": response.status_code,
        }

    def _listar_playlists_remotas(self):
        session = self._criar_sessao()

        autenticacao = self._autenticar_dispositivo(session)

        if not autenticacao.get("success"):
            return {
                "success": False,
                "message": autenticacao.get(
                    "message",
                    "Falha na autenticação.",
                ),
                "playlists": [],
                "data": autenticacao.get("data", {}),
                "http_status": autenticacao.get("http_status"),
            }

        response = session.get(
            f"{self.BASE_URL}/device",
            timeout=self.TIMEOUT,
        )

        data = self._json_resposta(response)

        # Algumas versões da API podem esperar o JWT sem o prefixo
        # Bearer. Se a primeira tentativa for recusada, tenta o formato
        # alternativo antes de declarar falha.
        if response.status_code in (401, 403):
            token = autenticacao.get("token", "")

            if token:
                session.headers.update({
                    "Authorization": token,
                })

                response = session.get(
                    f"{self.BASE_URL}/device",
                    timeout=self.TIMEOUT,
                )
                data = self._json_resposta(response)

        if response.status_code != 200:
            return {
                "success": False,
                "message": self._extrair_mensagem(
                    data,
                    "Não foi possível listar as playlists.",
                ),
                "playlists": [],
                "data": data,
                "http_status": response.status_code,
            }

        if not isinstance(data, dict):
            return {
                "success": False,
                "message": "A Fun Plays retornou uma resposta inválida.",
                "playlists": [],
                "data": data,
                "http_status": response.status_code,
            }

        dispositivo = data.get("message")

        if not isinstance(dispositivo, dict):
            dispositivo = {}

        playlists = dispositivo.get("playlists")

        if not isinstance(playlists, list):
            playlists = []

        return {
            "success": True,
            "message": "Playlists encontradas.",
            "playlists": playlists,
            "data": data,
            "token": autenticacao.get("token", ""),
            "http_status": response.status_code,
        }

    def _localizar_playlist_remota(
        self,
        nome_playlist="",
        usuario="",
    ):
        resultado = self._listar_playlists_remotas()

        if not resultado.get("success"):
            return {
                "success": False,
                "message": resultado.get(
                    "message",
                    "Não foi possível localizar a playlist.",
                ),
                "playlist": None,
                "data": resultado.get("data", {}),
                "http_status": resultado.get("http_status"),
            }

        playlists = resultado.get("playlists", [])
        nome_playlist = str(nome_playlist or "").strip().lower()
        usuario = str(usuario or "").strip().lower()

        candidatos = []

        for playlist in playlists:
            if not isinstance(playlist, dict):
                continue

            nome_remoto = str(
                playlist.get("name") or ""
            ).strip().lower()

            if usuario and nome_remoto == usuario:
                candidatos.append(playlist)
                continue

            if nome_playlist and nome_remoto == nome_playlist:
                candidatos.append(playlist)

        if not candidatos:
            return {
                "success": False,
                "message": (
                    "A playlist não foi localizada no dispositivo. "
                    "Confira o usuário IPTV e o nome da lista."
                ),
                "playlist": None,
                "data": {
                    "playlists": playlists,
                },
                "http_status": resultado.get("http_status"),
            }

        def chave_ordenacao(item):
            try:
                return int(item.get("id") or 0)
            except (TypeError, ValueError):
                return 0

        candidatos.sort(
            key=chave_ordenacao,
            reverse=True,
        )

        return {
            "success": True,
            "message": "Playlist localizada.",
            "playlist": candidatos[0],
            "data": {
                "playlists": playlists,
            },
            "http_status": resultado.get("http_status"),
        }

    def _procurar_playlist_id(self, valor):
        if isinstance(valor, dict):
            for chave in (
                "playlist_id",
                "playlistId",
                "id",
            ):
                encontrado = valor.get(chave)

                if encontrado not in (None, "", 0, "0"):
                    try:
                        return str(int(encontrado))
                    except (TypeError, ValueError):
                        pass

            for item in valor.values():
                resultado = self._procurar_playlist_id(item)

                if resultado:
                    return resultado

        elif isinstance(valor, list):
            for item in valor:
                resultado = self._procurar_playlist_id(item)

                if resultado:
                    return resultado

        return ""

    def listar_playlists(self, pin="", **kwargs):
        """
        Lista as playlists cadastradas no Fun Plays.

        Regras:
        - PIN vazio ou igual a "0": lista normalmente, sem liberar dados protegidos.
        - PIN informado: tenta liberar cada playlist protegida.
        - PIN incorreto em uma playlist: ignora somente aquela e continua.
        - Playlists não protegidas continuam sendo retornadas normalmente.
        """

        resultado = self._listar_playlists_remotas()

        if not resultado.get("success"):
            return {
                "success": False,
                "confirmed": False,
                "message": resultado.get(
                    "message",
                    "Não foi possível listar as playlists.",
                ),
                "status": "erro",
                "playlists": [],
                "data": resultado.get("data", {}),
                "http_status": resultado.get("http_status"),
            }

        pin = str(pin or "").strip()

        if pin == "0":
            pin = ""

        token = str(resultado.get("token") or "").strip()

        session = self._criar_sessao()

        # Tenta usar o token retornado pela autenticação.
        if token:
            if token.lower().startswith("bearer "):
                session.headers.update({
                    "Authorization": token,
                })
            else:
                session.headers.update({
                    "Authorization": f"Bearer {token}",
                })

        playlists_normalizadas = []
        erros_pin = []
        playlists_ignoradas = []

        playlists_remotas = resultado.get("playlists", [])

        if not isinstance(playlists_remotas, list):
            playlists_remotas = []

        for item in playlists_remotas:
            if not isinstance(item, dict):
                continue

            raw = dict(item)

            remote_id = (
                raw.get("id")
                or raw.get("playlist_id")
                or raw.get("remote_id")
            )

            nome_playlist = str(
                raw.get("name")
                or raw.get("nome")
                or raw.get("playlist_name")
                or remote_id
                or "Minha lista"
            ).strip()

            protegida = bool(
                raw.get(
                    "is_protected",
                    raw.get(
                        "protected",
                        raw.get("protegida", False),
                    ),
                )
            )

            # Caso a API retorne 1, "1", "true" ou "yes".
            valor_protegida = raw.get(
                "is_protected",
                raw.get(
                    "protected",
                    raw.get("protegida", False),
                ),
            )

            if isinstance(valor_protegida, str):
                protegida = valor_protegida.strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "sim",
                }

            elif isinstance(valor_protegida, int):
                protegida = valor_protegida == 1

            # Consulta os dados protegidos somente quando um PIN foi informado.
            if pin and protegida and remote_id:
                try:
                    response = session.get(
                        f"{self.BASE_URL}/protected_playlist",
                        params={
                            "id": remote_id,
                            "pin": pin,
                        },
                        timeout=self.TIMEOUT,
                    )

                    dados_protegidos = self._json_resposta(response)

                    # Algumas versões da API podem esperar o token sem "Bearer".
                    if response.status_code in (401, 403) and token:
                        session.headers.update({
                            "Authorization": token,
                        })

                        response = session.get(
                            f"{self.BASE_URL}/protected_playlist",
                            params={
                                "id": remote_id,
                                "pin": pin,
                            },
                            timeout=self.TIMEOUT,
                        )

                        dados_protegidos = self._json_resposta(response)

                    if response.status_code != 200:
                        mensagem_erro = self._extrair_mensagem(
                            dados_protegidos,
                            f"Erro HTTP {response.status_code}.",
                        )

                        erro_texto = (
                            f"{nome_playlist}: {mensagem_erro}"
                        )

                        erros_pin.append(erro_texto)

                        playlists_ignoradas.append({
                            "remote_id": str(remote_id or ""),
                            "nome": nome_playlist,
                            "motivo": mensagem_erro,
                        })

                        # PIN não bateu nessa playlist.
                        # Ignora somente ela e segue para a próxima.
                        continue

                    if (
                        isinstance(dados_protegidos, dict)
                        and dados_protegidos.get("error") is True
                    ):
                        mensagem_erro = self._extrair_mensagem(
                            dados_protegidos,
                            "PIN incorreto.",
                        )

                        erro_texto = (
                            f"{nome_playlist}: {mensagem_erro}"
                        )

                        erros_pin.append(erro_texto)

                        playlists_ignoradas.append({
                            "remote_id": str(remote_id or ""),
                            "nome": nome_playlist,
                            "motivo": mensagem_erro,
                        })

                        continue

                    dados_liberados = {}

                    if isinstance(dados_protegidos, dict):
                        dados_liberados = (
                            dados_protegidos.get("message")
                            or dados_protegidos.get("data")
                            or dados_protegidos.get("playlist")
                            or dados_protegidos
                        )

                    if isinstance(dados_liberados, list):
                        if dados_liberados:
                            primeiro_item = dados_liberados[0]

                            if isinstance(primeiro_item, dict):
                                dados_liberados = primeiro_item
                            else:
                                dados_liberados = {}

                        else:
                            dados_liberados = {}

                    if isinstance(dados_liberados, dict):
                        raw.update(dados_liberados)

                except requests.Timeout:
                    mensagem_erro = "Tempo limite excedido."

                    erros_pin.append(
                        f"{nome_playlist}: {mensagem_erro}"
                    )

                    playlists_ignoradas.append({
                        "remote_id": str(remote_id or ""),
                        "nome": nome_playlist,
                        "motivo": mensagem_erro,
                    })

                    continue

                except requests.RequestException as error:
                    mensagem_erro = str(error)

                    erros_pin.append(
                        f"{nome_playlist}: {mensagem_erro}"
                    )

                    playlists_ignoradas.append({
                        "remote_id": str(remote_id or ""),
                        "nome": nome_playlist,
                        "motivo": mensagem_erro,
                    })

                    continue

                except Exception as error:
                    mensagem_erro = str(error)

                    erros_pin.append(
                        f"{nome_playlist}: {mensagem_erro}"
                    )

                    playlists_ignoradas.append({
                        "remote_id": str(remote_id or ""),
                        "nome": nome_playlist,
                        "motivo": mensagem_erro,
                    })

                    continue

            url_playlist = str(
                raw.get("url")
                or raw.get("playlist_url")
                or raw.get("url_playlist")
                or raw.get("m3u_url")
                or ""
            ).strip()

            usuario = str(
                raw.get("username")
                or raw.get("user")
                or raw.get("usuario")
                or ""
            ).strip()

            senha = str(
                raw.get("password")
                or raw.get("pass")
                or raw.get("senha")
                or ""
            ).strip()

            dns = str(
                raw.get("dns")
                or raw.get("host")
                or raw.get("server")
                or raw.get("domain")
                or ""
            ).strip()

            codigo = str(
                raw.get("code")
                or raw.get("codigo")
                or raw.get("activation_code")
                or ""
            ).strip()

            nome_final = str(
                raw.get("name")
                or raw.get("nome")
                or raw.get("playlist_name")
                or nome_playlist
                or "Minha lista"
            ).strip()

            playlists_normalizadas.append({
                "remote_id": str(
                    raw.get("id")
                    or raw.get("playlist_id")
                    or raw.get("remote_id")
                    or remote_id
                    or ""
                ),
                "nome": nome_final,
                "protegida": protegida,
                "url": url_playlist,
                "url_playlist": url_playlist,
                "usuario": usuario,
                "username": usuario,
                "senha": senha,
                "password": senha,
                "dns": dns,
                "codigo": codigo,
                "code": codigo,

                # Guarda o PIN somente na playlist que foi liberada.
                "pin": pin if pin and protegida else "",

                "raw": raw,
            })

        quantidade_total = len(playlists_remotas)
        quantidade_carregadas = len(playlists_normalizadas)
        quantidade_ignoradas = len(playlists_ignoradas)

        if pin and quantidade_ignoradas and quantidade_carregadas:
            mensagem = (
                f"{quantidade_carregadas} playlist(s) carregada(s). "
                f"{quantidade_ignoradas} ignorada(s), pois o PIN não "
                "corresponde ou a API recusou o acesso."
            )

        elif pin and quantidade_ignoradas and not quantidade_carregadas:
            mensagem = (
                "Nenhuma playlist foi liberada com o PIN informado. "
                f"{quantidade_ignoradas} playlist(s) ignorada(s)."
            )

        elif pin:
            mensagem = (
                f"{quantidade_carregadas} playlist(s) carregada(s) "
                "com os dados protegidos."
            )

        else:
            mensagem = (
                f"{quantidade_carregadas} playlist(s) carregada(s)."
            )

        return {
            # Mantém success=True mesmo quando algumas playlists forem ignoradas.
            # Assim a view salva as playlists que realmente foram liberadas.
            "success": True,
            "confirmed": True,
            "message": mensagem,
            "status": "configurado",
            "playlists": playlists_normalizadas,
            "data": {
                "playlists": playlists_normalizadas,
                "consulta_protegida": bool(pin),
                "quantidade_total": quantidade_total,
                "quantidade_carregadas": quantidade_carregadas,
                "quantidade_ignoradas": quantidade_ignoradas,
                "playlists_ignoradas": playlists_ignoradas,
                "erros_pin": erros_pin,
            },
            "http_status": resultado.get("http_status") or 200,
        }





    def pesquisar_dispositivo(self, **kwargs):
        """
        Pesquisa os dados do dispositivo e suas playlists.
        """
        return self._listar_playlists_remotas()


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
        **kwargs,
    ):
        """
        Adiciona uma playlist no Fun Plays.
        """
        payload = {
            "name": str(nome_playlist or "").strip(),
            "username": str(usuario or "").strip(),
            "password": str(senha or "").strip(),
            "dns": str(dns or "").strip(),
            "url": str(url_playlist or "").strip(),
            "code": str(codigo or "").strip(),
            "is_protected": bool(proteger),
            "pin": str(pin or "").strip(),
        }

        session = self._criar_sessao()
        autenticacao = self._autenticar_dispositivo(session)

        if not autenticacao.get("success"):
            return {
                "success": False,
                "confirmed": False,
                "message": autenticacao.get(
                    "message",
                    "Não foi possível autenticar no Fun Plays.",
                ),
                "status": "erro",
                "data": autenticacao.get("data", {}),
                "http_status": autenticacao.get("http_status"),
            }

        response = session.post(
            f"{self.BASE_URL}/playlist",
            json=payload,
            timeout=self.TIMEOUT,
        )

        data = self._json_resposta(response)

        if response.status_code not in (200, 201):
            return {
                "success": False,
                "confirmed": False,
                "message": self._extrair_mensagem(
                    data,
                    "Não foi possível adicionar a playlist.",
                ),
                "status": "erro",
                "data": data,
                "http_status": response.status_code,
            }

        return {
            "success": True,
            "confirmed": True,
            "message": "Playlist adicionada com sucesso.",
            "status": "configurado",
            "data": data,
            "http_status": response.status_code,
        }
        # ==========================================================
        # ADICIONAR PLAYLIST
        # ==========================================================

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
            **kwargs,
        ):
            """
            Adiciona uma playlist e tenta identificar o ID remoto criado.

            Quando há Device Key, compara as playlists antes e depois do
            cadastro. Isso evita salvar o ID de uma lista antiga quando o
            mesmo usuário já aparece mais de uma vez no dispositivo.
            """
            mac = self._normalizar_mac(
                getattr(self.integracao, "mac_address", "")
            )

            codigo = str(
                codigo
                or getattr(self.integracao, "codigo", "")
                or ""
            ).strip()

            usuario = str(usuario or "").strip()
            senha = str(senha or "").strip()
            nome_playlist = str(nome_playlist or "").strip()
            pin = str(pin or "").strip()
            proteger = bool(proteger)

            if not mac:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": "Informe o MAC do dispositivo Fun Plays.",
                    "status": "erro",
                    "data": {},
                }

            if not codigo:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        "Informe o código do servidor usado pelo Fun Plays."
                    ),
                    "status": "erro",
                    "data": {},
                }

            if not usuario:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        "O cliente não possui usuário IPTV cadastrado."
                    ),
                    "status": "erro",
                    "data": {},
                }

            if not senha:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        "O cliente não possui senha IPTV cadastrada."
                    ),
                    "status": "erro",
                    "data": {},
                }

            if proteger and not pin:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": "Informe o PIN de proteção.",
                    "status": "erro",
                    "data": {},
                }

            payload = {
                "mac": mac,
                "code": codigo,
                "username": usuario,
                "password": senha,
                "is_protected": proteger,
                "type": "admin_server",
                "pin": pin if proteger else "",
                "confirm_pin": pin if proteger else "",
            }

            try:
                # Captura os IDs existentes antes do cadastro. A consulta só
                # funciona quando a integração possui Device Key válida.
                ids_antes = set()
                listagem_antes = None

                if self._obter_device_key():
                    listagem_antes = self._listar_playlists_remotas()

                    if listagem_antes.get("success"):
                        for playlist in listagem_antes.get("playlists", []):
                            if not isinstance(playlist, dict):
                                continue

                            playlist_id = playlist.get("id")

                            if playlist_id not in (None, "", 0, "0"):
                                ids_antes.add(str(playlist_id))

                response = requests.post(
                    f"{self.BASE_URL}/playlist/code",
                    json=payload,
                    headers=self._headers(),
                    timeout=self.TIMEOUT,
                )

                data = self._json_resposta(response)

                if response.status_code not in (200, 201):
                    return {
                        "success": False,
                        "confirmed": False,
                        "message": self._extrair_mensagem(
                            data,
                            (
                                "O Fun Plays recusou o cadastro da playlist. "
                                f"HTTP {response.status_code}."
                            ),
                        ),
                        "status": "erro",
                        "data": data,
                        "http_status": response.status_code,
                    }

                if not isinstance(data, dict):
                    return {
                        "success": False,
                        "confirmed": False,
                        "message": (
                            "O Fun Plays retornou uma resposta inválida "
                            "ao adicionar a playlist."
                        ),
                        "status": "erro",
                        "data": data,
                        "http_status": response.status_code,
                    }

                erro_api = data.get("error")
                mensagem_api = data.get("message")
                mensagem_normalizada = str(
                    mensagem_api or ""
                ).strip().lower()

                sucesso_por_mensagem = mensagem_normalizada in {
                    "success",
                    "sucesso",
                    "playlist added successfully",
                    "playlist created successfully",
                }

                sucesso_api = (
                    erro_api is False
                    or erro_api in (None, "", 0)
                    or sucesso_por_mensagem
                )

                if not sucesso_api:
                    return {
                        "success": False,
                        "confirmed": False,
                        "message": self._extrair_mensagem(
                            data,
                            "O Fun Plays recusou o cadastro da playlist.",
                        ),
                        "status": "erro",
                        "data": data,
                        "http_status": response.status_code,
                    }

                # Algumas respostas já podem conter o ID diretamente.
                remote_id = self._procurar_playlist_id(data)
                playlist_encontrada = None
                listagem_depois = None

                # Quando o cadastro não devolve o ID, consulta /device e
                # identifica a playlist nova comparando com os IDs anteriores.
                if not remote_id and self._obter_device_key():
                    usuario_normalizado = usuario.lower()
                    nome_normalizado = nome_playlist.lower()

                    for tentativa in range(3):
                        if tentativa:
                            time.sleep(1)

                        listagem_depois = self._listar_playlists_remotas()

                        if not listagem_depois.get("success"):
                            continue

                        candidatos_novos = []
                        candidatos_compativeis = []

                        for playlist in listagem_depois.get("playlists", []):
                            if not isinstance(playlist, dict):
                                continue

                            playlist_id = str(
                                playlist.get("id") or ""
                            ).strip()
                            nome_remoto = str(
                                playlist.get("name") or ""
                            ).strip().lower()

                            if not playlist_id:
                                continue

                            corresponde = (
                                nome_remoto == usuario_normalizado
                                or (
                                    nome_normalizado
                                    and nome_remoto == nome_normalizado
                                )
                            )

                            if not corresponde:
                                continue

                            candidatos_compativeis.append(playlist)

                            if playlist_id not in ids_antes:
                                candidatos_novos.append(playlist)

                        candidatos = (
                            candidatos_novos
                            or candidatos_compativeis
                        )

                        if candidatos:
                            def chave_id(item):
                                try:
                                    return int(item.get("id") or 0)
                                except (TypeError, ValueError):
                                    return 0

                            candidatos.sort(
                                key=chave_id,
                                reverse=True,
                            )
                            playlist_encontrada = candidatos[0]
                            remote_id = str(
                                playlist_encontrada.get("id") or ""
                            ).strip()
                            break

                if remote_id:
                    return {
                        "success": True,
                        "confirmed": True,
                        "message": (
                            "Playlist cadastrada e ID remoto identificado "
                            "com sucesso no Fun Plays."
                        ),
                        "status": "ativo",
                        "remote_id": remote_id,
                        "data": {
                            "resposta_cadastro": data,
                            "playlist_encontrada": playlist_encontrada,
                            "ids_antes": sorted(ids_antes),
                            "listagem_antes": listagem_antes,
                            "listagem_depois": listagem_depois,
                        },
                        "http_status": response.status_code,
                    }

                mensagem = (
                    "Playlist cadastrada, mas o ID remoto não pôde ser "
                    "identificado. Informe uma Device Key válida para que "
                    "o sistema consulte as playlists do dispositivo."
                    if not self._obter_device_key()
                    else (
                        "Playlist cadastrada, mas ela ainda não apareceu "
                        "na listagem remota do dispositivo."
                    )
                )

                return {
                    "success": True,
                    "confirmed": False,
                    "message": mensagem,
                    "status": "confirmacao_pendente",
                    "remote_id": "",
                    "data": {
                        "resposta_cadastro": data,
                        "ids_antes": sorted(ids_antes),
                        "listagem_antes": listagem_antes,
                        "listagem_depois": listagem_depois,
                    },
                    "http_status": response.status_code,
                }

            except requests.Timeout:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": "O Fun Plays demorou demais para responder.",
                    "status": "erro",
                    "data": {},
                }

            except requests.ConnectionError:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        "Não foi possível conectar à API do Fun Plays."
                    ),
                    "status": "erro",
                    "data": {},
                }

            except requests.RequestException as error:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": f"Erro ao acessar o Fun Plays: {error}",
                    "status": "erro",
                    "data": {},
                }

            except Exception as error:
                return {
                    "success": False,
                    "confirmed": False,
                    "message": (
                        "Erro inesperado ao adicionar a playlist: "
                        f"{error}"
                    ),
                    "status": "erro",
                    "data": {},
                }

        # ==========================================================
        # EXCLUIR PLAYLIST
        # ==========================================================

    def excluir_playlist(self, remote_id="", pin="", **kwargs):
        """
        Exclui uma playlist do Fun Plays.

        Fluxo confirmado pelo HAR:
        1. GET  /protected_playlist?id=ID&pin=PIN
        2. DELETE /palylist_from_web  (atenção: grafia "palylist")
        """
        remote_id = str(
            remote_id
            or getattr(self.integracao, "playlist_remote_id", "")
            or ""
        ).strip()

        pin = str(
            pin
            or getattr(self.integracao, "pin_protecao", "")
            or ""
        ).strip()

        if not remote_id:
            cliente = getattr(
                self.integracao,
                "cliente",
                None,
            )

            usuario = ""

            if cliente:
                usuario = str(
                    getattr(
                        cliente,
                        "login_externo",
                        "",
                    )
                    or ""
                ).strip()

            localizacao = self._localizar_playlist_remota(
                nome_playlist=getattr(
                    self.integracao,
                    "nome_playlist",
                    "",
                ),
                usuario=usuario,
            )

            if not localizacao.get("success"):
                return {
                    "success": False,
                    "confirmed": False,
                    "message": localizacao.get(
                        "message",
                        "ID remoto da playlist não encontrado.",
                    ),
                    "status": "erro",
                    "data": localizacao.get("data", {}),
                    "http_status": localizacao.get("http_status"),
                }

            playlist_remota = (
                localizacao.get("playlist") or {}
            )

            remote_id = str(
                playlist_remota.get("id") or ""
            ).strip()

        if not remote_id:
            return {
                "success": False,
                "confirmed": False,
                "message": "ID remoto da playlist não encontrado.",
                "status": "erro",
                "data": {},
            }

        try:
            remote_id_int = int(remote_id)
        except (TypeError, ValueError):
            return {
                "success": False,
                "confirmed": False,
                "message": f"ID remoto inválido: {remote_id}",
                "status": "erro",
                "data": {"remote_id": remote_id},
            }

        if not pin:
            return {
                "success": False,
                "confirmed": False,
                "message": "Informe o PIN de proteção da playlist.",
                "status": "erro",
                "data": {"remote_id": remote_id_int},
            }

        try:
            # 1. Validar PIN e confirmar playlist
            validar_response = requests.get(
                f"{self.BASE_URL}/protected_playlist",
                params={"id": remote_id_int, "pin": pin},
                headers=self._headers(),
                timeout=self.TIMEOUT,
            )
            validar_data = self._json_resposta(validar_response)

            if validar_response.status_code != 200 or validar_data.get("error"):
                msg = self._extrair_mensagem(validar_data, "PIN incorreto ou playlist não encontrada.")
                if "wrong pin" in str(msg).lower():
                    msg = "PIN informado está incorreto."
                return {
                    "success": False, "confirmed": False,
                    "message": msg, "status": "erro",
                    "data": validar_data,
                    "http_status": validar_response.status_code,
                }

            playlist_validada = validar_data.get("message", {})
            if isinstance(playlist_validada, dict):
                id_validado = playlist_validada.get("id")
                if id_validado and int(id_validado) != remote_id_int:
                    return {
                        "success": False, "confirmed": False,
                        "message": "Playlist validada não corresponde ao ID.",
                        "status": "erro", "data": validar_data,
                    }

            # 2. Excluir playlist (endpoint com grafia errada)
            excluir_response = requests.delete(
                f"{self.BASE_URL}/palylist_from_web",
                json={"id": remote_id_int, "pin": pin},
                headers=self._headers(),
                timeout=self.TIMEOUT,
            )
            excluir_data = self._json_resposta(excluir_response)

            sucesso = (
                excluir_response.status_code == 200
                and not excluir_data.get("error")
                and str(excluir_data.get("message", "")).strip().lower() in ("deleted", "success", "sucesso")
            )

            if not sucesso:
                msg = self._extrair_mensagem(excluir_data, "Falha ao excluir playlist.")
                if "wrong pin" in str(msg).lower():
                    msg = "PIN informado está incorreto."
                return {
                    "success": False, "confirmed": False,
                    "message": msg, "status": "erro",
                    "data": excluir_data,
                    "http_status": excluir_response.status_code,
                }

            return {
                "success": True, "confirmed": True,
                "message": "Playlist excluída com sucesso no Fun Plays.",
                "status": "excluido",
                "remote_id": str(remote_id_int),
                "data": {"validacao": validar_data, "exclusao": excluir_data},
                "http_status": excluir_response.status_code,
            }

        except requests.Timeout:
            return {"success": False, "confirmed": False, "message": "Timeout ao excluir playlist.", "status": "erro", "data": {}}
        except requests.ConnectionError:
            return {"success": False, "confirmed": False, "message": "Erro de conexão ao excluir playlist.", "status": "erro", "data": {}}
        except requests.RequestException as e:
            return {"success": False, "confirmed": False, "message": f"Erro ao acessar Fun Plays: {e}", "status": "erro", "data": {}}
        except Exception as e:
            return {"success": False, "confirmed": False, "message": f"Erro inesperado: {e}", "status": "erro", "data": {}}