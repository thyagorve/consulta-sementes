from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0049_reconciliar_contadores_solicitacao'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='estoque',
            index=models.Index(
                fields=['-data_ultima_movimentacao', '-id'],
                name='est_mov_data_id_idx',
            ),
        ),
    ]
