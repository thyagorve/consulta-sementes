from abc import ABC, abstractmethod


class PlaylistProvider(ABC):
    slug = ""
    nome = "Aplicativo"
    suporta_edicao_remota = False
    exige_captcha = False

    campos = {
        "mac_address": {"mostrar": True, "obrigatorio": True, "label": "MAC Address"},
        "device_key": {"mostrar": False, "obrigatorio": False, "label": "Device Key"},
        "codigo": {"mostrar": False, "obrigatorio": False, "label": "Código do servidor"},
        "dns": {"mostrar": False, "obrigatorio": False, "label": "DNS do servidor"},
        "url_template": {"mostrar": False, "obrigatorio": False, "label": "URL da playlist"},
    }

    def __init__(self, integracao):
        self.integracao = integracao

    @classmethod
    def configuracao_publica(cls):
        return {
            "slug": cls.slug,
            "nome": cls.nome,
            "campos": cls.campos,
            "modos_envio": getattr(cls, "modos_envio", {}),
            "suporta_edicao_remota": bool(getattr(cls, "suporta_edicao_remota", False)),
            "exige_captcha": bool(getattr(cls, "exige_captcha", False)),
        }

    @abstractmethod
    def pesquisar_dispositivo(self, **kwargs):
        raise NotImplementedError

    def listar_playlists(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def adicionar_playlist(self, **kwargs):
        raise NotImplementedError

    def editar_playlist(self, remote_id="", **kwargs):
        return {
            "success": False,
            "confirmed": False,
            "message": "Este aplicativo não permite edição remota direta.",
            "status": "erro",
            "remote_id": str(remote_id or ""),
            "data": {},
            "http_status": 400,
        }

    @abstractmethod
    def excluir_playlist(self, remote_id="", pin="", **kwargs):
        raise NotImplementedError

