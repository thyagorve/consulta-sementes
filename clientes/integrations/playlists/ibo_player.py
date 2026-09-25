from .ibo_base import IboBaseProvider


class IboPlayerProvider(IboBaseProvider):
    slug = "ibo_player"
    nome = "IBO Player"
    BASE_URL = "https://iboplayer.com"
