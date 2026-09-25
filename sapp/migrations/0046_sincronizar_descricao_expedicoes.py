import re
from django.db import migrations


def sincronizar_descricao_expedicoes(apps, schema_editor):
    HistoricoMovimentacao = apps.get_model('sapp', 'HistoricoMovimentacao')

    padrao = re.compile(
        r'(\bExpedido\s+)\d+(?:[\.,]\d+)?\s+(?:un|BAG|SC)\b',
        re.IGNORECASE,
    )

    qs = (
        HistoricoMovimentacao.objects
        .filter(tipo__icontains='Expedi')
        .select_related('estoque')
        .only('id', 'quantidade', 'descricao', 'estoque__embalagem')
    )

    for historico in qs.iterator(chunk_size=500):
        descricao = str(historico.descricao or '')
        if not descricao or not padrao.search(descricao):
            continue

        unidade = 'UN'
        if historico.estoque_id and historico.estoque:
            unidade = str(historico.estoque.embalagem or 'UN').upper()

        quantidade = int(historico.quantidade or 0)
        nova_descricao = padrao.sub(
            lambda match: f'{match.group(1)}{quantidade} {unidade}',
            descricao,
            count=1,
        )
        if nova_descricao != descricao:
            HistoricoMovimentacao.objects.filter(pk=historico.pk).update(
                descricao=nova_descricao
            )


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0045_normalizar_acessos_usuarios'),
    ]

    operations = [
        migrations.RunPython(
            sincronizar_descricao_expedicoes,
            migrations.RunPython.noop,
        ),
    ]
