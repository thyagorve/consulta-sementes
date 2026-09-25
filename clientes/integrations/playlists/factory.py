import importlib
import inspect
import logging
import pkgutil
import re
import unicodedata
from functools import lru_cache

from .base import PlaylistProvider

logger = logging.getLogger(__name__)

IGNORAR_MODULOS = {
    "base",
    "factory",
    "exceptions",
    "app_acesso_base",
    "app_acesso_url_base",
    "app_acesso_dual",
    "ibo_base",
}

ALIASES_PROVIDERS = {
    "fun_play": "fun_plays",
    "funplays": "fun_plays",
    "fun_player": "fun_plays",
    "focox": "focox_player",
    "foco_x": "focox_player",
    "lazer": "lazer_player",
    "ibo": "ibo_player",
    "iboplayer": "ibo_player",
    "ibo_player": "ibo_player",
}


def normalizar_slug(valor):
    valor = str(valor or "").strip().lower()
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    valor = re.sub(r"[^a-z0-9]+", "_", valor).strip("_")
    return ALIASES_PROVIDERS.get(valor, valor)


@lru_cache(maxsize=1)
def get_providers():
    providers = {}
    pacote = importlib.import_module("clientes.integrations.playlists")

    for modulo_info in pkgutil.iter_modules(pacote.__path__):
        nome_modulo = modulo_info.name
        if nome_modulo.startswith("_") or nome_modulo in IGNORAR_MODULOS:
            continue

        caminho_modulo = f"{pacote.__name__}.{nome_modulo}"
        try:
            modulo = importlib.import_module(caminho_modulo)
        except Exception:
            logger.exception("Falha ao importar provider %s", caminho_modulo)
            continue

        for _, classe in inspect.getmembers(modulo, inspect.isclass):
            if classe is PlaylistProvider:
                continue
            if not issubclass(classe, PlaylistProvider):
                continue
            if classe.__module__ != modulo.__name__:
                continue
            if inspect.isabstract(classe):
                logger.warning("Provider abstrato ignorado: %s", classe.__name__)
                continue

            slug = normalizar_slug(getattr(classe, "slug", ""))
            nome = str(getattr(classe, "nome", "") or "").strip()
            if not slug or not nome:
                continue

            classe.slug = slug
            providers[slug] = classe
            logger.info("Provider carregado: %s -> %s", slug, classe.__name__)

    return providers


def listar_provedores():
    return sorted(
        [classe.configuracao_publica() for classe in get_providers().values()],
        key=lambda item: str(item.get("nome", "")).casefold(),
    )


def get_playlist_provider(integracao):
    slug_original = getattr(integracao, "provedor", "") or ""
    slug = normalizar_slug(slug_original)
    classe = get_providers().get(slug)
    if classe is None:
        disponiveis = ", ".join(sorted(get_providers().keys())) or "nenhum"
        raise ValueError(
            f"Provider '{slug}' não foi encontrado. "
            f"Providers carregados: {disponiveis}."
        )
    return classe(integracao)


def limpar_cache_providers():
    get_providers.cache_clear()
