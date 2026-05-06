import json
import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q, Sum, Count
from django.contrib import messages
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from .models import Item, Saida, CarrinhoSolicitacao, Departamento, UnidadeMedida


def parse_decimal(value, default=None):
    """Converte string com vírgula para Decimal, removendo zeros à esquerda"""
    if value is None or str(value).strip() == '':
        return default
    try:
        val_str = str(value).strip().replace(',', '.')
        # Remove zeros à esquerda desnecessários
        d = Decimal(val_str)
        # Normaliza: 1.500 -> 1.5, 0.500 -> 0.5, 5.0 -> 5
        d = d.normalize()
        # Se for 0.5, mantém; se for 5, mantém como 5
        return d
    except (InvalidOperation, ValueError):
        return default


@ensure_csrf_cookie
def lista_itens(request):
    mostrar_todos = request.GET.get('todos', '0') == '1'
    
    itens = Item.objects.filter(ativo=True)
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
    
    ordenar = request.GET.get('ordenar', 'nome')
    ordenacao_map = {
        'nome': 'nome',
        '-quantidade': '-quantidade',
        'quantidade': 'quantidade',
        'recente': '-updated_at',
    }
    itens = itens.order_by(ordenacao_map.get(ordenar, 'nome'))
    
    usuario = request.session.get('usuario_carrinho', request.user.username if request.user.is_authenticated else 'anonimo')
    carrinho_count = CarrinhoSolicitacao.objects.filter(usuario=usuario).count()
    
    total_itens = itens.count()
    total_quantidade = itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
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
    }
    return render(request, 'almoxarifado/lista_itens.html', context)


def saidas_list(request):
    saidas = Saida.objects.select_related('item').all().order_by('-data', '-hora')
    
    busca = request.GET.get('busca', '')
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
    
    context = {
        'saidas': saidas,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'dept': dept,
        'departamentos': Departamento.choices,
        'total_saidas': total_saidas,
        'total_retirado': total_retirado,
    }
    return render(request, 'almoxarifado/saidas_list.html', context)


def buscar_itens_ajax(request):
    busca = request.GET.get('busca', '')
    departamento = request.GET.get('departamento', '')
    mostrar_todos = request.GET.get('todos', '0') == '1'
    ordenar = request.GET.get('ordenar', 'nome')
    
    itens = Item.objects.filter(ativo=True)
    if not mostrar_todos:
        itens = itens.filter(quantidade__gt=0)
    
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
    
    if departamento:
        itens = itens.filter(departamento=departamento)
    
    ordenacao_map = {'nome': 'nome', '-quantidade': '-quantidade', 'quantidade': 'quantidade', 'recente': '-updated_at'}
    itens = itens.order_by(ordenacao_map.get(ordenar, 'nome'))
    
    data = {
        'itens': [{
            'id': i.id, 'codigo': i.codigo, 'nome': i.nome,
            'quantidade': float(i.quantidade), 'unidade': i.get_unidade_display(),
            'localizacao': i.localizacao or '-', 'departamento': i.get_departamento_display(),
            'status_estoque': i.status_estoque, 'lote': i.lote or '-', 'ca': i.ca or '-',
        } for i in itens],
        'total_itens': itens.count(),
        'total_quantidade': float(itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0),
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
def buscar_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    if not codigo:
        return JsonResponse({'encontrado': False})
    
    try:
        item = Item.objects.get(codigo=codigo, ativo=True)
        return JsonResponse({
            'encontrado': True,
            'item': {
                'id': item.id, 'codigo': item.codigo, 'nome': item.nome,
                'descricao': item.descricao, 'departamento': item.departamento,
                'unidade': item.unidade, 'localizacao': item.localizacao,
                'estoque_minimo': float(item.estoque_minimo),
                'valor_unitario': float(item.valor_unitario) if item.valor_unitario else None,
                'fornecedor': item.fornecedor, 'quantidade': float(item.quantidade),
                'lote': item.lote, 'ca': item.ca, 'categoria': item.categoria,
                'marca': item.marca,
            }
        })
    except Item.DoesNotExist:
        # Verifica se existe desativado
        item_inativo = Item.objects.filter(codigo=codigo, ativo=False).first()
        if item_inativo:
            return JsonResponse({
                'encontrado': True, 
                'reativar': True,
                'item': {
                    'id': item_inativo.id, 'codigo': item_inativo.codigo, 'nome': item_inativo.nome,
                    'descricao': item_inativo.descricao, 'departamento': item_inativo.departamento,
                    'unidade': item_inativo.unidade, 'localizacao': item_inativo.localizacao,
                    'estoque_minimo': float(item_inativo.estoque_minimo),
                    'valor_unitario': float(item_inativo.valor_unitario) if item_inativo.valor_unitario else None,
                    'fornecedor': item_inativo.fornecedor, 'quantidade': 0,
                    'lote': item_inativo.lote, 'ca': item_inativo.ca, 'categoria': item_inativo.categoria,
                    'marca': item_inativo.marca,
                }
            })
        return JsonResponse({'encontrado': False})


@require_http_methods(["POST"])
def adicionar_item(request):
    
    """Adiciona novo item - SÓ SOMA se código + lote + CA + localização forem iguais"""
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome obrigatório'}, status=400)
        
        codigo = request.POST.get('codigo', '').strip() or None
        quantidade = parse_decimal(request.POST.get('quantidade', '0'), Decimal('0'))
        lote = request.POST.get('lote', '').strip() or None
        ca = request.POST.get('ca', '').strip() or None
        localizacao = request.POST.get('localizacao', '').strip() or None
        tamanho = request.POST.get('tamanho', '').strip() or None
        
        # ===== BUSCAR ITEM EXATAMENTE IGUAL =====
        # Só soma se Código + Lote + CA + Localização forem TODOS iguais
        
        if codigo:
            item_existente = Item.objects.filter(
                codigo=codigo,
                lote=lote,
                ca=ca,
                localizacao=localizacao
            ).first()
            
            if item_existente:
                if not item_existente.ativo:
                    # Reativar
                    item_existente.ativo = True
                    item_existente.quantidade = quantidade
                    item_existente.nome = nome
                    item_existente.save()
                    return JsonResponse({
                        'success': True,
                        'message': f'Item {codigo} reativado com sucesso!'
                    })
                
                # Item ativo - SOMAR
                if request.POST.get('somar', 'false') == 'true':
                    item_existente.quantidade += quantidade
                    item_existente.save()
                    return JsonResponse({
                        'success': True,
                        'message': f'Quantidade somada! Total: {float(item_existente.quantidade)} {item_existente.get_unidade_display()}'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'codigo_existente': True,
                        'error': f'Item {codigo} já existe com lote={item_existente.lote}, CA={item_existente.ca}, local={item_existente.localizacao}. Deseja somar?'
                    }, status=409)
        
        # Verificar por nome + lote + ca + localização (sem código)
        if not codigo:
            item_similar = Item.objects.filter(
                nome__iexact=nome,
                lote=lote,
                ca=ca,
                localizacao=localizacao,
                ativo=True
            ).first()
            
            if item_similar:
                if request.POST.get('somar', 'false') == 'true':
                    item_similar.quantidade += quantidade
                    item_similar.save()
                    return JsonResponse({
                        'success': True,
                        'message': f'Quantidade somada ao item {item_similar.codigo}!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'nome_existente': True,
                        'item_id': item_similar.id,
                        'nome': item_similar.nome,
                        'codigo': item_similar.codigo,
                        'quantidade': float(item_similar.quantidade),
                        'unidade': item_similar.get_unidade_display(),
                        'error': f'Item similar já existe ({item_similar.codigo}) com mesmo lote/CA/local. Deseja somar?'
                    }, status=409)
        
        # ===== CRIAR NOVO ITEM =====
        item = Item.objects.create(
            nome=nome,
            codigo=codigo,
            quantidade=quantidade,
            departamento=request.POST.get('departamento', 'OUT'),
            unidade=request.POST.get('unidade', 'UN'),
            localizacao=localizacao,
            descricao=request.POST.get('descricao', '').strip() or None,
            estoque_minimo=parse_decimal(request.POST.get('estoque_minimo', '5'), Decimal('5')),
            valor_unitario=parse_decimal(request.POST.get('valor_unitario', '')),
            fornecedor=request.POST.get('fornecedor', '').strip() or None,
            lote=lote,
            ca=ca,
            validade_ca=request.POST.get('validade_ca') or None,
            categoria=request.POST.get('categoria', '').strip() or None,
            marca=request.POST.get('marca', '').strip() or None,
            data_aquisicao=request.POST.get('data_aquisicao') or None,
            tamanho=tamanho,
        )
        
        if 'foto' in request.FILES:
            item.foto = request.FILES['foto']
            item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Item {item.codigo} criado com sucesso!',
            'item': {'id': item.id, 'codigo': item.codigo}
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["POST"])
def editar_item(request, pk):
    """Edita um item existente"""
    try:
        item = get_object_or_404(Item, pk=pk)
        data = request.POST
        
        if data.get('nome'): item.nome = str(data['nome']).strip()
        if 'descricao' in data: item.descricao = str(data.get('descricao', '')).strip() or None
        if data.get('departamento'): item.departamento = str(data['departamento'])[:4]
        if data.get('unidade'): item.unidade = str(data['unidade'])[:3]
        if 'localizacao' in data: item.localizacao = str(data.get('localizacao', '')).strip() or None
        if data.get('estoque_minimo'): item.estoque_minimo = parse_decimal(data['estoque_minimo'], item.estoque_minimo)
        if 'valor_unitario' in data: item.valor_unitario = parse_decimal(data.get('valor_unitario', ''))
        if 'fornecedor' in data: item.fornecedor = str(data.get('fornecedor', '')).strip() or None
        if 'lote' in data: item.lote = str(data.get('lote', '')).strip() or None
        if 'ca' in data: item.ca = str(data.get('ca', '')).strip() or None
        if data.get('validade_ca'): item.validade_ca = data['validade_ca'] or None
        if 'categoria' in data: item.categoria = str(data.get('categoria', '')).strip() or None
        if 'marca' in data: item.marca = str(data.get('marca', '')).strip() or None
        if data.get('data_aquisicao'): item.data_aquisicao = data['data_aquisicao'] or None
        if data.get('quantidade'): item.quantidade = parse_decimal(data['quantidade'], item.quantidade)
        if 'ativo' in data: item.ativo = str(data['ativo']).lower() in ['true', '1', 'on']
        if 'tamanho' in data: item.tamanho = str(data.get('tamanho', '')).strip() or None
        
        if 'foto' in request.FILES:
            item.foto = request.FILES['foto']
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Item {item.codigo} - {item.nome} atualizado com sucesso!',
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def detalhe_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    ultimas_saidas = item.saidas.all().order_by('-data', '-hora')[:5]
    
    return JsonResponse({
        'id': item.id, 'codigo': item.codigo, 'nome': item.nome,
        'quantidade': float(item.quantidade), 'unidade': item.get_unidade_display(),
        'departamento': item.get_departamento_display(), 'localizacao': item.localizacao or 'Não definida',
        'descricao': item.descricao or 'Sem descrição', 'estoque_minimo': float(item.estoque_minimo),
        'valor_unitario': float(item.valor_unitario) if item.valor_unitario else None,
        'valor_total': float(item.valor_total) if item.valor_total else None,
        'fornecedor': item.fornecedor or 'Não informado', 'marca': item.marca or '-',
        'lote': item.lote or '-', 'ca': item.ca or '-', 'categoria': item.categoria or '-',
        'validade_ca': item.validade_ca.strftime('%d/%m/%Y') if item.validade_ca else '-',
        'data_aquisicao': item.data_aquisicao.strftime('%d/%m/%Y') if item.data_aquisicao else '-',
        'status_estoque': item.status_estoque,
        'foto_url': item.foto.url if item.foto else None,
        'created_at': item.created_at.strftime('%d/%m/%Y %H:%M'),
        'updated_at': item.updated_at.strftime('%d/%m/%Y %H:%M'),
        'tamanho': item.tamanho or '-',
        'ultimas_saidas': [{
            'data': s.data.strftime('%d/%m/%Y'), 'hora': s.hora.strftime('%H:%M'),
            'solicitante': s.solicitante, 'quantidade': float(s.quantidade),
            'observacao': s.observacao[:50] if s.observacao else '',
        } for s in ultimas_saidas]
    })


@require_http_methods(["POST"])
def dar_baixa(request, pk):
    try:
        item = get_object_or_404(Item, pk=pk)
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        solicitante = data.get('solicitante', '').strip()
        quantidade = parse_decimal(data.get('quantidade', '0'))
        
        if not solicitante:
            return JsonResponse({'success': False, 'error': 'Solicitante obrigatório'}, status=400)
        if quantidade <= 0:
            return JsonResponse({'success': False, 'error': 'Quantidade deve ser maior que zero'}, status=400)
        if quantidade > item.quantidade:
            return JsonResponse({'success': False, 'error': f'Estoque insuficiente! Disponível: {float(item.quantidade)} {item.get_unidade_display()}'}, status=400)
        
        saida = Saida.objects.create(
            item=item, item_nome=item.nome, item_codigo=item.codigo,
            solicitante=solicitante,
            departamento=data.get('departamento') or None,
            quantidade=quantidade,
            data=data.get('data', date.today().isoformat()),
            hora=data.get('hora', datetime.now().strftime('%H:%M')),
            observacao=data.get('observacao', '').strip()
        )
        
        item.quantidade -= quantidade
        item.save()
        
        return JsonResponse({'success': True, 'message': f'Baixa de {float(quantidade)} {item.get_unidade_display()} realizada!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ===== CARRINHO =====

def ver_carrinho(request):
    usuario = request.session.get('usuario_carrinho', 'anonimo')
    itens = CarrinhoSolicitacao.objects.filter(usuario=usuario).select_related('item')
    return JsonResponse({
        'itens': [{
            'id': i.id, 'item_id': i.item.id, 'codigo': i.item.codigo,
            'nome': i.item.nome, 'quantidade': float(i.quantidade),
            'unidade': i.item.get_unidade_display(), 'estoque': float(i.item.quantidade),
        } for i in itens]
    })


@require_http_methods(["POST"])
def adicionar_ao_carrinho(request):
    try:
        usuario = request.session.get('usuario_carrinho', 'anonimo')
        item_id = request.POST.get('item_id')
        quantidade = parse_decimal(request.POST.get('quantidade', '1'), Decimal('1'))
        
        item = get_object_or_404(Item, pk=item_id, ativo=True)
        
        if quantidade > item.quantidade:
            return JsonResponse({'success': False, 'error': f'Estoque insuficiente! Disponível: {float(item.quantidade)}'}, status=400)
        
        carrinho_item, created = CarrinhoSolicitacao.objects.get_or_create(
            usuario=usuario, item=item,
            defaults={'quantidade': quantidade}
        )
        if not created:
            carrinho_item.quantidade += quantidade
            carrinho_item.save()
        
        return JsonResponse({'success': True, 'message': f'{item.nome} adicionado ao carrinho!', 'carrinho_count': CarrinhoSolicitacao.objects.filter(usuario=usuario).count()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def remover_do_carrinho(request, pk):
    try:
        usuario = request.session.get('usuario_carrinho', 'anonimo')
        CarrinhoSolicitacao.objects.filter(usuario=usuario, pk=pk).delete()
        count = CarrinhoSolicitacao.objects.filter(usuario=usuario).count()
        return JsonResponse({'success': True, 'message': 'Item removido!', 'carrinho_count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def finalizar_carrinho(request):
    try:
        usuario = request.session.get('usuario_carrinho', 'anonimo')
        itens_carrinho = CarrinhoSolicitacao.objects.filter(usuario=usuario).select_related('item')
        
        if not itens_carrinho.exists():
            return JsonResponse({'success': False, 'error': 'Carrinho vazio!'}, status=400)
        
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        solicitante = data.get('solicitante', '').strip()
        
        if not solicitante:
            return JsonResponse({'success': False, 'error': 'Solicitante obrigatório!'}, status=400)
        
        hoje = date.today()
        agora = datetime.now().strftime('%H:%M')
        total_itens = itens_carrinho.count()
        
        for ci in itens_carrinho:
            if ci.quantidade > ci.item.quantidade:
                return JsonResponse({'success': False, 'error': f'Estoque insuficiente para {ci.item.nome}!'}, status=400)
        
        for ci in itens_carrinho:
            Saida.objects.create(
                item=ci.item, item_nome=ci.item.nome, item_codigo=ci.item.codigo,
                solicitante=solicitante,
                departamento=data.get('departamento') or None,
                quantidade=ci.quantidade, data=hoje, hora=agora,
                observacao=data.get('observacao', '')
            )
            ci.item.quantidade -= ci.quantidade
            ci.item.save()
            ci.delete()
        
        return JsonResponse({'success': True, 'message': f'Baixa de {total_itens} itens realizada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def limpar_carrinho(request):
    usuario = request.session.get('usuario_carrinho', 'anonimo')
    count = CarrinhoSolicitacao.objects.filter(usuario=usuario).delete()[0]
    return JsonResponse({'success': True, 'message': f'{count} itens removidos do carrinho!'})


# ===== EXPORTAÇÃO =====

def exportar_excel(request):
    """Exporta itens para Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Estoque"
    
    cabecalhos = [
        'Código', 'Nome', 'Descrição', 'Departamento', 'Categoria',
        'Quantidade', 'Unidade', 'Localização', 'Estoque Mínimo',
        'Valor Unitário', 'Fornecedor', 'Marca',
        'Lote', 'CA', 'Validade CA', 'Data Aquisição', 'Status'
    ]
    
    header_font = Font(bold=True, color='FFFFFF', size=11, name='Arial')
    header_fill = PatternFill(start_color='1a202c', end_color='1a202c', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    for col, header in enumerate(cabecalhos, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    itens = Item.objects.filter(ativo=True).order_by('nome')
    status_map = {'zerado': 'Zerado', 'baixo': 'Baixo', 'medio': 'Médio', 'alto': 'Alto'}
    
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
            float(item.valor_unitario) if item.valor_unitario else '',
            item.fornecedor or '',
            item.marca or '',
            item.lote or '',
            item.ca or '',
            item.validade_ca.strftime('%d/%m/%Y') if item.validade_ca else '',
            item.data_aquisicao.strftime('%d/%m/%Y') if item.data_aquisicao else '',
            status_map.get(item.status_estoque, ''),
        ]
        
        for col, valor in enumerate(dados, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col in [6, 9]:
                cell.number_format = '#,##0.###'
            elif col == 10:
                cell.number_format = '#,##0.00'
    
    larguras = [8, 30, 25, 18, 15, 10, 8, 15, 12, 12, 20, 15, 15, 15, 12, 12, 10]
    for col, largura in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(col)].width = largura
    
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cabecalhos))}{itens.count() + 1}"
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=estoque_{date.today().strftime("%Y%m%d")}.xlsx'
    return response


def baixar_modelo_excel(request):
    """Baixa o modelo Excel para importação"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Modelo Importação"
    
    cabecalhos = [
        'Código', 'Nome', 'Descrição', 'Departamento', 'Categoria',
        'Quantidade', 'Unidade', 'Localização', 'Estoque Mínimo',
        'Valor Unitário', 'Fornecedor', 'Marca',
        'Lote', 'CA', 'Validade CA', 'Data Aquisição'
    ]
    
    header_font = Font(bold=True, color='FFFFFF', size=11, name='Arial')
    header_fill = PatternFill(start_color='2f8f4e', end_color='2f8f4e', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    for col, header in enumerate(cabecalhos, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    exemplos = [
        ['001', 'Parafuso 10mm', 'Parafuso sextavado zincado', 'Administrativo', 'Ferragens',
         100, 'Unidade', 'Prateleira A2', 10, 1.50, 'Fornecedor ABC', 'Tramontina',
         'LOTE-2024-001', 'CA-12345', '31/12/2025', '15/06/2024'],
        ['', 'Luva de Proteção', 'Luva de segurança tamanho M', 'Produção', 'EPI',
         50, 'Par', 'Armário 3', 20, 12.90, 'Fornecedor XYZ', '3M',
         'LOTE-2024-050', 'CA-67890', '30/06/2025', '10/01/2024'],
        ['', 'Óleo Lubrificante', 'Óleo sintético 5W30', 'Manutenção', 'Lubrificantes',
         25.5, 'Litro', 'Prateleira B1', 5, 45.00, 'Fornecedor LM', 'Shell',
         'LOTE-2024-100', '', '', ''],
        ['', 'Papel A4', 'Resma de papel sulfite', 'Administrativo', 'Material Escritório',
         200, 'Unidade', 'Almoxarifado Adm', 50, 0.35, 'Fornecedor Office', 'Report',
         '', '', '', '01/03/2024'],
    ]
    
    for row, exemplo in enumerate(exemplos, 2):
        for col, valor in enumerate(exemplo, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')
            if col in [6, 9]:
                cell.number_format = '#,##0.###'
            elif col == 10:
                cell.number_format = '#,##0.00'
    
    ws2 = wb.create_sheet("Instruções")
    instrucoes = [
        ['INSTRUÇÕES PARA IMPORTAÇÃO'],
        [''],
        ['1. Apenas a coluna "Nome" é obrigatória'],
        ['2. Se o Código for deixado em branco, será gerado automaticamente'],
        ['3. Se o Código já existir no sistema, a quantidade será SOMADA ao item existente'],
        ['4. Se o item estiver DESATIVADO, ele será REATIVADO ao importar'],
        ['5. Mesmo código + mesmo lote + mesmo CA + mesma localização = SOMA'],
        ['6. Itens com código/lote/CA/localização diferentes são criados separadamente'],
        ['7. Quantidades aceitam decimais (use ponto ou vírgula)'],
        ['8. Datas devem estar no formato DD/MM/AAAA'],
        ['9. Departamentos aceitos: Administrativo, Produção, Manutenção, TI, Marketing, Vendas, RH, Financeiro, Jurídico, Logística, Qualidade, Pesquisa, Outros'],
        ['10. Unidades aceitas: Unidade, Caixa, Pacote, Quilograma, Grama, Litro, Mililitro, Metro, Centímetro, Par, Dúzia, Rolo, Folha'],
        ['11. Após preencher, salve como .xlsx e importe no sistema'],
        ['12. O arquivo exportado pelo sistema tem o mesmo formato - use como referência!'],
    ]
    
    for row, linha in enumerate(instrucoes, 1):
        cell = ws2.cell(row=row, column=1, value=linha[0])
        if row == 1:
            cell.font = Font(bold=True, size=14, color='2f8f4e')
        else:
            cell.font = Font(size=11)
    
    ws2.column_dimensions['A'].width = 80
    
    larguras = [8, 30, 25, 18, 15, 10, 8, 15, 12, 12, 20, 15, 15, 15, 12, 12]
    for col, largura in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(col)].width = largura
    
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cabecalhos))}{len(exemplos) + 1}"
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=modelo_importacao_almoxarifado.xlsx'
    return response


@require_http_methods(["POST"])
def importar_excel(request):
    """Importa itens de arquivo Excel - CORRIGIDO"""
    try:
        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo enviado'}, status=400)
        
        from openpyxl import load_workbook
        wb = load_workbook(arquivo)
        ws = wb.active
        
        importados = 0
        somados = 0
        reativados = 0
        erros = []
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                if not row or not any(cell for cell in row):
                    continue
                
                # Extrair dados de TODAS as colunas
                codigo = str(row[0]).strip() if row[0] else None
                nome = str(row[1]).strip() if len(row) > 1 and row[1] else None
                
                if not nome:
                    erros.append(f'Linha {row_idx}: Nome obrigatório - ignorada')
                    continue
                
                # Quantidade
                quantidade = Decimal('0')
                if len(row) > 5 and row[5] is not None:
                    qtd_str = str(row[5]).strip().replace(',', '.')
                    try:
                        quantidade = Decimal(qtd_str).normalize()
                    except:
                        pass
                
                # Estoque mínimo
                estoque_minimo = Decimal('5')
                if len(row) > 8 and row[8] is not None:
                    try:
                        estoque_minimo = Decimal(str(row[8]).strip().replace(',', '.')).normalize()
                    except:
                        pass
                
                # Valor unitário
                valor_unitario = None
                if len(row) > 9 and row[9] is not None and str(row[9]).strip():
                    try:
                        valor_unitario = Decimal(str(row[9]).strip().replace(',', '.'))
                    except:
                        pass
                
                # Mapear departamento
                departamento = 'OUT'
                if len(row) > 3 and row[3]:
                    dept_str = str(row[3]).strip().upper()
                    dept_map = {
                        'ADM': 'ADM', 'ADMINISTRATIVO': 'ADM',
                        'PROD': 'PROD', 'PRODUÇÃO': 'PROD', 'PRODUCAO': 'PROD',
                        'MAN': 'MAN', 'MANUTENÇÃO': 'MAN', 'MANUTENCAO': 'MAN',
                        'TI': 'TI', 'TECNOLOGIA': 'TI',
                        'MKT': 'MKT', 'MARKETING': 'MKT',
                        'VEND': 'VEND', 'VENDAS': 'VEND',
                        'RH': 'RH', 'RECURSOS HUMANOS': 'RH',
                        'FIN': 'FIN', 'FINANCEIRO': 'FIN',
                        'JUR': 'JUR', 'JURÍDICO': 'JUR', 'JURIDICO': 'JUR',
                        'LOG': 'LOG', 'LOGÍSTICA': 'LOG', 'LOGISTICA': 'LOG',
                        'QUAL': 'QUAL', 'QUALIDADE': 'QUAL',
                        'PESQ': 'PESQ', 'PESQUISA': 'PESQ',
                        'OUT': 'OUT', 'OUTROS': 'OUT',
                    }
                    departamento = dept_map.get(dept_str, 'OUT')
                
                # Mapear unidade
                unidade = 'UN'
                if len(row) > 6 and row[6]:
                    un_str = str(row[6]).strip().upper()
                    un_map = {
                        'UN': 'UN', 'UNIDADE': 'UN', 'UND': 'UN',
                        'CX': 'CX', 'CAIXA': 'CX',
                        'PCT': 'PCT', 'PACOTE': 'PCT',
                        'KG': 'KG', 'KILO': 'KG', 'QUILOGRAMA': 'KG',
                        'G': 'G', 'GRAMA': 'G',
                        'L': 'L', 'LITRO': 'L',
                        'ML': 'ML', 'MILILITRO': 'ML',
                        'M': 'M', 'METRO': 'M',
                        'CM': 'CM', 'CENTIMETRO': 'CM', 'CENTÍMETRO': 'CM',
                        'PAR': 'PAR',
                        'DZ': 'DZ', 'DUZIA': 'DZ', 'DÚZIA': 'DZ',
                        'RL': 'RL', 'ROLO': 'RL',
                        'FL': 'FL', 'FOLHA': 'FL',
                    }
                    unidade = un_map.get(un_str, 'UN')
                
                # Demais campos
                descricao = str(row[2]).strip() if len(row) > 2 and row[2] else None
                categoria = str(row[4]).strip() if len(row) > 4 and row[4] else None
                localizacao = str(row[7]).strip() if len(row) > 7 and row[7] else None
                fornecedor = str(row[10]).strip() if len(row) > 10 and row[10] else None
                marca = str(row[11]).strip() if len(row) > 11 and row[11] else None
                lote = str(row[12]).strip() if len(row) > 12 and row[12] else None
                ca = str(row[13]).strip() if len(row) > 13 and row[13] else None
                
                # Datas
                validade_ca = None
                if len(row) > 14 and row[14]:
                    try:
                        if isinstance(row[14], str):
                            from datetime import datetime as dt
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                try:
                                    validade_ca = dt.strptime(row[14].strip(), fmt).date()
                                    break
                                except:
                                    pass
                        elif hasattr(row[14], 'date'):
                            validade_ca = row[14].date() if callable(row[14].date) else row[14]
                    except:
                        pass
                
                data_aquisicao = None
                if len(row) > 15 and row[15]:
                    try:
                        if isinstance(row[15], str):
                            from datetime import datetime as dt
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                try:
                                    data_aquisicao = dt.strptime(row[15].strip(), fmt).date()
                                    break
                                except:
                                    pass
                        elif hasattr(row[15], 'date'):
                            data_aquisicao = row[15].date() if callable(row[15].date) else row[15]
                    except:
                        pass
                
                # ===== LÓGICA DE IMPORTAÇÃO CORRIGIDA =====
                # SÓ SOMA SE: Código + Lote + CA + Localização forem TODOS IGUAIS
                # Caso contrário, cria NOVO registro
                
                item_alvo = None
                
                # Buscar item EXATAMENTE igual (todos os campos coincidem)
                item_alvo = Item.objects.filter(
                    codigo=codigo if codigo else None,
                    lote=lote if lote else None,
                    ca=ca if ca else None,
                    localizacao=localizacao if localizacao else None
                ).first()
                
                # Se não encontrou com todos os campos, verifica um por um
                if not item_alvo and codigo:
                    # Se tem código, busca APENAS por código + lote + ca + local
                    item_alvo = Item.objects.filter(
                        codigo=codigo,
                        lote=lote if lote else None,
                        ca=ca if ca else None,
                        localizacao=localizacao if localizacao else None
                    ).first()
                
                if item_alvo:
                    # ===== ITEM ENCONTRADO - MESMO CÓDIGO/LOTE/CA/LOCAL = SOMAR =====
                    
                    if not item_alvo.ativo:
                        # REATIVAR
                        item_alvo.ativo = True
                        item_alvo.quantidade = quantidade
                        item_alvo.nome = nome
                        item_alvo.descricao = descricao if descricao else item_alvo.descricao
                        item_alvo.departamento = departamento if departamento != 'OUT' else item_alvo.departamento
                        item_alvo.categoria = categoria if categoria else item_alvo.categoria
                        item_alvo.unidade = unidade
                        item_alvo.estoque_minimo = estoque_minimo
                        item_alvo.valor_unitario = valor_unitario if valor_unitario else item_alvo.valor_unitario
                        item_alvo.fornecedor = fornecedor if fornecedor else item_alvo.fornecedor
                        item_alvo.marca = marca if marca else item_alvo.marca
                        item_alvo.validade_ca = validade_ca if validade_ca else item_alvo.validade_ca
                        item_alvo.data_aquisicao = data_aquisicao if data_aquisicao else item_alvo.data_aquisicao
                        item_alvo.save()
                        reativados += 1
                    else:
                        # SOMAR quantidade
                        item_alvo.quantidade += quantidade
                        # Atualiza campos se informados
                        if descricao: item_alvo.descricao = descricao
                        if departamento != 'OUT': item_alvo.departamento = departamento
                        if categoria: item_alvo.categoria = categoria
                        if fornecedor: item_alvo.fornecedor = fornecedor
                        if marca: item_alvo.marca = marca
                        if validade_ca: item_alvo.validade_ca = validade_ca
                        if data_aquisicao: item_alvo.data_aquisicao = data_aquisicao
                        if valor_unitario: item_alvo.valor_unitario = valor_unitario
                        item_alvo.save()
                        somados += 1
                else:
                    # ===== NENHUM ITEM IGUAL - CRIAR NOVO =====
                    Item.objects.create(
                        codigo=codigo,
                        nome=nome,
                        descricao=descricao,
                        departamento=departamento,
                        categoria=categoria,
                        quantidade=quantidade,
                        unidade=unidade,
                        localizacao=localizacao,
                        estoque_minimo=estoque_minimo,
                        valor_unitario=valor_unitario,
                        fornecedor=fornecedor,
                        marca=marca,
                        lote=lote,
                        ca=ca,
                        validade_ca=validade_ca,
                        data_aquisicao=data_aquisicao,
                        ativo=True
                    )
                    importados += 1
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                erros.append(f'Linha {row_idx}: {str(e)}')
        
        # Montar mensagem
        partes = []
        if importados > 0: partes.append(f'{importados} novos')
        if somados > 0: partes.append(f'{somados} somados')
        if reativados > 0: partes.append(f'{reativados} reativados')
        
        mensagem = 'Importação concluída!'
        if partes:
            mensagem += ' ' + ', '.join(partes) + '.'
        if erros:
            mensagem += f' ({len(erros)} erros)'
        
        return JsonResponse({
            'success': True,
            'message': mensagem,
            'erros': erros[:20]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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
    response['Content-Disposition'] = f'attachment; filename=saidas_{date.today().strftime("%Y%m%d")}.xlsx'
    return response


@require_http_methods(["POST"])
def excluir_item(request, pk):
    try:
        item = get_object_or_404(Item, pk=pk)
        item.ativo = False
        item.save()
        return JsonResponse({'success': True, 'message': f'Item {item.codigo} desativado!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)