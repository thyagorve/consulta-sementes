from django.db import migrations
from django.contrib.auth.hashers import check_password


def normalizar_acessos(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    PerfilUsuario = apps.get_model('sapp', 'PerfilUsuario')

    senha_padrao = 'conceito123'

    try:
        almox_ver = Permission.objects.filter(
            codename='pode_ver_almoxarifado',
            content_type__app_label='almoxarifado',
        ).first()
        almox_ger = Permission.objects.filter(
            codename='pode_gerenciar_almoxarifado',
            content_type__app_label='almoxarifado',
        ).first()
        sapp_almox_ver = Permission.objects.filter(
            codename='pode_ver_almoxarifado',
            content_type__app_label='sapp',
        ).first()
        sapp_almox_ger = Permission.objects.filter(
            codename='pode_gerenciar_almoxarifado',
            content_type__app_label='sapp',
        ).first()
    except Exception:
        almox_ver = almox_ger = sapp_almox_ver = sapp_almox_ger = None

    for user in User.objects.filter(is_superuser=False).iterator():
        direct_ids = list(user.user_permissions.values_list('id', flat=True))

        # Contas legadas que dependiam somente de grupos mantêm o acesso atual,
        # mas as permissões são convertidas para individuais antes de remover
        # o grupo. Se já existem permissões individuais, elas são consideradas
        # a seleção explícita do administrador e prevalecem.
        if not direct_ids and user.groups.exists():
            group_permissions = Permission.objects.filter(group__user=user).distinct()
            if group_permissions.exists():
                user.user_permissions.add(*group_permissions)

        # Corrige permissões antigas de Almoxarifado gravadas no app sapp.
        current = user.user_permissions.all()
        if sapp_almox_ver and current.filter(pk=sapp_almox_ver.pk).exists():
            if almox_ver:
                user.user_permissions.add(almox_ver)
            user.user_permissions.remove(sapp_almox_ver)
        if sapp_almox_ger and current.filter(pk=sapp_almox_ger.pk).exists():
            if almox_ger:
                user.user_permissions.add(almox_ger)
            user.user_permissions.remove(sapp_almox_ger)

        user.groups.clear()

        perfil, _ = PerfilUsuario.objects.get_or_create(usuario_id=user.pk)
        deve_trocar = bool(user.password and check_password(senha_padrao, user.password))
        if perfil.primeiro_acesso != deve_trocar:
            perfil.primeiro_acesso = deve_trocar
            perfil.save(update_fields=['primeiro_acesso'])

    # Remove as permissões duplicadas do app sapp depois de migrar os vínculos
    # para as permissões oficiais do app almoxarifado.
    if sapp_almox_ver:
        sapp_almox_ver.delete()
    if sapp_almox_ger:
        sapp_almox_ger.delete()

    # Os grupos padrões ficam apenas como legado sem conceder acesso oculto.
    for group in Group.objects.filter(name__in=['admin', 'conferente', 'almoxarife', 'operador']):
        group.permissions.clear()


def noop_reverse(apps, schema_editor):
    # Não recriamos grupos antigos automaticamente.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0044_normalizar_cargas_avulsas'),
        ('almoxarifado', '0023_alter_dadosvalidadeitem_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='produto',
            options={
                'ordering': ['cultivar__nome', 'codigo'],
                'permissions': [
                    ('pode_ver_estoque', 'Pode visualizar estoque'),
                    ('pode_movimentar_estoque', 'Pode movimentar estoque'),
                    ('pode_ver_dashboard', 'Pode acessar o dashboard'),
                    ('pode_ver_empenhos', 'Pode visualizar empenhos'),
                    ('pode_criar_empenhos', 'Pode criar empenhos'),
                    ('pode_ver_mapa', 'Pode acessar mapa canvas'),
                    ('pode_gerenciar_usuarios', 'Pode gerenciar usuários'),
                    ('pode_configuracoes', 'Pode alterar configurações'),
                ],
                'verbose_name': 'Produto',
                'verbose_name_plural': 'Produtos',
            },
        ),
        migrations.RunPython(normalizar_acessos, noop_reverse),
    ]
