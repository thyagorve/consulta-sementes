from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def dec(valor):
    return Decimal(str(valor or 0))


def status_real(solicitado, empenhado, movimentado):
    solicitado = dec(solicitado)
    empenhado = dec(empenhado)
    movimentado = dec(movimentado)

    if solicitado <= 0:
        if empenhado > 0 and movimentado > 0:
            return 'MOVIMENTACAO_PARCIAL'
        if empenhado > 0:
            return 'EMPENHO_COMPLETO'
        if movimentado > 0:
            return 'CONCLUIDO'
        return 'AGUARDANDO_EMPENHO'

    if movimentado >= solicitado and empenhado <= 0:
        return 'CONCLUIDO'

    restante = max(Decimal('0'), solicitado - movimentado)
    if empenhado <= 0:
        return 'AGUARDANDO_EMPENHO'
    if empenhado < restante:
        return 'EMPENHO_PARCIAL'
    if movimentado > 0:
        return 'MOVIMENTACAO_PARCIAL'
    return 'EMPENHO_COMPLETO'


def reconciliar(apps, schema_editor):
    Solicitacao = apps.get_model('sapp', 'Solicitacao')
    ItemEmpenho = apps.get_model('sapp', 'ItemEmpenho')
    HistoricoItemEmpenho = apps.get_model('sapp', 'HistoricoItemEmpenho')

    for sol in Solicitacao.objects.all().iterator(chunk_size=200):
        itens = (
            ItemEmpenho.objects
            .filter(empenho__solicitacao_id=sol.id)
            .select_related('estoque')
        )
        historicos = (
            HistoricoItemEmpenho.objects
            .filter(empenho__solicitacao_id=sol.id)
            .exclude(tipo='removido')
            .select_related('estoque_origem')
        )

        if sol.unidade_controle == 'QUILOGRAMA':
            empenhado = Decimal('0')
            for item in itens:
                peso = dec(
                    getattr(item, 'peso_unitario_snapshot', 0)
                    or getattr(item.estoque, 'peso_unitario', 0)
                    or 0
                )
                empenhado += dec(item.quantidade) * peso

            movimentado = Decimal('0')
            for hist in historicos:
                peso = dec(
                    getattr(hist, 'peso_unitario', 0)
                    or getattr(hist.estoque_origem, 'peso_unitario', 0)
                    or 0
                )
                movimentado += dec(hist.quantidade) * peso
        else:
            empenhado = dec(
                itens.aggregate(total=Sum('quantidade'))['total'] or 0
            )
            movimentado = dec(
                historicos.aggregate(total=Sum('quantidade'))['total'] or 0
            )

        novo_status = status_real(
            sol.quantidade_solicitada,
            empenhado,
            movimentado,
        )

        sol.quantidade_empenhada = empenhado
        sol.quantidade_movimentada = movimentado
        sol.status = novo_status
        if novo_status != 'CONCLUIDO':
            sol.data_finalizacao = None
        sol.save(update_fields=[
            'quantidade_empenhada',
            'quantidade_movimentada',
            'status',
            'data_finalizacao',
        ])


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0048_ponto_restauracao_movimentacao'),
    ]

    operations = [
        migrations.RunPython(reconciliar, migrations.RunPython.noop),
    ]
