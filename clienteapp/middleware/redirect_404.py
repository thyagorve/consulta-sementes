# middleware/redirect_404.py
import logging
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse

logger = logging.getLogger(__name__)

class Redirect404ToLoginMiddleware(MiddlewareMixin):
    """
    Middleware para redirecionar erros 404 para a página de login
    """
    def process_response(self, request, response):
        # Só atua se for erro 404
        if response.status_code == 404:
            # Log para debugging
            logger.warning(f'404 detectado para URL: {request.path}')
            
            # URLs que NÃO devem redirecionar para login
            excluded_paths = [
                '/admin/',
                '/static/',
                '/media/',
                '/favicon.ico',
                '/robots.txt',
                '/__debug__/',  # Django Debug Toolbar
                '/sitemap.xml',
                 '/integra/webhook',
            ]
            
            # Verifica se é uma URL de arquivo estático
            if (request.path.startswith('/static/') or 
                request.path.startswith('/media/')):
                return response  # Mantém o 404 para arquivos estáticos
            
            # Verifica se a URL não está na lista de exclusão
            if not any(request.path.startswith(excluded) for excluded in excluded_paths):
                # Se já está autenticado, redireciona para dashboard
                if request.user.is_authenticated:
                    return redirect('dashboard')
                # Se não está autenticado, redireciona para login (página inicial)
                # Seu login está na raiz '/' com name='login'
                next_url = request.get_full_path()
                # Redireciona para a raiz (login) com parâmetro next
                return redirect(f'/?next={next_url}')
        
        return response