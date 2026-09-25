# whatsapp_integration/services/webhook_processor.py
"""
Processador de Mensagens em Background
Executado em thread separada para não travar o webhook principal
"""

import logging
import requests as http_requests
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)


def process_message_background(instance_name, sender, text):
    """
    Processa uma mensagem em background:
    1. Busca configurações de IA
    2. Verifica regras (grupo, marcação, etc)
    3. Busca cliente
    4. Gera resposta com IA
    5. Envia resposta via Evolution API
    """
    try:
        from whatsapp_integration.models import UserInstance, AIRevendaSettings
        from clientes.models import CustomUser
        
        # Buscar instância
        instance = UserInstance.objects.select_related('user').get(
            instance_name=instance_name
        )
        revenda = instance.user
        
        # Verificar IA ativa
        ai_settings = AIRevendaSettings.objects.filter(
            revenda=revenda, 
            ia_ativada=True
        ).first()
        
        if not ai_settings:
            logger.debug(f"IA desativada para {revenda}")
            return
        
        # Verificar se é grupo
        is_group = '@g.us' in sender or '@lid' in sender
        
        # Regras de grupo
        if is_group:
            if not ai_settings.responder_grupos:
                logger.debug(f"IA não responde em grupos")
                return
            
            if ai_settings.precisa_marcacao:
                marcacao = ai_settings.bot_marcacao or '@bot'
                if marcacao.lower() not in text.lower():
                    logger.debug(f"Bot não foi marcado no grupo")
                    return
        
        # Palavras de ativação
        if ai_settings.palavras_ativacao:
            palavras = [p.strip().lower() for p in ai_settings.palavras_ativacao.split(',')]
            if not any(p in text.lower() for p in palavras):
                logger.debug(f"Palavra de ativação não encontrada")
                return
        
        # Buscar cliente (consulta otimizada)
        number = sender.replace('@s.whatsapp.net', '').replace('@lid', '')
        
        cliente = CustomUser.objects.filter(
            dono=revenda
        ).filter(
            Q(whatsapp__endswith=number[-8:]) | 
            Q(whatsapp__endswith=number[-10:])
        ).select_related('plano').first()
        
        if cliente:
            logger.info(f"👤 Cliente encontrado: {cliente.nome}")
        else:
            logger.info(f"👤 Visitante não cadastrado")
        
        # Gerar resposta com IA
        from whatsapp_integration.services.ai_service import IsolatedAIService
        
        ai_service = IsolatedAIService.get_service(revenda)
        if not ai_service:
            logger.warning(f"Serviço IA indisponível para {revenda}")
            return
        
        reply = ai_service.generate_reply(cliente, text, instance)
        
        if not reply:
            logger.debug(f"IA não gerou resposta")
            return
        
        # Enviar resposta
        _send_whatsapp_message(instance_name, sender, reply)
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento background: {e}", exc_info=True)


def _send_whatsapp_message(instance_name, number, text):
    """Envia mensagem via Evolution API"""
    try:
        api_url = f"{settings.EVOLUTION_API_BASE_URL}/message/sendText/{instance_name}"
        
        headers = {
            'apikey': settings.EVOLUTION_GLOBAL_API_KEY,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "number": number,
            "text": text
        }
        
        response = http_requests.post(
            api_url, 
            json=payload, 
            headers=headers, 
            timeout=15
        )
        
        if response.status_code == 201 or response.status_code == 200:
            logger.info(f"✅ Mensagem enviada para {number[:20]}: {text[:50]}...")
        else:
            logger.error(f"❌ Erro ao enviar: {response.status_code} - {response.text[:200]}")
    
    except Exception as e:
        logger.error(f"❌ Falha ao enviar mensagem: {e}")