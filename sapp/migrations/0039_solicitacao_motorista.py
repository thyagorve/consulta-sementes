from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0038_solicitacao_carga_itens_e_snapshots'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='motorista',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Nome do motorista da carga/expedição.',
                max_length=150,
                verbose_name='Motorista',
            ),
        ),
    ]
