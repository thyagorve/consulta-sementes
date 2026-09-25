# clientes/mixins.py
import json
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from .models import LogAtividade

class LoggingMixin:
    """
    Mixin para adicionar logging automático às views
    """
    
    def criar_log(self, request, tipo_acao, descricao, modelo_afetado=None, 
                  objeto_id=None, dados_antes=None, dados_depois=None, status='sucesso'):
        """
        Método para criar logs de forma padronizada
        """
        # Converte objetos para JSON se necessário
        if dados_antes and not isinstance(dados_antes, (dict, list, type(None))):
            dados_antes = json.loads(json.dumps(dados_antes, cls=DjangoJSONEncoder))
        
        if dados_depois and not isinstance(dados_depois, (dict, list, type(None))):
            dados_depois = json.loads(json.dumps(dados_depois, cls=DjangoJSONEncoder))
        
        # Registra o log
        LogAtividade.registrar(
            request=request,
            usuario=request.user if request.user.is_authenticated else None,
            tipo_acao=tipo_acao,
            descricao=descricao,
            modelo_afetado=modelo_afetado,
            objeto_id=str(objeto_id) if objeto_id else None,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            status=status
        )
    
    def log_login(self, request, user, status='sucesso'):
        """
        Log específico para login
        """
        descricao = f"Usuário {user.username} fez login no sistema"
        if status != 'sucesso':
            descricao = f"Tentativa de login falhou para usuário {user.username}"
        
        self.criar_log(
            request=request,
            tipo_acao='login',
            descricao=descricao,
            status=status
        )
    
    def log_logout(self, request):
        """
        Log específico para logout
        """
        if request.user.is_authenticated:
            self.criar_log(
                request=request,
                tipo_acao='logout',
                descricao=f"Usuário {request.user.username} saiu do sistema"
            )
    
    def log_criacao(self, request, objeto, modelo_nome):
        """
        Log para criação de objetos
        """
        self.criar_log(
            request=request,
            tipo_acao='create',
            descricao=f"Usuário {request.user.username} criou {modelo_nome}: {str(objeto)}",
            modelo_afetado=modelo_nome,
            objeto_id=objeto.id,
            dados_depois=self._serializar_objeto(objeto)
        )
    
    def log_edicao(self, request, objeto, modelo_nome, dados_antes):
        """
        Log para edição de objetos
        """
        self.criar_log(
            request=request,
            tipo_acao='update',
            descricao=f"Usuário {request.user.username} editou {modelo_nome}: {str(objeto)}",
            modelo_afetado=modelo_nome,
            objeto_id=objeto.id,
            dados_antes=dados_antes,
            dados_depois=self._serializar_objeto(objeto)
        )
    
    def log_exclusao(self, request, objeto, modelo_nome, dados_antes):
        """
        Log para exclusão de objetos
        """
        self.criar_log(
            request=request,
            tipo_acao='delete',
            descricao=f"Usuário {request.user.username} excluiu {modelo_nome}: {str(objeto)}",
            modelo_afetado=modelo_nome,
            objeto_id=objeto.id,
            dados_antes=dados_antes
        )
    
    def _serializar_objeto(self, objeto):
        """
        Serializa um objeto para JSON
        """
        try:
            # Tenta serializar campos básicos
            dados = {}
            for field in objeto._meta.fields:
                if field.name not in ['password', 'senha', 'token', 'api_key']:  # Campos sensíveis
                    try:
                        value = getattr(objeto, field.name)
                        if hasattr(value, '__str__'):
                            dados[field.name] = str(value)
                        else:
                            dados[field.name] = value
                    except:
                        pass
            return dados
        except:
            return {'_repr': str(objeto)}