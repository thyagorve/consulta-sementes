from django.db import migrations, models


def copiar_codigo_legado(apps, schema_editor):
    Configuracao = apps.get_model('clientes', 'Configuracao')
    for config in Configuracao.objects.all().iterator():
        codigo_novo = (getattr(config, 'codigo_protecao_playlist', '') or '').strip()
        codigo_legado = (getattr(config, 'device_key_padrao', '') or '').strip()
        if not codigo_novo and codigo_legado:
            config.codigo_protecao_playlist = codigo_legado
            config.save(update_fields=['codigo_protecao_playlist'])


def reverso(apps, schema_editor):
    # Não sobrescreve o campo legado ao reverter.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0094_alter_configuracao_device_key_padrao'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracao',
            name='codigo_protecao_playlist',
            field=models.CharField(
                blank=True,
                help_text='Código/PIN aplicado automaticamente às novas listas para protegê-las no aplicativo.',
                max_length=150,
                null=True,
                verbose_name='Código de proteção das listas',
            ),
        ),
        migrations.RunPython(copiar_codigo_legado, reverso),
    ]
