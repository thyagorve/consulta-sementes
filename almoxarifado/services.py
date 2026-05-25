import re
import requests
import logging
from decimal import Decimal
from django.utils import timezone
from django.apps import apps

logger = logging.getLogger(__name__)


class WhatsAppNotificacaoService:
    """Serviço para envio de notificações via WhatsApp Evolution API"""
    
    def __init__(self):
        self._config = None
    
    def _get_config_model(self):
        return apps.get_model('almoxarifado', 'ConfiguracaoWhatsApp')
    
    def _get_historico_model(self):
        return apps.get_model('almoxarifado', 'HistoricoNotificacaoAlmoxarifado')
    
    @property
    def config(self):
        if self._config is None:
            try:
                ConfigModel = self._get_config_model()
                self._config = ConfigModel.get_config()
                logger.info(f"✅ Configuração carregada: Instance={self._config.instance_name}, URL={self._config.api_url}")
            except Exception as e:
                logger.warning(f"Erro ao carregar configuração: {e}")
                self._config = None
        return self._config
    
    def _formatar_url_api(self, url):
        """Garante que a URL tenha o protocolo correto"""
        if not url:
            return url
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')
    
    def formatar_numero(self, numero):
        """Formata número para o padrão da API Evolution (apenas dígitos, com 55)"""
        if not numero:
            return None
        # Remove tudo que não é dígito
        numero = re.sub(r'\D', '', str(numero))
        # Adiciona código do Brasil se necessário
        if not numero.startswith('55') and len(numero) >= 10:
            numero = f"55{numero}"
        return numero
    
    def enviar_mensagem(self, numero, mensagem):
        """Envia mensagem via API Evolution - Formato correto"""
        if not self.config or not self.config.ativo:
            return False, "Sistema desativado"
        
        if not self.config.api_url:
            return False, "API não configurada"
        
        if not self.config.api_key:
            return False, "API Key não configurada"
        
        if not self.config.instance_name:
            return False, "Instância não configurada"
        
        # FORMATAR URL CORRETAMENTE
        api_url = self._formatar_url_api(self.config.api_url)
        
        # Formatar número (apenas dígitos, com 55)
        numero_formatado = self.formatar_numero(numero)
        
        if not numero_formatado:
            return False, f"Número inválido: {numero}"
        
        headers = {
            'Content-Type': 'application/json',
            'apikey': self.config.api_key
        }
        
        url = f"{api_url}/message/sendText/{self.config.instance_name}"
        
        # Payload correto para a Evolution API
        payload = {
            "number": numero_formatado,
            "text": mensagem[:4096],  # texto direto
            "delay": 100,
            "linkPreview": False
        }
        
        logger.info(f"📤 Enviando mensagem para: {numero_formatado}")
        logger.info(f"📍 URL: {url}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Mensagem enviada com sucesso para {numero_formatado}")
                return True, response.json() if response.text else {"message": "OK"}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"❌ Erro ao enviar: {error_msg}")
                return False, error_msg
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout ao enviar para {numero_formatado}")
            return False, "Timeout na conexão"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Erro de conexão: {e}")
            return False, f"Erro de conexão com {api_url}"
        except Exception as e:
            logger.error(f"💥 Erro inesperado: {e}")
            return False, str(e)
    
    def substituir_variaveis(self, template, item, **kwargs):
        """Substitui variáveis no template"""
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
        
        mensagem = template
        for key, value in context.items():
            if isinstance(value, float):
                value = f"{value:.2f}".replace('.', ',')
            mensagem = mensagem.replace(f"{{{key}}}", str(value))
        
        # Remove placeholders não substituídos
        mensagem = re.sub(r'\{[^}]+\}', '', mensagem)
        mensagem = re.sub(r'\s+', ' ', mensagem).strip()
        
        return mensagem
    
    def get_numeros_destino(self, departamento=None):
        """Retorna lista de números de destino para um departamento"""
        if not self.config:
            return []
        
        # Se tem departamento, busca números específicos
        if departamento and hasattr(self.config, 'numeros_por_departamento') and self.config.numeros_por_departamento:
            dept_numeros = self.config.numeros_por_departamento.get(departamento, [])
            if dept_numeros:
                return dept_numeros
        
        # Se não tem números específicos, usa números padrão
        if hasattr(self.config, 'numeros_padrao') and self.config.numeros_padrao:
            return [n.strip() for n in self.config.numeros_padrao.split(',') if n.strip()]
        
        return []
    
    def notificar_item(self, item, tipo, adicionado=0):
        """Envia notificação para um item (agora com base no departamento)"""
        if not self.config or not self.config.ativo:
            return []
        
        # Verificar se o departamento está ativo para notificações
        depts_ativos = getattr(self.config, 'departamentos_ativos', [])
        if depts_ativos and item.departamento not in depts_ativos:
            logger.info(f"Departamento {item.departamento} não está ativo para notificações")
            return []
        
        resultados = []
        
        # Seleciona template
        if tipo == 'baixo' and getattr(self.config, 'notificar_baixo', self.config.notificar_estoque_baixo):
            template = self.config.template_estoque_baixo
        elif tipo == 'zerado' and getattr(self.config, 'notificar_zerado', self.config.notificar_estoque_zerado):
            template = self.config.template_estoque_zerado
        elif tipo == 'reposicao' and getattr(self.config, 'notificar_reposicao', self.config.notificar_reposicao):
            template = self.config.template_reposicao
        else:
            return resultados
        
        # Preparar kwargs extras
        kwargs = {}
        if tipo == 'reposicao':
            kwargs.update({
                'nova_quantidade': float(item.quantidade),
                'adicionado': float(adicionado),
                'status': 'Normalizado' if item.quantidade > item.estoque_minimo else 'Ainda Baixo'
            })
        
        mensagem = self.substituir_variaveis(template, item, **kwargs)
        
        # Obter números baseado no departamento do item
        numeros = self.get_numeros_destino(item.departamento)
        
        logger.info(f"📢 Enviando notificação de {tipo} para {item.nome}")
        logger.info(f"   Departamento: {item.departamento}")
        logger.info(f"   Números: {numeros}")
        
        if not numeros:
            logger.warning(f"⚠️ Nenhum número configurado para o departamento {item.departamento}")
            return resultados
        
        HistoricoModel = self._get_historico_model()
        
        for numero in numeros:
            try:
                # Registrar histórico
                historico = HistoricoModel.objects.create(
                    item=item,
                    tipo=tipo,
                    destinatario=numero,
                    mensagem=mensagem,
                    status='pendente'
                )
                
                # Enviar mensagem
                success, response = self.enviar_mensagem(numero, mensagem)
                
                if success:
                    historico.status = 'enviado'
                    historico.enviado_em = timezone.now()
                    if isinstance(response, dict):
                        historico.api_response = str(response)[:500]
                    historico.save()
                    resultados.append({'numero': numero, 'success': True})
                    logger.info(f"✅ Notificação enviada para {numero} - Depto: {item.departamento} - Item: {item.nome}")
                else:
                    historico.status = 'erro'
                    historico.erro = str(response)[:500]
                    historico.save()
                    resultados.append({'numero': numero, 'success': False, 'error': str(response)})
                    logger.error(f"❌ Falha ao enviar para {numero}: {response}")
                    
            except Exception as e:
                logger.error(f"💥 Erro ao processar notificação para {item.nome}: {e}")
                resultados.append({'numero': numero, 'success': False, 'error': str(e)})
        
        return resultados
    
    def testar_conexao(self, numero_teste):
        """Testa a conexão com a API"""
        from datetime import datetime
        mensagem_teste = f"""🧪 *TESTE DE CONEXÃO*

✅ Configuração funcionando!

📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔔 Sistema de Almoxarifado"""
        return self.enviar_mensagem(numero_teste, mensagem_teste)
    
    def listar_instancias_evolution(self):
        """Lista instâncias disponíveis na Evolution API"""
        if not self.config or not self.config.api_url:
            return []
        
        headers = {'apikey': self.config.api_key} if self.config.api_key else {}
        api_url = self._formatar_url_api(self.config.api_url)
        
        try:
            url = f"{api_url}/instance/fetchInstances"
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Erro ao listar instâncias: {e}")
        return []
    
    def criar_instancia_evolution(self, instance_name, webhook_url=None):
        """Cria uma nova instância na Evolution API"""
        if not self.config or not self.config.api_url:
            return False, "API não configurada"
        
        headers = {'Content-Type': 'application/json'}
        if self.config.api_key:
            headers['apikey'] = self.config.api_key
        
        api_url = self._formatar_url_api(self.config.api_url)
        
        payload = {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        if webhook_url:
            payload["webhook"] = {"url": webhook_url}
        
        try:
            url = f"{api_url}/instance/create"
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            return response.status_code in [200, 201], response.json() if response.text else {}
        except Exception as e:
            logger.error(f"Erro ao criar instância: {e}")
            return False, str(e)
    
    def obter_qrcode_instancia(self, instance_name):
        """Obtém QR Code para conectar a instância"""
        if not self.config or not self.config.api_url:
            return False, "API não configurada"
        
        headers = {'apikey': self.config.api_key} if self.config.api_key else {}
        api_url = self._formatar_url_api(self.config.api_url)
        
        try:
            url = f"{api_url}/instance/connect/{instance_name}"
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                # Tentar extrair pairing code ou QR Code
                pairing_code = data.get('pairingCode')
                qrcode = data.get('base64') or data.get('qrcode', {}).get('base64')
                
                if pairing_code:
                    return True, {'pairingCode': pairing_code}
                elif qrcode:
                    return True, {'qrcode': qrcode}
                else:
                    return False, "Nenhum código disponível"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Erro ao obter QR Code: {e}")
            return False, str(e)
    
    def verificar_status_instancia(self, instance_name):
        """Verifica o status da instância"""
        if not self.config or not self.config.api_url:
            return 'unknown'
        
        headers = {'apikey': self.config.api_key} if self.config.api_key else {}
        api_url = self._formatar_url_api(self.config.api_url)
        
        try:
            url = f"{api_url}/instance/fetchInstances?instanceName={instance_name}"
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    status = data[0].get('connectionStatus', 'close')
                    return 'connected' if status == 'open' else 'disconnected'
                elif isinstance(data, dict):
                    status = data.get('connectionStatus', 'close')
                    return 'connected' if status == 'open' else 'disconnected'
            return 'unknown'
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return 'unknown'
    
    def deletar_instancia_evolution(self, instance_name):
        """Deleta uma instância da Evolution API"""
        if not self.config or not self.config.api_url:
            return False, "API não configurada"
        
        headers = {'apikey': self.config.api_key} if self.config.api_key else {}
        api_url = self._formatar_url_api(self.config.api_url)
        
        try:
            url = f"{api_url}/instance/delete/{instance_name}"
            response = requests.delete(url, headers=headers, timeout=10, verify=False)
            return response.status_code in [200, 204], response.json() if response.text else {}
        except Exception as e:
            logger.error(f"Erro ao deletar instância: {e}")
            return False, str(e)


_notificacao_service = None


def get_notificacao_service():
    global _notificacao_service
    if _notificacao_service is None:
        _notificacao_service = WhatsAppNotificacaoService()
    return _notificacao_service