from decimal import Decimal


def _dec(valor):
    return Decimal(str(valor or 0))


def quantidade_empenhada_pendente(solicitacao):
    """Reserva que ainda existe fisicamente no empenho, na unidade do card."""
    return _dec(solicitacao.quantidade_empenhada)


def quantidade_comprometida(solicitacao):
    """Movimentado histórico + reserva ainda pendente."""
    return _dec(solicitacao.quantidade_movimentada) + quantidade_empenhada_pendente(solicitacao)


def status_automatico(solicitacao):
    """
    Define o status pelo estado real do card.

    Regras importantes:
    - aumentar um card já concluído não apaga o histórico movimentado;
    - se ainda falta quantidade e não há reserva pendente, volta para AGUARDANDO_EMPENHO;
    - CONCLUIDO só ocorre quando a meta foi movimentada e não há reserva pendente;
    - o que já foi movimentado e o que ainda está reservado nunca são confundidos.
    """
    solicitado = _dec(solicitacao.quantidade_solicitada)
    empenhado = _dec(solicitacao.quantidade_empenhada)
    movimentado = _dec(solicitacao.quantidade_movimentada)

    # Carga aberta: não existe uma meta finita. Mantém a semântica antiga,
    # mas sem apagar o histórico quando existe movimentação parcial.
    if solicitado <= 0:
        if empenhado > 0 and movimentado > 0:
            return 'MOVIMENTACAO_PARCIAL'
        if empenhado > 0:
            return 'EMPENHO_COMPLETO'
        if movimentado > 0:
            return 'CONCLUIDO'
        return 'AGUARDANDO_EMPENHO'

    # Meta finita: concluído somente quando tudo foi fisicamente movimentado
    # e não restou nenhum lote reservado para sair/transferir.
    if movimentado >= solicitado and empenhado <= 0:
        return 'CONCLUIDO'

    restante_para_movimentar = max(Decimal('0'), solicitado - movimentado)

    # Ex.: concluído 10/10 foi aumentado para 12. O histórico 10 permanece,
    # mas faltam novos lotes. O card deve voltar para Aguardando Empenho.
    if empenhado <= 0:
        return 'AGUARDANDO_EMPENHO'

    # Há reserva, mas ainda não cobre o restante da nova meta.
    if empenhado < restante_para_movimentar:
        return 'EMPENHO_PARCIAL'

    # Todo o restante está reservado. Se já houve saída anterior, o ciclo está
    # em movimentação parcial; se ainda não houve saída, está com empenho completo.
    if movimentado > 0:
        return 'MOVIMENTACAO_PARCIAL'

    return 'EMPENHO_COMPLETO'


def evento_para_status(status):
    return {
        'AGUARDANDO_EMPENHO': 'CRIACAO',
        'EMPENHO_PARCIAL': 'EMPENHO_PARCIAL',
        'EMPENHO_COMPLETO': 'EMPENHO_COMPLETO',
        'MOVIMENTACAO_PARCIAL': 'MOVIMENTACAO_PARCIAL',
        'CONCLUIDO': 'CONCLUSAO',
    }.get(str(status or '').upper())



def quantidades_reais(solicitacao):
    """
    Reconstrói os contadores a partir da verdade física do módulo:

    - empenhado = ItemEmpenho que ainda existe (reserva pendente);
    - movimentado = HistoricoItemEmpenho ainda válido (transferência/expedição).

    Movimentações desfeitas são removidas de HistoricoItemEmpenho pelo fluxo de
    restauração, portanto deixam naturalmente de compor o total.
    """
    from django.db.models import Sum
    from .models import ItemEmpenho, HistoricoItemEmpenho

    itens = (
        ItemEmpenho.objects
        .filter(empenho__solicitacao_id=solicitacao.id)
        .select_related('estoque')
    )
    historicos = (
        HistoricoItemEmpenho.objects
        .filter(empenho__solicitacao_id=solicitacao.id)
        .exclude(tipo='removido')
        .select_related('estoque_origem')
    )

    if solicitacao.unidade_controle == 'QUILOGRAMA':
        empenhado = Decimal('0')
        for item in itens:
            peso = _dec(
                getattr(item, 'peso_unitario_snapshot', 0)
                or getattr(item.estoque, 'peso_unitario', 0)
                or 0
            )
            empenhado += _dec(item.quantidade) * peso

        movimentado = Decimal('0')
        for hist in historicos:
            peso = _dec(
                getattr(hist, 'peso_unitario', 0)
                or getattr(hist.estoque_origem, 'peso_unitario', 0)
                or 0
            )
            movimentado += _dec(hist.quantidade) * peso
    else:
        empenhado = _dec(
            itens.aggregate(total=Sum('quantidade'))['total'] or 0
        )
        movimentado = _dec(
            historicos.aggregate(total=Sum('quantidade'))['total'] or 0
        )

    return empenhado, movimentado


def sincronizar_quantidades_reais(
    solicitacao,
    *,
    atualizar_status=True,
    persistir=True,
):
    """
    Corrige contadores legados/stale sem inventar movimentação.

    Retorna (empenhado, movimentado, status_calculado). O status só é salvo
    quando ``atualizar_status`` for True. A data de finalização não é criada
    aqui, porque uma reconciliação não deve fingir que concluiu o card agora.
    """
    empenhado, movimentado = quantidades_reais(solicitacao)

    solicitacao.quantidade_empenhada = empenhado
    solicitacao.quantidade_movimentada = movimentado

    # Invariante operacional: uma meta finita nunca pode ficar abaixo do que
    # já está fisicamente comprometido (movimentado no histórico + reserva
    # ainda pendente). Isso também repara cards antigos que ficaram, por
    # exemplo, com 2 solicitados apesar de já existirem 2 pendentes + 1
    # expedido. Cargas abertas (quantidade 0) continuam abertas.
    solicitado = _dec(solicitacao.quantidade_solicitada)
    comprometido = empenhado + movimentado
    quantidade_corrigida = False
    if solicitado > 0 and comprometido > solicitado:
        solicitacao.quantidade_solicitada = comprometido
        quantidade_corrigida = True

    status_calculado = (
        status_automatico(solicitacao)
        if atualizar_status
        else solicitacao.status
    )

    if atualizar_status:
        solicitacao.status = status_calculado
        if status_calculado != 'CONCLUIDO':
            solicitacao.data_finalizacao = None

    if persistir:
        campos = ['quantidade_empenhada', 'quantidade_movimentada']
        if quantidade_corrigida:
            campos.append('quantidade_solicitada')
        if atualizar_status:
            campos.extend(['status', 'data_finalizacao'])
        solicitacao.save(update_fields=campos)

    return empenhado, movimentado, status_calculado
