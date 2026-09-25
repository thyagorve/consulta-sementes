# clientes/context_processors.py
from .models import Configuracao

def user_config(request):
    """Adiciona a configuração do usuário em todos os templates"""
    if request.user.is_authenticated:
        config = Configuracao.objects.filter(usuario=request.user).first()
        return {'config': config}
    return {'config': None}