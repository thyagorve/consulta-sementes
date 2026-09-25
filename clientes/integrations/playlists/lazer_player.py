from .app_acesso_dual import AppAcessoDualProvider


class LazerPlayerProvider(AppAcessoDualProvider):
    slug = "lazer_player"
    nome = "Lazer Player"
    SITE_URL = "https://appacesso.com"
    BASE_URL = "https://api.appacesso.com/api"
