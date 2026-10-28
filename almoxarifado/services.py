"""Compatibilidade do antigo módulo de notificações externas do Almoxarifado.

A integração Evolution/WhatsApp foi removida do fluxo operacional. Este módulo
permanece apenas para não quebrar comandos legados que ainda possam importar
``get_notificacao_service``. Nenhum método realiza acesso de rede.
"""
import re
import logging
from django.apps import apps

logger = logging.getLogger(__name__)


class WhatsAppNotificacaoService:
    """Stub local e seguro da antiga integração externa.

    Nenhuma chamada HTTP é feita. Métodos antigos retornam um estado explícito
    de integração removida para preservar compatibilidade com código legado.
    """

    REMOVED_MESSAGE = 'Integração externa do Almoxarifado removida.'

    def __init__(self):
        self._config = None

    def _get_config_model(self):
        return apps.get_model('almoxarifado', 'ConfiguracaoWhatsApp')

    @property
    def config(self):
        if self._config is None:
            try:
                self._config = self._get_config_model().objects.first()
            except Exception:
                self._config = None
        return self._config

    def formatar_numero(self, numero):
        if not numero:
            return None
        numero = re.sub(r'\D', '', str(numero))
        if not numero.startswith('55') and len(numero) >= 10:
            numero = f'55{numero}'
        return numero

    def substituir_variaveis(self, template, item, **kwargs):
        context = {
            'nome': item.nome,
            'codigo': item.codigo or 'N/A',
            'localizacao': item.localizacao or 'N/A',
            'departamento': item.get_departamento_display(),
            'quantidade': float(item.quantidade),
            'minimo': float(item.estoque_minimo),
            'unidade': item.get_unidade_display(),
            'sugestao': max(0, float(item.estoque_minimo * 2 - item.quantidade)),
        }
        context.update(kwargs)
        mensagem = template or ''
        for key, value in context.items():
            if isinstance(value, float):
                value = f'{value:.2f}'.replace('.', ',')
            mensagem = mensagem.replace(f'{{{key}}}', str(value))
        mensagem = re.sub(r'\{[^}]+\}', '', mensagem)
        return re.sub(r'\s+', ' ', mensagem).strip()

    def get_numeros_destino(self, departamento=None):
        return []

    def enviar_mensagem(self, numero, mensagem):
        logger.info('Envio externo ignorado: integração do Almoxarifado removida.')
        return False, self.REMOVED_MESSAGE

    def notificar_item(self, item, tipo, adicionado=0):
        return []

    def testar_conexao(self, numero_teste):
        return False, self.REMOVED_MESSAGE

    def listar_instancias_evolution(self):
        return []

    def criar_instancia_evolution(self, instance_name):
        return False, self.REMOVED_MESSAGE

    def obter_qrcode_instancia(self, instance_name):
        return False, self.REMOVED_MESSAGE

    def verificar_status_instancia(self, instance_name):
        return 'disabled'

    def deletar_instancia_evolution(self, instance_name):
        return False, self.REMOVED_MESSAGE


_service_instance = None


def get_notificacao_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = WhatsAppNotificacaoService()
    return _service_instance
