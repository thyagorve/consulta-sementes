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
