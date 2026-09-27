from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clientes', '0097_testeplaylist'),
    ]

    operations = [
        migrations.AddField(
            model_name='testeplaylist',
            name='whatsapp',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='testeplaylist',
            name='plano_teste',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='testes_playlist_planejados',
                to='clientes.servico',
            ),
        ),
    ]
