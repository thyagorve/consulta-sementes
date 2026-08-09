from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.static import serve


def service_worker(request):
    """
    Disponibiliza o Service Worker na raiz:

        /service-worker.js

    Arquivo-fonte:
        sapp/static/js/service-worker.js

    Depois do collectstatic:
        STATIC_ROOT/js/service-worker.js
    """

    arquivo = (
        Path(settings.STATIC_ROOT)
        / 'js'
        / 'service-worker.js'
    )

    if not arquivo.exists():
        raise Http404(
            'Service Worker não encontrado.'
        )

    response = FileResponse(
        open(arquivo, 'rb'),
        content_type=(
            'application/javascript; charset=utf-8'
        ),
    )

    # Permite ao Service Worker controlar o site inteiro.
    response['Service-Worker-Allowed'] = '/'

    # Evita ficar preso em uma versão antiga depois de deploy.
    response['Cache-Control'] = (
        'no-cache, no-store, must-revalidate'
    )

    return response


urlpatterns = [

    # =========================================================
    # ADMIN
    # =========================================================
    path(
        'admin/',
        admin.site.urls,
    ),

    # =========================================================
    # PWA / SERVICE WORKER
    # =========================================================
    path(
        'service-worker.js',
        service_worker,
        name='service_worker',
    ),

    # =========================================================
    # SISTEMA PRINCIPAL
    # =========================================================
    path(
        '',
        include('sapp.urls'),
    ),

    # =========================================================
    # ALMOXARIFADO
    # =========================================================
    path(
        'almoxarifado/',
        include(
            'almoxarifado.urls',
            namespace='almoxarifado',
        ),
    ),
]


# =============================================================
# ARQUIVOS ESTÁTICOS EM PRODUÇÃO
# =============================================================

if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r'^static/(?P<path>.*)$',
            serve,
            {
                'document_root':
                    settings.STATIC_ROOT
            },
        ),
    ]