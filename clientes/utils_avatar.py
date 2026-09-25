import requests
import base64
import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from whatsapp_integration.models import UserInstance

logger = logging.getLogger(__name__)


def atualizar_avatar_rapido(cliente, forcar=False):
    """
    Tenta atualizar o avatar do cliente em até 2 segundos.
    Se não conseguir, aborta silenciosamente.
    O cron vai tentar depois.
    
    Args:
        cliente: Objeto CustomUser
        forcar: Se True, remove avatar antigo e busca novo mesmo se já tem
    
    Retorna: True se conseguiu, False se falhou/timeout
    """
    # Não tem WhatsApp? Pula
    if not cliente.whatsapp:
        return False
    
    # Se não forçar e já tem avatar válido recente (menos de 24h), pula
    if not forcar and cliente.whatsapp_avatar_status == 'found' and cliente.whatsapp_avatar_updated:
        horas = (timezone.now() - cliente.whatsapp_avatar_updated).total_seconds() / 3600
        if horas < 24:
            logger.info(f'ℹ️ Avatar de {cliente.nome} já está atualizado ({horas:.1f}h)')
            return True  # Já está bom
    
    try:
        # Formatar número
        numero = ''.join(filter(str.isdigit, cliente.whatsapp))
        if len(numero) < 10:
            return False
        
        if len(numero) in [10, 11]:
            formatted = f"55{numero}"
        elif numero.startswith('55'):
            formatted = numero
        else:
            formatted = f"55{numero}"
        
        if formatted.startswith('5555'):
            formatted = formatted[2:]
        
        # Buscar instância conectada
        instancia = None
        if cliente.dono:
            instancia = UserInstance.objects.filter(
                user=cliente.dono,
                status='connected',
                is_active=True
            ).first()
        
        if not instancia:
            instancia = UserInstance.objects.filter(
                instance_name='gestor',
                status='connected',
                is_active=True
            ).first()
        
        if not instancia:
            logger.info(f'⚠️ Nenhuma instância conectada para {cliente.nome}')
            return False
        
        # Buscar URL da foto (timeout 2 segundos). Segredos ficam no ambiente;
        # api_key do registro é apenas compatibilidade com instalações antigas.
        base_url = (getattr(settings, 'EVOLUTION_API_BASE_URL', '') or instancia.base_url or '').rstrip('/')
        api_key = instancia.api_key or getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
        if not base_url or not api_key:
            return False
        url = f"{base_url}/chat/fetchProfilePictureUrl/{instancia.instance_name}"
        headers = {'apikey': api_key, 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(
                url,
                json={"number": formatted},
                headers=headers,
                timeout=2  # ⏱️ Timeout de 2 segundos
            )
        except requests.Timeout:
            logger.info(f'⏱️ Avatar timeout para {cliente.nome}')
            return False
        except requests.RequestException:
            return False
        
        if response.status_code != 200:
            logger.info(f'⚠️ API retornou {response.status_code} para {cliente.nome}')
            return False
        
        data = response.json()
        foto_url = data.get('profilePictureUrl')
        
        if not foto_url:
            logger.info(f'⚠️ Sem foto de perfil para {cliente.nome}')
            # Se forçar, limpa o avatar antigo
            if forcar and cliente.whatsapp_avatar_url:
                cliente.whatsapp_avatar_url = None
                cliente.whatsapp_avatar_base64 = None
                cliente.whatsapp_avatar_status = 'not_found'
                cliente.whatsapp_avatar_updated = timezone.now()
                cliente.whatsapp_avatar_error = 'Usuário removeu a foto'
                cliente.save(update_fields=[
                    'whatsapp_avatar_url', 'whatsapp_avatar_base64',
                    'whatsapp_avatar_status', 'whatsapp_avatar_updated',
                    'whatsapp_avatar_error'
                ])
            return False
        
        # Se forçar ou se a URL mudou, baixa nova foto
        if not forcar and foto_url == cliente.whatsapp_avatar_url:
            logger.info(f'ℹ️ Avatar de {cliente.nome} não mudou')
            return True
        
        # Baixar a foto (timeout 2 segundos)
        try:
            img_response = requests.get(foto_url, timeout=2)
        except requests.Timeout:
            logger.info(f'⏱️ Download avatar timeout para {cliente.nome}')
            return False
        except requests.RequestException:
            return False
        
        if img_response.status_code != 200:
            return False
        
        # Verificar se é imagem
        content_type = img_response.headers.get('content-type', '')
        if 'image' not in content_type:
            return False
        
        # Salvar NOVA foto (substitui a antiga)
        image_data = img_response.content
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        cliente.whatsapp_avatar_url = foto_url
        cliente.whatsapp_avatar_base64 = image_base64
        cliente.whatsapp_avatar_status = 'found'
        cliente.whatsapp_avatar_updated = timezone.now()
        cliente.whatsapp_avatar_expires = timezone.now() + timedelta(days=7)
        cliente.whatsapp_avatar_error = None
        
        cliente.save(update_fields=[
            'whatsapp_avatar_url',
            'whatsapp_avatar_base64',
            'whatsapp_avatar_status',
            'whatsapp_avatar_updated',
            'whatsapp_avatar_expires',
            'whatsapp_avatar_error'
        ])
        
        logger.info(f'✅ Avatar atualizado: {cliente.nome} ({len(image_data)/1024:.0f}KB)')
        return True
        
    except Exception as e:
        logger.info(f'⚠️ Avatar falhou para {cliente.nome}: {str(e)[:50]}')
        return False