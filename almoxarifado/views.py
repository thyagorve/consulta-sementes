import json
from datetime import date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q, Sum, Count
from django.contrib import messages
from .models import Item, Saida, Departamento


@ensure_csrf_cookie
def lista_itens(request):
    """View principal - lista itens com estoque"""
    mostrar_todos = request.GET.get('todos', '0') == '1'
    
    if mostrar_todos:
        itens = Item.objects.filter(ativo=True)
    else:
        itens = Item.objects.filter(quantidade__gt=0, ativo=True)
    
    # Busca
    busca = request.GET.get('busca', '')
    if busca:
        itens = itens.filter(
            Q(nome__icontains=busca) | 
            Q(codigo__icontains=busca) |
            Q(localizacao__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(fornecedor__icontains=busca)
        )
    
    # Filtro por departamento
    departamento = request.GET.get('departamento', '')
    if departamento:
        itens = itens.filter(departamento=departamento)
    
    # Ordenação
    ordenar = request.GET.get('ordenar', 'nome')
    if ordenar == 'quantidade':
        itens = itens.order_by('quantidade')
    elif ordenar == '-quantidade':
        itens = itens.order_by('-quantidade')
    elif ordenar == 'recente':
        itens = itens.order_by('-updated_at')
    else:
        itens = itens.order_by('nome')
    
    # Estatísticas
    total_itens = itens.count()
    total_quantidade = itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
    context = {
        'itens': itens,
        'busca': busca,
        'departamento': departamento,
        'mostrar_todos': mostrar_todos,
        'ordenar': ordenar,
        'departamentos': Departamento.choices,
        'total_itens': total_itens,
        'total_quantidade': total_quantidade,
    }
    return render(request, 'almoxarifado/lista_itens.html', context)


def saidas_list(request):
    """View do histórico de saídas"""
    saidas = Saida.objects.select_related('item').all().order_by('-data', '-hora')
    
    # Busca
    busca = request.GET.get('busca', '')
    if busca:
        saidas = saidas.filter(
            Q(solicitante__icontains=busca) | 
            Q(item_nome__icontains=busca) |
            Q(item_codigo__icontains=busca) |
            Q(observacao__icontains=busca)
        )
    
    # Filtro por data
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        saidas = saidas.filter(data__gte=data_inicio)
    if data_fim:
        saidas = saidas.filter(data__lte=data_fim)
    
    # Filtro por departamento
    dept = request.GET.get('dept', '')
    if dept:
        saidas = saidas.filter(departamento=dept)
    
    # Estatísticas
    total_saidas = saidas.count()
    total_itens_retirados = saidas.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
    context = {
        'saidas': saidas,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'dept': dept,
        'departamentos': Departamento.choices,
        'total_saidas': total_saidas,
        'total_itens_retirados': total_itens_retirados,
    }
    return render(request, 'almoxarifado/saidas_list.html', context)


@require_http_methods(["GET"])
def buscar_por_codigo(request):
    """Busca item por código para autocompletar"""
    codigo = request.GET.get('codigo', '').strip()
    
    if not codigo:
        return JsonResponse({'encontrado': False})
    
    try:
        item = Item.objects.get(codigo=codigo, ativo=True)
        return JsonResponse({
            'encontrado': True,
            'item': {
                'id': item.id,
                'codigo': item.codigo,
                'nome': item.nome,
                'descricao': item.descricao,
                'departamento': item.departamento,
                'unidade': item.unidade,
                'localizacao': item.localizacao,
                'estoque_minimo': item.estoque_minimo,
                'valor_unitario': float(item.valor_unitario) if item.valor_unitario else None,
                'fornecedor': item.fornecedor,
                'quantidade': item.quantidade,
            }
        })
    except Item.DoesNotExist:
        return JsonResponse({'encontrado': False})
    except Item.MultipleObjectsReturned:
        return JsonResponse({'encontrado': False, 'error': 'Múltiplos itens com este código'})


@require_http_methods(["POST"])
def adicionar_item(request):
    """Adiciona novo item ao estoque"""
    try:
        nome = request.POST.get('nome', '').strip()
        quantidade = int(request.POST.get('quantidade', 0))
        codigo = request.POST.get('codigo', '').strip()
        departamento = request.POST.get('departamento', 'OUT')
        unidade = request.POST.get('unidade', 'UN')
        localizacao = request.POST.get('localizacao', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        estoque_minimo = int(request.POST.get('estoque_minimo', 5))
        valor_unitario = request.POST.get('valor_unitario', '').strip()
        fornecedor = request.POST.get('fornecedor', '').strip()
        
        # Validações
        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome do item é obrigatório'}, status=400)
        
        if quantidade < 0:
            return JsonResponse({'success': False, 'error': 'Quantidade não pode ser negativa'}, status=400)
        
        if estoque_minimo < 0:
            return JsonResponse({'success': False, 'error': 'Estoque mínimo não pode ser negativo'}, status=400)
        
        # Se informou código, verifica se já existe
        if codigo:
            item_existente_codigo = Item.objects.filter(codigo=codigo).first()
            if item_existente_codigo:
                # Se mesmo código, pergunta se quer somar
                if request.POST.get('somar', 'false') == 'true':
                    item_existente_codigo.quantidade += quantidade
                    if localizacao:
                        item_existente_codigo.localizacao = localizacao
                    if descricao:
                        item_existente_codigo.descricao = descricao
                    if fornecedor:
                        item_existente_codigo.fornecedor = fornecedor
                    if valor_unitario:
                        item_existente_codigo.valor_unitario = float(valor_unitario.replace(',', '.'))
                    item_existente_codigo.save()
                    
                    if 'foto' in request.FILES:
                        item_existente_codigo.foto = request.FILES['foto']
                        item_existente_codigo.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Quantidade somada ao item {codigo}!',
                        'item': {
                            'id': item_existente_codigo.id,
                            'codigo': item_existente_codigo.codigo,
                            'nome': item_existente_codigo.nome,
                            'quantidade': item_existente_codigo.quantidade,
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'codigo_existente': True,
                        'error': f'Código {codigo} já existe! Item: {item_existente_codigo.nome}'
                    }, status=409)
        
        # Verifica se já existe item com mesmo nome (apenas se não informou código)
        if not codigo:
            item_existente_nome = Item.objects.filter(nome__iexact=nome, ativo=True).first()
            if item_existente_nome and request.POST.get('somar', 'false') == 'false':
                return JsonResponse({
                    'success': False,
                    'nome_existente': True,
                    'item_id': item_existente_nome.id,
                    'nome': item_existente_nome.nome,
                    'codigo': item_existente_nome.codigo,
                    'quantidade': item_existente_nome.quantidade,
                    'unidade': item_existente_nome.get_unidade_display(),
                    'error': f'Item "{nome}" (Cód: {item_existente_nome.codigo}) já existe com {item_existente_nome.quantidade} {item_existente_nome.get_unidade_display()}. Deseja somar?'
                }, status=409)
        
        # Cria novo item
        valor = float(valor_unitario.replace(',', '.')) if valor_unitario else None
        
        item = Item.objects.create(
            nome=nome,
            codigo=codigo if codigo else None,  # None para auto-gerar
            quantidade=quantidade,
            departamento=departamento,
            unidade=unidade,
            localizacao=localizacao if localizacao else None,
            descricao=descricao if descricao else None,
            estoque_minimo=estoque_minimo,
            valor_unitario=valor,
            fornecedor=fornecedor if fornecedor else None,
        )
        
        # Processa foto
        if 'foto' in request.FILES:
            item.foto = request.FILES['foto']
            item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Item {item.codigo} - {item.nome} criado com sucesso!',
            'item': {
                'id': item.id,
                'codigo': item.codigo,
                'nome': item.nome,
                'quantidade': item.quantidade,
                'unidade': item.get_unidade_display(),
                'localizacao': item.localizacao,
            }
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Valor inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def editar_item(request, pk):
    """Edita um item existente"""
    try:
        item = get_object_or_404(Item, pk=pk)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Atualiza campos
        if 'nome' in data and data['nome'].strip():
            item.nome = data['nome'].strip()
        if 'descricao' in data:
            item.descricao = data['descricao'].strip()
        if 'departamento' in data:
            item.departamento = data['departamento']
        if 'unidade' in data:
            item.unidade = data['unidade']
        if 'localizacao' in data:
            item.localizacao = data['localizacao'].strip()
        if 'estoque_minimo' in data:
            item.estoque_minimo = int(data['estoque_minimo'])
        if 'valor_unitario' in data and data['valor_unitario']:
            item.valor_unitario = float(str(data['valor_unitario']).replace(',', '.'))
        if 'fornecedor' in data:
            item.fornecedor = data['fornecedor'].strip()
        if 'ativo' in data:
            item.ativo = data['ativo'] in [True, 'true', '1', 1]
        
        if 'foto' in request.FILES:
            item.foto = request.FILES['foto']
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Item {item.codigo} atualizado com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def detalhe_item(request, pk):
    """Retorna JSON com detalhes do item"""
    item = get_object_or_404(Item, pk=pk)
    
    # Últimas saídas deste item
    ultimas_saidas = item.saidas.all().order_by('-data', '-hora')[:5]
    
    data = {
        'id': item.id,
        'codigo': item.codigo,
        'nome': item.nome,
        'quantidade': item.quantidade,
        'unidade': item.get_unidade_display(),
        'departamento': item.get_departamento_display(),
        'localizacao': item.localizacao or 'Não definida',
        'descricao': item.descricao or 'Sem descrição',
        'estoque_minimo': item.estoque_minimo,
        'valor_unitario': float(item.valor_unitario) if item.valor_unitario else None,
        'valor_total': float(item.valor_total) if item.valor_total else None,
        'fornecedor': item.fornecedor or 'Não informado',
        'status_estoque': item.status_estoque,
        'foto_url': item.foto.url if item.foto else None,
        'created_at': item.created_at.strftime('%d/%m/%Y %H:%M'),
        'updated_at': item.updated_at.strftime('%d/%m/%Y %H:%M'),
        'ultimas_saidas': [
            {
                'data': s.data.strftime('%d/%m/%Y'),
                'hora': s.hora.strftime('%H:%M'),
                'solicitante': s.solicitante,
                'quantidade': s.quantidade,
                'observacao': s.observacao[:50] if s.observacao else '',
            } for s in ultimas_saidas
        ]
    }
    
    return JsonResponse(data)


@require_http_methods(["POST"])
def dar_baixa(request, pk):
    """Processa baixa de item do estoque"""
    try:
        item = get_object_or_404(Item, pk=pk)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        solicitante = data.get('solicitante', '').strip()
        quantidade = int(data.get('quantidade', 0))
        data_saida = data.get('data', date.today().isoformat())
        hora_saida = data.get('hora', datetime.now().strftime('%H:%M'))
        departamento = data.get('departamento', '')
        observacao = data.get('observacao', '').strip()
        
        # Validações
        if not solicitante:
            return JsonResponse({'success': False, 'error': 'Solicitante é obrigatório'}, status=400)
        
        if quantidade <= 0:
            return JsonResponse({'success': False, 'error': 'Quantidade deve ser maior que zero'}, status=400)
        
        if quantidade > item.quantidade:
            return JsonResponse({
                'success': False, 
                'error': f'Quantidade insuficiente! Estoque: {item.quantidade} {item.get_unidade_display()}'
            }, status=400)
        
        # Cria registro de saída
        saida = Saida.objects.create(
            item=item,
            item_nome=item.nome,
            item_codigo=item.codigo,
            solicitante=solicitante,
            departamento=departamento if departamento else None,
            quantidade=quantidade,
            data=data_saida,
            hora=hora_saida,
            observacao=observacao
        )
        
        # Atualiza estoque
        item.quantidade -= quantidade
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Baixa de {quantidade} {item.get_unidade_display()} realizada!',
            'saida': {
                'id': saida.id,
                'solicitante': solicitante,
                'item_codigo': item.codigo,
                'item_nome': item.nome,
                'quantidade': quantidade,
                'estoque_restante': item.quantidade
            }
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Valor inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def excluir_item(request, pk):
    """Soft delete de um item"""
    try:
        item = get_object_or_404(Item, pk=pk)
        item.ativo = False
        item.save()
        return JsonResponse({'success': True, 'message': f'Item {item.codigo} desativado!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

def buscar_itens_ajax(request):
    """Busca itens via AJAX (sem recarregar página)"""
    busca = request.GET.get('busca', '')
    departamento = request.GET.get('departamento', '')
    mostrar_todos = request.GET.get('todos', '0') == '1'
    ordenar = request.GET.get('ordenar', 'nome')
    
    if mostrar_todos:
        itens = Item.objects.filter(ativo=True)
    else:
        itens = Item.objects.filter(quantidade__gt=0, ativo=True)
    
    if busca:
        itens = itens.filter(
            Q(nome__icontains=busca) | 
            Q(codigo__icontains=busca) |
            Q(localizacao__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(fornecedor__icontains=busca)
        )
    
    if departamento:
        itens = itens.filter(departamento=departamento)
    
    if ordenar == 'quantidade':
        itens = itens.order_by('quantidade')
    elif ordenar == '-quantidade':
        itens = itens.order_by('-quantidade')
    elif ordenar == 'recente':
        itens = itens.order_by('-updated_at')
    else:
        itens = itens.order_by('nome')
    
    data = {
        'itens': [
            {
                'id': item.id,
                'codigo': item.codigo,
                'nome': item.nome,
                'quantidade': item.quantidade,
                'unidade': item.get_unidade_display(),
                'localizacao': item.localizacao or '-',
                'departamento': item.get_departamento_display(),
                'status_estoque': item.status_estoque,
            }
            for item in itens
        ],
        'total_itens': itens.count(),
        'total_quantidade': itens.aggregate(Sum('quantidade'))['quantidade__sum'] or 0,
    }
    
    return JsonResponse(data)