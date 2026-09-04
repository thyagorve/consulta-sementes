import re

from django.db import migrations, models


def inicializar_sequencia_carga(apps, schema_editor):
    Configuracao = apps.get_model('sapp', 'Configuracao')
    Solicitacao = apps.get_model('sapp', 'Solicitacao')

    maior = 0
    for titulo in Solicitacao.objects.filter(tipo_solicitacao='CARGA').values_list('titulo', flat=True).iterator():
        match = re.match(r'^\s*CARGA\s+(\d+)\b', str(titulo or ''), re.IGNORECASE)
        if match:
            maior = max(maior, int(match.group(1)))

    config, _ = Configuracao.objects.get_or_create(pk=1)
    config.proximo_numero_carga = max(int(config.proximo_numero_carga or 1), maior + 1)
    config.save(update_fields=['proximo_numero_carga'])


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0041_corrigir_quantidade_historico_entrada'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracao',
            name='proximo_numero_carga',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Sequência automática usada nos títulos CARGA N.',
                verbose_name='Próximo número de carga',
            ),
        ),
        migrations.RunPython(
            inicializar_sequencia_carga,
            migrations.RunPython.noop,
        ),
    ]
