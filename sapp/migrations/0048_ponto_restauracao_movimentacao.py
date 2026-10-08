from django.conf import settings
from django.db import migrations, models
from datetime import timedelta
import django.db.models.deletion


def criar_pontos_existentes(apps, schema_editor):
    Historico = apps.get_model('sapp', 'HistoricoItemEmpenho')
    HistoricoGeral = apps.get_model('sapp', 'HistoricoMovimentacao')
    Ponto = apps.get_model('sapp', 'PontoRestauracaoMovimentacao')

    for hist in Historico.objects.select_related('empenho__solicitacao').iterator(chunk_size=500):
        solicitacao = hist.empenho.solicitacao if hist.empenho_id else None
        estado = {}
        if solicitacao is not None:
            estado = {
                'status': solicitacao.status,
                'quantidade_solicitada': str(solicitacao.quantidade_solicitada or 0),
                'quantidade_empenhada': str(solicitacao.quantidade_empenhada or 0),
                'quantidade_movimentada': str(solicitacao.quantidade_movimentada or 0),
                'coluna_kanban_id': solicitacao.coluna_kanban_id,
                'data_finalizacao': (
                    solicitacao.data_finalizacao.isoformat()
                    if solicitacao.data_finalizacao else None
                ),
            }
        historicos_gerais_ids = []
        if hist.processado_em:
            inicio = hist.processado_em - timedelta(seconds=60)
            fim = hist.processado_em + timedelta(seconds=5)
            pares = []
            if hist.tipo == 'transferencia':
                pares = [
                    (hist.estoque_origem_id, 'Transferência (Saída)'),
                    (hist.estoque_destino_id, 'Transferência (Entrada)'),
                ]
            elif hist.tipo == 'expedicao':
                pares = [(hist.estoque_origem_id, 'Expedição')]
            for estoque_id, tipo_geral in pares:
                if not estoque_id:
                    continue
                geral = (
                    HistoricoGeral.objects
                    .filter(
                        estoque_id=estoque_id,
                        tipo=tipo_geral,
                        quantidade=hist.quantidade,
                        data_hora__gte=inicio,
                        data_hora__lte=fim,
                    )
                    .order_by('-data_hora', '-id')
                    .first()
                )
                if geral:
                    historicos_gerais_ids.append(geral.id)

        Ponto.objects.get_or_create(
            historico_id=hist.id,
            defaults={
                'historico_id_original': hist.id,
                'solicitacao_id': solicitacao.id if solicitacao else None,
                'criado_por_id': hist.processado_por_id,
                'tipo': hist.tipo or '',
                'lote': hist.lote or '',
                'quantidade': hist.quantidade or 0,
                'endereco_origem': hist.endereco_origem or '',
                'endereco_destino': hist.endereco_destino or '',
                'descricao': f'{hist.tipo or "movimentacao"} do lote {hist.lote or "-"} ({hist.quantidade or 0})',
                'estado_solicitacao': estado,
                'historicos_gerais_ids': historicos_gerais_ids,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sapp', '0047_descricoes_automaticas_carga'),
    ]

    operations = [
        migrations.CreateModel(
            name='PontoRestauracaoMovimentacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('historico_id_original', models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('tipo', models.CharField(blank=True, default='', max_length=20)),
                ('lote', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('quantidade', models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ('endereco_origem', models.CharField(blank=True, default='', max_length=100)),
                ('endereco_destino', models.CharField(blank=True, default='', max_length=100)),
                ('descricao', models.TextField(blank=True, default='')),
                ('estado_solicitacao', models.JSONField(blank=True, default=dict)),
                ('historicos_gerais_ids', models.JSONField(blank=True, default=list, help_text='IDs dos lançamentos gerais correspondentes à movimentação.')),
                ('status', models.CharField(choices=[('DISPONIVEL', 'Disponível'), ('RESTAURADO', 'Restaurado'), ('INDISPONIVEL', 'Indisponível')], db_index=True, default='DISPONIVEL', max_length=20)),
                ('restaurado_em', models.DateTimeField(blank=True, null=True)),
                ('observacao_restauracao', models.TextField(blank=True, default='')),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontos_restauracao_criados', to=settings.AUTH_USER_MODEL)),
                ('historico', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ponto_restauracao', to='sapp.historicoitemempenho')),
                ('restaurado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontos_restauracao_executados', to=settings.AUTH_USER_MODEL)),
                ('solicitacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontos_restauracao_movimentacao', to='sapp.solicitacao')),
            ],
            options={
                'verbose_name': 'Ponto de restauração de movimentação',
                'verbose_name_plural': 'Pontos de restauração de movimentações',
                'ordering': ['-criado_em', '-id'],
            },
        ),
        migrations.RunPython(criar_pontos_existentes, migrations.RunPython.noop),
    ]
