from django.db import migrations


def _sigla_embalagem(valor):
    texto = str(valor or '').strip().upper()
    if texto in {'SC', 'SACO', 'SACOS'}:
        return 'SC'
    if texto in {'BAG', 'BAGS', 'BIG BAG', 'BIGBAG'}:
        return 'BAG'
    return texto


def _tratamento(valor):
    texto = ' '.join(str(valor or '').strip().split()).upper()
    if texto in {
        '', 'S/T', 'ST', 'SEM TRATAMENTO', 'SEM TRAT.',
        'SEM TRAT', 'NAO TRATADO', 'NÃO TRATADO',
    }:
        return 'S/T'
    return texto


def _montar(especie='', cultivar='', embalagem='', tratamento=''):
    especie = ' '.join(str(especie or '').strip().split()).upper()
    cultivar = ' '.join(str(cultivar or '').strip().split()).upper()
    embalagem = _sigla_embalagem(embalagem)
    tratamento = _tratamento(tratamento)
    if not any((especie, cultivar, embalagem)):
        return ''
    partes = ['SEM.']
    if especie:
        partes.append(especie)
    if cultivar:
        partes.append(cultivar)
    if embalagem:
        partes.append(embalagem)
    partes.append(tratamento or 'S/T')
    descricao = ' '.join(partes).strip()
    if not descricao.endswith('.'):
        descricao += '.'
    return descricao


def preencher_descricoes(apps, schema_editor):
    Produto = apps.get_model('sapp', 'Produto')
    Estoque = apps.get_model('sapp', 'Estoque')
    ItemEmpenho = apps.get_model('sapp', 'ItemEmpenho')
    HistoricoItemEmpenho = apps.get_model('sapp', 'HistoricoItemEmpenho')
    SolicitacaoItemCarga = apps.get_model('sapp', 'SolicitacaoItemCarga')
    HistoricoCard = apps.get_model('sapp', 'HistoricoCard')

    produtos = {
        str(codigo or '').strip().upper(): str(descricao or '').strip()
        for codigo, descricao in Produto.objects.exclude(codigo='').values_list('codigo', 'descricao')
        if str(descricao or '').strip()
    }

    def descricao_estoque(estoque):
        if not estoque:
            return ''
        codigo = str(getattr(estoque, 'produto', '') or '').strip().upper()
        if codigo and produtos.get(codigo):
            return produtos[codigo]
        return _montar(
            getattr(getattr(estoque, 'especie', None), 'nome', ''),
            getattr(getattr(estoque, 'cultivar', None), 'nome', ''),
            getattr(estoque, 'embalagem', ''),
            getattr(getattr(estoque, 'tratamento', None), 'nome', ''),
        )

    # Snapshots ativos.
    itens = (
        ItemEmpenho.objects
        .filter(descricao_produto_snapshot='')
        .select_related('estoque', 'estoque__especie', 'estoque__cultivar', 'estoque__tratamento')
    )
    for item in itens.iterator(chunk_size=300):
        codigo = str(item.codigo_produto_snapshot or item.produto_snapshot or '').strip().upper()
        descricao = produtos.get(codigo, '') or descricao_estoque(item.estoque)
        if descricao:
            ItemEmpenho.objects.filter(pk=item.pk).update(descricao_produto_snapshot=descricao)

    # Histórico já concluído.
    historicos = HistoricoItemEmpenho.objects.filter(descricao_produto='')
    for hist in historicos.iterator(chunk_size=300):
        codigo = str(hist.codigo_produto or hist.produto or '').strip().upper()
        descricao = produtos.get(codigo, '') or _montar(
            hist.especie,
            hist.cultivar,
            hist.embalagem,
            hist.tratamento,
        )
        if descricao:
            HistoricoItemEmpenho.objects.filter(pk=hist.pk).update(descricao_produto=descricao)

    # Linhas de solicitação/carga antigas. Prioriza Produto; depois item ativo;
    # depois histórico; por fim procura o lote salvo na própria linha.
    linhas = SolicitacaoItemCarga.objects.filter(descricao='')
    for linha in linhas.iterator(chunk_size=200):
        codigo = str(linha.codigo or '').strip().upper()
        descricao = produtos.get(codigo, '')

        if not descricao:
            item = (
                ItemEmpenho.objects
                .filter(item_carga_id=linha.pk)
                .select_related('estoque', 'estoque__especie', 'estoque__cultivar', 'estoque__tratamento')
                .order_by('id')
                .first()
            )
            if item:
                descricao = str(item.descricao_produto_snapshot or '').strip() or descricao_estoque(item.estoque)

        if not descricao:
            hist = (
                HistoricoItemEmpenho.objects
                .filter(item_carga_id_original=linha.pk)
                .order_by('-processado_em', '-id')
                .first()
            )
            if hist:
                descricao = str(hist.descricao_produto or '').strip() or _montar(
                    hist.especie,
                    hist.cultivar,
                    hist.embalagem,
                    hist.tratamento,
                )

        if not descricao and str(linha.lote or '').strip():
            estoque = (
                Estoque.objects
                .filter(lote__iexact=str(linha.lote).strip())
                .select_related('especie', 'cultivar', 'tratamento')
                .order_by('-id')
                .first()
            )
            descricao = descricao_estoque(estoque)

        if descricao:
            SolicitacaoItemCarga.objects.filter(pk=linha.pk).update(descricao=descricao)

    # Versões antigas gravavam EMPENHO como BAG fixo. Corrige somente quando
    # todos os registros rastreáveis daquele lote/card confirmam que era SC.
    historicos_card = HistoricoCard.objects.filter(acao='EMPENHO', unidade='BAG')
    for card in historicos_card.iterator(chunk_size=300):
        lote = str(card.lote or '').strip()
        if not lote:
            continue
        embalagens = set(
            str(v or '').strip().upper()
            for v in ItemEmpenho.objects.filter(
                empenho__solicitacao_id=card.solicitacao_id,
                lote__iexact=lote,
            ).values_list('embalagem_snapshot', flat=True)
            if str(v or '').strip()
        )
        embalagens.update(
            str(v or '').strip().upper()
            for v in HistoricoItemEmpenho.objects.filter(
                empenho__solicitacao_id=card.solicitacao_id,
                lote__iexact=lote,
            ).values_list('embalagem', flat=True)
            if str(v or '').strip()
        )
        embalagens = {_sigla_embalagem(v) for v in embalagens if _sigla_embalagem(v)}
        if embalagens == {'SC'}:
            HistoricoCard.objects.filter(pk=card.pk).update(unidade='SC')


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0046_sincronizar_descricao_expedicoes'),
    ]

    operations = [
        migrations.RunPython(preencher_descricoes, migrations.RunPython.noop),
    ]
