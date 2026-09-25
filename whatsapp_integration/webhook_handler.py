# whatsapp_integration/webhook_handler.py
"""
Handler de Webhook Otimizado para Evolution API
- Recebe todos os eventos em um único endpoint
- Deduplica eventos repetidos
- Responde em < 100ms
- Processamento pesado em background
"""

import json
import logging
import time
import threading
import hmac
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


# ==========================================
# SISTEMA DE CACHE E DEDUPLICAÇÃO
# ==========================================

class WebhookCache:
    """
    Cache em memória para evitar:
    - Processamento duplicado de mensagens
    - Consultas repetidas ao banco
    """
    
    def __init__(self):
        self.messages = {}        # Deduplicação de mensagens
        self.instances = {}       # Cache de instâncias
        self.instances_time = {}  # Timestamp do cache
        self.message_ttl = 30     # 30 segundos para deduplicar
        self.instance_ttl = 60    # 60 segundos de cache de instância
    
    def should_process_message(self, message_id):
        """Retorna True se a mensagem deve ser processada"""
        now = time.time()
        
        # Limpar expirados
        self.messages = {
            k: v for k, v in self.messages.items() 
            if now - v < self.message_ttl
        }
        
        if message_id in self.messages:
            logger.debug(f"🔄 Mensagem duplicada ignorada: {message_id}")
            return False
        
        self.messages[message_id] = now
        return True
    
    def get_instance(self, instance_name):
        """Busca instância do cache ou banco"""
        now = time.time()
        
        # Verificar cache
        if instance_name in self.instances:
            if now - self.instances_time.get(instance_name, 0) < self.instance_ttl:
                return self.instances[instance_name]
        
        # Buscar do banco
        try:
            from whatsapp_integration.models import UserInstance
            instance = UserInstance.objects.select_related('user').get(
                instance_name=instance_name
            )
            self.instances[instance_name] = instance
            self.instances_time[instance_name] = now
            return instance
        except Exception:
            return None
    
    def clear_instance(self, instance_name):
        """Remove instância do cache"""
        self.instances.pop(instance_name, None)
        self.instances_time.pop(instance_name, None)


# Instância global do cache
cache = WebhookCache()


# ==========================================
# AUTENTICAÇÃO DO WEBHOOK
# ==========================================

def _webhook_is_authorized(request):
    """Valida segredo compartilhado quando configurado no ambiente."""
    expected = str(getattr(settings, 'EVOLUTION_WEBHOOK_SECRET', '') or '').strip()
    if not expected:
        return True

    supplied = str(request.headers.get('X-Webhook-Secret', '') or '').strip()
    if not supplied:
        auth = str(request.headers.get('Authorization', '') or '').strip()
        if auth.lower().startswith('bearer '):
            supplied = auth[7:].strip()

    return bool(supplied) and hmac.compare_digest(supplied, expected)


# ==========================================
# ENDPOINT PRINCIPAL DO WEBHOOK
# ==========================================

@csrf_exempt
@require_POST
def webhook_receiver(request):
    """
    Endpoint ÚNICO para todos os webhooks do Evolution API
    
    Evolution API deve apontar para:
    https://gestor.tlsprimesolutions.com.br/integra/webhook/receiver/
    
    Eventos ignorados (respondidos com 200 em < 1ms):
    - presence.update
    - chats.update, chats.set
    - contacts.update, contacts.set
    
    Eventos processados:
    - messages.upsert → background thread
    - connection.update → atualização rápida
    - instance.delete → limpeza
    """
    start_time = time.time()

    if not _webhook_is_authorized(request):
        logger.warning('Webhook rejeitado por autenticação inválida')
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    try:
        # Parse do JSON
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("Webhook recebeu JSON inválido")
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        # Extrair dados básicos
        event_type = payload.get('event', '')
        instance_name = payload.get('instance', '')
        
        # ==========================================
        # EVENTOS IGNORADOS (Resposta Instantânea)
        # ==========================================
        IGNORED_EVENTS = [
            'presence.update',
            'chats.update', 
            'chats.set',
            'contacts.update', 
            'contacts.set',
            'messages.edited',
            'messages.update',
        ]
        
        if event_type in IGNORED_EVENTS:
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"⚡ Ignorado {event_type} em {elapsed:.1f}ms")
            return JsonResponse({'success': True, 'ignored': event_type}, status=200)
        
        # ==========================================
        # CONNECTION UPDATE
        # ==========================================
        if event_type == 'connection.update':
            state = payload.get('data', {}).get('state', '')
            
            if state == 'open':
                logger.info(f"🟢 INSTÂNCIA CONECTADA: {instance_name}")
                # Atualizar banco em thread separada
                threading.Thread(
                    target=_update_connection_status,
                    args=(instance_name, 'connected'),
                    daemon=True
                ).start()
            
            elif state in ['close', 'disconnected']:
                logger.warning(f"🔴 INSTÂNCIA DESCONECTADA: {instance_name}")
                threading.Thread(
                    target=_update_connection_status,
                    args=(instance_name, 'disconnected'),
                    daemon=True
                ).start()
            
            elapsed = (time.time() - start_time) * 1000
            return JsonResponse({'success': True, 'status': state}, status=200)
        
        # ==========================================
        # MESSAGES UPSERT (PRINCIPAL)
        # ==========================================
        if event_type == 'messages.upsert':
            msg_data = payload.get('data', {})
            
            # Ignorar mensagens próprias IMEDIATAMENTE
            if msg_data.get('key', {}).get('fromMe'):
                return JsonResponse({'success': True, 'own_message': True}, status=200)
            
            # Deduplicar
            msg_id = msg_data.get('key', {}).get('id', '')
            if msg_id and not cache.should_process_message(msg_id):
                return JsonResponse({'success': True, 'deduplicated': True}, status=200)
            
            # Verificar se tem texto
            text = (
                msg_data.get('message', {}).get('conversation', '') or
                msg_data.get('message', {}).get('extendedTextMessage', {}).get('text', '')
            )
            
            if not text:
                return JsonResponse({'success': True, 'no_text': True}, status=200)
            
            sender = msg_data.get('key', {}).get('remoteJid', '')
            
            # Verificar cache da instância
            instance = cache.get_instance(instance_name)
            if not instance:
                logger.warning(f"Instância não encontrada: {instance_name}")
                return JsonResponse({'success': True, 'no_instance': True}, status=200)
            
            # Disparar processamento em background
            from whatsapp_integration.services.webhook_processor import process_message_background
            
            threading.Thread(
                target=process_message_background,
                args=(instance_name, sender, text),
                daemon=True
            ).start()
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"📩 Mensagem encaminhada em {elapsed:.1f}ms: {text[:50]}...")
            return JsonResponse({'success': True, 'processing': True}, status=200)
        
        # ==========================================
        # INSTANCE DELETE
        # ==========================================
        if event_type == 'instance_deleted':
            # Exclusão definitiva fica restrita à API autenticada do painel.
            # O webhook somente espelha que a instância sumiu da Evolution.
            logger.info("Evento de exclusão recebido para instância %s; marcando-a como inativa", instance_name)
            threading.Thread(
                target=_mark_instance_removed_remotely,
                args=(instance_name,),
                daemon=True
            ).start()
            return JsonResponse({'success': True, 'marked_inactive': True}, status=200)
        
        # Evento desconhecido
        logger.debug(f"Evento não mapeado: {event_type}")
        return JsonResponse({'success': True, 'unknown_event': event_type}, status=200)
        
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.error(f"❌ Erro no webhook ({elapsed:.1f}ms): {e}", exc_info=True)
        # Sempre retornar 200 para Evolution API não reenviar
        return JsonResponse({'success': False, 'error': 'Webhook processing error'}, status=200)


# ==========================================
# FUNÇÕES AUXILIARES (Background)
# ==========================================

def _update_connection_status(instance_name, status):
    """Atualiza status da instância no banco (executado em thread)"""
    try:
        from whatsapp_integration.models import UserInstance
        UserInstance.objects.filter(instance_name=instance_name).update(status=status)
        # Limpar cache se desconectou
        if status == 'disconnected':
            cache.clear_instance(instance_name)
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}")


def _mark_instance_removed_remotely(instance_name):
    """Marca remoção remota sem apagar o cadastro local do usuário."""
    try:
        from whatsapp_integration.models import UserInstance
        UserInstance.objects.filter(instance_name=instance_name).update(
            status='disconnected',
            is_active=False,
        )
        cache.clear_instance(instance_name)
    except Exception as e:
        logger.error("Erro ao marcar instância como removida remotamente: %s", e)
