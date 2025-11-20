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

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verifica se o usuário tem perfil e se está marcado como primeiro acesso
            try:
                if request.user.perfil.primeiro_acesso:
                    # Evita loop infinito permitindo acesso à página de mudar senha e logout
                    allowed_urls = [
                        reverse('sapp:mudar_senha'),
                        reverse('sapp:logout'),
                    ]
                    if request.path not in allowed_urls:
                        return redirect('sapp:mudar_senha')
            except:
                pass # Se não tiver perfil (ex: admin criado via terminal antigo), ignora

        response = self.get_response(request)
        return response