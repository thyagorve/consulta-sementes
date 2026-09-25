from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden
import time
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import LogAtividade

class VerificacaoPermissaoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Views que queremos proteger, mapeadas por tipo de usuário
        protected_paths = {
            'admin': ['listar_clientes', 'cadastrar_cliente', 'listar_servicos'],  # Exemplo de views para admin
            'revenda': ['listar_clientes', 'cadastrar_cliente'],  # Exemplo de views para revenda
            'cliente': ['outra_pagina'],  # Exemplo de view para cliente
        }
        
        tipo_usuario = request.session.get('tipo_usuario')
        
        # Caminho atual da requisição
        current_path = request.path_info
        
        # Verificação baseada no tipo de usuário e caminho da requisição
        if tipo_usuario in protected_paths:
            for view_name in protected_paths[tipo_usuario]:
                if current_path == reverse(view_name):
                    # Redireciona para o login se o usuário não tiver permissão para acessar
                    if not request.user.is_authenticated:
                        return redirect('login')

        # Verifica se o tipo de usuário não autorizado tenta acessar uma página protegida
        if any(current_path == reverse(view) for view in protected_paths.get(tipo_usuario, [])):
            return self.get_response(request)

        # Caso o usuário não tenha permissão para acessar
        return HttpResponseForbidden("Você não tem permissão para acessar esta página.")







class LogAcessoMiddleware(MiddlewareMixin):
    """
    Middleware para registrar acesso a páginas
    """
    
    def process_request(self, request):
        # Marca o tempo de início da requisição
        request._log_start_time = time.time()
        
        # Ignora alguns paths
        paths_ignorados = [
            '/static/', '/media/', '/favicon.ico', 
            '/admin/jsi18n/', '/admin/static/',
            '__debug__'
        ]
        
        if any(path in request.path for path in paths_ignorados):
            return None
        
        # Log de acesso a página (apenas para usuários autenticados)
        if request.user.is_authenticated and request.method == 'GET':
            # Registra após um pequeno delay para evitar spam
            if hasattr(request, '_log_access') and not request._log_access:
                request._log_access = True
                
                # Não loga requisições AJAX
                if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    LogAtividade.registrar(
                        request=request,
                        usuario=request.user,
                        tipo_acao='view',
                        descricao=f"Acesso à página: {request.path}",
                        url_acessada=request.build_absolute_uri()
                    )
        
        return None
    
    def process_response(self, request, response):
        # Calcula duração da requisição
        if hasattr(request, '_log_start_time'):
            duracao = time.time() - request._log_start_time
            
            # Log de ações importantes
            if request.user.is_authenticated and request.method == 'POST':
                # Identifica a ação baseada na URL
                if '/login/' in request.path:
                    # Já tratado na view de login
                    pass
                elif '/logout/' in request.path:
                    # Já tratado na view de logout
                    pass
                elif '/cliente/ativar/' in request.path or '/cliente/desativar/' in request.path:
                    # Log de ativação/desativação
                    try:
                        cliente_id = request.path.split('/')[-2]
                        acao = 'ativado' if 'ativar' in request.path else 'desativado'
                        LogAtividade.registrar(
                            request=request,
                            usuario=request.user,
                            tipo_acao='update',
                            descricao=f"Cliente ID {cliente_id} {acao} por {request.user.username}",
                            modelo_afetado='CustomUser',
                            objeto_id=cliente_id
                        )
                    except:
                        pass
        
        return response