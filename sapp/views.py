# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.core.serializers.json import DjangoJSONEncoder 
from .models import HistoricoMovimentacao
from .models import OrigemDestino

# Adicione no topo com os outros imports
import datetime
from django import forms  #
# Python imports
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import random
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ArmazemLayout, ElementoMapa, Estoque
import json
from django.utils import timezone


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# App imports
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario, Especie, OrigemDestino,Armazem, Endereco  
)
from .forms import (
    NovaEntradaForm, ConfiguracaoForm, CultivarForm, PeneiraForm, 
    CategoriaForm, TratamentoForm, NovoConferenteUserForm, MudarSenhaForm  
)

# Pandas e outros imports
import pandas as pd
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import json
from django.db import transaction
import tempfile
import os

from django.db import transaction
from .models import FotoMovimentacao # e os outros models   
    

# No início de views.py, com os outros imports de models
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario,
    # Adicione estes:
    Empenho, ItemEmpenho, EmpenhoStatus
)


from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from sapp.models import Estoque, Cultivar, Peneira, Categoria, Tratamento, Especie
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, TratamentoForm
)

# views.py - ARQUIVO COMPLETO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto, Estoque,
    HistoricoMovimentacao, Empenho, ItemEmpenho,
    ArmazemLayout, ElementoMapa
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, 
    TratamentoForm, ProdutoForm, NovaEntradaForm
)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto, Estoque
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, 
    TratamentoForm, ProdutoForm
)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Q

from .models import (
    Estoque,
    Empenho,
    ItemEmpenho,
    EmpenhoStatus,
    HistoricoMovimentacao
)
from django.contrib.admin.views.decorators import staff_member_required 
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ArmazemLayout, ElementoMapa, Estoque
import json
# ================================================================
# FUNÇÕES AUXILIARES (ADICIONAR NO TOPO DO ARQUIVO views.py)
# ================================================================
def processar_inteiro(valor, default=0):
    """Converte valor para inteiro com segurança"""
    if valor is None or valor == '':
        return default
    
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, mantendo ponto decimal para conversão
            valor_limpo = ''
            for char in valor:
                if char.isdigit() or char in '.,':
                    valor_limpo += char
            valor = valor_limpo.replace(',', '.')
            
            if '.' in valor:
                # Se tiver decimal, arredonda para baixo
                return int(float(valor))
            else:
                return int(valor) if valor else default
        else:
            return int(valor)
    except (ValueError, TypeError, AttributeError):
        return default

def processar_decimal(valor, default=Decimal('0.00')):
    """Converte valor para Decimal com segurança"""
    if valor is None:
        return default
    
    try:
        if isinstance(valor, str):
            valor = valor.replace(',', '.')
            # Remove caracteres não numéricos, mantendo ponto decimal
            valor = ''.join(c for c in valor if c.isdigit() or c == '.' or c == '-')
            if not valor:
                return default
        
        # Converte para Decimal, limitando casas decimais
        return Decimal(str(valor)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return default


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from .models import Estoque, HistoricoMovimentacao, Especie, Cultivar, Peneira

@login_required
def dashboard(request):
    """Dashboard inicial"""
    context = {
        'tipos_semente': Especie.objects.filter(estoque__saldo__gt=0).values_list('nome', flat=True).distinct().order_by('nome'),
        'cultivares_lista': Cultivar.objects.filter(estoque__saldo__gt=0).distinct().order_by('nome'),
        'peneiras_lista': Peneira.objects.filter(estoque__saldo__gt=0).distinct().order_by('nome'),
        'armazens_lista': Estoque.objects.filter(saldo__gt=0).exclude(az__isnull=True).exclude(az='').values_list('az', flat=True).distinct().order_by('az'),
    }
    return render(request, 'sapp/dashboard.html', context)


@login_required
def dashboard_data(request):
    """Endpoint AJAX para dados do dashboard"""
    try:
        # Receber filtros (listas)
        tipos_semente = request.GET.getlist('tipo_semente[]')
        cultivares = request.GET.getlist('cultivar[]')
        peneiras = request.GET.getlist('peneira[]')
        unidades = request.GET.getlist('unidade[]')
        armazens = request.GET.getlist('armazem[]')
        data_inicio = request.GET.get('data_inicio', '').strip()
        data_fim = request.GET.get('data_fim', '').strip()
        tipo_mov = request.GET.get('tipo_mov', '').strip()
        search = request.GET.get('search', '').strip()
        
        # Base queries
        est_qs = Estoque.objects.filter(saldo__gt=0)
        mov_qs = HistoricoMovimentacao.objects.select_related('estoque', 'usuario')
        
        # Aplicar filtros de estoque
        if tipos_semente:
            est_qs = est_qs.filter(especie__nome__in=tipos_semente)
        
        if cultivares:
            est_qs = est_qs.filter(cultivar_id__in=cultivares)
        
        if peneiras:
            est_qs = est_qs.filter(peneira_id__in=peneiras)
        
        if unidades:
            est_qs = est_qs.filter(embalagem__in=unidades)
        
        if armazens:
            est_qs = est_qs.filter(az__in=armazens)
        
        if search:
            est_qs = est_qs.filter(
                Q(lote__icontains=search) | 
                Q(cultivar__nome__icontains=search) |
                Q(especie__nome__icontains=search)
            )
        
        # Aplicar filtros de movimentação
        mov_qs = mov_qs.filter(estoque__in=est_qs)
        
        # Filtros de data
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                mov_qs = mov_qs.filter(data_hora__date__gte=data_inicio_obj)
            except:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                mov_qs = mov_qs.filter(data_hora__date__lte=data_fim_obj)
            except:
                pass
        
        if tipo_mov:
            mov_qs = mov_qs.filter(tipo__iexact=tipo_mov)
        
        # Calcular KPIs
        bags = est_qs.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
        scs = est_qs.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
        total_sc = (bags * 25) + scs
        
        kpis = {
            'total_sc': int(total_sc),
            'bags': int(bags),
            'scs': int(scs),
            'peso': float(est_qs.aggregate(s=Sum('peso_total'))['s'] or 0),
            'ativos': est_qs.count(),
            'parados': est_qs.filter(data_ultima_movimentacao__lt=timezone.now() - timedelta(days=30)).count()
        }
        
        # Dados dos gráficos
        cores_padrao = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1']
        
        cultivares_data = list(est_qs.filter(cultivar__isnull=False)
                               .values('cultivar__nome')
                               .annotate(volume=Sum('saldo'))
                               .filter(volume__gt=0)
                               .order_by('-volume')[:10])
        
        peneiras_data = list(est_qs.filter(peneira__isnull=False)
                             .values('peneira__nome')
                             .annotate(volume=Sum('saldo'))
                             .filter(volume__gt=0)
                             .order_by('-volume'))
        
        armazens_data = list(est_qs.exclude(az__isnull=True).exclude(az='')
                             .values('az')
                             .annotate(volume=Sum('saldo'))
                             .filter(volume__gt=0)
                             .order_by('az'))
        
        # Tendência
        data_limite = timezone.now() - timedelta(days=15)
        tendencia_data = list(mov_qs.filter(data_hora__date__gte=data_limite.date())
                              .annotate(dia=TruncDate('data_hora'))
                              .values('dia')
                              .annotate(
                                  entradas=Count('id', filter=Q(tipo__iexact='Entrada')),
                                  saidas=Count('id', filter=Q(tipo__iexact='Saída'))
                              )
                              .order_by('dia'))
        
        graficos = {
            'cultivar': {
                'labels': [d['cultivar__nome'] for d in cultivares_data],
                'values': [int(d['volume']) for d in cultivares_data],
                'colors': cores_padrao[:len(cultivares_data)]
            },
            'peneira': {
                'labels': [d['peneira__nome'] for d in peneiras_data],
                'values': [int(d['volume']) for d in peneiras_data],
                'colors': cores_padrao[:len(peneiras_data)]
            },
            'armazem': {
                'labels': [d['az'] for d in armazens_data],
                'values': [int(d['volume']) for d in armazens_data],
                'colors': cores_padrao[:len(armazens_data)]
            },
            'tendencia': {
                'labels': [d['dia'].strftime('%d/%m') for d in tendencia_data],
                'entradas': [d['entradas'] for d in tendencia_data],
                'saidas': [d['saidas'] for d in tendencia_data]
            }
        }
        
        # Opções de filtros (encadeamento)
        opcoes_filtros = {
            'tipos_semente': list(est_qs.values_list('especie__nome', flat=True).distinct().order_by('especie__nome')),
            'cultivares': list(est_qs.filter(cultivar__isnull=False).values('cultivar_id', 'cultivar__nome').distinct().order_by('cultivar__nome')),
            'peneiras': list(est_qs.filter(peneira__isnull=False).values('peneira_id', 'peneira__nome').distinct().order_by('peneira__nome')),
            'armazens': list(est_qs.exclude(az__isnull=True).exclude(az='').values_list('az', flat=True).distinct().order_by('az'))
        }
        
        # Movimentações recentes
        movimentacoes = []
        for mov in mov_qs.order_by('-data_hora')[:10]:
            movimentacoes.append({
                'dt': mov.data_hora.strftime('%d/%m/%Y %H:%M') if mov.data_hora else '--',
                'tp': mov.tipo or '--',
                'lt': mov.lote_ref or (mov.estoque.lote if mov.estoque else '--'),
                'unidade': mov.estoque.embalagem if mov.estoque else '--',
                'qtd': getattr(mov, 'quantidade', 0),
                'us': mov.usuario.username if mov.usuario else 'Sistema'
            })
        
        return JsonResponse({
            'success': True,
            'kpis': kpis,
            'graficos': graficos,
            'recentes': movimentacoes,
            'opcoes_filtros': opcoes_filtros
        })
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
# ================================================================
# LISTA DE ESTOQUE (TABELA PRINCIPAL)
# ================================================================

@login_required
def lista_estoque(request, template_name='sapp/tabela_estoque.html'):
    """
    View para a página principal de estoque - MOSTRA TODOS OS LOTES
    """
    
    # QuerySet Base - TODOS os lotes (inclusive zerados) PARA EXIBIÇÃO
    qs = Estoque.objects.all().select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente'
    ).order_by('-data_ultima_movimentacao', '-id')
    
    # QuerySet Base para MÉTRICAS - TODOS os lotes (para os cards)
    qs_metrics = Estoque.objects.all()
    
    
    # FILTRO POR STATUS
    status = request.GET.get('status', 'todos')
    if status == 'disponivel':
        qs = qs.filter(saldo__gt=0)
    elif status == 'esgotado':
        qs = qs.filter(saldo=0)

    # Busca Global
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(especie__nome__icontains=termo) |
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo)
            )

    # Aplicar filtros sequenciais - COM SUPORTE A VALORES VAZIOS (__null__)
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }

    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        # REMOVER VALORES VAZIOS
        values = [v for v in values if v and v.strip()]
        
        # VERIFICAR SE TEM O VALOR ESPECIAL __null__ (VAZIO)
        tem_null = '__null__' in values
        if tem_null:
            values.remove('__null__')
        
        if values and tem_null:
            # CASO: TEM VALORES ESPECÍFICOS E TAMBÉM QUER VAZIOS
            q = Q(**{lookup: values}) | Q(**{f"{param}__isnull": True}) | Q(**{f"{param}": ''})
            qs = qs.filter(q)
        elif values:
            # CASO: SÓ VALORES ESPECÍFICOS
            qs = qs.filter(**{lookup: values})
        elif tem_null:
            # CASO: SÓ VAZIOS
            qs = qs.filter(Q(**{f"{param}__isnull": True}) | Q(**{f"{param}": ''}))

    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            qs = qs.filter(**{f'{field}__gte': min_val})
        if max_val:
            qs = qs.filter(**{f'{field}__lte': max_val})

    # MÉTRICAS PARA OS CARDS - Usando o queryset NÃO FILTRADO (qs_metrics)
    # CARD 1: Lotes Ativos (APENAS saldo > 0)
    total_itens_ativos = qs_metrics.filter(saldo__gt=0).count()
    
    # CARD 2: SC Equivalente (somente saldo > 0)
    saldo_bags = qs_metrics.filter(embalagem='BAG', saldo__gt=0).aggregate(s=Sum('saldo'))['s'] or 0
    saldo_sc = qs_metrics.filter(embalagem='SC', saldo__gt=0).aggregate(s=Sum('saldo'))['s'] or 0
    saldo_total_sc = (saldo_bags * 25) + saldo_sc
    origens = OrigemDestino.objects.all().order_by('nome')
    # CARD 3: Unidades BAG (somente saldo > 0)
    saldo_bags_total = qs_metrics.filter(embalagem='BAG', saldo__gt=0).aggregate(s=Sum('saldo'))['s'] or 0
    
    # CARD 4: PME Total (KG)
    pme_total = qs_metrics.filter(saldo__gt=0).aggregate(s=Sum('peso_total'))['s'] or Decimal('0.00')
    
    # CARD 5: Clientes Únicos (somente saldo > 0)
    clientes_unicos = qs_metrics.filter(
        saldo__gt=0
    ).exclude(
        cliente__isnull=True
    ).exclude(
        cliente=''
    ).values('cliente').distinct().count()

    # Opções de Filtro (baseadas no queryset filtrado qs, NÃO no qs_metrics)
    def get_options_list(field_lookup, param_name):
        vals = qs.values_list(field_lookup, flat=True).distinct().order_by(field_lookup)
        options = [str(v) for v in vals if v is not None and str(v).strip() != '']
        # Ordenar e retornar
        return sorted(options)

    filter_options = {
        'az': get_options_list('az', 'az'),
        'lote': get_options_list('lote', 'lote'),
        'produto': get_options_list('produto', 'produto'),
        'cultivar': get_options_list('cultivar__nome', 'cultivar'),
        'peneira': get_options_list('peneira__nome', 'peneira'),
        'categoria': get_options_list('categoria__nome', 'categoria'),
        'endereco': get_options_list('endereco', 'endereco'),
        'especie': get_options_list('especie__nome', 'especie'),
        'tratamento': get_options_list('tratamento__nome', 'tratamento'),
        'embalagem': get_options_list('embalagem', 'embalagem'),
        'cliente': get_options_list('cliente', 'cliente'),
        'empresa': get_options_list('empresa', 'empresa'),
        'conferente': get_options_list('conferente__username', 'conferente')
    }

    # Paginação
    page_size = request.GET.get('page_size', 25)
    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    context = {
        'estoque': page_obj,
        'itens': page_obj,
        'status': status,
        'busca': busca,
        'total_itens': total_itens_ativos,  # CARD 1: APENAS saldo > 0
        'total_sc': saldo_total_sc,          # CARD 2: APENAS saldo > 0
        'total_bags': saldo_bags_total,      # CARD 3: APENAS saldo > 0
        'total_pme': pme_total,              # CARD 4: NOVO CARD
        'clientes_unicos': clientes_unicos,  # CARD 5: APENAS saldo > 0
        'filter_options': filter_options,
        'url_params': query_params.urlencode(),
        'page_sizes': [10, 25, 50, 100, 200],
        'page_size': page_size,
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
        'all_especies': Especie.objects.all(),
        'origens': origens,
    }
    
    return render(request, template_name, context)


@login_required
def gestao_estoque(request, template_name='sapp/gestao_estoque.html'):
    """
    View para gestão de estoque - MOSTRA APENAS LOTES COM SALDO > 0
    """
    
    # QuerySet Base - APENAS LOTES COM SALDO > 0 - NUNCA mostrar saldo zero
    qs = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente'
    ).order_by('-data_ultima_movimentacao', '-id')
    
    # NÃO existe qs_metrics separado - tudo deve usar o mesmo filtro
    
    # FILTRO POR STATUS SISTÊMICO
    status_filter = request.GET.getlist('status_sistemico')
    if status_filter:
        if '__null__' in status_filter:
            qs = qs.filter(
                Q(status_sistemico__in=[s for s in status_filter if s != '__null__']) | 
                Q(status_sistemico__isnull=True)
            )
        else:
            qs = qs.filter(status_sistemico__in=status_filter)
    
    # Busca Global
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(especie__nome__icontains=termo) |
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo)
            )

    # Aplicar filtros sequenciais
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }

    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        values = [v for v in values if v and v.strip()]
        
        if values:
            if '__null__' in values:
                specific_values = [v for v in values if v != '__null__']
                if specific_values:
                    qs = qs.filter(
                        Q(**{lookup: specific_values}) | 
                        Q(**{lookup.replace('__in', '__isnull'): True})
                    )
                else:
                    qs = qs.filter(**{lookup.replace('__in', '__isnull'): True})
            else:
                qs = qs.filter(**{lookup: values})

    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            try:
                qs = qs.filter(**{f'{field}__gte': float(min_val)})
            except ValueError:
                pass
        if max_val:
            try:
                qs = qs.filter(**{f'{field}__lte': float(max_val)})
            except ValueError:
                pass

    # MÉTRICAS - usando o mesmo queryset filtrado
    saldo_bags = qs.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_sc = qs.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_total_sc = (saldo_bags * 25) + saldo_sc
    
    total_pme = qs.aggregate(s=Sum('peso_total'))['s'] or 0
    
    # Opções de Filtro - baseadas no queryset COMPLETO (com saldo > 0)
    base_options_qs = Estoque.objects.filter(saldo__gt=0)
    
    def get_options_list(field_lookup):
        vals = base_options_qs.values_list(field_lookup, flat=True).distinct().order_by(field_lookup)
        options = []
        for v in vals:
            if v is not None and str(v).strip() != '':
                options.append(str(v))
        return options

    status_options = ['ok', 'parcial', 'critico']
    
    filter_options = {
        'status_sistemico': status_options,
        'az': get_options_list('az'),
        'lote': get_options_list('lote'),
        'produto': get_options_list('produto'),
        'cultivar': get_options_list('cultivar__nome'),
        'peneira': get_options_list('peneira__nome'),
        'categoria': get_options_list('categoria__nome'),
        'endereco': get_options_list('endereco'),
        'especie': get_options_list('especie__nome'),
        'tratamento': get_options_list('tratamento__nome'),
        'embalagem': get_options_list('embalagem'),
        'cliente': get_options_list('cliente'),
        'empresa': get_options_list('empresa'),
        'conferente': get_options_list('conferente__username')
    }

    # Paginação
    page_size = request.GET.get('page_size', 25)
    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    total_itens = qs.count()
    clientes_unicos = qs.exclude(cliente__isnull=True).exclude(cliente='').values('cliente').distinct().count()

    context = {
        'estoque': page_obj,
        'itens': page_obj,
        'busca': busca,
        'total_itens': total_itens,
        'total_sc': saldo_total_sc,
        'total_bags': saldo_bags,
        'total_sc_fisico': saldo_sc,
        'total_pme': total_pme,
        'clientes_unicos': clientes_unicos,
        'filter_options': filter_options,
        'url_params': query_params.urlencode(),
        'page_sizes': [10, 25, 50, 100, 200],
        'page_size': page_size,
    }
    
    return render(request, template_name, context)

@login_required
def registrar_saida(request, id):
    print("🔍 [REGISTRAR SAÍDA] Iniciando processamento da expedição")
    
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Captura de Dados
                qtd = int(request.POST.get('quantidade_saida', 0))
                carga = request.POST.get('numero_carga', '')
                motorista = request.POST.get('motorista', '')
                placa = request.POST.get('placa', '')
                cliente = request.POST.get('cliente', '')
                obs = request.POST.get('observacao', '')
                fotos = request.FILES.getlist('fotos')

                print(f"📦 Dados recebidos:")
                print(f"   Quantidade: {qtd}")
                print(f"   Carga: {carga}")
                print(f"   Motorista: {motorista}")
                print(f"   Placa: {placa}")
                print(f"   Cliente: {cliente}")
                print(f"   Obs: {obs}")
                print(f"   Fotos recebidas: {len(fotos)}")

                # 2. Validação Rigorosa
                erros = []
                if qtd <= 0: 
                    erros.append("❌ Quantidade inválida.")
                if qtd > item.saldo: 
                    erros.append(f"❌ Saldo insuficiente. Disponível: {item.saldo}.")
                if not motorista.strip(): 
                    erros.append("❌ Motorista é obrigatório.")
                if not placa.strip(): 
                    erros.append("❌ Placa é obrigatória.")
                if not carga.strip(): 
                    erros.append("❌ Número da Carga é obrigatório.")
                
                # Fotos são obrigatórias para expedição
                if len(fotos) == 0:
                    erros.append("❌ Pelo menos uma foto é obrigatória na expedição.")
                
                if erros:
                    for e in erros: 
                        print(f"⚠️ {e}")
                        messages.error(request, e)
                    return redirect('sapp:lista_estoque')

                # 3. Salvar estado anterior para histórico
                saldo_anterior = item.saldo
                print(f"💰 Saldo anterior: {saldo_anterior}")

                # 4. Processamento da Saída
                item.saida += qtd
                item.saldo = item.entrada - item.saida
                item.conferente = request.user
                item.data_ultima_saida = timezone.now()
                
                # Atualizar peso total
                if item.peso_unitario and item.peso_unitario > 0:
                    item.peso_total = Decimal(str(item.saldo)) * Decimal(str(item.peso_unitario))
                    item.peso_total = item.peso_total.quantize(Decimal('0.01'))
                
                # Atualizar observação
                obs_historico = f"[EXPEDIÇÃO {timezone.now().strftime('%d/%m/%Y %H:%M')}] Carga: {carga}, Motorista: {motorista}"
                if obs:
                    obs_historico += f" | Obs: {obs}"
                
                if item.observacao:
                    item.observacao += f"\n\n{obs_historico}"
                else:
                    item.observacao = obs_historico
                
                item.save()
                print(f"✅ Item atualizado: {item.lote} | Saldo anterior: {saldo_anterior} → Novo saldo: {item.saldo}")

                # 5. Descrição Rica em HTML para o Histórico
                desc_html = f"""
                    <div class="d-flex flex-column gap-1">
                        <div class="d-flex justify-content-between border-bottom pb-1">
                            <span><strong>Qtd Expedida:</strong> <span class="text-danger">-{qtd}</span></span>
                            <span><strong>Saldo Restante:</strong> {item.saldo}</span>
                        </div>
                        <div class="small text-muted mt-1">
                            <i class="fas fa-truck"></i> <strong>Carga:</strong> {carga} | <strong>Placa:</strong> {placa}<br>
                            <i class="fas fa-id-card"></i> <strong>Motorista:</strong> {motorista}<br>
                            <i class="fas fa-building"></i> <strong>Cliente:</strong> {cliente or 'N/A'}<br>
                            <i class="fas fa-user"></i> <strong>Responsável:</strong> {request.user.get_full_name() or request.user.username}<br>
                            <i class="fas fa-clock"></i> <strong>Data/Hora:</strong> {timezone.now().strftime('%d/%m/%Y %H:%M')}
                        </div>
                        {f'<div class="mt-1 p-1 bg-light rounded small"><strong>Obs:</strong> {obs}</div>' if obs else ''}
                    </div>
                """

                print(f"📝 Criando histórico de movimentação...")

                # 6. Criar histórico de movimentação
                historico = HistoricoMovimentacao.objects.create(
                    estoque=item,
                    usuario=request.user,
                    tipo='Expedição',
                    descricao=desc_html,
                    quantidade=qtd,
                    numero_carga=carga,
                    motorista=motorista,
                    placa=placa,
                    cliente=cliente
                )

                print(f"✅ Histórico criado: ID {historico.id}")

                # 7. **CORREÇÃO CRÍTICA: Salvar Fotos**
                fotos_salvas = 0
                for foto in fotos:
                    try:
                        # CORREÇÃO AQUI: Use o objeto 'historico' diretamente
                        FotoMovimentacao.objects.create(
                            historico=historico,  # Usando o objeto já salvo
                            arquivo=foto,
                            legenda=f"Expedição {carga} - {item.lote} - {timezone.now().strftime('%d/%m/%Y')}"
                        )
                        fotos_salvas += 1
                        print(f"📸 Foto salva: {foto.name} (ID: {historico.id})")
                    except Exception as foto_error:
                        print(f"⚠️ Erro ao salvar foto {foto.name}: {foto_error}")
                        # Não falha a operação por causa de uma foto

                print(f"✅ Fotos salvas: {fotos_salvas}/{len(fotos)}")

                # 8. Mensagem de sucesso
                mensagem_sucesso = f"✅ Expedição da Carga {carga} registrada com sucesso!"
                if fotos_salvas < len(fotos):
                    mensagem_sucesso += f" ({fotos_salvas}/{len(fotos)} fotos salvas)"
                
                messages.success(request, mensagem_sucesso)
                print(f"🎉 Expedição concluída com sucesso!")
                
                # 9. DEBUG: Verificar se fotos foram realmente salvas
                fotos_salvas_query = FotoMovimentacao.objects.filter(historico=historico).count()
                print(f"🔍 DEBUG - Fotos no banco para histórico {historico.id}: {fotos_salvas_query}")

        except Exception as e:
            import traceback
            print(f"💥 ERRO CRÍTICO NA EXPEDIÇÃO:")
            print(f"   Mensagem: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            messages.error(request, f"❌ Erro crítico ao registrar expedição: {str(e)}")
            
    return redirect('sapp:lista_estoque')

from django.views.decorators.csrf import csrf_protect

@csrf_protect
@login_required
def transferir(request, id):
    origem = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                qtd = int(request.POST.get('quantidade', 0))
                tipo_transferencia = request.POST.get('tipo_transferencia', 'normal')
                novo_end = request.POST.get('novo_endereco', '').strip().upper()
                
                # === VALIDAÇÕES BÁSICAS (COMUNS A AMBOS OS TIPOS) ===
                if qtd <= 0:
                    messages.error(request, "❌ Quantidade deve ser maior que zero!")
                    return redirect('sapp:lista_estoque')
                
                if qtd > origem.saldo:
                    messages.error(request, f"❌ Saldo insuficiente. Disponível: {origem.saldo}")
                    return redirect('sapp:lista_estoque')
                
                # Validação de endereço apenas para transferência normal
                if tipo_transferencia == 'normal' and not novo_end:
                    messages.error(request, "❌ Novo endereço é obrigatório para transferência normal!")
                    return redirect('sapp:lista_estoque')
                
                # === 1. SEMPRE DAR BAIXA NA ORIGEM ===
                origem.saida += qtd
                origem.save()  # Saldo é recalculado automaticamente no save()
                
                # === 2. PROCESSAMENTO POR TIPO DE TRANSFERÊNCIA ===
                if tipo_transferencia == 'beneficiamento':
                    # ============================================
                    # CASO 1: ENVIO PARA BENEFICIAMENTO
                    # ============================================
                    
                    # Criar histórico de beneficiamento (NÃO cria destino)
                    descricao_beneficiamento = f"Enviado para beneficiamento – Quantidade: {qtd} {origem.embalagem}"
                    if novo_end:
                        descricao_beneficiamento += f" | Destino referência: {novo_end}"
                    
                    historico_beneficiamento = HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        tipo='Beneficiamento',
                        descricao=descricao_beneficiamento
                    )
                    
                    # Salvar fotos no histórico de beneficiamento
                    for f in request.FILES.getlist('fotos'):
                        FotoMovimentacao.objects.create(historico=historico_beneficiamento, arquivo=f)
                    
                    messages.success(
                        request, 
                        f"✅ Lote enviado para beneficiamento! Quantidade baixada: {qtd} {origem.embalagem}"
                    )
                    
                else:  # tipo_transferencia == 'normal'
                    # ============================================
                    # CASO 2: TRANSFERÊNCIA NORMAL (FLUXO ORIGINAL)
                    # ============================================
                    
                    # BUSCAR OBJETOS RELACIONADOS
                    # Espécie
                    novo_especie_id = request.POST.get('especie')
                    if novo_especie_id and novo_especie_id.strip() != '':
                        obj_especie = get_object_or_404(Especie, id=novo_especie_id)
                    else:
                        obj_especie = origem.especie
                    
                    # Cultivar
                    cultivar_id = request.POST.get('cultivar')
                    if cultivar_id and cultivar_id.strip() != '':
                        obj_cultivar = get_object_or_404(Cultivar, id=cultivar_id)
                    else:
                        obj_cultivar = origem.cultivar
                    
                    # Peneira
                    peneira_id = request.POST.get('peneira')
                    if peneira_id and peneira_id.strip() != '':
                        obj_peneira = get_object_or_404(Peneira, id=peneira_id)
                    else:
                        obj_peneira = origem.peneira
                    
                    # Categoria
                    categoria_id = request.POST.get('categoria')
                    if categoria_id and categoria_id.strip() != '':
                        obj_categoria = get_object_or_404(Categoria, id=categoria_id)
                    else:
                        obj_categoria = origem.categoria
                    
                    # Tratamento
                    tratamento_id = request.POST.get('tratamento')
                    if tratamento_id and tratamento_id.strip() != '':
                        obj_tratamento = get_object_or_404(Tratamento, id=tratamento_id)
                    else:
                        obj_tratamento = origem.tratamento
                    
                    # Processar peso unitário
                    peso_raw = request.POST.get('peso_unitario', origem.peso_unitario or '0')
                    try:
                        peso_raw = str(peso_raw).replace(',', '.')
                        if peso_raw.count('.') > 1:
                            partes = peso_raw.split('.')
                            peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                        novo_peso = Decimal(peso_raw).quantize(Decimal('0.01'))
                    except:
                        novo_peso = origem.peso_unitario or Decimal('0.00')
                    
                    # 🔥 CORREÇÃO: Separar os filtros corretamente
                    # Primeiro, montar dicionário com todos os campos EXCETO saldo__gt
                    campos_base = {
                        'lote': origem.lote,
                        'cultivar': obj_cultivar,
                        'especie': obj_especie,
                        'peneira': obj_peneira,
                        'categoria': obj_categoria,
                        'tratamento': obj_tratamento,
                        'embalagem': request.POST.get('embalagem', origem.embalagem),
                        'empresa': request.POST.get('empresa', origem.empresa or ''),
                        'cliente': request.POST.get('cliente', origem.cliente or ''),
                        'endereco': novo_end,
                    }
                    
                    # Buscar registro existente com MESMO PESO
                    destino_existente = Estoque.objects.filter(
                        **campos_base,
                        peso_unitario=novo_peso,
                        saldo__gt=0  # 🔥 AGORA CORRETO: um único argumento saldo__gt
                    ).first()
                    
                    # 🔥 CORREÇÃO: Buscar registro com PESO DIFERENTE
                    destino_peso_diferente = None
                    if not destino_existente:
                        destino_peso_diferente = Estoque.objects.filter(
                            **campos_base,  # Mesmos campos base
                            saldo__gt=0  # 🔥 AGORA CORRETO
                        ).exclude(
                            peso_unitario=novo_peso  # Exclui quem tem o mesmo peso
                        ).first()
                    
                    if destino_existente:
                        # 🔥 CASO 1: MESMO PESO - PODE SOMAR
                        saldo_anterior = destino_existente.saldo
                        destino_existente.entrada += qtd
                        destino_existente.saldo += qtd
                        
                        # Atualizar campos que podem ter mudado
                        destino_existente.peso_unitario = novo_peso  # Mantém o mesmo peso
                        destino_existente.empresa = request.POST.get('empresa', destino_existente.empresa or '')
                        destino_existente.cliente = request.POST.get('cliente', destino_existente.cliente or '')
                        destino_existente.az = request.POST.get('az', destino_existente.az or '')
                        destino_existente.conferente = request.user
                        
                        # Atualizar observação
                        obs_atual = destino_existente.observacao or ''
                        nova_obs = request.POST.get('observacao', '')
                        if nova_obs:
                            if obs_atual:
                                destino_existente.observacao = f"{obs_atual}\n[TRANSFERÊNCIA {timezone.now().strftime('%d/%m %H:%M')}]: {nova_obs}"
                            else:
                                destino_existente.observacao = f"[TRANSFERÊNCIA {timezone.now().strftime('%d/%m %H:%M')}]: {nova_obs}"
                        
                        destino_existente.save()
                        
                        destino = destino_existente
                        mensagem_tipo = f"somado ao registro existente (Saldo anterior: {saldo_anterior}, Peso: {novo_peso} kg)"
                        
                        print(f"✅ Somando ao lote existente com mesmo peso: {origem.lote} | Peso: {novo_peso} kg")
                        
                    elif destino_peso_diferente:
                        # 🔥 CASO 2: PESO DIFERENTE - NÃO SOMA, CRIA NOVO REGISTRO
                        print(f"⚠️ Lote {origem.lote} já existe em {novo_end} com peso DIFERENTE ({destino_peso_diferente.peso_unitario} kg vs {novo_peso} kg)")
                        
                        # Avisar ao usuário
                        messages.warning(
                            request,
                            f"⚠️ Já existe um lote {origem.lote} em {novo_end} com peso {destino_peso_diferente.peso_unitario} kg. "
                            f"Como o peso é diferente ({novo_peso} kg), foi criado um NOVO registro."
                        )
                        
                        # Criar NOVO registro (não somar)
                        destino = Estoque.objects.create(
                            lote=origem.lote,
                            endereco=novo_end,
                            entrada=qtd,
                            saldo=qtd,
                            conferente=request.user,
                            origem_destino=f"Transferência de {origem.endereco}",
                            
                            # Campos de texto com fallback
                            produto=request.POST.get('produto', origem.produto or ''),
                            cliente=request.POST.get('cliente', origem.cliente or ''),
                            empresa=request.POST.get('empresa', origem.empresa or ''),
                            az=request.POST.get('az', origem.az or ''),
                            peso_unitario=novo_peso,  # Peso NOVO
                            embalagem=request.POST.get('embalagem', origem.embalagem),
                            observacao=request.POST.get('observacao', origem.observacao or '') + f" [Peso: {novo_peso} kg - DIFERENTE DO EXISTENTE]",
                            
                            # Foreign Keys (Objetos, não IDs)
                            especie=obj_especie,
                            cultivar=obj_cultivar,
                            peneira=obj_peneira,
                            categoria=obj_categoria,
                            tratamento=obj_tratamento,
                        )
                        mensagem_tipo = f"criado no novo endereço (peso diferente: {novo_peso} kg)"
                        
                    else:
                        # 🔥 CASO 3: NÃO EXISTE - CRIAR NOVO REGISTRO
                        destino = Estoque.objects.create(
                            lote=origem.lote,
                            endereco=novo_end,
                            entrada=qtd,
                            saldo=qtd,
                            conferente=request.user,
                            origem_destino=f"Transferência de {origem.endereco}",
                            
                            # Campos de texto com fallback
                            produto=request.POST.get('produto', origem.produto or ''),
                            cliente=request.POST.get('cliente', origem.cliente or ''),
                            empresa=request.POST.get('empresa', origem.empresa or ''),
                            az=request.POST.get('az', origem.az or ''),
                            peso_unitario=novo_peso,
                            embalagem=request.POST.get('embalagem', origem.embalagem),
                            observacao=request.POST.get('observacao', origem.observacao or ''),
                            
                            # Foreign Keys (Objetos, não IDs)
                            especie=obj_especie,
                            cultivar=obj_cultivar,
                            peneira=obj_peneira,
                            categoria=obj_categoria,
                            tratamento=obj_tratamento,
                        )
                        mensagem_tipo = "criado no novo endereço"
                    
                    # Históricos (Saída da origem)
                    hist_saida = HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        tipo='Transferência (Saída)',
                        descricao=f"Transferido para {novo_end} ({destino.lote}) - Quantidade: {qtd} {origem.embalagem} | {mensagem_tipo}"
                    )
                    
                    # Histórico (Entrada no destino)
                    hist_entrada = HistoricoMovimentacao.objects.create(
                        estoque=destino,
                        usuario=request.user,
                        tipo='Transferência (Entrada)',
                        descricao=f"Recebido de {origem.endereco} ({origem.lote}) - Quantidade: {qtd} {origem.embalagem} | Peso: {novo_peso} kg | Novo saldo: {destino.saldo}"
                    )
                    
                    # Salvar fotos na saída (origem)
                    for f in request.FILES.getlist('fotos'):
                        FotoMovimentacao.objects.create(historico=hist_saida, arquivo=f)
                    
                    messages.success(request, f"✅ Transferência concluída! {qtd} unidades {mensagem_tipo} em {novo_end}")
                
        except Exception as e:
            import traceback
            print(f"❌ ERRO NA TRANSFERÊNCIA: {e}")
            print(traceback.format_exc())
            messages.error(request, f"❌ Erro ao transferir: {str(e)}")
            
    return redirect('sapp:lista_estoque')



# No seu views.py
from django.http import JsonResponse

@login_required
def detalhes_estoque_api(request, id):
    """API para retornar dados de um item do estoque"""
    try:
        item = Estoque.objects.get(id=id)
        data = {
            'id': item.id,
            'lote': item.lote,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'produto': item.produto,
            'cliente': item.cliente,
            'empresa': item.empresa,
            'az': item.az,
            'peso_unitario': str(item.peso_unitario) if item.peso_unitario else '',
            'embalagem': item.embalagem,
            'observacao': item.observacao or '',
            'especie_id': item.especie.id if item.especie else '',
            'cultivar_id': item.cultivar.id if item.cultivar else '',
            'peneira_id': item.peneira.id if item.peneira else '',
            'categoria_id': item.categoria.id if item.categoria else '',
            'tratamento_id': item.tratamento.id if item.tratamento else '',
        }
        return JsonResponse(data)
    except Estoque.DoesNotExist:
        return JsonResponse({'error': 'Item não encontrado'}, status=404)

@login_required
def nova_entrada(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = request.POST.get('lote', '').strip()
                endereco = request.POST.get('endereco', '').strip().upper()
                produto = request.POST.get('produto', '').strip()
                qtd = int(request.POST.get('entrada', 0))
                
                # 🔥 NOVO: Capturar o checkbox
                ultimo_lote_linha = request.POST.get('ultimo_lote_linha') == 'on'
                
                # Processar peso unitário
                peso_raw = request.POST.get('peso_unitario', '0')
                try:
                    peso_raw = str(peso_raw).replace(',', '.')
                    if peso_raw.count('.') > 1:
                        partes = peso_raw.split('.')
                        peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                    novo_peso = Decimal(peso_raw).quantize(Decimal('0.01'))
                except:
                    novo_peso = Decimal('0.00')
                
                # Buscar objetos relacionados
                especie_id = request.POST.get('especie')
                if especie_id:
                    especie_obj = get_object_or_404(Especie, id=especie_id)
                else:
                    especie_obj, _ = Especie.objects.get_or_create(nome='SOJA')

                cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
                peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
                categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
                
                trat_id = request.POST.get('tratamento')
                tratamento = Tratamento.objects.filter(id=trat_id).first() if trat_id else None

                # Buscar item existente
                item = Estoque.objects.filter(
                    lote=lote, 
                    endereco=endereco,
                    produto=produto,
                    cultivar=cultivar,
                    peso_unitario=novo_peso
                ).first()
                
                if item:
                    # Soma ao existente
                    item.entrada += qtd
                    item.observacao += f"\n[+ENTRADA {qtd} em {timezone.now().strftime('%d/%m')}]"
                    item.especie = especie_obj
                    
                    # 🔥 IMPORTANTE: Se for marcar como último lote
                    if ultimo_lote_linha:
                        # Verificar se já existe outro último na mesma linha
                        dados_end = extrair_ln_p(endereco)
                        if dados_end:
                            outro_ultimo = Estoque.objects.filter(
                                endereco__startswith=f"{dados_end['rua']} {dados_end['ln']} P",
                                ultimo_lote_linha=True
                            ).exclude(id=item.id).first()
                            
                            if outro_ultimo:
                                outro_ultimo.ultimo_lote_linha = False
                                outro_ultimo.save()
                        
                        item.ultimo_lote_linha = True
                    
                    msg = "adicionados ao lote existente"
                    print(f"✅ Somando ao lote existente: {lote}")
                else:
                    # Criar novo lote
                    item = Estoque(
                        lote=lote, 
                        endereco=endereco, 
                        entrada=qtd, 
                        saldo=qtd,
                        cultivar=cultivar, 
                        peneira=peneira, 
                        categoria=categoria, 
                        tratamento=tratamento,
                        especie=especie_obj,
                        conferente=request.user,
                        produto=produto,
                        cliente=request.POST.get('cliente', ''),
                        empresa=request.POST.get('empresa', ''),
                        az=request.POST.get('az', ''),
                        origem_destino=request.POST.get('origem_destino', ''),
                        peso_unitario=novo_peso,
                        embalagem=request.POST.get('embalagem', 'BAG'),
                        observacao=request.POST.get('observacao', ''),
                        ultimo_lote_linha=ultimo_lote_linha  # 🔥 NOVO
                    )
                    
                    # Se for marcar como último, verificar conflitos
                    if ultimo_lote_linha:
                        dados_end = extrair_ln_p(endereco)
                        if dados_end:
                            outro_ultimo = Estoque.objects.filter(
                                endereco__startswith=f"{dados_end['rua']} {dados_end['ln']} P",
                                ultimo_lote_linha=True
                            ).first()
                            
                            if outro_ultimo:
                                outro_ultimo.ultimo_lote_linha = False
                                outro_ultimo.save()
                    
                    msg = "criado com sucesso"
                    print(f"🆕 Novo lote criado: {lote}")
                
                item.save()
                
                # Calcular peso total
                if item.peso_unitario and item.peso_unitario > 0:
                    item.peso_total = Decimal(str(item.saldo)) * item.peso_unitario
                    item.peso_total = item.peso_total.quantize(Decimal('0.01'))
                    item.save()
                
                # Histórico
                status_ultimo = " e marcado como ÚLTIMO DA LINHA" if ultimo_lote_linha else ""
                descricao_historico = f"Entrada de {qtd} unidades. ({msg}{status_ultimo}) | Produto: {produto} | Peso: {novo_peso} kg"
                hist = HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Entrada',
                    descricao=descricao_historico
                )
                
                for f in request.FILES.getlist('fotos'):
                    FotoMovimentacao.objects.create(historico=hist, arquivo=f)
                
                messages.success(request, f"✅ Lote {lote} {msg}!{status_ultimo}")
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"Erro ao processar entrada: {str(e)}")
            
    return redirect('sapp:lista_estoque')

@login_required
def nova_saida(request):
    print("veio aqui na função  nova_saida")
    """Registra uma nova saída geral (para qualquer lote)"""
    if request.method == 'POST':
        try:
            lote_id = request.POST.get('lote_id')
            quantidade = int(request.POST.get('quantidade', 0))
            numero_carga = request.POST.get('numero_carga', '')
            motorista = request.POST.get('motorista', '')
            cliente = request.POST.get('cliente', '')
            observacao = request.POST.get('observacao', '')
            
            if not lote_id or quantidade <= 0:
                messages.error(request, "❌ Dados inválidos.")
                return redirect('sapp:lista_estoque')
            
            item = Estoque.objects.get(id=lote_id)
            
            if quantidade > item.saldo:
                messages.error(request, f"❌ Quantidade excede o saldo disponível ({item.saldo}).")
                return redirect('sapp:lista_estoque')
            
            # Salvar estado anterior
            saldo_anterior = item.saldo
            
            # Atualizar saída e saldo
            item.saida += quantidade  # CORRETO
            item.saldo = item.entrada - item.saida  # CORRETO
            
            # Recalcular peso total
            if item.peso_unitario:
                item.peso_total = Decimal(item.saldo) * Decimal(item.peso_unitario)
            
            # Atualizar data da última saída
            item.data_ultima_saida = timezone.now()
            
            # Atualizar observação
            if observacao:
                if item.observacao:
                    item.observacao += f"\n\n[EXPEDIÇÃO GERAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
                else:
                    item.observacao = f"[EXPEDIÇÃO GERAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
            
            item.save()
            
            # Registrar histórico
            historico = HistoricoMovimentacao.objects.create(
                estoque=item,
                usuario=request.user,
                tipo='Expedição via Sistema',
                descricao=(
                    f"<b>📤 EXPEDIÇÃO REGISTRADA</b><br>"
                    f"<b>Método:</b> Formulário Geral<br>"
                    f"<b>Quantidade:</b> {quantidade} unidades<br>"
                    f"<b>Carga:</b> {numero_carga}<br>"
                    f"<b>Motorista:</b> {motorista}<br>"
                    f"<b>Cliente:</b> {cliente}<br>"
                    f"<b>Saldo anterior:</b> {saldo_anterior}<br>"
                    f"<b>Novo saldo:</b> {item.saldo}<br>"
                    f"<b>Observação:</b> {observacao or 'Nenhuma'}<br>"
                    f"<b>Responsável:</b> {request.user.get_full_name() or request.user.username}"
                ),
                numero_carga=numero_carga,
                motorista=motorista,
                cliente=cliente
            )
            
            # Salvar foto se existir
            if 'foto' in request.FILES:
                historico.foto = request.FILES['foto']
                historico.save()
            
            messages.success(request, f"✅ Expedição de {quantidade} unidades registrada para o lote {item.lote}!")
            
        except Estoque.DoesNotExist:
            messages.error(request, "❌ Lote não encontrado.")
        except Exception as e:
            messages.error(request, f"❌ Erro ao registrar expedição: {str(e)}")
            import traceback
            print(f"🔍 Erro detalhado: {traceback.format_exc()}")
    
    return redirect('sapp:lista_estoque')

@login_required
def relatorio_saidas(request):
    """Relatório detalhado de todas as saídas"""
    if request.method == 'POST':
        # Filtros por período
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        
        saidas = HistoricoMovimentacao.objects.filter(tipo__contains='Saída')
        
        if data_inicio:
            saidas = saidas.filter(data_hora__gte=data_inicio)
        if data_fim:
            saidas = saidas.filter(data_hora__lte=data_fim)
        
        # Agrupar por destino
        saidas_por_destino = saidas.values('descricao').annotate(
            total=Count('id'),
            ultima_data=Max('data_hora')
        )
        
        context = {
            'saidas': saidas,
            'saidas_por_destino': saidas_por_destino,
            'total_saidas': saidas.count(),
            'periodo': f"{data_inicio} a {data_fim}" if data_inicio and data_fim else "Todos os períodos"
        }
        
        return render(request, 'sapp/relatorio_saidas.html', context)
    
    return render(request, 'sapp/relatorio_saidas.html')


from django.http import JsonResponse
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required

@login_required
def api_estoque_estatisticas(request):
    """API para atualizar os cards de estatísticas com base nos filtros atuais"""
    
    # Query base - apenas saldo > 0
    qs = Estoque.objects.filter(saldo__gt=0)
    
    # Aplicar os mesmos filtros da view principal
    # Status sistêmico
    status_filter = request.GET.getlist('status_sistemico')
    if status_filter:
        if '__null__' in status_filter:
            qs = qs.filter(
                Q(status_sistemico__in=[s for s in status_filter if s != '__null__']) | 
                Q(status_sistemico__isnull=True)
            )
        else:
            qs = qs.filter(status_sistemico__in=status_filter)
    
    # Busca
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo)
            )
    
    # Filtros de seleção
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }

    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        values = [v for v in values if v and v.strip()]
        if values:
            if '__null__' in values:
                specific_values = [v for v in values if v != '__null__']
                if specific_values:
                    qs = qs.filter(
                        Q(**{lookup: specific_values}) | 
                        Q(**{lookup.replace('__in', '__isnull'): True})
                    )
                else:
                    qs = qs.filter(**{lookup.replace('__in', '__isnull'): True})
            else:
                qs = qs.filter(**{lookup: values})
    
    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            try:
                qs = qs.filter(**{f'{field}__gte': float(min_val)})
            except ValueError:
                pass
        if max_val:
            try:
                qs = qs.filter(**{f'{field}__lte': float(max_val)})
            except ValueError:
                pass
    
    # Calcular estatísticas
    total_itens = qs.count()
    
    saldo_bags = qs.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_sc = qs.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
    total_sc = (saldo_bags * 25) + saldo_sc
    
    total_pme = qs.aggregate(s=Sum('peso_total'))['s'] or 0
    
    clientes_unicos = qs.exclude(cliente__isnull=True).exclude(cliente='').values('cliente').distinct().count()
    
    return JsonResponse({
        'success': True,
        'total_itens': total_itens,
        'total_sc': total_sc,
        'total_bags': saldo_bags,
        'total_pme': total_pme,
        'clientes_unicos': clientes_unicos
    })




@login_required
def api_opcoes_filtro(request):
    """Retorna opções de filtro baseadas nos filtros atuais (encadeamento)"""
    coluna = request.GET.get('coluna')
    if not coluna:
        return JsonResponse({'success': False, 'error': 'Coluna não especificada'})
    
    # Query base - APENAS saldo > 0
    qs = Estoque.objects.filter(saldo__gt=0)
    
    # Aplicar TODOS os filtros atuais
    # Status sistêmico
    status_filter = request.GET.getlist('status_sistemico')
    if status_filter and coluna != 'status_sistemico':
        if '__null__' in status_filter:
            qs = qs.filter(
                Q(status_sistemico__in=[s for s in status_filter if s != '__null__']) | 
                Q(status_sistemico__isnull=True)
            )
        else:
            qs = qs.filter(status_sistemico__in=status_filter)
    
    # Busca
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo)
            )
    
    # Mapeamento de filtros
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }
    
    # Aplicar outros filtros (exceto a coluna atual)
    for param, lookup in filter_map.items():
        if param == coluna:
            continue
            
        values = request.GET.getlist(param)
        values = [v for v in values if v and v.strip()]
        if values:
            if '__null__' in values:
                specific_values = [v for v in values if v != '__null__']
                if specific_values:
                    qs = qs.filter(
                        Q(**{lookup: specific_values}) | 
                        Q(**{lookup.replace('__in', '__isnull'): True})
                    )
                else:
                    qs = qs.filter(**{lookup.replace('__in', '__isnull'): True})
            else:
                qs = qs.filter(**{lookup: values})
    
    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        if field == coluna:
            continue
            
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            try:
                qs = qs.filter(**{f'{field}__gte': float(min_val)})
            except ValueError:
                pass
        if max_val:
            try:
                qs = qs.filter(**{f'{field}__lte': float(max_val)})
            except ValueError:
                pass
    
    # Mapeamento para buscar os valores distintos
    field_lookup_map = {
        'az': 'az',
        'lote': 'lote',
        'produto': 'produto',
        'cultivar': 'cultivar__nome',
        'peneira': 'peneira__nome',
        'categoria': 'categoria__nome',
        'endereco': 'endereco',
        'especie': 'especie__nome',
        'tratamento': 'tratamento__nome',
        'embalagem': 'embalagem',
        'cliente': 'cliente',
        'empresa': 'empresa',
        'conferente': 'conferente__username'
    }
    
    if coluna in field_lookup_map:
        lookup = field_lookup_map[coluna]
        
        # Verificar se existem valores nulos
        tem_null = qs.filter(**{lookup + '__isnull': True}).exists() or qs.filter(**{lookup: ''}).exists()
        
        # Buscar valores não nulos
        valores = qs.exclude(**{lookup: None}).exclude(**{lookup: ''}).values_list(lookup, flat=True).distinct().order_by(lookup)
        opcoes = [str(v) for v in valores if v is not None and str(v).strip() != '']
        
        return JsonResponse({
            'success': True, 
            'opcoes': opcoes,
            'tem_null': tem_null
        })
    
    return JsonResponse({'success': False, 'error': 'Coluna inválida'})


############################################################################
# NO VIEWS.PY - CORRIGIR A FUNÇÃO editar COMPLETAMENTE:
@login_required
def editar(request, id):
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. CAPTURA O ESTADO ANTIGO (Para histórico)
                antigo = {
                    'lote': item.lote,
                    'endereco': item.endereco,
                    'empresa': item.empresa or "",
                    'origem_destino': item.origem_destino or "",
                    'peso_unitario': item.peso_unitario,
                    'entrada': item.entrada,  # NOVO
                    'saida': item.saida,      # NOVO (para referência)
                    'saldo': item.saldo,      # NOVO (para referência)
                    'embalagem': item.embalagem,
                    'az': item.az or "",
                    'observacao': item.observacao or "",
                    'cliente': item.cliente or "", 
                    'cultivar': item.cultivar.nome if item.cultivar else "",
                    'peneira': item.peneira.nome if item.peneira else "",
                    'categoria': item.categoria.nome if item.categoria else "",
                    'especie': item.especie.nome if item.especie else "SOJA",
                    'tratamento': item.tratamento.nome if item.tratamento else "Sem Tratamento",
                    'produto': item.produto or "", 
                }

                # 2. CAPTURA OS NOVOS VALORES
                novo_lote = request.POST.get('lote', '').strip()
                novo_endereco = request.POST.get('endereco', '').strip().upper()
                novo_empresa = request.POST.get('empresa', '').strip()
                novo_origem_destino = request.POST.get('origem_destino', '').strip()
                novo_produto = request.POST.get('produto', '').strip()
                novo_cliente = request.POST.get('cliente', '').strip()
                
                # NOVO: Capturar quantidade
                nova_entrada_raw = request.POST.get('entrada', '0')
                try:
                    nova_entrada = int(float(nova_entrada_raw))
                    if nova_entrada < 0:
                        nova_entrada = 0
                except:
                    nova_entrada = item.entrada
                
                # Tratamento do peso
                peso_raw = request.POST.get('peso_unitario', '0')
                try:
                    peso_raw = str(peso_raw).replace(',', '.')
                    if peso_raw.count('.') > 1:
                        partes = peso_raw.split('.')
                        peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                    novo_peso = Decimal(peso_raw)
                except:
                    novo_peso = Decimal('0.00')
                
                novo_emb = request.POST.get('embalagem', 'BAG')
                novo_az = request.POST.get('az', '').strip()
                novo_obs = request.POST.get('observacao', '').strip()

                # 3. BUSCAR OBJETOS RELACIONADOS
                # Espécie
                novo_especie_id = request.POST.get('especie')
                if novo_especie_id:
                    obj_especie = get_object_or_404(Especie, id=novo_especie_id)
                else:
                    obj_especie = item.especie

                # Cultivar
                try:
                    obj_cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
                except:
                    obj_cultivar = item.cultivar
                    
                # Peneira
                try:
                    obj_peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
                except:
                    obj_peneira = item.peneira
                    
                # Categoria
                try:
                    obj_categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
                except:
                    obj_categoria = item.categoria
                
                # Tratamento
                tratamento_id = request.POST.get('tratamento')
                if tratamento_id:
                    try:
                        obj_tratamento = get_object_or_404(Tratamento, id=tratamento_id)
                    except:
                        obj_tratamento = item.tratamento
                else:
                    obj_tratamento = None

                # 4. COMPARAÇÃO DETALHADA PARA O HISTÓRICO
                mudancas = []
                
                # Campos básicos (incluindo entrada)
                campos_para_comparar = [
                    ('lote', 'Lote', antigo['lote'], novo_lote),
                    ('endereco', 'Endereço', antigo['endereco'], novo_endereco),
                    ('empresa', 'Empresa', antigo['empresa'], novo_empresa),
                    ('origem_destino', 'Origem/Destino', antigo['origem_destino'], novo_origem_destino),
                    ('produto', 'Produto', antigo['produto'], novo_produto),
                    ('cliente', 'Cliente', antigo['cliente'], novo_cliente),
                    ('peso_unitario', 'Peso Unitário', antigo['peso_unitario'], novo_peso),
                    ('entrada', 'Quantidade (Entrada)', antigo['entrada'], nova_entrada),  # NOVO
                    ('embalagem', 'Embalagem', antigo['embalagem'], novo_emb),
                    ('az', 'AZ', antigo['az'], novo_az),
                    ('observacao', 'Observação', antigo['observacao'], novo_obs),
                    ('cultivar', 'Cultivar', antigo['cultivar'], obj_cultivar.nome if obj_cultivar else '-'),
                    ('peneira', 'Peneira', antigo['peneira'], obj_peneira.nome if obj_peneira else '-'),
                    ('categoria', 'Categoria', antigo['categoria'], obj_categoria.nome if obj_categoria else '-'),
                    ('especie', 'Espécie', antigo['especie'], obj_especie.nome if obj_especie else '-'),
                    ('tratamento', 'Tratamento', antigo['tratamento'], obj_tratamento.nome if obj_tratamento else 'Sem Tratamento'),
                ]
                
                for campo_nome, label, valor_antigo, valor_novo in campos_para_comparar:
                    if str(valor_antigo or '') != str(valor_novo or ''):
                        mudancas.append(f"{label}: {valor_antigo} → <b>{valor_novo}</b>")

                # 5. ATUALIZAR O OBJETO
                item.lote = novo_lote
                item.endereco = novo_endereco
                item.empresa = novo_empresa
                item.origem_destino = novo_origem_destino
                item.produto = novo_produto
                item.cliente = novo_cliente
                item.peso_unitario = novo_peso
                item.entrada = nova_entrada  # NOVO: Atualiza a entrada
                # NÃO altera a saída - mantém o valor original
                item.embalagem = novo_emb
                item.az = novo_az
                item.observacao = novo_obs
                
                # Atualizando Foreign Keys
                item.cultivar = obj_cultivar
                item.peneira = obj_peneira
                item.categoria = obj_categoria
                item.tratamento = obj_tratamento
                item.especie = obj_especie
                
                item.conferente = request.user
                
                # 6. SALVAR (o método save() recalcula saldo e peso_total automaticamente)
                item.save()

                # 7. VERIFICAR SE HOUVE MUDANÇA NA QUANTIDADE E CRIAR HISTÓRICO ESPECÍFICO
                if antigo['entrada'] != nova_entrada:
                    diferenca = nova_entrada - antigo['entrada']
                    if diferenca > 0:
                        tipo_historico = 'Ajuste de Estoque (Adição)'
                        descricao_adicional = f"<br><span class='text-success'>📦 Quantidade aumentada em <b>{diferenca}</b> unidades (entrada: {antigo['entrada']} → {nova_entrada})</span>"
                    else:
                        tipo_historico = 'Ajuste de Estoque (Redução)'
                        descricao_adicional = f"<br><span class='text-danger'>📦 Quantidade reduzida em <b>{abs(diferenca)}</b> unidades (entrada: {antigo['entrada']} → {nova_entrada})</span>"
                    
                    # Adiciona ao histórico principal ou cria um separado
                    HistoricoMovimentacao.objects.create(
                        estoque=item,
                        usuario=request.user,
                        tipo=tipo_historico,
                        descricao=f"<b>AJUSTE MANUAL DE QUANTIDADE:</b><br>{descricao_adicional}"
                    )

                # 8. REGISTRAR HISTÓRICO PRINCIPAL
                if mudancas:
                    descricao_html = "<br>".join(mudancas)
                    HistoricoMovimentacao.objects.create(
                        estoque=item,
                        usuario=request.user,
                        tipo='Edição de Lote',
                        descricao=f"<b>EDIÇÃO REALIZADA:</b><br>{descricao_html}"
                    )
                elif antigo['entrada'] == nova_entrada:  # Só cria se não houve mudança na quantidade
                    HistoricoMovimentacao.objects.create(
                        estoque=item,
                        usuario=request.user,
                        tipo='Edição (Sem mudanças)',
                        descricao="Salvo sem alterações visíveis."
                    )

                messages.success(request, f"✅ Lote {item.lote} atualizado com sucesso! Saldo atual: {item.saldo} unidades")
                
        except Exception as e:
            import traceback
            print(f"❌ ERRO NA EDIÇÃO: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Erro ao editar lote: {str(e)}")
            
    return redirect('sapp:lista_estoque')
      






@login_required
def excluir_lote(request, id):
    item = get_object_or_404(Estoque, id=id)
    if request.method == 'POST':
        HistoricoMovimentacao.objects.create(
            estoque=None, 
            lote_ref=f"{item.lote} (Excluído)",
            usuario=request.user,
            tipo='EXCLUSÃO',
            descricao=f"Lote <b>{item.lote}</b> do endereço <b>{item.endereco}</b> foi excluído."
        )
        item.delete()
        messages.success(request, "Lote excluído.")
    return redirect('sapp:lista_estoque')

def logout_view(request):
    """
    Realiza o logout e redireciona para o login.
    Aceita POST (padrão recomendado) ou GET se necessário.
    """
    logout(request)
    return redirect('sapp:login')






@login_required
def configuracoes(request):
    
    config = Configuracao.get_solo()
    
    usuarios_conferentes = User.objects.filter(
        is_superuser=False
    ).order_by('username')
    
    # =============================
    # QUERYSETS
    # =============================
    
    produtos = Produto.objects.select_related(
        'cultivar',
        'peneira',
        'especie',
        'categoria',
        'tratamento'
    ).all().order_by('-data_cadastro')
    
    cultivares = Cultivar.objects.all().order_by('nome')
    peneiras = Peneira.objects.all().order_by('nome')
    especies = Especie.objects.all().order_by('nome')
    categorias = Categoria.objects.all().order_by('nome')
    tratamentos = Tratamento.objects.all().order_by('nome')
    
    # ARMAZÉNS (de volta!)
    armazens_lista = Armazem.objects.all().order_by('nome')
    
    # ENDEREÇOS (com armazém)
    enderecos_lista = Endereco.objects.select_related('armazem').all().order_by('codigo')
    
    origens_lista = OrigemDestino.objects.all().order_by('nome')
    
    # =============================
    # POST
    # =============================
    
    if request.method == 'POST':
        
        acao = request.POST.get('acao')
        
        # ====================================
        # PRODUTOS
        # ====================================
        
        if acao == 'add_produto':
            try:
                cultivar_id = request.POST.get('cultivar')
                codigo = request.POST.get('codigo', '').strip().upper()
                descricao = request.POST.get('descricao', '').strip()
                
                if not cultivar_id or not codigo:
                    messages.error(request, "❌ Cultivar e Código são obrigatórios!")
                elif Produto.objects.filter(codigo=codigo).exists():
                    messages.error(request, f"❌ Código '{codigo}' já existe!")
                else:
                    produto = Produto.objects.create(
                        cultivar_id=cultivar_id,
                        codigo=codigo,
                        descricao=descricao,
                        tipo=request.POST.get('tipo', '').strip(),
                        empresa=request.POST.get('empresa', '').strip(),
                        ativo=request.POST.get('ativo') == 'on'
                    )
                    produto.peneira_id = request.POST.get('peneira') or None
                    produto.especie_id = request.POST.get('especie') or None
                    produto.categoria_id = request.POST.get('categoria') or None
                    produto.tratamento_id = request.POST.get('tratamento') or None
                    produto.save()
                    messages.success(request, f"✅ Produto '{codigo}' cadastrado!")
            except Exception as e:
                messages.error(request, f"❌ Erro: {str(e)}")
        
        elif acao == 'delete_produto':
            try:
                item_id = request.POST.get('id_item')
                if not item_id:
                    messages.error(request, "❌ Produto não identificado!")
                else:
                    Produto.objects.filter(id=item_id).delete()
                    messages.success(request, "✅ Produto excluído!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao excluir: {str(e)}")
        
        # ====================================
        # USUÁRIOS
        # ====================================
        
        elif acao == 'add_conferente_user':
            if request.user.is_superuser:
                username = request.POST.get('username', '').strip()
                if username and not User.objects.filter(username=username).exists():
                    User.objects.create_user(
                        username=username,
                        password='conceito',
                        first_name=request.POST.get('first_name', '').strip()
                    )
                    messages.success(request, f"✅ Usuário {username} criado! Senha padrão: conceito")
                else:
                    messages.error(request, "❌ Usuário já existe ou nome inválido.")
        
        # ====================================
        # CONFIGURAÇÃO GERAL
        # ====================================
        
        elif acao == 'config_geral':
            form = ConfiguracaoForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, "✅ Configurações salvas!")
        
        # ====================================
        # ARMAZÉM (de volta!)
        # ====================================
        
        elif acao == 'add_armazem':
            nome = request.POST.get('nome', '').strip().upper()
            if nome:
                obj, created = Armazem.objects.get_or_create(nome=nome)
                if created:
                    messages.success(request, f"✅ Armazém {nome} criado!")
                else:
                    messages.warning(request, "⚠️ Armazém já existe.")
        
        # ====================================
        # ENDEREÇO (com armazém)
        # ====================================
        
        elif acao == 'add_endereco':
            endereco_codigo = request.POST.get('endereco_codigo', '').strip().upper()
            armazem_id = request.POST.get('armazem_id')
            
            if not endereco_codigo:
                messages.error(request, "❌ Endereço não informado!")
            elif not armazem_id:
                messages.error(request, "❌ Selecione um armazém!")
            else:
                try:
                    armazem = Armazem.objects.get(id=armazem_id)
                    
                    if Endereco.objects.filter(codigo=endereco_codigo).exists():
                        messages.warning(request, f"⚠️ Endereço '{endereco_codigo}' já cadastrado!")
                    else:
                        Endereco.objects.create(
                            codigo=endereco_codigo,
                            armazem=armazem
                        )
                        messages.success(request, f"✅ Endereço '{endereco_codigo}' cadastrado no armazém {armazem.nome}!")
                        
                except Armazem.DoesNotExist:
                    messages.error(request, "❌ Armazém não encontrado!")
                except Exception as e:
                    messages.error(request, f"❌ Erro ao cadastrar endereço: {str(e)}")
        
        # ====================================
        # CADASTROS SIMPLES
        # ====================================
        
        elif acao in ['add_cultivar', 'add_peneira', 'add_especie', 'add_categoria', 'add_tratamento', 'add_origem']:
            model_map = {
                'add_cultivar': Cultivar,
                'add_peneira': Peneira,
                'add_especie': Especie,
                'add_categoria': Categoria,
                'add_tratamento': Tratamento,
                'add_origem': OrigemDestino
            }
            model = model_map.get(acao)
            if model:
                nome = request.POST.get('nome', '').strip()
                if nome:
                    obj, created = model.objects.get_or_create(nome=nome)
                    if created:
                        messages.success(request, f"✅ '{nome}' adicionado!")
                    else:
                        messages.warning(request, "⚠️ Registro já existe.")
        
        # ====================================
        # EXCLUSÃO
        # ====================================
        
        elif acao == 'delete_item':
            tipo = request.POST.get('tipo_item')
            item_id = request.POST.get('id_item')
            
            if not item_id:
                messages.error(request, "❌ Item não identificado!")
            else:
                model_map = {
                    'cultivar': Cultivar,
                    'especie': Especie,
                    'peneira': Peneira,
                    'categoria': Categoria,
                    'tratamento': Tratamento,
                    'armazem': Armazem,
                    'endereco': Endereco,
                    'origem': OrigemDestino,
                    'conferente': User,
                    'produto': Produto,
                }
                
                if tipo in model_map:
                    try:
                        item = model_map[tipo].objects.get(id=item_id)
                        nome_excluido = str(item)
                        
                        if tipo == 'conferente' and item.is_superuser:
                            messages.error(request, "❌ Não é possível excluir um Administrador.")
                        else:
                            # Verifica se o endereço está sendo usado
                            if tipo == 'endereco' and Estoque.objects.filter(endereco=item.codigo).exists():
                                messages.error(request, f"❌ Endereço '{nome_excluido}' está sendo usado em lotes de estoque.")
                            elif tipo == 'armazem' and Endereco.objects.filter(armazem=item).exists():
                                messages.error(request, f"❌ Armazém '{nome_excluido}' possui endereços vinculados.")
                            else:
                                item.delete()
                                messages.success(request, f"✅ Registro '{nome_excluido}' removido!")
                                
                    except model_map[tipo].DoesNotExist:
                        messages.error(request, "❌ Registro não encontrado.")
                    except Exception as e:
                        messages.error(request, f"❌ Erro ao remover: {str(e)}")
                else:
                    messages.error(request, "❌ Tipo de item inválido!")
        
        return redirect('sapp:configuracoes')
    
    # =============================
    # CONTEXT
    # =============================
    
    context = {
        'form_config': ConfiguracaoForm(instance=config),
        
        'cultivares': cultivares,
        'especies': especies,
        'peneiras': peneiras,
        'categorias': categorias,
        'tratamentos': tratamentos,
        
        'usuarios_conferentes': usuarios_conferentes,
        
        'form_conf_user': NovoConferenteUserForm(),
        
        'produtos': produtos,
        
        'armazens': armazens_lista,  # De volta!
        'enderecos': enderecos_lista,
        'origens': origens_lista,
    }
    
    return render(request, 'sapp/configuracoes.html', context)
    
    # =============================
    # CONTEXT (ATUALIZADO - sem ruas/linhas)
    # =============================
    
    context = {
        'form_config': ConfiguracaoForm(instance=config),
        
        'cultivares': cultivares,
        'especies': especies,
        'peneiras': peneiras,
        'categorias': categorias,
        'tratamentos': tratamentos,
        
        'usuarios_conferentes': usuarios_conferentes,
        
        'form_conf_user': NovoConferenteUserForm(),
        
        'produtos': produtos,
        
        'armazens': armazens_lista,
        'enderecos': enderecos_lista,  # Lista de endereços unificada
        'origens': origens_lista,
    }
    
    return render(request, 'sapp/configuracoes.html', context)



@login_required
def historico_geral(request):
    """Histórico completo para DataTables"""
    historico_completo = HistoricoMovimentacao.objects.all().select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')
    
    # Estatísticas para os cards
    total_registros = historico_completo.count()
    
    total_entradas = historico_completo.filter(
        Q(tipo__icontains='Entrada') | Q(tipo__icontains='entrada')
    ).count()
    
    total_saidas = historico_completo.filter(
        Q(tipo__icontains='Saída') | Q(tipo__icontains='Expedição')
    ).count()
    
    total_transferencias = historico_completo.filter(
        tipo__icontains='Transferência'
    ).count()
    
    # Totais de bags e sc
    entradas_bags = historico_completo.filter(
        tipo__icontains='Entrada', 
        estoque__embalagem='BAG'
    ).aggregate(total=Sum('quantidade'))['total'] or 0
    
    entradas_sc = historico_completo.filter(
        tipo__icontains='Entrada',
        estoque__embalagem='SC'
    ).aggregate(total=Sum('quantidade'))['total'] or 0
    
    saidas_bags = historico_completo.filter(
        Q(tipo__icontains='Saída') | Q(tipo__icontains='Expedição'),
        estoque__embalagem='BAG'
    ).aggregate(total=Sum('quantidade'))['total'] or 0
    
    saidas_sc = historico_completo.filter(
        Q(tipo__icontains='Saída') | Q(tipo__icontains='Expedição'),
        estoque__embalagem='SC'
    ).aggregate(total=Sum('quantidade'))['total'] or 0
    
    context = {
        'historico_lista': historico_completo,
        'total_registros': total_registros,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_transferencias': total_transferencias,
        'entradas_bags': entradas_bags,
        'entradas_sc': entradas_sc,
        'saidas_bags': saidas_bags,
        'saidas_sc': saidas_sc,
    }
    
    return render(request, 'sapp/historico_geral.html', context)



@login_required
def mudar_senha(request):
    if request.method == 'POST':
        form = MudarSenhaForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['nova_senha'])
            request.user.save()
            try:
                # Atualiza perfil se existir
                perfil = request.user.perfil
                perfil.primeiro_acesso = False
                perfil.save()
            except: pass
            
            update_session_auth_hash(request, request.user)
            messages.success(request, "Senha atualizada com sucesso!")
            return redirect('sapp:lista_estoque')
    else:
        form = MudarSenhaForm()
    return render(request, 'sapp/mudar_senha.html', {'form': form})

def exportar_excel(request):
    estoque = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    )
    
    # Criar DataFrame
    data = []
    for item in estoque:
        data.append({
            'Lote': item.lote,
            'Produto': item.produto or '',  # 🔥 NOVO CAMPO
            'Cultivar': item.cultivar.nome,
            'Peneira': item.peneira.nome,
            'Categoria': item.categoria.nome,
            'Endereço': item.endereco,
            'Saldo': item.saldo,
            'Peso Unitário (kg)': float(item.peso_unitario),
            'Peso Total (kg)': float(item.peso_total),
            'Tratamento': item.tratamento.nome if item.tratamento else '',
            'Embalagem': item.get_embalagem_display(),
            'Conferente': item.conferente.first_name,
            'Data Entrada': item.data_entrada.strftime('%d/%m/%Y'),
            'AZ': item.az or '',
            'Origem/Destino': item.origem_destino,
            'Empresa': item.empresa,
            'Espécie': item.especie,
            'Observação': item.observacao or ''
        })
    
    df = pd.DataFrame(data)
    
    # Criar resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="estoque_sementes.xlsx"'
    
    # Exportar para Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estoque', index=False)
        
        # Formatar a planilha
        workbook = writer.book
        worksheet = writer.sheets['Estoque']
        
        # Ajustar largura das colunas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return response

def exportar_pdf(request):
    estoque = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    )[:100]  # Limitar para não sobrecarregar o PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    title = Paragraph("RELATÓRIO DE ESTOQUE - SEMENTES", styles['Title'])
    elements.append(title)
    elements.append(Paragraph(f"Data: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph("<br/>", styles['Normal']))
    
    # Dados da tabela ATUALIZADOS
    data = [['Lote', 'Produto', 'Cultivar', 'Peneira', 'Endereço', 'Saldo', 'Peso Total']]  # 🔥 ADICIONADO PRODUTO
    
    for item in estoque:
        data.append([
            item.lote,
            item.produto or '',  # 🔥 NOVO CAMPO
            item.cultivar.nome,
            item.peneira.nome,
            item.endereco,
            str(item.saldo),
            f"{item.peso_total:.2f} kg"
        ])
    
    # Criar tabela
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f8f4e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Rodapé
    elements.append(Paragraph(f"<br/>Total de itens: {estoque.count()}", styles['Normal']))
    
    # Gerar PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="estoque_sementes.pdf"'
    
    return response

################ DEBUG #####################
@login_required
def debug_estoque_completo(request):
    """Debug COMPLETO do estoque atual"""
    estoque = Estoque.objects.all().select_related('peneira', 'cultivar', 'tratamento', 'categoria')
    
    print("🔍 [DEBUG COMPLETO DO ESTOQUE]")
    print("=" * 80)
    
    for item in estoque:
        print(f"Lote: {item.lote}")
        print(f"  Peneira: '{item.peneira.nome if item.peneira else 'None'}'")
        print(f"  Cultivar: '{item.cultivar.nome if item.cultivar else 'None'}'")
        print(f"  Tratamento: '{item.tratamento.nome if item.tratamento else 'None'}'")
        print(f"  Categoria: '{item.categoria.nome if item.categoria else 'None'}'")
        print(f"  Endereço: '{item.endereco}'")
        print(f"  Saldo: {item.saldo}")
        print("-" * 40)
    
    return JsonResponse({'success': True, 'message': 'Check console for debug info'})

@login_required
def debug_estoque_status(request):
    """Debug para ver status do estoque"""
    total_lotes = Estoque.objects.count()
    lotes_com_saldo = Estoque.objects.filter(saldo__gt=0).count()
    lotes_sem_saldo = Estoque.objects.filter(saldo=0).count()
    
    print("🔍 [DEBUG ESTOQUE STATUS]")
    print(f"📊 Total de lotes: {total_lotes}")
    print(f"✅ Com saldo > 0: {lotes_com_saldo}")
    print(f"❌ Com saldo = 0: {lotes_sem_saldo}")
    
    # Listar alguns lotes com saldo 0
    lotes_zerados = Estoque.objects.filter(saldo=0).values('lote', 'endereco', 'id')[:10]
    print("\n📝 Primeiros 10 lotes com saldo 0:")
    for lote in lotes_zerados:
        print(f"   Lote: {lote['lote']} | Endereço: {lote['endereco']} | ID: {lote['id']}")
    
    return JsonResponse({
        'success': True,
        'total_lotes': total_lotes,
        'com_saldo': lotes_com_saldo,
        'sem_saldo': lotes_sem_saldo
    })
################     API    ############################
@login_required
def api_saldo_lote(request, id):
    """API para obter saldo de um lote específico"""
    try:
        item = get_object_or_404(Estoque, id=id)
        return JsonResponse({
            'success': True,
            'lote': item.lote,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'saida': item.saida,
            'cultivar': item.cultivar.nome if item.cultivar else '',
            'endereco': item.endereco,
            'embalagem': item.embalagem,
            'peso_unitario': float(item.peso_unitario) if item.peso_unitario else 0,
            'peso_total': float(item.peso_total) if item.peso_total else 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_buscar_lotes(request):

    query = request.GET.get('q', '')

    if not query:
        return JsonResponse({'results': []})

    lotes = (
        Estoque.objects
        .filter(Q(lote__icontains=query))
        .select_related(
            'cultivar',
            'peneira',
            'categoria',
            'tratamento',
            'especie'
        )
        .order_by('-data_ultima_movimentacao')[:10]
    )

    results = []

    for item in lotes:
        results.append({
            "id": item.id,
            "lote": item.lote,
            "produto": item.produto,
            "cultivar": item.cultivar.nome if item.cultivar else "",
            "cultivar_id": item.cultivar.id if item.cultivar else None,
            "especie_id": item.especie.id if item.especie else None,
            "peneira_id": item.peneira.id if item.peneira else None,
            "categoria_id": item.categoria.id if item.categoria else None,
            "tratamento_id": item.tratamento.id if item.tratamento else None,
            "empresa": item.empresa,
            "cliente": item.cliente,
            "peso_unitario": float(item.peso_unitario) if item.peso_unitario else "",
            "embalagem": item.embalagem,
            "az": item.az,
            "endereco": item.endereco,
            "saldo": float(item.saldo)
        })

    return JsonResponse({"results": results})


@login_required
def api_buscar_lote_completo(request):
    """API para buscar todos os dados de um lote existente"""
    lote = request.GET.get('lote', '')
    
    if not lote:
        return JsonResponse({'encontrado': False, 'error': 'Lote não especificado'})
    item = Estoque.objects.filter(lote=lote).order_by('-id').first()
    
    if item:
        data = {
            'encontrado': True,
            'lote': item.lote,
            'produto': item.produto or '',
            'cultivar_id': item.cultivar.id if item.cultivar else None,
            'peneira_id': item.peneira.id if item.peneira else None,
            'categoria_id': item.categoria.id if item.categoria else None,
            'tratamento_id': item.tratamento.id if item.tratamento else None,
            'empresa': item.empresa or '',
            'origem_destino': item.origem_destino or '',
            'especie_id': item.especie.id if item.especie else None,
            'peso_unitario': str(item.peso_unitario),
            'embalagem': item.embalagem or 'BAG',
            'az': item.az or '',
            'observacao': item.observacao or ''
        }
        return JsonResponse(data)
    
    return JsonResponse({'encontrado': False})

@login_required
def api_verificar_lote(request):
    """API para verificar se um lote existe"""
    lote = request.GET.get('lote', '')
    
    if not lote:
        return JsonResponse({'existe': False})
    
    existe = Estoque.objects.filter(lote=lote).exists()
    
    return JsonResponse({'existe': existe, 'lote': lote})

@login_required
def api_estoque_resumo(request):
    """API para resumo do estoque (usado no dashboard)"""
    total_lotes = Estoque.objects.count()
    lotes_ativos = Estoque.objects.filter(saldo__gt=0).count()
    lotes_esgotados = Estoque.objects.filter(saldo=0).count()
    total_entrada = Estoque.objects.aggregate(total=Sum('entrada'))['total'] or 0
    total_saida = Estoque.objects.aggregate(total=Sum('saida'))['total'] or 0
    
    # Top 5 cultivares
    top_cultivares = Estoque.objects.filter(saldo__gt=0).values(
        'cultivar__nome'
    ).annotate(
        total_saldo=Sum('saldo'),
        total_lotes=Count('id')
    ).order_by('-total_saldo')[:5]
    
    return JsonResponse({
        'success': True,
        'total_lotes': total_lotes,
        'lotes_ativos': lotes_ativos,
        'lotes_esgotados': lotes_esgotados,
        'total_entrada': total_entrada,
        'total_saida': total_saida,
        'top_cultivares': list(top_cultivares)
    })

@login_required
def api_ultimas_movimentacoes(request):
    """API para últimas movimentações"""
    movimentacoes = HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')[:10]
    
    data = []
    for mov in movimentacoes:
        data.append({
            'id': mov.id,
            'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M'),
            'tipo': mov.tipo,
            'descricao': mov.descricao,
            'usuario': mov.usuario.username if mov.usuario else 'Sistema',
            'lote': mov.lote_ref
        })
    
    return JsonResponse({
        'success': True,
        'movimentacoes': data
    })
    
@login_required
def pagina_rascunho(request):
    user = request.user
    MARCA_ORIGEM = "[REP]"

    # =====================================================
    # POST (AÇÕES)
    # =====================================================
    if request.method == 'POST':

        # -------------------------
        # EXCLUIR CARD
        # -------------------------
        if 'excluir_card' in request.POST:
            Empenho.objects.filter(
                id=request.POST.get('empenho_id'),
                usuario=user
            ).delete()
            messages.success(request, "Card excluído com sucesso.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # EXCLUIR ITEM DO CARD
        # -------------------------
        if 'excluir_item' in request.POST:
            ItemEmpenho.objects.filter(
                id=request.POST.get('item_id'),
                empenho__usuario=user
            ).delete()
            messages.success(request, "Item removido do rascunho.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # ADICIONAR AO RASCUNHO
        # -------------------------
        if 'empenhar_lote' in request.POST:
            lote_id = request.POST.get('lote_id')
            qtd = int(request.POST.get('quantidade', 0))
            nome_card = request.POST.get('nome_empenho', '').strip().upper()

            lote = get_object_or_404(Estoque, id=lote_id)

            if qtd <= 0:
                messages.error(request, "Quantidade inválida.")
                return redirect('sapp:pagina_rascunho')

            ja_empenhado = (
                ItemEmpenho.objects
                .filter(empenho__usuario=user, estoque=lote)
                .aggregate(total=models.Sum('quantidade'))['total'] or 0
            )

            if ja_empenhado + qtd > lote.saldo:
                messages.error(
                    request,
                    f"Saldo insuficiente. Disponível: {lote.saldo}. "
                    f"Já empenhado: {ja_empenhado}."
                )
                return redirect('sapp:pagina_rascunho')

            status, _ = EmpenhoStatus.objects.get_or_create(
                id=1, defaults={'nome': 'Rascunho'}
            )

            empenho, _ = Empenho.objects.get_or_create(
                usuario=user,
                observacao=nome_card,
                status=status
            )

            item, _ = ItemEmpenho.objects.get_or_create(
                empenho=empenho,
                estoque=lote,
                defaults={'quantidade': 0}
            )

            item.quantidade += qtd
            item.save()

            messages.success(request, "Lote adicionado ao rascunho.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # TRANSFERIR / EXPEDIR EM MASSA
        # -------------------------
        if request.POST.get('origem_acao') == 'cards':
            acao = request.POST.get('acao_tipo')
            empenho_id = request.POST.get('empenho_id')
            obs_global = request.POST.get('obs_global', '').strip()

            try:
                with transaction.atomic():

                    empenho = get_object_or_404(
                        Empenho, id=empenho_id, usuario=user
                    )

                    # 🔒 BLOQUEIO DE CONCORRÊNCIA + VALIDAÇÃO FINAL
                    itens = (
                        empenho.itens
                        .select_related('estoque')
                        .select_for_update()
                    )

                    for item in itens:
                        item.estoque.refresh_from_db()
                        if item.quantidade > item.estoque.saldo:
                            raise Exception(
                                f"Lote {item.estoque.lote} tem apenas "
                                f"{item.estoque.saldo} disponível "
                                f"(solicitado {item.quantidade})."
                            )

                    for item in itens:
                        origem = item.estoque
                        qtd = item.quantidade

                        # =====================
                        # TRANSFERÊNCIA
                        # =====================
                        if acao == 'transferir':
                            novo_end = request.POST.get('novo_endereco', '').strip().upper()
                            novo_az = request.POST.get('az', '').strip().upper() or origem.az

                            if not novo_end:
                                raise Exception("Novo endereço não informado.")

                            destino = Estoque.objects.filter(
                                lote=origem.lote,
                                produto=origem.produto,
                                cultivar=origem.cultivar,
                                peneira=origem.peneira,
                                categoria=origem.categoria,
                                tratamento=origem.tratamento,
                                especie=origem.especie,
                                endereco=novo_end,
                                az=novo_az,
                                empresa=origem.empresa,
                                embalagem=origem.embalagem
                            ).first()

                            if destino:
                                destino.entrada += qtd
                                destino.save()
                            else:
                                destino = Estoque.objects.create(
                                    lote=origem.lote,
                                    produto=origem.produto,
                                    cultivar=origem.cultivar,
                                    peneira=origem.peneira,
                                    categoria=origem.categoria,
                                    tratamento=origem.tratamento,
                                    especie=origem.especie,
                                    endereco=novo_end,
                                    az=novo_az,
                                    entrada=qtd,
                                    peso_unitario=origem.peso_unitario,
                                    embalagem=origem.embalagem,
                                    conferente=user,
                                    empresa=origem.empresa,
                                    cliente=origem.cliente,
                                    observacao=f"{MARCA_ORIGEM} {obs_global}"
                                )

                            origem.saida += qtd
                            origem.save()
                            HistoricoMovimentacao.objects.create(
                                estoque=origem,
                                usuario=user,
                                quantidade=qtd,  # <--- ADICIONADO
                                tipo='Transferência (Saída)',
                                descricao=f"{MARCA_ORIGEM} Transferido {qtd} un para {novo_end}."
                            )

                            HistoricoMovimentacao.objects.create(
                                estoque=destino,
                                usuario=user,
                                quantidade=qtd,  # <--- ADICIONADO
                                tipo='Transferência (Entrada)',
                                descricao=f"{MARCA_ORIGEM} Recebido {qtd} un de {origem.endereco}."
                            )

                            # 2. EXPEDIÇÃO (Correção: adicionar quantidade=qtd)
                        elif acao == 'expedir':
                                origem.saida += qtd
                                origem.save()

                                HistoricoMovimentacao.objects.create(
                                    estoque=origem,
                                    usuario=user,
                                    quantidade=qtd,  # <--- ADICIONADO
                                    tipo='Expedição',
                                    descricao=f"{MARCA_ORIGEM} Expedido {qtd} un. {obs_global}",
                                    numero_carga=request.POST.get('numero_carga'),
                                    cliente=request.POST.get('cliente'),
                                    placa=request.POST.get('placa')
                                )

                    empenho.delete()
                    messages.success(request, "Ação em lote realizada com sucesso.")

            except Exception as e:
                messages.error(request, f"Erro ao processar: {str(e)}")

            return redirect('sapp:pagina_rascunho')

    # =====================================================
    # GET (DADOS)
    # =====================================================
    ids_rascunhos = ItemEmpenho.objects.filter(
        empenho__usuario=user
    ).values_list('estoque_id', flat=True)

    estoque_qs = (
        Estoque.objects
        .filter(Q(saldo__gt=0) | Q(id__in=ids_rascunhos))
        .select_related('cultivar', 'peneira', 'categoria', 'tratamento', 'especie')
        .order_by('lote', 'endereco')
    )

    todos_itens = (
        ItemEmpenho.objects
        .filter(empenho__usuario=user)
        .select_related('empenho')
    )

    lotes_contexto = []

    for lote in estoque_qs:
        itens = [i for i in todos_itens if i.estoque_id == lote.id]
        empenhado = sum(i.quantidade for i in itens)

        for i in itens:
            i.inconsistente = i.quantidade > lote.saldo

        lotes_contexto.append({
            'lote': lote,
            'empenhado': empenhado,
            'disponivel': lote.saldo - empenhado,
            'itens_empenho': itens,
            'tem_inconsistencia': any(i.inconsistente for i in itens)
        })

    cards = (
        Empenho.objects
        .filter(usuario=user, status__id=1)
        .prefetch_related('itens', 'itens__estoque')
    )

    return render(request, 'sapp/pagina_rascunho.html', {
        'lotes': lotes_contexto,
        'cards': cards,
    })

@login_required
def api_buscar_dados_lote(request):
    item_id = request.GET.get('item_id')
    
    try:
        item = Estoque.objects.select_related(
            'cultivar', 'peneira', 'categoria', 'tratamento', 'especie'
        ).get(id=item_id)
        data = {
            'encontrado': True,
            'id': item.id,
            'lote': item.lote,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'produto': item.produto or '',
            'cliente': item.cliente or '',
            'empresa': item.empresa or '',
            'az': item.az or '',
            'peso_unitario': str(item.peso_unitario).replace(',', '.') if item.peso_unitario else '0.00',
            'embalagem': item.embalagem,
            'observacao': item.observacao or '',
            'especie_id': item.especie.id if item.especie else '',
            'cultivar_id': item.cultivar.id if item.cultivar else '',
            'peneira_id': item.peneira.id if item.peneira else '',
            'categoria_id': item.categoria.id if item.categoria else '',
            'tratamento_id': item.tratamento.id if item.tratamento else '',
        }
        return JsonResponse(data)
    except Estoque.DoesNotExist:
        return JsonResponse({'encontrado': False, 'erro': 'Lote não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'encontrado': False, 'erro': str(e)}, status=500)

@login_required
def api_itens_empenhos(request):
    """API para buscar itens dos empenhos selecionados"""
    empenhos_ids = request.GET.get('empenhos_ids', '')
    
    if not empenhos_ids:
        return JsonResponse({'itens': []})
    
    ids_list = [int(id) for id in empenhos_ids.split(',') if id.isdigit()]
    
    itens = ItemEmpenho.objects.filter(
        empenho_id__in=ids_list,
        empenho__usuario=request.user
    ).select_related('estoque', 'empenho')
    
    itens_data = []
    for item in itens:
        itens_data.append({
            'lote': item.estoque.lote,
            'quantidade': item.quantidade,
            'empenho': item.empenho.observacao,
            'endereco': item.estoque.endereco
        })
    
    return JsonResponse({
        'itens': itens_data,
        'total': len(itens_data)
    })
    
@login_required
def api_autocomplete_nova_entrada(request):
    """
    Busca lotes pelo termo digitado e retorna TODOS os dados para preenchimento.
    """
    # No views.py, dentro de nova_entrada ou editar:

    endereco_raw = request.POST.get('endereco', '').strip().upper() # R-A LN01 P01
    # Regex para separar: (Rua) (Linha) (Posição)
    import re
    match = re.match(r'^(R-[A-Z]+)\s+(LN\d+)\s+(P\d+)$', endereco_raw)

    if not match:
        messages.error(request, "Formato de endereço inválido! Use: R-A LN01 P01")
        return redirect('sapp:lista_estoque')

    rua_nome, linha_nome, posicao_str = match.groups()

    # 1. Validar Posição (01 a 06)
    posicao_num = int(re.search(r'\d+', posicao_str).group())
    if posicao_num < 1 or posicao_num > 6:
        messages.error(request, f"Posição {posicao_str} inválida! Use de 01 a 06.")
        return redirect('sapp:lista_estoque')

    # 2. Verificar se Rua e Linha existem no cadastro
    rua_obj = Rua.objects.filter(nome=rua_nome).first()
    if not rua_obj:
        messages.error(request, f"Rua {rua_nome} não cadastrada!")
        return redirect('sapp:lista_estoque')

    if not Linha.objects.filter(nome=linha_nome).exists():
        messages.error(request, f"Linha {linha_nome} não cadastrada!")
        return redirect('sapp:lista_estoque')

    # 3. SETAR ARMAZÉM AUTOMÁTICO (Puxa da Rua)
    item.az = rua_obj.armazem.nome
    item.endereco = endereco_raw
    termo = request.GET.get('term', '').strip()
    
    if len(termo) < 2:
        return JsonResponse([], safe=False)
    
    # Busca lotes que contenham o texto digitado
    qs = Estoque.objects.filter(lote__icontains=termo).select_related(
        'especie', 'cultivar', 'peneira', 'categoria', 'tratamento'
    ).order_by('-id')
    
    resultados = []
    lotes_vistos = set()
    
    for item in qs:
        if item.lote not in lotes_vistos:
            dados_item = {
                'lote': item.lote,
                'produto': item.produto or '',
                'cultivar__id': item.cultivar.id if item.cultivar else None,
                'peneira__id': item.peneira.id if item.peneira else None,
                'categoria__id': item.categoria.id if item.categoria else None,
                'tratamento__id': item.tratamento.id if item.tratamento else None,
                'especie__id': item.especie.id if item.especie else None,
                
                'empresa': item.empresa or '',
                'origem_destino': item.origem_destino or '',
                'cliente': item.cliente or '',
                'peso_unitario': str(item.peso_unitario),
                'embalagem': item.embalagem,
                'az': item.az or '',
                'observacao': item.observacao or ''
            }

            resultados.append({
                'label': item.lote,
                'dados': dados_item
            })
            lotes_vistos.add(item.lote)
        
        if len(resultados) >= 10: 
            break
            
    return JsonResponse(resultados, safe=False)

@staff_member_required
def api_status_enderecos(request):
    enderecos = MapeamentoEndereco.objects.filter(ativo=True)
    resultado = {}
    
    for mapa in enderecos:
        tem_saldo = Estoque.objects.filter(
            endereco=mapa.endereco, 
            saldo__gt=0
        ).exists()
        
        resultado[mapa.endereco] = {
            'tem_saldo': tem_saldo,
            'cor_padrao': mapa.cor_padrao,
            'cor_positivo': mapa.cor_positivo
        }
    
    return JsonResponse(resultado)

# ============================================================================
# APIs PARA O CANVAS (ADMIN APENAS)
# ============================================================================

def verificar_estoque_endereco(request, endereco):
    """API para verificar se existe estoque em um endereço"""
    if request.method == 'GET':
        try:
            # Decodifica o endereço (pode ter espaços ou caracteres especiais)
            endereco_decodificado = endereco
            
            # Verifica se há estoque
            tem_estoque = Estoque.objects.filter(
                endereco__iexact=endereco_decodificado,
                saldo__gt=0
            ).exists()
            
            # Verifica se existe cadastro (mesmo com saldo zero)
            existe_cadastro = Estoque.objects.filter(
                endereco__iexact=endereco_decodificado
            ).exists()
            
            return JsonResponse({
                'success': True,
                'endereco': endereco_decodificado,
                'tem_estoque': tem_estoque,
                'existe_cadastro': existe_cadastro,
                'mensagem': f'Endereço {endereco_decodificado} tem estoque' if tem_estoque else f'Endereço {endereco_decodificado} está vazio'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e),
                'endereco': endereco
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

def exportar_mapa_json(request, armazem_numero):
    """Exporta o layout do mapa como JSON"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero)
    elementos = armazem.elementos.all().order_by('ordem_z')
    
    dados = {
        'armazem': {
            'id': armazem.id,
            'numero': armazem.numero,
            'nome': armazem.nome,
            'largura_canvas': armazem.largura_canvas,
            'altura_canvas': armazem.altura_canvas,
        },
        'elementos': [
            {
                'id': elem.id,
                'tipo': elem.tipo,
                'pos_x': elem.pos_x,
                'pos_y': elem.pos_y,
                'largura': elem.largura,
                'altura': elem.altura,
                'cor_preenchimento': elem.cor_preenchimento,
                'cor_borda': elem.cor_borda,
                'espessura_borda': elem.espessura_borda,
                'conteudo_texto': elem.conteudo_texto,
                'fonte_nome': elem.fonte_nome,
                'fonte_tamanho': elem.fonte_tamanho,
                'texto_negrito': elem.texto_negrito,
                'texto_italico': elem.texto_italico,
                'texto_direcao': elem.texto_direcao,
                'linha_tipo': elem.linha_tipo,
                'identificador': elem.identificador,
                'ordem_z': elem.ordem_z,
            }
            for elem in elementos
        ],
        'total_elementos': elementos.count(),
        'exportado_em': timezone.now().isoformat()
    }
    
    return JsonResponse(dados, json_dumps_params={'indent': 2})

@staff_member_required
@csrf_exempt
def importar_mapa_json(request, armazem_numero):
    """Importa layout do mapa a partir de JSON"""
    if request.method == 'POST':
        try:
            armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero)
            data = json.loads(request.body)
            
            # Limpa elementos existentes
            ElementoMapa.objects.filter(armazem=armazem).delete()
            
            # Cria novos elementos
            elementos_criados = []
            for idx, elem_data in enumerate(data.get('elementos', [])):
                elemento = ElementoMapa.objects.create(
                    armazem=armazem,
                    tipo=elem_data.get('tipo', 'RETANGULO'),
                    pos_x=elem_data.get('pos_x', 0),
                    pos_y=elem_data.get('pos_y', 0),
                    largura=elem_data.get('largura', 100),
                    altura=elem_data.get('altura', 60),
                    cor_preenchimento=elem_data.get('cor_preenchimento', '#CCCCCC'),
                    cor_borda=elem_data.get('cor_borda', '#000000'),
                    espessura_borda=elem_data.get('espessura_borda', 2),
                    conteudo_texto=elem_data.get('conteudo_texto', ''),
                    fonte_nome=elem_data.get('fonte_nome', 'Arial'),
                    fonte_tamanho=elem_data.get('fonte_tamanho', 14),
                    texto_negrito=elem_data.get('texto_negrito', False),
                    texto_italico=elem_data.get('texto_italico', False),
                    texto_direcao=elem_data.get('texto_direcao', 'horizontal'),
                    linha_tipo=elem_data.get('linha_tipo', 'solida'),
                    identificador=elem_data.get('identificador', ''),
                    ordem_z=elem_data.get('ordem_z', idx + 1),
                )
                elementos_criados.append(elemento.id)
            
            return JsonResponse({
                'success': True,
                'message': f'Mapa importado com sucesso! {len(elementos_criados)} elementos criados.',
                'armazem': armazem.numero,
                'total_elementos': len(elementos_criados)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# ============================================================================
# VIEW DE FALLBACK (para compatibilidade)
# ============================================================================

def lista_armazens(request):
    """Lista todos os armazéns disponíveis"""
    armazens = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazens': armazens,
        'is_admin': request.user.is_staff,
        'titulo_pagina': 'Mapas dos Armazéns'
    }
    return render(request, 'sapp/lista_armazens.html', context)

@staff_member_required
def criar_armazem(request):
    """Cria um novo AZ e redireciona para o editor dele"""
    if request.method == 'POST':
        numero = request.POST.get('numero')
        nome = request.POST.get('nome')
        largura = request.POST.get('largura_canvas', 1200)
        altura = request.POST.get('altura_canvas', 800)
        
        novo_az = ArmazemLayout.objects.create(
            numero=numero,
            nome=nome,
            largura_canvas=largura,
            altura_canvas=altura
        )
        messages.success(request, f"Armazém {novo_az.numero} criado com sucesso!")
        return redirect('sapp:editor_avancado', armazem_numero=novo_az.numero)
    return redirect('sapp:lista_armazens')

@staff_member_required
def editar_config_armazem(request, armazem_id):
    """Edita as configurações (tamanho/nome) de um AZ existente"""
    if request.method == 'POST':
        armazem = get_object_or_404(ArmazemLayout, id=armazem_id)
        armazem.numero = request.POST.get('numero')
        armazem.nome = request.POST.get('nome')
        armazem.largura_canvas = request.POST.get('largura_canvas')
        armazem.altura_canvas = request.POST.get('altura_canvas')
        armazem.save()
        
        messages.success(request, "Configurações do mapa atualizadas!")
        return redirect('sapp:editor_avancado', armazem_numero=armazem.numero)
    return redirect('sapp:lista_armazens')

# ============================================================================
# EDITOR DE MAPA (ADMIN)
# ============================================================================

@login_required
def mapa_ocupacao_canvas(request, armazem_numero=1):
    # 1. Busca Armazém e Elementos
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero, ativo=True)
    elementos_db = armazem.elementos.all().order_by('ordem_z')
    armazens_disponiveis = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    # 2. Busca Estoque com Saldo > 0
    itens_estoque = Estoque.objects.filter(saldo__gt=0)

    # 3. Mapeia Estoque (Normalizando Endereço: Tira espaços e põe Maiúsculo)
    dados_ocupacao = {}
    
    for item in itens_estoque:
        if item.endereco:
            # A MÁGICA: .strip().upper() garante que " a-01" seja igual a "A-01"
            chave = item.endereco.strip().upper()
            
            if chave not in dados_ocupacao:
                dados_ocupacao[chave] = []
            
            dados_ocupacao[chave].append({
                'lote': item.lote,
                'produto': str(item.produto or 'S/ Produto'),
                'qtd': float(item.saldo),
                'embalagem': str(item.embalagem),
                'cliente': str(item.cliente or '-')
            })

    # 4. Prepara Elementos para o Mapa (Já definindo a cor aqui)
    elementos_render = []
    
    for el in elementos_db:
        # Dados básicos
        item_dict = {
            'tipo': el.tipo,
            'x': el.pos_x, 'y': el.pos_y, 'w': el.largura, 'h': el.altura, 'rot': el.rotacao,
            'texto': el.conteudo_texto,
            'id': el.identificador
        }

        # SE FOR RETÂNGULO: Verifica se deve pintar
        if el.tipo == 'RETANGULO' and el.identificador:
            chave_mapa = el.identificador.strip().upper() # Normaliza também
            
            if chave_mapa in dados_ocupacao:
                # TEM ESTOQUE -> VERDE
                item_dict['cor'] = '#10b981' 
                item_dict['stroke'] = '#065f46'
                item_dict['ocupado'] = True
            else:
                # VAZIO -> CINZA (Ou a cor que você escolheu no editor)
                item_dict['cor'] = el.cor_preenchimento or '#f3f4f6'
                item_dict['stroke'] = el.cor_borda or '#9ca3af'
                item_dict['ocupado'] = False
        else:
            # TEXTOS e LINHAS -> Cor original
            item_dict['cor'] = el.cor_preenchimento
            item_dict['stroke'] = el.cor_borda
            item_dict['ocupado'] = False

        elementos_render.append(item_dict)

    # 5. Renderiza
    context = {
        'armazem': armazem,
        'armazens_disponiveis': armazens_disponiveis,
        'elementos_json': json.dumps(elementos_render, cls=DjangoJSONEncoder),
        'dados_ocupacao_json': json.dumps(dados_ocupacao, cls=DjangoJSONEncoder),
        'is_admin': request.user.is_staff,
    }
    
    return render(request, 'sapp/mapa_visualizacao.html', context)

@staff_member_required
@csrf_exempt
def salvar_todos_elementos(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            armazem_id = data.get('armazem_id')
            elementos_data = data.get('elementos', [])
            
            armazem = ArmazemLayout.objects.get(id=armazem_id)
            
            ElementoMapa.objects.filter(armazem=armazem).delete()
            
            novos_objetos = []
            for idx, item in enumerate(elementos_data):
                novo = ElementoMapa(
                    armazem=armazem,
                    tipo=item.get('tipo', 'RETANGULO'),
                    pos_x=item.get('pos_x'),
                    pos_y=item.get('pos_y'),
                    largura=item.get('largura'),
                    altura=item.get('altura'),
                    rotacao=item.get('rotacao', 0),
                    ordem_z=idx, # A ordem que vem do array é a ordem visual
                    
                    # Dados visuais
                    cor_preenchimento=item.get('cor_preenchimento'),
                    conteudo_texto=item.get('conteudo_texto', ''),
                    fonte_tamanho=item.get('fonte_tamanho', 14),
                    
                    # O MAIS IMPORTANTE: O ENDEREÇO
                    identificador=item.get('identificador', '').strip().upper() 
                )
                novos_objetos.append(novo)
            
            # Bulk create é muito mais rápido
            ElementoMapa.objects.bulk_create(novos_objetos)
            
            return JsonResponse({'success': True, 'total': len(novos_objetos)})
            
        except Exception as e:
            print(f"Erro ao salvar mapa: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Método inválido'})

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def lista_armazens(request):
    armazens = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazens': armazens,
        'is_admin': request.user.is_staff,
        'titulo_pagina': 'Mapas dos Armazéns'
    }
    return render(request, 'sapp/lista_armazens.html', context)

@staff_member_required
@csrf_exempt
def criar_armazens_automaticos(request):
    """API para criar armazéns automaticamente"""
    if request.method == 'POST':
        try:
            armazens_padrao = [
                {'numero': 1, 'nome': 'Armazém Principal', 'largura_canvas': 1200, 'altura_canvas': 800},
                {'numero': 2, 'nome': 'Armazém Secundário', 'largura_canvas': 1000, 'altura_canvas': 600},
                {'numero': 3, 'nome': 'Armazém de Reserva', 'largura_canvas': 800, 'altura_canvas': 500},
            ]
            
            criados = []
            for data in armazens_padrao:
                armazem, created = ArmazemLayout.objects.get_or_create(
                    numero=data['numero'],
                    defaults=data
                )
                if created:
                    criados.append(f"Armazém {armazem.numero} - {armazem.nome}")
            
            return JsonResponse({
                'success': True,
                'message': f'{len(criados)} armazéns criados com sucesso!',
                'armazens': criados
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


@staff_member_required
def editor_avancado(request, armazem_numero=1):
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero, ativo=True)
    elementos = armazem.elementos.all().order_by('ordem_z')
    
    # ADICIONE ESTA LINHA ABAIXO se não tiver:
    armazens_disponiveis = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazem': armazem,
        'elementos': elementos,
        'armazens_disponiveis': armazens_disponiveis, # ENVIE PARA O CONTEXTO
        'titulo_pagina': f'Editor Gráfico - Armazém {armazem.numero}',
    }
    return render(request, 'sapp/editor_avancado.html', context)


@csrf_exempt  # Se precisar de POST, mas GET não precisa normalmente
def api_buscar_produto(request):

    try:
        # Log para debug
        print("=" * 50)
        print("API: Recebida requisição para buscar produto")
        print(f"API: Método: {request.method}")
        print(f"API: GET params: {dict(request.GET)}")
        
        # Apenas aceita GET
        if request.method != 'GET':
            return JsonResponse({
                'encontrado': False,
                'erro': 'Método não permitido. Use GET.'
            }, status=405)
        
        # Pegar código da query string
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            print("API: Erro - Código não fornecido")
            return JsonResponse({
                'encontrado': False, 
                'erro': 'Código não fornecido'
            }, status=400)
        
        print(f"API: Buscando produto com código: '{codigo}'")
        
        # Importar dentro da função para evitar problemas de importação circular
        from .models import Produto
        
        # Buscar produto ativo pelo código
        produto = Produto.objects.filter(codigo=codigo, ativo=True).first()
        
        if not produto:
            print(f"API: Produto '{codigo}' não encontrado ou inativo")
            return JsonResponse({
                'encontrado': False, 
                'erro': f'Produto "{codigo}" não encontrado ou inativo'
            })
        
        print(f"API: Produto encontrado - ID: {produto.id}, Código: {produto.codigo}")
        
        # Preparar dados para resposta - USANDO OS CAMPOS REAIS DO SEU MODELO
        dados = {
            'codigo': produto.codigo,
            'cultivar_id': str(produto.cultivar.id) if produto.cultivar else None,
            'cultivar_nome': produto.cultivar.nome if produto.cultivar else '',
            'peneira_id': str(produto.peneira.id) if produto.peneira else None,
            'peneira_nome': produto.peneira.nome if produto.peneira else '',
            'especie_id': str(produto.especie.id) if produto.especie else None,
            'especie_nome': produto.especie.nome if produto.especie else '',
            'categoria_id': str(produto.categoria.id) if produto.categoria else None,
            'categoria_nome': produto.categoria.nome if produto.categoria else '',
            'tratamento_id': str(produto.tratamento.id) if produto.tratamento else None,
            'tratamento_nome': produto.tratamento.nome if produto.tratamento else '',
            'empresa': produto.empresa or '',
            'tipo': produto.tipo or '',
            'descricao': produto.descricao or ''
        }
        
        print(f"API: Dados preparados para retorno: {json.dumps(dados, indent=2, ensure_ascii=False)}")
        
        # Criar resposta
        response_data = {
            'encontrado': True, 
            'dados': dados
        }
        
        print("API: Retornando dados com sucesso")
        print("=" * 50)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"API: ERRO INTERNO: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'encontrado': False, 
            'erro': f'Erro interno do servidor: {str(e)}'
        }, status=500)
    



@login_required
def api_atualizar_status_sistemico(request):
    """API para atualizar o status sistêmico de um lote (qualquer usuário)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lote_id = data.get('lote_id')
            
            if not lote_id:
                return JsonResponse({'success': False, 'error': 'ID do lote não fornecido'})
            
            lote = get_object_or_404(Estoque, id=lote_id)
            
            # Ciclo: critico -> parcial -> ok -> critico
            novo_status = {
                'critico': 'parcial',
                'parcial': 'ok',
                'ok': 'critico'
            }.get(lote.status_sistemico, 'critico')
            
            lote.status_sistemico = novo_status
            lote.status_sistemico_alterado_por = request.user
            lote.status_sistemico_alterado_em = timezone.now()
            lote.save()
            
            # Registrar no histórico
            HistoricoMovimentacao.objects.create(
                estoque=lote,
                usuario=request.user,
                tipo='Status Sistêmico',
                descricao=f'Status alterado para: {lote.get_status_sistemico_display()}'
            )
            
            return JsonResponse({
                'success': True,
                'novo_status': lote.status_sistemico,
                'display': lote.get_status_sistemico_display(),
                'alterado_por': request.user.get_full_name() or request.user.username,
                'alterado_em': lote.status_sistemico_alterado_em.strftime('%d/%m/%Y %H:%M')
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})




################# dashboard ###########################################
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import json
from .models import (
    Estoque, Cultivar, Peneira, Categoria, Especie, Tratamento, Produto,
    DashboardConfig, HistoricoMovimentacao, ArmazemLayout
)
from django.contrib import messages

def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Administradores').exists()

@login_required
def dashboard_view(request):
    """Dashboard principal com gráficos dinâmicos"""
    
    # ==================== CONFIGURAÇÃO DO DASHBOARD ====================
    try:
        config = DashboardConfig.objects.get(criado_por=request.user)
    except DashboardConfig.DoesNotExist:
        config = DashboardConfig.objects.create(criado_por=request.user)
    
    # ==================== QUERYSET BASE COM FILTROS ====================
    queryset = Estoque.objects.all()
    
    # APLICAR FILTRO PL (peneira é null ou nome='sp')
    tipo_filtro = request.GET.get('tipo', 'todos')
    if tipo_filtro == 'pl':
        # PL = Sem peneira (peneira_id is null) OU peneira.nome = 'sp'
        queryset = queryset.filter(
            Q(peneira__isnull=True) | 
            Q(peneira__nome__iexact='sp')
        )
    elif tipo_filtro == 'nao_pl':
        # Não PL = Tem peneira e não é 'sp'
        queryset = queryset.filter(
            peneira__isnull=False
        ).exclude(peneira__nome__iexact='sp')
    
    # Outros filtros
    if request.GET.get('cultivar'):
        queryset = queryset.filter(cultivar_id=request.GET.get('cultivar'))
    if request.GET.get('peneira') and request.GET.get('peneira') != 'sp':
        queryset = queryset.filter(peneira_id=request.GET.get('peneira'))
    if request.GET.get('armazem'):
        queryset = queryset.filter(az=request.GET.get('armazem'))
    if request.GET.get('especie'):
        queryset = queryset.filter(especie_id=request.GET.get('especie'))
    
    # ==================== DADOS PARA O TEMPLATE ====================
    
    # KPIs principais
    total_sc = queryset.aggregate(total=Sum('saldo'))['total'] or 0
    total_bag = queryset.filter(embalagem='BAG').aggregate(total=Sum('saldo'))['total'] or 0
    peso_total = queryset.aggregate(total=Sum('peso_total'))['total'] or 0
    
    # Totais PL e Não PL
    total_pl_geral = Estoque.objects.filter(
        Q(peneira__isnull=True) | Q(peneira__nome__iexact='sp')
    ).count()
    total_nao_pl_geral = Estoque.objects.filter(
        peneira__isnull=False
    ).exclude(peneira__nome__iexact='sp').count()
    
    # Lotes ativos e esgotados
    itens_ativos = queryset.filter(saldo__gt=0).count()
    itens_esgotados = queryset.filter(saldo=0).count()
    
    # Movimentação do mês
    inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    movimentacao_mes = HistoricoMovimentacao.objects.filter(data_hora__gte=inicio_mes).count()
    
    # TOP CULTIVARES
    top_cultivares = list(queryset.filter(
        saldo__gt=0, cultivar__isnull=False
    ).values('cultivar__nome').annotate(
        total_saldo=Sum('saldo')
    ).order_by('-total_saldo')[:10])
    
    # Dados para gráfico de ESPÉCIE
    dados_especie = list(queryset.filter(
        especie__isnull=False, saldo__gt=0
    ).values('especie__nome').annotate(
        total=Sum('saldo')
    ).order_by('-total')[:10])
    
    # Dados para gráfico de PENEIRA
    categorias_distribuicao = list(queryset.filter(
        saldo__gt=0, peneira__isnull=False
    ).exclude(peneira__nome__iexact='sp').values('peneira__nome').annotate(
        total=Sum('saldo')
    ).order_by('-total'))
    
    # ==================== GRÁFICO DE ARMAZÉM COM FILTROS ====================
    # Aplicar filtros ao queryset de armazém
    armazem_queryset = queryset.filter(az__isnull=False).exclude(az='')
    
    # Aplicar filtro por espécie no armazém
    if request.GET.get('armazem_especie'):
        armazem_queryset = armazem_queryset.filter(especie_id=request.GET.get('armazem_especie'))
    
    # Aplicar filtro por peneira no armazém
    if request.GET.get('armazem_peneira'):
        if request.GET.get('armazem_peneira') == 'pl':
            armazem_queryset = armazem_queryset.filter(
                Q(peneira__isnull=True) | Q(peneira__nome__iexact='sp')
            )
        elif request.GET.get('armazem_peneira') == 'nao_pl':
            armazem_queryset = armazem_queryset.filter(
                peneira__isnull=False
            ).exclude(peneira__nome__iexact='sp')
        else:
            armazem_queryset = armazem_queryset.filter(peneira_id=request.GET.get('armazem_peneira'))
    
    # Dados para gráfico de ARMAZÉM
    capacidade_armazem = list(armazem_queryset.values('az').annotate(
        total_sc=Sum('saldo'),
        total_lotes=Count('id'),
        peso_total=Sum('peso_total')
    ).order_by('az'))
    
    # ==================== GRÁFICO DE TENDÊNCIA CORRIGIDO ====================
    # Período baseado na configuração ou parâmetro da URL
    dias_tendencia = int(request.GET.get('tendencia_dias', 7))
    data_limite = timezone.now() - timedelta(days=dias_tendencia)
    
    from django.db.models.functions import TruncDate
    
    # Base queryset para tendência
    tendencia_queryset = HistoricoMovimentacao.objects.filter(
        data_hora__gte=data_limite
    )
    
    # Aplicar filtros à tendência
    if request.GET.get('tendencia_tipo'):
        if request.GET.get('tendencia_tipo') == 'pl':
            tendencia_queryset = tendencia_queryset.filter(
                Q(estoque__peneira__isnull=True) | 
                Q(estoque__peneira__nome__iexact='sp')
            )
        elif request.GET.get('tendencia_tipo') == 'nao_pl':
            tendencia_queryset = tendencia_queryset.filter(
                estoque__peneira__isnull=False
            ).exclude(estoque__peneira__nome__iexact='sp')
    
    if request.GET.get('tendencia_especie'):
        tendencia_queryset = tendencia_queryset.filter(
            estoque__especie_id=request.GET.get('tendencia_especie')
        )
    
    # Entradas por dia
    entradas = tendencia_queryset.filter(
        tipo__icontains='Entrada'
    ).annotate(
        dia=TruncDate('data_hora')
    ).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    
    # Saídas por dia
    saidas = tendencia_queryset.filter(
        Q(tipo__icontains='Saída') | Q(tipo__icontains='Expedição')
    ).annotate(
        dia=TruncDate('data_hora')
    ).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    
    # Criar dicionários para fácil acesso
    entradas_dict = {item['dia']: item['total'] for item in entradas}
    saidas_dict = {item['dia']: item['total'] for item in saidas}
    
    # Gerar lista de dias do período
    dias = []
    for i in range(dias_tendencia):
        dia = (timezone.now() - timedelta(days=i)).date()
        dias.append(dia)
    dias.reverse()
    
    movimentacoes_diarias = []
    for dia in dias:
        movimentacoes_diarias.append({
            'dia': dia.strftime('%d/%m'),
            'entradas': entradas_dict.get(dia, 0),
            'saidas': saidas_dict.get(dia, 0)
        })
    
    # Clientes únicos
    clientes_unicos = queryset.exclude(
        cliente__isnull=True
    ).exclude(cliente='').values('cliente').distinct().count()
    
    # Taxa de ocupação
    total_armazens = ArmazemLayout.objects.filter(ativo=True).count()
    if capacidade_armazem and total_armazens > 0:
        total_ocupado = sum([item['total_sc'] for item in capacidade_armazem])
        # Considerando capacidade média de 1000 SC por armazém
        taxa_ocupacao = min(round((total_ocupado / (total_armazens * 1000)) * 100), 100)
    else:
        taxa_ocupacao = 0
    
    # Movimentações recentes
    movimentacao_recente = HistoricoMovimentacao.objects.select_related(
        'usuario', 'estoque'
    ).order_by('-data_hora')[:10]
    
    # ==================== CONTEXTO ====================
    context = {
        # Configuração
        'config': config,
        'is_admin': is_admin(request.user),
        
        # KPIs principais
        'total_sc': total_sc,
        'total_sc_convertido': total_sc,
        'total_bag': total_bag,
        'peso_total': peso_total,
        'itens_ativos': itens_ativos,
        'itens_esgotados': itens_esgotados,
        'movimentacao_mes': movimentacao_mes,
        'clientes_unicos': clientes_unicos,
        'taxa_ocupacao': taxa_ocupacao,
        
        # Totais PL/Não PL
        'total_pl': total_pl_geral,
        'total_nao_pl': total_nao_pl_geral,
        
        # Dados para gráficos
        'top_cultivares': top_cultivares,
        'dados_especie': dados_especie,
        'categorias_distribuicao': categorias_distribuicao,
        'capacidade_armazem': capacidade_armazem,
        'movimentacoes_diarias': movimentacoes_diarias,
        'movimentacao_recente': movimentacao_recente,
        
        # Dados para filtros
        'cultivares': Cultivar.objects.all().order_by('nome'),
        'peneiras': Peneira.objects.all().order_by('nome'),
        'armazens': ArmazemLayout.objects.filter(ativo=True).order_by('numero'),
        'especies': Especie.objects.all().order_by('nome'),
        
        # Filtro ativo
        'tipo_filtro_ativo': tipo_filtro,
        'tendencia_dias_atual': dias_tendencia,
        
        'page_title': 'Dashboard Analítico',
    }
    
    return render(request, 'sapp/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def salvar_config_dashboard(request):
    """Salva configurações do dashboard (apenas admin)"""
    if request.method == 'POST':
        config, created = DashboardConfig.objects.update_or_create(
            criado_por=request.user,
            defaults={
                'cultivar_tipo': request.POST.get('cultivar_tipo', 'doughnut'),
                'cultivar_qtd': int(request.POST.get('cultivar_qtd', 10)),
                'cultivar_ordem': request.POST.get('cultivar_ordem', 'valor_desc'),
                'cultivar_zerados': request.POST.get('cultivar_zerados') == 'on',
                'cultivar_agrupar_outros': request.POST.get('cultivar_agrupar_outros') == 'on',
                'peneira_tipo': request.POST.get('peneira_tipo', 'pie'),
                'peneira_qtd': int(request.POST.get('peneira_qtd', 8)),
                'peneira_ordem': request.POST.get('peneira_ordem', 'valor_desc'),
                'armazem_tipo': request.POST.get('armazem_tipo', 'bar'),
                'armazem_ordem': request.POST.get('armazem_ordem', 'nome_asc'),
                'armazem_metrica': request.POST.get('armazem_metrica', 'volume'),
                'tendencia_periodo': int(request.POST.get('tendencia_periodo', 7)),
                'tendencia_saidas': request.POST.get('tendencia_saidas') == 'on',
                'tendencia_transferencias': request.POST.get('tendencia_transferencias') == 'on',
                'tendencia_agrupamento': request.POST.get('tendencia_agrupamento', 'day'),
                'auto_refresh': int(request.POST.get('auto_refresh', 0)),
                'unidade_padrao': request.POST.get('unidade_padrao', 'sc'),
                'tema_cores': request.POST.get('tema_cores', 'default'),
                'mostrar_legendas': request.POST.get('mostrar_legendas') == 'on',
                'mostrar_percentuais': request.POST.get('mostrar_percentuais') == 'on',
                'filtro_cultivar': request.POST.get('filtro_cultivar') == 'on',
                'filtro_peneira': request.POST.get('filtro_peneira') == 'on',
                'filtro_armazem': request.POST.get('filtro_armazem') == 'on',
                'filtro_periodo': request.POST.get('filtro_periodo') == 'on',
            }
        )
        
        messages.success(request, 'Configurações salvas com sucesso!')
        return redirect('sapp:dashboard')
    
    return redirect('sapp:dashboard')
################################################## fim dashbord ##################
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Estoque, Produto, ConfiguracaoLogo
import re

@login_required
def ficha_rastreabilidade(request):
    """
    View para exibir a ficha de rastreabilidade
    PRIORIDADE: 
    1. parâmetro 'item_id' (para pegar a linha específica)
    2. parâmetro 'lote' (fallback para compatibilidade)
    3. filtros normais (exatamente 1 resultado)
    """
    
    import re
    from django.db.models import Q
    from .models import Estoque, Produto, ConfiguracaoLogo
    
    # ========== CASO 1: TEM ITEM_ID ESPECÍFICO ==========
    item_id = request.GET.get('item_id', '').strip()
    
    if item_id and item_id.isdigit():
        try:
            item = Estoque.objects.filter(id=item_id).first()
            
            if not item:
                messages.error(request, f"Item ID '{item_id}' não encontrado.")
                return redirect('sapp:gestao_estoque')
            
            # Processar o item e renderizar a ficha
            return processar_item_ficha(request, item)
            
        except Exception as e:
            messages.error(request, f"Erro ao buscar item: {str(e)}")
            return redirect('sapp:gestao_estoque')
    
    # ========== CASO 2: TEM LOTE ESPECÍFICO (FALLBACK) ==========
    lote_especifico = request.GET.get('lote', '').strip()
    
    if lote_especifico:
        try:
            # Busca o primeiro item com este lote
            item = Estoque.objects.filter(lote=lote_especifico).first()
            
            if not item:
                messages.error(request, f"Lote '{lote_especifico}' não encontrado.")
                return redirect('sapp:gestao_estoque')
            
            # Processar o item e renderizar a ficha
            return processar_item_ficha(request, item)
            
        except Exception as e:
            messages.error(request, f"Erro ao buscar lote: {str(e)}")
            return redirect('sapp:gestao_estoque')
    
    # ========== CASO 3: SEM LOTE ESPECÍFICO - USAR FILTROS NORMAIS ==========
    filtros = Q()
    
    # Campos de texto (busca parcial)
    campos_texto = ['lote', 'az', 'produto', 'endereco', 'cliente', 'empresa']
    for campo in campos_texto:
        valor = request.GET.get(campo, '')
        if valor and valor.strip():
            filtros &= Q(**{f'{campo}__icontains': valor.strip()})
    
    # Busca global
    busca = request.GET.get('busca', '')
    if busca and busca.strip():
        for termo in busca.split():
            filtros &= (
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(especie__nome__icontains=termo) |
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo)
            )
    
    # Filtros de seleção
    campos_selecao = [
        ('cultivar', 'cultivar__id__in'),
        ('peneira', 'peneira__id__in'),
        ('categoria', 'categoria__id__in'),
        ('especie', 'especie__id__in'),
        ('tratamento', 'tratamento__id__in'),
        ('embalagem', 'embalagem__in'),
    ]
    
    for param, lookup in campos_selecao:
        values = request.GET.getlist(param)
        values = [v for v in values if v and str(v).strip()]
        if values:
            filtros &= Q(**{lookup: values})
    
    # Filtro por status
    status = request.GET.get('status', 'todos')
    if status == 'disponivel':
        filtros &= Q(saldo__gt=0)
    elif status == 'esgotado':
        filtros &= Q(saldo=0)
    
    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val and min_val.strip():
            try:
                filtros &= Q(**{f'{field}__gte': float(min_val)})
            except:
                pass
        if max_val and max_val.strip():
            try:
                filtros &= Q(**{f'{field}__lte': float(max_val)})
            except:
                pass
    
    # ========== BUSCAR ITENS COM OS FILTROS ==========
    itens_filtrados = Estoque.objects.filter(filtros).distinct()
    
    if itens_filtrados.count() != 1:
        messages.error(
            request, 
            f"É necessário ter exatamente 1 lote filtrado. Encontrados: {itens_filtrados.count()}"
        )
        return redirect(request.META.get('HTTP_REFERER', 'sapp:gestao_estoque'))
    
    # PEGAR O ÚNICO ITEM
    item = itens_filtrados.first()
    
    # Processar o item
    return processar_item_ficha(request, item)


def processar_item_ficha(request, item):
    """
    Função auxiliar para processar os dados do item e renderizar a ficha
    """
    import re
    from .models import Produto, ConfiguracaoLogo
    
    # Extrair código do produto do campo produto
    codigo_produto = ''
    descricao_completa = ''
    produto_obj = None
    
    # Tenta encontrar o código do produto
    if item.produto:
        # Primeiro tenta encontrar padrão de 10 dígitos
        match = re.search(r'\b(\d{10})\b', item.produto)
        if match:
            codigo_produto = match.group(1)
            produto_obj = Produto.objects.filter(codigo=codigo_produto).first()
        
        # Se não achou com 10 dígitos, usa o próprio produto como código
        if not produto_obj:
            codigo_produto = item.produto
            produto_obj = Produto.objects.filter(codigo=item.produto).first()
    
    # Se encontrou o produto, usa a descrição EXATA que está no model
    if produto_obj and produto_obj.descricao:
        descricao_completa = produto_obj.descricao
    
    # QR Code: código_produto/lote
    qrcode_texto = item.lote
    if codigo_produto:
        qrcode_texto = f"{codigo_produto}/{item.lote}"
    
    # Safra padrão 2025/2026
    safra = "2025/2026"
    
    # Extrair AZ do endereço se necessário
    az = item.az
    if not az and item.endereco:
        # Pega as primeiras letras do endereço como AZ
        az = ''.join([c for c in item.endereco[:2] if c.isalpha()]).upper()
    
    # Extrair RUA, LN, PS do endereço (formato: AZ RUA LN PS)
    rua = ''
    ln = ''
    ps = ''
    
    if item.endereco:
        partes = item.endereco.split()
        if len(partes) >= 4:
            rua = partes[1] if len(partes) > 1 else ''
            ln = partes[2] if len(partes) > 2 else ''
            ps = partes[3] if len(partes) > 3 else ''
    
    # Dados completos
    item_data = {
        'id': item.id,
        'lote': item.lote,
        'safra': safra,
        'codigo_produto': codigo_produto,
        'descricao': descricao_completa,
        'produto': descricao_completa,
        'az': az or '',
        'rua': rua,
        'ln': ln,
        'ps': ps,
        'endereco': item.endereco or '',
        'empresa': item.empresa or 'GRUPO CONCEITO',
        'peneira': item.peneira.nome if item.peneira else '',
        'categoria': item.categoria.nome if item.categoria else '',
        'cultivar': item.cultivar.nome if item.cultivar else '',
        'peso_unitario': item.peso_unitario,
        'peso_total': item.peso_total,
        'embalagem': item.get_embalagem_display() if hasattr(item, 'get_embalagem_display') else item.embalagem,
        'cliente': item.cliente or '',
        'status': item.status,
        'status_sistemico': item.status_sistemico,
        'saldo': item.saldo,
        'qrcode_texto': qrcode_texto,
    }
    
    # Buscar configuração da logo
    config_logo = ConfiguracaoLogo.get_logo()
    
    context = {
        'item': item_data,
        'config_logo': config_logo,
        'erro': None,
        'item_id': item.id,
        'lote_buscado': item.lote,
        'filtros_aplicados': request.GET.urlencode(),
    }
    
    return render(request, 'sapp/ficha_rastreabilidade.html', context)


def processar_item_ficha(request, item):
    """
    Função auxiliar para processar os dados do item e renderizar a ficha
    """
    # Extrair código do produto do campo produto
    codigo_produto = ''
    descricao_completa = ''
    produto_obj = None
    
    print(f"🔍 Debug - item.produto: '{item.produto}'")  # Debug
    
    # Tenta encontrar o código do produto
    if item.produto:
        # Primeiro tenta encontrar padrão de 10 dígitos
        match = re.search(r'\b(\d{10})\b', item.produto)
        if match:
            codigo_produto = match.group(1)
            produto_obj = Produto.objects.filter(codigo=codigo_produto).first()
            print(f"🔍 Debug - Código extraído (10 dígitos): '{codigo_produto}'")
        
        # Se não achou com 10 dígitos, usa o próprio produto como código
        if not produto_obj:
            codigo_produto = item.produto
            produto_obj = Produto.objects.filter(codigo=item.produto).first()
            print(f"🔍 Debug - Usando produto como código: '{codigo_produto}'")
    
    # Se encontrou o produto, usa a descrição EXATA que está no model
    if produto_obj and produto_obj.descricao:
        descricao_completa = produto_obj.descricao
        print(f"✅ Descrição encontrada no Produto: '{descricao_completa}'")
    else:
        # Fallback: vazio
        descricao_completa = ''
        print(f"⚠️ Nenhuma descrição encontrada")
    
    # QR Code: código_produto/lote
    qrcode_texto = item.lote
    if codigo_produto:
        qrcode_texto = f"{codigo_produto}/{item.lote}"
    
    # Safra padrão 2025/2026
    safra = "2025/2026"
    
    # Dados completos
    item_data = {
        'id': item.id,
        'lote': item.lote,
        'safra': safra,
        'codigo_produto': codigo_produto,
        'descricao': descricao_completa,
        'produto': descricao_completa,
        'az': item.az or (item.endereco[:2] if item.endereco else ''),
        'endereco': item.endereco or '',
        'empresa': item.empresa or 'GRUPO CONCEITO',
        'peneira': item.peneira.nome if item.peneira else '',
        'categoria': item.categoria.nome if item.categoria else '',
        'cultivar': item.cultivar.nome if item.cultivar else '',
        'peso_unitario': item.peso_unitario,
        'peso_total': item.peso_total,
        'embalagem': item.get_embalagem_display() if hasattr(item, 'get_embalagem_display') else item.embalagem,
        'cliente': item.cliente or '',
        'status': item.status,
        'status_sistemico': item.status_sistemico,
        'saldo': item.saldo,
        'qrcode_texto': qrcode_texto,
    }
    
    # Buscar configuração da logo
    config_logo = ConfiguracaoLogo.get_logo()
    
    context = {
        'item': item_data,
        'config_logo': config_logo,
        'erro': None,
        'lote_buscado': item.lote,
        'filtros_aplicados': request.GET.urlencode(),
    }
    
    return render(request, 'sapp/ficha_rastreabilidade.html', context)


def extrair_safra(lote):
    """Mantida para compatibilidade, mas não usada"""
    return "2025/2026"




def extrair_safra(lote):
    """
    Extrai a safra do número do lote
    Exemplos: 2025/2026, 2025, 25/26, SAFRA25
    """
    if not lote:
        return '______________'
    
    lote_str = str(lote)
    
    # Padrão: 2025/2026
    padrao1 = r'(20\d{2}[/-]20\d{2})'
    match = re.search(padrao1, lote_str)
    if match:
        return match.group(1)
    
    # Padrão: 25/26
    padrao2 = r'(\d{2}[/-]\d{2})'
    match = re.search(padrao2, lote_str)
    if match:
        ano1 = match.group(1)[:2]
        ano2 = match.group(1)[-2:]
        return f"20{ano1}/20{ano2}"
    
    # Padrão: SAFRA25 ou SAFRA2025
    padrao3 = r'SAFRA[-\s]*(\d{2,4})'
    match = re.search(padrao3, lote_str, re.IGNORECASE)
    if match:
        ano = match.group(1)
        if len(ano) == 2:
            return f"20{ano}"
        return ano
    
    # Padrão: apenas ano 2025
    padrao4 = r'(20\d{2})'
    match = re.search(padrao4, lote_str)
    if match:
        return match.group(1)
    
    return '______________'

def get_safra_from_lote(lote):
    """
    Função auxiliar para extrair safra do número do lote
    Adapte conforme o formato dos seus lotes
    """
    if not lote:
        return '______________'
    
    # Tenta encontrar padrões comuns de safra (ex: 22/23, 2022, SAFRA22)
    import re
    
    # Padrão: XX/XX (ex: 22/23)
    safra_pattern = r'(\d{2}[/-]\d{2})'
    match = re.search(safra_pattern, lote)
    if match:
        return match.group(1)
    
    # Padrão: 20XX (ex: 2022)
    ano_pattern = r'(20\d{2})'
    match = re.search(ano_pattern, lote)
    if match:
        return match.group(1)
    
    # Padrão: SAFRAXX
    safra_text_pattern = r'(SAFRA\d{2})'
    match = re.search(safra_text_pattern, lote, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return '______________'

# View alternativa que busca por ID (caso queira usar ID em vez de lote)
@login_required
def ficha_rastreabilidade_por_id(request, estoque_id):
    """
    View para exibir ficha de rastreabilidade por ID do estoque
    URL: /ficha-rastreabilidade/<int:estoque_id>/
    """
    try:
        item = get_object_or_404(Estoque, id=estoque_id)
        
        item_data = {
            'lote': item.lote,
            'safra': get_safra_from_lote(item.lote),
            'produto': str(item.cultivar) if item.cultivar else item.produto,
            'az': item.az or item.endereco[:2] if item.endereco else '',
            'empresa': item.empresa or 'GRUPO CONCEITO',
            'peneira': item.peneira,
            'categoria': item.categoria,
            'cultivar': item.cultivar,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'peso_unitario': item.peso_unitario,
            'peso_total': item.peso_total,
            'embalagem': item.get_embalagem_display(),
            'cliente': item.cliente,
            'status': item.status,
            'status_sistemico': item.status_sistemico,
        }
        
        context = {
            'item': item_data,
            'erro': None,
            'lote_buscado': item.lote,
        }
    except Exception as e:
        context = {
            'item': {
                'lote': '______________',
                'safra': '______________',
                'produto': '______________',
                'az': '______________',
                'empresa': '______________',
                'peneira': None,
                'categoria': None,
                'cultivar': None,
                'endereco': '______________',
                'saldo': 0,
                'peso_unitario': 0,
                'peso_total': 0,
                'embalagem': '---',
                'cliente': '______________',
                'status': '---',
                'status_sistemico': 'critico',
            },
            'erro': f"Erro ao buscar item: {str(e)}",
            'lote_buscado': None,
        }
    
    return render(request, 'ficha_rastreabilidade.html', context)

# View para múltiplos lotes (caso queira uma ficha com vários itens)
@login_required
def ficha_rastreabilidade_multipla(request):
    """
    View para exibir fichas de múltiplos lotes
    Uso: /ficha-rastreabilidade/multipla/?lotes=123,456,789
    """
    lotes_param = request.GET.get('lotes', '')
    itens = []
    
    if lotes_param:
        lista_lotes = [l.strip() for l in lotes_param.split(',') if l.strip()]
        for lote in lista_lotes:
            item = Estoque.objects.filter(lote=lote).first()
            if item:
                itens.append({
                    'lote': item.lote,
                    'safra': get_safra_from_lote(item.lote),
                    'produto': str(item.cultivar) if item.cultivar else item.produto,
                    'az': item.az or item.endereco[:2] if item.endereco else '',
                    'empresa': item.empresa or 'GRUPO CONCEITO',
                    'peneira': item.peneira,
                    'categoria': item.categoria,
                    'endereco': item.endereco,
                    'saldo': item.saldo,
                })
    
    context = {
        'itens': itens,
        'total_itens': len(itens),
    }
    return render(request, 'ficha_rastreabilidade_multipla.html', context)



import re

def extrair_ln_p(endereco):
    """
    Extrai LN e P de um endereço no formato R-X LN## P##
    Retorna (rua, ln, posicao) ou None se não seguir o padrão
    """
    if not endereco:
        return None
    
    # Padrão: R-X LN## P## (ex: R-A LN10 P03)
    pattern = r'^(R-[A-Z])\s+(LN\d+)\s+(P\d+)$'
    match = re.match(pattern, endereco.strip().upper())
    
    if match:
        rua = match.group(1)  # R-A
        ln = match.group(2)   # LN10
        p = match.group(3)    # P03
        posicao = int(re.search(r'\d+', p).group())  # 3
        return {
            'rua': rua,
            'ln': ln,
            'posicao': posicao,
            'endereco_completo': endereco
        }
    return None

def get_posicoes_linha(rua, ln):
    """
    Retorna todas as posições existentes de uma rua+linha
    """
    enderecos = Estoque.objects.filter(
        endereco__startswith=f"{rua} {ln} P"
    ).values_list('endereco', flat=True).distinct()
    
    posicoes = []
    for end in enderecos:
        dados = extrair_ln_p(end)
        if dados:
            posicoes.append({
                'endereco': end,
                'posicao': dados['posicao']
            })
    
    # Ordenar por posição numérica
    return sorted(posicoes, key=lambda x: x['posicao'])

@login_required
def marcar_ultimo_lote_linha(request, estoque_id):
    """
    Marca/desmarca um lote como último da linha
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    try:
        lote = Estoque.objects.get(id=estoque_id)
        
        # Verificar se o endereço segue o padrão
        dados_end = extrair_ln_p(lote.endereco)
        if not dados_end:
            return JsonResponse({
                'success': False,
                'error': 'Endereço não segue padrão LN + P'
            })
        
        # Se já está marcado, desmarcar
        if lote.ultimo_lote_linha:
            lote.ultimo_lote_linha = False
            lote.save()
            
            # Limpar marcações da linha
            posicoes = get_posicoes_linha(dados_end['rua'], dados_end['ln'])
            for pos in posicoes:
                if pos['posicao'] >= dados_end['posicao']:
                    # Aqui você pode limpar alguma flag visual se necessário
                    pass
            
            return JsonResponse({
                'success': True,
                'marcado': False,
                'mensagem': 'Marca removida'
            })
        
        # Verificar se já existe outro último na mesma linha
        outro_ultimo = Estoque.objects.filter(
            endereco__startswith=f"{dados_end['rua']} {dados_end['ln']} P",
            ultimo_lote_linha=True
        ).exclude(id=estoque_id).first()
        
        if outro_ultimo:
            # Desmarcar o outro
            outro_ultimo.ultimo_lote_linha = False
            outro_ultimo.save()
        
        # Marcar este como último
        lote.ultimo_lote_linha = True
        lote.save()
        
        return JsonResponse({
            'success': True,
            'marcado': True,
            'mensagem': 'Marcado como último lote da linha'
        })
        
    except Estoque.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lote não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_marcacoes_linha(request, rua, ln):
    """
    Retorna as posições afetadas pela marcação
    """
    try:
        # Encontrar o último lote marcado nesta linha
        ultimo = Estoque.objects.filter(
            endereco__startswith=f"{rua} {ln} P",
            ultimo_lote_linha=True
        ).first()
        
        if not ultimo:
            return JsonResponse({
                'success': True,
                'tem_marcacao': False,
                'posicoes_afetadas': []
            })
        
        dados_ultimo = extrair_ln_p(ultimo.endereco)
        if not dados_ultimo:
            return JsonResponse({
                'success': True,
                'tem_marcacao': False,
                'posicoes_afetadas': []
            })
        
        # Todas as posições da linha
        posicoes = get_posicoes_linha(rua, ln)
        
        # Filtrar posições >= a posição marcada
        posicoes_afetadas = [
            p['endereco'] for p in posicoes 
            if p['posicao'] >= dados_ultimo['posicao']
        ]
        
        return JsonResponse({
            'success': True,
            'tem_marcacao': True,
            'lote_marcado': ultimo.lote,
            'posicao_marcada': dados_ultimo['posicao'],
            'posicoes_afetadas': posicoes_afetadas
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


@login_required
def api_mapa_dados(request, armazem_numero):
    """API para retornar dados do mapa em formato JSON"""
    try:
        armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero)
        elementos = armazem.elementos.all()
        
        # Buscar estoque
        itens_estoque = Estoque.objects.filter(saldo__gt=0)
        ocupacao = {}
        
        for el in elementos:
            if el.tipo == 'RETANGULO' and el.identificador:
                chave = el.identificador.strip().upper()
                tem_estoque = itens_estoque.filter(endereco__iexact=chave).exists()
                if tem_estoque:
                    ocupacao[el.id] = True
        
        # Converter elementos para dicionário
        elementos_list = []
        for el in elementos:
            el_dict = {
                'id': el.id,
                'tipo': el.tipo,
                'x': el.pos_x,
                'y': el.pos_y,
                'w': el.largura,
                'h': el.altura,
                'rot': el.rotacao,
                'cor': el.cor_preenchimento,
                'stroke': el.cor_borda,
                'texto': el.conteudo_texto,
                'identificador': el.identificador,
            }
            elementos_list.append(el_dict)
        
        return JsonResponse({
            'success': True,
            'armazem': {
                'id': armazem.id,
                'numero': armazem.numero,
                'nome': armazem.nome,
                'largura_canvas': armazem.largura_canvas,
                'altura_canvas': armazem.altura_canvas,
            },
            'elementos': elementos_list,
            'ocupacao': ocupacao
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def api_marcacoes_ultimo_lote(request):
    """
    Retorna todas as posições que devem receber marcação de X
    (posições posteriores à posição marcada como último lote)
    """
    try:
        from .models import ArmazemLayout, ElementoMapa
        
        # Buscar todos os lotes marcados como último
        lotes_marcados = Estoque.objects.filter(
            ultimo_lote_linha=True,
            saldo__gt=0
        )
        
        marcacoes = {}
        
        for lote in lotes_marcados:
            # Extrair informações do endereço usando regex
            dados_end = extrair_info_endereco(lote.endereco)
            if not dados_end:
                continue
            
            rua = dados_end.get('rua')        # R-A
            ln = dados_end.get('linha')       # LN01
            posicao_marcada = dados_end.get('posicao')  # 4
            
            # Se não tiver posição, pula
            if not posicao_marcada:
                continue
            
            # Buscar no MAPA todos os endereços desta linha
            padrao = f"{rua} {ln} P"
            elementos = ElementoMapa.objects.filter(
                tipo='RETANGULO',
                identificador__startswith=padrao
            ).values_list('identificador', flat=True).distinct()
            
            # Para cada endereço do mapa, verificar se é posterior
            for endereco in elementos:
                dados_pos = extrair_info_endereco(endereco)
                if dados_pos and dados_pos.get('posicao', 0) > posicao_marcada:
                    marcacoes[endereco.strip().upper()] = True
        
        return JsonResponse({
            'success': True,
            'marcacoes': marcacoes,
            'total': len(marcacoes)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def api_get_armazem_by_rua(request):
    """
    Obtém o armazém a partir de um endereço
    """
    endereco_codigo = request.GET.get('endereco', '').strip().upper()
    
    if not endereco_codigo:
        return JsonResponse({'sucesso': False, 'msg': 'Endereço não informado'}, status=400)
    
    try:
        # Busca o endereço pelo código exato ou contém
        endereco = Endereco.objects.select_related('armazem').filter(
            codigo__icontains=endereco_codigo
        ).first()
        
        if endereco:
            # Extrai informações adicionais do endereço (se possível)
            dados = extrair_info_endereco(endereco.codigo)
            
            return JsonResponse({
                'sucesso': True, 
                'az': endereco.armazem.nome,
                'endereco': endereco.codigo,
                'rua': dados.get('rua') if dados else None,
                'linha': dados.get('linha') if dados else None,
                'posicao': dados.get('posicao') if dados else None
            })
        
        return JsonResponse({'sucesso': False, 'msg': 'Endereço não cadastrado'}, status=404)
        
    except Exception as e:
        return JsonResponse({'sucesso': False, 'msg': str(e)}, status=500)


def extrair_info_endereco(endereco_str):
    """
    Função auxiliar para extrair rua, linha e posição de um endereço
    Usa regex para extrair informações mesmo sem campos no banco
    
    Exemplos:
    - "R-A LN10 P02" -> {'rua': 'R-A', 'linha': 'LN10', 'posicao': 2}
    - "R-A LN10" -> {'rua': 'R-A', 'linha': 'LN10', 'posicao': None}
    - "R-A GERAL" -> {'rua': 'R-A', 'linha': 'GERAL', 'posicao': None}
    - "R-A" -> {'rua': 'R-A', 'linha': None, 'posicao': None}
    """
    import re
    
    if not endereco_str:
        return None
    
    endereco_str = endereco_str.strip().upper()
    
    # Padrão completo: R-A LN10 P02
    match_completo = re.match(r'^(R-[A-Z])\s+LN(\d{2})\s+P(\d{2})$', endereco_str)
    if match_completo:
        return {
            'rua': match_completo.group(1),
            'linha': f"LN{match_completo.group(2)}",
            'posicao': int(match_completo.group(3))
        }
    
    # Padrão sem posição: R-A LN10
    match_linha = re.match(r'^(R-[A-Z])\s+LN(\d{2})$', endereco_str)
    if match_linha:
        return {
            'rua': match_linha.group(1),
            'linha': f"LN{match_linha.group(2)}",
            'posicao': None
        }
    
    # Padrão geral: R-A GERAL
    match_geral = re.match(r'^(R-[A-Z])\s+GERAL$', endereco_str)
    if match_geral:
        return {
            'rua': match_geral.group(1),
            'linha': 'GERAL',
            'posicao': None
        }
    
    # Apenas a rua: R-A
    match_rua = re.match(r'^(R-[A-Z])$', endereco_str)
    if match_rua:
        return {
            'rua': match_rua.group(1),
            'linha': None,
            'posicao': None
        }
    
    # Formato livre: tenta extrair o primeiro como rua
    partes = endereco_str.split()
    return {
        'rua': partes[0] if partes else endereco_str,
        'linha': None,
        'posicao': None
    }


@login_required
def validar_endereco(request):
    """
    Valida endereço - busca nos endereços cadastrados e sugere cadastro se não existir
    """
    
    endereco_raw = request.GET.get('endereco', '').strip().upper()
    
    if not endereco_raw:
        return JsonResponse({
            'valido': False,
            'erro': 'Endereço não informado'
        })
    
    try:
        # Busca exata primeiro
        endereco_obj = Endereco.objects.filter(codigo=endereco_raw).select_related('armazem').first()
        
        if endereco_obj:
            return JsonResponse({
                'valido': True,
                'mensagem': f'✅ Endereço válido! Localizado no armazém {endereco_obj.armazem.nome}',
                'endereco_formatado': endereco_obj.codigo,
                'dados': {
                    'codigo': endereco_obj.codigo,
                    'id': endereco_obj.id,
                    'armazem': endereco_obj.armazem.nome,
                    'armazem_id': endereco_obj.armazem.id
                }
            })
        
        # Busca parcial (se digitar só parte do endereço)
        enderecos_similares = Endereco.objects.filter(
            codigo__icontains=endereco_raw
        ).select_related('armazem')[:5]
        
        if enderecos_similares.exists():
            sugestoes = [f"{e.codigo} ({e.armazem.nome})" for e in enderecos_similares]
            return JsonResponse({
                'valido': False,
                'erro': f'Endereço não encontrado. Você quis dizer: {", ".join(sugestoes)}?',
                'sugestoes': sugestoes
            })
        
        # Não encontrou nenhum
        return JsonResponse({
            'valido': False,
            'erro': f'❌ Endereço "{endereco_raw}" não cadastrado. Por favor, cadastre-o nas configurações primeiro.'
        })
        
    except Exception as e:
        return JsonResponse({
            'valido': False,
            'erro': f'Erro na validação: {str(e)}'
        })
    

@login_required
def buscar_origens(request):
    """
    Busca origens/destinos para autocomplete (mantida igual)
    """
    termo = request.GET.get('term', '').strip()
    if len(termo) < 2:
        return JsonResponse([], safe=False)
    
    origens = OrigemDestino.objects.filter(nome__icontains=termo)[:10]
    resultados = [{'id': o.id, 'nome': o.nome} for o in origens]
    
    return JsonResponse(resultados, safe=False)


@login_required
def api_buscar_enderecos(request):
    """
    Busca ENDEREÇOS para autocomplete (NOVA)
    """
    termo = request.GET.get('termo', '').strip().upper()
    
    if not termo or len(termo) < 2:
        return JsonResponse([], safe=False)
    
    enderecos = Endereco.objects.filter(
        codigo__icontains=termo
    ).select_related('armazem')[:10]
    
    resultados = []
    for end in enderecos:
        resultados.append({
            'id': end.id,
            'codigo': end.codigo,
            'armazem': end.armazem.nome,
            'label': f"{end.codigo} ({end.armazem.nome})",
            'value': end.codigo
        })
    
    return JsonResponse(resultados, safe=False)


@login_required
def api_listar_enderecos(request):
    """
    Lista TODOS os endereços para o frontend (NOVA)
    """
    enderecos = Endereco.objects.select_related('armazem').all().order_by('codigo')
    
    dados = []
    for end in enderecos:
        dados.append({
            'id': end.id,
            'codigo': end.codigo,
            'armazem': end.armazem.nome,
            'armazem_id': end.armazem.id
        })
    
    return JsonResponse(dados, safe=False)