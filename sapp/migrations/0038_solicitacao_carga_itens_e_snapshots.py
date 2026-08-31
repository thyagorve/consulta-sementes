# Generated for support to load/dispatch requests with multiple clients/products.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0037_historicoitemempenho_az_origem_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='tipo_solicitacao',
            field=models.CharField(
                choices=[
                    ('TRANSFERENCIA', 'Transferência'),
                    ('CARGA', 'Carga / Expedição'),
                ],
                db_index=True,
                default='TRANSFERENCIA',
                max_length=20,
                verbose_name='Tipo de solicitação',
            ),
        ),
        migrations.CreateModel(
            name='SolicitacaoItemCarga',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cliente', models.CharField(max_length=255)),
                ('codigo', models.CharField(db_index=True, max_length=100)),
                ('descricao', models.TextField(blank=True, default='')),
                ('categoria', models.CharField(blank=True, default='', max_length=100)),
                ('peneira', models.CharField(blank=True, default='', max_length=100)),
                ('lote', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('quantidade_solicitada', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('ordem', models.PositiveIntegerField(default=0)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('produto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_solicitacao_carga', to='sapp.produto')),
                ('solicitacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens_carga', to='sapp.solicitacao')),
            ],
            options={
                'verbose_name': 'Item de carga',
                'verbose_name_plural': 'Itens de carga',
                'ordering': ['ordem', 'id'],
            },
        ),
        migrations.AddField(
            model_name='itemempenho',
            name='item_carga',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_empenhados', to='sapp.solicitacaoitemcarga', verbose_name='Item da carga'),
        ),
        migrations.AddField(
            model_name='itemempenho',
            name='cliente_solicitacao_snapshot',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='itemempenho',
            name='codigo_produto_snapshot',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='itemempenho',
            name='descricao_produto_snapshot',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='historicoitemempenho',
            name='item_carga_id_original',
            field=models.PositiveBigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='historicoitemempenho',
            name='cliente_solicitacao',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='historicoitemempenho',
            name='codigo_produto',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='historicoitemempenho',
            name='descricao_produto',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterUniqueTogether(
            name='itemempenho',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='itemempenho',
            constraint=models.UniqueConstraint(
                condition=models.Q(item_carga__isnull=True),
                fields=('empenho', 'estoque'),
                name='uniq_empenho_estoque_sem_item_carga',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemempenho',
            constraint=models.UniqueConstraint(
                condition=models.Q(item_carga__isnull=False),
                fields=('empenho', 'estoque', 'item_carga'),
                name='uniq_empenho_estoque_item_carga',
            ),
        ),
        migrations.AlterField(
            model_name='empenho',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='auth.user'),
        ),
        migrations.AlterField(
            model_name='historicocard',
            name='acao',
            field=models.CharField(
                choices=[
                    ('CRIACAO', 'criou a solicitação'),
                    ('EMPENHO', 'empenhou'),
                    ('TRANSFERENCIA', 'transferiu'),
                    ('EXPEDICAO', 'expediu'),
                    ('CANCELAMENTO', 'cancelou'),
                    ('MOVIMENTACAO_KANBAN', 'moveu o card'),
                    ('REMOCAO_ITEM', 'removeu item'),
                    ('CONCLUSAO', 'concluiu'),
                    ('EDICAO', 'editou a solicitação'),
                ],
                max_length=20,
                verbose_name='Ação',
            ),
        ),
    ]
