from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0039_solicitacao_motorista'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='placa',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Placa do veículo da carga/expedição.',
                max_length=20,
                verbose_name='Placa',
            ),
        ),
    ]
