from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserInstance
from .services.evolution_service import evolution_service
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@receiver(pre_delete, sender=UserInstance)
def delete_instance_from_api(sender, instance, **kwargs):
    """Quando uma instância é deletada, tenta deletar da API também"""
    try:
        evolution_service.delete_instance(instance.instance_name)
        logger.info(f"Instância {instance.instance_name} deletada da API")
    except Exception as e:
        logger.warning(f"Erro ao deletar instância da API: {str(e)}")

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Exemplo: Criar alguma configuração padrão para o usuário"""
    if created:
        logger.info(f"Usuário {instance.username} criado")
        # Aqui você pode adicionar lógica personalizada