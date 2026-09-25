from .app_acesso_dual import AppAcessoDualProvider


class FocoXPlayerProvider(AppAcessoDualProvider):
    slug = "focox_player"
    nome = "FocoX Player"
    SITE_URL = "https://appacesso.com"
    BASE_URL = "https://api.appacesso.com/api"
