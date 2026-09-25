import time
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import auth, messages
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse

from .access_control import (
    first_allowed_url,
    has_any_direct_permission,
    has_direct_permission,
)
from .models import PerfilUsuario


class AutoLogoutMiddleware:
    """Desloga o usuário após o tempo de inatividade configurado."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'AUTO_LOGOUT_DELAY', 1800)

    def __call__(self, request):
        if request.user.is_authenticated:
            now = int(time.time())
            last_activity = request.session.get('last_activity', now)
            if now - last_activity > self.timeout:
                auth.logout(request)
                return redirect('/login/?expired=1')
            request.session['last_activity'] = now
        return self.get_response(request)


class Smart404FallbackMiddleware:
    """Em 404 autenticado, volta para a primeira tela permitida do usuário."""

    def __init__(self, get_response):
        self.get_response = get_response
        login_url = settings.LOGIN_URL
        self.login_url = reverse(login_url) if ':' in login_url else login_url

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code != 404:
            return response

        path = request.path
        if not request.user.is_authenticated:
            if path != self.login_url.split('?')[0]:
                return redirect(self.login_url)
            return response

        destino = first_allowed_url(request.user)
        return redirect(destino) if destino else response


class ForcarTrocaSenhaMiddleware:
    """Obriga usuários comuns marcados como primeiro acesso a trocar a senha."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)
            if perfil.primeiro_acesso:
                current_path = request.path
                paths_exatos = {
                    reverse('sapp:mudar_senha'),
                    reverse('sapp:logout'),
                }
                prefixes = ('/static/', '/media/', '/service-worker.js', '/sw.js')
                permitido = current_path in paths_exatos or current_path.startswith(prefixes)
                if not permitido:
                    return redirect('sapp:mudar_senha')

        return self.get_response(request)


class PermissionMiddleware:
    """Bloqueia páginas principais que não estejam explicitamente liberadas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def _deny(self, request):
        messages.error(request, '❌ Você não tem permissão para acessar esta página.')
        destino = first_allowed_url(request.user)
        if destino and request.path != urlparse(destino).path:
            return redirect(destino)
        auth.logout(request)
        return redirect('sapp:login')

    def __call__(self, request):
        user = request.user
        if not user.is_authenticated or user.is_superuser:
            return self.get_response(request)

        path = request.path

        # Rotas de autenticação, assets e raiz de redirecionamento.
        if (
            path in {reverse('sapp:redirecionar'), reverse('sapp:mudar_senha'), reverse('sapp:logout')}
            or path.startswith('/static/')
            or path.startswith('/media/')
            or path in {'/service-worker.js', '/sw.js'}
        ):
            return self.get_response(request)

        required_all = None
        required_any = None

        # Dashboard é uma permissão independente do Estoque.
        if path == '/dashboard/' or path.startswith('/dashboard-data/'):
            required_all = 'sapp.pode_ver_dashboard'

        # Estoque.
        elif path.startswith('/estoque/gestao/') or path.startswith('/estoque/transferir/') \
                or path.startswith('/estoque/editar/') or path.startswith('/estoque/excluir/') \
                or path.startswith('/estoque/registrar-saida/') or path.startswith('/estoque/nova-saida/') \
                or path.startswith('/estoque/nova-entrada/'):
            required_all = 'sapp.pode_movimentar_estoque'
        elif path == '/estoque/' or path.startswith('/estoque/inventario/') \
                or path.startswith('/historico-geral/') or path.startswith('/ficha-rastreabilidade/'):
            required_any = ('sapp.pode_ver_estoque', 'sapp.pode_movimentar_estoque')

        # Mapa.
        elif path.startswith('/mapa-armazem/') or path.startswith('/editor-mapa/'):
            required_all = 'sapp.pode_ver_mapa'

        # Solicitações e Kanban.
        elif path.startswith('/solicitacoes/nova/'):
            required_all = 'sapp.pode_criar_solicitacao'
        elif path.startswith('/solicitacoes/'):
            required_all = 'sapp.pode_ver_empenhos'
        elif path.startswith('/kanban/') or path.startswith('/api/kanban/'):
            required_any = (
                'sapp.pode_ver_empenhos',
                'sapp.pode_criar_solicitacao',
                'sapp.pode_empenhar_solicitacao',
                'sapp.pode_movimentar_solicitacao',
                'sapp.pode_cancelar_solicitacao',
                'sapp.pode_criar_empenhos',
            )
        elif path.startswith('/cargas/') or path.startswith('/api/cargas/'):
            required_any = ('sapp.pode_ver_empenhos', 'sapp.pode_movimentar_solicitacao')
        elif path == '/api/solicitacoes/listar/':
            required_all = 'sapp.pode_ver_empenhos'

        # Almoxarifado. CRUD continua protegido pelas decorators próprias.
        elif path.startswith('/almoxarifado/'):
            required_any = (
                'almoxarifado.pode_ver_almoxarifado',
                'almoxarifado.pode_gerenciar_almoxarifado',
            )

        # Configurações.
        elif path.startswith('/configuracoes/') or path.startswith('/configuracao-workflow/'):
            required_all = 'sapp.pode_configuracoes'

        if required_all and not has_direct_permission(user, required_all):
            return self._deny(request)
        if required_any and not has_any_direct_permission(user, *required_any):
            return self._deny(request)

        return self.get_response(request)
