import html
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone

from .base import PlaylistProvider


class IboBaseProvider(PlaylistProvider):
    BASE_URL = ""
    TIMEOUT = 30

    CAPTCHA_PATH = "/frontend/captcha/generate"
    LOGIN_PATH = "/frontend/device/login"
    DEVICE_PATH = "/frontend/device"
    PLAYLISTS_PATH = "/frontend/device/playlists"
    SAVE_PATH = "/frontend/device/savePlaylist"
    DELETE_PATH = "/frontend/device/deletePlayListUrl/{remote_id}"
    CHECK_PIN_PATH = "/frontend/device/checkPlaylistPinCode/{remote_id}/{pin}"
    PLAYLISTS_WITH_PIN_PATH = "/frontend/device/playlists/{pin}"

    suporta_edicao_remota = True
    exige_captcha = True

    campos = {
        "mac_address": {"mostrar": True, "obrigatorio": True, "label": "MAC Address"},
        "device_key": {"mostrar": True, "obrigatorio": True, "label": "Device Key"},
        "codigo": {"mostrar": False, "obrigatorio": False, "label": "Código do servidor"},
        "dns": {"mostrar": False, "obrigatorio": False, "label": "DNS do servidor"},
        "url_template": {"mostrar": True, "obrigatorio": False, "label": "URL completa da playlist"},
    }
    modos_envio = {"url": "URL M3U"}

    def _url(self, path):
        return f"{self.BASE_URL.rstrip('/')}/{str(path).lstrip('/')}"

    def _session(self):
        session = requests.Session()
        session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": self.BASE_URL.rstrip("/"),
            "Referer": f"{self.BASE_URL.rstrip('/')}/dashboard",
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 15; Pixel 9) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Mobile Safari/537.36"
            ),
        })
        token = self._token_salvo()
        if token:
            session.headers["Authorization"] = f"Bearer {token}"
        return session

    @staticmethod
    def _json(response):
        try:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        except ValueError:
            return {"raw": response.text}

    @staticmethod
    def _mensagem(data, padrao):
        if not isinstance(data, dict):
            return padrao
        for chave in ("message", "msg", "error", "erro"):
            valor = data.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
        return padrao

    def _dados_remotos(self):
        dados = getattr(self.integracao, "dados_remotos", {})
        return dict(dados) if isinstance(dados, dict) else {}

    def _token_salvo(self):
        dados = self._dados_remotos().get("ibo_auth", {})
        if not isinstance(dados, dict):
            return ""
        expiracao = dados.get("expira_em")
        if expiracao:
            try:
                if timezone.now() >= timezone.datetime.fromisoformat(expiracao):
                    return ""
            except Exception:
                pass
        return str(dados.get("token") or "").strip()

    def _salvar_auth(self, token, device=None):
        dados = self._dados_remotos()
        dados["ibo_auth"] = {
            "token": str(token or "").strip(),
            "expira_em": (timezone.now() + timedelta(hours=23)).isoformat(),
            "device": device if isinstance(device, dict) else {},
        }
        self.integracao.dados_remotos = dados
        self.integracao.save(update_fields=["dados_remotos", "atualizado_em"])

    def _limpar_auth(self):
        dados = self._dados_remotos()
        dados.pop("ibo_auth", None)
        self.integracao.dados_remotos = dados
        self.integracao.save(update_fields=["dados_remotos", "atualizado_em"])

    def gerar_captcha(self):
        try:
            response = requests.get(
                self._url(self.CAPTCHA_PATH),
                headers={"Accept": "application/json, text/plain, */*"},
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            svg = str(data.get("svg") or "").strip()
            token = str(data.get("token") or "").strip()
            sucesso = response.status_code == 200 and bool(svg and token)
            return {
                "success": sucesso,
                "message": "CAPTCHA gerado." if sucesso else self._mensagem(data, "Não foi possível gerar o CAPTCHA."),
                "svg": svg,
                "token": token,
                "http_status": response.status_code,
                "data": data,
            }
        except requests.RequestException as erro:
            return {"success": False, "message": f"Erro ao gerar CAPTCHA: {erro}", "svg": "", "token": "", "http_status": None, "data": {}}

    def autenticar(self, captcha="", captcha_token=""):
        mac = str(getattr(self.integracao, "mac_address", "") or "").strip().lower()
        key = str(getattr(self.integracao, "device_key", "") or "").strip()
        captcha = str(captcha or "").strip().upper()
        captcha_token = str(captcha_token or "").strip()

        faltando = []
        if not mac:
            faltando.append("MAC")
        if not key:
            faltando.append("Device Key")
        if not captcha:
            faltando.append("CAPTCHA")
        if not captcha_token:
            faltando.append("token do CAPTCHA")
        if faltando:
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": "Informe: " + ", ".join(faltando) + ".", "status": "aguardando_captcha", "data": {}, "http_status": 400}

        session = self._session()
        try:
            response = session.post(
                self._url(self.LOGIN_PATH),
                json={"mac_address": mac, "device_key": key, "captcha": captcha, "token": captcha_token},
                timeout=self.TIMEOUT,
            )
            data = self._json(response)
            sucesso = response.status_code == 200 and str(data.get("status") or "").lower() == "success"
            token = str(data.get("token") or "").strip()
            device = data.get("device") if isinstance(data.get("device"), dict) else {}
            if sucesso and token:
                self._salvar_auth(token, device)
            return {
                "success": bool(sucesso and token),
                "confirmed": bool(sucesso and token),
                "requires_captcha": not bool(sucesso and token),
                "message": "IBO autenticado com sucesso." if sucesso and token else self._mensagem(data, "CAPTCHA, MAC ou Device Key inválidos."),
                "status": "configurado" if sucesso and token else "aguardando_captcha",
                "data": {"device": device},
                "http_status": response.status_code,
            }
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": f"Erro ao autenticar no {self.nome}: {erro}", "status": "erro", "data": {}, "http_status": None}

    def _request(self, method, path, **kwargs):
        session = self._session()
        response = session.request(method, self._url(path), timeout=self.TIMEOUT, **kwargs)
        data = self._json(response)
        if response.status_code in (401, 403):
            self._limpar_auth()
        return response, data

    @staticmethod
    def _normalizar_playlist(item):
        if not isinstance(item, dict):
            return None
        remote_id = str(item.get("_id") or item.get("id") or "").strip()
        if not remote_id:
            return None
        return {
            "remote_id": remote_id,
            "nome": str(item.get("playlist_name") or item.get("name") or "Minha lista").strip(),
            "url": str(item.get("url") or item.get("playlist_url") or "").strip(),
            "url_playlist": str(item.get("url") or item.get("playlist_url") or "").strip(),
            "usuario": str(item.get("username") or "").strip(),
            "senha": str(item.get("password") or "").strip(),
            "dns": "",
            "codigo": "",
            "protegida": bool(item.get("is_protected")),
            "pin": str(item.get("pin") or "").strip(),
            "raw": item,
        }

    def pesquisar_dispositivo(self, captcha="", captcha_token="", **kwargs):
        if captcha or captcha_token:
            return self.autenticar(captcha=captcha, captcha_token=captcha_token)
        if not self._token_salvo():
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": "Autentique o IBO com o CAPTCHA antes de continuar.", "status": "aguardando_captcha", "data": {}, "http_status": 401}
        try:
            response, data = self._request("GET", self.DEVICE_PATH)
            sucesso = response.status_code in (200, 304) and str(data.get("status") or "").lower() in {"success", "sucess"}
            return {"success": sucesso, "confirmed": sucesso, "message": "Dispositivo IBO encontrado." if sucesso else self._mensagem(data, "Não foi possível consultar o dispositivo IBO."), "status": "configurado" if sucesso else "erro", "data": data, "http_status": response.status_code}
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "message": f"Erro ao consultar o IBO: {erro}", "status": "erro", "data": {}, "http_status": None}

    def listar_playlists(self, pin="", **kwargs):
        if not self._token_salvo():
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": "Autentique o IBO com o CAPTCHA antes de puxar as listas.", "status": "aguardando_captcha", "playlists": [], "data": {}, "http_status": 401}
        path = self.PLAYLISTS_WITH_PIN_PATH.format(pin=pin) if str(pin or "").strip() else self.PLAYLISTS_PATH
        try:
            response, data = self._request("GET", path)
            sucesso = response.status_code in (200, 304) and str(data.get("status") or "").lower() in {"success", "sucess"}
            items = data.get("playlists") if isinstance(data.get("playlists"), list) else []
            playlists = [p for p in (self._normalizar_playlist(item) for item in items) if p]
            return {"success": sucesso, "confirmed": sucesso, "message": f"{len(playlists)} playlist(s) encontrada(s) no {self.nome}." if sucesso else self._mensagem(data, "Não foi possível listar as playlists."), "status": "ativo" if sucesso else "erro", "playlists": playlists, "data": {"playlists": playlists, "resposta_api": data}, "http_status": response.status_code}
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "message": f"Erro ao listar playlists do {self.nome}: {erro}", "status": "erro", "playlists": [], "data": {}, "http_status": None}

    @staticmethod
    def _montar_url(dns, usuario, senha, url_playlist):
        url_playlist = str(url_playlist or "").strip()
        if url_playlist:
            return url_playlist
        dns = str(dns or "").strip().rstrip("/")
        if not dns:
            return ""
        if not dns.startswith(("http://", "https://")):
            dns = f"http://{dns}"
        return f"{dns}/get.php?{urlencode({'username': usuario, 'password': senha, 'type': 'm3u_plus', 'output': 'ts'})}"

    def _salvar_playlist(self, remote_id="", nome_playlist="", usuario="", senha="", dns="", url_playlist="", proteger=False, pin="", **kwargs):
        if not self._token_salvo():
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": "Autentique o IBO com o CAPTCHA antes de enviar a playlist.", "status": "aguardando_captcha", "remote_id": str(remote_id or ""), "data": {}, "http_status": 401}
        nome_playlist = str(nome_playlist or "Minha lista").strip()
        usuario = str(usuario or "").strip()
        senha = str(senha or "").strip()
        pin = str(pin or "").strip()
        url_final = self._montar_url(dns, usuario, senha, url_playlist)
        if not url_final:
            return {"success": False, "confirmed": False, "message": "Informe a URL completa ou DNS, usuário e senha.", "status": "erro", "remote_id": str(remote_id or ""), "data": {}, "http_status": 400}
        if proteger and not pin:
            return {"success": False, "confirmed": False, "message": "Informe o PIN de proteção.", "status": "erro", "remote_id": str(remote_id or ""), "data": {}, "http_status": 400}
        payload = {
            "current_playlist_url_id": str(remote_id).strip() if remote_id else -1,
            "playlist_url": url_final,
            "playlist_name": nome_playlist,
            "username": "",
            "password": "",
            "playlist_type": "general",
            "protect": "true" if proteger else "false",
            "xml_url": "",
            "pin": pin if proteger else "",
        }
        try:
            response, data = self._request("POST", self.SAVE_PATH, json=payload)
            sucesso = response.status_code == 200 and str(data.get("status") or "").lower() == "success"
            retorno = data.get("data") if isinstance(data.get("data"), dict) else {}
            novo_id = str(retorno.get("_id") or remote_id or "").strip()
            return {"success": sucesso, "confirmed": bool(sucesso and novo_id), "message": "Playlist atualizada no IBO." if sucesso and remote_id else "Playlist cadastrada no IBO." if sucesso else self._mensagem(data, "Não foi possível salvar a playlist no IBO."), "status": "ativo" if sucesso else "erro", "remote_id": novo_id, "data": data, "http_status": response.status_code}
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "message": f"Erro ao salvar playlist no {self.nome}: {erro}", "status": "erro", "remote_id": str(remote_id or ""), "data": {}, "http_status": None}

    def adicionar_playlist(self, **kwargs):
        return self._salvar_playlist(remote_id="", **kwargs)

    def editar_playlist(self, remote_id="", **kwargs):
        remote_id = str(remote_id or "").strip()
        if not remote_id:
            return {"success": False, "confirmed": False, "message": "ID remoto não informado.", "status": "erro", "remote_id": "", "data": {}, "http_status": 400}
        return self._salvar_playlist(remote_id=remote_id, **kwargs)

    def excluir_playlist(self, remote_id="", pin="", protegida=False, **kwargs):
        remote_id = str(remote_id or "").strip()
        pin = str(pin or "").strip()
        if not remote_id:
            return {"success": False, "confirmed": False, "message": "ID remoto não informado.", "status": "erro", "data": {}, "http_status": 400}
        if not self._token_salvo():
            return {"success": False, "confirmed": False, "requires_captcha": True, "message": "Autentique o IBO com o CAPTCHA antes de excluir.", "status": "aguardando_captcha", "data": {}, "http_status": 401}
        if protegida and not pin:
            return {"success": False, "confirmed": False, "message": "Informe o PIN da playlist protegida.", "status": "erro", "data": {}, "http_status": 400}
        try:
            path = self.DELETE_PATH.format(remote_id=remote_id)
            response, data = self._request("DELETE", path, json={"pin": pin})
            sucesso = response.status_code == 200 and str(data.get("status") or "").lower() == "success"
            return {"success": sucesso, "confirmed": sucesso, "message": "Playlist excluída do IBO." if sucesso else self._mensagem(data, "Não foi possível excluir a playlist do IBO."), "status": "excluido" if sucesso else "erro", "remote_id": remote_id, "data": data, "http_status": response.status_code}
        except requests.RequestException as erro:
            return {"success": False, "confirmed": False, "message": f"Erro ao excluir playlist do {self.nome}: {erro}", "status": "erro", "remote_id": remote_id, "data": {}, "http_status": None}
