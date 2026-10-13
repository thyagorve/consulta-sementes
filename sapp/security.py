import logging

from django.shortcuts import redirect
from django.urls import reverse
from django.views.csrf import csrf_failure as django_csrf_failure

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    """Mantém CSRF ativo e recupera somente o login de token obsoleto.

    O Service Worker/PWA de versões antigas podia devolver um HTML de login
    armazenado com token anterior. Em vez de relaxar a segurança, fazemos um
    novo GET do login, que recebe cookie/token compatíveis.
    """
    if request.path.rstrip('/') == '/login':
        logger.warning('CSRF rejeitado no login; renovando formulário. Motivo: %s', reason)
        response = redirect(f"{reverse('sapp:login')}?csrf=1")
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response
    return django_csrf_failure(request, reason=reason)
