from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import sys
import logging

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def configurar_grupos_almoxarifado(sender, **kwargs):
    if sender.name != 'almoxarifado':
        return
    
    if 'migrate' in sys.argv and '--fake' in sys.argv:
        return
    
    print("🔧 Configurando grupos e permissões do almoxarifado...")
    
    try:
        content_type = ContentType.objects.get(app_label='almoxarifado', model='item')
        perm_ver = Permission.objects.get(codename='pode_ver_almoxarifado', content_type=content_type)
        perm_gerenciar = Permission.objects.get(codename='pode_gerenciar_almoxarifado', content_type=content_type)
        
        grupo_almoxarife, _ = Group.objects.get_or_create(name='almoxarife')
        grupo_almoxarife.permissions.add(perm_ver, perm_gerenciar)
        
        grupo_operador, _ = Group.objects.get_or_create(name='operador')
        grupo_operador.permissions.add(perm_ver)
        
        print("✅ Grupos configurados!")
    except Exception as e:
        print(f"❌ Erro: {e}")


# Signal para notificações
@receiver(post_save, sender='almoxarifado.Item')
def verificar_estoque_notificacao(sender, instance, created, **kwargs):
    """Dispara notificações quando o estoque muda"""
    
    try:
        from .services import get_notificacao_service
        from .models import ConfiguracaoWhatsApp
        
        config = ConfiguracaoWhatsApp.get_config()
        if not config.ativo:
            return
        
        service = get_notificacao_service()
        
        if created:
            # Novo item - verifica se já está baixo
            if instance.quantidade <= 0:
                service.notificar_item(instance, 'zerado')
            elif instance.quantidade <= instance.estoque_minimo:
                service.notificar_item(instance, 'baixo')
        else:
            # Item editado - verificar mudanças
            try:
                original = sender.objects.get(pk=instance.pk)
                
                # Verifica reposição (quantidade aumentou)
                if original.quantidade < instance.quantidade:
                    adicionado = instance.quantidade - original.quantidade
                    service.notificar_item(instance, 'reposicao', adicionado)
                
                # Verifica estoque baixo/zerado
                if instance.quantidade <= 0 and original.quantidade > 0:
                    service.notificar_item(instance, 'zerado')
                elif instance.quantidade <= instance.estoque_minimo and original.quantidade > instance.estoque_minimo:
                    service.notificar_item(instance, 'baixo')
                    
            except sender.DoesNotExist:
                pass
                
    except Exception as e:
        logger.error(f"Erro no signal de notificação: {e}")