from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import sys


@receiver(post_migrate)
def configurar_grupos_almoxarifado(sender, **kwargs):
    """Mantém os grupos legados sem permissões automáticas.

    O antigo signal de notificações externas foi removido. Alterações de Item
    não disparam mais chamadas HTTP ou tarefas de WhatsApp.
    """
    if sender.name != 'almoxarifado':
        return
    if 'migrate' in sys.argv and '--fake' in sys.argv:
        return

    print('🔧 Configurando grupos e permissões do almoxarifado...')
    try:
        content_type = ContentType.objects.get(app_label='almoxarifado', model='item')
        Permission.objects.get(codename='pode_ver_almoxarifado', content_type=content_type)
        Permission.objects.get(codename='pode_gerenciar_almoxarifado', content_type=content_type)

        grupo_almoxarife, _ = Group.objects.get_or_create(name='almoxarife')
        grupo_operador, _ = Group.objects.get_or_create(name='operador')
        grupo_almoxarife.permissions.clear()
        grupo_operador.permissions.clear()
        print('✅ Grupos legados mantidos sem permissões automáticas.')
    except Exception as exc:
        print(f'❌ Erro: {exc}')
