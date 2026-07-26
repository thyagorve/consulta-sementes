import time
from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.contrib import messages

class AutoLogoutMiddleware:
    """
    Desloga usuário se ficar inativo por mais que AUTO_LOGOUT_DELAY segundos.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'AUTO_LOGOUT_DELAY', 1800)  # default 30min

    def __call__(self, request):
        if request.user.is_authenticated:
            now = int(time.time())
            last_activity = request.session.get('last_activity', now)
            if now - last_activity > self.timeout:
                auth.logout(request)
                messages.warning(request, "Você foi desconectado por inatividade.")  # opcional
                return redirect('sapp:login')  # ou o nome da sua URL de login
            request.session['last_activity'] = now
        return self.get_response(request)


# sapp/middleware.py
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.conf import settings

class Smart404FallbackMiddleware:
    """
    - Se 404 e não autenticado: redireciona para o login.
    - Se 404 e autenticado: tenta usar o último segmento como named URL (ex: 'historico').
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = reverse(settings.LOGIN_URL) if ':' in settings.LOGIN_URL else reverse(settings.LOGIN_URL)

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 404:
            return response

        path = request.path
        if not request.user.is_authenticated:
            # evita loop se já estiver no login
            if path != self.login_url:
                return redirect(self.login_url)
            return response

        # autenticado: tenta recuperar por último segmento
        parts = [p for p in path.strip('/').split('/') if p]
        if parts:
            last = parts[-1]
            try:
                target = reverse(f'sapp:{last}')
                return redirect(target)
            except NoReverseMatch:
                pass  # não encontrou, cai no 404 normal

        return response


from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.hashers import check_password

SENHA_PADRAO = 'conceito123'

class ForcePasswordChangeMiddleware:
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verifica se a senha atual é a padrão
            if check_password(SENHA_PADRAO, request.user.password):
                # Permite acesso apenas a estas URLs
                urls_permitidas = [
                    reverse('sapp:mudar_senha'),
                    reverse('sapp:logout'),
                    '/static/',   # arquivos estáticos
                    '/media/',    # uploads
                ]
                current_path = request.path
                if not any(current_path.startswith(url) for url in urls_permitidas):
                    return redirect('sapp:mudar_senha')
        return self.get_response(request)
    

# sapp/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class PermissionMiddleware:
    """
    Middleware para verificar permissões de acesso às páginas
    """
    
    # Mapeamento de URLs para permissões necessárias
    URL_PERMISSIONS = {
        # Estoque
        '/estoque/lista/': 'sapp.pode_ver_estoque',
        '/estoque/movimentar/': 'sapp.pode_movimentar_estoque',
        
        # Almoxarifado
        '/almoxarifado/lista/': 'sapp.pode_ver_almoxarifado',
        '/almoxarifado/criar/': 'sapp.pode_gerenciar_almoxarifado',
        '/almoxarifado/editar/': 'sapp.pode_gerenciar_almoxarifado',
        '/almoxarifado/excluir/': 'sapp.pode_gerenciar_almoxarifado',
        
        # Empenho
        '/empenho/': 'sapp.pode_ver_empenhos',
        '/empenho/criar/': 'sapp.pode_criar_empenhos',
        
        # Mapa
        '/mapa/': 'sapp.pode_ver_mapa',
        
        # Configurações
        '/configuracoes/': 'sapp.pode_configuracoes',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verifica se o usuário está autenticado
        if request.user.is_authenticated and not request.user.is_superuser:
            path = request.path
            
            # Verifica cada URL pattern
            for url_path, permission_needed in self.URL_PERMISSIONS.items():
                if url_path in path:
                    # Se não tiver a permissão, redireciona para dashboard
                    if not request.user.has_perm(permission_needed):
                        messages.error(request, f"❌ Você não tem permissão para acessar esta página!")
                        return redirect(reverse('sapp:dashboard'))
                    break
        
        response = self.get_response(request)
        return response