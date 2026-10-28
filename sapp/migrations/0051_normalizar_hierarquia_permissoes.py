from django.db import migrations


def normalizar_permissoes(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    antiga = Permission.objects.filter(
        codename='pode_criar_empenhos',
        content_type__app_label='sapp',
    ).first()
    nova = Permission.objects.filter(
        codename='pode_empenhar_solicitacao',
        content_type__app_label='sapp',
    ).first()

    if antiga and nova:
        for usuario in User.objects.filter(user_permissions=antiga).iterator():
            usuario.user_permissions.add(nova)
            usuario.user_permissions.remove(antiga)

    # Os grupos são apenas legado. Nenhum grupo pode conceder acesso oculto.
    for grupo in Group.objects.filter(
        name__in=['admin', 'conferente', 'almoxarife', 'operador']
    ):
        grupo.permissions.clear()

    # Depois de migrar os vínculos, a permissão duplicada deixa de fazer parte
    # do modelo e pode ser removida do banco.
    if antiga:
        antiga.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0050_estoque_indice_data_movimentacao'),
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
                    ('pode_ver_mapa', 'Pode acessar mapa canvas'),
                    ('pode_gerenciar_usuarios', 'Pode gerenciar usuários'),
                    ('pode_configuracoes', 'Pode alterar configurações'),
                ],
                'verbose_name': 'Produto',
                'verbose_name_plural': 'Produtos',
            },
        ),
        migrations.RunPython(normalizar_permissoes, noop_reverse),
    ]
