import os
from urllib.parse import urljoin

import requests


class SigmanAPIError(Exception):
    pass


class SigmanClient:
    """Cliente somente-leitura para testar a API SIGMAN antes da integração real.

    A documentação pública usa dois headers:
      - x-api-key
      - x-painel-token

    Este cliente não possui métodos POST/PUT/DELETE de propósito.
    """

    DEFAULT_URL = "https://apiiptv.quickgestor.com/api"

    def __init__(self, base_url=None, api_key=None, painel_token=None, timeout=25):
        self.base_url = (base_url or os.getenv("SIGMAN_API_URL") or self.DEFAULT_URL).rstrip("/")
        self.api_key = api_key or os.getenv("SIGMAN_API_KEY") or ""
        self.painel_token = painel_token or os.getenv("SIGMAN_PAINEL_TOKEN") or ""
        self.timeout = timeout

        if not self.api_key:
            raise SigmanAPIError(
                "API key não informada. Defina SIGMAN_API_KEY ou passe --api-key."
            )
        if not self.painel_token:
            raise SigmanAPIError(
                "Token do painel não informado. Defina SIGMAN_PAINEL_TOKEN ou passe --token."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-painel-token": self.painel_token,
            "User-Agent": "PainelCliente/SigmanReadOnlyTest",
        })

    def _url(self, path):
        return urljoin(self.base_url + "/", str(path).lstrip("/"))

    def _get(self, path, params=None):
        try:
            response = self.session.get(self._url(path), params=params or {}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SigmanAPIError(f"Falha de conexão com a API SIGMAN: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            trecho = (response.text or "")[:500].replace("\n", " ")
            raise SigmanAPIError(
                f"API retornou conteúdo não-JSON (HTTP {response.status_code}): {trecho}"
            ) from exc

        if not response.ok:
            mensagem = self._mensagem(payload) or f"HTTP {response.status_code}"
            raise SigmanAPIError(f"SIGMAN recusou a requisição: {mensagem}")

        if isinstance(payload, dict) and payload.get("success") is False:
            raise SigmanAPIError(self._mensagem(payload) or "A API SIGMAN retornou erro.")

        return payload

    @staticmethod
    def _mensagem(payload):
        if not isinstance(payload, dict):
            return ""
        for chave in ("message", "mensagem", "error", "erro", "detail"):
            valor = payload.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
            if isinstance(valor, dict):
                for sub in ("message", "detail", "error"):
                    texto = valor.get(sub)
                    if isinstance(texto, str) and texto.strip():
                        return texto.strip()
        return ""

    def me(self):
        return self._get("me")

    def servers(self):
        return self._get("servers")

    def users(self, *, page=1, per_page=100, username="", todos=True, **filters):
        params = {
            "userId": filters.get("userId", ""),
            "page": page,
            "connections": filters.get("connections", ""),
            "isTrial": filters.get("isTrial", ""),
            "status": filters.get("status", ""),
            "serverId": filters.get("serverId", ""),
            "packageId": filters.get("packageId", ""),
            "expiryFrom": filters.get("expiryFrom", ""),
            "expiryTo": filters.get("expiryTo", ""),
            "perPage": per_page,
            "username": username or "",
            "todos": "true" if todos else "false",
        }
        return self._get("users", params=params)

    def playlist(self, username):
        return self._get("playlist", params={"username": username})

    @staticmethod
    def extract_items(payload):
        """Aceita lista direta, envelope {data:[...]}, paginator Laravel e envelopes aninhados."""
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        data = payload.get("data", payload)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for chave in ("data", "users", "customers", "items", "results"):
                valor = data.get(chave)
                if isinstance(valor, list):
                    return valor
        return []

    @staticmethod
    def normalize_user(item):
        if not isinstance(item, dict):
            return {}

        package_obj = item.get("package")
        if isinstance(package_obj, dict):
            package = (
                package_obj.get("name")
                or package_obj.get("title")
                or package_obj.get("label")
                or package_obj.get("package")
                or ""
            )
        else:
            package = package_obj or item.get("plan") or item.get("plan_name") or ""

        server_obj = item.get("server")
        if isinstance(server_obj, dict):
            server = server_obj.get("name") or server_obj.get("title") or server_obj.get("label") or ""
        else:
            server = server_obj or item.get("server_name") or ""

        expiry = (
            item.get("expires_at_tz")
            or item.get("expires_at")
            or item.get("expiry")
            or item.get("expiration")
            or item.get("expiration_date")
            or item.get("expiry_date")
            or ""
        )

        return {
            "id": item.get("id") or item.get("user_id") or "",
            "name": item.get("name") or item.get("customer_name") or "",
            "username": item.get("username") or item.get("user") or "",
            "password": item.get("password") or item.get("pass") or "",
            "package": package,
            "expiry": expiry,
            "status": item.get("status") or "",
            "connections": item.get("connections") or item.get("max_connections") or "",
            "server": server,
            "plan_price": item.get("plan_price") or item.get("price") or "",
            "m3u_url": item.get("m3u_url") or "",
            "raw": item,
        }
