import re

from django.db import migrations


def corrigir_quantidades_entrada(apps, schema_editor):
    """Repara entradas antigas criadas pelo formulário com quantidade=0.

    O bug anterior gravava corretamente a quantidade no Estoque, mas não passava
    `quantidade` ao HistoricoMovimentacao. A descrição gerada por esse fluxo é
    estável: "Entrada de X unidades...". Só corrigimos registros do tipo exato
    "Entrada" com quantidade zero e com esse padrão explícito, evitando inferir
    valores em outros tipos de histórico.
    """
    HistoricoMovimentacao = apps.get_model('sapp', 'HistoricoMovimentacao')

    qs = HistoricoMovimentacao.objects.filter(
        tipo__iexact='Entrada',
        quantidade=0,
    ).only('id', 'descricao', 'quantidade')

    for historico in qs.iterator():
        descricao = historico.descricao or ''
        match = re.search(r'Entrada\s+de\s+(\d+)\s+unidades', descricao, re.IGNORECASE)
        if not match:
            continue

        quantidade = int(match.group(1))
        if quantidade <= 0:
            continue

        HistoricoMovimentacao.objects.filter(pk=historico.pk).update(
            quantidade=quantidade
        )


class Migration(migrations.Migration):

    dependencies = [
        ('sapp', '0040_solicitacao_placa'),
    ]

    operations = [
        migrations.RunPython(
            corrigir_quantidades_entrada,
            migrations.RunPython.noop,
        ),
    ]
