from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .access_control import has_direct_permission
from .status_solicitacao import status_automatico, evento_para_status, quantidade_comprometida, quantidade_empenhada_pendente, sincronizar_quantidades_reais
from .models import (
    ColunaKanban,
    Empenho,
    EmpenhoStatus,
    Estoque,
    HistoricoCard,
    HistoricoItemEmpenho,
    HistoricoMovimentacao,
    ItemEmpenho,
    PontoRestauracaoMovimentacao,
    Solicitacao,
    SolicitacaoItemCarga,
)


def _usuario_admin_operacional(user):
    """Admin funcional: superuser, staff ou administrador configurado no sistema."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    return (
        has_direct_permission(user, "sapp.pode_configuracoes")
        and has_direct_permission(user, "sapp.pode_gerenciar_usuarios")
    )


def admin_operacional_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _usuario_admin_operacional(request.user):
            return HttpResponseForbidden(
                "Esta área é exclusiva para administradores."
            )
        return view_func(request, *args, **kwargs)

    return wrapper


def _json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("JSON inválido.") from exc


def _decimal(value, nome="Valor"):
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{nome} inválido.") from exc


def _inteiro_positivo(value, nome="Quantidade"):
    numero = _decimal(value, nome)
    if numero <= 0 or numero != numero.to_integral_value():
        raise ValueError(f"{nome} deve ser um número inteiro maior que zero.")
    return int(numero)


def _nome_usuario(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def _status_rascunho():
    status, _ = EmpenhoStatus.objects.get_or_create(
        nome="Rascunho",
        defaults={"descricao": "Empenho em edição/movimentação"},
    )
    return status


def _obter_empenho_editavel(solicitacao, usuario):
    empenho = (
        Empenho.objects.filter(
            solicitacao=solicitacao,
            status__nome__iexact="Rascunho",
        )
        .order_by("id")
        .first()
    )
    if empenho:
        return empenho

    return Empenho.objects.create(
        solicitacao=solicitacao,
        usuario=usuario,
        status=_status_rascunho(),
        tipo_movimentacao=(
            "EXPEDICAO"
            if solicitacao.tipo_solicitacao == "CARGA"
            else "TRANSFERENCIA"
        ),
        observacao=f"Empenho administrativo da solicitação #{solicitacao.id}",
        numero_carga=(
            solicitacao.titulo
            if solicitacao.tipo_solicitacao == "CARGA"
            else None
        ),
        motorista=solicitacao.motorista or None,
        placa=solicitacao.placa or None,
        cliente=solicitacao.cliente or None,
    )


def _total_empenhado(solicitacao):
    itens = ItemEmpenho.objects.filter(
        empenho__solicitacao=solicitacao
    ).select_related("estoque")

    if solicitacao.unidade_controle == "QUILOGRAMA":
        total = Decimal("0")
        for item in itens:
            peso = Decimal(str(item.estoque.peso_unitario or 0))
            total += Decimal(str(item.quantidade or 0)) * peso
        return total

    total = itens.aggregate(total=Sum("quantidade"))["total"] or 0
    return Decimal(str(total))


def _recalcular_solicitacao(solicitacao, *, status_manual=None):
    """Reconstrói empenhado + movimentado pela verdade física e recalcula o status."""
    sincronizar_quantidades_reais(
        solicitacao,
        atualizar_status=(status_manual is None),
        persistir=False,
    )

    if status_manual:
        solicitacao.status = status_manual
    else:
        solicitacao.status = status_automatico(solicitacao)

    # Ao reabrir um concluído, a finalização corrente deixa de existir.
    # O histórico da conclusão anterior continua nos históricos do card.
    if solicitacao.status != "CONCLUIDO":
        solicitacao.data_finalizacao = None

    solicitacao.save(
        update_fields=[
            "quantidade_solicitada",
            "quantidade_empenhada",
            "quantidade_movimentada",
            "status",
            "data_finalizacao",
            "data_atualizacao",
        ]
    )
    cache.delete("cards_version_hash")
    return solicitacao


def _sincronizar_workflow_admin(solicitacao, usuario):
    """Move a coluna junto com o status automático, reutilizando o workflow normal."""
    evento = evento_para_status(solicitacao.status)
    if not evento:
        return
    try:
        # Import local evita dependência circular durante o carregamento das URLs.
        from .views import avaliar_workflow
        avaliar_workflow(solicitacao, evento, usuario)
    except Exception:
        # A correção administrativa não deve falhar apenas porque não há regra
        # de workflow configurada para o status resultante.
        return


def _registrar_admin(solicitacao, usuario, texto, *, lote=None, quantidade=None, unidade=None):
    HistoricoCard.objects.create(
        solicitacao=solicitacao,
        usuario=usuario,
        acao="EDICAO",
        lote=lote,
        quantidade=quantidade,
        unidade=unidade,
        observacao=f"[ADMIN] {texto}",
    )


def _snapshot_solicitacao(solicitacao):
    return {
        "id": solicitacao.id,
        "titulo": solicitacao.titulo,
        "tipo_solicitacao": solicitacao.tipo_solicitacao,
        "cliente": solicitacao.cliente or "",
        "destino": solicitacao.destino or "",
        "motorista": solicitacao.motorista or "",
        "placa": solicitacao.placa or "",
        "status": solicitacao.status,
        "status_display": solicitacao.get_status_display(),
        "quantidade_solicitada": str(solicitacao.quantidade_solicitada or 0),
        "quantidade_empenhada": str(solicitacao.quantidade_empenhada or 0),
        "quantidade_movimentada": str(solicitacao.quantidade_movimentada or 0),
        "unidade_controle": solicitacao.unidade_controle,
        "prioridade": solicitacao.prioridade,
        "coluna_kanban_id": solicitacao.coluna_kanban_id,
        "coluna_kanban": solicitacao.coluna_kanban.nome if solicitacao.coluna_kanban else "",
        "observacao": solicitacao.observacao or "",
    }


@admin_operacional_required
@require_GET
def painel_admin_empenhos(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()

    qs = (
        Solicitacao.objects.select_related(
            "criador", "responsavel", "coluna_kanban", "armazem"
        )
        .prefetch_related("empenhos__itens", "empenhos__historico_itens")
        .order_by("-data_atualizacao", "-id")
    )

    if q:
        qs = qs.filter(
            Q(titulo__icontains=q)
            | Q(cliente__icontains=q)
            | Q(destino__icontains=q)
            | Q(produto__icontains=q)
            | Q(empenhos__itens__lote__icontains=q)
            | Q(empenhos__historico_itens__lote__icontains=q)
        ).distinct()

    if status:
        qs = qs.filter(status=status)

    solicitacoes = list(qs[:250])

    return render(
        request,
        "sapp/admin_operacional_empenhos.html",
        {
            "solicitacoes": solicitacoes,
            "q": q,
            "status_filtro": status,
            "status_choices": Solicitacao.STATUS_CHOICES,
        },
    )


@admin_operacional_required
@require_GET
def detalhe_admin_empenho(request, solicitacao_id):
    solicitacao = get_object_or_404(
        Solicitacao.objects.select_related(
            "criador", "responsavel", "armazem", "especie", "coluna_kanban"
        ).prefetch_related("itens_carga"),
        pk=solicitacao_id,
    )

    # Repara contadores/metas legadas antes de exibir a Central Admin.
    sincronizar_quantidades_reais(
        solicitacao,
        atualizar_status=True,
        persistir=True,
    )

    empenho = (
        Empenho.objects.filter(solicitacao=solicitacao)
        .select_related("status", "usuario")
        .order_by("id")
        .first()
    )

    itens_pendentes = list(
        ItemEmpenho.objects.filter(empenho__solicitacao=solicitacao)
        .select_related("estoque", "item_carga", "empenho")
        .order_by("-data_criacao", "-id")
    )

    movimentacoes = list(
        HistoricoItemEmpenho.objects.filter(empenho__solicitacao=solicitacao)
        .select_related("estoque_origem", "estoque_destino", "processado_por")
        .order_by("-processado_em", "-id")[:150]
    )

    pontos_restauracao = list(
        PontoRestauracaoMovimentacao.objects.filter(solicitacao=solicitacao)
        .select_related("historico", "criado_por", "restaurado_por")
        .order_by("-criado_em", "-id")[:150]
    )

    destinos_cards = list(
        Solicitacao.objects.exclude(pk=solicitacao.pk)
        .order_by("-data_atualizacao")
        .values("id", "titulo", "status")[:300]
    )

    return render(
        request,
        "sapp/admin_operacional_empenho_detalhe.html",
        {
            "solicitacao": solicitacao,
            "empenho": empenho,
            "itens_pendentes": itens_pendentes,
            "movimentacoes": movimentacoes,
            "pontos_restauracao": pontos_restauracao,
            "quantidade_minima": quantidade_comprometida(solicitacao),
            "status_choices": Solicitacao.STATUS_CHOICES,
            "prioridade_choices": Solicitacao.PRIORIDADE_CHOICES,
            "unidade_choices": Solicitacao.UNIDADE_CHOICES,
            "colunas": ColunaKanban.objects.filter(ativa=True).order_by("ordem", "nome"),
            "empenho_status": EmpenhoStatus.objects.all().order_by("nome"),
            "itens_carga": solicitacao.itens_carga.all(),
            "destinos_cards": destinos_cards,
        },
    )


@admin_operacional_required
@require_GET
def api_admin_buscar_estoque(request):
    q = (request.GET.get("q") or "").strip()
    qs = Estoque.objects.select_related(
        "cultivar", "peneira", "categoria", "tratamento", "especie"
    ).order_by("lote", "endereco")

    if q:
        qs = qs.filter(
            Q(lote__icontains=q)
            | Q(produto__icontains=q)
            | Q(endereco__icontains=q)
            | Q(cliente__icontains=q)
            | Q(az__icontains=q)
        )
    else:
        qs = qs.filter(saldo__gt=0)

    resultados = []
    for estoque in qs[:80]:
        resultados.append(
            {
                "id": estoque.id,
                "lote": estoque.lote,
                "produto": estoque.produto or "",
                "endereco": estoque.endereco or "",
                "az": estoque.az or "",
                "saldo": estoque.saldo,
                "empenhado": estoque.empenhado,
                "disponivel": estoque.disponivel,
                "embalagem": estoque.embalagem or "",
                "cliente": estoque.cliente or "",
                "peso_unitario": str(estoque.peso_unitario or 0),
            }
        )

    return JsonResponse({"success": True, "resultados": resultados})


@admin_operacional_required
@require_POST
def api_admin_salvar_solicitacao(request, solicitacao_id):
    try:
        dados = _json(request)
        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            # A fonte da trava é o estado físico real, não contadores que possam
            # estar antigos: histórico movimentado + ItemEmpenho ainda pendente.
            sincronizar_quantidades_reais(
                solicitacao,
                atualizar_status=True,
                persistir=True,
            )
            minimo_meta_fisico = quantidade_comprometida(solicitacao)
            antes = _snapshot_solicitacao(solicitacao)

            campos_texto = {
                "titulo": "titulo",
                "cliente": "cliente",
                "destino": "destino",
                "motorista": "motorista",
                "placa": "placa",
                "observacao": "observacao",
            }
            for chave, campo in campos_texto.items():
                if chave in dados:
                    setattr(solicitacao, campo, str(dados.get(chave) or "").strip())

            if "tipo_solicitacao" in dados:
                valor = str(dados.get("tipo_solicitacao") or "").upper()
                validos = {v for v, _ in Solicitacao.TIPO_SOLICITACAO_CHOICES}
                if valor not in validos:
                    raise ValueError("Tipo de solicitação inválido.")
                solicitacao.tipo_solicitacao = valor

            if "unidade_controle" in dados:
                valor = str(dados.get("unidade_controle") or "").upper()
                validos = {v for v, _ in Solicitacao.UNIDADE_CHOICES}
                if valor not in validos:
                    raise ValueError("Unidade de controle inválida.")
                solicitacao.unidade_controle = valor

            if "prioridade" in dados:
                valor = str(dados.get("prioridade") or "").upper()
                validos = {v for v, _ in Solicitacao.PRIORIDADE_CHOICES}
                if valor not in validos:
                    raise ValueError("Prioridade inválida.")
                solicitacao.prioridade = valor

            if "quantidade_solicitada" in dados:
                valor = _decimal(dados.get("quantidade_solicitada"), "Quantidade solicitada")
                if valor < 0:
                    raise ValueError("Quantidade solicitada não pode ser negativa.")
                solicitacao.quantidade_solicitada = valor

            if "quantidade_movimentada" in dados:
                valor = _decimal(dados.get("quantidade_movimentada"), "Quantidade movimentada")
                if valor < 0:
                    raise ValueError("Quantidade movimentada não pode ser negativa.")
                solicitacao.quantidade_movimentada = valor

            # A meta nunca pode ficar abaixo do total fisicamente comprometido.
            # Ex.: 2 pendentes + 1 expedido => mínimo 3. Para baixar para 2, o
            # admin precisa primeiro desfazer a movimentação ou remover empenho.
            if (
                Decimal(str(solicitacao.quantidade_solicitada or 0)) > 0
                and Decimal(str(solicitacao.quantidade_solicitada or 0)) < minimo_meta_fisico
            ):
                raise ValueError(
                    f"Quantidade solicitada não pode ser menor que o total comprometido "
                    f"({minimo_meta_fisico}: movimentado + empenho pendente). "
                    "Desfaça primeiro a movimentação ou remova corretamente o empenho."
                )

            if "coluna_kanban_id" in dados:
                coluna_id = dados.get("coluna_kanban_id")
                if coluna_id in (None, "", 0, "0"):
                    solicitacao.coluna_kanban = None
                else:
                    solicitacao.coluna_kanban = ColunaKanban.objects.get(pk=int(coluna_id))

            status_manual = None
            if "status" in dados:
                status_recebido = str(dados.get("status") or "").upper()
                validos = {v for v, _ in Solicitacao.STATUS_CHOICES}
                if status_recebido not in validos:
                    raise ValueError("Status inválido.")
                # O formulário sempre envia o status atual. Só tratamos como
                # alteração manual quando o admin realmente escolheu outro.
                if status_recebido != str(antes.get("status") or "").upper():
                    status_manual = status_recebido
                    solicitacao.status = status_manual

            solicitacao.save()
            _recalcular_solicitacao(solicitacao, status_manual=status_manual)
            if not status_manual:
                _sincronizar_workflow_admin(solicitacao, request.user)

            depois = _snapshot_solicitacao(solicitacao)
            _registrar_admin(
                solicitacao,
                request.user,
                f"Solicitação editada. Antes: {antes}. Depois: {depois}.",
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Solicitação atualizada com sucesso.",
                "solicitacao": _snapshot_solicitacao(solicitacao),
            }
        )
    except Solicitacao.DoesNotExist:
        return JsonResponse({"success": False, "error": "Solicitação não encontrada."}, status=404)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_salvar_empenho(request, solicitacao_id):
    try:
        dados = _json(request)
        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            empenho = _obter_empenho_editavel(solicitacao, request.user)
            empenho = Empenho.objects.select_for_update().get(pk=empenho.pk)

            if "status_id" in dados and dados.get("status_id"):
                empenho.status = EmpenhoStatus.objects.get(pk=int(dados["status_id"]))

            if "tipo_movimentacao" in dados:
                tipo = str(dados.get("tipo_movimentacao") or "").upper()
                validos = {v for v, _ in Empenho._meta.get_field("tipo_movimentacao").choices}
                if tipo not in validos:
                    raise ValueError("Tipo de movimentação do empenho inválido.")
                empenho.tipo_movimentacao = tipo

            for campo in ("numero_carga", "motorista", "placa", "cliente", "ordem_entrega", "observacao"):
                if campo in dados:
                    setattr(empenho, campo, str(dados.get(campo) or "").strip())

            empenho.save()
            _registrar_admin(
                solicitacao,
                request.user,
                f"Dados do Empenho #{empenho.id} alterados pela Central Administrativa.",
            )

        return JsonResponse({"success": True, "message": "Empenho atualizado."})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_adicionar_lote(request, solicitacao_id):
    try:
        dados = _json(request)
        estoque_id = int(dados.get("estoque_id") or 0)
        quantidade = _inteiro_positivo(dados.get("quantidade"), "Quantidade")
        item_carga_id = dados.get("item_carga_id")

        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            status_anterior = solicitacao.status
            estoque = Estoque.objects.select_for_update().get(pk=estoque_id)
            empenho = _obter_empenho_editavel(solicitacao, request.user)
            empenho = Empenho.objects.select_for_update().get(pk=empenho.pk)

            item_carga = None
            if item_carga_id not in (None, "", 0, "0"):
                item_carga = SolicitacaoItemCarga.objects.get(
                    pk=int(item_carga_id), solicitacao=solicitacao
                )

            disponivel = Decimal(str(estoque.saldo or 0)) - Decimal(str(estoque.empenhado or 0))
            if Decimal(quantidade) > disponivel:
                raise ValueError(
                    f"Saldo disponível insuficiente no lote {estoque.lote}. Disponível: {disponivel}."
                )

            item = ItemEmpenho.objects.filter(
                empenho=empenho,
                estoque=estoque,
                item_carga=item_carga,
            ).first()

            if item:
                item.quantidade = int(item.quantidade or 0) + quantidade
                item.endereco_destino = solicitacao.destino or item.endereco_destino or ""
                item.save(update_fields=["quantidade", "endereco_destino"])
            else:
                item = ItemEmpenho.objects.create(
                    empenho=empenho,
                    estoque=estoque,
                    item_carga=item_carga,
                    quantidade=quantidade,
                    endereco_destino=solicitacao.destino or "",
                    cliente_solicitacao_snapshot=(
                        item_carga.cliente if item_carga else (solicitacao.cliente or "")
                    ),
                    codigo_produto_snapshot=(
                        item_carga.codigo if item_carga else (estoque.produto or "")
                    ),
                    descricao_produto_snapshot=(
                        item_carga.descricao if item_carga else ""
                    ),
                )

            # Se o admin adicionou acima da meta atual, a meta acompanha o
            # total realmente comprometido. Histórico movimentado nunca é zerado.
            emp_apos = _total_empenhado(solicitacao)
            mov_apos = Decimal(str(solicitacao.quantidade_movimentada or 0))
            solicitado = Decimal(str(solicitacao.quantidade_solicitada or 0))
            if solicitado > 0 and mov_apos + emp_apos > solicitado:
                solicitacao.quantidade_solicitada = mov_apos + emp_apos
                solicitacao.save(update_fields=["quantidade_solicitada", "data_atualizacao"])

            _recalcular_solicitacao(solicitacao)
            _sincronizar_workflow_admin(solicitacao, request.user)

            _registrar_admin(
                solicitacao,
                request.user,
                f"Adicionou {quantidade} unidade(s) do lote {estoque.lote} ao empenho."
                + (
                    f" O status foi recalculado para {solicitacao.status}."
                    if status_anterior == "CONCLUIDO"
                    else ""
                ),
                lote=estoque.lote,
                quantidade=quantidade,
                unidade=estoque.embalagem or "UN",
            )

        return JsonResponse(
            {
                "success": True,
                "message": f"Lote {estoque.lote} adicionado ao empenho.",
                "status": solicitacao.status,
                "quantidade_solicitada": str(solicitacao.quantidade_solicitada or 0),
                "quantidade_empenhada": str(solicitacao.quantidade_empenhada or 0),
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _trocar_estoque_item(item, novo_estoque, nova_quantidade):
    """Troca lote/estoque de um ItemEmpenho preservando a reserva corretamente."""
    estoque_antigo = Estoque.objects.select_for_update().get(pk=item.estoque_id)
    if novo_estoque.pk == estoque_antigo.pk:
        item.quantidade = nova_quantidade
        item.save(update_fields=["quantidade"])
        return item

    estoque_novo = Estoque.objects.select_for_update().get(pk=novo_estoque.pk)
    quantidade_antiga = int(item.quantidade or 0)

    disponivel_novo = int(estoque_novo.saldo or 0) - int(estoque_novo.empenhado or 0)
    if nova_quantidade > disponivel_novo:
        raise ValueError(
            f"Saldo disponível insuficiente no lote {estoque_novo.lote}. Disponível: {disponivel_novo}."
        )

    estoque_antigo.empenhado = max(0, int(estoque_antigo.empenhado or 0) - quantidade_antiga)
    estoque_antigo.save(update_fields=["empenhado"])

    estoque_novo.empenhado = int(estoque_novo.empenhado or 0) + nova_quantidade
    estoque_novo.save(update_fields=["empenhado"])

    ItemEmpenho.objects.filter(pk=item.pk).update(
        estoque=estoque_novo,
        quantidade=nova_quantidade,
        lote=estoque_novo.lote or "",
        endereco_origem=estoque_novo.endereco or "",
        az_origem=estoque_novo.az or "",
        cultivar=estoque_novo.cultivar.nome if estoque_novo.cultivar else "",
        peneira=estoque_novo.peneira.nome if estoque_novo.peneira else "",
        categoria=estoque_novo.categoria.nome if estoque_novo.categoria else "",
        produto_snapshot=estoque_novo.produto or "",
        especie_snapshot=estoque_novo.especie.nome if estoque_novo.especie else "",
        tratamento_snapshot=estoque_novo.tratamento.nome if estoque_novo.tratamento else "",
        embalagem_snapshot=estoque_novo.embalagem or "",
        empresa_snapshot=estoque_novo.empresa or "",
        cliente_snapshot=estoque_novo.cliente or "",
        peso_unitario_snapshot=estoque_novo.peso_unitario or 0,
        saldo_anterior=estoque_novo.saldo or 0,
    )
    return ItemEmpenho.objects.get(pk=item.pk)


@admin_operacional_required
@require_POST
def api_admin_editar_item(request, solicitacao_id, item_id):
    try:
        dados = _json(request)
        nova_quantidade = _inteiro_positivo(dados.get("quantidade"), "Quantidade")
        novo_estoque_id = int(dados.get("estoque_id") or 0)

        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            item = (
                ItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("estoque", "empenho")
                .get(pk=item_id, empenho__solicitacao=solicitacao)
            )
            lote_antigo = item.lote
            qtd_antiga = item.quantidade
            novo_estoque = Estoque.objects.get(pk=novo_estoque_id or item.estoque_id)
            item = _trocar_estoque_item(item, novo_estoque, nova_quantidade)
            item.endereco_destino = solicitacao.destino or item.endereco_destino or ""
            ItemEmpenho.objects.filter(pk=item.pk).update(
                endereco_destino=item.endereco_destino
            )

            emp_apos = _total_empenhado(solicitacao)
            mov_apos = Decimal(str(solicitacao.quantidade_movimentada or 0))
            solicitado = Decimal(str(solicitacao.quantidade_solicitada or 0))
            if solicitado > 0 and mov_apos + emp_apos > solicitado:
                solicitacao.quantidade_solicitada = mov_apos + emp_apos
                solicitacao.save(update_fields=["quantidade_solicitada", "data_atualizacao"])
            _recalcular_solicitacao(solicitacao)
            _sincronizar_workflow_admin(solicitacao, request.user)

            _registrar_admin(
                solicitacao,
                request.user,
                f"Item #{item.id} alterado de lote {lote_antigo} / qtd {qtd_antiga} para "
                f"lote {item.lote} / qtd {item.quantidade}.",
                lote=item.lote,
                quantidade=item.quantidade,
                unidade=item.estoque.embalagem or "UN",
            )

        return JsonResponse({"success": True, "message": "Item atualizado com sucesso."})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_remover_item(request, solicitacao_id, item_id):
    try:
        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            item = (
                ItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("estoque", "empenho")
                .get(pk=item_id, empenho__solicitacao=solicitacao)
            )
            lote = item.lote
            quantidade = item.quantidade
            unidade = item.estoque.embalagem or "UN"
            item.delete()
            _recalcular_solicitacao(solicitacao)
            _sincronizar_workflow_admin(solicitacao, request.user)
            _registrar_admin(
                solicitacao,
                request.user,
                f"Removeu o item #{item_id} do empenho sem bloqueio por status.",
                lote=lote,
                quantidade=quantidade,
                unidade=unidade,
            )

        return JsonResponse({"success": True, "message": f"Lote {lote} removido do empenho."})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_mover_item_card(request, solicitacao_id, item_id):
    try:
        dados = _json(request)
        destino_id = int(dados.get("solicitacao_destino_id") or 0)
        if not destino_id or destino_id == solicitacao_id:
            raise ValueError("Informe outro card de destino.")

        with transaction.atomic():
            origem_sol = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            destino_sol = Solicitacao.objects.select_for_update().get(pk=destino_id)
            item = (
                ItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("estoque", "empenho", "item_carga")
                .get(pk=item_id, empenho__solicitacao=origem_sol)
            )
            empenho_destino = _obter_empenho_editavel(destino_sol, request.user)

            existente = ItemEmpenho.objects.filter(
                empenho=empenho_destino,
                estoque_id=item.estoque_id,
                item_carga_id=None,
            ).first()

            lote = item.lote
            quantidade = item.quantidade
            if existente:
                # Os dois itens já fazem parte de Estoque.empenhado. Somamos as
                # quantidades via update() e removemos a linha de origem também
                # via queryset para não liberar/reservar o estoque duas vezes.
                nova_qtd = int(existente.quantidade or 0) + int(quantidade or 0)
                ItemEmpenho.objects.filter(pk=existente.pk).update(quantidade=nova_qtd)
                ItemEmpenho.objects.filter(pk=item.pk).delete()
            else:
                # update() evita tocar em Estoque.empenhado: a reserva já existe e
                # apenas muda de card.
                ItemEmpenho.objects.filter(pk=item.pk).update(
                    empenho=empenho_destino,
                    item_carga=None,
                    endereco_destino=destino_sol.destino or "",
                    cliente_solicitacao_snapshot=destino_sol.cliente or "",
                )

            _recalcular_solicitacao(origem_sol)
            _sincronizar_workflow_admin(origem_sol, request.user)

            emp_destino = _total_empenhado(destino_sol)
            mov_destino = Decimal(str(destino_sol.quantidade_movimentada or 0))
            solicitado_destino = Decimal(str(destino_sol.quantidade_solicitada or 0))
            if solicitado_destino > 0 and mov_destino + emp_destino > solicitado_destino:
                destino_sol.quantidade_solicitada = mov_destino + emp_destino
                destino_sol.save(update_fields=["quantidade_solicitada", "data_atualizacao"])
            _recalcular_solicitacao(destino_sol)
            _sincronizar_workflow_admin(destino_sol, request.user)

            _registrar_admin(
                origem_sol,
                request.user,
                f"Moveu o lote {lote} ({quantidade}) deste card para a solicitação #{destino_sol.id} - {destino_sol.titulo}.",
                lote=lote,
                quantidade=quantidade,
            )
            _registrar_admin(
                destino_sol,
                request.user,
                f"Recebeu o lote {lote} ({quantidade}) da solicitação #{origem_sol.id} - {origem_sol.titulo}.",
                lote=lote,
                quantidade=quantidade,
            )

        return JsonResponse({"success": True, "message": f"Lote movido para {destino_sol.titulo}."})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _remover_historicos_gerais_da_movimentacao(hist, ponto=None):
    """Remove os lançamentos gerais que pertencem à movimentação estornada."""
    removidos = []

    # Pontos criados pela V3 guardam os IDs exatos dos lançamentos gerais.
    # Isso evita apagar por engano outra movimentação do mesmo lote/quantidade
    # que tenha ocorrido quase no mesmo instante.
    ids_exatos = list(getattr(ponto, 'historicos_gerais_ids', None) or [])
    if ids_exatos:
        for mov in HistoricoMovimentacao.objects.filter(id__in=ids_exatos).order_by('id'):
            removidos.append(mov.id)
            mov.delete()
        return removidos

    # Compatibilidade com pontos/históricos antigos que não possuíam vínculo
    # explícito com o histórico geral.
    inicio = hist.processado_em - timedelta(seconds=60)
    fim = hist.processado_em + timedelta(seconds=5)

    if hist.tipo == "transferencia":
        candidatos = [
            (hist.estoque_origem_id, "Transferência (Saída)"),
            (hist.estoque_destino_id, "Transferência (Entrada)"),
        ]
    else:
        candidatos = [(hist.estoque_origem_id, "Expedição")]

    for estoque_id, tipo in candidatos:
        if not estoque_id:
            continue
        mov = (
            HistoricoMovimentacao.objects.filter(
                estoque_id=estoque_id,
                tipo=tipo,
                quantidade=hist.quantidade,
                data_hora__gte=inicio,
                data_hora__lte=fim,
            )
            .order_by("-data_hora", "-id")
            .first()
        )
        if mov:
            removidos.append(mov.id)
            mov.delete()
    return removidos


def _desfazer_historico_item(hist, usuario):
    solicitacao = hist.empenho.solicitacao
    if not solicitacao:
        raise ValueError("A movimentação não está vinculada a uma solicitação.")

    quantidade = int(hist.quantidade or 0)
    if quantidade <= 0:
        raise ValueError("A movimentação possui quantidade inválida.")

    origem = Estoque.objects.select_for_update().get(pk=hist.estoque_origem_id)
    destino = None
    if hist.estoque_destino_id:
        destino = Estoque.objects.select_for_update().get(pk=hist.estoque_destino_id)

    if hist.tipo == "transferencia":
        if not destino:
            raise ValueError("A transferência não possui estoque de destino para ser desfeita.")
        if int(destino.entrada or 0) < quantidade:
            raise ValueError(
                f"Não é possível desfazer sem corromper o estoque: a entrada atual do destino ({destino.entrada}) "
                f"é menor que a quantidade original ({quantidade})."
            )
        saldo_destino_apos = (
            int(destino.entrada or 0)
            - quantidade
            - int(destino.saida or 0)
        )
        if saldo_destino_apos < int(destino.empenhado or 0):
            raise ValueError(
                "A movimentação pode ser desfeita em qualquer status, mas este lote do destino "
                "já possui reserva posterior. Remova ou mova primeiro esse empenho para não deixar "
                "o estoque disponível negativo."
            )
        if int(origem.saida or 0) < quantidade:
            raise ValueError("A saída atual da origem é menor que a quantidade da movimentação.")

        destino.entrada = int(destino.entrada or 0) - quantidade
        destino.save()
        origem.saida = int(origem.saida or 0) - quantidade
        origem.save()
    else:
        if int(origem.saida or 0) < quantidade:
            raise ValueError("A saída atual do lote é menor que a quantidade da expedição.")
        origem.saida = int(origem.saida or 0) - quantidade
        origem.save()

    empenho = _obter_empenho_editavel(solicitacao, usuario)
    item_carga = None
    if hist.item_carga_id_original:
        item_carga = SolicitacaoItemCarga.objects.filter(
            pk=hist.item_carga_id_original,
            solicitacao=solicitacao,
        ).first()

    item = ItemEmpenho.objects.filter(
        empenho=empenho,
        estoque=origem,
        item_carga=item_carga,
    ).first()

    if item:
        item.quantidade = int(item.quantidade or 0) + quantidade
        item.save(update_fields=["quantidade"])
    else:
        item = ItemEmpenho.objects.create(
            empenho=empenho,
            estoque=origem,
            item_carga=item_carga,
            quantidade=quantidade,
            lote=hist.lote or origem.lote or "",
            endereco_origem=hist.endereco_origem or origem.endereco or "",
            endereco_destino=solicitacao.destino or "",
            cultivar=hist.cultivar or "",
            peneira=hist.peneira or "",
            categoria=hist.categoria or "",
            saldo_anterior=hist.saldo_anterior or origem.saldo or 0,
            produto_snapshot=hist.produto or origem.produto or "",
            especie_snapshot=hist.especie or "",
            tratamento_snapshot=hist.tratamento or "",
            embalagem_snapshot=hist.embalagem or origem.embalagem or "",
            empresa_snapshot=hist.empresa or origem.empresa or "",
            cliente_snapshot=hist.cliente or origem.cliente or "",
            cliente_solicitacao_snapshot=hist.cliente_solicitacao or solicitacao.cliente or "",
            codigo_produto_snapshot=hist.codigo_produto or origem.produto or "",
            descricao_produto_snapshot=hist.descricao_produto or "",
            az_origem=hist.az_origem or origem.az or "",
            peso_unitario_snapshot=hist.peso_unitario or origem.peso_unitario or 0,
            observacao_snapshot=hist.observacao_origem or "",
            conferente_snapshot=hist.conferente or "",
        )

    peso = Decimal(str(hist.peso_unitario or origem.peso_unitario or 0))
    if solicitacao.unidade_controle == "QUILOGRAMA":
        abatimento = Decimal(quantidade) * peso
    else:
        abatimento = Decimal(quantidade)

    solicitacao.quantidade_movimentada = max(
        Decimal("0"),
        Decimal(str(solicitacao.quantidade_movimentada or 0)) - abatimento,
    )

    ponto = PontoRestauracaoMovimentacao.objects.filter(historico_id=hist.id).first()
    ids_historicos = _remover_historicos_gerais_da_movimentacao(hist, ponto=ponto)
    lote = hist.lote
    tipo = hist.get_tipo_display()
    hist_id = hist.id
    hist.delete()

    # O lançamento original é retirado das métricas operacionais, mas criamos
    # um evento explícito de restauração. Além de deixar auditoria legível,
    # isso dispara o versionamento offline do lote e avisa outros dispositivos
    # de que o saldo físico mudou novamente.
    if tipo.lower().startswith("transfer"):
        HistoricoMovimentacao.objects.create(
            estoque=origem,
            usuario=usuario,
            quantidade=quantidade,
            tipo="Restauração de transferência",
            descricao=(
                f"Admin desfez a transferência #{hist_id}. "
                f"Quantidade {quantidade} retornou ao estoque de origem e ao empenho."
            ),
        )
        if destino:
            HistoricoMovimentacao.objects.create(
                estoque=destino,
                usuario=usuario,
                quantidade=quantidade,
                tipo="Restauração de transferência",
                descricao=(
                    f"Admin desfez a transferência #{hist_id}. "
                    f"Quantidade {quantidade} foi retirada do destino para recompor a origem."
                ),
            )
    else:
        HistoricoMovimentacao.objects.create(
            estoque=origem,
            usuario=usuario,
            quantidade=quantidade,
            tipo="Restauração de expedição",
            descricao=(
                f"Admin desfez a expedição #{hist_id}. "
                f"Quantidade {quantidade} retornou ao estoque e ao empenho."
            ),
        )

    _recalcular_solicitacao(solicitacao)
    _sincronizar_workflow_admin(solicitacao, usuario)

    if ponto:
        ponto.status = "RESTAURADO"
        ponto.restaurado_por = usuario
        ponto.restaurado_em = timezone.now()
        ponto.observacao_restauracao = (
            f"Movimentação #{hist_id} desfeita. Saldo físico e empenho reconstruídos."
        )
        ponto.save(update_fields=[
            "status", "restaurado_por", "restaurado_em", "observacao_restauracao"
        ])

    _registrar_admin(
        solicitacao,
        usuario,
        f"Desfez {tipo.lower()} do histórico #{hist_id}, lote {lote}, quantidade {quantidade}. "
        f"O item voltou ao empenho. Lançamentos gerais estornados: {ids_historicos or 'nenhum localizado'}.",
        lote=lote,
        quantidade=quantidade,
        unidade=("KG" if solicitacao.unidade_controle == "QUILOGRAMA" else (origem.embalagem or "UN")),
    )
    return solicitacao, item


@admin_operacional_required
@require_POST
def api_admin_desfazer_movimentacao(request, solicitacao_id, historico_id):
    try:
        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            hist = (
                HistoricoItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("empenho", "estoque_origem", "estoque_destino")
                .get(pk=historico_id, empenho__solicitacao=solicitacao)
            )
            solicitacao, item = _desfazer_historico_item(hist, request.user)

        return JsonResponse(
            {
                "success": True,
                "message": f"Movimentação desfeita. O lote {item.lote} voltou ao empenho.",
                "status": solicitacao.status,
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_desfazer_ultima_movimentacao(request, solicitacao_id):
    try:
        with transaction.atomic():
            solicitacao = Solicitacao.objects.select_for_update().get(pk=solicitacao_id)
            hist = (
                HistoricoItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("empenho", "estoque_origem", "estoque_destino")
                .filter(empenho__solicitacao=solicitacao)
                .order_by("-processado_em", "-id")
                .first()
            )
            if not hist:
                raise ValueError("Esta solicitação não possui movimentação para desfazer.")
            solicitacao, item = _desfazer_historico_item(hist, request.user)

        return JsonResponse(
            {
                "success": True,
                "message": f"Última movimentação desfeita. O lote {item.lote} voltou ao empenho.",
                "status": solicitacao.status,
            }
        )
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)


@admin_operacional_required
@require_POST
def api_admin_restaurar_ponto(request, ponto_id):
    """Restaura uma movimentação pelo ponto automático, somente para admin."""
    try:
        with transaction.atomic():
            ponto = (
                PontoRestauracaoMovimentacao.objects.select_for_update(of=("self",))
                .select_related("historico__empenho__solicitacao")
                .get(pk=ponto_id)
            )
            if ponto.status != "DISPONIVEL":
                raise ValueError("Este ponto de restauração já foi utilizado ou não está disponível.")
            if not ponto.historico_id:
                raise ValueError("O histórico original deste ponto não está mais disponível.")

            hist = (
                HistoricoItemEmpenho.objects.select_for_update(of=("self",))
                .select_related("empenho", "estoque_origem", "estoque_destino")
                .get(pk=ponto.historico_id)
            )
            solicitacao, item = _desfazer_historico_item(hist, request.user)

        return JsonResponse({
            "success": True,
            "message": f"Ponto #{ponto_id} restaurado. O lote {item.lote} voltou ao empenho.",
            "status": solicitacao.status,
        })
    except PontoRestauracaoMovimentacao.DoesNotExist:
        return JsonResponse({"success": False, "error": "Ponto de restauração não encontrado."}, status=404)
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
