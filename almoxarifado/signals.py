# almoxarifado/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

@receiver(post_migrate)
def configurar_grupos_almoxarifado(sender, **kwargs):
    """Configura grupos automaticamente após as migrações"""
    
    # Só executa para o app almoxarifado
    if sender.name != 'almoxarifado':
        return
    
    print("🔧 Configurando grupos e permissões do almoxarifado...")
    
    try:
        # Buscar as permissões que foram criadas automaticamente
        content_type = ContentType.objects.get(app_label='almoxarifado', model='item')
        
        # Buscar as permissões
        perm_ver = Permission.objects.get(codename='pode_ver_almoxarifado', content_type=content_type)
        perm_gerenciar = Permission.objects.get(codename='pode_gerenciar_almoxarifado', content_type=content_type)
        
        # Configurar grupo ALMOXARIFE
        grupo_almoxarife, created = Group.objects.get_or_create(name='almoxarife')
        grupo_almoxarife.permissions.add(perm_ver, perm_gerenciar)
        print(f"   ✅ Grupo 'almoxarife' configurado com {grupo_almoxarife.permissions.count()} permissões")
        
        # Configurar grupo OPERADOR (apenas visualização)
        grupo_operador, created = Group.objects.get_or_create(name='operador')
        grupo_operador.permissions.add(perm_ver)
        print(f"   ✅ Grupo 'operador' configurado com {grupo_operador.permissions.count()} permissões")
        
        print("   ✅ Configuração concluída!")
        
    except ContentType.DoesNotExist:
        print("   ⚠️ ContentType do modelo Item não encontrado, aguardando migrações...")
    except Permission.DoesNotExist:
        print("   ⚠️ Permissões ainda não criadas, aguardando migrações...")
    except Exception as e:
        print(f"   ❌ Erro ao configurar grupos: {e}")