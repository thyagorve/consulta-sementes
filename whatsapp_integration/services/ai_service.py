# whatsapp_integration/services/ai_service.py
import requests
import logging
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)

class IsolatedAIService:
    """Serviço de IA isolado por revenda"""
    
    _instances = {}
    
    @classmethod
    def get_service(cls, revenda):
        """Obtém ou cria serviço para uma revenda"""
        if revenda.id not in cls._instances:
            from whatsapp_integration.models import AIConfig, AIRevendaSettings
            ai_config = AIConfig.get_config(revenda=revenda)
            ai_personal = AIRevendaSettings.objects.filter(revenda=revenda).first()
            if ai_config:
                cls._instances[revenda.id] = cls(ai_config, ai_personal)
            else:
                return None
        return cls._instances[revenda.id]
    
    def __init__(self, ai_config, ai_personal=None):
        self.config = ai_config
        self.personal = ai_personal
        
        providers = {
            'groq': {
                'url': 'https://api.groq.com/openai/v1/chat/completions',
                'model': 'llama-3.3-70b-versatile'
            },
            'openai': {
                'url': 'https://api.openai.com/v1/chat/completions',
                'model': 'gpt-4o-mini'
            },
            'deepseek': {
                'url': 'https://api.deepseek.com/v1/chat/completions',
                'model': 'deepseek-chat'
            }
        }
        
        provider = providers.get(ai_config.provider, providers['groq'])
        self.api_url = provider['url']
        self.model = provider['model']
        self.api_key = ai_config.api_key or getattr(settings, 'GROQ_API_KEY', '')
    
    def _buscar_cliente_por_whatsapp(self, revenda, sender):
        """Busca cliente no banco pelo número de WhatsApp"""
        try:
            from clientes.models import CustomUser
            
            # Limpar número
            number = sender.replace('@s.whatsapp.net', '')
            
            # Buscar por correspondência exata ou parcial
            cliente = CustomUser.objects.filter(dono=revenda).filter(
                Q(whatsapp__icontains=number) | 
                Q(whatsapp__icontains=number[-8:]) |
                Q(whatsapp__endswith=number[-9:])
            ).first()
            
            return cliente
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cliente: {e}")
            return None
    
    def _buscar_historico_pagamentos(self, cliente, limite=3):
        """Busca últimos pagamentos do cliente"""
        try:
            from clientes.models import RelatorioFinanceiro
            
            pagamentos = RelatorioFinanceiro.objects.filter(
                cliente=cliente
            ).order_by('-data_geracao')[:limite]
            
            historico = []
            for p in pagamentos:
                historico.append({
                    'data': p.data_geracao.strftime('%d/%m/%Y') if p.data_geracao else 'N/A',
                    'valor': str(p.valor_pago) if p.valor_pago else '0',
                    'servidor': p.servidor or 'N/A'
                })
            
            return historico
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico: {e}")
            return []
    
    def _construir_contexto_cliente(self, cliente, push_name, sender):
        """Constrói o contexto do cliente para a IA"""
        
        if cliente:
            # ✅ CLIENTE ENCONTRADO NO BANCO
            dados = {
                'nome': cliente.nome or 'Cliente',
                'usuario': cliente.login_externo or cliente.username or 'N/A',
                'plano': cliente.plano.nome if cliente.plano else 'N/A',
                'vencimento': cliente.data_vencimento.strftime('%d/%m/%Y') if cliente.data_vencimento else 'N/A',
                'whatsapp': cliente.whatsapp or 'N/A',
                'saldo': f"R$ {cliente.saldo}" if cliente.saldo else 'R$ 0,00',
                'is_cliente': True,
            }
            
            # Buscar histórico de pagamentos
            historico = self._buscar_historico_pagamentos(cliente)
            
            contexto = f"""
✅ CLIENTE IDENTIFICADO (ACESSO AO BANCO LIBERADO)

DADOS DO CLIENTE NO SISTEMA:
- Nome: {dados['nome']}
- Usuário/Login: {dados['usuario']}
- Plano Atual: {dados['plano']}
- Vencimento: {dados['vencimento']}
- Saldo/Devedor: {dados['saldo']}
"""

            if historico:
                contexto += "\nÚLTIMOS PAGAMENTOS:\n"
                for i, pag in enumerate(historico, 1):
                    contexto += f"  {i}. Data: {pag['data']} | Valor: R$ {pag['valor']} | Servidor: {pag['servidor']}\n"
                contexto += f"\nTotal de pagamentos recentes: {len(historico)}\n"
            
            contexto += """
⚠️ REGRAS PARA ESTE CLIENTE (DADOS DO BANCO):
- VOCÊ PODE falar sobre: nome, plano, vencimento, saldo, pagamentos, usuário/login
- VOCÊ PODE informar valores e datas que estão no sistema
- Se perguntarem "quanto devo", "quando vence", "qual meu plano", RESPONDA com os dados acima
- Se perguntarem "qual meu usuário/senha", informe o usuário/login
- NÃO invente dados que não estão listados acima
"""
            
            return dados, contexto
        
        else:
            # ❌ NÃO É CLIENTE - Visitante
            nome = push_name or 'Visitante'
            
            dados = {
                'nome': nome,
                'usuario': 'N/A',
                'plano': 'N/A',
                'vencimento': 'N/A',
                'saldo': 'N/A',
                'is_cliente': False,
            }
            
            contexto = f"""
⚠️ VISITANTE (NÃO É CLIENTE CADASTRADO)

DADOS DISPONÍVEIS:
- Nome (do WhatsApp): {nome}
- Número: {sender}

🚫 REGRAS PARA VISITANTE (DADOS DO BANCO BLOQUEADOS):
- NÃO TEMOS dados deste número no sistema
- NÃO invente nomes, planos, vencimentos ou valores
- Se perguntarem sobre plano/vencimento/saldo, diga: "Não encontrei seu cadastro. Por favor, informe seu nome completo ou WhatsApp para verificarmos."
- Responda APENAS perguntas gerais sobre a empresa
- Ofereça ajuda para se cadastrar ou falar com um atendente
"""
            
            return dados, contexto
    
    def generate_reply(self, cliente_obj, message, instance, sender=None, push_name=None):
        """Gera resposta da IA com contexto real do banco"""
        
        if not self.api_key:
            logger.warning("❌ API Key não configurada")
            return None
        
        # Verificar limite diário
        if not self.config.can_send_message():
            logger.warning(f"⚠️ Limite diário atingido: {self.config.messages_sent_today}/{self.config.max_messages_per_day}")
            return "⚠️ Limite de mensagens diárias atingido. Tente novamente amanhã."
        
        # Buscar revenda
        revenda = self.config.revenda or self.config.admin
        
        # ✅ BUSCAR CLIENTE REAL NO BANCO PELO NÚMERO
        cliente_real = None
        if sender:
            cliente_real = self._buscar_cliente_por_whatsapp(revenda, sender)
        
        # Se encontrou no banco, USA ELE. Senão, usa o objeto passado (visitante)
        if cliente_real:
            logger.info(f"👤 Cliente encontrado no banco: {cliente_real.nome}")
            dados, contexto_banco = self._construir_contexto_cliente(cliente_real, push_name, sender)
        else:
            logger.info(f"👤 Visitante (não é cliente): {push_name or 'Desconhecido'}")
            dados, contexto_banco = self._construir_contexto_cliente(None, push_name, sender)
        
        # ✅ Usar prompt PERSONALIZADO da revenda (do HTML)
        if self.personal and self.personal.prompt_personalizado:
            system_prompt = self.personal.prompt_personalizado
            logger.info(f"📝 Usando prompt personalizado da revenda")
        else:
            system_prompt = self.config.system_prompt or "Você é um assistente virtual profissional."
            logger.info(f"📝 Usando prompt global do admin")
        
        # ✅ Adicionar regras de segurança (sempre)
        system_prompt += """

⚠️ REGRAS DE SEGURANÇA (INQUEBRÁVEIS):
1. SÓ use dados que estão no CONTEXTO acima
2. Se for CLIENTE IDENTIFICADO, pode falar os dados dele
3. Se for VISITANTE, NÃO invente dados bancários
4. NUNCA invente nomes, valores ou datas
5. Se não souber, diga "Não tenho essa informação"
6. Seja educado, profissional e responda em português
7. CHAME A PESSOA PELO NOME (use o nome do contexto)
8. Máximo 5 frases por resposta
9. NÃO repita a mesma resposta para o mesmo usuário
"""
        
        # ✅ Juntar tudo
        full_context = contexto_banco
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt + full_context},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.3,
                "max_tokens": 300
            }
            
            logger.info(f"🧠 Chamando API Groq para {dados['nome']}...")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                reply = data['choices'][0]['message']['content']
                
                # Atualizar contador
                self.config.messages_sent_today += 1
                self.config.save()
                
                logger.info(f"📊 Mensagens: {self.config.messages_sent_today}/{self.config.max_messages_per_day}")
                
                # Salvar no histórico (passa o cliente real se existir)
                cliente_para_salvar = cliente_real if cliente_real else (cliente_obj if hasattr(cliente_obj, 'id') and cliente_obj.id else None)
                self._save_conversation(cliente_para_salvar, message, reply, instance, dados['nome'])
                
                return reply
            elif response.status_code == 429:
                logger.error("❌ Rate limit excedido na API")
                return "⚠️ Muitas mensagens! Aguarde um momento e tente novamente."
            else:
                logger.error(f"❌ Erro API IA: {response.status_code}")
                return "Desculpe, estou com dificuldades técnicas. Tente novamente mais tarde."
                
        except Exception as e:
            logger.error(f"❌ Erro IA: {e}")
            return None
    
    def _save_conversation(self, cliente, message, reply, instance, nome_fallback='Visitante'):
        """Salva a conversa no histórico"""
        try:
            from whatsapp_integration.models import AIConversation
            
            revenda = self.config.revenda or self.config.admin
            
            conversation, created = AIConversation.objects.get_or_create(
                revenda=revenda,
                cliente=cliente if (cliente and hasattr(cliente, 'id') and cliente.id) else None,
                instance=instance,
                defaults={'status': 'active'}
            )
            
            conversation.add_message('user', message)
            conversation.add_message('assistant', reply)
            
            logger.info(f"💾 Conversa salva: {conversation.total_messages} mensagens")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar conversa: {e}")