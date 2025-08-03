# sapp/context_processors.py

from django.conf import settings

def app_version_processor(request):
    """
    Adiciona a variável APP_VERSION do settings.py ao contexto de todos os templates.
    """
    return {'APP_VERSION': settings.APP_VERSION}