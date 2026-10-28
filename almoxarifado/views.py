import json
import csv
import io
import logging
from functools import wraps
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sapp.access_control import has_any_direct_permission
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q, Sum, Count, F, OuterRef, Subquery, Case, When, Value, IntegerField
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import (
    Item, Saida, CarrinhoSolicitacao, Departamento, UnidadeMedida,
    EntradaNotaFiscal, ItemEntrada, DadosValidadeItem
)
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


def parse_decimal(value, default=None):
    if value is None or str(value).strip() == '':
        return default
    try:
        val_str = str(value).strip().replace(',', '.')
        d = Decimal(val_str)
        d = d.normalize()
        return d
    except (InvalidOperation, ValueError):
        return default


def _tem_acesso_almoxarifado(user, gerenciar=False):
    if gerenciar:
        return has_any_direct_permission(user, 'almoxarifado.pode_gerenciar_almoxarifado')
    return has_any_direct_permission(
        user,
        'almoxarifado.pode_ver_almoxarifado',
        'almoxarifado.pode_gerenciar_almoxarifado',
    )


def almoxarifado_access_required(*, gerenciar=False):
    """Protege as views do app sem depender apenas do menu/middleware."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not _tem_acesso_almoxarifado(request.user, gerenciar=gerenciar):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _carrinho_usuario(request):
    """Identificador estável por usuário. Evita carrinho compartilhado como 'anonimo'."""
    return request.user.username


# ============================
# VIEWS PRINCIPAIS
# ============================

@almoxarifado_access_required()
def lista_itens(request):
    mostrar_todos = request.GET.get('todos', '0') == '1'
    filtro_status = request.GET.get('status', '')
    ordenar = request.GET.get('ordenar', 'vencimento')  # padrão vencimento

    itens = Item.objects.filter(ativo=True).select_related('dados_validade')
    hoje = timezone.localdate()

    # Anotar dados de validade
    validade_subquery = DadosValidadeItem.objects.filter(item=OuterRef('id'))
    itens = itens.annotate(
        data_vencimento=Subquery(validade_subquery.values('data_vencimento')[:1]),
        data_fabricacao=Subquery(validade_subquery.values('data_fabricacao')[:1]),
    )

    # Filtros de status (incluindo vencimento)
    if filtro_status == 'zerados':
        itens = itens.filter(quantidade__lte=0)
    elif filtro_status == 'baixo':
        itens = itens.filter(quantidade__gt=0, quantidade__lte=F('estoque_minimo'))
    elif filtro_status == 'vencidos':
        itens = itens.filter(data_vencimento__lt=hoje)
    elif filtro_status == 'proximos':
        itens = itens.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=30)
        )

    if not mostrar_todos:
        itens = itens.filter(quantidade__gt=0)

    busca = request.GET.get('busca', '')
    if busca:
        itens = itens.filter(
            Q(nome__icontains=busca) |
            Q(codigo__icontains=busca) |
            Q(localizacao__icontains=busca) |
            Q(fornecedor__icontains=busca) |
            Q(lote__icontains=busca) |
            Q(ca__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(marca__icontains=busca)
        )

    departamento = request.GET.get('departamento', '')
    if departamento:
        itens = itens.filter(departamento=departamento)

    # ===== ORDENAÇÃO COM NULLS LAST =====
    if ordenar == 'vencimento':
        itens = itens.order_by(
            Case(
                When(data_vencimento__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            F('data_vencimento').asc(nulls_last=True)
        )
    elif ordenar == '-vencimento':
        itens = itens.order_by(
            Case(
                When(data_vencimento__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            F('data_vencimento').desc(nulls_last=True)
        )
    else:
        ordenacao_map = {
            'nome': 'nome',
            '-quantidade': '-quantidade',
            'quantidade': 'quantidade',
            'recente': '-updated_at',
        }
        itens = itens.order_by(ordenacao_map.get(ordenar, 'nome'))

    usuario = _carrinho_usuario(request)
    carrinho_count = CarrinhoSolicitacao.objects.filter(usuario=usuario).count()

    # Totais da listagem em uma única consulta.
    totais = itens.aggregate(total_itens=Count('id'), total_quantidade=Sum('quantidade'))
    total_itens = totais['total_itens'] or 0
    total_quantidade = totais['total_quantidade'] or 0

    # Cards de estoque em duas consultas agregadas, evitando vários COUNT separados.
    status_totais = Item.objects.filter(ativo=True).aggregate(
        zerados=Count('id', filter=Q(quantidade__lte=0)),
        baixo=Count('id', filter=Q(quantidade__gt=0, quantidade__lte=F('estoque_minimo'))),
    )
    validade_totais = DadosValidadeItem.objects.filter(item__ativo=True).aggregate(
        vencidos=Count('id', filter=Q(data_vencimento__lt=hoje)),
        proximos=Count('id', filter=Q(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=30),
        )),
    )
    zerados_count = status_totais['zerados'] or 0
    baixo_count = status_totais['baixo'] or 0
    vencidos_count = validade_totais['vencidos'] or 0
    proximos_count = validade_totais['proximos'] or 0

    context = {
        'itens': itens,
        'busca': busca,
        'departamento': departamento,
        'mostrar_todos': mostrar_todos,
        'ordenar': ordenar,
        'departamentos': Departamento.choices,
        'unidades': UnidadeMedida.choices,
        'total_itens': total_itens,
        'total_quantidade': total_quantidade,
        'carrinho_count': carrinho_count,
        'zerados_count': zerados_count,
        'baixo_count': baixo_count,
        'vencidos_count': vencidos_count,
        'proximos_count': proximos_count,
        'filtro_status': filtro_status,
    }
    return render(request, 'almoxarifado/lista_itens.html', context)


@almoxarifado_access_required()
@require_http_methods(["GET"])
def buscar_itens_ajax(request):
    busca = request.GET.get('busca', '').strip()[:120]
    departamento = request.GET.get('departamento', '')
    mostrar_todos = request.GET.get('todos', '0') == '1'
    ordenar = request.GET.get('ordenar', 'vencimento')
    filtro_status = request.GET.get('status', '')

    itens = Item.objects.filter(ativo=True)
    hoje = timezone.localdate()
    validade_subquery = DadosValidadeItem.objects.filter(item=OuterRef('id'))
    itens = itens.annotate(
        data_vencimento=Subquery(validade_subquery.values('data_vencimento')[:1]),
        data_fabricacao=Subquery(validade_subquery.values('data_fabricacao')[:1]),
    )

    if filtro_status == 'zerados':
        itens = itens.filter(quantidade__lte=0)
    elif filtro_status == 'baixo':
        itens = itens.filter(quantidade__gt=0, quantidade__lte=F('estoque_minimo'))
    elif filtro_status == 'vencidos':
        itens = itens.filter(data_vencimento__lt=hoje)
    elif filtro_status == 'proximos':
        itens = itens.filter(data_vencimento__gte=hoje, data_vencimento__lte=hoje + timedelta(days=30))

    if not mostrar_todos:
        itens = itens.filter(quantidade__gt=0)
    if busca:
        itens = itens.filter(
            Q(nome__icontains=busca) | Q(codigo__icontains=busca) |
            Q(localizacao__icontains=busca) | Q(fornecedor__icontains=busca) |
            Q(lote__icontains=busca) | Q(ca__icontains=busca)
        )
    if departamento:
        itens = itens.filter(departamento=departamento)

    if ordenar == 'vencimento':
        itens = itens.order_by(
            Case(When(data_vencimento__isnull=True, then=Value(1)), default=Value(0), output_field=IntegerField()),
            F('data_vencimento').asc(nulls_last=True)
        )
    elif ordenar == '-vencimento':
        itens = itens.order_by(
            Case(When(data_vencimento__isnull=True, then=Value(1)), default=Value(0), output_field=IntegerField()),
            F('data_vencimento').desc(nulls_last=True)
        )
    else:
        itens = itens.order_by({
            'nome': 'nome', '-quantidade': '-quantidade',
            'quantidade': 'quantidade', 'recente': '-updated_at',
        }.get(ordenar, 'nome'))

    data = {'itens': [{
        'id': i.id,
        'codigo': i.codigo,
        'nome': i.nome,
        'quantidade': float(i.quantidade),
        'unidade': i.get_unidade_display(),
        'localizacao': i.localizacao or '-',
        'departamento': i.get_departamento_display(),
        'status_estoque': i.status_estoque,
        'lote': i.lote or '-',
        'ca': i.ca or '-',
        'tamanho': i.tamanho or '-',
        'data_fabricacao': i.data_fabricacao.strftime('%Y-%m-%d') if i.data_fabricacao else None,
        'data_vencimento': i.data_vencimento.strftime('%Y-%m-%d') if i.data_vencimento else None,
        'dias_para_vencer': (i.data_vencimento - hoje).days if i.data_vencimento else None,
        'status_vencimento': (
            'vencido' if (i.data_vencimento and (i.data_vencimento - hoje).days < 0) else
            'proximo' if (i.data_vencimento and (i.data_vencimento - hoje).days <= 30) else
            'em_dia' if i.data_vencimento else 'sem_data'
        ),
    } for i in itens]}
    return JsonResponse(data)


@almoxarifado_access_required()
@require_http_methods(["GET"])
def saidas_list(request):
    saidas = Saida.objects.select_related('item').all().order_by('-data', '-hora')
    busca = request.GET.get('busca', '').strip()[:120]
    if busca:
        saidas = saidas.filter(
            Q(solicitante__icontains=busca) |
            Q(item_nome__icontains=busca) |
            Q(item_codigo__icontains=busca)
        )
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        saidas = saidas.filter(data__gte=data_inicio)
    if data_fim:
        saidas = saidas.filter(data__lte=data_fim)
    dept = request.GET.get('dept', '')
    if dept:
        saidas = saidas.filter(departamento=dept)
    total_saidas = saidas.count()
    total_retirado = saidas.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    return render(request, 'almoxarifado/saidas_list.html', {
        'saidas': saidas, 'busca': busca, 'data_inicio': data_inicio,
        'data_fim': data_fim, 'dept': dept, 'departamentos': Departamento.choices,
        'total_saidas': total_saidas, 'total_retirado': total_retirado,
    })



@almoxarifado_access_required()
@require_http_methods(["GET"])
def buscar_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()[:20]
    if not codigo:
        return JsonResponse({'encontrado': False})
    item = Item.objects.filter(codigo=codigo, ativo=True).first()
    if not item:
        return JsonResponse({'encontrado': False})
    return JsonResponse({'encontrado': True, 'item': {
        'id': item.id, 'codigo': item.codigo, 'nome': item.nome,
        'descricao': item.descricao, 'departamento': item.departamento,
        'unidade': item.unidade, 'localizacao': item.localizacao,
        'estoque_minimo': float(item.estoque_minimo),
        'fornecedor': item.fornecedor, 'quantidade': float(item.quantidade),
        'lote': item.lote, 'ca': item.ca, 'categoria': item.categoria,
        'marca': item.marca, 'tamanho': item.tamanho,
    }})


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def adicionar_item(request):
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome obrigatório'}, status=400)

        codigo = request.POST.get('codigo', '').strip() or None
        quantidade = parse_decimal(request.POST.get('quantidade', '0'), Decimal('0'))
        estoque_minimo = parse_decimal(request.POST.get('estoque_minimo', '5'), Decimal('5'))
        if quantidade is None or quantidade < 0:
            return JsonResponse({'success': False, 'error': 'Quantidade não pode ser negativa.'}, status=400)
        if estoque_minimo is None or estoque_minimo < 0:
            return JsonResponse({'success': False, 'error': 'Estoque mínimo não pode ser negativo.'}, status=400)

        lote = request.POST.get('lote', '').strip() or None
        ca = request.POST.get('ca', '').strip() or None
        localizacao = request.POST.get('localizacao', '').strip() or None
        tamanho = request.POST.get('tamanho', '').strip() or None

        with transaction.atomic():
            if codigo:
                item_existente = Item.objects.select_for_update().filter(
                    codigo=codigo, lote=lote, ca=ca, localizacao=localizacao
                ).first()
                if item_existente:
                    if request.POST.get('somar', 'false') == 'true':
                        item_existente.quantidade += quantidade
                        item_existente.ativo = True
                        item_existente.save(update_fields=['quantidade', 'ativo', 'updated_at'])
                        return JsonResponse({
                            'success': True,
                            'message': f'Quantidade somada! Total: {float(item_existente.quantidade)} {item_existente.get_unidade_display()}'
                        })
                    return JsonResponse({
                        'success': False, 'codigo_existente': True,
                        'error': f'Item {codigo} já existe. Deseja somar?'
                    }, status=409)

            item = Item.objects.create(
                nome=nome, codigo=codigo, quantidade=quantidade,
                departamento=request.POST.get('departamento', 'OUT'),
                unidade=request.POST.get('unidade', 'UN'), localizacao=localizacao,
                descricao=request.POST.get('descricao', '').strip() or None,
                estoque_minimo=estoque_minimo,
                fornecedor=request.POST.get('fornecedor', '').strip() or None,
                lote=lote, ca=ca,
                categoria=request.POST.get('categoria', '').strip() or None,
                marca=request.POST.get('marca', '').strip() or None,
                tamanho=tamanho,
            )
            if 'foto' in request.FILES:
                item.foto = request.FILES['foto']
                item.save(update_fields=['foto', 'updated_at'])
        return JsonResponse({'success': True, 'message': f'Item {item.codigo} criado com sucesso!'})
    except Exception:
        logger.exception('Erro ao adicionar item no almoxarifado')
        return JsonResponse({'success': False, 'error': 'Não foi possível cadastrar o item.'}, status=500)


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def editar_item(request, pk):
    try:
        with transaction.atomic():
            item = get_object_or_404(Item.objects.select_for_update(), pk=pk, ativo=True)
            if request.POST.get('nome'):
                item.nome = str(request.POST['nome']).strip()
            if 'descricao' in request.POST:
                item.descricao = str(request.POST.get('descricao', '')).strip() or None
            if request.POST.get('departamento'):
                item.departamento = str(request.POST['departamento'])[:4]
            if request.POST.get('unidade'):
                item.unidade = str(request.POST['unidade'])[:3]
            if 'localizacao' in request.POST:
                item.localizacao = str(request.POST.get('localizacao', '')).strip() or None
            if 'estoque_minimo' in request.POST:
                minimo = parse_decimal(request.POST.get('estoque_minimo'), item.estoque_minimo)
                if minimo is None or minimo < 0:
                    return JsonResponse({'success': False, 'error': 'Estoque mínimo não pode ser negativo.'}, status=400)
                item.estoque_minimo = minimo
            if 'fornecedor' in request.POST:
                item.fornecedor = str(request.POST.get('fornecedor', '')).strip() or None
            if 'lote' in request.POST:
                item.lote = str(request.POST.get('lote', '')).strip() or None
            if 'ca' in request.POST:
                item.ca = str(request.POST.get('ca', '')).strip() or None
            if 'categoria' in request.POST:
                item.categoria = str(request.POST.get('categoria', '')).strip() or None
            if 'marca' in request.POST:
                item.marca = str(request.POST.get('marca', '')).strip() or None
            if 'quantidade' in request.POST:
                qtd = parse_decimal(request.POST.get('quantidade'), item.quantidade)
                if qtd is None or qtd < 0:
                    return JsonResponse({'success': False, 'error': 'Quantidade não pode ser negativa.'}, status=400)
                item.quantidade = qtd
            if 'tamanho' in request.POST:
                item.tamanho = str(request.POST.get('tamanho', '')).strip() or None
            if 'foto' in request.FILES:
                item.foto = request.FILES['foto']
            item.save()
        return JsonResponse({'success': True, 'message': f'Item {item.codigo} atualizado!'})
    except Exception:
        logger.exception('Erro ao editar item %s', pk)
        return JsonResponse({'success': False, 'error': 'Não foi possível atualizar o item.'}, status=500)


@almoxarifado_access_required()
@require_http_methods(["GET"])
def detalhe_item(request, pk):
    item = get_object_or_404(Item, pk=pk, ativo=True)
    ultimas_saidas = item.saidas.all().order_by('-data', '-hora')[:5]
    return JsonResponse({
        'id': item.id, 'codigo': item.codigo, 'nome': item.nome,
        'quantidade': float(item.quantidade), 'unidade': item.get_unidade_display(),
        'departamento': item.get_departamento_display(), 'localizacao': item.localizacao or 'Não definida',
        'descricao': item.descricao or 'Sem descrição', 'estoque_minimo': float(item.estoque_minimo),
        'fornecedor': item.fornecedor or 'Não informado', 'marca': item.marca or '-',
        'lote': item.lote or '-', 'ca': item.ca or '-', 'categoria': item.categoria or '-',
        'status_estoque': item.status_estoque,
        'foto_url': item.foto.url if item.foto else None,
        'tamanho': item.tamanho or '-',
        'ultimas_saidas': [{
            'data': s.data.strftime('%d/%m/%Y'), 'hora': s.hora.strftime('%H:%M'),
            'solicitante': s.solicitante, 'quantidade': float(s.quantidade),
            'observacao': s.observacao[:50] if s.observacao else '',
        } for s in ultimas_saidas]
    })


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def dar_baixa(request, pk):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        solicitante = str(data.get('solicitante', '')).strip()[:200]
        quantidade = parse_decimal(data.get('quantidade', '0'))
        if not solicitante:
            return JsonResponse({'success': False, 'error': 'Solicitante obrigatório'}, status=400)
        if quantidade is None or quantidade <= 0:
            return JsonResponse({'success': False, 'error': 'Quantidade deve ser maior que zero'}, status=400)

        with transaction.atomic():
            item = get_object_or_404(Item.objects.select_for_update(), pk=pk, ativo=True)
            if quantidade > item.quantidade:
                return JsonResponse({'success': False, 'error': f'Estoque insuficiente! Disponível: {float(item.quantidade)}'}, status=400)
            Saida.objects.create(
                item=item, item_nome=item.nome, item_codigo=item.codigo,
                solicitante=solicitante, departamento=data.get('departamento') or None,
                quantidade=quantidade,
                data=data.get('data', timezone.localdate().isoformat()),
                hora=data.get('hora', timezone.localtime(timezone.now()).strftime('%H:%M')),
                observacao=str(data.get('observacao', '')).strip()[:2000]
            )
            item.quantidade = F('quantidade') - quantidade
            item.save(update_fields=['quantidade', 'updated_at'])
            item.refresh_from_db(fields=['quantidade'])
        return JsonResponse({'success': True, 'message': f'Baixa de {float(quantidade)} {item.get_unidade_display()} realizada!'})
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception:
        logger.exception('Erro ao dar baixa no item %s', pk)
        return JsonResponse({'success': False, 'error': 'Não foi possível realizar a baixa.'}, status=500)


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def excluir_item(request, pk):
    """Desativa o item e remove referências temporárias de carrinho."""
    try:
        with transaction.atomic():
            item = get_object_or_404(Item.objects.select_for_update(), pk=pk, ativo=True)
            item.ativo = False
            item.save(update_fields=['ativo', 'updated_at'])
            CarrinhoSolicitacao.objects.filter(item=item).delete()
        return JsonResponse({'success': True, 'message': f'Item {item.codigo} desativado com sucesso!'})
    except Exception:
        logger.exception('Erro ao desativar item %s', pk)
        return JsonResponse({'success': False, 'error': 'Não foi possível desativar o item.'}, status=500)


# ===== CARRINHO =====

@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["GET"])
def ver_carrinho(request):
    usuario = _carrinho_usuario(request)
    itens = CarrinhoSolicitacao.objects.filter(usuario=usuario, item__ativo=True).select_related('item')
    return JsonResponse({'itens': [{
        'id': i.id, 'item_id': i.item.id, 'codigo': i.item.codigo,
        'nome': i.item.nome, 'quantidade': float(i.quantidade),
        'unidade': i.item.get_unidade_display(), 'estoque': float(i.item.quantidade),
    } for i in itens]})


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def adicionar_ao_carrinho(request):
    try:
        usuario = _carrinho_usuario(request)
        item_id = request.POST.get('item_id')
        quantidade = parse_decimal(request.POST.get('quantidade', '1'), Decimal('1'))
        if quantidade is None or quantidade <= 0:
            return JsonResponse({'success': False, 'error': 'Quantidade deve ser maior que zero.'}, status=400)

        with transaction.atomic():
            item = get_object_or_404(Item.objects.select_for_update(), pk=item_id, ativo=True)
            carrinho_item = CarrinhoSolicitacao.objects.select_for_update().filter(usuario=usuario, item=item).first()
            quantidade_final = quantidade + (carrinho_item.quantidade if carrinho_item else Decimal('0'))
            if quantidade_final > item.quantidade:
                return JsonResponse({
                    'success': False,
                    'error': f'Estoque insuficiente! Disponível: {float(item.quantidade)}; já no carrinho: {float(carrinho_item.quantidade) if carrinho_item else 0}.'
                }, status=400)
            if carrinho_item:
                carrinho_item.quantidade = quantidade_final
                carrinho_item.save(update_fields=['quantidade'])
            else:
                CarrinhoSolicitacao.objects.create(usuario=usuario, item=item, quantidade=quantidade)
            count = CarrinhoSolicitacao.objects.filter(usuario=usuario).count()
        return JsonResponse({'success': True, 'message': f'{item.nome} adicionado ao carrinho!', 'carrinho_count': count})
    except Exception:
        logger.exception('Erro ao adicionar item ao carrinho')
        return JsonResponse({'success': False, 'error': 'Não foi possível adicionar ao carrinho.'}, status=500)


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def remover_do_carrinho(request, pk):
    usuario = _carrinho_usuario(request)
    CarrinhoSolicitacao.objects.filter(usuario=usuario, pk=pk).delete()
    count = CarrinhoSolicitacao.objects.filter(usuario=usuario).count()
    return JsonResponse({'success': True, 'message': 'Item removido!', 'carrinho_count': count})


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def finalizar_carrinho(request):
    try:
        usuario = _carrinho_usuario(request)
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        solicitante = str(data.get('solicitante', '')).strip()[:200]
        if not solicitante:
            return JsonResponse({'success': False, 'error': 'Solicitante obrigatório!'}, status=400)

        with transaction.atomic():
            carrinho = list(
                CarrinhoSolicitacao.objects.select_for_update()
                .filter(usuario=usuario, item__ativo=True)
                .select_related('item')
            )
            if not carrinho:
                return JsonResponse({'success': False, 'error': 'Carrinho vazio!'}, status=400)

            item_ids = sorted({ci.item_id for ci in carrinho})
            itens = {i.id: i for i in Item.objects.select_for_update().filter(id__in=item_ids, ativo=True)}
            for ci in carrinho:
                item = itens.get(ci.item_id)
                if item is None or ci.quantidade > item.quantidade:
                    disponivel = float(item.quantidade) if item else 0
                    return JsonResponse({'success': False, 'error': f'Estoque insuficiente para {ci.item.nome}! Disponível: {disponivel}'}, status=400)

            hoje = timezone.localdate()
            agora = timezone.localtime(timezone.now()).time().replace(second=0, microsecond=0)
            saidas = []
            atualizado_em = timezone.now()
            for ci in carrinho:
                item = itens[ci.item_id]
                saidas.append(Saida(
                    item=item, item_nome=item.nome, item_codigo=item.codigo,
                    solicitante=solicitante, departamento=data.get('departamento') or None,
                    quantidade=ci.quantidade, data=hoje, hora=agora,
                    observacao=str(data.get('observacao', '')).strip()[:2000]
                ))
                item.quantidade -= ci.quantidade
                item.updated_at = atualizado_em
            Saida.objects.bulk_create(saidas)
            Item.objects.bulk_update(list(itens.values()), ['quantidade', 'updated_at'])
            CarrinhoSolicitacao.objects.filter(usuario=usuario).delete()
        return JsonResponse({'success': True, 'message': 'Baixa concluída com sucesso!'})
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Dados inválidos.'}, status=400)
    except Exception:
        logger.exception('Erro ao finalizar carrinho')
        return JsonResponse({'success': False, 'error': 'Não foi possível finalizar a baixa.'}, status=500)


@almoxarifado_access_required(gerenciar=True)
@require_http_methods(["POST"])
def limpar_carrinho(request):
    usuario = _carrinho_usuario(request)
    CarrinhoSolicitacao.objects.filter(usuario=usuario).delete()
    return JsonResponse({'success': True, 'message': 'Carrinho limpo!'})


# ===== EXPORTAÇÃO =====

@almoxarifado_access_required()
@require_http_methods(["GET"])
def exportar_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Estoque"
    
    cabecalhos = [
        'Código', 'Nome', 'Descrição', 'Departamento', 'Categoria',
        'Quantidade', 'Unidade', 'Localização', 'Estoque Mínimo',
        'Fornecedor', 'Marca', 'Lote', 'CA', 'Tamanho'
    ]
    
    header_font = Font(bold=True, color='FFFFFF', size=11, name='Arial')
    header_fill = PatternFill(start_color='059669', end_color='059669', fill_type='solid')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    for col, header in enumerate(cabecalhos, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    
    itens = Item.objects.filter(ativo=True).order_by('nome')
    
    for row, item in enumerate(itens, 2):
        dados = [
            item.codigo or '',
            item.nome,
            item.descricao or '',
            item.get_departamento_display(),
            item.categoria or '',
            float(item.quantidade),
            item.get_unidade_display(),
            item.localizacao or '',
            float(item.estoque_minimo),
            item.fornecedor or '',
            item.marca or '',
            item.lote or '',
            item.ca or '',
            item.tamanho or '',
        ]
        
        for col, valor in enumerate(dados, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=estoque_{timezone.localdate().strftime("%Y%m%d")}.xlsx'
    return response


@almoxarifado_access_required()
@require_http_methods(["GET"])
def baixar_modelo_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Modelo Importação"
    
    cabecalhos = [
        'Código', 'Nome', 'Descrição', 'Departamento', 'Categoria',
        'Quantidade', 'Unidade', 'Localização', 'Estoque Mínimo',
        'Fornecedor', 'Marca', 'Lote', 'CA', 'Tamanho'
    ]
    
    header_font = Font(bold=True, color='FFFFFF', size=11, name='Arial')
    header_fill = PatternFill(start_color='2f8f4e', end_color='2f8f4e', fill_type='solid')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    for col, header in enumerate(cabecalhos, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    exemplos = [
        ['001', 'Parafuso 10mm', 'Parafuso sextavado', 'Administrativo', 'Ferragens',
         100, 'Unidade', 'Prateleira A2', 10, 'Fornecedor ABC', 'Tramontina',
         'LOTE-001', 'CA-12345', 'Pequeno'],
    ]
    
    for row, exemplo in enumerate(exemplos, 2):
        for col, valor in enumerate(exemplo, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.border = thin_border
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=modelo_importacao_almoxarifado.xlsx'
    return response


@almoxarifado_access_required()
@require_http_methods(["GET"])
def exportar_saidas_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Saídas"
    
    cabecalhos = ['Data', 'Hora', 'Solicitante', 'Departamento', 'Código Item', 'Item', 'Quantidade', 'Observação']
    
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='dc3545', end_color='dc3545', fill_type='solid')
    
    for col, header in enumerate(cabecalhos, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    saidas = Saida.objects.all().order_by('-data', '-hora')
    for row, saida in enumerate(saidas, 2):
        dados = [
            saida.data.strftime('%d/%m/%Y'), saida.hora.strftime('%H:%M'),
            saida.solicitante, saida.get_departamento_display() or '',
            saida.item_codigo or '', saida.item_nome, float(saida.quantidade),
            saida.observacao or ''
        ]
        for col, valor in enumerate(dados, 1):
            ws.cell(row=row, column=col, value=valor)
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=saidas_{timezone.localdate().strftime("%Y%m%d")}.xlsx'
    return response
