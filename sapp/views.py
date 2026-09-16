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
from .models import Estoque, Cultivar, Peneira, Categoria, StatusSistemico
from django.db.models import Q, Sum, Prefetch, F
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

from django.db.models import (
    Case,
    F,
    IntegerField,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Trim, Upper
from django.core.cache import cache

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# App imports
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario, Especie, OrigemDestino,Armazem, Endereco, Solicitacao, ColunaKanban, 
    RegraWorkflow,
    HistoricoCard,
    ConfiguracaoAtualizacao,  


)
from collections import defaultdict
from .forms import (
    NovaEntradaForm, ConfiguracaoForm, CultivarForm, PeneiraForm, 
    CategoriaForm, TratamentoForm, NovoConferenteUserForm, MudarSenhaForm  
)


# sapp/views.py - No início do arquivo, adicione:

from django.shortcuts import render, redirect, reverse  # Adicione 'reverse' aqui
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse  # Também pode importar assim
from .models import (
    Produto, Cultivar, Peneira, Especie, Categoria, Tratamento, 
    Armazem, Endereco, OrigemDestino, Configuracao, normalizar_texto_cadastro
)
from .forms import ConfiguracaoForm, NovoConferenteUserForm

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
import unicodedata
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from django.db import transaction
from .models import FotoMovimentacao # e os outros models   
from .models import SolicitacaoItemCarga
    

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
from django.contrib.auth.decorators import login_required, permission_required
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
                'dt': timezone.localtime(mov.data_hora).strftime('%d/%m/%Y %H:%M') if mov.data_hora else '--',
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
        'conferente': 'conferente__username__in',
        'observacao': 'observacao__in'
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
    for field in ['saldo', 'empenhado', 'disponivel_filtro', 'peso_unitario', 'peso_total']:
        param_field = 'disponivel' if field == 'disponivel_filtro' else field
        min_val = request.GET.get(f'min_{param_field}')
        max_val = request.GET.get(f'max_{param_field}')
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

    # ================================================================
    # RESERVAS / EMPENHOS POR LOTE
    # ================================================================
    # O estoque físico continua separado por endereço, mas o usuário precisa
    # enxergar quando o LOTE possui reserva em qualquer endereço.
    lotes_visiveis = list(qs.values_list('lote', flat=True).distinct())
    empenhos_por_lote = {
        row['lote']: int(row['total'] or 0)
        for row in (
            Estoque.objects
            .filter(lote__in=lotes_visiveis)
            .values('lote')
            .annotate(total=Sum('empenhado'))
        )
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
    
    # Atributos transitórios usados apenas pelo template.
    # disponivel = saldo físico deste endereço - reserva atribuída a este registro.
    # empenhado_lote = reserva total do lote, independentemente do endereço.
    for item in page_obj.object_list:
        item.disponivel_ui = max(0, int(item.disponivel or 0))
        item.empenhado_lote_ui = empenhos_por_lote.get(item.lote, 0)

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


def _aplicar_filtro_valores(qs, lookup_in, valores):
    """Aplica multisseleção sem diferenciar maiúsculas/minúsculas e aceita vazio."""
    valores = [str(v) for v in (valores or []) if str(v).strip()]
    if not valores:
        return qs
    campo = lookup_in[:-4] if lookup_in.endswith('__in') else lookup_in
    tem_vazio = '__null__' in valores
    especificos = [v for v in valores if v != '__null__']
    cond = Q()
    for valor in especificos:
        cond |= Q(**{f'{campo}__iexact': str(valor).strip()})
    if tem_vazio:
        cond |= Q(**{f'{campo}__isnull': True}) | Q(**{campo: ''})
    return qs.filter(cond)


@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def gestao_estoque(request, template_name='sapp/gestao_estoque.html'):
    """
    View para gestão de estoque - MOSTRA APENAS LOTES COM SALDO > 0
    """
    
    # QuerySet Base - APENAS LOTES COM SALDO > 0 - NUNCA mostrar saldo zero
    qs = Estoque.objects.filter(saldo__gt=0).annotate(
        disponivel_filtro=F('saldo') - F('empenhado')
    ).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente', 'status_sistemico'
    ).order_by('-data_ultima_movimentacao', '-id')
    
    # NÃO existe qs_metrics separado - tudo deve usar o mesmo filtro
    
    # FILTRO POR STATUS SISTÊMICO
    # Aceita ID, nome e também a opção especial de status vazio.
    status_filter = request.GET.getlist('status_sistemico')

    if status_filter:
        status_ids = []
        incluir_vazio = '__null__' in status_filter

        for status_value in status_filter:
            if status_value == '__null__':
                continue
            try:
                if str(status_value).isdigit():
                    status_ids.append(int(status_value))
                else:
                    status_obj = StatusSistemico.objects.filter(
                        nome__iexact=str(status_value).strip()
                    ).first()
                    if status_obj:
                        status_ids.append(status_obj.id)
            except (TypeError, ValueError):
                pass

        if status_ids or incluir_vazio:
            cond_status = Q()
            if status_ids:
                cond_status |= Q(status_sistemico_id__in=status_ids)
            if incluir_vazio:
                cond_status |= Q(status_sistemico__isnull=True)
            qs = qs.filter(cond_status)
    
    # Busca Global
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | Q(peneira__nome__icontains=termo) |
                Q(categoria__nome__icontains=termo) | Q(especie__nome__icontains=termo) |
                Q(tratamento__nome__icontains=termo) | Q(endereco__icontains=termo) |
                Q(az__icontains=termo) | Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo) | Q(conferente__username__icontains=termo) |
                Q(observacao__icontains=termo)
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
        'conferente': 'conferente__username__in',
        'observacao': 'observacao__in'
    }

    for param, lookup in filter_map.items():
        qs = _aplicar_filtro_valores(qs, lookup, request.GET.getlist(param))

    # Filtros numéricos de todas as colunas quantitativas.
    numeric_fields = {
        'saldo': 'saldo',
        'empenhado': 'empenhado',
        'disponivel': 'disponivel_filtro',
        'peso_unitario': 'peso_unitario',
        'peso_total': 'peso_total',
    }
    for param, field in numeric_fields.items():
        min_val = request.GET.get(f'min_{param}')
        max_val = request.GET.get(f'max_{param}')
        if min_val:
            try:
                qs = qs.filter(**{f'{field}__gte': Decimal(str(min_val).replace(',', '.'))})
            except (ValueError, InvalidOperation):
                pass
        if max_val:
            try:
                qs = qs.filter(**{f'{field}__lte': Decimal(str(max_val).replace(',', '.'))})
            except (ValueError, InvalidOperation):
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
    status_ids_em_uso = qs.exclude(
        status_sistemico__isnull=True
    ).values_list(
        'status_sistemico_id',
        flat=True
    ).distinct()

    status_em_uso = StatusSistemico.objects.filter(
        ativo=True,
        id__in=status_ids_em_uso
    ).order_by('ordem', 'nome')

    status_options = [
        {
            'value': str(s.id),
            'label': f"{s.icone or ''} {s.nome}".strip()
        }
        for s in status_em_uso
    ]
    
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
        'conferente': get_options_list('conferente__username'),
        'observacao': get_options_list('observacao')
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

    total_empenhado = qs.aggregate(e=Sum('empenhado'))['e'] or 0
    total_disponivel = (qs.aggregate(s=Sum('saldo'))['s'] or 0) - total_empenhado

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
        'total_empenhado': total_empenhado,
        'total_disponivel': total_disponivel,
    }
    
    return render(request, template_name, context)



@login_required
def opcoes_filtro_api(request):
    coluna = request.GET.get('coluna')

    if not coluna:
        return JsonResponse({
            'success': False,
            'error': 'Coluna não especificada'
        })

    qs = Estoque.objects.filter(saldo__gt=0)

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

    field_map = {
        'az': 'az',
        'lote': 'lote',
        'produto': 'produto',
        'cultivar': 'cultivar__nome',
        'peneira': 'peneira__nome',
        'categoria': 'categoria__nome',
        'endereco': 'endereco',
        'saldo': 'saldo',
        'peso_unitario': 'peso_unitario',
        'peso_total': 'peso_total',
        'especie': 'especie__nome',
        'tratamento': 'tratamento__nome',
        'embalagem': 'embalagem',
        'cliente': 'cliente',
        'empresa': 'empresa',
        'conferente': 'conferente__username',
    }

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
        'conferente': 'conferente__username__in',
    }

    for param, lookup in filter_map.items():
        if param == coluna:
            continue

        values = request.GET.getlist(param)
        values = [v for v in values if v and v.strip()]

        if values:
            if '__null__' in values:
                specific_values = [v for v in values if v != '__null__']
                null_lookup = lookup.replace('__in', '__isnull')

                if specific_values:
                    qs = qs.filter(
                        Q(**{lookup: specific_values}) |
                        Q(**{null_lookup: True})
                    )
                else:
                    qs = qs.filter(**{null_lookup: True})
            else:
                qs = qs.filter(**{lookup: values})

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

    status_filter = request.GET.getlist('status_sistemico')
    if status_filter and coluna != 'status_sistemico':
        status_ids = []

        for status_value in status_filter:
            try:
                if str(status_value).isdigit():
                    status_ids.append(int(status_value))
                else:
                    status_obj = StatusSistemico.objects.get(nome=status_value)
                    status_ids.append(status_obj.id)
            except StatusSistemico.DoesNotExist:
                pass

        if status_ids:
            qs = qs.filter(status_sistemico__in=status_ids)

    if coluna == 'status_sistemico':
        status_ids_em_uso = qs.exclude(
            status_sistemico__isnull=True
        ).values_list(
            'status_sistemico_id',
            flat=True
        ).distinct()

        status_em_uso = StatusSistemico.objects.filter(
            ativo=True,
            id__in=status_ids_em_uso
        ).order_by('ordem', 'nome')

        opcoes = [
            {
                'value': str(s.id),
                'label': f"{s.icone or ''} {s.nome}".strip()
            }
            for s in status_em_uso
        ]

        return JsonResponse({
            'success': True,
            'opcoes': opcoes,
            'tem_null': qs.filter(status_sistemico__isnull=True).exists()
        })

    if coluna not in field_map:
        return JsonResponse({
            'success': False,
            'error': f'Coluna inválida: {coluna}'
        })

    field = field_map[coluna]

    try:
        values = qs.filter(
            **{f'{field}__isnull': False}
        ).exclude(
            **{f'{field}': ''}
        ).values_list(
            field, flat=True
        ).distinct().order_by(field)

        values = [v for v in values if v is not None and str(v).strip() != '']

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

    opcoes = [
        {
            'value': str(v),
            'label': str(v)
        }
        for v in values
    ]

    tem_null = qs.filter(**{f'{field}__isnull': True}).exists()

    return JsonResponse({
        'success': True,
        'opcoes': opcoes,
        'tem_null': tem_null
    })

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def registrar_saida(request, id):
    print("🔍 [REGISTRAR SAÍDA] Iniciando processamento da expedição")

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Bloqueia o registro de estoque até o fim da transação.
                # Isso impede duas requisições simultâneas de lerem o mesmo saldo.
                item = Estoque.objects.select_for_update(of=('self',)).get(id=id)

                # 1. Captura de Dados
                qtd = int(request.POST.get('quantidade_saida', 0))
                carga = request.POST.get('numero_carga', '')
                nome_carga_avulsa = ' '.join(str(request.POST.get('nome_carga_avulsa', '') or '').strip().split())
                motorista = request.POST.get('motorista', '')
                placa = request.POST.get('placa', '')
                cliente = request.POST.get('cliente', '')
                obs = request.POST.get('observacao', '')
                fotos = request.FILES.getlist('fotos')
                operation_token = ''.join(
                    ch for ch in str(request.POST.get('operation_token') or '').strip()
                    if ch.isalnum() or ch in '-_:.'
                )[:160]

                # Idempotência: cada abertura do modal envia um token. Se o mesmo
                # formulário chegar novamente por duplo clique/reenvio, a segunda
                # requisição não movimenta o estoque outra vez.
                if operation_token and HistoricoMovimentacao.objects.filter(
                    estoque=item,
                    tipo='Expedição',
                    descricao__contains=f'data-operation-token="{operation_token}"',
                ).exists():
                    messages.warning(request, '⚠️ Esta expedição já foi processada. O envio duplicado foi ignorado.')
                    return redirect('sapp:lista_estoque')

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
                disponivel_avulso = max(0, int(item.disponivel or 0))
                if qtd > disponivel_avulso:
                    if item.empenhado > 0:
                        erros.append(
                            f"🔒 Este registro possui {item.empenhado} unidade(s) empenhada(s). "
                            f"Na expedição avulsa só é permitido expedir o disponível: {disponivel_avulso}. "
                            "Para expedir a parte empenhada, abra o card correspondente."
                        )
                    else:
                        erros.append(
                            f"❌ Quantidade acima do disponível ({disponivel_avulso})."
                        )
                # Na carga avulsa, número, nome, placa, motorista, cliente e fotos
                # são opcionais. Lote e quantidade continuam sendo a movimentação real.
                
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
                obs_historico = f"[EXPEDIÇÃO {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}] Carga: {carga}, Motorista: {motorista}"
                if obs:
                    obs_historico += f" | Obs: {obs}"
                
                if item.observacao:
                    item.observacao += f"\n\n{obs_historico}"
                else:
                    item.observacao = obs_historico
                
                item.save()
                print(f"✅ Item atualizado: {item.lote} | Saldo anterior: {saldo_anterior} → Novo saldo: {item.saldo}")

                # 5. Descrição Rica em HTML para o Histórico
                token_html = (
                    f'<span class="d-none" data-operation-token="{operation_token}"></span>'
                    if operation_token else ''
                )
                desc_html = f"""
                    {token_html}
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
                            <i class="fas fa-clock"></i> <strong>Data/Hora:</strong> {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}
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
                    numero_carga=carga or None,
                    motorista=motorista or None,
                    placa=placa or None,
                    cliente=cliente or None,
                    origem_carga='AVULSA',
                    nome_carga_avulsa=nome_carga_avulsa,
                )

                print(f"✅ Histórico criado: ID {historico.id}")

                # 7. **CORREÇÃO CRÍTICA: Salvar Fotos**
                fotos_salvas = 0
                for foto in fotos:
                    try:
                        # CORREÇÃO AQUI: Use o objeto 'historico' diretamente
                        FotoMovimentacao.objects.create(
                            historico=historico,
                            arquivo=foto,
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

        except Estoque.DoesNotExist:
            messages.error(request, '❌ Lote não encontrado.')
        except Exception as e:
            import traceback
            print(f"💥 ERRO CRÍTICO NA EXPEDIÇÃO:")
            print(f"   Mensagem: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            messages.error(request, f"❌ Erro crítico ao registrar expedição: {str(e)}")
            
    return redirect('sapp:lista_estoque')

from django.views.decorators.csrf import csrf_protect

def _realocar_empenho_apos_transferencia_avulsa(origem, destino):
    """
    Mantém o empenho vivo quando uma transferência AVULSA desloca fisicamente
    um lote para outro endereço.

    A reserva só é realocada se o saldo restante da origem não for suficiente
    para sustentar o empenho atualmente vinculado àquele registro.
    A transferência não consome a reserva. O consumo continua acontecendo
    apenas nas movimentações feitas pelo card.
    """
    origem.refresh_from_db(fields=['saldo', 'empenhado'])
    destino.refresh_from_db(fields=['saldo', 'empenhado'])

    excesso = max(0, int(origem.empenhado or 0) - int(origem.saldo or 0))
    if excesso <= 0:
        return 0

    itens = list(
        ItemEmpenho.objects
        .select_for_update()
        .filter(estoque=origem)
        .select_related('empenho')
        .order_by('id')
    )

    restante = excesso
    movido = 0

    for item in itens:
        if restante <= 0:
            break

        qtd_item = int(item.quantidade or 0)
        qtd_mover = min(qtd_item, restante)
        if qtd_mover <= 0:
            continue

        destino_item = (
            ItemEmpenho.objects
            .select_for_update()
            .filter(empenho=item.empenho, estoque=destino)
            .first()
        )

        if qtd_mover == qtd_item:
            if destino_item:
                ItemEmpenho.objects.filter(pk=destino_item.pk).update(
                    quantidade=F('quantidade') + qtd_mover
                )
                # QuerySet.delete() é intencional: não chama ItemEmpenho.delete(),
                # pois os contadores de estoque são ajustados manualmente abaixo.
                ItemEmpenho.objects.filter(pk=item.pk).delete()
            else:
                ItemEmpenho.objects.filter(pk=item.pk).update(estoque=destino)
        else:
            ItemEmpenho.objects.filter(pk=item.pk).update(
                quantidade=F('quantidade') - qtd_mover
            )

            if destino_item:
                ItemEmpenho.objects.filter(pk=destino_item.pk).update(
                    quantidade=F('quantidade') + qtd_mover
                )
            else:
                # Criação por bulk_create para preservar o snapshot original
                # sem disparar ItemEmpenho.save() e duplicar os contadores.
                clone = ItemEmpenho(
                    empenho=item.empenho,
                    estoque=destino,
                    quantidade=qtd_mover,
                    endereco_origem=item.endereco_origem,
                    endereco_destino=item.endereco_destino,
                    observacao=item.observacao,
                    lote=item.lote,
                    cultivar=item.cultivar,
                    peneira=item.peneira,
                    categoria=item.categoria,
                    saldo_anterior=item.saldo_anterior,
                    produto_snapshot=item.produto_snapshot,
                    especie_snapshot=item.especie_snapshot,
                    tratamento_snapshot=item.tratamento_snapshot,
                    embalagem_snapshot=item.embalagem_snapshot,
                    empresa_snapshot=item.empresa_snapshot,
                    cliente_snapshot=item.cliente_snapshot,
                    az_origem=item.az_origem,
                    peso_unitario_snapshot=item.peso_unitario_snapshot,
                    observacao_snapshot=item.observacao_snapshot,
                    conferente_snapshot=item.conferente_snapshot,
                )
                ItemEmpenho.objects.bulk_create([clone])

        restante -= qtd_mover
        movido += qtd_mover

    if movido:
        Estoque.objects.filter(pk=origem.pk).update(
            empenhado=F('empenhado') - movido
        )
        Estoque.objects.filter(pk=destino.pk).update(
            empenhado=F('empenhado') + movido
        )
        origem.refresh_from_db(fields=['saldo', 'empenhado'])
        destino.refresh_from_db(fields=['saldo', 'empenhado'])

    return movido


@csrf_protect
@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def transferir(request, id):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                origem = Estoque.objects.select_for_update(of=('self',)).get(id=id)
                qtd = int(request.POST.get('quantidade', 0))
                tipo_transferencia = request.POST.get('tipo_transferencia', 'normal')
                novo_end = request.POST.get('novo_endereco', '').strip().upper()
                operation_token = ''.join(
                    ch for ch in str(request.POST.get('operation_token') or '').strip()
                    if ch.isalnum() or ch in '-_:.'
                )[:160]
                token_marker = (
                    f'<!-- data-operation-token="{operation_token}" -->'
                    if operation_token else ''
                )

                if operation_token and HistoricoMovimentacao.objects.filter(
                    estoque=origem,
                    descricao__contains=f'data-operation-token="{operation_token}"',
                ).exists():
                    messages.warning(request, '⚠️ Esta movimentação já foi processada. O envio duplicado foi ignorado.')
                    return redirect('sapp:lista_estoque')
                
                # === VALIDAÇÕES BÁSICAS (COMUNS A AMBOS OS TIPOS) ===
                if qtd <= 0:
                    messages.error(request, "❌ Quantidade deve ser maior que zero!")
                    return redirect('sapp:lista_estoque')
                
                if qtd > origem.saldo:
                    messages.error(
                        request,
                        f"❌ Quantidade acima do saldo físico ({origem.saldo})."
                    )
                    return redirect('sapp:lista_estoque')

                empenhado_lote = int(
                    Estoque.objects
                    .filter(lote=origem.lote)
                    .aggregate(total=Sum('empenhado'))['total']
                    or 0
                )

                # Beneficiamento é uma saída definitiva. Não pode consumir a
                # parcela empenhada fora do card.
                if tipo_transferencia == 'beneficiamento' and qtd > max(0, int(origem.disponivel or 0)):
                    messages.error(
                        request,
                        f"🔒 O lote possui reserva ativa. Para beneficiamento avulso, "
                        f"use no máximo o disponível ({max(0, int(origem.disponivel or 0))}). "
                        "A parte empenhada só pode ser consumida pelo card."
                    )
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
                    descricao_beneficiamento = f"{token_marker} Enviado para beneficiamento – Quantidade: {qtd} {origem.embalagem}"
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
                                destino_existente.observacao = f"{obs_atual}\n[TRANSFERÊNCIA {timezone.localtime(timezone.now()).strftime('%d/%m %H:%M')}]: {nova_obs}"
                            else:
                                destino_existente.observacao = f"[TRANSFERÊNCIA {timezone.localtime(timezone.now()).strftime('%d/%m %H:%M')}]: {nova_obs}"
                        
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
                    
                    # Se a transferência avulsa deslocou quantidade que era
                    # necessária para sustentar uma reserva, move internamente a
                    # reserva para o destino SEM consumir o empenho.
                    reserva_realocada = _realocar_empenho_apos_transferencia_avulsa(
                        origem,
                        destino,
                    )

                    # Históricos (Saída da origem)
                    hist_saida = HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        tipo='Transferência (Saída)',
                        descricao=f"{token_marker} Transferido para {novo_end} ({destino.lote}) - Quantidade: {qtd} {origem.embalagem} | {mensagem_tipo}"
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
                    
                    if empenhado_lote > 0:
                        aviso_reserva = (
                            f" ⚠️ O lote possui {empenhado_lote} unidade(s) empenhada(s). "
                            "A transferência foi permitida e o empenho foi preservado."
                        )
                        if reserva_realocada:
                            aviso_reserva += (
                                f" {reserva_realocada} unidade(s) da reserva passaram a "
                                f"acompanhar o estoque no endereço {novo_end}."
                            )
                        messages.warning(request, aviso_reserva)

                    messages.success(
                        request,
                        f"✅ Transferência concluída! {qtd} unidades {mensagem_tipo} em {novo_end}."
                    )
                
        except Estoque.DoesNotExist:
            messages.error(request, '❌ Lote não encontrado.')
        except Exception as e:
            import traceback
            print(f"❌ ERRO NA TRANSFERÊNCIA: {e}")
            print(traceback.format_exc())
            messages.error(request, f"❌ Erro ao transferir: {str(e)}")
            
    return redirect('sapp:lista_estoque')



# No seu views.py
from django.http import JsonResponse

@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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

def _resolver_produto_para_lote(codigo, cultivar, tratamento):
    """Resolve o Produto para um lote. Código informado tem prioridade.

    Sem código, a combinação Cultivar + Tratamento só é usada quando identifica
    exatamente um Produto ativo. Em caso de ambiguidade o usuário precisa informar
    o código, evitando associação silenciosa ao produto errado.
    """
    codigo = _normalizar_codigo_produto(codigo)
    if codigo:
        produto = Produto.objects.filter(codigo__iexact=codigo, ativo=True).first()
        return produto, codigo

    qs = Produto.objects.filter(cultivar=cultivar, ativo=True)
    if tratamento is None:
        qs = qs.filter(tratamento__isnull=True)
    else:
        qs = qs.filter(tratamento=tratamento)

    encontrados = list(qs.order_by('id')[:2])
    if len(encontrados) == 1:
        return encontrados[0], _normalizar_codigo_produto(encontrados[0].codigo)
    if len(encontrados) > 1:
        raise ValueError(
            f'Existe mais de um produto ativo para {cultivar} / '
            f'{tratamento or "SEM TRATAMENTO"}. Informe o código para identificar corretamente.'
        )
    return None, ''


def _aplicar_produto_ao_lote_por_codigo(item, produto):
    """Quando o código é conhecido, completa os parâmetros cadastrados sem apagar dados opcionais."""
    if not produto:
        return item
    item.produto = _normalizar_codigo_produto(produto.codigo)
    item.cultivar = produto.cultivar or item.cultivar
    if produto.tratamento_id is not None:
        item.tratamento = produto.tratamento
    if produto.peneira_id is not None:
        item.peneira = produto.peneira
    if produto.categoria_id is not None:
        item.categoria = produto.categoria
    if produto.especie_id is not None:
        item.especie = produto.especie
    if produto.empresa:
        item.empresa = produto.empresa
    return item

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def nova_entrada(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = normalizar_texto_cadastro(request.POST.get('lote', ''))
                endereco = normalizar_texto_cadastro(request.POST.get('endereco', ''))
                produto = _normalizar_codigo_produto(request.POST.get('produto', ''))
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

                produto_obj, produto_resolvido = _resolver_produto_para_lote(
                    produto, cultivar, tratamento
                )
                if produto_resolvido:
                    produto = produto_resolvido

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
                    item.observacao += f"\n[+ENTRADA {qtd} em {timezone.localtime(timezone.now()).strftime('%d/%m')}]"
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
                        cliente=normalizar_texto_cadastro(request.POST.get('cliente', '')),
                        empresa=normalizar_texto_cadastro(request.POST.get('empresa', '')),
                        az=normalizar_texto_cadastro(request.POST.get('az', '')),
                        origem_destino=normalizar_texto_cadastro(request.POST.get('origem_destino', '')),
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
                
                _aplicar_produto_ao_lote_por_codigo(item, produto_obj)
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
                    quantidade=qtd,
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
            
            disponivel_avulso = max(0, int(item.disponivel or 0))
            if quantidade > disponivel_avulso:
                if item.empenhado > 0:
                    messages.error(
                        request,
                        f"🔒 O lote possui {item.empenhado} unidade(s) empenhada(s) neste endereço. "
                        f"Expedição avulsa limitada ao disponível ({disponivel_avulso}). "
                        "A quantidade empenhada só pode ser expedida pelo card."
                    )
                else:
                    messages.error(
                        request,
                        f"❌ Quantidade excede o disponível ({disponivel_avulso})."
                    )
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
                    item.observacao += f"\n\n[EXPEDIÇÃO GERAL {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}]: {observacao}"
                else:
                    item.observacao = f"[EXPEDIÇÃO GERAL {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}]: {observacao}"
            
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
def api_estoque_estatisticas(request):
    """API para atualizar os cards de estatísticas com base nos filtros atuais"""
    
    # Query base - apenas saldo > 0
    qs = Estoque.objects.filter(saldo__gt=0).annotate(disponivel_filtro=F('saldo') - F('empenhado'))
    
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
                Q(cultivar__nome__icontains=termo) | Q(peneira__nome__icontains=termo) |
                Q(categoria__nome__icontains=termo) | Q(especie__nome__icontains=termo) |
                Q(tratamento__nome__icontains=termo) | Q(endereco__icontains=termo) |
                Q(az__icontains=termo) | Q(cliente__icontains=termo) | Q(empresa__icontains=termo) |
                Q(conferente__username__icontains=termo) | Q(observacao__icontains=termo)
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
        'conferente': 'conferente__username__in',
        'observacao': 'observacao__in'
    }

    for param, lookup in filter_map.items():
        qs = _aplicar_filtro_valores(qs, lookup, request.GET.getlist(param))

    numeric_fields = {
        'saldo': 'saldo', 'empenhado': 'empenhado', 'disponivel': 'disponivel_filtro',
        'peso_unitario': 'peso_unitario', 'peso_total': 'peso_total',
    }
    for param, field in numeric_fields.items():
        min_val = request.GET.get(f'min_{param}')
        max_val = request.GET.get(f'max_{param}')
        if min_val:
            try: qs = qs.filter(**{f'{field}__gte': Decimal(str(min_val).replace(',', '.'))})
            except (ValueError, InvalidOperation): pass
        if max_val:
            try: qs = qs.filter(**{f'{field}__lte': Decimal(str(max_val).replace(',', '.'))})
            except (ValueError, InvalidOperation): pass
    
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
def api_opcoes_filtro(request):
    """Opções encadeadas para TODOS os filtros da Gestão de Estoque.

    A mesma nomenclatura usada no HTML é usada aqui. Ao abrir uma coluna,
    os filtros das demais colunas continuam valendo, no estilo do Excel.
    """
    coluna = str(request.GET.get('coluna') or '').strip()
    if not coluna:
        return JsonResponse({'success': False, 'error': 'Coluna não especificada'}, status=400)

    campos_texto = {
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
        'conferente': 'conferente__username',
        'observacao': 'observacao',
    }
    campos_numericos = {
        'saldo': 'saldo',
        'empenhado': 'empenhado',
        'disponivel': 'disponivel_filtro',
        'peso_unitario': 'peso_unitario',
        'peso_total': 'peso_total',
    }
    colunas_validas = set(campos_texto) | set(campos_numericos) | {'status_sistemico'}
    if coluna not in colunas_validas:
        return JsonResponse({'success': False, 'error': f'Coluna inválida: {coluna}'}, status=400)

    qs = Estoque.objects.filter(saldo__gt=0).annotate(
        disponivel_filtro=F('saldo') - F('empenhado')
    )

    # Busca geral, idêntica à página principal.
    busca = str(request.GET.get('busca') or '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | Q(peneira__nome__icontains=termo) |
                Q(categoria__nome__icontains=termo) | Q(especie__nome__icontains=termo) |
                Q(tratamento__nome__icontains=termo) | Q(endereco__icontains=termo) |
                Q(az__icontains=termo) | Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo) | Q(conferente__username__icontains=termo) |
                Q(observacao__icontains=termo)
            )

    # Status atual, exceto quando o próprio menu de Status está sendo aberto.
    if coluna != 'status_sistemico':
        valores_status = request.GET.getlist('status_sistemico')
        if valores_status:
            ids_status = []
            incluir_vazio = '__null__' in valores_status
            for valor in valores_status:
                if valor == '__null__':
                    continue
                if str(valor).isdigit():
                    ids_status.append(int(valor))
                else:
                    status_obj = StatusSistemico.objects.filter(nome__iexact=str(valor).strip()).first()
                    if status_obj:
                        ids_status.append(status_obj.id)
            if ids_status or incluir_vazio:
                cond = Q()
                if ids_status:
                    cond |= Q(status_sistemico_id__in=ids_status)
                if incluir_vazio:
                    cond |= Q(status_sistemico__isnull=True)
                qs = qs.filter(cond)

    # Demais colunas de seleção, exceto a coluna que está sendo aberta.
    for param, campo in campos_texto.items():
        if param == coluna:
            continue
        valores = [str(v) for v in request.GET.getlist(param) if str(v).strip()]
        if not valores:
            continue

        incluir_vazio = '__null__' in valores
        especificos = [v for v in valores if v != '__null__']
        cond = Q()
        if especificos:
            # OR com iexact torna o filtro tolerante a cadastros antigos com
            # diferenças de maiúsculas/minúsculas.
            for valor in especificos:
                cond |= Q(**{f'{campo}__iexact': valor})
        if incluir_vazio:
            cond |= Q(**{f'{campo}__isnull': True}) | Q(**{campo: ''})
        qs = qs.filter(cond)

    # Demais filtros numéricos, exceto a coluna que está sendo aberta.
    for param, campo in campos_numericos.items():
        if param == coluna:
            continue
        min_val = request.GET.get(f'min_{param}')
        max_val = request.GET.get(f'max_{param}')
        if min_val not in (None, ''):
            try:
                qs = qs.filter(**{f'{campo}__gte': Decimal(str(min_val).replace(',', '.'))})
            except (ValueError, InvalidOperation):
                pass
        if max_val not in (None, ''):
            try:
                qs = qs.filter(**{f'{campo}__lte': Decimal(str(max_val).replace(',', '.'))})
            except (ValueError, InvalidOperation):
                pass

    # Colunas numéricas usam mínimo/máximo e não precisam de lista de opções.
    if coluna in campos_numericos:
        return JsonResponse({'success': True, 'opcoes': [], 'tem_null': False})

    if coluna == 'status_sistemico':
        ids_em_uso = qs.exclude(status_sistemico__isnull=True).values_list(
            'status_sistemico_id', flat=True
        ).distinct()
        status = StatusSistemico.objects.filter(
            ativo=True, id__in=ids_em_uso
        ).order_by('ordem', 'nome')
        return JsonResponse({
            'success': True,
            'opcoes': [
                {'value': str(s.id), 'label': f'{s.icone or ""} {s.nome}'.strip()}
                for s in status
            ],
            'tem_null': qs.filter(status_sistemico__isnull=True).exists(),
        })

    campo = campos_texto[coluna]
    tem_null = (
        qs.filter(**{f'{campo}__isnull': True}).exists()
        or qs.filter(**{campo: ''}).exists()
    )
    valores = (
        qs.exclude(**{f'{campo}__isnull': True})
        .exclude(**{campo: ''})
        .values_list(campo, flat=True)
        .distinct()
        .order_by(campo)
    )
    opcoes = [
        {'value': str(v), 'label': str(v)}
        for v in valores
        if v is not None and str(v).strip()
    ]
    return JsonResponse({'success': True, 'opcoes': opcoes, 'tem_null': tem_null})


############################################################################
# NO VIEWS.PY - CORRIGIR A FUNÇÃO editar COMPLETAMENTE:
@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
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
                novo_lote = normalizar_texto_cadastro(request.POST.get('lote', ''))
                novo_endereco = normalizar_texto_cadastro(request.POST.get('endereco', ''))
                novo_empresa = normalizar_texto_cadastro(request.POST.get('empresa', ''))
                novo_origem_destino = normalizar_texto_cadastro(request.POST.get('origem_destino', ''))
                novo_produto = _normalizar_codigo_produto(request.POST.get('produto', ''))
                novo_cliente = normalizar_texto_cadastro(request.POST.get('cliente', ''))
                
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
                novo_az = normalizar_texto_cadastro(request.POST.get('az', ''))
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

                produto_obj, codigo_resolvido = _resolver_produto_para_lote(
                    novo_produto, obj_cultivar, obj_tratamento
                )
                if codigo_resolvido:
                    novo_produto = codigo_resolvido
                if produto_obj:
                    obj_cultivar = produto_obj.cultivar or obj_cultivar
                    obj_tratamento = produto_obj.tratamento if produto_obj.tratamento_id is not None else obj_tratamento
                    obj_peneira = produto_obj.peneira if produto_obj.peneira_id is not None else obj_peneira
                    obj_categoria = produto_obj.categoria if produto_obj.categoria_id is not None else obj_categoria
                    obj_especie = produto_obj.especie if produto_obj.especie_id is not None else obj_especie
                    if produto_obj.empresa:
                        novo_empresa = produto_obj.empresa

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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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





# sapp/views.py - Função completa corrigida

# sapp/views.py - Substitua a função configuracoes por esta versão SIMPLIFICADA

def _normalizar_coluna_planilha(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_')


def _valor_linha_planilha(linha, *nomes):
    for nome in nomes:
        valor = linha.get(_normalizar_coluna_planilha(nome), '')
        if pd.notna(valor) and str(valor).strip():
            return str(valor).strip()
    return ''


def _resolver_fk_planilha(model, valor, rotulo, obrigatorio=False):
    valor = normalizar_texto_cadastro(valor)
    if not valor:
        if obrigatorio:
            raise ValueError(f'{rotulo} é obrigatório e deve existir na base de Configurações.')
        return None

    # A planilha NUNCA cria dependências automaticamente.
    # O valor precisa corresponder a uma opção já cadastrada na base.
    obj = model.objects.filter(nome__iexact=valor).first()
    if not obj:
        opcoes = list(
            model.objects
            .order_by('nome')
            .values_list('nome', flat=True)[:12]
        )
        exemplo = ', '.join(str(v) for v in opcoes) if opcoes else 'nenhuma opção cadastrada'
        raise ValueError(
            f'{rotulo} "{valor}" não existe na base. '
            f'Use exatamente um valor cadastrado em Configurações. Base disponível: {exemplo}.'
        )
    return obj



CONFIG_IMPORT_SCHEMAS = {
    'cultivar': {'titulo': 'Cultivares', 'headers': ['nome']},
    'peneira': {'titulo': 'Peneiras', 'headers': ['nome']},
    'especie': {'titulo': 'Espécies', 'headers': ['nome']},
    'categoria': {'titulo': 'Categorias', 'headers': ['nome']},
    'tratamento': {'titulo': 'Tratamentos', 'headers': ['nome']},
    'produto': {
        'titulo': 'Produtos',
        'headers': [
            'codigo', 'cultivar', 'descricao', 'peneira', 'especie',
            'categoria', 'tratamento', 'empresa', 'tipo', 'ativo',
        ],
    },
    'armazem': {'titulo': 'Armazéns', 'headers': ['nome']},
    'endereco': {'titulo': 'Endereços', 'headers': ['codigo', 'armazem']},
    'origem': {'titulo': 'Origens e Destinos', 'headers': ['nome']},
}


def _schema_importacao_config(tipo):
    tipo = str(tipo or '').strip().lower()
    schema = CONFIG_IMPORT_SCHEMAS.get(tipo)
    if not schema:
        raise ValueError('Tipo de cadastro inválido para importação.')
    return tipo, schema


def _validar_bases_importacao(tipo):
    """Impede importar registros dependentes antes das respectivas bases."""
    tipo, _ = _schema_importacao_config(tipo)

    if tipo == 'produto':
        # No cadastro manual, somente Cultivar é uma relação obrigatória.
        # Peneira, Espécie, Categoria e Tratamento são opcionais.
        # Quando forem informados na planilha, _resolver_fk_planilha()
        # continua exigindo que o valor exista exatamente na respectiva base.
        if not Cultivar.objects.exists():
            raise ValueError(
                'Antes de importar Produtos, cadastre pelo menos um Cultivar na base.'
            )

    elif tipo == 'endereco' and not Armazem.objects.exists():
        raise ValueError('Antes de importar Endereços, cadastre pelo menos um Armazém na base.')


def _linhas_arquivo_base_config(tipo, arquivo):
    """Aceita apenas o XLSX-base da própria aba e valida o cabeçalho exato."""
    tipo, schema = _schema_importacao_config(tipo)

    if not arquivo:
        raise ValueError('Selecione o arquivo base preenchido para importar.')

    nome = str(getattr(arquivo, 'name', '') or '').lower()
    if not nome.endswith('.xlsx'):
        raise ValueError('Use o arquivo base XLSX baixado nesta aba.')

    try:
        workbook = load_workbook(arquivo, read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError(f'Não foi possível abrir o arquivo XLSX: {exc}')

    try:
        if 'IMPORTAR' not in workbook.sheetnames:
            raise ValueError('Arquivo fora do padrão. Baixe novamente o modelo desta aba.')

        sheet = workbook['IMPORTAR']
        cabecalhos = [_normalizar_coluna_planilha(cell.value) for cell in sheet[1]]
        while cabecalhos and not cabecalhos[-1]:
            cabecalhos.pop()

        esperado = [_normalizar_coluna_planilha(col) for col in schema['headers']]
        if cabecalhos != esperado:
            raise ValueError(
                'Arquivo fora do modelo desta aba. '
                f"Colunas esperadas: {', '.join(schema['headers'])}. "
                f"Colunas encontradas: {', '.join(cabecalhos) or '(sem cabeçalho)'}. "
                'Baixe o arquivo base novamente e não altere as colunas.'
            )

        linhas = []
        for numero_linha, valores in enumerate(
            sheet.iter_rows(min_row=2, max_col=len(esperado), values_only=True),
            start=2,
        ):
            if not any(str(valor or '').strip() for valor in valores):
                continue
            linhas.append((
                numero_linha,
                {
                    esperado[idx]: ('' if valor is None else str(valor).strip())
                    for idx, valor in enumerate(valores)
                },
            ))

        if not linhas:
            raise ValueError('O arquivo base não possui nenhuma linha preenchida.')
        return linhas
    finally:
        workbook.close()


def _adicionar_validacao_lista(ws, coluna, valores, coluna_base, max_linhas=1000):
    valores = [str(v).strip() for v in valores if str(v).strip()]
    if not valores:
        return
    fim = len(valores) + 1
    dv = DataValidation(
        type='list',
        formula1=f"'BASES'!${coluna_base}$2:${coluna_base}${fim}",
        allow_blank=True,
    )
    dv.error = 'Selecione um valor existente na aba BASES.'
    dv.errorTitle = 'Valor inválido'
    dv.prompt = 'Use um valor da base cadastrada no sistema.'
    dv.promptTitle = 'Base do sistema'
    ws.add_data_validation(dv)
    dv.add(f'{coluna}2:{coluna}{max_linhas}')


@login_required
@permission_required('sapp.pode_configuracoes', raise_exception=True)
def baixar_modelo_configuracao(request, tipo):
    """Gera o arquivo-base XLSX específico da aba de Configurações."""
    try:
        tipo, schema = _schema_importacao_config(tipo)
    except ValueError as exc:
        return HttpResponse(str(exc), status=404, content_type='text/plain; charset=utf-8')

    workbook = Workbook()
    ws = workbook.active
    ws.title = 'IMPORTAR'

    fill = PatternFill('solid', fgColor='1E5F34')
    font = Font(color='FFFFFF', bold=True)
    for idx, header in enumerate(schema['headers'], start=1):
        cell = ws.cell(row=1, column=idx, value=header)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(idx)].width = max(16, len(header) + 5)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(schema['headers']))}1"

    instrucoes = workbook.create_sheet('INSTRUCOES')
    instrucoes['A1'] = f"MODELO DE IMPORTAÇÃO - {schema['titulo'].upper()}"
    instrucoes['A1'].font = Font(bold=True, size=14, color='1E5F34')
    instrucoes['A3'] = '1. Preencha somente a aba IMPORTAR.'
    instrucoes['A4'] = '2. Não renomeie, remova, acrescente ou mude a ordem das colunas.'
    instrucoes['A5'] = '3. Salve em XLSX e importe na mesma aba de Configurações.'
    instrucoes.column_dimensions['A'].width = 100

    if tipo == 'produto':
        bases = workbook.create_sheet('BASES')
        listas = [
            ('Cultivares', list(Cultivar.objects.order_by('nome').values_list('nome', flat=True))),
            ('Peneiras', list(Peneira.objects.order_by('nome').values_list('nome', flat=True))),
            ('Espécies', list(Especie.objects.order_by('nome').values_list('nome', flat=True))),
            ('Categorias', list(Categoria.objects.order_by('nome').values_list('nome', flat=True))),
            ('Tratamentos', list(Tratamento.objects.order_by('nome').values_list('nome', flat=True))),
        ]
        for col_idx, (titulo, valores) in enumerate(listas, start=1):
            c = bases.cell(row=1, column=col_idx, value=titulo)
            c.fill = fill
            c.font = font
            bases.column_dimensions[get_column_letter(col_idx)].width = 28
            for row_idx, valor in enumerate(valores, start=2):
                bases.cell(row=row_idx, column=col_idx, value=valor)

        _adicionar_validacao_lista(ws, 'B', listas[0][1], 'A')
        _adicionar_validacao_lista(ws, 'D', listas[1][1], 'B')
        _adicionar_validacao_lista(ws, 'E', listas[2][1], 'C')
        _adicionar_validacao_lista(ws, 'F', listas[3][1], 'D')
        _adicionar_validacao_lista(ws, 'G', listas[4][1], 'E')
        ativo = DataValidation(type='list', formula1='"SIM,NAO"', allow_blank=True)
        ws.add_data_validation(ativo)
        ativo.add('J2:J1000')
        instrucoes['A7'] = 'Produtos: Código e Cultivar são obrigatórios. Peneira, Espécie, Categoria, Tratamento, Descrição, Empresa e Tipo são opcionais.'
        instrucoes['A8'] = 'Quando Peneira, Espécie, Categoria ou Tratamento forem preenchidos, use exatamente um valor existente na aba BASES.'
        instrucoes['A9'] = 'Ativo é opcional; se ficar vazio, o produto será importado como ativo.'

    elif tipo == 'endereco':
        bases = workbook.create_sheet('BASES')
        armazens = list(Armazem.objects.order_by('nome').values_list('nome', flat=True))
        bases['A1'] = 'Armazéns'
        bases['A1'].fill = fill
        bases['A1'].font = font
        bases.column_dimensions['A'].width = 30
        for row_idx, valor in enumerate(armazens, start=2):
            bases.cell(row=row_idx, column=1, value=valor)
        _adicionar_validacao_lista(ws, 'B', armazens, 'A')
        instrucoes['A7'] = 'Endereços: o Armazém precisa existir previamente e deve ser escolhido na aba BASES.'

    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="modelo_{tipo}.xlsx"'
    return response


def _normalizar_codigo_produto(valor):
    """Normaliza código sem alterar zeros à esquerda."""
    return normalizar_texto_cadastro(valor)


def _sincronizar_solicitacoes_carga_produto(produto):
    """
    Vincula pedidos de carga antigos ao Produto quando o código foi
    cadastrado depois da solicitação. A configuração complementa apenas
    a descrição; lote/categoria/peneira/AZ/endereço continuam vindo do
    estoque escolhido no empenho.
    """
    if not produto or not produto.codigo:
        return 0

    codigo = _normalizar_codigo_produto(produto.codigo)
    descricao = (produto.descricao or '').strip()

    return (
        SolicitacaoItemCarga.objects
        .filter(codigo__iexact=codigo)
        .update(
            produto=produto,
            descricao=descricao,
        )
    )


def _sincronizar_item_carga_com_produto(item):
    """Sincronização defensiva ao abrir um pedido antigo para empenho."""
    if not item or not item.codigo:
        return item

    codigo = _normalizar_codigo_produto(item.codigo)
    produto = (
        Produto.objects
        .filter(codigo__iexact=codigo)
        .first()
    )

    if not produto:
        return item

    descricao = (produto.descricao or '').strip()
    campos = []

    if item.produto_id != produto.id:
        item.produto = produto
        campos.append('produto')

    if (item.descricao or '') != descricao:
        item.descricao = descricao
        campos.append('descricao')

    if campos:
        campos.append('atualizado_em')
        item.save(update_fields=campos)

    return item


def _importar_configuracoes_planilha(tipo, arquivo):
    tipo, _ = _schema_importacao_config(tipo)
    _validar_bases_importacao(tipo)
    linhas = _linhas_arquivo_base_config(tipo, arquivo)

    simples = {
        'cultivar': Cultivar,
        'peneira': Peneira,
        'especie': Especie,
        'categoria': Categoria,
        'tratamento': Tratamento,
        'armazem': Armazem,
        'origem': OrigemDestino,
    }
    criados = 0
    atualizados = 0
    erros = []

    with transaction.atomic():
        for linha_num, linha in linhas:
            try:
                if tipo in simples:
                    nome_item = normalizar_texto_cadastro(_valor_linha_planilha(linha, 'nome'))
                    if not nome_item:
                        raise ValueError('NOME é obrigatório.')
                    _, created = simples[tipo].objects.get_or_create(
                        nome__iexact=nome_item,
                        defaults={'nome': nome_item},
                    )
                    criados += int(created)
                    atualizados += int(not created)

                elif tipo == 'endereco':
                    codigo = normalizar_texto_cadastro(_valor_linha_planilha(linha, 'codigo'))
                    armazem_nome = normalizar_texto_cadastro(_valor_linha_planilha(linha, 'armazem'))
                    if not codigo:
                        raise ValueError('CÓDIGO é obrigatório.')
                    armazem = _resolver_fk_planilha(Armazem, armazem_nome, 'Armazém', obrigatorio=True)
                    endereco_obj = Endereco.objects.filter(codigo__iexact=codigo).first()
                    created = endereco_obj is None
                    if created:
                        endereco_obj = Endereco(codigo=codigo, armazem=armazem)
                    else:
                        endereco_obj.codigo = codigo
                        endereco_obj.armazem = armazem
                    endereco_obj.save()
                    criados += int(created)
                    atualizados += int(not created)

                elif tipo == 'produto':
                    codigo = _valor_linha_planilha(linha, 'codigo')
                    if not codigo:
                        raise ValueError('CÓDIGO é obrigatório.')
                    # Mesma obrigatoriedade do cadastro manual:
                    # Cultivar é obrigatório; os demais relacionamentos são opcionais.
                    # Se um opcional vier preenchido, ele precisa existir na base.
                    cultivar = _resolver_fk_planilha(
                        Cultivar,
                        _valor_linha_planilha(linha, 'cultivar'),
                        'Cultivar',
                        obrigatorio=True,
                    )
                    peneira = _resolver_fk_planilha(
                        Peneira,
                        _valor_linha_planilha(linha, 'peneira'),
                        'Peneira',
                        obrigatorio=False,
                    )
                    especie = _resolver_fk_planilha(
                        Especie,
                        _valor_linha_planilha(linha, 'especie'),
                        'Espécie',
                        obrigatorio=False,
                    )
                    categoria = _resolver_fk_planilha(
                        Categoria,
                        _valor_linha_planilha(linha, 'categoria'),
                        'Categoria',
                        obrigatorio=False,
                    )
                    tratamento = _resolver_fk_planilha(
                        Tratamento,
                        _valor_linha_planilha(linha, 'tratamento'),
                        'Tratamento',
                        obrigatorio=False,
                    )
                    ativo_txt = _valor_linha_planilha(linha, 'ativo')
                    ativo = str(ativo_txt or 'SIM').strip().lower() not in {'0', 'nao', 'não', 'false', 'inativo'}

                    codigo_norm = _normalizar_codigo_produto(codigo)
                    produto = Produto.objects.filter(codigo__iexact=codigo_norm).first()
                    created = produto is None
                    if created:
                        produto = Produto(codigo=codigo_norm)
                    produto.cultivar = cultivar
                    produto.descricao = _valor_linha_planilha(linha, 'descricao')
                    produto.tipo = _valor_linha_planilha(linha, 'tipo')
                    produto.empresa = _valor_linha_planilha(linha, 'empresa')
                    produto.peneira = peneira
                    produto.especie = especie
                    produto.categoria = categoria
                    produto.tratamento = tratamento
                    produto.ativo = ativo
                    produto.save()
                    _sincronizar_solicitacoes_carga_produto(produto)
                    criados += int(created)
                    atualizados += int(not created)
            except Exception as exc:
                erros.append(f'Linha {linha_num}: {exc}')

    return criados, atualizados, erros


def _dependencias_configuracao(tipo, item):
    """Retorna um resumo legível do que impede a exclusão de um cadastro."""
    deps = []
    checks = []
    if tipo == 'cultivar':
        checks = [('Produtos', Produto.objects.filter(cultivar=item)), ('Lotes de estoque', Estoque.objects.filter(cultivar=item))]
    elif tipo == 'peneira':
        checks = [('Produtos', Produto.objects.filter(peneira=item)), ('Lotes de estoque', Estoque.objects.filter(peneira=item))]
    elif tipo == 'especie':
        checks = [('Produtos', Produto.objects.filter(especie=item)), ('Lotes de estoque', Estoque.objects.filter(especie=item))]
    elif tipo == 'categoria':
        checks = [('Produtos', Produto.objects.filter(categoria=item)), ('Lotes de estoque', Estoque.objects.filter(categoria=item))]
    elif tipo == 'tratamento':
        checks = [('Produtos', Produto.objects.filter(tratamento=item)), ('Lotes de estoque', Estoque.objects.filter(tratamento=item))]
    elif tipo == 'armazem':
        checks = [('Endereços', item.enderecos.all()), ('Solicitações', Solicitacao.objects.filter(armazem=item))]
    elif tipo == 'endereco':
        checks = [('Lotes de estoque', Estoque.objects.filter(endereco__iexact=item.codigo))]
    elif tipo == 'produto':
        checks = [
            ('Itens de carga', SolicitacaoItemCarga.objects.filter(Q(produto=item) | Q(codigo__iexact=item.codigo))),
            ('Lotes de estoque', Estoque.objects.filter(produto__iexact=item.codigo)),
        ]
    elif tipo == 'origem':
        checks = [('Lotes de estoque', Estoque.objects.filter(origem_destino__iexact=item.nome))]

    for rotulo, qs in checks:
        qtd = qs.count()
        if qtd:
            amostras = [str(x) for x in qs[:3]]
            deps.append(f'{rotulo}: {qtd}' + (f' ({"; ".join(amostras)})' if amostras else ''))
    return deps


def _editar_item_configuracao(tipo, item_id, post):
    simples = {
        'cultivar': Cultivar, 'peneira': Peneira, 'especie': Especie,
        'categoria': Categoria, 'tratamento': Tratamento, 'origem': OrigemDestino,
        'armazem': Armazem,
    }
    if tipo in simples:
        obj = get_object_or_404(simples[tipo], id=item_id)
        nome = normalizar_texto_cadastro(post.get('nome', ''))
        if not nome:
            raise ValueError('Informe o nome.')
        if simples[tipo].objects.filter(nome__iexact=nome).exclude(id=obj.id).exists():
            raise ValueError(f'Já existe um cadastro com o nome {nome}.')
        obj.nome = nome
        obj.save()
        return str(obj)

    if tipo == 'endereco':
        obj = get_object_or_404(Endereco, id=item_id)
        codigo = normalizar_texto_cadastro(post.get('codigo', ''))
        armazem_id = post.get('armazem_id')
        if not codigo or not armazem_id:
            raise ValueError('Endereço e Armazém são obrigatórios.')
        if Endereco.objects.filter(codigo__iexact=codigo).exclude(id=obj.id).exists():
            raise ValueError(f'Já existe o endereço {codigo}.')
        obj.codigo = codigo
        obj.armazem = get_object_or_404(Armazem, id=armazem_id)
        obj.save()
        return str(obj)

    if tipo == 'produto':
        obj = get_object_or_404(Produto, id=item_id)
        codigo = _normalizar_codigo_produto(post.get('codigo', ''))
        cultivar_id = post.get('cultivar')
        if not codigo or not cultivar_id:
            raise ValueError('Código e Cultivar são obrigatórios.')
        if Produto.objects.filter(codigo__iexact=codigo).exclude(id=obj.id).exists():
            raise ValueError(f'Já existe o produto {codigo}.')
        obj.codigo = codigo
        obj.cultivar_id = cultivar_id
        obj.descricao = normalizar_texto_cadastro(post.get('descricao', ''))
        obj.tipo = normalizar_texto_cadastro(post.get('tipo', ''))
        obj.empresa = normalizar_texto_cadastro(post.get('empresa', ''))
        obj.peneira_id = post.get('peneira') or None
        obj.especie_id = post.get('especie') or None
        obj.categoria_id = post.get('categoria') or None
        obj.tratamento_id = post.get('tratamento') or None
        obj.ativo = post.get('ativo') == 'on'
        obj.save()
        _sincronizar_solicitacoes_carga_produto(obj)
        return str(obj)
    raise ValueError('Tipo de cadastro inválido.')

@login_required
@permission_required('sapp.pode_configuracoes', raise_exception=True)
def configuracoes(request):
    """
    View completa de configurações do sistema
    Gerencia: Produtos, Armazéns, Endereços, Usuários, Permissões
    """
    
    config = Configuracao.get_solo()
    
    # =============================
    # QUERYSETS PRINCIPAIS
    # =============================
    
    # Usuários (todos exceto o próprio usuário logado)
    usuarios_conferentes = User.objects.filter(
        is_superuser=False,
        is_active=True,
    ).exclude(id=request.user.id).order_by('username')
    
    # Produtos com relacionamentos
    produtos = Produto.objects.select_related(
        'cultivar', 'peneira', 'especie', 'categoria', 'tratamento'
    ).all().order_by('-data_cadastro')
    
    # Parâmetros
    cultivares = Cultivar.objects.all().order_by('nome')
    peneiras = Peneira.objects.all().order_by('nome')
    especies = Especie.objects.all().order_by('nome')
    categorias = Categoria.objects.all().order_by('nome')
    tratamentos = Tratamento.objects.all().order_by('nome')
    
    # Armazéns
    armazens_lista = Armazem.objects.all().order_by('nome')
    
    # Endereços com armazém
    enderecos_lista = Endereco.objects.select_related('armazem').all().order_by('codigo')
    
    # Origens/Destinos
    origens_lista = OrigemDestino.objects.all().order_by('nome')
    
    # =============================
    # PROCESSAMENTO POST
    # =============================
    
    if request.method == 'POST':
        
        acao = request.POST.get('acao')
        active_tab = request.POST.get('active_tab', 'cultivar')
        
        # ====================================
        # IMPORTAÇÃO EM MASSA
        # ====================================
        if acao == 'importar_planilha_config':
            try:
                tipo_importacao = request.POST.get('tipo_importacao', '')
                criados, atualizados, erros = _importar_configuracoes_planilha(
                    tipo_importacao,
                    request.FILES.get('arquivo_planilha'),
                )
                if criados or atualizados:
                    messages.success(
                        request,
                        f'✅ Importação concluída: {criados} criado(s) e {atualizados} já existente(s)/atualizado(s).'
                    )
                if erros:
                    resumo_erros = ' | '.join(erros[:8])
                    if len(erros) > 8:
                        resumo_erros += f' | +{len(erros)-8} erro(s)'
                    messages.warning(request, f'⚠️ Algumas linhas não foram importadas: {resumo_erros}')
            except Exception as e:
                messages.error(request, f'❌ Erro na importação: {e}')

        # ====================================
        # 1. PRODUTOS
        # ====================================
        elif acao == 'add_produto':
            try:
                if not cultivares.exists():
                    raise ValueError('Cadastre primeiro pelo menos um Cultivar.')
                cultivar_id = request.POST.get('cultivar')
                codigo = _normalizar_codigo_produto(request.POST.get('codigo', ''))
                descricao = normalizar_texto_cadastro(request.POST.get('descricao', ''))
                
                if not cultivar_id or not codigo:
                    messages.error(request, "❌ Cultivar e Código são obrigatórios!")
                elif Produto.objects.filter(codigo__iexact=codigo).exists():
                    messages.error(request, f"❌ Código '{codigo}' já existe!")
                else:
                    with transaction.atomic():
                        produto = Produto.objects.create(
                            cultivar_id=cultivar_id,
                            codigo=codigo,
                            descricao=descricao,
                            tipo=normalizar_texto_cadastro(request.POST.get('tipo', '')),
                            empresa=normalizar_texto_cadastro(request.POST.get('empresa', '')),
                            ativo=request.POST.get('ativo') == 'on'
                        )
                        produto.peneira_id = request.POST.get('peneira') or None
                        produto.especie_id = request.POST.get('especie') or None
                        produto.categoria_id = request.POST.get('categoria') or None
                        produto.tratamento_id = request.POST.get('tratamento') or None
                        produto.save()
                        _sincronizar_solicitacoes_carga_produto(produto)
                        messages.success(request, f"✅ Produto '{codigo}' cadastrado com sucesso!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao cadastrar produto: {str(e)}")
        
        elif acao == 'delete_produto':
            try:
                item_id = request.POST.get('id_item')
                if not item_id:
                    messages.error(request, "❌ Produto não identificado!")
                else:
                    produto = Produto.objects.get(id=item_id)
                    codigo = produto.codigo
                    deps = _dependencias_configuracao('produto', produto)
                    if deps:
                        messages.error(request, f"❌ Não é possível excluir Produto '{codigo}'. Vinculado a: " + ' | '.join(deps))
                    else:
                        produto.delete()
                        messages.success(request, f"✅ Produto '{codigo}' excluído com sucesso!")
            except Produto.DoesNotExist:
                messages.error(request, "❌ Produto não encontrado!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao excluir produto: {str(e)}")
        
        # ====================================
        # 2. USUÁRIOS E PERMISSÕES (APENAS INDIVIDUAIS - SEM GRUPOS)
        # ====================================
        
        elif acao == 'create_conferente_user':
            # Verifica permissão para criar usuários
            if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
                messages.error(request, "❌ Você não tem permissão para criar usuários!")
            else:
                username = request.POST.get('username', '').strip()
                first_name = request.POST.get('first_name', '').strip()
                password = request.POST.get('password', '').strip()
                
                # Validações
                if not username or not first_name:
                    messages.error(request, "❌ Nome de usuário e nome completo são obrigatórios!")
                elif User.objects.filter(username__iexact=username).exists():
                    messages.error(request, f"❌ Usuário '{username}' já existe!")
                else:
                    try:
                        with transaction.atomic():
                            # Define senha padrão se não for fornecida
                            if not password:
                                password = 'conceito123'
                            elif len(password) < 6:
                                messages.error(request, "❌ A senha deve ter no mínimo 6 caracteres!")
                                return redirect(f"{reverse('sapp:configuracoes')}#{active_tab}")
                            
                            # Cria o usuário (SEM grupos)
                            user = User.objects.create_user(
                                username=username,
                                first_name=first_name,
                                password=password
                            )
                            
                            # NÃO ADICIONA GRUPOS - apenas permissões individuais
                            
                            # 🔥 Adiciona permissões específicas selecionadas nos checkboxes
                            permissions_added = []
                            for key, value in request.POST.items():
                                if key.startswith('pode_') and value == 'on':
                                    try:
                                        # Buscar permissão no app sapp
                                        permission = Permission.objects.filter(
                                            codename=key,
                                            content_type__app_label='sapp'
                                        ).first()
                                        
                                        # Se não encontrar, buscar no almoxarifado
                                        if not permission:
                                            permission = Permission.objects.filter(
                                                codename=key,
                                                content_type__app_label='almoxarifado'
                                            ).first()
                                        
                                        if permission:
                                            user.user_permissions.add(permission)
                                            permissions_added.append(key)
                                    except Exception as e:
                                        print(f"Erro ao adicionar permissão {key}: {e}")
                            
                            messages.success(request, f"✅ Usuário '{first_name}' criado com sucesso! Senha: {password}")
                            if permissions_added:
                                messages.info(request, f"📋 Permissões adicionadas: {', '.join(permissions_added)}")
                    
                    except Exception as e:
                        messages.error(request, f"❌ Erro ao criar usuário: {str(e)}")
        
# sapp/views.py - Substitua a função update_user_permissions

        elif acao == 'update_user_permissions':
            # Verifica permissão para editar permissões
            if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
                messages.error(request, "❌ Você não tem permissão para editar permissões!")
            else:
                user_id = request.POST.get('user_id')
                
                print(f"\n🔍 [DEBUG] Recebida requisição update_user_permissions")
                print(f"   user_id: {user_id}")
                print(f"   POST keys: {list(request.POST.keys())}")
                
                try:
                    user = User.objects.get(id=user_id)
                    
                    if user == request.user and not request.user.is_superuser:
                        messages.error(request, "❌ Você não pode editar suas próprias permissões!")
                    else:
                        with transaction.atomic():
                            # 🔥 LIMPA TODAS as permissões atuais
                            user.user_permissions.clear()
                            print(f"   ✅ Permissões antigas removidas")
                            
                            # 🔥 Lista para guardar as permissões adicionadas
                            permissions_added = []
                            
                            # 🔥 Percorre todos os campos do POST
                            for key, value in request.POST.items():
                                # Ignora campos que não são permissões
                                if key in ['csrfmiddlewaretoken', 'acao', 'user_id', 'active_tab', 'group_name']:
                                    continue
                                
                                print(f"   Campo: {key} = {value}")
                                
                                # sapp/views.py - Substitua a parte de busca de permissão

                                if value == 'on':  # Checkbox marcado
                                    permission = None
                                    
                                    # 🔥 CORREÇÃO: Buscar em ORDEM CORRETA
                                    # Primeiro no app almoxarifado (para permissões de almoxarifado)
                                    if key in ['pode_ver_almoxarifado', 'pode_gerenciar_almoxarifado']:
                                        permission = Permission.objects.filter(
                                            codename=key,
                                            content_type__app_label='almoxarifado'
                                        ).first()
                                    
                                    # Depois no app sapp
                                    if not permission:
                                        permission = Permission.objects.filter(
                                            codename=key,
                                            content_type__app_label='sapp'
                                        ).first()
                                    
                                    if permission:
                                        user.user_permissions.add(permission)
                                        permissions_added.append(key)
                                        print(f"   ✅ Adicionada permissão: {key} (app: {permission.content_type.app_label})")
                                    else:
                                        print(f"   ❌ Permissão não encontrada: {key}")
                            
                            # 🔥 Salvar (garantir que foi salvo)
                            user.save()
                            
                            # 🔥 Verificar se salvou
                            saved_perms = list(user.user_permissions.values_list('codename', flat=True))
                            print(f"   📋 Permissões salvas no banco: {saved_perms}")
                            
                            if permissions_added:
                                messages.success(request, f"✅ Permissões de '{user.first_name}' atualizadas! ({len(permissions_added)} permissões)")
                            else:
                                messages.success(request, f"✅ Todas as permissões de '{user.first_name}' foram removidas!")
                            
                except User.DoesNotExist:
                    messages.error(request, "❌ Usuário não encontrado!")
                except Exception as e:
                    print(f"❌ Erro: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"❌ Erro ao atualizar permissões: {str(e)}")
        elif acao == 'edit_user_basic':
            if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
                messages.error(request, '❌ Você não tem permissão para editar usuários!')
            else:
                try:
                    user_id = request.POST.get('user_id')
                    usuario = User.objects.get(id=user_id, is_active=True)
                    username = str(request.POST.get('username', '') or '').strip()
                    first_name = str(request.POST.get('first_name', '') or '').strip()
                    if not username or not first_name:
                        raise ValueError('Login e nome são obrigatórios.')
                    if User.objects.filter(username__iexact=username).exclude(id=usuario.id).exists():
                        raise ValueError(f'O login {username} já está em uso.')
                    nova_senha = str(request.POST.get('password', '') or '').strip()
                    if nova_senha and len(nova_senha) < 6:
                        raise ValueError('A senha deve ter no mínimo 6 caracteres.')
                    usuario.username = username
                    usuario.first_name = first_name
                    campos_atualizados = ['username', 'first_name']
                    if nova_senha:
                        usuario.set_password(nova_senha)
                        campos_atualizados.append('password')
                    usuario.save(update_fields=campos_atualizados)
                    messages.success(request, f'✅ Usuário {first_name} atualizado com sucesso!')
                except User.DoesNotExist:
                    messages.error(request, '❌ Usuário não encontrado!')
                except Exception as exc:
                    messages.error(request, f'❌ Não foi possível editar o usuário: {exc}')

        elif acao == 'reset_password':
            # Verifica permissão para resetar senha
            if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
                messages.error(request, "❌ Você não tem permissão para resetar senhas!")
            else:
                user_id = request.POST.get('user_id')
                try:
                    user = User.objects.get(id=user_id)
                    
                    # Não permite resetar próprio usuário (exceto se for superusuário)
                    if user == request.user and not request.user.is_superuser:
                        messages.error(request, "❌ Você não pode resetar sua própria senha!")
                    else:
                        new_password = 'conceito123'
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, f"✅ Senha de '{user.first_name}' resetada para: {new_password}")
                
                except User.DoesNotExist:
                    messages.error(request, "❌ Usuário não encontrado!")
                except Exception as e:
                    messages.error(request, f"❌ Erro ao resetar senha: {str(e)}")
        
        elif acao == 'delete_user':
            # Verifica permissão para excluir usuário
            if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
                messages.error(request, "❌ Você não tem permissão para excluir usuários!")
            else:
                user_id = request.POST.get('user_id')
                try:
                    user = User.objects.get(id=user_id)
                    
                    # Não permite excluir próprio usuário
                    if user == request.user:
                        messages.error(request, "❌ Você não pode excluir sua própria conta!")
                    else:
                        username = user.username
                        if not user.first_name and not user.last_name:
                            user.first_name = username
                        sufixo = timezone.localtime(timezone.now()).strftime('%Y%m%d%H%M%S')
                        user.username = f'inativo_{user.id}_{sufixo}_{username}'[:150]
                        user.is_active = False
                        user.is_staff = False
                        user.is_superuser = False
                        user.email = ''
                        user.set_unusable_password()
                        user.save()
                        user.groups.clear()
                        user.user_permissions.clear()
                        messages.success(
                            request,
                            f"✅ Usuário '{username}' desativado. Todos os dados e históricos vinculados foram preservados."
                        )
                
                except User.DoesNotExist:
                    messages.error(request, "❌ Usuário não encontrado!")
                except Exception as e:
                    messages.error(request, f"❌ Erro ao excluir usuário: {str(e)}")
        
        # ====================================
        # 3. ARMAZÉNS
        # ====================================
        
        elif acao == 'add_armazem':
            nome = normalizar_texto_cadastro(request.POST.get('nome', ''))
            if nome:
                obj = Armazem.objects.filter(nome__iexact=nome).first()
                created = False
                if not obj:
                    obj = Armazem.objects.create(nome=nome)
                    created = True
                if created:
                    messages.success(request, f"✅ Armazém '{nome}' criado com sucesso!")
                else:
                    messages.warning(request, f"⚠️ Armazém '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome do armazém não informado!")
        
        # ====================================
        # 4. ENDEREÇOS
        # ====================================
        
        elif acao == 'add_endereco':
            endereco_codigo = normalizar_texto_cadastro(request.POST.get('endereco_codigo', ''))
            armazem_id = request.POST.get('armazem_id')
            
            if not endereco_codigo:
                messages.error(request, "❌ Endereço não informado!")
            elif not armazem_id:
                messages.error(request, "❌ Selecione um armazém!")
            else:
                try:
                    armazem = Armazem.objects.get(id=armazem_id)
                    
                    if Endereco.objects.filter(codigo__iexact=endereco_codigo).exists():
                        messages.warning(request, f"⚠️ Endereço '{endereco_codigo}' já cadastrado!")
                    else:
                        Endereco.objects.create(
                            codigo=endereco_codigo,
                            armazem=armazem
                        )
                        messages.success(request, f"✅ Endereço '{endereco_codigo}' cadastrado no armazém '{armazem.nome}'!")
                        
                except Armazem.DoesNotExist:
                    messages.error(request, "❌ Armazém não encontrado!")
                except Exception as e:
                    messages.error(request, f"❌ Erro ao cadastrar endereço: {str(e)}")
        
        # ====================================
        # 5. CONFIGURAÇÃO GERAL
        # ====================================
        
        elif acao == 'config_geral':
            form = ConfiguracaoForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, "✅ Configurações gerais salvas com sucesso!")
            else:
                messages.error(request, "❌ Erro ao salvar configurações. Verifique os dados.")
        
        # ====================================
        # 6. CADASTROS SIMPLES (CRUD)
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
            nome_display = {
                'add_cultivar': 'Cultivar',
                'add_peneira': 'Peneira',
                'add_especie': 'Espécie',
                'add_categoria': 'Categoria',
                'add_tratamento': 'Tratamento',
                'add_origem': 'Origem/Destino'
            }
            
            if model:
                nome = normalizar_texto_cadastro(request.POST.get('nome', ''))
                if nome:
                    obj = model.objects.filter(nome__iexact=nome).first()
                    created = False
                    if not obj:
                        obj = model.objects.create(nome=nome)
                        created = True
                    if created:
                        messages.success(request, f"✅ {nome_display[acao]} '{nome}' adicionado com sucesso!")
                    else:
                        messages.warning(request, f"⚠️ {nome_display[acao]} '{nome}' já existe!")
                else:
                    messages.error(request, f"❌ Nome do {nome_display[acao]} não informado!")
        
        # ====================================
        # 7. EXCLUSÃO GENÉRICA
        # ====================================
        
        elif acao == 'edit_item':
            tipo = request.POST.get('tipo_item', '')
            item_id = request.POST.get('id_item')
            try:
                nome = _editar_item_configuracao(tipo, item_id, request.POST)
                messages.success(request, f'✅ Cadastro atualizado: {nome}')
            except Exception as exc:
                messages.error(request, f'❌ Não foi possível editar: {exc}')

        elif acao == 'delete_item':
            tipo = request.POST.get('tipo_item')
            item_id = request.POST.get('id_item')
            
            if not item_id:
                messages.error(request, "❌ Item não identificado!")
            else:
                model_map = {
                    'cultivar': (Cultivar, 'Cultivar'),
                    'especie': (Especie, 'Espécie'),
                    'peneira': (Peneira, 'Peneira'),
                    'categoria': (Categoria, 'Categoria'),
                    'tratamento': (Tratamento, 'Tratamento'),
                    'armazem': (Armazem, 'Armazém'),
                    'endereco': (Endereco, 'Endereço'),
                    'origem': (OrigemDestino, 'Origem/Destino'),
                    'produto': (Produto, 'Produto'),
                }
                
                if tipo in model_map:
                    model, nome_tipo = model_map[tipo]
                    try:
                        item = model.objects.get(id=item_id)
                        nome_excluido = str(item)
                        dependencias = _dependencias_configuracao(tipo, item)
                        if dependencias:
                            messages.error(
                                request,
                                f"❌ Não é possível excluir {nome_tipo} '{nome_excluido}'. Vinculado a: "
                                + ' | '.join(dependencias)
                            )
                            return redirect(f"{reverse('sapp:configuracoes')}#{active_tab}")
                        
                        # Validações de integridade referencial
                        if tipo == 'endereco' and hasattr(item, 'estoque_set') and item.estoque_set.exists():
                            messages.error(request, f"❌ Endereço '{nome_excluido}' está sendo usado em lotes de estoque!")
                        elif tipo == 'armazem' and hasattr(item, 'enderecos') and item.enderecos.exists():
                            messages.error(request, f"❌ Armazém '{nome_excluido}' possui endereços vinculados!")
                        elif tipo == 'cultivar' and Produto.objects.filter(cultivar=item).exists():
                            messages.error(request, f"❌ Cultivar '{nome_excluido}' está sendo usado em produtos!")
                        elif tipo == 'especie' and Produto.objects.filter(especie=item).exists():
                            messages.error(request, f"❌ Espécie '{nome_excluido}' está sendo usada em produtos!")
                        elif tipo == 'peneira' and Produto.objects.filter(peneira=item).exists():
                            messages.error(request, f"❌ Peneira '{nome_excluido}' está sendo usada em produtos!")
                        elif tipo == 'categoria' and Produto.objects.filter(categoria=item).exists():
                            messages.error(request, f"❌ Categoria '{nome_excluido}' está sendo usada em produtos!")
                        elif tipo == 'tratamento' and Produto.objects.filter(tratamento=item).exists():
                            messages.error(request, f"❌ Tratamento '{nome_excluido}' está sendo usado em produtos!")
                        else:
                            item.delete()
                            messages.success(request, f"✅ {nome_tipo} '{nome_excluido}' removido com sucesso!")
                            
                    except model.DoesNotExist:
                        messages.error(request, f"❌ {nome_tipo} não encontrado!")
                    except Exception as e:
                        messages.error(request, f"❌ Erro ao remover {nome_tipo.lower()}: {str(e)}")
                else:
                    messages.error(request, "❌ Tipo de item inválido!")
        
        # Redireciona para a mesma aba
        return redirect(f"{reverse('sapp:configuracoes')}#{active_tab}")
    
    # =============================
    # CONTEXT PARA RENDERIZAÇÃO
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
        'cadastro_produto_liberado': cultivares.exists(),
        # Para importação em massa, segue a obrigatoriedade real dos campos:
        # Produto exige Código + Cultivar. As demais bases são opcionais e
        # somente precisam existir quando o respectivo valor for informado.
        'importacao_produto_liberada': cultivares.exists(),
        'cadastro_endereco_liberado': armazens_lista.exists(),
        
        'armazens': armazens_lista,
        'enderecos': enderecos_lista,
        'origens': origens_lista,
    }
    
    return render(request, 'sapp/configuracoes.html', context)



@login_required
@permission_required('sapp.pode_gerenciar_usuarios', raise_exception=True)
def api_user_permissions(request, user_id):
    """
    API para buscar as permissões atuais de um usuário
    """
    if not request.user.is_superuser and not request.user.has_perm('sapp.pode_gerenciar_usuarios'):
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        
        # 🔥 Retornar o nome completo da permissão (com app)
        permissions = []
        for perm in user.user_permissions.all():
            permissions.append(perm.codename)
        
        return JsonResponse({
            'success': True,
            'permissions': permissions,
            'username': user.username,
            'first_name': user.first_name,
            'is_superuser': user.is_superuser,
            'groups': []
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuário não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Min
from django.contrib.auth.decorators import login_required, permission_required
from sapp.models import HistoricoItemEmpenho

from collections import defaultdict

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from sapp.models import HistoricoItemEmpenho


def campo_existe(model, caminho):
    """
    Verifica se um caminho de campo existe no model.

    Exemplos:
        cliente__nome
        empenho__cliente__nome
        processado_por__username
    """
    model_atual = model

    try:
        partes = caminho.split('__')

        for indice, parte in enumerate(partes):
            campo = model_atual._meta.get_field(parte)

            if indice < len(partes) - 1:
                if not campo.is_relation or not campo.related_model:
                    return False

                model_atual = campo.related_model

        return True

    except Exception:
        return False


def encontrar_campo_cliente():
    """
    Procura automaticamente onde está armazenado o nome do cliente.

    Adicione outros caminhos nesta lista caso seu model use outro nome.
    """
    campos_possiveis = [
        'cliente_nome',
        'nome_cliente',
        'cliente__nome',
        'cliente__razao_social',
        'cliente__nome_fantasia',

        'empenho__cliente_nome',
        'empenho__nome_cliente',
        'empenho__cliente__nome',
        'empenho__cliente__razao_social',
        'empenho__cliente__nome_fantasia',

        'estoque_origem__cliente__nome',
        'estoque_destino__cliente__nome',
    ]

    for caminho in campos_possiveis:
        if campo_existe(HistoricoItemEmpenho, caminho):
            return caminho

    return None


def obter_valor_atributo(objeto, caminho):
    """
    Obtém um valor usando caminhos como:
        empenho.cliente.nome
        cliente.razao_social
    """
    if objeto is None or not caminho:
        return ''

    valor = objeto

    for parte in caminho.split('__'):
        if valor is None:
            return ''

        valor = getattr(valor, parte, None)

        if callable(valor):
            try:
                valor = valor()
            except Exception:
                return ''

    if valor is None:
        return ''

    return str(valor).strip()


def obter_nome_cliente(movimentacao, campo_cliente=None):
    """
    Retorna o nome do cliente da movimentação.
    """
    if campo_cliente:
        nome = obter_valor_atributo(movimentacao, campo_cliente)

        if nome:
            return nome

    # Fallback para propriedades ou atributos que não sejam campos do banco.
    caminhos_fallback = [
        'cliente_nome',
        'nome_cliente',
        'cliente__nome',
        'cliente__razao_social',
        'cliente__nome_fantasia',

        'empenho__cliente_nome',
        'empenho__nome_cliente',
        'empenho__cliente__nome',
        'empenho__cliente__razao_social',
        'empenho__cliente__nome_fantasia',
    ]

    for caminho in caminhos_fallback:
        nome = obter_valor_atributo(movimentacao, caminho)

        if nome:
            return nome

    return ''


def obter_nome_usuario(usuario):
    """
    Retorna o nome completo do usuário ou o username.
    """
    if not usuario:
        return ''

    nome_completo = usuario.get_full_name().strip()

    if nome_completo:
        return nome_completo

    return usuario.username or ''


from collections import defaultdict
from types import SimpleNamespace

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import HistoricoMovimentacao, HistoricoItemEmpenho


def nome_usuario_historico(usuario):
    """Nome completo do usuário ou username; 'Sistema' se nulo."""
    if not usuario:
        return 'Sistema'
    nome = usuario.get_full_name().strip()
    return nome or usuario.username or 'Sistema'


def normalizar_tipo_historico(tipo):
    """
    Retorna o tipo normalizado (sem acentos, sem espaços extras, minúsculo).
    Mapeia variações comuns para uma chave única.
    """
    tipo_original = str(tipo or '').strip()
    tipo_lower = tipo_original.lower()

    mapa = {
        'entrada': 'entrada',
        'nova entrada': 'entrada',
        'saida': 'saida',
        'saída': 'saida',
        'baixa': 'saida',
        'transferencia': 'transferencia',
        'transferência': 'transferencia',
        'expedicao': 'expedicao',
        'expedição': 'expedicao',
        'edicao': 'edicao',
        'edição': 'edicao',
        'exclusao': 'exclusao',
        'exclusão': 'exclusao',
    }
    return mapa.get(tipo_lower, tipo_lower.replace(' ', '_'))


def nome_tipo_historico(tipo):
    """Nome amigável para exibição."""
    nomes = {
        'entrada': 'Entrada',
        'saida': 'Saída',
        'transferencia': 'Transferência',
        'expedicao': 'Expedição',
        'edicao': 'Edição',
        'exclusao': 'Exclusão',
    }
    return nomes.get(tipo, str(tipo or 'Não informado').replace('_', ' ').title())


def obter_enderecos_historico_antigo(movimentacao, tipo):
    """
    No histórico antigo não há endereços separados.
    Utiliza o endereço do estoque quando disponível.
    """
    endereco = movimentacao.estoque.endereco if movimentacao.estoque else ''

    if tipo == 'entrada':
        return '', endereco
    if tipo in ('saida', 'expedicao'):
        return endereco, ''
    if tipo == 'transferencia':
        return endereco, ''  # origem; destino normalmente na descrição
    return endereco, ''


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
def historico_geral(request):
    # ----------------------------------------------------------
    # 1. Captura dos parâmetros de filtro
    # ----------------------------------------------------------
    busca = request.GET.get('busca', '').strip()
    filtro_lote = request.GET.get('lote', '').strip()
    filtro_produto = request.GET.get('produto', '').strip()
    filtro_cliente = request.GET.get('cliente', '').strip()
    filtro_tipo = request.GET.get('tipo', '').strip()
    filtro_usuario = request.GET.get('usuario', '').strip()
    data_inicial_txt = request.GET.get('data_inicial', '').strip()
    data_final_txt = request.GET.get('data_final', '').strip()

    data_inicial = parse_date(data_inicial_txt)
    data_final = parse_date(data_final_txt)

    # ----------------------------------------------------------
    # 2. Querysets base
    # ----------------------------------------------------------
    qs_antigo = HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).all()

    qs_novo = HistoricoItemEmpenho.objects.select_related(
        'estoque_origem', 'estoque_destino', 'processado_por', 'empenho'
    ).all()

    # ----------------------------------------------------------
    # 3. Busca textual (múltiplos termos → AND)
    # ----------------------------------------------------------
    if busca:
        termos = [t for t in busca.split() if t]
        for termo in termos:
            qs_antigo = qs_antigo.filter(
                Q(lote_ref__icontains=termo) |
                Q(estoque__lote__icontains=termo) |
                Q(estoque__produto__icontains=termo) |
                Q(estoque__cultivar__nome__icontains=termo) |
                Q(estoque__cliente__icontains=termo) |
                Q(estoque__empresa__icontains=termo) |
                Q(cliente__icontains=termo) |
                Q(tipo__icontains=termo) |
                Q(descricao__icontains=termo) |
                Q(numero_carga__icontains=termo) |
                Q(motorista__icontains=termo) |
                Q(placa__icontains=termo) |
                Q(ordem_entrega__icontains=termo) |
                Q(usuario__username__icontains=termo) |
                Q(usuario__first_name__icontains=termo) |
                Q(usuario__last_name__icontains=termo)
            )
            qs_novo = qs_novo.filter(
                Q(lote__icontains=termo) |
                Q(produto__icontains=termo) |
                Q(cultivar__icontains=termo) |
                Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo) |
                Q(tipo__icontains=termo) |
                Q(observacao__icontains=termo) |
                Q(numero_carga__icontains=termo) |
                Q(placa__icontains=termo) |
                Q(endereco_origem__icontains=termo) |
                Q(endereco_destino__icontains=termo) |
                Q(processado_por__username__icontains=termo) |
                Q(processado_por__first_name__icontains=termo) |
                Q(processado_por__last_name__icontains=termo)
            )

    # ----------------------------------------------------------
    # 4. Filtros exatos
    # ----------------------------------------------------------
    if filtro_lote:
        qs_antigo = qs_antigo.filter(
            Q(lote_ref=filtro_lote) | Q(estoque__lote=filtro_lote)
        )
        qs_novo = qs_novo.filter(lote=filtro_lote)

    if filtro_produto:
        qs_antigo = qs_antigo.filter(estoque__produto=filtro_produto)
        qs_novo = qs_novo.filter(produto=filtro_produto)

    if filtro_cliente:
        qs_antigo = qs_antigo.filter(
            Q(cliente=filtro_cliente) | Q(estoque__cliente=filtro_cliente)
        )
        qs_novo = qs_novo.filter(cliente=filtro_cliente)

    if filtro_usuario:
        qs_antigo = qs_antigo.filter(usuario__username=filtro_usuario)
        qs_novo = qs_novo.filter(processado_por__username=filtro_usuario)

    # Filtro por tipo – agora 100% flexível: usamos icontains com a string normalizada,
    # o que casa com qualquer variação de maiúsculas/minúsculas e acentos.
    if filtro_tipo:
        tipo_normalizado = normalizar_tipo_historico(filtro_tipo)
        # Mapeamos as grafias mais comuns que podem estar no banco para o termo normalizado
        mapa_busca = {
            'entrada': ['entrada', 'nova entrada'],
            'saida': ['saida', 'saída', 'baixa'],
            'transferencia': ['transferencia', 'transferência'],
            'expedicao': ['expedicao', 'expedição'],
            'edicao': ['edicao', 'edição'],
            'exclusao': ['exclusao', 'exclusão'],
        }
        variantes = mapa_busca.get(tipo_normalizado, [filtro_tipo])
        tipo_q = Q()
        for v in variantes:
            tipo_q |= Q(tipo__icontains=v)  # icontains ignora case e acentos parcialmente
        qs_antigo = qs_antigo.filter(tipo_q)
        qs_novo = qs_novo.filter(tipo_q)

    # Datas
    if data_inicial:
        qs_antigo = qs_antigo.filter(data_hora__date__gte=data_inicial)
        qs_novo = qs_novo.filter(processado_em__date__gte=data_inicial)
    if data_final:
        qs_antigo = qs_antigo.filter(data_hora__date__lte=data_final)
        qs_novo = qs_novo.filter(processado_em__date__lte=data_final)

    # ----------------------------------------------------------
    # 5. Normalização dos registros (histórico antigo + novo)
    # ----------------------------------------------------------
    movimentacoes = []

    for m in qs_antigo.iterator(chunk_size=1000):
        estoque = m.estoque
        lote = m.lote_ref or (estoque.lote if estoque else '') or 'Sem lote'
        produto = estoque.produto if estoque else ''
        cliente = m.cliente or (estoque.cliente if estoque else '') or ''
        empresa = estoque.empresa if estoque else ''
        tipo = normalizar_tipo_historico(m.tipo)
        end_orig, end_dest = obter_enderecos_historico_antigo(m, tipo)

        movimentacoes.append(SimpleNamespace(
            chave=f'antigo-{m.pk}',
            origem_historico='Histórico geral',
            lote=lote,
            produto=produto,
            cliente_exibicao=cliente,
            empresa=empresa,
            cultivar=estoque.cultivar.nome if estoque and estoque.cultivar else '',
            peneira=estoque.peneira.nome if estoque and estoque.peneira else '',
            categoria=estoque.categoria.nome if estoque and estoque.categoria else '',
            tratamento=estoque.tratamento.nome if estoque and estoque.tratamento else '',
            especie=estoque.especie.nome if estoque and estoque.especie else '',
            embalagem=estoque.embalagem if estoque else '',
            quantidade=m.quantidade or 0,
            tipo=tipo,
            tipo_exibicao=nome_tipo_historico(tipo),
            endereco_origem=end_orig,
            endereco_destino=end_dest,
            usuario_exibicao=nome_usuario_historico(m.usuario),
            processado_em=m.data_hora,
            observacao=m.descricao or '',
            numero_carga=m.numero_carga or '',
            motorista=m.motorista or '',
            placa=m.placa or '',
            ordem_entrega=m.ordem_entrega or '',
        ))

    for m in qs_novo.iterator(chunk_size=1000):
        tipo = normalizar_tipo_historico(m.tipo)
        movimentacoes.append(SimpleNamespace(
            chave=f'novo-{m.pk}',
            origem_historico='Cards e empenhos',
            lote=m.lote or 'Sem lote',
            produto=m.produto or '',
            cliente_exibicao=m.cliente or '',
            empresa=m.empresa or '',
            cultivar=m.cultivar or '',
            peneira=m.peneira or '',
            categoria=m.categoria or '',
            tratamento=m.tratamento or '',
            especie=m.especie or '',
            embalagem=m.embalagem or '',
            quantidade=m.quantidade or 0,
            tipo=tipo,
            tipo_exibicao=nome_tipo_historico(tipo),
            endereco_origem=m.endereco_origem or '',
            endereco_destino=m.endereco_destino or '',
            usuario_exibicao=nome_usuario_historico(m.processado_por),
            processado_em=m.processado_em,
            observacao=m.observacao or '',
            numero_carga=m.numero_carga or '',
            motorista=m.empenho.motorista if m.empenho else '',
            placa=m.placa or '',
            ordem_entrega='',
        ))

    # ----------------------------------------------------------
    # 6. Ordenação e deduplicação leve
    # ----------------------------------------------------------
    data_minima = timezone.make_aware(timezone.datetime.min)
    movimentacoes.sort(key=lambda x: x.processado_em or data_minima, reverse=True)

    # Remove eventos duplicados (mesmo lote, tipo, qtd, data/minuto e carga)
    vistos = set()
    unicos = []
    for mov in movimentacoes:
        data_chave = mov.processado_em.strftime('%Y-%m-%d %H:%M') if mov.processado_em else ''
        chave = (
            str(mov.lote).strip().upper(),
            mov.tipo,
            int(mov.quantidade or 0),
            data_chave,
            str(mov.numero_carga or '').strip().upper(),
        )
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(mov)
    movimentacoes = unicos

    # ----------------------------------------------------------
    # 7. Agrupamento por lote
    # ----------------------------------------------------------
    por_lote = defaultdict(list)
    for mov in movimentacoes:
        por_lote[str(mov.lote or 'Sem lote').strip()].append(mov)

    lotes_agrupados = []
    for idx, (lote_ref, movs) in enumerate(por_lote.items(), start=1):
        movs.sort(key=lambda x: x.processado_em or data_minima, reverse=True)
        ultima = movs[0]
        quantidade_total = sum(int(m.quantidade or 0) for m in movs)

        # Clientes e produtos únicos (resumo)
        clientes_unicos = list(dict.fromkeys(m.cliente_exibicao for m in movs if m.cliente_exibicao))
        cliente_resumo = ', '.join(clientes_unicos[:3])
        if len(clientes_unicos) > 3:
            cliente_resumo += f' +{len(clientes_unicos)-3}'

        produtos_unicos = list(dict.fromkeys(m.produto for m in movs if m.produto))
        produto_resumo = ', '.join(produtos_unicos[:2])
        if len(produtos_unicos) > 2:
            produto_resumo += f' +{len(produtos_unicos)-2}'

        lotes_agrupados.append({
            'grupo_id': f'grupo-{idx}',
            'lote_ref': lote_ref,
            'produto': produto_resumo,
            'cliente': cliente_resumo,
            'total_mov': len(movs),
            'quantidade_total': quantidade_total,
            'ultima_data': ultima.processado_em,
            'ultimo_end_origem': ultima.endereco_origem,
            'ultimo_end_destino': ultima.endereco_destino,
            'ultimo_usuario': ultima.usuario_exibicao,
            'ultimo_tipo': ultima.tipo,
            'ultimo_tipo_exibicao': ultima.tipo_exibicao,
            'movimentacoes': movs,
        })

    lotes_agrupados.sort(key=lambda g: g['ultima_data'] or data_minima, reverse=True)

    # ----------------------------------------------------------
    # 8. Cards informativos
    # ----------------------------------------------------------
    hoje = timezone.localdate()
    total_mov = len(movimentacoes)
    total_lotes = len(lotes_agrupados)
    total_exp = sum(1 for m in movimentacoes if m.tipo == 'expedicao')
    mov_hoje = sum(
        1 for m in movimentacoes
        if m.processado_em and timezone.localtime(m.processado_em).date() == hoje
    )

    # ----------------------------------------------------------
    # 9. Opções para os selects (sempre completas, sem filtro)
    # ----------------------------------------------------------
    def _lista_distinta(qs, campo, modelo_rel=None):
        """Extrai valores distintos de um campo, aceitando relacionamento."""
        if modelo_rel:
            return set(
                qs.exclude(**{f'{modelo_rel}__isnull': True})
                .values_list(f'{modelo_rel}__{campo}', flat=True)
            )
        return set(qs.exclude(**{campo: ''}).values_list(campo, flat=True))

    lotes_ant = _lista_distinta(HistoricoMovimentacao.objects, 'lote_ref')
    lotes_ant_est = _lista_distinta(HistoricoMovimentacao.objects, 'lote', modelo_rel='estoque')
    lotes_nov = _lista_distinta(HistoricoItemEmpenho.objects, 'lote')
    opcoes_lotes = sorted({x.strip() for x in (lotes_ant | lotes_ant_est | lotes_nov) if x and x.strip()}, key=str.lower)

    prod_ant = _lista_distinta(HistoricoMovimentacao.objects, 'produto', modelo_rel='estoque')
    prod_nov = _lista_distinta(HistoricoItemEmpenho.objects, 'produto')
    opcoes_produtos = sorted({x.strip() for x in (prod_ant | prod_nov) if x and x.strip()}, key=str.lower)

    cli_ant = _lista_distinta(HistoricoMovimentacao.objects, 'cliente')
    cli_ant_est = _lista_distinta(HistoricoMovimentacao.objects, 'cliente', modelo_rel='estoque')
    cli_nov = _lista_distinta(HistoricoItemEmpenho.objects, 'cliente')
    opcoes_clientes = sorted({x.strip() for x in (cli_ant | cli_ant_est | cli_nov) if x and x.strip()}, key=str.lower)

    # Usuários (dicionário username -> nome)
    usuarios_dict = {}
    for u in HistoricoMovimentacao.objects.select_related('usuario').exclude(usuario__isnull=True).values('usuario__username', 'usuario__first_name', 'usuario__last_name').distinct():
        username = u['usuario__username']
        nome = f"{u['usuario__first_name']} {u['usuario__last_name']}".strip() or username
        usuarios_dict[username] = nome
    for u in HistoricoItemEmpenho.objects.select_related('processado_por').exclude(processado_por__isnull=True).values('processado_por__username', 'processado_por__first_name', 'processado_por__last_name').distinct():
        username = u['processado_por__username']
        nome = f"{u['processado_por__first_name']} {u['processado_por__last_name']}".strip() or username
        usuarios_dict[username] = nome
    opcoes_usuarios = [{'valor': k, 'nome': v} for k, v in sorted(usuarios_dict.items(), key=lambda item: item[1].lower())]

    choices_tipo = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('transferencia', 'Transferência'),
        ('expedicao', 'Expedição'),
        ('edicao', 'Edição'),
        ('exclusao', 'Exclusão'),
    ]

    # ----------------------------------------------------------
    # 10. Paginação dos lotes agrupados
    # ----------------------------------------------------------
    try:
        page_size = int(request.GET.get('page_size', 25))
    except (ValueError, TypeError):
        page_size = 25
    if page_size not in (10, 25, 50, 100, 200):
        page_size = 25

    paginator = Paginator(lotes_agrupados, page_size)
    page_number = request.GET.get('page', 1)
    try:
        pagina = paginator.page(page_number)
    except PageNotAnInteger:
        pagina = paginator.page(1)
    except EmptyPage:
        pagina = paginator.page(paginator.num_pages)

    # Ajusta IDs dos grupos por página
    for i, grupo in enumerate(pagina.object_list, start=1):
        grupo['grupo_id'] = f'grupo-{pagina.number}-{i}'

    query_params = request.GET.copy()
    query_params.pop('page', None)
    url_params = query_params.urlencode()

    context = {
        'lotes': pagina,
        'busca': busca,
        'filtro_lote': filtro_lote,
        'filtro_produto': filtro_produto,
        'filtro_cliente': filtro_cliente,
        'filtro_tipo': filtro_tipo,
        'filtro_usuario': filtro_usuario,
        'data_inicial': data_inicial_txt,
        'data_final': data_final_txt,
        'opcoes_lotes': opcoes_lotes,
        'opcoes_produtos': opcoes_produtos,
        'opcoes_clientes': opcoes_clientes,
        'opcoes_usuarios': opcoes_usuarios,
        'choices_tipo': choices_tipo,
        'total_movimentacoes': total_mov,
        'total_lotes': total_lotes,
        'total_expedicoes': total_exp,
        'movimentacoes_hoje': mov_hoje,
        'page_size': page_size,
        'page_sizes': [10, 25, 50, 100, 200],
        'url_params': url_params,
    }
    return render(request, 'sapp/historico_geral.html', context)


from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import MudarSenhaForm

@login_required
def mudar_senha(request):
    if request.method == 'POST':
        form = MudarSenhaForm(request.POST)
        if form.is_valid():
            nova_senha = form.cleaned_data['nova_senha']
            
            # Impede que o usuário use a senha padrão novamente
            if nova_senha == 'conceito123':
                messages.error(request, "❌ Não utilize a senha padrão. Escolha uma senha segura.")
                return render(request, 'sapp/mudar_senha.html', {'form': form})
            
            request.user.set_password(nova_senha)
            request.user.save()
            
            try:
                perfil = request.user.perfil
                perfil.primeiro_acesso = False
                perfil.save()
            except:
                pass
            
            update_session_auth_hash(request, request.user)
            messages.success(request, "✅ Senha atualizada com sucesso!")
            return redirect('sapp:redirecionar')
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
    elements.append(Paragraph(f"Data: {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
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
@permission_required('sapp.pode_configuracoes', raise_exception=True)
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
@permission_required('sapp.pode_configuracoes', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_configuracoes', raise_exception=True)
def api_verificar_lote(request):
    """API para verificar se um lote existe"""
    lote = request.GET.get('lote', '')
    
    if not lote:
        return JsonResponse({'existe': False})
    
    existe = Estoque.objects.filter(lote=lote).exists()
    
    return JsonResponse({'existe': existe, 'lote': lote})

@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_configuracoes', raise_exception=True)
def api_ultimas_movimentacoes(request):
    """API para últimas movimentações"""
    movimentacoes = HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')[:10]
    
    data = []
    for mov in movimentacoes:
        data.append({
            'id': mov.id,
            'data_hora': timezone.localtime(mov.data_hora).strftime('%d/%m/%Y %H:%M') if mov.data_hora else '--',
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
@permission_required('sapp.pode_ver_empenhos', raise_exception=True)
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
            empenho_id = request.POST.get('empenho_id')
            empenho = get_object_or_404(Empenho, id=empenho_id)
            
            if empenho.historico_itens.exists():
                messages.warning(
                    request, 
                    "Este card possui itens já processados e não pode ser excluído. "
                    "Ele permanecerá disponível para consulta e impressão."
                )
            else:
                nome_card = empenho.observacao or f'Card #{empenho.id}'
                empenho.delete()
                messages.success(request, f"Card '{nome_card}' excluído com sucesso.")
            
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # EXCLUIR ITEM DO CARD
        # -------------------------
        if 'excluir_item' in request.POST:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(
                ItemEmpenho.objects.select_related('empenho'), 
                id=item_id
            )
            
            empenho = item.empenho
            lote_info = item.lote
            item.delete()
            
            if not empenho.itens.exists() and not empenho.historico_itens.exists():
                empenho.delete()
                messages.success(request, f"Item '{lote_info}' removido. Card estava vazio e foi excluído.")
            else:
                messages.success(request, f"Item '{lote_info}' removido do card.")
            
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # TRANSFERIR / EXPEDIR EM MASSA
        # -------------------------
        if request.POST.get('origem_acao') == 'cards':
            acao = request.POST.get('acao_tipo')
            empenho_id = request.POST.get('empenho_id')
            obs_global = request.POST.get('obs_global', '').strip()
            
            if acao not in ['transferir', 'expedir']:
                messages.error(request, "Ação inválida. Use 'transferir' ou 'expedir'.")
                return redirect('sapp:pagina_rascunho')
            
            try:
                selected_items_json = request.POST.get('selected_items', '[]')
                selected_items = json.loads(selected_items_json)
                
                if not isinstance(selected_items, list):
                    raise ValueError("Formato inválido: esperado array")
                
                selected_ids = []
                for item in selected_items:
                    if isinstance(item, dict):
                        item_id = item.get('item_id')
                    else:
                        item_id = item
                    
                    try:
                        item_id = int(item_id)
                        if item_id > 0:
                            selected_ids.append(item_id)
                    except (ValueError, TypeError):
                        continue
                
                selected_ids = list(set(selected_ids))
                
                if not selected_ids:
                    raise ValueError("Nenhum ID válido encontrado")
                    
            except (json.JSONDecodeError, ValueError) as e:
                messages.error(request, f"Dados de seleção inválidos: {str(e)}")
                return redirect('sapp:pagina_rascunho')
            
            try:
                with transaction.atomic():
                    try:
                        empenho = (
                            Empenho.objects
                            .select_for_update()
                            .select_related('solicitacao')
                            .get(id=empenho_id)
                        )
                    except Empenho.DoesNotExist:
                        raise ValueError("Card não encontrado.")

                    solicitacao_vinculada = empenho.solicitacao
                    if solicitacao_vinculada:
                        if solicitacao_vinculada.tipo_solicitacao == 'CARGA' and acao != 'expedir':
                            raise ValueError('Solicitação de carga permite somente Expedir.')
                        if solicitacao_vinculada.tipo_solicitacao != 'CARGA' and acao != 'transferir':
                            raise ValueError('Solicitação comum permite somente Transferir.')
                    
                    itens = list(
                        ItemEmpenho.objects
                        .filter(id__in=selected_ids, empenho=empenho)
                        .select_related('estoque', 'item_carga')
                        .select_for_update()
                    )
                    
                    if not itens:
                        raise ValueError("Nenhum item válido encontrado para processamento.")
                    
                    encontrados_ids = {item.id for item in itens}
                    nao_encontrados = set(selected_ids) - encontrados_ids
                    if nao_encontrados:
                        raise ValueError(
                            f"Alguns itens não pertencem a este card ou não existem: "
                            f"{sorted(nao_encontrados)}"
                        )
                    
                    for item in itens:
                        # Bloqueia também a linha física do estoque. Isso evita duas
                        # requisições concorrentes consumirem o mesmo saldo.
                        item.estoque = (
                            Estoque.objects
                            .select_for_update(of=('self',))
                            .get(pk=item.estoque_id)
                        )
                        
                        if item.quantidade <= 0:
                            raise ValueError(
                                f"Item ID {item.id} (lote {item.lote}) "
                                f"com quantidade inválida: {item.quantidade}"
                            )
                        
                        if item.quantidade > item.estoque.saldo:
                            raise ValueError(
                                f"Saldo insuficiente para lote {item.lote}. "
                                f"Disponível: {item.estoque.saldo}, "
                                f"Solicitado: {item.quantidade}."
                            )
                    
                    movimentado_unidades = Decimal('0')
                    movimentado_kg = Decimal('0')

                    for item in itens:
                        origem = item.estoque
                        qtd = item.quantidade
                        movimentado_unidades += Decimal(str(qtd or 0))
                        movimentado_kg += Decimal(str(qtd or 0)) * Decimal(str(origem.peso_unitario or 0))

                        if acao == 'transferir':
                            # Processar transferência
                            novo_end = request.POST.get('novo_endereco', '').strip().upper()
                            novo_az = request.POST.get('az', '').strip().upper() or origem.az
                            obs_transferencia = request.POST.get('obs_transferencia', '').strip()
                            
                            if not novo_end:
                                raise ValueError("Novo endereço não informado.")
                            
                            if novo_end == origem.endereco:
                                raise ValueError(
                                    f"Endereço de destino igual ao de origem para lote {origem.lote}."
                                )
                            
                            destino = (
                                Estoque.objects
                                .select_for_update()
                                .filter(
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
                                )
                                .first()
                            )
                            
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
                                    observacao=f"{MARCA_ORIGEM} {obs_global} {obs_transferencia}".strip()
                                )
                            
                            origem.saida += qtd
                            origem.save()
                            
                            HistoricoMovimentacao.objects.create(
                                estoque=origem,
                                usuario=user,
                                quantidade=qtd,
                                tipo='Transferência (Saída)',
                                descricao=(
                                    f"{MARCA_ORIGEM} Transferido {qtd} un de "
                                    f"{origem.endereco} para {novo_end}. "
                                    f"{obs_transferencia}"
                                ).strip()
                            )
                            
                            HistoricoMovimentacao.objects.create(
                                estoque=destino,
                                usuario=user,
                                quantidade=qtd,
                                tipo='Transferência (Entrada)',
                                descricao=(
                                    f"{MARCA_ORIGEM} Recebido {qtd} un de "
                                    f"{origem.endereco} em {novo_end}. "
                                    f"{obs_transferencia}"
                                ).strip()
                            )
                            
                            HistoricoItemEmpenho.objects.create(
                                empenho=empenho,
                                item_empenho_id_original=item.id,
                                item_carga_id_original=item.item_carga_id,
                                cliente_solicitacao=(item.cliente_solicitacao_snapshot or (item.item_carga.cliente if item.item_carga else '')),
                                codigo_produto=(item.codigo_produto_snapshot or (item.item_carga.codigo if item.item_carga else '')),
                                descricao_produto=(item.descricao_produto_snapshot or (item.item_carga.descricao if item.item_carga else '')),
                                estoque_origem=origem,
                                estoque_destino=destino,
                                lote=origem.lote,
                                produto=origem.produto or '',
                                cultivar=origem.cultivar.nome if origem.cultivar else '',
                                peneira=origem.peneira.nome if origem.peneira else '',
                                categoria=origem.categoria.nome if origem.categoria else '',
                                tratamento=origem.tratamento.nome if origem.tratamento else '',
                                especie=origem.especie.nome if origem.especie else '',
                                embalagem=origem.embalagem or '',
                                empresa=origem.empresa or '',
                                cliente=origem.cliente or '',
                                endereco_origem=origem.endereco,
                                endereco_destino=novo_end,
                                quantidade=qtd,
                                tipo='transferencia',
                                observacao=obs_transferencia,
                                processado_por=user
                            )
                        else:
                            # Processar expedição
                            obs_expedicao = request.POST.get('obs_expedicao', '').strip()
                            numero_carga = normalizar_texto_cadastro(request.POST.get('numero_carga', ''))
                            cliente = normalizar_texto_cadastro(request.POST.get('cliente', ''))
                            placa = normalizar_texto_cadastro(request.POST.get('placa', ''))
                            motorista_exp = ''
                            if solicitacao_vinculada and solicitacao_vinculada.tipo_solicitacao == 'CARGA':
                                numero_carga = normalizar_texto_cadastro(solicitacao_vinculada.titulo)
                                placa = placa or normalizar_texto_cadastro(solicitacao_vinculada.placa)
                                motorista_exp = normalizar_texto_cadastro(solicitacao_vinculada.motorista)
                            
                            origem.saida += qtd
                            origem.save()
                            
                            cliente_item_carga = (
                                item.cliente_solicitacao_snapshot
                                or (item.item_carga.cliente if item.item_carga else '')
                            )
                            cliente_movimentacao = (
                                cliente_item_carga
                                if solicitacao_vinculada and solicitacao_vinculada.tipo_solicitacao == 'CARGA'
                                else (cliente or origem.cliente or '')
                            )

                            HistoricoMovimentacao.objects.create(
                                estoque=origem,
                                usuario=user,
                                quantidade=qtd,
                                tipo='Expedição',
                                descricao=(
                                    f"{MARCA_ORIGEM} Expedido {qtd} un. "
                                    + (f"Carga: {numero_carga}. " if numero_carga else '')
                                    + f"{obs_global} {obs_expedicao}"
                                ).strip(),
                                numero_carga=numero_carga or None,
                                cliente=cliente_movimentacao,
                                placa=placa or None,
                                motorista=motorista_exp or None,
                                origem_carga=(
                                    'GERADA'
                                    if solicitacao_vinculada and solicitacao_vinculada.tipo_solicitacao == 'CARGA'
                                    else ''
                                ),
                            )
                            
                            HistoricoItemEmpenho.objects.create(
                                empenho=empenho,
                                item_empenho_id_original=item.id,
                                item_carga_id_original=item.item_carga_id,
                                cliente_solicitacao=(item.cliente_solicitacao_snapshot or (item.item_carga.cliente if item.item_carga else '')),
                                codigo_produto=(item.codigo_produto_snapshot or (item.item_carga.codigo if item.item_carga else '')),
                                descricao_produto=(item.descricao_produto_snapshot or (item.item_carga.descricao if item.item_carga else '')),
                                estoque_origem=origem,
                                lote=origem.lote,
                                produto=origem.produto or '',
                                cultivar=origem.cultivar.nome if origem.cultivar else '',
                                peneira=origem.peneira.nome if origem.peneira else '',
                                categoria=origem.categoria.nome if origem.categoria else '',
                                tratamento=origem.tratamento.nome if origem.tratamento else '',
                                especie=origem.especie.nome if origem.especie else '',
                                embalagem=origem.embalagem or '',
                                empresa=origem.empresa or '',
                                cliente=cliente or origem.cliente or '',
                                endereco_origem=origem.endereco,
                                quantidade=qtd,
                                tipo='expedicao',
                                observacao=obs_expedicao,
                                numero_carga=numero_carga,
                                placa=placa,
                                processado_por=user
                            )
                        
                        # SÓ AGORA excluir o item processado
                        item.delete()
                    
                    # Atualizar status do card
                    empenho.refresh_from_db()
                    if not empenho.itens.exists():
                        if empenho.historico_itens.exists():
                            status_concluido, _ = EmpenhoStatus.objects.get_or_create(
                                nome='Concluído',
                                defaults={'descricao': 'Card processado completamente'}
                            )
                            empenho.status = status_concluido
                            empenho.save()
                            messages.info(request, "Todos os itens foram processados. Card marcado como concluído.")
                        else:
                            empenho.delete()
                    
                    if solicitacao_vinculada:
                        incremento = (
                            movimentado_kg
                            if solicitacao_vinculada.unidade_controle == 'QUILOGRAMA'
                            else movimentado_unidades
                        )
                        solicitacao_vinculada.quantidade_movimentada = (
                            Decimal(str(solicitacao_vinculada.quantidade_movimentada or 0))
                            + incremento
                        )

                        if solicitacao_vinculada.unidade_controle == 'QUILOGRAMA':
                            restante = Decimal('0')
                            for item_restante in empenho.itens.select_related('estoque'):
                                restante += Decimal(str(item_restante.quantidade or 0)) * Decimal(str(item_restante.estoque.peso_unitario or 0))
                            solicitacao_vinculada.quantidade_empenhada = restante
                        else:
                            restante = empenho.itens.aggregate(total=Sum('quantidade'))['total'] or 0
                            solicitacao_vinculada.quantidade_empenhada = Decimal(str(restante))

                        solicitado = Decimal(str(solicitacao_vinculada.quantidade_solicitada or 0))
                        if solicitado > 0 and solicitacao_vinculada.quantidade_movimentada >= solicitado:
                            solicitacao_vinculada.quantidade_movimentada = solicitado
                            solicitacao_vinculada.status = 'CONCLUIDO'
                        elif solicitacao_vinculada.quantidade_movimentada > 0:
                            solicitacao_vinculada.status = 'MOVIMENTACAO_PARCIAL'

                        solicitacao_vinculada.save(update_fields=[
                            'quantidade_movimentada',
                            'quantidade_empenhada',
                            'status',
                            'data_atualizacao',
                        ])
                        cache.delete('cards_version_hash')

                    acao_nome = 'Transferência' if acao == 'transferir' else 'Expedição'
                    messages.success(
                        request, 
                        f"{acao_nome} realizada com sucesso! "
                        f"{len(itens)} item(ns) processado(s)."
                    )
                    
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Erro inesperado ao processar: {str(e)}")
            
            return redirect('sapp:pagina_rascunho')

    # =====================================================
    # GET (DADOS)
    # =====================================================
    
    ids_rascunhos = ItemEmpenho.objects.all().values_list('estoque_id', flat=True)

    estoque_qs = (
        Estoque.objects
        .filter(Q(saldo__gt=0) | Q(id__in=ids_rascunhos))
        .select_related(
            'cultivar', 'peneira', 'categoria', 
            'tratamento', 'especie', 'conferente',
            'status_sistemico'
        )
        .order_by('lote', 'endereco')
    )

    todos_itens = list(
        ItemEmpenho.objects
        .select_related('empenho', 'estoque', 'item_carga')
    )

    itens_por_estoque = defaultdict(list)
    for item in todos_itens:
        itens_por_estoque[item.estoque_id].append(item)

    lotes_contexto = []
    for lote in estoque_qs:
        itens = itens_por_estoque.get(lote.id, [])
        empenhado = lote.empenhado
        disponivel = lote.disponivel
        
        for item in itens:
            item.inconsistente = item.quantidade > lote.saldo
        
        tem_inconsistencia = any(
            item.quantidade > lote.saldo for item in itens
        )
        
        lotes_contexto.append({
            'lote': lote,
            'empenhado': empenhado,
            'disponivel': disponivel,
            'itens_empenho': itens,
            'tem_inconsistencia': tem_inconsistencia
        })

    cards_ativos = (
        Empenho.objects
        .filter(status__nome='Rascunho')
        .select_related('solicitacao')
        .prefetch_related(
            'itens',
            'itens__estoque',
            'historico_itens'
        )
        .order_by('-id')
    )
    
    cards_concluidos = (
        Empenho.objects
        .filter(status__nome='Concluído')
        .select_related('solicitacao')
        .prefetch_related('historico_itens')
        .order_by('-id')
    )
    
    # ================================================================
    # DADOS PARA O MODAL (JSON)
    # ================================================================
    cards_impressao = {}
    for card in list(cards_ativos) + list(cards_concluidos):
        itens_pendentes = []
        for item in card.itens.all():
            estoque = item.estoque
            if estoque is None:
                continue
            itens_pendentes.append({
                'item_id': item.id,
                'empenho_id': card.id,
                'estoque_id': estoque.id,
                'lote': item.lote or estoque.lote,
                'quantidade': item.quantidade,
                'endereco': estoque.endereco or item.endereco_origem,
                'produto': estoque.produto or '',
                'cultivar': item.cultivar or (estoque.cultivar.nome if estoque.cultivar else ''),
                'peneira': item.peneira or (estoque.peneira.nome if estoque.peneira else ''),
                'categoria': item.categoria or (estoque.categoria.nome if estoque.categoria else ''),
                'especie': estoque.especie.nome if estoque.especie else '',
                'tratamento': estoque.tratamento.nome if estoque.tratamento else '',
                'embalagem': estoque.embalagem or '',
                'empresa': estoque.empresa or '',
                'cliente': item.cliente_solicitacao_snapshot or (item.item_carga.cliente if item.item_carga else '') or estoque.cliente or '',
                'codigo': item.codigo_produto_snapshot or (item.item_carga.codigo if item.item_carga else '') or estoque.produto or '',
                'descricao': item.descricao_produto_snapshot or (item.item_carga.descricao if item.item_carga else '') or '',
                'saldo_atual': estoque.saldo,
                'peso_unitario': str(estoque.peso_unitario) if estoque.peso_unitario else '0',
                'peso_total': str(estoque.peso_total) if estoque.peso_total else '0',
                'az': estoque.az or '',
                'conferente': estoque.conferente.get_full_name() if estoque.conferente else '',
                'observacao': item.observacao or estoque.observacao or '',
                'status_sistemico': estoque.status_sistemico.nome if estoque.status_sistemico else '',
                'situacao': 'pendente',
                'processado_em': None,
                'data_ultima_movimentacao': timezone.localtime(estoque.data_ultima_movimentacao).strftime('%d/%m/%Y %H:%M') if estoque.data_ultima_movimentacao else '',
            })
        
        itens_processados = []
        for hist in card.historico_itens.all():
            itens_processados.append({
                'item_id': hist.id,
                'empenho_id': card.id,
                'estoque_id': hist.estoque_origem_id,
                'lote': hist.lote,
                'quantidade': hist.quantidade,
                'endereco': hist.endereco_origem,
                'produto': hist.produto,
                'cultivar': hist.cultivar,
                'peneira': hist.peneira,
                'categoria': hist.categoria,
                'especie': hist.especie,
                'tratamento': hist.tratamento,
                'embalagem': hist.embalagem,
                'empresa': hist.empresa,
                'cliente': hist.cliente_solicitacao or hist.cliente,
                'codigo': hist.codigo_produto or hist.produto,
                'descricao': hist.descricao_produto or '',
                'saldo_atual': 0,
                'peso_unitario': '0',
                'peso_total': '0',
                'az': '',
                'conferente': '',
                'observacao': hist.observacao,
                'status_sistemico': '',
                'situacao': 'transferido' if hist.tipo == 'transferencia' else 'expedido',
                'processado_em': timezone.localtime(hist.processado_em).strftime('%d/%m/%Y %H:%M') if hist.processado_em else '',
                'data_ultima_movimentacao': timezone.localtime(hist.processado_em).strftime('%d/%m/%Y %H:%M') if hist.processado_em else '',
                'tipo': hist.get_tipo_display(),
                'endereco_destino': hist.endereco_destino if hist.tipo == 'transferencia' else '',
            })
        
        cards_impressao[str(card.id)] = {
            'card_id': card.id,
            'card_nome': card.observacao or f'Card #{card.id}',
            'tipo_solicitacao': card.solicitacao.tipo_solicitacao if card.solicitacao else '',
            'solicitacao_id': card.solicitacao_id,
            'itens_pendentes': itens_pendentes,
            'itens_processados': itens_processados,
            'total_pendentes': len(itens_pendentes),
            'total_processados': len(itens_processados),
            'itens_ids': [item['item_id'] for item in itens_pendentes],
        }

    return render(request, 'sapp/pagina_rascunho.html', {
        'lotes': lotes_contexto,
        'cards_ativos': cards_ativos,
        'cards_concluidos': cards_concluidos,
        'cards_impressao': cards_impressao,
        'cards_impressao_json': json.dumps(cards_impressao, ensure_ascii=False),
    })


    
def processar_transferencia_item(request, item, user, MARCA_ORIGEM, obs_global, empenho):
    """Processa a transferência de um item específico."""
    origem = item.estoque
    qtd = item.quantidade  # Quantidade total do item, nunca parcial
    
    novo_end = request.POST.get('novo_endereco', '').strip().upper()
    novo_az = request.POST.get('az', '').strip().upper() or origem.az
    obs_transferencia = request.POST.get('obs_transferencia', '').strip()
    
    if not novo_end:
        raise ValueError("Novo endereço não informado.")
    
    if novo_end == origem.endereco:
        raise ValueError(
            f"Endereço de destino igual ao de origem para lote {origem.lote}."
        )
    
    # Buscar ou criar destino com lock para evitar duplicação
    destino = (
        Estoque.objects
        .select_for_update()
        .filter(
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
        )
        .first()
    )
    
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
            observacao=f"{MARCA_ORIGEM} {obs_global} {obs_transferencia}".strip()
        )
    
    # Atualizar saída da origem
    origem.saida += qtd
    origem.save()
    
    # Criar histórico de movimentação (saída)
    HistoricoMovimentacao.objects.create(
        estoque=origem,
        usuario=user,
        quantidade=qtd,
        tipo='Transferência (Saída)',
        descricao=(
            f"{MARCA_ORIGEM} Transferido {qtd} un de "
            f"{origem.endereco} para {novo_end}. "
            f"{obs_transferencia}"
        ).strip()
    )
    
    # Criar histórico de movimentação (entrada)
    HistoricoMovimentacao.objects.create(
        estoque=destino,
        usuario=user,
        quantidade=qtd,
        tipo='Transferência (Entrada)',
        descricao=(
            f"{MARCA_ORIGEM} Recebido {qtd} un de "
            f"{origem.endereco} em {novo_end}. "
            f"{obs_transferencia}"
        ).strip()
    )
    
    # Criar histórico do item empenho (ANTES de excluir o item)
    HistoricoItemEmpenho.objects.create(
        empenho=empenho,
        item_empenho_id_original=item.id,
        estoque_origem=origem,
        estoque_destino=destino,
        lote=origem.lote,
        produto=origem.produto or '',
        cultivar=origem.cultivar.nome if origem.cultivar else '',
        peneira=origem.peneira.nome if origem.peneira else '',
        categoria=origem.categoria.nome if origem.categoria else '',
        tratamento=origem.tratamento.nome if origem.tratamento else '',
        especie=origem.especie.nome if origem.especie else '',
        embalagem=origem.embalagem or '',
        empresa=origem.empresa or '',
        cliente=origem.cliente or '',
        endereco_origem=origem.endereco,
        endereco_destino=novo_end,
        quantidade=qtd,
        tipo='transferencia',
        observacao=obs_transferencia,
        processado_por=user
    )
    
    # SÓ AGORA excluir o item original
    item.delete()


def processar_expedicao_item(request, item, user, MARCA_ORIGEM, obs_global, empenho):
    """Processa a expedição de um item específico."""
    origem = item.estoque
    qtd = item.quantidade  # Quantidade total do item, nunca parcial
    
    obs_expedicao = request.POST.get('obs_expedicao', '').strip()
    numero_carga = request.POST.get('numero_carga', '').strip()
    cliente = request.POST.get('cliente', '').strip()
    placa = request.POST.get('placa', '').strip()

    solicitacao_vinculada = getattr(empenho, 'solicitacao', None)
    if solicitacao_vinculada and solicitacao_vinculada.tipo_solicitacao == 'CARGA':
        numero_carga = str(solicitacao_vinculada.titulo or '').strip()
    
    if not numero_carga:
        raise ValueError("Número da carga/pedido não informado.")
    
    # Atualizar saída da origem
    origem.saida += qtd
    origem.save()
    
    # Criar histórico de movimentação
    HistoricoMovimentacao.objects.create(
        estoque=origem,
        usuario=user,
        quantidade=qtd,
        tipo='Expedição',
        descricao=(
            f"{MARCA_ORIGEM} Expedido {qtd} un. "
            f"Carga: {numero_carga}. "
            f"{obs_global} {obs_expedicao}"
        ).strip(),
        numero_carga=numero_carga,
        cliente=cliente or origem.cliente,
        placa=placa,
        origem_carga=(
            'GERADA'
            if solicitacao_vinculada and solicitacao_vinculada.tipo_solicitacao == 'CARGA'
            else ''
        ),
    )
    
    # Criar histórico do item empenho (ANTES de excluir o item)
    HistoricoItemEmpenho.objects.create(
        empenho=empenho,
        item_empenho_id_original=item.id,
        estoque_origem=origem,
        lote=origem.lote,
        produto=origem.produto or '',
        cultivar=origem.cultivar.nome if origem.cultivar else '',
        peneira=origem.peneira.nome if origem.peneira else '',
        categoria=origem.categoria.nome if origem.categoria else '',
        tratamento=origem.tratamento.nome if origem.tratamento else '',
        especie=origem.especie.nome if origem.especie else '',
        embalagem=origem.embalagem or '',
        empresa=origem.empresa or '',
        cliente=cliente or origem.cliente or '',
        endereco_origem=origem.endereco,
        quantidade=qtd,
        tipo='expedicao',
        observacao=obs_expedicao,
        numero_carga=numero_carga,
        placa=placa,
        processado_por=user
    )
    
    # SÓ AGORA excluir o item original
    item.delete()


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)  # CORRIGIDO
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

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@        ESTA COM DECORADOR         @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@login_required
@permission_required('sapp.pode_ver_empenhos', raise_exception=True)
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
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_autocomplete_nova_entrada(request):
    
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


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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

@login_required
@permission_required('sapp.pode_ver_mapa', raise_exception=True)  # 🔥 ADICIONAR
def lista_armazens(request):
  
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
@permission_required('sapp.pode_ver_mapa', raise_exception=True)
def mapa_ocupacao_canvas(request, armazem_numero=1):
    # 1. Busca Armazém e Elementos
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero, ativo=True)
    elementos_db = armazem.elementos.all().order_by('ordem_z')
    armazens_disponiveis = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    # 2. Limita o estoque SOMENTE ao armazém/mapa aberto.
    # Primeiro tenta relacionar ArmazemLayout com o cadastro de Armazem pelo nome.
    nomes_possiveis = [
        str(armazem.nome).strip(),
        f'ARMAZEM {armazem.numero}',
        f'ARMAZÉM {armazem.numero}',
        f'AZ {armazem.numero}',
        f'AZ{armazem.numero}',
    ]
    armazem_cadastro = next((
        cadastro
        for nome in nomes_possiveis
        for cadastro in [Armazem.objects.filter(nome__iexact=nome).first()]
        if cadastro
    ), None)

    # Endereços desenhados especificamente neste mapa.
    enderecos_mapa = {
        el.identificador.strip().upper()
        for el in elementos_db
        if el.tipo == 'RETANGULO' and el.identificador
    }

    if armazem_cadastro:
        enderecos_permitidos = list(
            Endereco.objects.filter(armazem=armazem_cadastro)
            .values_list('codigo', flat=True)
        )
    else:
        # Fallback seguro para instalações nas quais os nomes ainda não coincidem.
        enderecos_permitidos = list(enderecos_mapa)

    enderecos_permitidos_normalizados = {
        str(codigo).strip().upper()
        for codigo in enderecos_permitidos
        if codigo
    }
    itens_estoque = (
        Estoque.objects.filter(saldo__gt=0)
        .select_related('especie', 'cultivar')
    )

    # 3. Mapeia Estoque (Normalizando Endereço: Tira espaços e põe Maiúsculo)
    dados_ocupacao = {}
    
    for item in itens_estoque:
        if item.endereco:
            # A MÁGICA: .strip().upper() garante que " a-01" seja igual a "A-01"
            chave = item.endereco.strip().upper()
            if chave not in enderecos_permitidos_normalizados:
                continue
            
            if chave not in dados_ocupacao:
                dados_ocupacao[chave] = []
            
            dados_ocupacao[chave].append({
                'lote': item.lote,
                'produto': str(item.produto or 'S/ Produto'),
                'qtd': float(item.saldo),
                'embalagem': str(item.embalagem),
                'cliente': str(item.cliente or '-'),
                'especie': str(item.especie or 'Não informado'),
                'cultivar': str(item.cultivar or 'Não informado'),
                'armazem_numero': str(armazem.numero),
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
"""
def lista_armazens(request):
    armazens = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazens': armazens,
        'is_admin': request.user.is_staff,
        'titulo_pagina': 'Mapas dos Armazéns'
    }
    return render(request, 'sapp/lista_armazens.html', context)
"""
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


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
def api_buscar_produto(request):
    """
    Resolve produto por código ou, quando o código estiver vazio,
    por Cultivar + Tratamento. Nunca escolhe silenciosamente quando
    existir mais de um produto compatível.
    """
    if request.method != 'GET':
        return JsonResponse({'encontrado': False, 'erro': 'Método não permitido.'}, status=405)

    try:
        codigo = _normalizar_codigo_produto(request.GET.get('codigo', ''))
        cultivar_id = request.GET.get('cultivar_id') or request.GET.get('cultivar')
        tratamento_id = request.GET.get('tratamento_id') or request.GET.get('tratamento')

        if codigo:
            produto = (
                Produto.objects
                .filter(codigo__iexact=codigo, ativo=True)
                .select_related('cultivar', 'peneira', 'especie', 'categoria', 'tratamento')
                .first()
            )
            if not produto:
                return JsonResponse({
                    'encontrado': False,
                    'erro': f'Produto {codigo} não encontrado ou inativo.'
                })
        else:
            if not cultivar_id:
                return JsonResponse({
                    'encontrado': False,
                    'erro': 'Informe o código ou selecione Cultivar + Tratamento.'
                })

            qs = (
                Produto.objects
                .filter(cultivar_id=cultivar_id, ativo=True)
                .select_related('cultivar', 'peneira', 'especie', 'categoria', 'tratamento')
            )
            if tratamento_id:
                qs = qs.filter(tratamento_id=tratamento_id)
            else:
                qs = qs.filter(tratamento__isnull=True)

            produtos = list(qs.order_by('id')[:2])
            if not produtos:
                return JsonResponse({
                    'encontrado': False,
                    'erro': 'Nenhum produto cadastrado para essa combinação.'
                })
            if len(produtos) > 1:
                return JsonResponse({
                    'encontrado': False,
                    'ambiguo': True,
                    'erro': 'Existe mais de um produto para essa combinação. Informe o código.'
                })
            produto = produtos[0]

        dados = {
            'codigo': produto.codigo,
            'cultivar_id': str(produto.cultivar_id) if produto.cultivar_id else None,
            'cultivar_nome': produto.cultivar.nome if produto.cultivar else '',
            'peneira_id': str(produto.peneira_id) if produto.peneira_id else None,
            'peneira_nome': produto.peneira.nome if produto.peneira else '',
            'especie_id': str(produto.especie_id) if produto.especie_id else None,
            'especie_nome': produto.especie.nome if produto.especie else '',
            'categoria_id': str(produto.categoria_id) if produto.categoria_id else None,
            'categoria_nome': produto.categoria.nome if produto.categoria else '',
            'tratamento_id': str(produto.tratamento_id) if produto.tratamento_id else None,
            'tratamento_nome': produto.tratamento.nome if produto.tratamento else '',
            'empresa': produto.empresa or '',
            'tipo': produto.tipo or '',
            'descricao': produto.descricao or '',
        }
        return JsonResponse({'encontrado': True, 'dados': dados})
    except Exception as exc:
        logger.exception('Erro ao resolver produto para lote')
        return JsonResponse({'encontrado': False, 'erro': str(exc)}, status=500)



# sapp/views.py

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_atualizar_status_sistemico(request):
    """API para atualizar o status sistêmico com cores personalizadas"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lote_id = data.get('lote_id')
            status_id = data.get('status_id')
            observacao = data.get('observacao', '').strip()
            
            if not lote_id or not status_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'ID do lote e status são obrigatórios'
                })
            
            with transaction.atomic():
                lote = get_object_or_404(Estoque, id=lote_id)
                status_anterior = lote.status_sistemico
                novo_status = get_object_or_404(StatusSistemico, id=status_id)
                
                # Salvar histórico
                HistoricoStatusSistemico.objects.create(
                    estoque=lote,
                    status_anterior=status_anterior,
                    status_novo=novo_status,
                    observacao=observacao or '',
                    alterado_por=request.user
                )
                
                # Atualizar o lote
                lote.status_sistemico = novo_status
                lote.status_sistemico_alterado_por = request.user
                lote.status_sistemico_alterado_em = timezone.now()
                lote.status_sistemico_observacao = observacao or ''
                lote.save()
                
                # Registrar no histórico geral
                HistoricoMovimentacao.objects.create(
                    estoque=lote,
                    usuario=request.user,
                    tipo='Status Sistêmico',
                    descricao=f'Status alterado para: {novo_status.nome} - {observacao or "Sem observação"}'
                )
                
                return JsonResponse({
                    'success': True,
                    'status': {
                        'id': novo_status.id,
                        'nome': novo_status.nome,
                        'cor': novo_status.cor,
                        'icone': novo_status.icone or '',
                        'legenda': novo_status.legenda or '',
                    },
                    'alterado_por': request.user.get_full_name() or request.user.username,
                    'alterado_em': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
                    'observacao': observacao or ''
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# sapp/views.py - Adicione esta função

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_excluir_status(request, status_id):
    """Exclui um status personalizado (apenas se não estiver em uso)"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    
    try:
        status = get_object_or_404(StatusSistemico, id=status_id)
        
        # Verificar se é status padrão
        if status.e_padrao:
            return JsonResponse({
                'success': False, 
                'error': 'Status padrão não pode ser excluído'
            })
        
        # Verificar se está em uso
        em_uso = Estoque.objects.filter(status_sistemico=status).exists()
        if em_uso:
            return JsonResponse({
                'success': False, 
                'error': 'Status está em uso por um ou mais lotes. Remova os lotes primeiro.'
            })
        
        # Excluir
        status.delete()
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# sapp/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from .models import Estoque, StatusSistemico, HistoricoStatusSistemico

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_atualizar_status_sistemico(request):
    """API para atualizar o status sistêmico com cores personalizadas"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lote_id = data.get('lote_id')
            status_id = data.get('status_id')
            observacao = data.get('observacao', '').strip()
            nova_legenda = data.get('nova_legenda', '').strip()
            
            if not lote_id or not status_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'ID do lote e status são obrigatórios'
                })
            
            with transaction.atomic():
                lote = get_object_or_404(Estoque, id=lote_id)
                status_anterior = lote.status_sistemico
                novo_status = get_object_or_404(StatusSistemico, id=status_id)
                
                # Atualizar legenda se fornecida
                if nova_legenda:
                    novo_status.legenda = nova_legenda
                    novo_status.save(update_fields=['legenda'])
                
                # Salvar histórico antes de alterar
                HistoricoStatusSistemico.objects.create(
                    estoque=lote,
                    status_anterior=status_anterior,
                    status_novo=novo_status,
                    observacao=observacao or '',
                    alterado_por=request.user
                )
                
                # Atualizar o lote
                lote.status_sistemico = novo_status
                lote.status_sistemico_alterado_por = request.user
                lote.status_sistemico_alterado_em = timezone.now()
                lote.status_sistemico_observacao = observacao or ''
                lote.save()
                
                # Registrar no histórico geral
                HistoricoMovimentacao.objects.create(
                    estoque=lote,
                    usuario=request.user,
                    tipo='Status Sistêmico',
                    descricao=f'Status alterado para: {novo_status.nome} - {observacao or "Sem observação"}'
                )
                
                return JsonResponse({
                    'success': True,
                    'status': {
                        'id': novo_status.id,
                        'nome': novo_status.nome,
                        'cor': novo_status.cor,
                        'icone': novo_status.icone or '',
                        'legenda': novo_status.legenda or '',
                    },
                    'alterado_por': request.user.get_full_name() or request.user.username,
                    'alterado_em': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
                    'observacao': observacao or ''
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_listar_status(request):
    """Lista todos os status disponíveis"""
    status_list = StatusSistemico.objects.filter(ativo=True).order_by('ordem', 'nome')
    return JsonResponse({
        'success': True,
        'status': [{
            'id': s.id,
            'nome': s.nome,
            'cor': s.cor,
            'icone': s.icone or '',
            'legenda': s.legenda or '',
            'e_padrao': s.e_padrao,
        } for s in status_list]
    })

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_criar_status(request):
    """Cria um novo status personalizado"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nome = data.get('nome', '').strip()
            cor = data.get('cor', '#6c757d')
            legenda = data.get('legenda', '').strip()
            icone = data.get('icone', '')
            
            if not nome:
                return JsonResponse({'success': False, 'error': 'Nome do status é obrigatório'})
            
            # Verificar se já existe
            if StatusSistemico.objects.filter(nome__iexact=nome).exists():
                return JsonResponse({
                    'success': False, 
                    'error': f'Já existe um status com o nome "{nome}"'
                })
            
            status = StatusSistemico.objects.create(
                nome=nome,
                cor=cor,
                legenda=legenda or nome,
                icone=icone or '🔹',
                e_padrao=False,
                ativo=True,
                criado_por=request.user
            )
            
            return JsonResponse({
                'success': True,
                'status': {
                    'id': status.id,
                    'nome': status.nome,
                    'cor': status.cor,
                    'icone': status.icone,
                    'legenda': status.legenda,
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
def api_editar_status(request, status_id):
    """Edita um status existente"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = get_object_or_404(StatusSistemico, id=status_id)
            
            # Atualizar campos
            if 'nome' in data:
                status.nome = data['nome'].strip()
            if 'cor' in data:
                status.cor = data['cor']
            if 'legenda' in data:
                status.legenda = data['legenda'].strip()
            if 'icone' in data:
                status.icone = data['icone']
            if 'ativo' in data:
                status.ativo = data['ativo']
            
            status.save()
            
            return JsonResponse({
                'success': True,
                'status': {
                    'id': status.id,
                    'nome': status.nome,
                    'cor': status.cor,
                    'icone': status.icone,
                    'legenda': status.legenda,
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


######################################################################################################################################
######################################################################################################################################
######################################################################################################################################
################# dashboard ##########################################################################################################

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.db.models import (
    Count,
    Q,
    Sum,
)
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import (
    DashboardConfig,
    Estoque,
    HistoricoMovimentacao,
)


# ================================================================
# PERMISSÕES
# ================================================================

def is_admin(user):
    """
    Considera administrador:
    - superusuário;
    - usuário pertencente ao grupo Administradores.
    """
    return (
        user.is_superuser
        or user.groups.filter(
            name='Administradores'
        ).exists()
    )


# ================================================================
# PÁGINA PRINCIPAL DO DASHBOARD
# ================================================================

@login_required
def dashboard(request):
    """
    Renderiza a página do Dashboard.

    O Dashboard V2/V3 carrega KPIs, gráficos, filtros e movimentações
    pelo endpoint AJAX dashboard_data. Portanto não precisamos repetir
    todas as consultas pesadas aqui.
    """

    tem_permissao = (
        request.user.is_superuser
        or request.user.has_perm(
            'sapp.pode_ver_dashboard'
        )
        or request.user.has_perm(
            'sapp.pode_ver_estoque'
        )
    )

    if not tem_permissao:
        return redirect(
            'sapp:redirecionar'
        )

    config, _ = (
        DashboardConfig.objects
        .get_or_create(
            criado_por=request.user
        )
    )

    context = {
        'config': config,
        'is_admin': is_admin(
            request.user
        ),
        'page_title': (
            'Dashboard Analítico'
        ),
    }

    return render(
        request,
        'sapp/dashboard.html',
        context,
    )


# ================================================================
# CONFIGURAÇÃO DO DASHBOARD
# ================================================================

@login_required
@user_passes_test(is_admin)
def salvar_config_dashboard(request):
    """
    Salva configurações visuais/operacionais do Dashboard.
    """

    if request.method != 'POST':
        return redirect(
            'sapp:dashboard'
        )

    def inteiro(
        nome,
        padrao,
        minimo=None,
        maximo=None,
    ):
        try:
            valor = int(
                request.POST.get(
                    nome,
                    padrao,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            valor = padrao

        if minimo is not None:
            valor = max(
                minimo,
                valor,
            )

        if maximo is not None:
            valor = min(
                maximo,
                valor,
            )

        return valor

    DashboardConfig.objects.update_or_create(
        criado_por=request.user,
        defaults={
            'cultivar_tipo': request.POST.get(
                'cultivar_tipo',
                'doughnut',
            ),
            'cultivar_qtd': inteiro(
                'cultivar_qtd',
                10,
                1,
                50,
            ),
            'cultivar_ordem': request.POST.get(
                'cultivar_ordem',
                'valor_desc',
            ),
            'cultivar_zerados': (
                request.POST.get(
                    'cultivar_zerados'
                )
                == 'on'
            ),
            'cultivar_agrupar_outros': (
                request.POST.get(
                    'cultivar_agrupar_outros'
                )
                == 'on'
            ),
            'peneira_tipo': request.POST.get(
                'peneira_tipo',
                'pie',
            ),
            'peneira_qtd': inteiro(
                'peneira_qtd',
                8,
                1,
                50,
            ),
            'peneira_ordem': request.POST.get(
                'peneira_ordem',
                'valor_desc',
            ),
            'armazem_tipo': request.POST.get(
                'armazem_tipo',
                'bar',
            ),
            'armazem_ordem': request.POST.get(
                'armazem_ordem',
                'nome_asc',
            ),
            'armazem_metrica': request.POST.get(
                'armazem_metrica',
                'volume',
            ),
            'tendencia_periodo': inteiro(
                'tendencia_periodo',
                15,
                7,
                90,
            ),
            'tendencia_saidas': (
                request.POST.get(
                    'tendencia_saidas'
                )
                == 'on'
            ),
            'tendencia_transferencias': (
                request.POST.get(
                    'tendencia_transferencias'
                )
                == 'on'
            ),
            'tendencia_agrupamento': (
                request.POST.get(
                    'tendencia_agrupamento',
                    'day',
                )
            ),
            'auto_refresh': inteiro(
                'auto_refresh',
                0,
                0,
                3600,
            ),
            'unidade_padrao': request.POST.get(
                'unidade_padrao',
                'sc',
            ),
            'tema_cores': request.POST.get(
                'tema_cores',
                'default',
            ),
            'mostrar_legendas': (
                request.POST.get(
                    'mostrar_legendas'
                )
                == 'on'
            ),
            'mostrar_percentuais': (
                request.POST.get(
                    'mostrar_percentuais'
                )
                == 'on'
            ),
            'filtro_cultivar': (
                request.POST.get(
                    'filtro_cultivar'
                )
                == 'on'
            ),
            'filtro_peneira': (
                request.POST.get(
                    'filtro_peneira'
                )
                == 'on'
            ),
            'filtro_armazem': (
                request.POST.get(
                    'filtro_armazem'
                )
                == 'on'
            ),
            'filtro_periodo': (
                request.POST.get(
                    'filtro_periodo'
                )
                == 'on'
            ),
        },
    )

    messages.success(
        request,
        'Configurações salvas com sucesso!',
    )

    return redirect(
        'sapp:dashboard'
    )


# ================================================================
# HELPERS DE FILTRO
# ================================================================

def _dashboard_aplicar_filtros_estoque(
    queryset,
    *,
    tipos_semente=None,
    cultivares=None,
    peneiras=None,
    unidades=None,
    armazens=None,
    search='',
):
    """
    Aplica filtros ao estoque.

    Esta função não força saldo > 0.
    Quem chama decide se quer somente estoque ativo.
    """

    tipos_semente = (
        tipos_semente or []
    )
    cultivares = (
        cultivares or []
    )
    peneiras = (
        peneiras or []
    )
    unidades = (
        unidades or []
    )
    armazens = (
        armazens or []
    )

    if tipos_semente:
        queryset = queryset.filter(
            especie__nome__in=
                tipos_semente
        )

    if cultivares:
        queryset = queryset.filter(
            cultivar_id__in=
                cultivares
        )

    if peneiras:
        queryset = queryset.filter(
            peneira_id__in=
                peneiras
        )

    if unidades:
        queryset = queryset.filter(
            embalagem__in=
                unidades
        )

    if armazens:
        queryset = queryset.filter(
            az__in=
                armazens
        )

    if search:
        queryset = queryset.filter(
            Q(
                lote__icontains=
                    search
            )
            | Q(
                produto__icontains=
                    search
            )
            | Q(
                cultivar__nome__icontains=
                    search
            )
            | Q(
                especie__nome__icontains=
                    search
            )
            | Q(
                cliente__icontains=
                    search
            )
            | Q(
                endereco__icontains=
                    search
            )
            | Q(
                az__icontains=
                    search
            )
        )

    return queryset


def _dashboard_aplicar_filtros_movimentacao(
    queryset,
    *,
    tipos_semente=None,
    cultivares=None,
    peneiras=None,
    unidades=None,
    armazens=None,
    search='',
):
    """
    Aplica filtros ao histórico usando os dados relacionados ao estoque.

    Importante:
    NÃO restringe o histórico aos lotes que ainda possuem saldo positivo.
    Assim um lote totalmente expedido continua aparecendo nos gráficos.
    """

    tipos_semente = (
        tipos_semente or []
    )
    cultivares = (
        cultivares or []
    )
    peneiras = (
        peneiras or []
    )
    unidades = (
        unidades or []
    )
    armazens = (
        armazens or []
    )

    if tipos_semente:
        queryset = queryset.filter(
            estoque__especie__nome__in=
                tipos_semente
        )

    if cultivares:
        queryset = queryset.filter(
            estoque__cultivar_id__in=
                cultivares
        )

    if peneiras:
        queryset = queryset.filter(
            estoque__peneira_id__in=
                peneiras
        )

    if unidades:
        queryset = queryset.filter(
            estoque__embalagem__in=
                unidades
        )

    if armazens:
        queryset = queryset.filter(
            estoque__az__in=
                armazens
        )

    if search:
        queryset = queryset.filter(
            Q(
                lote_ref__icontains=
                    search
            )
            | Q(
                estoque__lote__icontains=
                    search
            )
            | Q(
                estoque__produto__icontains=
                    search
            )
            | Q(
                estoque__cultivar__nome__icontains=
                    search
            )
            | Q(
                estoque__especie__nome__icontains=
                    search
            )
            | Q(
                estoque__cliente__icontains=
                    search
            )
            | Q(
                estoque__endereco__icontains=
                    search
            )
            | Q(
                descricao__icontains=
                    search
            )
            | Q(
                numero_carga__icontains=
                    search
            )
            | Q(
                placa__icontains=
                    search
            )
            | Q(
                motorista__icontains=
                    search
            )
            | Q(
                cliente__icontains=
                    search
            )
        )

    return queryset


def _dashboard_q_entrada():
    """
    Entradas comuns e Transferência (Entrada).
    """
    return (
        Q(
            tipo__icontains='Entrada'
        )
    )


def _dashboard_q_saida():
    """
    Saídas reconhecidas pelo sistema:
    - Saída
    - Transferência (Saída)
    - Expedição

    Inclui também versões sem acento para proteger dados antigos.
    """
    return (
        Q(
            tipo__icontains='Saída'
        )
        | Q(
            tipo__icontains='Saida'
        )
        | Q(
            tipo__icontains='Expedição'
        )
        | Q(
            tipo__icontains='Expedicao'
        )
    )


def _dashboard_filtro_tipo_movimentacao(
    queryset,
    tipo_mov,
):
    """
    Traduz o filtro da tela para os tipos gravados no histórico.
    """

    tipo_mov = str(
        tipo_mov or ''
    ).strip().lower()

    if not tipo_mov:
        return queryset

    if tipo_mov in {
        'entrada',
        'entradas',
    }:
        return queryset.filter(
            _dashboard_q_entrada()
        )

    if tipo_mov in {
        'saida',
        'saída',
        'saidas',
        'saídas',
    }:
        return queryset.filter(
            _dashboard_q_saida()
        )

    if tipo_mov in {
        'expedicao',
        'expedição',
    }:
        return queryset.filter(
            Q(
                tipo__icontains=
                    'Expedição'
            )
            | Q(
                tipo__icontains=
                    'Expedicao'
            )
        )

    if tipo_mov in {
        'transferencia',
        'transferência',
    }:
        return queryset.filter(
            Q(
                tipo__icontains=
                    'Transferência'
            )
            | Q(
                tipo__icontains=
                    'Transferencia'
            )
        )

    return queryset.filter(
        tipo__icontains=
            tipo_mov
    )


def _dashboard_numero(valor):
    """
    Converte Decimal/int/None para float seguro.
    """
    try:
        return float(
            valor or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _dashboard_data_segura(
    valor,
):
    """
    Converte YYYY-MM-DD para date.
    Retorna None se inválido.
    """

    if not valor:
        return None

    try:
        return datetime.strptime(
            valor,
            '%Y-%m-%d',
        ).date()
    except ValueError:
        return None


def _dashboard_normalizar_carga(valor):
    """
    Normaliza o identificador da carga para agrupamento no dashboard.

    Exemplos que passam a representar a mesma carga:
    - 432
    - carga 432
    - CARGA-432
    - CARGA: 432
    """
    texto = str(valor or '').strip().upper()
    texto = texto.replace('-', ' ').replace(':', ' ')
    texto = ' '.join(texto.split())

    if not texto:
        return '', ''

    if texto.isdigit():
        numero = texto.lstrip('0') or '0'
        texto = f'CARGA {numero}'
    elif texto.startswith('CARGA'):
        restante = texto[5:].strip()
        if restante.isdigit():
            numero = restante.lstrip('0') or '0'
            texto = f'CARGA {numero}'

    return texto, texto


def _dashboard_q_expedicao():
    """Reconhece expedições com ou sem acento em históricos antigos."""
    return (
        Q(tipo__icontains='Expedição')
        | Q(tipo__icontains='Expedicao')
    )


def _dashboard_tipo_inclui_expedicao(tipo_mov):
    """
    Diz se o filtro de tipo atual permite exibir o bloco de expedições.
    'Saída' inclui expedição no dashboard; Entrada/Transferência não.
    """
    valor = str(tipo_mov or '').strip().lower()
    if not valor:
        return True
    return valor in {
        'saida', 'saída', 'saidas', 'saídas',
        'expedicao', 'expedição',
    }


# ================================================================
# API DO DASHBOARD
# ================================================================

@login_required
@permission_required(
    'sapp.pode_ver_estoque',
    raise_exception=True,
)
def dashboard_data(request):
    """
    Endpoint AJAX do Dashboard Analítico.

    Principais regras:
    - estoque atual usa saldo > 0;
    - histórico não é apagado da análise quando saldo zera;
    - gráfico de tendência usa quantidade movimentada;
    - saída inclui Saída, Transferência (Saída) e Expedição;
    - dias sem movimento aparecem como zero;
    - filtros disponíveis são encadeados.
    """

    try:
        # --------------------------------------------------------
        # PARÂMETROS
        # --------------------------------------------------------
        tipos_semente = (
            request.GET.getlist(
                'tipo_semente[]'
            )
        )

        cultivares = (
            request.GET.getlist(
                'cultivar[]'
            )
        )

        peneiras = (
            request.GET.getlist(
                'peneira[]'
            )
        )

        unidades = (
            request.GET.getlist(
                'unidade[]'
            )
        )

        armazens = (
            request.GET.getlist(
                'armazem[]'
            )
        )

        data_inicio = (
            _dashboard_data_segura(
                request.GET.get(
                    'data_inicio',
                    ''
                ).strip()
            )
        )

        data_fim = (
            _dashboard_data_segura(
                request.GET.get(
                    'data_fim',
                    ''
                ).strip()
            )
        )

        tipo_mov = (
            request.GET.get(
                'tipo_mov',
                ''
            ).strip()
        )

        search = (
            request.GET.get(
                'search',
                ''
            ).strip()
        )

        # Filtros exclusivos do quadro de Expedições / Carregamentos.
        # Eles não alteram os demais KPIs/gráficos do dashboard.
        exp_data_inicio = _dashboard_data_segura(
            request.GET.get('exp_data_inicio', '').strip()
        )
        exp_data_fim = _dashboard_data_segura(
            request.GET.get('exp_data_fim', '').strip()
        )
        exp_carga = request.GET.get('exp_carga', '').strip()
        exp_cliente = request.GET.get('exp_cliente', '').strip()
        exp_placa = request.GET.get('exp_placa', '').strip()
        exp_motorista = request.GET.get('exp_motorista', '').strip()
        exp_lote = request.GET.get('exp_lote', '').strip()

        try:
            periodo_dias = int(
                request.GET.get(
                    'periodo',
                    15,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            periodo_dias = 15

        periodo_dias = max(
            7,
            min(
                periodo_dias,
                90,
            ),
        )

        # --------------------------------------------------------
        # ESTOQUE ATUAL
        # --------------------------------------------------------
        est_qs = (
            Estoque.objects
            .select_related(
                'cultivar',
                'peneira',
                'especie',
            )
            .filter(
                saldo__gt=0
            )
        )

        est_qs = (
            _dashboard_aplicar_filtros_estoque(
                est_qs,
                tipos_semente=
                    tipos_semente,
                cultivares=
                    cultivares,
                peneiras=
                    peneiras,
                unidades=
                    unidades,
                armazens=
                    armazens,
                search=
                    search,
            )
        )

        # --------------------------------------------------------
        # HISTÓRICO
        # --------------------------------------------------------
        mov_qs = (
            HistoricoMovimentacao.objects
            .select_related(
                'estoque',
                'estoque__cultivar',
                'estoque__peneira',
                'estoque__especie',
                'usuario',
            )
            .all()
        )

        mov_qs = (
            _dashboard_aplicar_filtros_movimentacao(
                mov_qs,
                tipos_semente=
                    tipos_semente,
                cultivares=
                    cultivares,
                peneiras=
                    peneiras,
                unidades=
                    unidades,
                armazens=
                    armazens,
                search=
                    search,
            )
        )

        if data_inicio:
            mov_qs = mov_qs.filter(
                data_hora__date__gte=
                    data_inicio
            )

        if data_fim:
            mov_qs = mov_qs.filter(
                data_hora__date__lte=
                    data_fim
            )

        mov_qs_filtrado_tipo = (
            _dashboard_filtro_tipo_movimentacao(
                mov_qs,
                tipo_mov,
            )
        )

        # --------------------------------------------------------
        # KPIs
        # --------------------------------------------------------
        bags = (
            est_qs
            .filter(
                embalagem__iexact=
                    'BAG'
            )
            .aggregate(
                total=Sum('saldo')
            )['total']
            or 0
        )

        scs = (
            est_qs
            .filter(
                embalagem__iexact=
                    'SC'
            )
            .aggregate(
                total=Sum('saldo')
            )['total']
            or 0
        )

        # Regra utilizada no seu projeto:
        # 1 BAG = 25 SC.
        total_sc = (
            (bags * 25)
            + scs
        )

        peso = (
            est_qs
            .aggregate(
                total=Sum(
                    'peso_total'
                )
            )['total']
            or 0
        )

        limite_parado = (
            timezone.now()
            - timedelta(
                days=30
            )
        )

        parados = (
            est_qs
            .filter(
                Q(
                    data_ultima_movimentacao__lt=
                        limite_parado
                )
                | Q(
                    data_ultima_movimentacao__isnull=
                        True
                )
            )
            .count()
        )

        hoje = (
            timezone.localdate()
        )

        data_limite = (
            hoje
            - timedelta(
                days=
                    periodo_dias - 1
            )
        )

        tendencia_qs = (
            mov_qs
            .filter(
                data_hora__date__gte=
                    data_limite,
                data_hora__date__lte=
                    hoje,
            )
        )

        q_entrada = (
            _dashboard_q_entrada()
        )

        q_saida = (
            _dashboard_q_saida()
        )

        entradas_periodo = (
            tendencia_qs
            .filter(
                q_entrada
            )
            .aggregate(
                total=Sum(
                    'quantidade'
                )
            )['total']
            or 0
        )

        saidas_periodo = (
            tendencia_qs
            .filter(
                q_saida
            )
            .aggregate(
                total=Sum(
                    'quantidade'
                )
            )['total']
            or 0
        )

        kpis = {
            'total_sc': int(
                total_sc
            ),
            'bags': int(
                bags
            ),
            'scs': int(
                scs
            ),
            'peso': (
                _dashboard_numero(
                    peso
                )
            ),
            'ativos': (
                est_qs.count()
            ),
            'parados': (
                parados
            ),
            'entradas_periodo': (
                _dashboard_numero(
                    entradas_periodo
                )
            ),
            'saidas_periodo': (
                _dashboard_numero(
                    saidas_periodo
                )
            ),
            'eventos_periodo': (
                tendencia_qs.count()
            ),
            'periodo_dias': (
                periodo_dias
            ),
        }

        # --------------------------------------------------------
        # GRÁFICO CULTIVAR
        # --------------------------------------------------------
        cultivares_data = list(
            est_qs
            .filter(
                cultivar__isnull=False
            )
            .values(
                'cultivar__nome'
            )
            .annotate(
                volume=Sum(
                    'saldo'
                )
            )
            .filter(
                volume__gt=0
            )
            .order_by(
                '-volume'
            )[:10]
        )

        # --------------------------------------------------------
        # GRÁFICO PENEIRA
        # --------------------------------------------------------
        peneiras_data = list(
            est_qs
            .filter(
                peneira__isnull=False
            )
            .values(
                'peneira__nome'
            )
            .annotate(
                volume=Sum(
                    'saldo'
                )
            )
            .filter(
                volume__gt=0
            )
            .order_by(
                '-volume'
            )
        )

        # --------------------------------------------------------
        # GRÁFICO ARMAZÉM
        # --------------------------------------------------------
        armazens_data = list(
            est_qs
            .exclude(
                az__isnull=True
            )
            .exclude(
                az=''
            )
            .values(
                'az'
            )
            .annotate(
                volume=Sum(
                    'saldo'
                )
            )
            .filter(
                volume__gt=0
            )
            .order_by(
                'az'
            )
        )

        cores = [
            '#2f8f4e',
            '#3b82f6',
            '#f59e0b',
            '#ef4444',
            '#8b5cf6',
            '#06b6d4',
            '#84cc16',
            '#f97316',
            '#ec4899',
            '#6366f1',
            '#14b8a6',
            '#64748b',
        ]

        def cores_para(
            quantidade,
        ):
            if quantidade <= 0:
                return []

            repeticoes = (
                quantidade
                // len(cores)
                + 1
            )

            return (
                cores
                * repeticoes
            )[:quantidade]

        # --------------------------------------------------------
        # TENDÊNCIA POR DIA
        # --------------------------------------------------------
        tendencia_agregada = list(
            tendencia_qs
            .annotate(
                dia=TruncDate(
                    'data_hora'
                )
            )
            .values(
                'dia'
            )
            .annotate(
                entradas=Sum(
                    'quantidade',
                    filter=
                        q_entrada,
                ),
                saidas=Sum(
                    'quantidade',
                    filter=
                        q_saida,
                ),
                eventos=Count(
                    'id'
                ),
            )
            .order_by(
                'dia'
            )
        )

        tendencia_por_dia = {
            item['dia']: {
                'entradas': (
                    _dashboard_numero(
                        item[
                            'entradas'
                        ]
                    )
                ),
                'saidas': (
                    _dashboard_numero(
                        item[
                            'saidas'
                        ]
                    )
                ),
                'eventos': int(
                    item[
                        'eventos'
                    ]
                    or 0
                ),
            }
            for item
            in tendencia_agregada
        }

        labels_tendencia = []
        entradas_tendencia = []
        saidas_tendencia = []
        eventos_tendencia = []

        for indice in range(
            periodo_dias
        ):
            dia = (
                data_limite
                + timedelta(
                    days=indice
                )
            )

            valores = (
                tendencia_por_dia.get(
                    dia,
                    {
                        'entradas': 0,
                        'saidas': 0,
                        'eventos': 0,
                    },
                )
            )

            labels_tendencia.append(
                dia.strftime(
                    '%d/%m'
                )
            )

            entradas_tendencia.append(
                valores[
                    'entradas'
                ]
            )

            saidas_tendencia.append(
                valores[
                    'saidas'
                ]
            )

            eventos_tendencia.append(
                valores[
                    'eventos'
                ]
            )

        graficos = {
            'cultivar': {
                'labels': [
                    item[
                        'cultivar__nome'
                    ]
                    for item
                    in cultivares_data
                ],
                'values': [
                    _dashboard_numero(
                        item[
                            'volume'
                        ]
                    )
                    for item
                    in cultivares_data
                ],
                'colors': cores_para(
                    len(
                        cultivares_data
                    )
                ),
            },

            'peneira': {
                'labels': [
                    item[
                        'peneira__nome'
                    ]
                    for item
                    in peneiras_data
                ],
                'values': [
                    _dashboard_numero(
                        item[
                            'volume'
                        ]
                    )
                    for item
                    in peneiras_data
                ],
                'colors': cores_para(
                    len(
                        peneiras_data
                    )
                ),
            },

            'armazem': {
                'labels': [
                    item[
                        'az'
                    ]
                    for item
                    in armazens_data
                ],
                'values': [
                    _dashboard_numero(
                        item[
                            'volume'
                        ]
                    )
                    for item
                    in armazens_data
                ],
                'colors': cores_para(
                    len(
                        armazens_data
                    )
                ),
            },

            'tendencia': {
                'labels': (
                    labels_tendencia
                ),
                'entradas': (
                    entradas_tendencia
                ),
                'saidas': (
                    saidas_tendencia
                ),
                'eventos': (
                    eventos_tendencia
                ),
            },
        }

        # --------------------------------------------------------
        # OPÇÕES DE FILTROS ENCADEADOS
        # --------------------------------------------------------
        def estoque_para_opcao(
            ignorar,
        ):
            return (
                _dashboard_aplicar_filtros_estoque(
                    Estoque.objects
                    .filter(
                        saldo__gt=0
                    ),
                    tipos_semente=(
                        []
                        if ignorar == 'tipo'
                        else tipos_semente
                    ),
                    cultivares=(
                        []
                        if ignorar == 'cultivar'
                        else cultivares
                    ),
                    peneiras=(
                        []
                        if ignorar == 'peneira'
                        else peneiras
                    ),
                    unidades=(
                        []
                        if ignorar == 'unidade'
                        else unidades
                    ),
                    armazens=(
                        []
                        if ignorar == 'armazem'
                        else armazens
                    ),
                    search=search,
                )
            )

        qs_tipo = (
            estoque_para_opcao(
                'tipo'
            )
        )

        qs_cultivar = (
            estoque_para_opcao(
                'cultivar'
            )
        )

        qs_peneira = (
            estoque_para_opcao(
                'peneira'
            )
        )

        qs_unidade = (
            estoque_para_opcao(
                'unidade'
            )
        )

        qs_armazem = (
            estoque_para_opcao(
                'armazem'
            )
        )

        opcoes_filtros = {
            'tipos_semente': list(
                qs_tipo
                .exclude(
                    especie__isnull=True
                )
                .exclude(
                    especie__nome=''
                )
                .values_list(
                    'especie__nome',
                    flat=True,
                )
                .distinct()
                .order_by(
                    'especie__nome'
                )
            ),

            'cultivares': list(
                qs_cultivar
                .filter(
                    cultivar__isnull=False
                )
                .values(
                    'cultivar_id',
                    'cultivar__nome',
                )
                .distinct()
                .order_by(
                    'cultivar__nome'
                )
            ),

            'peneiras': list(
                qs_peneira
                .filter(
                    peneira__isnull=False
                )
                .values(
                    'peneira_id',
                    'peneira__nome',
                )
                .distinct()
                .order_by(
                    'peneira__nome'
                )
            ),

            'unidades': list(
                qs_unidade
                .exclude(
                    embalagem__isnull=True
                )
                .exclude(
                    embalagem=''
                )
                .values_list(
                    'embalagem',
                    flat=True,
                )
                .distinct()
                .order_by(
                    'embalagem'
                )
            ),

            'armazens': list(
                qs_armazem
                .exclude(
                    az__isnull=True
                )
                .exclude(
                    az=''
                )
                .values_list(
                    'az',
                    flat=True,
                )
                .distinct()
                .order_by(
                    'az'
                )
            ),
        }

        # --------------------------------------------------------
        # EXPEDIÇÕES / CARREGAMENTOS
        # --------------------------------------------------------
        # O período acompanha o seletor do dashboard quando não há
        # datas explícitas. Se o usuário escolher datas, elas prevalecem.
        expedicao_inicio = exp_data_inicio or data_inicio or data_limite
        expedicao_fim = exp_data_fim or data_fim or hoje

        expedicoes_qs = (
            mov_qs
            .filter(
                _dashboard_q_expedicao(),
                data_hora__date__gte=expedicao_inicio,
                data_hora__date__lte=expedicao_fim,
            )
            .order_by('-data_hora', '-id')
        )

        # Respeita também o filtro "Tipo movimentação" do dashboard.
        if not _dashboard_tipo_inclui_expedicao(tipo_mov):
            expedicoes_qs = expedicoes_qs.none()

        # Filtros específicos da área de expedição.
        if exp_cliente:
            expedicoes_qs = expedicoes_qs.filter(
                Q(cliente__icontains=exp_cliente)
                | Q(estoque__cliente__icontains=exp_cliente)
            )

        if exp_placa:
            expedicoes_qs = expedicoes_qs.filter(
                placa__icontains=exp_placa
            )

        if exp_motorista:
            expedicoes_qs = expedicoes_qs.filter(
                motorista__icontains=exp_motorista
            )

        if exp_lote:
            expedicoes_qs = expedicoes_qs.filter(
                Q(lote_ref__icontains=exp_lote)
                | Q(estoque__lote__icontains=exp_lote)
            )

        if exp_carga:
            # Aceita procurar tanto por "432" quanto por "CARGA 432".
            _, carga_normalizada = _dashboard_normalizar_carga(exp_carga)
            termos_carga = {exp_carga}
            if carga_normalizada:
                termos_carga.add(carga_normalizada)
                if carga_normalizada.startswith('CARGA '):
                    termos_carga.add(carga_normalizada.split(' ', 1)[1])

            filtro_carga = Q()
            for termo_carga in termos_carga:
                termo_carga = str(termo_carga or '').strip()
                if termo_carga:
                    filtro_carga |= (
                        Q(numero_carga__icontains=termo_carga)
                        | Q(nome_carga_avulsa__icontains=termo_carga)
                    )

            if filtro_carga:
                expedicoes_qs = expedicoes_qs.filter(filtro_carga)

        cargas_agrupadas = {}
        dias_expedicao = defaultdict(
            lambda: {
                'equivalente_sc': Decimal('0'),
                'bags': Decimal('0'),
                'scs': Decimal('0'),
                'cargas': set(),
                'origens': set(),
            }
        )
        placas_unicas = set()
        total_baixas_expedicao = 0
        volume_expedido = Decimal('0')
        total_bag_expedido = Decimal('0')
        total_sc_expedido = Decimal('0')
        total_outros_expedido = Decimal('0')
        total_equivalente_sc = Decimal('0')

        # Compatibilidade com expedições GERADAS registradas em versões
        # anteriores: alguns históricos guardavam no numero_carga um texto
        # digitado no modal (por exemplo, uma data) e não o título oficial do
        # card. O HistoricoItemEmpenho mantém o vínculo com a Solicitação e é
        # usado aqui somente para recuperar a identidade correta sem alterar o
        # histórico antigo no banco.
        gerada_por_chave_exata = {}
        gerada_por_chave_base = defaultdict(set)
        historicos_itens_gerados = (
            HistoricoItemEmpenho.objects
            .filter(
                tipo='expedicao',
                processado_em__date__gte=expedicao_inicio,
                processado_em__date__lte=expedicao_fim,
                empenho__solicitacao__tipo_solicitacao='CARGA',
            )
            .select_related('empenho__solicitacao')
            .only(
                'estoque_origem_id', 'quantidade', 'processado_por_id',
                'processado_em', 'numero_carga',
                'empenho__solicitacao__titulo',
                'empenho__solicitacao__tipo_solicitacao',
            )
        )
        for hist_item in historicos_itens_gerados:
            solicitacao_hist = getattr(hist_item.empenho, 'solicitacao', None)
            titulo_oficial = str(getattr(solicitacao_hist, 'titulo', '') or '').strip()
            if not titulo_oficial or not hist_item.processado_em:
                continue
            data_hist = timezone.localtime(hist_item.processado_em).date()
            chave_base_hist = (
                hist_item.estoque_origem_id,
                int(hist_item.quantidade or 0),
                hist_item.processado_por_id,
                data_hist,
            )
            numero_hist = normalizar_texto_cadastro(hist_item.numero_carga or '')
            if numero_hist:
                gerada_por_chave_exata[chave_base_hist + (numero_hist,)] = titulo_oficial
            gerada_por_chave_base[chave_base_hist].add(titulo_oficial)

        for mov in expedicoes_qs:
            origem_carga = str(getattr(mov, 'origem_carga', '') or '').strip().upper()
            nome_avulsa = ' '.join(str(getattr(mov, 'nome_carga_avulsa', '') or '').strip().split())
            numero_carga_mov = str(getattr(mov, 'numero_carga', '') or '').strip()

            # Se não é uma avulsa explicitamente identificada, tenta recuperar
            # o card CARGA N que originou esta baixa. Isso corrige a exibição de
            # dados antigos e faz 3 lotes da mesma carga aparecerem como UMA
            # carga com 3 lotes.
            if origem_carga != 'AVULSA' and not nome_avulsa and mov.data_hora:
                data_mov_hist = timezone.localtime(mov.data_hora).date()
                chave_base_mov = (
                    mov.estoque_id,
                    int(mov.quantidade or 0),
                    mov.usuario_id,
                    data_mov_hist,
                )
                numero_mov_norm = normalizar_texto_cadastro(numero_carga_mov)
                titulo_oficial = None
                if numero_mov_norm:
                    titulo_oficial = gerada_por_chave_exata.get(
                        chave_base_mov + (numero_mov_norm,)
                    )
                if not titulo_oficial:
                    titulos_possiveis = gerada_por_chave_base.get(chave_base_mov, set())
                    if len(titulos_possiveis) == 1:
                        titulo_oficial = next(iter(titulos_possiveis))
                if titulo_oficial:
                    origem_carga = 'GERADA'
                    numero_carga_mov = titulo_oficial

            # Avulsa: o NOME é a identidade operacional. Várias baixas com o
            # mesmo nome normalizado formam uma única carga, mesmo que o número
            # humano se repita em uma carga GERADA.
            if origem_carga == 'AVULSA' and nome_avulsa:
                chave_nome = normalizar_texto_cadastro(nome_avulsa)
                chave_carga = f'AVULSA:NOME:{chave_nome}'
                nome_carga = nome_avulsa
            else:
                chave_carga, nome_carga = _dashboard_normalizar_carga(
                    numero_carga_mov
                )
                if origem_carga == 'AVULSA' and chave_carga:
                    chave_carga = f'AVULSA:NUM:{chave_carga}'

            # Sem nome/número não é seguro unir duas avulsas distintas.
            if not chave_carga:
                chave_carga = f'AVULSA:{mov.id}'
                nome_carga = nome_avulsa or 'AVULSA'

            quantidade_mov = Decimal(
                str(getattr(mov, 'quantidade', 0) or 0)
            )

            # A embalagem vem do lote movimentado. Esta é a mesma regra
            # de conversão já utilizada no dashboard geral do projeto:
            # 1 BAG = 25 SC; cada SC físico = 1 SC equivalente.
            unidade_mov = str(
                getattr(mov.estoque, 'embalagem', '')
                if mov.estoque
                else ''
            ).strip().upper()
            if unidade_mov not in ('BAG', 'SC'):
                unidade_mov = 'UN'

            if unidade_mov == 'BAG':
                equivalente_sc_mov = quantidade_mov * Decimal('25')
                total_bag_expedido += quantidade_mov
            elif unidade_mov == 'SC':
                equivalente_sc_mov = quantidade_mov
                total_sc_expedido += quantidade_mov
            else:
                equivalente_sc_mov = Decimal('0')
                total_outros_expedido += quantidade_mov

            total_equivalente_sc += equivalente_sc_mov

            # Para o gráfico de vários dias, o volume é atribuído ao dia
            # real de cada movimentação. Assim uma carga com vários lotes
            # não perde o histórico diário por ter sido agrupada no resumo.
            if mov.data_hora:
                data_local_mov = timezone.localtime(mov.data_hora).date()
                dia_mov = dias_expedicao[data_local_mov]
                dia_mov['equivalente_sc'] += equivalente_sc_mov
                if unidade_mov == 'BAG':
                    dia_mov['bags'] += quantidade_mov
                elif unidade_mov == 'SC':
                    dia_mov['scs'] += quantidade_mov
                dia_mov['cargas'].add(chave_carga)
                dia_mov['origens'].add(
                    origem_carga or ('AVULSA' if nome_avulsa else 'GERADA')
                )

            lote_mov = (
                mov.lote_ref
                or (mov.estoque.lote if mov.estoque else '')
                or '--'
            )

            placa_mov = ' '.join(
                str(mov.placa or '').strip().upper().split()
            )
            motorista_mov = ' '.join(
                str(mov.motorista or '').strip().split()
            )
            cliente_mov = ' '.join(
                str(mov.cliente or '').strip().split()
            )

            if placa_mov:
                placas_unicas.add(placa_mov)

            grupo = cargas_agrupadas.setdefault(
                chave_carga,
                {
                    'carga': nome_carga,
                    'origem': origem_carga or ('AVULSA' if nome_avulsa else 'GERADA'),
                    'numero_carga': numero_carga_mov,
                    'data_hora': mov.data_hora,
                    'qtd': Decimal('0'),
                    'qtd_bag': Decimal('0'),
                    'qtd_sc': Decimal('0'),
                    'qtd_outros': Decimal('0'),
                    'equivalente_sc': Decimal('0'),
                    'baixas': 0,
                    'lotes': {},
                    'placas': set(),
                    'motoristas': set(),
                    'clientes': set(),
                },
            )

            # Como o queryset está do mais novo para o mais antigo,
            # a primeira data já representa a última baixa da carga.
            grupo['qtd'] += quantidade_mov
            grupo['equivalente_sc'] += equivalente_sc_mov
            grupo['baixas'] += 1

            if unidade_mov == 'BAG':
                grupo['qtd_bag'] += quantidade_mov
            elif unidade_mov == 'SC':
                grupo['qtd_sc'] += quantidade_mov
            else:
                grupo['qtd_outros'] += quantidade_mov

            # O mesmo lote pode aparecer em mais de uma movimentação.
            # A unidade faz parte da chave para nunca somar BAG e SC
            # como se fossem a mesma grandeza.
            lote_chave = (lote_mov, unidade_mov)
            lote_info = grupo['lotes'].setdefault(
                lote_chave,
                {
                    'lote': lote_mov,
                    'unidade': unidade_mov,
                    'qtd': Decimal('0'),
                    'equivalente_sc': Decimal('0'),
                },
            )
            lote_info['qtd'] += quantidade_mov
            lote_info['equivalente_sc'] += equivalente_sc_mov

            if placa_mov:
                grupo['placas'].add(placa_mov)
            if motorista_mov:
                grupo['motoristas'].add(motorista_mov)
            if cliente_mov:
                grupo['clientes'].add(cliente_mov)

            total_baixas_expedicao += 1
            volume_expedido += quantidade_mov

        cargas_lista = []
        total_lotes_nas_cargas = 0
        cargas_multiplas_baixas = 0

        for grupo in cargas_agrupadas.values():
            lotes = [
                {
                    'lote': info_lote['lote'],
                    'unidade': info_lote['unidade'],
                    'qtd': _dashboard_numero(info_lote['qtd']),
                    'equivalente_sc': _dashboard_numero(
                        info_lote['equivalente_sc']
                    ),
                }
                for _, info_lote in sorted(
                    grupo['lotes'].items(),
                    key=lambda item: (str(item[0][0]), str(item[0][1])),
                )
            ]

            total_lotes_nas_cargas += len(lotes)
            if grupo['baixas'] > 1:
                cargas_multiplas_baixas += 1

            data_local_carga = (
                timezone.localtime(grupo['data_hora'])
                if grupo['data_hora']
                else None
            )

            cargas_lista.append({
                'carga': grupo['carga'],
                'origem': grupo.get('origem') or 'GERADA',
                'numero_carga': grupo.get('numero_carga') or '',
                'dt': (
                    data_local_carga.strftime('%d/%m/%Y')
                    if data_local_carga
                    else '--'
                ),
                'data_iso': (
                    data_local_carga.strftime('%Y-%m-%d')
                    if data_local_carga
                    else ''
                ),
                'qtd': _dashboard_numero(grupo['qtd']),
                'qtd_bag': _dashboard_numero(grupo['qtd_bag']),
                'qtd_sc': _dashboard_numero(grupo['qtd_sc']),
                'qtd_outros': _dashboard_numero(grupo['qtd_outros']),
                'equivalente_sc': _dashboard_numero(
                    grupo['equivalente_sc']
                ),
                'baixas': int(grupo['baixas']),
                'lotes': lotes,
                'placa': ' / '.join(sorted(grupo['placas'])) or '--',
                'motorista': ' / '.join(sorted(grupo['motoristas'])) or '--',
                'cliente': ' / '.join(sorted(grupo['clientes'])) or '--',
            })

        # --------------------------------------------------------
        # GRÁFICO DINÂMICO DE EXPEDIÇÃO
        # --------------------------------------------------------
        # 1 dia  -> compara as cargas daquele dia.
        # >1 dia -> consolida o volume equivalente em SC por data.
        # O gráfico usa todas as cargas filtradas, não apenas as 30
        # exibidas na tabela.
        grafico_modo = (
            'cargas'
            if expedicao_inicio == expedicao_fim
            else 'dias'
        )

        grafico_labels = []
        grafico_valores = []
        grafico_bags = []
        grafico_scs = []
        grafico_cargas_qtd = []
        grafico_detalhes = []

        if grafico_modo == 'cargas':
            cargas_grafico = sorted(
                cargas_lista,
                key=lambda item: (
                    item.get('data_iso', ''),
                    str(item.get('carga', '')),
                ),
            )

            for carga_item in cargas_grafico:
                grafico_labels.append(carga_item['carga'])
                grafico_valores.append(carga_item['equivalente_sc'])
                grafico_bags.append(carga_item['qtd_bag'])
                grafico_scs.append(carga_item['qtd_sc'])
                grafico_cargas_qtd.append(1)
                grafico_detalhes.append({
                    'carga': carga_item['carga'],
                    'origem': carga_item.get('origem') or 'GERADA',
                    'placa': carga_item['placa'],
                    'cliente': carga_item['cliente'],
                    'bags': carga_item['qtd_bag'],
                    'scs': carga_item['qtd_sc'],
                    'equivalente_sc': carga_item['equivalente_sc'],
                })
        else:
            # Inclui também dias sem carregamento para o gráfico refletir
            # fielmente todo o intervalo escolhido pelo usuário.
            cursor_dia = expedicao_inicio
            while cursor_dia <= expedicao_fim:
                dia_info = dias_expedicao[cursor_dia]
                grafico_labels.append(cursor_dia.strftime('%d/%m'))
                grafico_valores.append(
                    _dashboard_numero(dia_info['equivalente_sc'])
                )
                grafico_bags.append(_dashboard_numero(dia_info['bags']))
                grafico_scs.append(_dashboard_numero(dia_info['scs']))
                grafico_cargas_qtd.append(len(dia_info['cargas']))
                grafico_detalhes.append({
                    'data': cursor_dia.strftime('%d/%m/%Y'),
                    'cargas': len(dia_info['cargas']),
                    'origens': sorted(dia_info['origens']),
                    'bags': _dashboard_numero(dia_info['bags']),
                    'scs': _dashboard_numero(dia_info['scs']),
                    'equivalente_sc': _dashboard_numero(
                        dia_info['equivalente_sc']
                    ),
                })
                cursor_dia += timedelta(days=1)

        total_cargas_grafico = len(cargas_agrupadas)
        dias_periodo = max(
            1,
            (expedicao_fim - expedicao_inicio).days + 1,
        )
        dias_com_carga = sum(
            1
            for data_dia, info_dia in dias_expedicao.items()
            if (
                expedicao_inicio <= data_dia <= expedicao_fim
                and bool(info_dia['cargas'])
            )
        )

        media_por_carga_sc = (
            total_equivalente_sc / Decimal(total_cargas_grafico)
            if total_cargas_grafico
            else Decimal('0')
        )
        media_por_dia_sc = (
            total_equivalente_sc / Decimal(dias_periodo)
            if dias_periodo
            else Decimal('0')
        )

        maior_carga = None
        if cargas_lista:
            maior_carga = max(
                cargas_lista,
                key=lambda item: Decimal(
                    str(item.get('equivalente_sc', 0) or 0)
                ),
            )

        dia_pico_label = '--'
        dia_pico_sc = Decimal('0')
        if grafico_modo == 'dias' and grafico_valores:
            indice_pico = max(
                range(len(grafico_valores)),
                key=lambda idx: Decimal(
                    str(grafico_valores[idx] or 0)
                ),
            )
            if grafico_detalhes[indice_pico].get('data'):
                dia_pico_label = grafico_detalhes[indice_pico]['data']
            dia_pico_sc = Decimal(
                str(grafico_valores[indice_pico] or 0)
            )

        grafico_expedicao = {
            'modo': grafico_modo,
            'titulo': (
                f'Cargas carregadas em {expedicao_inicio.strftime("%d/%m/%Y")}'
                if grafico_modo == 'cargas'
                else 'Volume carregado por dia'
            ),
            'subtitulo': (
                'Comparativo do equivalente em sacos (SC) por carga.'
                if grafico_modo == 'cargas'
                else 'Volume equivalente em sacos (SC) dentro do período filtrado.'
            ),
            'labels': grafico_labels,
            'valores': grafico_valores,
            'bags': grafico_bags,
            'scs': grafico_scs,
            'cargas_qtd': grafico_cargas_qtd,
            'detalhes': grafico_detalhes,
            'resumo': {
                'cargas': total_cargas_grafico,
                'equivalente_sc': _dashboard_numero(total_equivalente_sc),
                'bags': _dashboard_numero(total_bag_expedido),
                'scs': _dashboard_numero(total_sc_expedido),
                'media_por_carga_sc': _dashboard_numero(media_por_carga_sc),
                'media_por_dia_sc': _dashboard_numero(media_por_dia_sc),
                'dias_periodo': dias_periodo,
                'dias_com_carga': dias_com_carga,
                'maior_carga': (
                    maior_carga['carga']
                    if maior_carga
                    else '--'
                ),
                'maior_carga_sc': (
                    maior_carga['equivalente_sc']
                    if maior_carga
                    else 0
                ),
                'dia_pico': dia_pico_label,
                'dia_pico_sc': _dashboard_numero(dia_pico_sc),
            },
        }

        # Os KPIs consideram TODAS as cargas do período. A interface faz
        # paginação visual de 10 por vez para não criar uma lista gigante.
        expedicoes = {
            'resumo': {
                'cargas': len(cargas_agrupadas),
                'volume': _dashboard_numero(volume_expedido),
                'bags': _dashboard_numero(total_bag_expedido),
                'scs': _dashboard_numero(total_sc_expedido),
                'outros': _dashboard_numero(total_outros_expedido),
                'equivalente_sc': _dashboard_numero(total_equivalente_sc),
                'lotes': int(total_lotes_nas_cargas),
                'placas': len(placas_unicas),
                'baixas': int(total_baixas_expedicao),
                'multiplas_baixas': int(cargas_multiplas_baixas),
            },
            'periodo': {
                'inicio': expedicao_inicio.strftime('%d/%m/%Y'),
                'fim': expedicao_fim.strftime('%d/%m/%Y'),
            },
            'grafico': grafico_expedicao,
            'cargas': cargas_lista,
        }

        # --------------------------------------------------------
        # MOVIMENTAÇÕES RECENTES
        # --------------------------------------------------------
        movimentacoes = []

        recentes_qs = (
            mov_qs_filtrado_tipo
            .order_by(
                '-data_hora'
            )[:12]
        )

        for mov in recentes_qs:
            estoque = mov.estoque

            lote = (
                mov.lote_ref
                or (
                    estoque.lote
                    if estoque
                    else ''
                )
                or '--'
            )

            unidade = (
                (
                    estoque.embalagem
                    if estoque
                    else ''
                )
                or '--'
            )

            if mov.usuario:
                usuario = (
                    mov.usuario.get_full_name()
                    or mov.usuario.username
                )
            else:
                usuario = 'Sistema'

            movimentacoes.append({
                'dt': (
                    timezone.localtime(
                        mov.data_hora
                    ).strftime(
                        '%d/%m/%Y %H:%M'
                    )
                    if mov.data_hora
                    else '--'
                ),
                'tp': (
                    mov.tipo
                    or '--'
                ),
                'lt': lote,
                'unidade': unidade,
                'qtd': (
                    _dashboard_numero(
                        getattr(
                            mov,
                            'quantidade',
                            0,
                        )
                    )
                ),
                'us': usuario,
            })

        return JsonResponse({
            'success': True,
            'kpis': kpis,
            'graficos': graficos,
            'expedicoes': expedicoes,
            'recentes': movimentacoes,
            'opcoes_filtros': (
                opcoes_filtros
            ),
        })

    except Exception as erro:
        import traceback

        traceback.print_exc()

        return JsonResponse(
            {
                'success': False,
                'error': str(
                    erro
                ),
            },
            status=500,
        )

################################################## fim dashbord ##################
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Estoque, Produto, ConfiguracaoLogo
import re

@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
def ficha_rastreabilidade_por_id(request, estoque_id):
    """
    View para exibir ficha de rastreabilidade por ID do estoque
    URL: /ficha-rastreabilidade/<int:estoque_id>/
    """
    try:
        item = get_object_or_404(Estoque, id=estoque_id)
        
        item_data = {
            'lote': item.lote,
            'safra': extrair_safra(item.lote),
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)  # CORRIGIDO
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
                    'safra': extrair_safra(item.lote),
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
@permission_required('sapp.pode_movimentar_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_mapa', raise_exception=True)
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
@permission_required('sapp.pode_ver_mapa', raise_exception=True) 
def api_marcacoes_ultimo_lote(request):
    """
    Retorna todas as posições que devem receber marcação de X
    (posições posteriores à posição marcada como último lote)
    """
    try:
        from .models import ArmazemLayout, ElementoMapa
        
        armazem_numero = request.GET.get('armazem', 1)
        mapa_atual = get_object_or_404(
            ArmazemLayout,
            numero=armazem_numero,
            ativo=True,
        )
        nomes_possiveis = [
            str(mapa_atual.nome).strip(),
            f'ARMAZEM {mapa_atual.numero}',
            f'ARMAZÉM {mapa_atual.numero}',
            f'AZ {mapa_atual.numero}',
            f'AZ{mapa_atual.numero}',
        ]
        armazem_cadastro = next((
            cadastro
            for nome in nomes_possiveis
            for cadastro in [Armazem.objects.filter(nome__iexact=nome).first()]
            if cadastro
        ), None)
        elementos_mapa = ElementoMapa.objects.filter(
            armazem=mapa_atual,
            tipo='RETANGULO',
        )
        enderecos_mapa = list(
            elementos_mapa.exclude(identificador__isnull=True)
            .exclude(identificador='')
            .values_list('identificador', flat=True)
        )
        if armazem_cadastro:
            enderecos_permitidos = list(
                Endereco.objects.filter(armazem=armazem_cadastro)
                .values_list('codigo', flat=True)
            )
        else:
            enderecos_permitidos = enderecos_mapa

        # Buscar somente os lotes marcados pertencentes ao armazém aberto.
        enderecos_permitidos_normalizados = {
            str(codigo).strip().upper()
            for codigo in enderecos_permitidos
            if codigo
        }
        lotes_marcados = Estoque.objects.filter(
            ultimo_lote_linha=True,
            saldo__gt=0,
        )
        
        marcacoes = {}
        
        for lote in lotes_marcados:
            if not lote.endereco or lote.endereco.strip().upper() not in enderecos_permitidos_normalizados:
                continue
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
            elementos = elementos_mapa.filter(
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)  # Mude
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
    

def validar_edicao_empenho_solicitacao(solicitacao):
    """
    Impede criação, alteração ou remoção de empenho
    depois que a movimentação da solicitação começou.
    """

    status_bloqueados = {
        'MOVIMENTACAO_PARCIAL',
        'CONCLUIDO',
        'CANCELADO',
    }

    if solicitacao.status in status_bloqueados:
        raise ValueError(
            'Não é possível alterar o empenho porque '
            'a movimentação desta solicitação já foi iniciada.'
        )

    quantidade_movimentada = Decimal(
        str(
            solicitacao.quantidade_movimentada
            or 0
        )
    )

    if quantidade_movimentada > 0:
        raise ValueError(
            'Não é possível alterar o empenho porque '
            'esta solicitação já possui itens movimentados.'
        )


@login_required
@permission_required('sapp.pode_ver_estoque', raise_exception=True)
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True) 
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
@permission_required('sapp.pode_ver_estoque', raise_exception=True)  # Mude
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




# sapp/views.py - Adicione ou substitua esta função

@login_required
def redirecionar_usuario(request):
    """
    Envia o usuário para a primeira tela que ele realmente pode acessar.

    Importante: o login usa esta view como LOGIN_REDIRECT_URL. Assim um
    usuário sem Dashboard, mas com Estoque/Solicitações/Almoxarifado, não
    cai em uma página proibida logo depois de autenticar.
    """
    user = request.user

    if user.is_superuser:
        return redirect('sapp:dashboard')

    # Almoxarifado
    if (
        user.has_perm('almoxarifado.pode_ver_almoxarifado')
        or user.has_perm('almoxarifado.pode_gerenciar_almoxarifado')
    ):
        return redirect('almoxarifado:lista_itens')

    # Solicitações / empenho
    if user.has_perm('sapp.pode_ver_empenhos'):
        return redirect('sapp:pagina_solicitacoes')

    if user.has_perm('sapp.pode_criar_solicitacao'):
        return redirect('sapp:criar_solicitacao')

    if (
        user.has_perm('sapp.pode_empenhar_solicitacao')
        or user.has_perm('sapp.pode_movimentar_solicitacao')
        or user.has_perm('sapp.pode_cancelar_solicitacao')
        or user.has_perm('sapp.pode_criar_empenhos')
    ):
        return redirect('sapp:pagina_kanban')

    # Estoque
    if user.has_perm('sapp.pode_ver_estoque'):
        return redirect('sapp:lista_estoque')

    if user.has_perm('sapp.pode_movimentar_estoque'):
        return redirect('sapp:gestao_estoque')

    # Mapa
    if user.has_perm('sapp.pode_ver_mapa'):
        return redirect('sapp:mapa_canvas', armazem_numero=1)

    # Dashboard
    if user.has_perm('sapp.pode_ver_dashboard'):
        return redirect('sapp:dashboard')

    # Configuração do sistema
    if user.has_perm('sapp.pode_configuracoes'):
        return redirect('sapp:configuracoes')

    # Nenhuma permissão de navegação válida.
    from django.contrib.auth import logout
    messages.error(
        request,
        'Sua conta está ativa, mas ainda não possui permissão de acesso. '
        'Peça a um administrador para revisar suas permissões.'
    )
    logout(request)
    return redirect('sapp:login')



# sapp/views.py - Exportação SEM saldo 0

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from .models import Estoque
from datetime import datetime
from django.db.models import Q

def exportar_estoque_excel(request):
    """Exporta o estoque para Excel com os filtros aplicados (apenas saldo > 0)"""
    
    try:
        # Cria o workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Estoque"
        
        # Estilos
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='2F8F4E', end_color='2F8F4E', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        cell_font = Font(name='Arial', size=10)
        cell_alignment = Alignment(vertical='center')
        
        thin_border = Border(
            left=Side(style='thin', color='D3D3D3'),
            right=Side(style='thin', color='D3D3D3'),
            top=Side(style='thin', color='D3D3D3'),
            bottom=Side(style='thin', color='D3D3D3')
        )
        
        # Cabeçalhos
        headers = [
            'Status', 'AZ', 'Lote', 'Produto', 'Cultivar', 'Peneira', 
            'Categoria', 'Endereço', 'Saldo', 'Peso Unit.', 'Peso Total',
            'Espécie', 'Tratamento', 'Embalagem', 'Cliente', 'Empresa', 
            'Conferente', 'Observação'
        ]
        
        # Aplica estilos nos cabeçalhos
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Query base - FILTRA APENAS SALDO > 0
        queryset = Estoque.objects.select_related(
            'cultivar', 'peneira', 'categoria', 'tratamento', 
            'especie', 'status_sistemico', 'conferente'
        ).filter(saldo__gt=0)  # 🔥 AQUI: Apenas itens com saldo maior que 0
        
        # Aplica busca
        busca = request.GET.get('busca', '')
        if busca:
            queryset = queryset.filter(
                Q(lote__icontains=busca) |
                Q(produto__icontains=busca) |
                Q(endereco__icontains=busca) |
                Q(cliente__icontains=busca) |
                Q(empresa__icontains=busca) |
                Q(az__icontains=busca) |
                Q(observacao__icontains=busca) |
                Q(conferente__username__icontains=busca) |
                Q(conferente__first_name__icontains=busca) |
                Q(conferente__last_name__icontains=busca)
            )
        
        # Aplica filtros de coluna (exceto page, page_size, busca, export)
        for key, values in request.GET.lists():
            if key in ['page', 'page_size', 'busca', 'export']:
                continue
            
            # Filtros numéricos
            if key.startswith('min_'):
                campo = key.replace('min_', '')
                for val in values:
                    if val:
                        try:
                            queryset = queryset.filter(**{f"{campo}__gte": float(val)})
                        except (ValueError, TypeError):
                            pass
                continue
            
            if key.startswith('max_'):
                campo = key.replace('max_', '')
                for val in values:
                    if val:
                        try:
                            queryset = queryset.filter(**{f"{campo}__lte": float(val)})
                        except (ValueError, TypeError):
                            pass
                continue
            
            # Filtros de seleção múltipla
            if values and values != ['']:
                filtro_q = Q()
                for valor in values:
                    if valor == '__null__':
                        # Filtra por valores vazios/nulos
                        if key in ['cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'status_sistemico']:
                            filtro_q |= Q(**{f"{key}__isnull": True})
                        else:
                            filtro_q |= Q(**{f"{key}__exact": ''}) | Q(**{f"{key}__isnull": True})
                    else:
                        # Mapeia campos relacionados
                        if key == 'cultivar':
                            filtro_q |= Q(cultivar__nome=valor)
                        elif key == 'peneira':
                            filtro_q |= Q(peneira__nome=valor)
                        elif key == 'categoria':
                            filtro_q |= Q(categoria__nome=valor)
                        elif key == 'tratamento':
                            filtro_q |= Q(tratamento__nome=valor)
                        elif key == 'especie':
                            filtro_q |= Q(especie__nome=valor)
                        elif key == 'status_sistemico':
                            filtro_q |= Q(status_sistemico__nome=valor)
                        elif key == 'conferente':
                            filtro_q |= Q(conferente__username=valor)
                        else:
                            filtro_q |= Q(**{key: valor})
                
                queryset = queryset.filter(filtro_q)
        
        # Ordena
        queryset = queryset.order_by('lote')
        
        total_registros = queryset.count()
        print(f"📊 Exportando {total_registros} registros (apenas saldo > 0)")
        
        # Preenche os dados
        for row_idx, item in enumerate(queryset, 2):
            # Nome do conferente
            nome_conferente = ''
            if item.conferente:
                nome_conferente = item.conferente.get_full_name().strip()
                if not nome_conferente:
                    nome_conferente = item.conferente.first_name.strip()
                if not nome_conferente:
                    nome_conferente = item.conferente.username
            
            # Nome do status
            nome_status = item.status_sistemico.nome if item.status_sistemico else 'Indefinido'
            
            data_row = [
                nome_status,
                item.az or '',
                item.lote or '',
                item.produto or '',
                item.cultivar.nome if item.cultivar else '',
                item.peneira.nome if item.peneira else '',
                item.categoria.nome if item.categoria else '',
                item.endereco or '',
                item.saldo if item.saldo is not None else 0,
                float(item.peso_unitario) if item.peso_unitario else 0.0,
                float(item.peso_total) if item.peso_total else 0.0,
                item.especie.nome if item.especie else '',
                item.tratamento.nome if item.tratamento else '',
                item.get_embalagem_display() if item.embalagem else '',
                item.cliente or '',
                item.empresa or '',
                nome_conferente,
                item.observacao or '',
            ]
            
            for col, value in enumerate(data_row, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.font = cell_font
                cell.alignment = cell_alignment
                cell.border = thin_border
        
        # Ajusta largura das colunas
        column_widths = {
            1: 15,   # Status
            2: 8,    # AZ
            3: 20,   # Lote
            4: 30,   # Produto
            5: 15,   # Cultivar
            6: 10,   # Peneira
            7: 12,   # Categoria
            8: 18,   # Endereço
            9: 10,   # Saldo
            10: 12,  # Peso Unit.
            11: 12,  # Peso Total
            12: 12,  # Espécie
            13: 15,  # Tratamento
            14: 12,  # Embalagem
            15: 25,  # Cliente
            16: 25,  # Empresa
            17: 25,  # Conferente
            18: 30,  # Observação
        }
        
        for col, width in column_widths.items():
            ws.column_dimensions[get_column_letter(col)].width = width
        
        # Congela o cabeçalho
        ws.freeze_panes = 'A2'
        
        # Filtro automático
        if total_registros > 0:
            ultima_linha = total_registros + 1
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ultima_linha}"
        
        # Altura das linhas
        ws.row_dimensions[1].height = 30
        
        # Prepara resposta
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'estoque_{timestamp}.xlsx'
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        wb.save(response)
        
        print(f"✅ Arquivo Excel gerado: {filename} com {total_registros} registros")
        
        return response
        
    except Exception as e:
        import traceback
        print(f"❌ Erro na exportação Excel: {e}")
        print(traceback.format_exc())
        
        return HttpResponse(
            f"Erro ao gerar arquivo Excel: {str(e)}",
            content_type='text/plain',
            status=500
        )




# ============================================================================
# FASE 4 - ATUALIZAÇÃO AO VIVO, FEED E SOM
# ============================================================================

@login_required
def api_versao_cards(request):
    """
    Retorna um hash/versão dos cards para verificar se houve alteração.
    Usado pelo polling de 30 segundos.
    """
    from django.core.cache import cache
    from hashlib import md5
    
    cache_key = 'cards_version_hash'
    version = cache.get(cache_key)
    
    if not version:
        # Gerar hash baseado nos cards ativos
        cards_data = Solicitacao.objects.exclude(
            status='CONCLUIDO'
        ).values_list('id', 'data_atualizacao', 'status', 'quantidade_empenhada')
        
        hash_input = str(list(cards_data)).encode('utf-8')
        version = md5(hash_input).hexdigest()
        cache.set(cache_key, version, 5)  # Cache por 30 segundos
    
    return JsonResponse({
        'success': True,
        'version': version,
        'timestamp': timezone.now().isoformat(),
    })




@login_required
def api_configuracao_atualizacao(request):
    """
    GET: Retorna configuração do usuário
    POST: Salva configuração do usuário
    """
    config, created = ConfiguracaoAtualizacao.objects.get_or_create(
        usuario=request.user,
        defaults={
            'som_ativo': True,
            'volume': 50,
            'intervalo_atualizacao': 30,
        }
    )
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'config': {
                'som_ativo': config.som_ativo,
                'volume': config.volume,
                'intervalo_atualizacao': config.intervalo_atualizacao,
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            if 'som_ativo' in data:
                config.som_ativo = bool(data['som_ativo'])
            if 'volume' in data:
                config.volume = max(0, min(100, int(data['volume'])))
            if 'intervalo_atualizacao' in data:
                config.intervalo_atualizacao = max(10, min(300, int(data['intervalo_atualizacao'])))
            
            config.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Configuração salva com sucesso!',
                'config': {
                    'som_ativo': config.som_ativo,
                    'volume': config.volume,
                    'intervalo_atualizacao': config.intervalo_atualizacao,
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_html_cards_atualizados(request):
    """
    Retorna o HTML atualizado dos cards para substituição no frontend.
    Usado pelo polling para atualizar sem recarregar a página.
    """
    solicitacoes = Solicitacao.objects.select_related(
        'criador', 'armazem', 'especie', 'coluna_kanban'
    ).order_by('-data_criacao')
    
    data = []
    for sol in solicitacoes:
        data.append({
            'id': sol.id,
            'titulo': sol.titulo,
            'criador_nome': sol.criador.get_full_name() or sol.criador.username,
            'data_criacao': sol.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'status': sol.status,
            'unidade_controle': sol.unidade_controle,
            'quantidade_solicitada': float(sol.quantidade_solicitada),
            'quantidade_empenhada': float(sol.quantidade_empenhada),
            'percentual_empenhado': float(sol.percentual_empenhado),
            'coluna_kanban': sol.coluna_kanban.nome if sol.coluna_kanban else 'Início',
            'prioridade': sol.prioridade,
            'criterios': {
                'armazem': sol.armazem.nome if sol.armazem else '',
                'produto': sol.produto or '',
                'especie': sol.especie.nome if sol.especie else '',
                'cliente': sol.cliente or '',
            }
        })
    
    return JsonResponse({
        'success': True,
        'cards': data,
        'timestamp': timezone.now().isoformat(),
    })


# ============================================================================
# FASE 5 - KANBAN COMPLETO, REGRAS AUTOMÁTICAS E WORKFLOW
# ============================================================================







@login_required
@permission_required('sapp.pode_configuracoes', raise_exception=True)
def pagina_config_workflow(request):
    """Página de configuração do workflow"""
    return render(request, 'sapp/pagina_config_workflow.html')

from sapp.models import ColunaKanban, RegraWorkflow
def criar_regras_workflow_padrao():
    """
    Cria as regras de workflow padrão se não existirem.
    Chamar via manage.py ou na primeira migração.
    """
    # Garantir que colunas existem
    ColunaKanban.criar_colunas_padrao()
    
    coluna_inicio = ColunaKanban.objects.get(nome='Início')
    coluna_meio = ColunaKanban.objects.get(nome='Meio')
    coluna_fim = ColunaKanban.objects.get(nome='Fim')
    
    regras_padrao = [
        # Início
        {'coluna': coluna_inicio, 'evento': 'CRIACAO', 'status': 'AGUARDANDO_EMPENHO', 'auto': True},
        
        # Meio
        {'coluna': coluna_meio, 'evento': 'PRIMEIRO_EMPENHO', 'status': 'EMPENHO_PARCIAL', 'auto': True},
        {'coluna': coluna_meio, 'evento': 'EMPENHO_PARCIAL', 'status': 'EMPENHO_PARCIAL', 'auto': True},
        {'coluna': coluna_meio, 'evento': 'EMPENHO_COMPLETO', 'status': 'EMPENHO_COMPLETO', 'auto': True},
        {'coluna': coluna_meio, 'evento': 'PRIMEIRA_MOVIMENTACAO', 'status': 'MOVIMENTACAO_PARCIAL', 'auto': True},
        {'coluna': coluna_meio, 'evento': 'MOVIMENTACAO_PARCIAL', 'status': 'MOVIMENTACAO_PARCIAL', 'auto': True},
        
        # Fim
        {'coluna': coluna_fim, 'evento': 'TRANSFERENCIA_COMPLETA', 'status': 'CONCLUIDO', 'auto': True},
        {'coluna': coluna_fim, 'evento': 'EXPEDICAO_COMPLETA', 'status': 'CONCLUIDO', 'auto': True},
        {'coluna': coluna_fim, 'evento': 'CONCLUSAO', 'status': 'CONCLUIDO', 'auto': True},
        {'coluna': coluna_fim, 'evento': 'CANCELAMENTO', 'status': 'CANCELADO', 'auto': True},
    ]
    
    created_count = 0
    for regra_data in regras_padrao:
        regra, created = RegraWorkflow.objects.get_or_create(
            coluna=regra_data['coluna'],
            evento=regra_data['evento'],
            defaults={
                'status_resultante': regra_data['status'],
                'movimentacao_automatica': regra_data['auto'],
            }
        )
        if created:
            created_count += 1
    
    return created_count



@login_required
def api_remover_itens_solicitacao(
    request,
    solicitacao_id
):
    """
    Remove todos os itens pendentes do empenho vinculado
    exclusivamente à solicitação informada.
    """
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    try:
        with transaction.atomic():
            solicitacao = (
                Solicitacao.objects
                .select_for_update()
                .get(id=solicitacao_id)
            )

            if solicitacao.status in [
                'CONCLUIDO',
                'CANCELADO',
            ]:
                raise ValueError(
                    'Este card já está concluído ou cancelado.'
                )

            empenho = (
                Empenho.objects
                .select_for_update()
                .filter(
                    solicitacao_id=solicitacao.id,
                    status__nome='Rascunho'
                )
                .first()
            )

            if not empenho:
                return JsonResponse({
                    'success': True,
                    'message': 'Nenhum item para remover.'
                })

            itens = list(
                empenho.itens.select_related(
                    'estoque'
                )
            )

            quantidade_removida = sum(
                item.quantidade
                for item in itens
            )

            quantidade_itens = len(itens)

            # Exclusão individual para executar
            # ItemEmpenho.delete() e liberar Estoque.empenhado.
            for item in itens:
                item.delete()

            solicitacao.quantidade_empenhada = Decimal('0')
            solicitacao.status = 'AGUARDANDO_EMPENHO'

            solicitacao.save(
                update_fields=[
                    'quantidade_empenhada',
                    'status',
                    'data_atualizacao',
                ]
            )

            avaliar_workflow(
                solicitacao,
                'CRIACAO',
                request.user
            )

            HistoricoCard.objects.create(
                solicitacao=solicitacao,
                usuario=request.user,
                acao='REMOCAO_ITEM',
                quantidade=quantidade_removida,
                unidade=(
                    'KG'
                    if solicitacao.unidade_controle
                    == 'QUILOGRAMA'
                    else 'BAG'
                ),
                observacao=(
                    f'{quantidade_itens} item(ns) removido(s) '
                    f'do Empenho #{empenho.id}'
                )
            )

            from django.core.cache import cache
            cache.delete('cards_version_hash')

            return JsonResponse({
                'success': True,
                'message': (
                    f'{quantidade_itens} item(ns) '
                    f'removido(s) com sucesso.'
                ),
                'quantidade_empenhada': 0,
                'status': solicitacao.status,
            })

    except Solicitacao.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Solicitação não encontrada.'
            },
            status=404
        )

    except ValueError as erro:
        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=400
        )

    except Exception as erro:
        logger.exception(
            'Erro ao remover itens da solicitação %s',
            solicitacao_id
        )

        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=500
        )









# ============================================================================
# IMPORTS NECESSÁRIOS (verifique se estão no topo do arquivo)
# ============================================================================
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, models
from django.http import JsonResponse
from django.db.models import Q, Sum, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import (
    Empenho, EmpenhoStatus, ItemEmpenho, Estoque, 
    HistoricoMovimentacao, HistoricoItemEmpenho, StatusSistemico,
    Cultivar, Peneira, Categoria, Tratamento, Especie,
    Armazem, Produto, Solicitacao, ColunaKanban, RegraWorkflow,
    HistoricoCard, ConfiguracaoAtualizacao,
)






def get_coluna_por_posicao(posicao):
    """
    Retorna a coluna do Kanban pela posição (0=primeira, 1=segunda, etc.)
    Se não existir coluna suficiente, retorna a primeira disponível.
    """
    colunas = list(ColunaKanban.objects.filter(ativa=True).order_by('ordem'))
    if not colunas:
        # Criar colunas padrão se não existirem
        ColunaKanban.criar_colunas_padrao()
        colunas = list(ColunaKanban.objects.filter(ativa=True).order_by('ordem'))
    
    if posicao < len(colunas):
        return colunas[posicao]
    return colunas[0] if colunas else None




# ============================================================================
# IMPORTS (VERIFIQUE SE ESTÃO TODOS NO TOPO DO ARQUIVO)
# ============================================================================
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db import transaction, models
from django.http import JsonResponse
from django.db.models import Q, Sum, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import (
    Empenho, EmpenhoStatus, ItemEmpenho, Estoque, 
    HistoricoMovimentacao, HistoricoItemEmpenho, StatusSistemico,
    Cultivar, Peneira, Categoria, Tratamento, Especie,
    Armazem, Produto, Solicitacao, ColunaKanban, RegraWorkflow,
    HistoricoCard, ConfiguracaoAtualizacao,
)

logger = logging.getLogger(__name__)

def obter_empenho_da_solicitacao(
    solicitacao,
    status_nome='Rascunho'
):
    """
    Retorna exclusivamente o empenho vinculado à solicitação
    recebida.

    Não utiliza título ou observação para localizar o empenho.
    """

    if not solicitacao or not solicitacao.id:
        return None

    filtros = {
        'solicitacao_id': solicitacao.id,
    }

    if status_nome:
        filtros['status__nome'] = status_nome

    return (
        Empenho.objects
        .filter(**filtros)
        .order_by('-data_criacao', '-id')
        .first()
    )
# ============================================================================
# FUNÇÃO CENTRAL DO WORKFLOW
# ============================================================================
def avaliar_workflow(solicitacao, evento, usuario=None):
    """
    Avalia as regras de workflow configuradas e move o card se necessário.
    Usa EXCLUSIVAMENTE as regras da tabela RegraWorkflow.
    """
    try:
        regra = RegraWorkflow.objects.filter(
            evento=evento,
            coluna__ativa=True
        ).select_related('coluna').first()
        
        if not regra:
            return False
        
        if not regra.movimentacao_automatica:
            return False
        
        coluna_anterior = solicitacao.coluna_kanban.nome if solicitacao.coluna_kanban else 'Nenhuma'
        
        if solicitacao.coluna_kanban and solicitacao.coluna_kanban.id == regra.coluna.id:
            if solicitacao.status != regra.status_resultante:
                solicitacao.status = regra.status_resultante
                solicitacao.save(update_fields=['status', 'data_atualizacao'])
            return False
        
        solicitacao.coluna_kanban = regra.coluna
        solicitacao.status = regra.status_resultante
        solicitacao.save(update_fields=['coluna_kanban', 'status', 'data_atualizacao'])
        
        HistoricoCard.objects.create(
            solicitacao=solicitacao,
            usuario=usuario or solicitacao.criador,
            acao='MOVIMENTACAO_KANBAN',
            coluna_anterior=coluna_anterior,
            coluna_nova=regra.coluna.nome,
            observacao=f'Automático: {regra.get_evento_display()} → {regra.coluna.nome}'
        )
        
        from django.core.cache import cache
        cache.delete('cards_version_hash')
        
        return True
        
    except Exception as e:
        logger.error(f"Erro workflow solicitação {solicitacao.id}, evento {evento}: {e}")
        return False



# ============================================================
# SUBSTITUA APENAS ESTAS DUAS VIEWS NO SEU views.py
# ============================================================





@login_required
@permission_required(
    'sapp.pode_criar_solicitacao',
    raise_exception=True
)
def criar_solicitacao(request):
    """Cria solicitação normal ou uma carga com múltiplas linhas."""
    return _salvar_solicitacao_form(request)


@login_required
@permission_required(
    'sapp.pode_criar_solicitacao',
    raise_exception=True
)
def editar_solicitacao(request, solicitacao_id):
    """Edita o card sem quebrar reservas/movimentações já registradas."""
    solicitacao = get_object_or_404(
        Solicitacao.objects.prefetch_related('itens_carga'),
        id=solicitacao_id,
    )

    if solicitacao.status in {'CONCLUIDO', 'CANCELADO'}:
        messages.warning(
            request,
            'Solicitações concluídas ou canceladas ficam preservadas para auditoria e não podem ser editadas.'
        )
        return redirect('sapp:pagina_solicitacoes')

    return _salvar_solicitacao_form(request, solicitacao=solicitacao)


def _parse_decimal_solicitacao(valor, nome='Quantidade'):
    try:
        numero = Decimal(str(valor or '').replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{nome} inválida.')
    if numero <= 0:
        raise ValueError(f'{nome} deve ser maior que zero.')
    return numero


def _ler_itens_carga_post(request):
    """
    Lê as linhas comerciais da carga.

    A solicitação guarda somente cliente + código + quantidade.
    A descrição é apenas um complemento do cadastro Produto e NÃO é
    obrigatória. Lote, categoria, peneira, AZ, endereço e peso pertencem
    ao lote escolhido no empenho.
    """
    ids = request.POST.getlist('carga_item_id[]') or request.POST.getlist('carga_item_id')
    clientes = request.POST.getlist('carga_cliente[]') or request.POST.getlist('carga_cliente')
    codigos = request.POST.getlist('carga_codigo[]') or request.POST.getlist('carga_codigo')
    quantidades = request.POST.getlist('carga_quantidade[]') or request.POST.getlist('carga_quantidade')

    total_linhas = max(len(ids), len(clientes), len(codigos), len(quantidades), 0)
    itens = []

    for idx in range(total_linhas):
        item_id_txt = (ids[idx] if idx < len(ids) else '').strip()
        cliente = normalizar_texto_cadastro(clientes[idx] if idx < len(clientes) else '')
        codigo = _normalizar_codigo_produto(codigos[idx] if idx < len(codigos) else '')
        qtd_txt = (quantidades[idx] if idx < len(quantidades) else '').strip()

        if not any([item_id_txt, cliente, codigo, qtd_txt]):
            continue

        if not cliente or not codigo:
            raise ValueError(
                f'Linha {idx + 1} da carga: Cliente e Código são obrigatórios.'
            )

        # Quantidade vazia/zero significa CARGA ABERTA: não existe teto de empenho.
        if qtd_txt:
            quantidade = _parse_decimal_solicitacao(qtd_txt, f'Quantidade da linha {idx + 1}')
            if quantidade != quantidade.to_integral_value():
                raise ValueError(
                    f'Linha {idx + 1}: a quantidade da carga deve ser informada em embalagens inteiras.'
                )
        else:
            quantidade = Decimal('0')

        item_id = None
        if item_id_txt:
            try:
                item_id = int(item_id_txt)
            except (TypeError, ValueError):
                raise ValueError(f'Linha {idx + 1}: identificador do item inválido.')

        # Produto é OPCIONAL. Serve exclusivamente para obter a descrição.
        produto = (
            Produto.objects
            .filter(codigo__iexact=codigo)
            .first()
        )

        itens.append({
            'id': item_id,
            'cliente': cliente,
            'produto': produto,
            # Mantém o código informado na solicitação, mesmo sem cadastro.
            'codigo': codigo,
            'descricao': (produto.descricao or '') if produto else '',
            # Estes dados vêm do LOTE EMPENHADO, não de Configurações.
            'categoria': '',
            'peneira': '',
            'lote': '',
            'quantidade_solicitada': quantidade,
            'ordem': len(itens) + 1,
        })

    if not itens:
        raise ValueError('Adicione pelo menos um item à carga.')

    return itens


def _item_carga_tem_empenho(item):
    """Uma linha já utilizada não pode ter seus critérios comerciais alterados."""
    if ItemEmpenho.objects.filter(item_carga_id=item.id).exists():
        return True

    return HistoricoItemEmpenho.objects.filter(
        empenho__solicitacao_id=item.solicitacao_id,
        item_carga_id_original=item.id,
    ).exists()


def _quantidade_item_carga_empenhada(item):
    atual = (
        ItemEmpenho.objects
        .filter(item_carga_id=item.id)
        .aggregate(total=Sum('quantidade'))['total']
        or 0
    )
    historica = (
        HistoricoItemEmpenho.objects
        .filter(
            empenho__solicitacao_id=item.solicitacao_id,
            item_carga_id_original=item.id,
        )
        .aggregate(total=Sum('quantidade'))['total']
        or 0
    )
    return Decimal(str(atual)) + Decimal(str(historica))


def _sincronizar_itens_carga(solicitacao, itens_post):
    """
    Atualiza somente linhas que ainda nunca foram empenhadas.

    Linhas já empenhadas são preservadas mesmo que alguém tente alterar o POST.
    Linhas livres podem ser editadas/removidas e novas linhas podem ser incluídas.
    """
    existentes = {
        item.id: item
        for item in solicitacao.itens_carga.select_for_update().all()
    }
    recebidos = set()

    for ordem, dados_originais in enumerate(itens_post, start=1):
        dados = dict(dados_originais)
        item_id = dados.pop('id', None)
        dados['ordem'] = ordem

        if item_id:
            item = existentes.get(item_id)
            if not item:
                raise ValueError('Um dos itens informados não pertence a esta carga.')

            recebidos.add(item_id)

            # Linha já usada no empenho é imutável em cliente/código/quantidade.
            if _item_carga_tem_empenho(item):
                continue

            for campo in (
                'cliente', 'produto', 'codigo', 'descricao',
                'categoria', 'peneira', 'lote',
                'quantidade_solicitada', 'ordem',
            ):
                setattr(item, campo, dados[campo])
            item.save(update_fields=[
                'cliente', 'produto', 'codigo', 'descricao',
                'categoria', 'peneira', 'lote',
                'quantidade_solicitada', 'ordem', 'atualizado_em',
            ])
        else:
            novo = SolicitacaoItemCarga.objects.create(
                solicitacao=solicitacao,
                **dados,
            )
            recebidos.add(novo.id)

    # Só pode excluir linha que ainda não foi utilizada em nenhum empenho.
    for item_id, item in existentes.items():
        if item_id in recebidos:
            continue
        if not _item_carga_tem_empenho(item):
            item.delete()

    if not solicitacao.itens_carga.exists():
        raise ValueError('A carga precisa possuir pelo menos um item.')


def _reservar_titulo_carga():
    """Reserva, com lock, o próximo título CARGA N sem reutilizar números."""
    config = (
        Configuracao.objects
        .select_for_update()
        .filter(pk=1)
        .first()
    )
    if config is None:
        config = Configuracao.objects.create(pk=1, proximo_numero_carga=1)

    numero = max(1, int(config.proximo_numero_carga or 1))
    while Solicitacao.objects.filter(titulo__iexact=f'CARGA {numero}').exists():
        numero += 1

    config.proximo_numero_carga = numero + 1
    config.save(update_fields=['proximo_numero_carga'])
    return f'CARGA {numero}'


def _descricao_produto_por_codigo(codigo):
    codigo = _normalizar_codigo_produto(codigo)
    if not codigo:
        return ''
    produto = Produto.objects.filter(codigo__iexact=codigo).only('descricao').first()
    return (produto.descricao or '') if produto else ''


def _contexto_form_solicitacao(solicitacao=None, edicao_estrutural_bloqueada=False):
    produtos = (
        Produto.objects
        .select_related('cultivar')
        .order_by('codigo')
    )
    produtos_js = [
        {
            'id': p.id,
            'codigo': p.codigo,
            'descricao': p.descricao or '',
            'cultivar': p.cultivar.nome if p.cultivar else '',
        }
        for p in produtos
    ]

    itens_carga_edicao = []
    if solicitacao:
        for item in solicitacao.itens_carga.all():
            item.quantidade_empenhada_edicao = _quantidade_item_carga_empenhada(item)
            item.edicao_bloqueada = item.quantidade_empenhada_edicao > 0
            itens_carga_edicao.append(item)

    return {
        'armazens': Armazem.objects.all().order_by('nome'),
        'especies': Especie.objects.all().order_by('nome'),
        'solicitacao': solicitacao,
        'itens_carga_edicao': itens_carga_edicao,
        'produtos_carga_json': json.dumps(produtos_js, cls=DjangoJSONEncoder),
        'proximo_titulo_carga': f"CARGA {max(1, int(Configuracao.get_solo().proximo_numero_carga or 1))}",
        # Bloqueio GLOBAL continua válido para tipo/armazém e solicitação normal.
        # Carga usa item.edicao_bloqueada para bloquear somente a linha já empenhada.
        'edicao_estrutural_bloqueada': edicao_estrutural_bloqueada,
    }


def _salvar_solicitacao_form(request, solicitacao=None):
    editando = solicitacao is not None
    edicao_estrutural_bloqueada = bool(
        editando and (
            Decimal(str(solicitacao.quantidade_empenhada or 0)) > 0
            or Decimal(str(solicitacao.quantidade_movimentada or 0)) > 0
        )
    )

    if request.method == 'POST':
        try:
            tipo_postado = request.POST.get('tipo_solicitacao', 'TRANSFERENCIA').strip().upper()
            if tipo_postado not in {'TRANSFERENCIA', 'CARGA'}:
                tipo_postado = 'TRANSFERENCIA'

            titulo_digitado = normalizar_texto_cadastro(request.POST.get('titulo', ''))
            # Carga nova recebe título sequencial dentro da transação. Para
            # transferência, o título continua informado pelo usuário.
            if tipo_postado != 'CARGA' and not titulo_digitado:
                raise ValueError('Título é obrigatório.')

            destino = normalizar_texto_cadastro(request.POST.get('destino', ''))
            observacao = request.POST.get('observacao', '').strip()
            prioridade = request.POST.get('prioridade', 'MEDIA')

            with transaction.atomic():
                if not editando:
                    solicitacao = Solicitacao(criador=request.user)

                tipo_anterior = solicitacao.tipo_solicitacao if editando else None

                # Depois do primeiro empenho, tipo e armazém não mudam.
                if edicao_estrutural_bloqueada:
                    tipo = solicitacao.tipo_solicitacao
                else:
                    tipo = tipo_postado
                    solicitacao.tipo_solicitacao = tipo

                    armazem_id = request.POST.get('armazem')
                    solicitacao.armazem = (
                        Armazem.objects.filter(id=armazem_id).first()
                        if armazem_id else None
                    )

                if tipo == 'CARGA':
                    if (not editando) or tipo_anterior != 'CARGA':
                        titulo = _reservar_titulo_carga()
                    else:
                        titulo = solicitacao.titulo
                else:
                    titulo = titulo_digitado

                solicitacao.titulo = titulo
                solicitacao.destino = destino
                solicitacao.observacao = observacao or None
                solicitacao.prioridade = prioridade

                if tipo == 'CARGA':
                    motorista = normalizar_texto_cadastro(request.POST.get('motorista', ''))
                    if not motorista:
                        raise ValueError('Informe o nome do motorista da carga.')

                    placa = normalizar_texto_cadastro(request.POST.get('placa', ''))

                    solicitacao.motorista = motorista
                    solicitacao.placa = placa
                    solicitacao.produto = None
                    solicitacao.cliente = None
                    solicitacao.especie = None
                    solicitacao.unidade_controle = 'EMBALAGEM'

                    # Em carga, mesmo após um empenho, as linhas ainda NÃO empenhadas
                    # continuam editáveis. As linhas já usadas são preservadas.
                    itens_carga = _ler_itens_carga_post(request)
                else:
                    solicitacao.motorista = ''
                    solicitacao.placa = ''
                    itens_carga = []

                    if not edicao_estrutural_bloqueada:
                        especie_id = request.POST.get('especie')
                        solicitacao.especie = (
                            Especie.objects.filter(id=especie_id).first()
                            if especie_id else None
                        )
                        solicitacao.produto = _normalizar_codigo_produto(request.POST.get('produto', '')) or None
                        solicitacao.cliente = normalizar_texto_cadastro(request.POST.get('cliente', '')) or 'CS'
                        solicitacao.unidade_controle = request.POST.get('unidade_controle', 'EMBALAGEM')
                        solicitacao.quantidade_solicitada = _parse_decimal_solicitacao(
                            request.POST.get('quantidade_solicitada', '0')
                        )

                is_new = solicitacao.pk is None
                if is_new:
                    solicitacao.status = 'AGUARDANDO_EMPENHO'

                # Para carga nova, a quantidade é calculada depois da criação das linhas.
                if is_new and tipo == 'CARGA':
                    solicitacao.quantidade_solicitada = Decimal('0')

                solicitacao.save()

                if tipo == 'CARGA':
                    if is_new:
                        SolicitacaoItemCarga.objects.bulk_create([
                            SolicitacaoItemCarga(
                                solicitacao=solicitacao,
                                **{k: v for k, v in item.items() if k != 'id'}
                            )
                            for item in itens_carga
                        ])
                    else:
                        _sincronizar_itens_carga(solicitacao, itens_carga)

                    tem_linha_aberta = solicitacao.itens_carga.filter(quantidade_solicitada__lte=0).exists()
                    total_carga = (
                        solicitacao.itens_carga
                        .aggregate(total=Sum('quantidade_solicitada'))['total']
                        or Decimal('0')
                    )
                    # Se qualquer linha estiver sem quantidade, a carga é aberta como um todo.
                    # Linhas que possuem quantidade continuam respeitando seu próprio limite.
                    solicitacao.quantidade_solicitada = Decimal('0') if tem_linha_aberta else Decimal(str(total_carga))

                    # Se o total foi corrigido/adicionado, o status acompanha o saldo.
                    if solicitacao.status in {
                        'AGUARDANDO_EMPENHO', 'EMPENHO_PARCIAL', 'EMPENHO_COMPLETO'
                    }:
                        qtd_emp = Decimal(str(solicitacao.quantidade_empenhada or 0))
                        if qtd_emp <= 0:
                            solicitacao.status = 'AGUARDANDO_EMPENHO'
                        elif solicitacao.quantidade_solicitada <= 0:
                            solicitacao.status = 'EMPENHO_COMPLETO'
                        elif qtd_emp >= solicitacao.quantidade_solicitada:
                            solicitacao.status = 'EMPENHO_COMPLETO'
                        else:
                            solicitacao.status = 'EMPENHO_PARCIAL'

                    solicitacao.save(update_fields=[
                        'quantidade_solicitada', 'status', 'data_atualizacao'
                    ])
                elif not edicao_estrutural_bloqueada:
                    # Se mudou de uma carga ainda sem empenho para transferência,
                    # remove as linhas antigas porque ainda não possuem histórico físico.
                    solicitacao.itens_carga.all().delete()

                if is_new:
                    avaliar_workflow(solicitacao, 'CRIACAO', request.user)
                    HistoricoCard.objects.create(
                        solicitacao=solicitacao,
                        usuario=request.user,
                        acao='CRIACAO',
                        quantidade=solicitacao.quantidade_solicitada,
                        unidade='BAG' if solicitacao.unidade_controle == 'EMBALAGEM' else 'KG',
                        observacao=(
                            f'Solicitação criada: {titulo}'
                            f' | Tipo: {solicitacao.get_tipo_solicitacao_display()}'
                            + (f' | Motorista: {solicitacao.motorista}' if tipo == 'CARGA' and solicitacao.motorista else '')
                            + (f' | Placa: {solicitacao.placa}' if tipo == 'CARGA' and solicitacao.placa else '')
                            + (f' | Destino: {destino}' if destino else '')
                        ),
                    )
                else:
                    HistoricoCard.objects.create(
                        solicitacao=solicitacao,
                        usuario=request.user,
                        acao='EDICAO',
                        quantidade=solicitacao.quantidade_solicitada,
                        unidade='BAG' if solicitacao.unidade_controle == 'EMBALAGEM' else 'KG',
                        observacao='Dados da solicitação editados. Linhas já empenhadas foram preservadas.',
                    )

                cache.delete('cards_version_hash')

            messages.success(
                request,
                f'Solicitação "{titulo}" {"atualizada" if editando else "criada"} com sucesso!'
            )
            return redirect('sapp:pagina_solicitacoes')

        except ValueError as erro:
            messages.error(request, str(erro))
        except Exception as erro:
            logger.exception('Erro ao salvar solicitação')
            messages.error(request, f'Erro ao salvar solicitação: {erro}')

    return render(
        request,
        'sapp/criar_solicitacao.html',
        _contexto_form_solicitacao(solicitacao, edicao_estrutural_bloqueada),
    )

def _data_local_formatada(valor):
    """
    Converte a data para o fuso horário
    configurado no Django.
    """

    if not valor:
        return ''

    return timezone.localtime(
        valor
    ).strftime(
        '%d/%m/%Y %H:%M'
    )


@login_required
def api_dados_impressao_solicitacao(
    request,
    solicitacao_id
):
    """
    API da impressão.

    A coluna Armazém de cada item usa o AZ real do lote:
    - pendente: item.estoque.az
    - processado: historico.estoque_origem.az
      com fallback para estoque_destino.az
    """

    if request.method != 'GET':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    solicitacao = get_object_or_404(
        Solicitacao.objects
        .select_related(
            'criador',
            'responsavel',
            'armazem',
            'especie'
        ),
        id=solicitacao_id
    )

    empenhos = (
        Empenho.objects
        .filter(
            solicitacao_id=solicitacao.id
        )
        .prefetch_related(
            'itens__estoque',
            'itens__estoque__cultivar',
            'itens__estoque__peneira',
            'itens__estoque__categoria',
            'itens__estoque__especie',
            'itens__estoque__tratamento',
            Prefetch(
                'historico_itens',
                queryset=(
                    HistoricoItemEmpenho.objects
                    .select_related(
                        'estoque_origem',
                        'estoque_destino'
                    )
                    .order_by(
                        'processado_em',
                        'id'
                    )
                )
            )
        )
        .order_by(
            'data_criacao',
            'id'
        )
    )

    itens_pendentes = []
    itens_processados = []

    for empenho in empenhos:

        for item in empenho.itens.all():

            estoque = item.estoque

            itens_pendentes.append({
                'item_id': item.id,
                'situacao': 'PENDENTE',
                'lote': item.lote or '',
                'quantidade': float(
                    item.quantidade or 0
                ),

                # AZ REAL DO LOTE
                'armazem': (
                    estoque.az
                    if (
                        estoque
                        and estoque.az
                    )
                    else ''
                ),

                # Endereço operacional atual. Se uma transferência avulsa
                # realocou a reserva, o card acompanha o lote.
                'endereco': (
                    estoque.endereco
                    if estoque
                    else item.endereco_origem
                ),

                'produto': (
                    estoque.produto
                    if estoque
                    else ''
                ),

                'cultivar': (
                    item.cultivar
                    or (
                        estoque.cultivar.nome
                        if (
                            estoque
                            and estoque.cultivar
                        )
                        else ''
                    )
                ),

                'peneira': (
                    item.peneira
                    or (
                        estoque.peneira.nome
                        if (
                            estoque
                            and estoque.peneira
                        )
                        else ''
                    )
                ),

                'categoria': (
                    item.categoria
                    or (
                        estoque.categoria.nome
                        if (
                            estoque
                            and estoque.categoria
                        )
                        else ''
                    )
                ),

                'especie': (
                    estoque.especie.nome
                    if (
                        estoque
                        and estoque.especie
                    )
                    else ''
                ),

                'tratamento': (
                    estoque.tratamento.nome
                    if (
                        estoque
                        and estoque.tratamento
                    )
                    else ''
                ),

                'embalagem': (
                    estoque.embalagem
                    if estoque
                    else ''
                ),

                'empresa': (
                    estoque.empresa
                    if estoque
                    else ''
                ),

                'cliente': (
                    estoque.cliente
                    if estoque
                    else ''
                ),
            })

        for historico in empenho.historico_itens.all():

            tipo = str(
                historico.tipo or ''
            ).lower()

            if tipo == 'transferencia':
                situacao = 'TRANSFERIDO'

            elif tipo == 'expedicao':
                situacao = 'EXPEDIDO'

            else:
                situacao = (
                    historico.get_tipo_display()
                    if hasattr(
                        historico,
                        'get_tipo_display'
                    )
                    else str(
                        historico.tipo or ''
                    )
                ).upper()

            estoque_origem = (
                historico.estoque_origem
                if hasattr(
                    historico,
                    'estoque_origem'
                )
                else None
            )

            estoque_destino = (
                historico.estoque_destino
                if hasattr(
                    historico,
                    'estoque_destino'
                )
                else None
            )

            armazem_lote = (
                estoque_origem.az
                if (
                    estoque_origem
                    and estoque_origem.az
                )
                else (
                    estoque_destino.az
                    if (
                        estoque_destino
                        and estoque_destino.az
                    )
                    else ''
                )
            )

            itens_processados.append({
                'item_id': historico.id,
                'situacao': situacao,
                'lote': historico.lote or '',
                'quantidade': float(
                    historico.quantidade or 0
                ),

                # AZ REAL DO LOTE ORIGINAL
                'armazem': (
                    armazem_lote
                    or ''
                ),

                'endereco': (
                    historico.endereco_origem
                    or ''
                ),

                'endereco_destino': (
                    historico.endereco_destino
                    or ''
                ),

                'produto': (
                    historico.produto
                    or ''
                ),

                'cultivar': (
                    historico.cultivar
                    or ''
                ),

                'peneira': (
                    historico.peneira
                    or ''
                ),

                'categoria': (
                    historico.categoria
                    or ''
                ),

                'especie': (
                    historico.especie
                    or ''
                ),

                'tratamento': (
                    historico.tratamento
                    or ''
                ),

                'embalagem': (
                    historico.embalagem
                    or ''
                ),

                'empresa': (
                    historico.empresa
                    or ''
                ),

                'cliente': (
                    historico.cliente
                    or ''
                ),

                'processado_em': (
                    _data_local_formatada(
                        historico.processado_em
                    )
                ),
            })

    status_display = (
        solicitacao.get_status_display()
        if hasattr(
            solicitacao,
            'get_status_display'
        )
        else solicitacao.status
    )

    emitido_em = (
        _data_local_formatada(
            timezone.now()
        )
    )

    if (
        solicitacao.unidade_controle
        == 'QUILOGRAMA'
    ):
        quantidade_empenhada_display = (
            solicitacao.quantidade_empenhada_kg
            or Decimal('0')
        )
    else:
        quantidade_empenhada_display = (
            solicitacao.quantidade_empenhada
            or Decimal('0')
        )

    return JsonResponse({
        'success': True,
        'emitido_em': emitido_em,

        'solicitacao': {
            'id': solicitacao.id,
            'titulo': solicitacao.titulo,

            'criador': (
                solicitacao.criador.get_full_name()
                or solicitacao.criador.username
            ),

            'responsavel': (
                (
                    solicitacao.responsavel.get_full_name()
                    or solicitacao.responsavel.username
                )
                if solicitacao.responsavel
                else ''
            ),

            'data_criacao': (
                _data_local_formatada(
                    solicitacao.data_criacao
                )
            ),

            'data_atualizacao': (
                _data_local_formatada(
                    solicitacao.data_atualizacao
                )
            ),

            'data_finalizacao': (
                _data_local_formatada(
                    solicitacao.data_finalizacao
                )
                if (
                    solicitacao.status
                    == 'CONCLUIDO'
                    and solicitacao.data_finalizacao
                )
                else ''
            ),

            'destino': (
                solicitacao.destino
                or ''
            ),

            'observacao': (
                solicitacao.observacao
                or ''
            ),

            'prioridade': (
                solicitacao.get_prioridade_display()
                if hasattr(
                    solicitacao,
                    'get_prioridade_display'
                )
                else solicitacao.prioridade
            ),

            'quantidade_solicitada': float(
                solicitacao.quantidade_solicitada
                or 0
            ),

            'quantidade_empenhada': float(
                solicitacao.quantidade_empenhada
                or 0
            ),

            'quantidade_empenhada_display': float(
                quantidade_empenhada_display
            ),

            'quantidade_movimentada': float(
                solicitacao.quantidade_movimentada
                or 0
            ),

            'unidade_controle': (
                solicitacao.unidade_controle
            ),

            'status': (
                solicitacao.status
            ),

            'status_display': (
                status_display
            ),

            'criterios': {
                'armazem': (
                    solicitacao.armazem.nome
                    if solicitacao.armazem
                    else ''
                ),

                'produto': (
                    solicitacao.produto
                    or ''
                ),

                'especie': (
                    solicitacao.especie.nome
                    if solicitacao.especie
                    else ''
                ),

                'cliente': (
                    solicitacao.cliente
                    or ''
                ),

                'destino': (
                    solicitacao.destino
                    or ''
                ),
            },
        },

        'itens_pendentes': (
            itens_pendentes
        ),

        'itens_processados': (
            itens_processados
        ),
    })

# ============================================================================
# PÁGINA DE SOLICITAÇÕES
# ============================================================================
@login_required
@permission_required('sapp.pode_ver_empenhos', raise_exception=True)
def pagina_solicitacoes(request):
    """Página principal de solicitações"""
    return render(request, 'sapp/pagina_solicitacoes.html')


# ============================================================================
# API LISTAR SOLICITAÇÕES
# ============================================================================
@login_required
def api_listar_solicitacoes(request):

    solicitacoes = (
        Solicitacao.objects
        .select_related(
            'criador',
            'armazem',
            'especie',
            'coluna_kanban',
        )
        .prefetch_related(
            'empenhos__itens',
            'empenhos__historico_itens',
            'itens_carga__produto__categoria',
            'itens_carga__produto__peneira',
        )
        .order_by('-data_criacao')
    )

    data = []

    for sol in solicitacoes:

        # =====================================================
        # QUANTIDADE EMPENHADA
        # =====================================================

        if sol.unidade_controle == 'QUILOGRAMA':
            qtd_emp = (
                sol.quantidade_empenhada_kg
                or Decimal('0')
            )
        else:
            qtd_emp = Decimal(
                str(sol.quantidade_empenhada)
            )

        if sol.quantidade_solicitada > 0:
            percentual = (
                qtd_emp
                / sol.quantidade_solicitada
            ) * 100
        elif sol.tipo_solicitacao == 'CARGA' and qtd_emp > 0:
            # Carga aberta não possui teto pré-definido: qualquer quantidade
            # empenhada representa 100% do ciclo atual, mas novos empenhos
            # continuam permitidos até a movimentação começar.
            percentual = Decimal('100')
        else:
            percentual = Decimal('0')


        # =====================================================
        # LOTES RELACIONADOS AO CARD
        # =====================================================

        lotes = set()
        embalagens = set()
        # Itens que ainda estão empenhados
        for empenho in sol.empenhos.all():

            for item in empenho.itens.all():

                lote = str(
                    item.lote or ''
                ).strip()

                if lote:
                    lotes.add(lote)

                embalagem = str(
                    getattr(
                        item,
                        'embalagem_snapshot',
                        ''
                    )
                    or ''
                ).strip().upper()

                if embalagem:
                    embalagens.add(embalagem)


            # Itens que já foram transferidos ou expedidos
            for historico in empenho.historico_itens.all():

                lote = str(
                    historico.lote or ''
                ).strip()

                if lote:
                    lotes.add(lote)

                embalagem = str(
                    historico.embalagem
                    or ''
                ).strip().upper()

                if embalagem:
                    embalagens.add(embalagem)


        # Histórico do próprio card.
        # Também ajuda com cards antigos.
        lotes_historico_card = (
            HistoricoCard.objects
            .filter(
                solicitacao_id=sol.id
            )
            .exclude(
                lote__isnull=True
            )
            .exclude(
                lote=''
            )
            .values_list(
                'lote',
                flat=True
            )
        )

        for lote in lotes_historico_card:

            lote = str(
                lote or ''
            ).strip()

            if lote:
                lotes.add(lote)


        # =====================================================
        # ITENS DE CARGA
        # =====================================================
        itens_carga = []
        for item_carga in sol.itens_carga.all():
            itens_carga.append({
                'id': item_carga.id,
                'cliente': item_carga.cliente,
                'codigo': item_carga.codigo,
                'descricao': item_carga.descricao,
                'categoria': item_carga.categoria,
                'peneira': item_carga.peneira,
                'quantidade_solicitada': float(item_carga.quantidade_solicitada or 0),
            })

        # =====================================================
        # JSON
        # =====================================================

        data.append({

            'id': sol.id,

            'titulo': sol.titulo,
            'tipo_solicitacao': sol.tipo_solicitacao,
            'tipo_solicitacao_display': sol.get_tipo_solicitacao_display(),
            'destino': sol.destino or '',
            'observacao': sol.observacao or '',
            'itens_carga': itens_carga,

            'criador_nome': (
                sol.criador.get_full_name()
                or sol.criador.username
            ),

            'data_criacao': (
                timezone.localtime(sol.data_criacao).strftime(
                    '%d/%m/%Y %H:%M'
                )
                if sol.data_criacao else ''
            ),

            'status': sol.status,
            'status_display': sol.get_status_display(),

            'unidade_controle': (
                sol.unidade_controle
            ),

            'quantidade_solicitada': float(
                sol.quantidade_solicitada
            ),

            # Valor bruto em unidades
            'quantidade_empenhada': float(
                sol.quantidade_empenhada
            ),

            # Valor convertido conforme unidade
            'quantidade_empenhada_display': float(
                qtd_emp
            ),

            'quantidade_movimentada': float(
                sol.quantidade_movimentada
            ),

            'percentual_empenhado': float(
                percentual
            ),

            'percentual_movimentado': float(
                sol.percentual_movimentado
            ),

            'coluna_kanban': (
                sol.coluna_kanban.nome
                if sol.coluna_kanban
                else 'Sem coluna'
            ),

            'coluna_kanban_id': (
                sol.coluna_kanban.id
                if sol.coluna_kanban
                else None
            ),

            'prioridade': sol.prioridade,


            # =============================================
            # NOVO
            # =============================================

            'lotes': sorted(lotes),
            'embalagens': sorted(embalagens),

            'criterios': {

                'armazem': (
                    sol.armazem.nome
                    if sol.armazem
                    else ''
                ),

                'produto': (
                    sol.produto
                    or ''
                ),

                'especie': (
                    sol.especie.nome
                    if sol.especie
                    else ''
                ),

                'cliente': (
                    sol.cliente
                    or ''
                ),
            }

        })

    return JsonResponse({
        'success': True,
        'solicitacoes': data,
    })

    


@login_required
@permission_required(
    'sapp.pode_empenhar_solicitacao',
    raise_exception=True
)
def api_lotes_disponiveis_para_solicitacao(
    request,
    solicitacao_id
):
    """
    Lista lotes compatíveis com a solicitação.

    Os itens salvos no empenho do card atual aparecem primeiro.

    Um item empenhado por outro card:
    - não aparece como empenho deste card;
    - não fica selecionado;
    - não sobe para o topo;
    - continua descontado do saldo disponível.
    """

    solicitacao = get_object_or_404(
        Solicitacao.objects.select_related(
            'armazem',
            'especie',
        ).prefetch_related(
            'itens_carga__produto__categoria',
            'itens_carga__produto__peneira',
        ),
        id=solicitacao_id
    )

    # Busca exclusivamente o empenho salvo deste card.
    empenho = obter_empenho_da_solicitacao(
        solicitacao=solicitacao,
        status_nome='Rascunho'
    )

    # --------------------------------------------------------------
    # CARGA: cada linha da solicitação é independente.
    # O lote NÃO vem da solicitação. Primeiro escolhemos qual linha
    # (cliente + código + quantidade) está sendo atendida e só então
    # mostramos os lotes físicos compatíveis com aquele código.
    # --------------------------------------------------------------
    itens_carga = list(solicitacao.itens_carga.all())

    # Pedido pode ter sido criado antes do Produto existir em Configurações.
    # Ao abrir o empenho, atualizamos vínculo e descrição sem alterar
    # cliente, código ou quantidade da solicitação.
    if solicitacao.tipo_solicitacao == 'CARGA':
        for item in itens_carga:
            _sincronizar_item_carga_com_produto(item)

    totais_empenhados_carga = {}
    item_carga_ativo = None

    if solicitacao.tipo_solicitacao == 'CARGA':
        totais_empenhados_carga = dict(
            ItemEmpenho.objects
            .filter(
                empenho__solicitacao_id=solicitacao.id,
                item_carga_id__isnull=False,
            )
            .values('item_carga_id')
            .annotate(total=Sum('quantidade'))
            .values_list('item_carga_id', 'total')
        )

        item_carga_id_param = request.GET.get('item_carga_id')
        if item_carga_id_param:
            try:
                item_carga_id_param = int(item_carga_id_param)
            except (TypeError, ValueError):
                item_carga_id_param = None

        if item_carga_id_param:
            item_carga_ativo = next(
                (item for item in itens_carga if item.id == item_carga_id_param),
                None,
            )

        if item_carga_ativo is None:
            # Abre primeiro a primeira linha que ainda possui saldo a empenhar.
            item_carga_ativo = next(
                (
                    item for item in itens_carga
                    if Decimal(str(totais_empenhados_carga.get(item.id, 0) or 0))
                    < Decimal(str(item.quantidade_solicitada or 0))
                ),
                itens_carga[0] if itens_carga else None,
            )

    itens_ativos_card = ItemEmpenho.objects.filter(
        empenho__solicitacao_id=solicitacao.id,
        empenho__status__nome='Rascunho',
    )
    if solicitacao.tipo_solicitacao == 'CARGA' and item_carga_ativo:
        itens_ativos_card = itens_ativos_card.filter(item_carga_id=item_carga_ativo.id)

    ids_empenhados_no_card = list(
        itens_ativos_card.values_list('estoque_id', flat=True)
    )

    # Mostra:
    # 1. lotes que ainda têm disponibilidade;
    # 2. lotes do empenho do card atual, mesmo se a
    #    disponibilidade geral estiver zerada.
    qs = (
        Estoque.objects
        .filter(
            Q(saldo__gt=F('empenhado'))
            |
            Q(id__in=ids_empenhados_no_card)
        )
        # Normaliza o código gravado no estoque para evitar que espaços
        # acidentais ou diferenças de caixa escondam um lote válido.
        .annotate(
            produto_normalizado=Upper(Trim('produto'))
        )
        .select_related(
            'cultivar',
            'peneira',
            'categoria',
            'especie',
            'tratamento',
            'status_sistemico',
            'conferente',
        )
    )

    # ------------------------------------------------------------------
    # FILTROS DA SOLICITAÇÃO
    # ------------------------------------------------------------------
    if solicitacao.armazem:
        qs = qs.filter(
            az=solicitacao.armazem.nome
        )

    if solicitacao.tipo_solicitacao == 'CARGA':
        if item_carga_ativo:
            codigo_item = _normalizar_codigo_produto(item_carga_ativo.codigo)
            qs = qs.filter(produto_normalizado=codigo_item)
        else:
            qs = qs.none()
    else:
        if solicitacao.produto:
            qs = qs.filter(
                produto_normalizado=_normalizar_codigo_produto(solicitacao.produto)
            )

        if solicitacao.especie:
            qs = qs.filter(
                especie=solicitacao.especie
            )

        # Cliente da solicitação é o cliente comercial do empenho, como em
        # Carga. Ele NÃO restringe o proprietário gravado no estoque.

    # ------------------------------------------------------------------
    # BUSCA
    # ------------------------------------------------------------------
    busca = request.GET.get(
        'busca',
        ''
    ).strip()

    if busca:
        filtro_busca = (
            Q(lote__icontains=busca)
            | Q(produto__icontains=busca)
            | Q(endereco__icontains=busca)
            | Q(cliente__icontains=busca)
            | Q(cultivar__nome__icontains=busca)
            | Q(az__icontains=busca)
        )

        # Para carga, Cliente/Descrição/Categoria/Peneira pertencem também
        # ao item da solicitação. Traduzimos a busca nesses dados para os
        # respectivos código/lote do estoque, mantendo o resultado coerente
        # com o que a tabela realmente exibe.
        if solicitacao.tipo_solicitacao == 'CARGA' and item_carga_ativo:
            termo = busca.casefold()
            texto_item = ' '.join([
                str(item_carga_ativo.cliente or ''),
                str(item_carga_ativo.codigo or ''),
                str(item_carga_ativo.descricao or ''),
                str(item_carga_ativo.categoria or ''),
                str(item_carga_ativo.peneira or ''),
            ]).casefold()
            if termo in texto_item:
                filtro_busca |= Q(produto_normalizado=_normalizar_codigo_produto(item_carga_ativo.codigo))

        qs = qs.filter(filtro_busca)

    # ------------------------------------------------------------------
    # FILTROS POR COLUNA
    # ------------------------------------------------------------------
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
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in',
    }

    # Em carga, a coluna Cliente representa o cliente da SOLICITAÇÃO,
    # e não necessariamente o proprietário gravado no estoque.
    clientes_filtro = [
        valor.strip()
        for valor in request.GET.getlist('cliente')
        if valor and valor.strip()
    ]
    if clientes_filtro:
        if solicitacao.tipo_solicitacao == 'CARGA':
            clientes_normalizados = {v.casefold() for v in clientes_filtro}
            cliente_ativo = str(item_carga_ativo.cliente or '').strip().casefold() if item_carga_ativo else ''
            if cliente_ativo not in clientes_normalizados:
                qs = qs.none()
        else:
            clientes_normalizados = {v.casefold() for v in clientes_filtro}
            cliente_solicitacao = str(solicitacao.cliente or 'CS').strip().casefold()
            if cliente_solicitacao not in clientes_normalizados:
                qs = qs.none()

    for param, lookup in filter_map.items():
        valores = [
            valor.strip()
            for valor in request.GET.getlist(param)
            if valor and valor.strip()
        ]

        if valores:
            qs = qs.filter(**{
                lookup: valores
            })

    # ------------------------------------------------------------------
    # MARCAR SOMENTE OS ITENS DO EMPENHO DO CARD ATUAL
    # ------------------------------------------------------------------
    if ids_empenhados_no_card:
        qs = qs.annotate(
            empenho_do_card_atual=Case(
                When(
                    id__in=ids_empenhados_no_card,
                    then=Value(1)
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    else:
        qs = qs.annotate(
            empenho_do_card_atual=Value(
                0,
                output_field=IntegerField()
            )
        )

    # Os itens salvos no empenho deste card ficam no topo.
    qs = qs.order_by(
        '-empenho_do_card_atual',
        'lote',
        'endereco',
        'id',
    )

    # ------------------------------------------------------------------
    # PAGINAÇÃO
    # ------------------------------------------------------------------
    try:
        page = max(
            1,
            int(
                request.GET.get(
                    'page',
                    1
                )
            )
        )

        page_size = int(
            request.GET.get(
                'page_size',
                100
            )
        )

        page_size = max(
            1,
            min(
                page_size,
                1000
            )
        )

    except (TypeError, ValueError):
        page = 1
        page_size = 100

    total = qs.count()

    start = (
        page - 1
    ) * page_size

    end = start + page_size

    lotes_qs = list(qs[start:end])

    codigos_pagina = {
        _normalizar_codigo_produto(lote.produto)
        for lote in lotes_qs
        if lote.produto
    }
    descricoes_produtos = {
        _normalizar_codigo_produto(produto.codigo): (produto.descricao or '')
        for produto in Produto.objects.filter(codigo__in=codigos_pagina).only('codigo', 'descricao')
    }

    # Mapa dos itens salvos no empenho atual.
    itens_empenhados_por_estoque = {}

    if ids_empenhados_no_card:
        itens_empenhados_por_estoque = {
            item.estoque_id: item
            for item in itens_ativos_card.select_related('estoque')
        }

    lotes = []

    for lote in lotes_qs:
        item_empenhado = (
            itens_empenhados_por_estoque.get(
                lote.id
            )
        )

        pertence_ao_empenho_atual = (
            item_empenhado is not None
        )

        # Quantidade que pertence ao empenho deste card.
        quantidade_empenhada_card = (
            item_empenhado.quantidade
            if item_empenhado
            else 0
        )

        # O disponível normal já desconta empenhos de todos os cards.
        disponivel_geral = Decimal(
            str(
                lote.disponivel
                or 0
            )
        )

        # Para um item que já pertence ao card atual,
        # devolvemos sua própria reserva ao limite editável.
        disponivel_para_card = (
            disponivel_geral
            + Decimal(
                str(
                    quantidade_empenhada_card
                    or 0
                )
            )
        )

        item_carga_match = None
        if (
            solicitacao.tipo_solicitacao == 'CARGA'
            and item_carga_ativo
            and _normalizar_codigo_produto(item_carga_ativo.codigo)
                == _normalizar_codigo_produto(lote.produto)
        ):
            item_carga_match = item_carga_ativo

        lotes.append({
            'id': lote.id,
            'item_carga_id': item_carga_match.id if item_carga_match else None,
            'cliente_solicitacao': item_carga_match.cliente if item_carga_match else '',
            'codigo_solicitacao': item_carga_match.codigo if item_carga_match else '',
            'descricao_configuracao': item_carga_match.descricao if item_carga_match else '',
            'quantidade_solicitada_item': float(item_carga_match.quantidade_solicitada or 0) if item_carga_match else 0,

            'lote': lote.lote,
            'produto': lote.produto or '',
            'descricao': (
                item_carga_match.descricao
                if item_carga_match
                else descricoes_produtos.get(_normalizar_codigo_produto(lote.produto), '')
            ),

            'cultivar': (
                lote.cultivar.nome
                if lote.cultivar
                else ''
            ),

            'peneira': (
                lote.peneira.nome
                if lote.peneira
                else ''
            ),

            'categoria': (
                lote.categoria.nome
                if lote.categoria
                else ''
            ),

            'especie': (
                lote.especie.nome
                if lote.especie
                else ''
            ),

            'tratamento': (
                lote.tratamento.nome
                if lote.tratamento
                else ''
            ),

            'endereco': lote.endereco or '',

            'saldo': float(
                lote.saldo or 0
            ),

            # Quantidade reservada no estoque por todos os empenhos.
            'empenhado': float(
                lote.empenhado or 0
            ),

            'disponivel': float(
                disponivel_geral
            ),

            # Limite que o card atual pode utilizar.
            'disponivel_para_card': float(
                disponivel_para_card
            ),

            'peso_unitario': float(
                lote.peso_unitario or 0
            ),

            'peso_total': float(
                lote.peso_total or 0
            ),
            'data_ultima_movimentacao': (
                timezone.localtime(lote.data_ultima_movimentacao).strftime('%d/%m/%Y %H:%M')
                if lote.data_ultima_movimentacao else ''
            ),

            'embalagem': lote.embalagem or '',
            'cliente_estoque': lote.cliente or '',
            'cliente': (
                item_carga_match.cliente
                if item_carga_match
                else (solicitacao.cliente or 'CS')
            ),
            'empresa': lote.empresa or '',
            'az': lote.az or '',

            'conferente': (
                (
                    lote.conferente.get_full_name()
                    or lote.conferente.username
                )
                if lote.conferente
                else ''
            ),

            'observacao': (
                lote.observacao or ''
            ),

            'status_sistemico': (
                {
                    'nome': (
                        lote.status_sistemico.nome
                    ),
                    'cor': (
                        lote.status_sistemico.cor
                    ),
                    'icone': (
                        lote.status_sistemico.icone
                    ),
                }
                if lote.status_sistemico
                else None
            ),

            # Estes campos dizem respeito somente
            # ao empenho salvo do card aberto.
            'empenho_do_card_atual': (
                pertence_ao_empenho_atual
            ),

            'item_empenho_id': (
                item_empenhado.id
                if item_empenhado
                else None
            ),

            'quantidade_empenhada_card': float(
                quantidade_empenhada_card or 0
            ),
        })

    # ------------------------------------------------------------------
    # ITENS SALVOS EXCLUSIVAMENTE NO EMPENHO DO CARD ATUAL
    # ------------------------------------------------------------------
    itens_empenhados = []

    if ids_empenhados_no_card:
        itens_qs = itens_ativos_card.select_related('estoque', 'empenho').order_by(
            'lote',
            'endereco_origem',
            'id',
        )

        for item in itens_qs:
            estoque = item.estoque

            itens_empenhados.append({
                'id': item.id,
                'empenho_id': item.empenho_id,
                'solicitacao_id': solicitacao.id,

                'estoque_id': item.estoque_id,
                'item_carga_id': item.item_carga_id,
                'cliente_solicitacao': item.cliente_solicitacao_snapshot or '',
                'codigo_solicitacao': item.codigo_produto_snapshot or '',
                'lote': item.lote,

                'quantidade': float(
                    item.quantidade or 0
                ),

                # Para operação do card, mostrar a localização física atual.
                'endereco': (
                    estoque.endereco
                    if estoque
                    else item.endereco_origem
                ),

                'peso_unitario': float(
                    estoque.peso_unitario or 0
                ) if estoque else 0,

                'empenho_salvo': True,
                'empenho_do_card_atual': True,
            })

    quantidade_movimentada = Decimal(
        str(
            solicitacao.quantidade_movimentada
            or 0
        )
    )

    empenho_bloqueado = (
        solicitacao.status in {
            'MOVIMENTACAO_PARCIAL',
            'CONCLUIDO',
            'CANCELADO',
        }
        or quantidade_movimentada > 0
    )

    itens_carga_resumo = []
    quantidade_solicitada_escopo = Decimal(str(solicitacao.quantidade_solicitada or 0))
    quantidade_empenhada_escopo = Decimal(str(solicitacao.quantidade_empenhada or 0))

    if solicitacao.tipo_solicitacao == 'CARGA':
        for item in itens_carga:
            qtd_item = Decimal(str(item.quantidade_solicitada or 0))
            qtd_emp_item = Decimal(str(totais_empenhados_carga.get(item.id, 0) or 0))
            ilimitado = qtd_item <= 0
            restante_item = Decimal('0') if ilimitado else max(Decimal('0'), qtd_item - qtd_emp_item)
            itens_carga_resumo.append({
                'id': item.id,
                'ordem': item.ordem,
                'cliente': item.cliente,
                'codigo': item.codigo,
                'descricao': item.descricao,
                'categoria': item.categoria,
                'peneira': item.peneira,
                'quantidade_solicitada': float(qtd_item),
                'quantidade_empenhada': float(qtd_emp_item),
                'quantidade_restante': None if ilimitado else float(restante_item),
                'quantidade_aberta': ilimitado,
                'completo': False if ilimitado else restante_item <= 0,
            })

        if item_carga_ativo:
            quantidade_solicitada_escopo = Decimal(str(item_carga_ativo.quantidade_solicitada or 0))
            quantidade_empenhada_escopo = Decimal(str(totais_empenhados_carga.get(item_carga_ativo.id, 0) or 0))

    return JsonResponse({
        'success': True,

        'lotes': lotes,

        'total': total,
        'page': page,
        'page_size': page_size,
        'has_more': end < total,
        'itens_carga': itens_carga_resumo,
        'item_carga_ativo_id': item_carga_ativo.id if item_carga_ativo else None,

        'solicitacao': {
            'id': solicitacao.id,
            'titulo': solicitacao.titulo,
            'tipo_solicitacao': solicitacao.tipo_solicitacao,
            'quantidade_solicitada_escopo': float(quantidade_solicitada_escopo),
            'quantidade_empenhada_escopo': float(quantidade_empenhada_escopo),

            'quantidade_solicitada': float(
                solicitacao.quantidade_solicitada
                or 0
            ),

            'quantidade_empenhada': float(
                solicitacao.quantidade_empenhada
                or 0
            ),

            'quantidade_movimentada': float(
                solicitacao.quantidade_movimentada
                or 0
            ),

            'unidade_controle': (
                solicitacao.unidade_controle
            ),

            'status': solicitacao.status,
            'destino': solicitacao.destino or '',
            'observacao': solicitacao.observacao or '',
            'cliente': solicitacao.cliente or ('CS' if solicitacao.tipo_solicitacao != 'CARGA' else ''),

            'empenho_bloqueado': empenho_bloqueado,
        },

        'empenho_id': (
            empenho.id
            if empenho
            else None
        ),

        # Somente itens do empenho salvo deste card.
        'itens_empenhados': itens_empenhados,
    })
# ============================================================================
# EMPENHAR NA SOLICITAÇÃO
# ============================================================================

@login_required
@permission_required(
    'sapp.pode_empenhar_solicitacao',
    raise_exception=True
)
def empenhar_na_solicitacao(
    request,
    solicitacao_id
):
    """
    Cria ou atualiza o empenho vinculado exclusivamente
    à solicitação informada.

    Depois que existir movimentação, o empenho fica congelado.
    """

    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    try:
        data = json.loads(
            request.body or '{}'
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                'success': False,
                'error': 'JSON inválido.'
            },
            status=400
        )

    itens_selecionados = data.get(
        'itens',
        []
    )

    if not isinstance(
        itens_selecionados,
        list
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Lista de itens inválida.'
            },
            status=400
        )

    if not itens_selecionados:
        return JsonResponse(
            {
                'success': False,
                'error': 'Nenhum item selecionado.'
            },
            status=400
        )

    try:
        with transaction.atomic():

            # Bloqueia somente a solicitação.
            solicitacao = (
                Solicitacao.objects
                .select_for_update(
                    of=('self',)
                )
                .get(
                    id=solicitacao_id
                )
            )

            # Depois que começou a movimentar,
            # não pode criar nem atualizar empenho.
            validar_edicao_empenho_solicitacao(
                solicitacao
            )

            status_rascunho, _ = (
                EmpenhoStatus.objects
                .get_or_create(
                    nome='Rascunho',
                    defaults={
                        'descricao': (
                            'Card em elaboração'
                        )
                    }
                )
            )

            # Busca somente o empenho deste card.
            empenho = (
                Empenho.objects
                .select_for_update(
                    of=('self',)
                )
                .filter(
                    solicitacao_id=solicitacao.id,
                    status_id=status_rascunho.id,
                )
                .order_by(
                    '-data_criacao',
                    '-id',
                )
                .first()
            )

            if not empenho:
                empenho = Empenho.objects.create(
                    solicitacao=solicitacao,
                    usuario=request.user,
                    status=status_rascunho,
                    observacao=solicitacao.titulo,
                )

            elif (
                empenho.observacao
                != solicitacao.titulo
            ):
                empenho.observacao = (
                    solicitacao.titulo
                )

                empenho.save(
                    update_fields=[
                        'observacao',
                        'data_atualizacao',
                    ]
                )

            # ----------------------------------------------------------
            # TOTAL ATUAL DO EMPENHO
            # ----------------------------------------------------------
            total_kg_empenhado = Decimal('0')

            if (
                solicitacao.unidade_controle
                == 'QUILOGRAMA'
            ):
                itens_atuais = (
                    empenho.itens
                    .select_related(
                        'estoque'
                    )
                )

                for item_existente in itens_atuais:
                    peso = Decimal(
                        str(
                            item_existente
                            .estoque
                            .peso_unitario
                            or 0
                        )
                    )

                    quantidade_atual = Decimal(
                        str(
                            item_existente.quantidade
                            or 0
                        )
                    )

                    total_kg_empenhado += (
                        quantidade_atual
                        * peso
                    )

            itens_validos = 0

            # ----------------------------------------------------------
            # PROCESSAR ITENS RECEBIDOS
            # ----------------------------------------------------------
            for item_data in itens_selecionados:

                try:
                    lote_id = int(
                        item_data.get(
                            'lote_id'
                        )
                    )

                    quantidade_adicionar = Decimal(
                        str(
                            item_data.get(
                                'quantidade',
                                0
                            )
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                    ArithmeticError,
                ):
                    raise ValueError(
                        'Lote ou quantidade inválidos.'
                    )

                if quantidade_adicionar <= 0:
                    continue

                # Bloqueia somente o estoque.
                lote = (
                    Estoque.objects
                    .select_for_update(
                        of=('self',)
                    )
                    .get(
                        id=lote_id
                    )
                )

                item_carga = None
                if solicitacao.tipo_solicitacao == 'CARGA':
                    try:
                        item_carga_id = int(item_data.get('item_carga_id'))
                    except (TypeError, ValueError):
                        raise ValueError(
                            f'O lote {lote.lote} não está vinculado a uma linha válida da carga.'
                        )

                    item_carga = (
                        SolicitacaoItemCarga.objects
                        .select_for_update(of=('self',))
                        .filter(
                            id=item_carga_id,
                            solicitacao_id=solicitacao.id,
                        )
                        .first()
                    )
                    if not item_carga:
                        raise ValueError('Item da carga não encontrado.')

                    if _normalizar_codigo_produto(lote.produto) != _normalizar_codigo_produto(item_carga.codigo):
                        raise ValueError(
                            f'O produto do lote {lote.lote} não corresponde ao código {item_carga.codigo} da carga.'
                        )

                # Busca o item exclusivamente no empenho
                # vinculado ao card atual.
                filtro_item = {
                    'empenho_id': empenho.id,
                    'estoque_id': lote.id,
                }
                if item_carga:
                    filtro_item['item_carga_id'] = item_carga.id
                else:
                    filtro_item['item_carga__isnull'] = True

                item_existente = (
                    ItemEmpenho.objects
                    .select_for_update(
                        of=('self',)
                    )
                    .filter(**filtro_item)
                    .first()
                )

                quantidade_anterior = Decimal(
                    str(
                        item_existente.quantidade
                        if item_existente
                        else 0
                    )
                )

                saldo = Decimal(
                    str(
                        lote.saldo
                        or 0
                    )
                )

                empenhado_geral = Decimal(
                    str(
                        lote.empenhado
                        or 0
                    )
                )

                # O empenhado geral contém reservas de todos os cards.
                # Recolocamos somente a reserva deste card para permitir
                # editar seu próprio empenho.
                disponivel_para_card = (
                    saldo
                    - empenhado_geral
                    + quantidade_anterior
                )

                quantidade_final = (
                    quantidade_anterior
                    + quantidade_adicionar
                )

                if item_carga:
                    outros_da_linha = (
                        ItemEmpenho.objects
                        .filter(
                            empenho__solicitacao_id=solicitacao.id,
                            item_carga_id=item_carga.id,
                        )
                        .exclude(pk=item_existente.pk if item_existente else None)
                        .aggregate(total=Sum('quantidade'))['total']
                        or 0
                    )
                    total_linha = Decimal(str(outros_da_linha)) + quantidade_final
                    limite_linha = Decimal(str(item_carga.quantidade_solicitada or 0))
                    if limite_linha > 0 and total_linha > limite_linha:
                        raise ValueError(
                            f'A linha da carga {item_carga.cliente} / {item_carga.codigo} permite no máximo '
                            f'{limite_linha} embalagem(ns). Já ficaria com {total_linha}.'
                        )

                if (
                    quantidade_final
                    > disponivel_para_card
                ):
                    raise ValueError(
                        f'Quantidade indisponível para o lote '
                        f'{lote.lote}. Disponível para este '
                        f'card: {disponivel_para_card}.'
                    )

                # ------------------------------------------------------
                # VALIDAÇÃO EM KG
                # ------------------------------------------------------
                if (
                    solicitacao.unidade_controle
                    == 'QUILOGRAMA'
                ):
                    peso = Decimal(
                        str(
                            lote.peso_unitario
                            or 0
                        )
                    )

                    if peso <= 0:
                        raise ValueError(
                            f'O lote {lote.lote} não possui '
                            f'peso unitário válido.'
                        )

                    kg_adicionados = (
                        quantidade_adicionar
                        * peso
                    )

                    total_kg_empenhado += (
                        kg_adicionados
                    )

                    quantidade_solicitada = Decimal(
                        str(
                            solicitacao
                            .quantidade_solicitada
                            or 0
                        )
                    )

                    if (
                        total_kg_empenhado
                        > quantidade_solicitada
                    ):
                        raise ValueError(
                            f'O total de '
                            f'{total_kg_empenhado:.2f} KG '
                            f'excede os '
                            f'{quantidade_solicitada:.2f} KG '
                            f'solicitados.'
                        )

                # ------------------------------------------------------
                # SALVAR ITEM NO EMPENHO DO CARD ATUAL
                # ------------------------------------------------------
                descricao_lote_config = _descricao_produto_por_codigo(lote.produto)
                cliente_solicitacao_item = (
                    item_carga.cliente if item_carga else (solicitacao.cliente or 'CS')
                )
                codigo_solicitacao_item = item_carga.codigo if item_carga else (lote.produto or '')
                descricao_solicitacao_item = item_carga.descricao if item_carga else descricao_lote_config

                if item_existente:
                    item_existente.quantidade = quantidade_final
                    item_existente.cliente_solicitacao_snapshot = cliente_solicitacao_item
                    item_existente.codigo_produto_snapshot = codigo_solicitacao_item
                    item_existente.descricao_produto_snapshot = descricao_solicitacao_item
                    campos_update = [
                        'quantidade',
                        'cliente_solicitacao_snapshot',
                        'codigo_produto_snapshot',
                        'descricao_produto_snapshot',
                    ]
                    if item_carga:
                        item_existente.item_carga = item_carga
                        campos_update.append('item_carga')
                    item_existente.save(update_fields=campos_update)

                else:
                    ItemEmpenho.objects.create(
                        empenho=empenho,
                        estoque=lote,
                        item_carga=item_carga,
                        quantidade=quantidade_adicionar,
                        cliente_solicitacao_snapshot=cliente_solicitacao_item,
                        codigo_produto_snapshot=codigo_solicitacao_item,
                        descricao_produto_snapshot=descricao_solicitacao_item,

                        lote=lote.lote,

                        cultivar=(
                            lote.cultivar.nome
                            if lote.cultivar
                            else ''
                        ),

                        peneira=(
                            lote.peneira.nome
                            if lote.peneira
                            else ''
                        ),

                        categoria=(
                            lote.categoria.nome
                            if lote.categoria
                            else ''
                        ),

                        endereco_origem=(
                            lote.endereco
                        ),

                        saldo_anterior=(
                            lote.saldo
                        ),
                    )

                itens_validos += 1

                # ------------------------------------------------------
                # HISTÓRICO
                # ------------------------------------------------------
                if (
                    solicitacao.unidade_controle
                    == 'QUILOGRAMA'
                ):
                    quantidade_historico = (
                        quantidade_adicionar
                        * Decimal(
                            str(
                                lote.peso_unitario
                                or 0
                            )
                        )
                    )

                    unidade_historico = 'KG'

                else:
                    quantidade_historico = (
                        quantidade_adicionar
                    )

                    unidade_historico = 'BAG'

                HistoricoCard.objects.create(
                    solicitacao=solicitacao,
                    usuario=request.user,
                    acao='EMPENHO',
                    lote=lote.lote,

                    quantidade=(
                        quantidade_historico
                    ),

                    unidade=unidade_historico,

                    observacao=(
                        f'Item salvo no Empenho '
                        f'#{empenho.id} deste card.'
                    )
                )

            if itens_validos == 0:
                raise ValueError(
                    'Nenhum item possui quantidade válida.'
                )

            # ----------------------------------------------------------
            # RECALCULAR TOTAL DO EMPENHO
            # ----------------------------------------------------------
            itens_ativos_solicitacao = ItemEmpenho.objects.filter(
                empenho__solicitacao_id=solicitacao.id
            )

            total_unidades = (
                itens_ativos_solicitacao.aggregate(
                    total=Sum('quantidade')
                )['total']
                or Decimal('0')
            )

            if (
                solicitacao.unidade_controle
                == 'QUILOGRAMA'
            ):
                total_kg_final = Decimal('0')

                itens_finais = itens_ativos_solicitacao.select_related('estoque')

                for item_final in itens_finais:
                    quantidade_item = Decimal(
                        str(
                            item_final.quantidade
                            or 0
                        )
                    )

                    peso_item = Decimal(
                        str(
                            item_final
                            .estoque
                            .peso_unitario
                            or 0
                        )
                    )

                    total_kg_final += (
                        quantidade_item
                        * peso_item
                    )

                solicitacao.quantidade_empenhada = (
                    total_kg_final
                )

                quantidade_para_status = (
                    total_kg_final
                )

            else:
                solicitacao.quantidade_empenhada = (
                    Decimal(
                        str(
                            total_unidades
                        )
                    )
                )

                quantidade_para_status = (
                    solicitacao.quantidade_empenhada
                )

            quantidade_solicitada = Decimal(
                str(
                    solicitacao.quantidade_solicitada
                    or 0
                )
            )

            # ----------------------------------------------------------
            # ATUALIZAR STATUS
            # ----------------------------------------------------------
            if quantidade_para_status <= 0:
                solicitacao.status = 'AGUARDANDO_EMPENHO'
                evento = 'CRIACAO'

            elif solicitacao.tipo_solicitacao == 'CARGA' and quantidade_solicitada <= 0:
                # Carga aberta sempre mostra 100% após o primeiro empenho,
                # mas permanece apta a receber mais empenhos até iniciar a movimentação.
                solicitacao.status = 'EMPENHO_COMPLETO'
                evento = 'EMPENHO_COMPLETO'

            elif (
                quantidade_para_status
                >= quantidade_solicitada
            ):
                solicitacao.status = (
                    'EMPENHO_COMPLETO'
                )

                evento = 'EMPENHO_COMPLETO'

            else:
                solicitacao.status = (
                    'EMPENHO_PARCIAL'
                )

                evento = 'EMPENHO_PARCIAL'

            solicitacao.save(
                update_fields=[
                    'quantidade_empenhada',
                    'status',
                    'data_atualizacao',
                ]
            )

            avaliar_workflow(
                solicitacao,
                evento,
                request.user
            )

            cache.delete(
                'cards_version_hash'
            )

            coluna_kanban_nome = ''

            if solicitacao.coluna_kanban_id:
                coluna_kanban_nome = (
                    ColunaKanban.objects
                    .filter(
                        id=solicitacao.coluna_kanban_id
                    )
                    .values_list(
                        'nome',
                        flat=True
                    )
                    .first()
                    or ''
                )

            return JsonResponse({
                'success': True,

                'message': (
                    f'{itens_validos} item(ns) '
                    f'salvo(s) no empenho deste card.'
                ),

                'empenho_id': empenho.id,
                'solicitacao_id': solicitacao.id,

                'total_empenhado': float(
                    solicitacao.quantidade_empenhada
                    or 0
                ),

                'percentual': float(
                    solicitacao.percentual_empenhado
                    or 0
                ),

                'status': solicitacao.status,
                'coluna_kanban': coluna_kanban_nome,

                'empenho_bloqueado': False,
            })

    except Solicitacao.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Solicitação não encontrada.'
            },
            status=404
        )

    except Estoque.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Um dos lotes não foi encontrado.'
            },
            status=404
        )

    except ValueError as erro:
        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=400
        )

    except Exception as erro:
        logger.exception(
            'Erro ao empenhar solicitação %s',
            solicitacao_id
        )

        return JsonResponse(
            {
                'success': False,
                'error': f'Erro ao empenhar: {erro}'
            },
            status=500
        )
# ============================================================================
# REMOVER ITEM DO EMPENHO
# ============================================================================
@login_required
@permission_required(
    'sapp.pode_empenhar_solicitacao',
    raise_exception=True
)
def api_remover_item_empenho(
    request,
    solicitacao_id,
    item_id
):
    """
    Remove um item exclusivamente do empenho do card atual.

    Não permite remoção depois que a movimentação começou.
    """

    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    try:
        with transaction.atomic():

            solicitacao = (
                Solicitacao.objects
                .select_for_update(
                    of=('self',)
                )
                .get(
                    id=solicitacao_id
                )
            )

            validar_edicao_empenho_solicitacao(
                solicitacao
            )

            item = (
                ItemEmpenho.objects
                .select_for_update(of=('self',))
                .select_related('empenho')
                .get(
                    id=item_id,
                    empenho__solicitacao_id=solicitacao.id,
                    empenho__status__nome='Rascunho',
                )
            )
            empenho = item.empenho

            quantidade_removida = Decimal(
                str(
                    item.quantidade
                    or 0
                )
            )

            lote_nome = item.lote

            estoque_id = item.estoque_id

            peso_unitario = Decimal('0')

            if estoque_id:
                estoque = (
                    Estoque.objects
                    .select_for_update(
                        of=('self',)
                    )
                    .get(
                        id=estoque_id
                    )
                )

                peso_unitario = Decimal(
                    str(
                        estoque.peso_unitario
                        or 0
                    )
                )

            # Executa o delete personalizado do item.
            item.delete()

            # ----------------------------------------------------------
            # RECALCULAR EMPENHO DO CARD
            # ----------------------------------------------------------
            if (
                solicitacao.unidade_controle
                == 'QUILOGRAMA'
            ):
                total_restante = Decimal('0')

                itens_restantes = (
                    ItemEmpenho.objects
                    .filter(empenho__solicitacao_id=solicitacao.id)
                    .select_related('estoque')
                )

                for item_restante in itens_restantes:
                    quantidade = Decimal(
                        str(
                            item_restante.quantidade
                            or 0
                        )
                    )

                    peso = Decimal(
                        str(
                            item_restante
                            .estoque
                            .peso_unitario
                            or 0
                        )
                    )

                    total_restante += (
                        quantidade
                        * peso
                    )

                solicitacao.quantidade_empenhada = (
                    total_restante
                )

                quantidade_historico = (
                    quantidade_removida
                    * peso_unitario
                )

                unidade_historico = 'KG'

            else:
                total_restante = (
                    ItemEmpenho.objects
                    .filter(empenho__solicitacao_id=solicitacao.id)
                    .aggregate(total=Sum('quantidade'))['total']
                    or Decimal('0')
                )

                solicitacao.quantidade_empenhada = (
                    Decimal(
                        str(
                            total_restante
                        )
                    )
                )

                quantidade_historico = (
                    quantidade_removida
                )

                unidade_historico = 'BAG'

            quantidade_solicitada = Decimal(
                str(
                    solicitacao.quantidade_solicitada
                    or 0
                )
            )

            if (
                solicitacao.quantidade_empenhada
                <= 0
            ):
                solicitacao.status = (
                    'AGUARDANDO_EMPENHO'
                )

                evento = 'CRIACAO'

            elif (
                solicitacao.quantidade_empenhada
                >= quantidade_solicitada
            ):
                solicitacao.status = (
                    'EMPENHO_COMPLETO'
                )

                evento = 'EMPENHO_COMPLETO'

            else:
                solicitacao.status = (
                    'EMPENHO_PARCIAL'
                )

                evento = 'EMPENHO_PARCIAL'

            solicitacao.save(
                update_fields=[
                    'quantidade_empenhada',
                    'status',
                    'data_atualizacao',
                ]
            )

            HistoricoCard.objects.create(
                solicitacao=solicitacao,
                usuario=request.user,
                acao='REMOCAO_EMPENHO',
                lote=lote_nome,
                quantidade=quantidade_historico,
                unidade=unidade_historico,
                observacao=(
                    f'Item removido do Empenho '
                    f'#{empenho.id} deste card.'
                )
            )

            avaliar_workflow(
                solicitacao,
                evento,
                request.user
            )

            cache.delete(
                'cards_version_hash'
            )

            return JsonResponse({
                'success': True,

                'message': (
                    f'Item do lote {lote_nome} '
                    f'removido do empenho.'
                ),

                'item_id': item_id,
                'estoque_id': estoque_id,

                'total_empenhado': float(
                    solicitacao.quantidade_empenhada
                    or 0
                ),

                'status': solicitacao.status,
            })

    except Solicitacao.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Solicitação não encontrada.'
            },
            status=404
        )

    except ItemEmpenho.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': (
                    'Item não encontrado no empenho '
                    'deste card.'
                )
            },
            status=404
        )

    except Estoque.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Estoque do item não encontrado.'
            },
            status=404
        )

    except ValueError as erro:
        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=400
        )

    except Exception as erro:
        logger.exception(
            'Erro ao remover o item %s do card %s',
            item_id,
            solicitacao_id
        )

        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=500
        )
# ============================================================================
# MOVIMENTAR SOLICITAÇÃO (TRANSFERIR / EXPEDIR)
# ============================================================================
# ============================================================================
# MOVIMENTAR (TRANSFERIR / EXPEDIR)
# ============================================================================
@login_required
def api_movimentar_solicitacao(request, solicitacao_id):
    """
    Transfere ou expede itens pertencentes exclusivamente
    ao empenho vinculado à solicitação informada.
    """

    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    # ------------------------------------------------------------------------
    # LER JSON
    # ------------------------------------------------------------------------
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse(
            {
                'success': False,
                'error': 'JSON inválido.'
            },
            status=400
        )

    acao = str(data.get('acao') or '').strip().lower()
    itens_ids = data.get('itens_ids', [])
    observacao = str(
        data.get('observacao') or ''
    ).strip()

    # ------------------------------------------------------------------------
    # VALIDAR AÇÃO
    # ------------------------------------------------------------------------
    if acao not in [
        'transferir',
        'expedir',
    ]:
        return JsonResponse(
            {
                'success': False,
                'error': 'Ação inválida.'
            },
            status=400
        )

    # ------------------------------------------------------------------------
    # VALIDAR ITENS
    # ------------------------------------------------------------------------
    if not isinstance(itens_ids, list) or not itens_ids:
        return JsonResponse(
            {
                'success': False,
                'error': 'Nenhum item selecionado.'
            },
            status=400
        )

    try:
        itens_ids = [
            int(item_id)
            for item_id in itens_ids
        ]
    except (TypeError, ValueError):
        return JsonResponse(
            {
                'success': False,
                'error': 'Lista de itens inválida.'
            },
            status=400
        )

    # Remove IDs repetidos.
    itens_ids = list(dict.fromkeys(itens_ids))

    try:
        with transaction.atomic():

            # ================================================================
            # BLOQUEAR SOMENTE A SOLICITAÇÃO
            #
            # Não utilizar select_related aqui.
            # coluna_kanban pode aceitar NULL e gerar LEFT OUTER JOIN.
            # ================================================================
            solicitacao = (
                Solicitacao.objects
                .select_for_update(of=('self',))
                .get(id=solicitacao_id)
            )

            # A operação permitida é definida pelo tipo do card.
            if solicitacao.tipo_solicitacao == 'CARGA' and acao != 'expedir':
                raise ValueError('Solicitação de carga permite somente Expedir.')
            if solicitacao.tipo_solicitacao != 'CARGA' and acao != 'transferir':
                raise ValueError('Solicitação comum permite somente Transferir.')

            # Impede movimentação em cards finalizados.
            if solicitacao.status in [
                'CONCLUIDO',
                'CANCELADO',
            ]:
                raise ValueError(
                    'Este card já está concluído ou cancelado.'
                )

            # ================================================================
            # BLOQUEAR SOMENTE O EMPENHO
            #
            # of=('self',) impede que o PostgreSQL tente bloquear
            # outras tabelas usadas na consulta.
            # ================================================================
            empenho = (
                Empenho.objects
                .select_for_update(of=('self',))
                .filter(
                    solicitacao_id=solicitacao.id,
                    status__nome='Rascunho',
                )
                .order_by('id')
                .first()
            )

            if not empenho:
                raise ValueError(
                    'Nenhum empenho em rascunho foi encontrado '
                    'para esta solicitação.'
                )

            # ================================================================
            # BLOQUEAR SOMENTE OS ITENS
            #
            # Não usar select_related junto com select_for_update.
            # ================================================================
            itens = list(
                ItemEmpenho.objects
                .select_for_update(of=('self',))
                .filter(
                    id__in=itens_ids,
                    empenho_id=empenho.id,
                )
                .order_by('id')
            )

            if not itens:
                raise ValueError(
                    'Nenhum item válido foi encontrado.'
                )

            # Confirma que todos os itens enviados pertencem
            # ao empenho desta solicitação.
            ids_encontrados = {
                item.id
                for item in itens
            }

            ids_solicitados = set(itens_ids)

            if ids_encontrados != ids_solicitados:
                raise ValueError(
                    'Um ou mais itens não pertencem '
                    'a esta solicitação.'
                )

            # ================================================================
            # DADOS DA AÇÃO
            # ================================================================
            novo_endereco = ''
            novo_az = ''
            numero_carga = ''
            cliente_expedicao = ''
            placa = ''
            motorista_expedicao = ''

            if acao == 'transferir':
                novo_endereco = str(
                    data.get('novo_endereco') or ''
                ).strip().upper()

                novo_az = str(
                    data.get('az') or ''
                ).strip().upper()

                if not novo_endereco:
                    raise ValueError(
                        'Novo endereço não informado '
                        'para transferência.'
                    )

                # ============================================================
                # VALIDAR ENDEREÇO NO BACKEND
                #
                # Não confiar apenas no JavaScript.
                # Transferência só pode ir para um endereço cadastrado.
                # O AZ também é obtido do cadastro e não do valor enviado
                # pelo navegador.
                # ============================================================
                endereco_destino = (
                    Endereco.objects
                    .select_related('armazem')
                    .filter(
                        codigo__iexact=novo_endereco
                    )
                    .first()
                )

                if not endereco_destino:
                    raise ValueError(
                        f'O endereço "{novo_endereco}" não está '
                        'cadastrado no sistema. '
                        'Cadastre o endereço antes de transferir.'
                    )

                novo_endereco = (
                    endereco_destino.codigo
                    .strip()
                    .upper()
                )

                novo_az = (
                    endereco_destino.armazem.nome
                    if endereco_destino.armazem
                    else ''
                )

            else:
                numero_carga = str(
                    data.get('numero_carga') or ''
                ).strip()

                # Para uma solicitação do tipo CARGA, o identificador oficial
                # é o título sequencial do card (CARGA N). Não aceitamos um
                # texto digitado no modal como identidade da carga, pois isso
                # quebraria o agrupamento de vários lotes da mesma expedição.
                if str(getattr(solicitacao, 'tipo_solicitacao', '') or '').upper() == 'CARGA':
                    numero_carga = str(getattr(solicitacao, 'titulo', '') or '').strip()

                cliente_expedicao = str(
                    data.get('cliente') or ''
                ).strip()

                placa_informada = str(
                    data.get('placa') or ''
                ).strip().upper()

                # Se a tela de movimentação vier em branco, preserva a placa
                # cadastrada na própria solicitação de carga.
                placa = (
                    placa_informada
                    or str(getattr(solicitacao, 'placa', '') or '').strip().upper()
                )

                # Em cargas o motorista é definido na própria solicitação.
                motorista_expedicao = str(
                    getattr(solicitacao, 'motorista', '') or ''
                ).strip()

                if motorista_expedicao and empenho.motorista != motorista_expedicao:
                    empenho.motorista = motorista_expedicao
                    empenho.save(update_fields=['motorista', 'data_atualizacao'])

            total_movimentado_unidades = Decimal('0')
            total_movimentado_kg = Decimal('0')

            # ================================================================
            # PROCESSAR ITENS
            #
            # IMPORTANTE:
            # - origem (Estoque) é usada para movimentar o saldo físico atual.
            # - item (ItemEmpenho) é usado para auditoria/impressão, pois guarda
            #   o retrato do lote no momento em que foi empenhado.
            # ================================================================
            for item in itens:

                # ------------------------------------------------------------
                # BLOQUEAR SOMENTE O ESTOQUE DE ORIGEM
                #
                # Não utilizar select_related aqui.
                # cultivar, peneira, tratamento etc. podem aceitar NULL.
                # ------------------------------------------------------------
                origem = (
                    Estoque.objects
                    .select_for_update(of=('self',))
                    .get(id=item.estoque_id)
                )

                quantidade = Decimal(
                    str(item.quantidade or 0)
                )

                saldo_atual = Decimal(
                    str(origem.saldo or 0)
                )

                quantidade_reservada = Decimal(
                    str(origem.empenhado or 0)
                )

                peso_unitario = Decimal(
                    str(origem.peso_unitario or 0)
                )

                if quantidade <= 0:
                    raise ValueError(
                        f'Quantidade inválida para '
                        f'o lote {item.lote}.'
                    )

                if quantidade > saldo_atual:
                    raise ValueError(
                        f'Saldo insuficiente para o lote '
                        f'{item.lote}. Saldo atual: '
                        f'{origem.saldo}.'
                    )

                if quantidade > quantidade_reservada:
                    raise ValueError(
                        f'A quantidade reservada do lote '
                        f'{item.lote} é insuficiente.'
                    )

                # ============================================================
                # TRANSFERÊNCIA
                # ============================================================
                if acao == 'transferir':

                    az_destino = (
                        novo_az
                        or origem.az
                        or ''
                    )

                    endereco_origem = (
                        origem.endereco or ''
                    )

                    az_origem = (
                        origem.az or ''
                    )

                    # Impede transferência para o mesmo local.
                    if (
                        endereco_origem.strip().upper()
                        == novo_endereco
                        and
                        az_origem.strip().upper()
                        == az_destino.strip().upper()
                    ):
                        raise ValueError(
                            f'O lote {origem.lote} já está no '
                            f'endereço {novo_endereco}, '
                            f'AZ {az_destino or "-"}.'
                        )

                    # --------------------------------------------------------
                    # BUSCAR ESTOQUE DE DESTINO
                    #
                    # Não há select_related nesta consulta.
                    # O bloqueio fica somente em Estoque.
                    # --------------------------------------------------------
                    destino = (
                        Estoque.objects
                        .select_for_update(of=('self',))
                        .filter(
                            lote=origem.lote,
                            produto=origem.produto,
                            cultivar=origem.cultivar,
                            peneira=origem.peneira,
                            categoria=origem.categoria,
                            tratamento=origem.tratamento,
                            especie=origem.especie,
                            endereco=novo_endereco,
                            az=az_destino,
                            empresa=origem.empresa,
                            embalagem=origem.embalagem,
                            cliente=origem.cliente,
                            peso_unitario=origem.peso_unitario,
                        )
                        .order_by('id')
                        .first()
                    )

                    # Caso não exista estoque no destino,
                    # cria um novo registro.
                    if not destino:
                        destino = Estoque.objects.create(
                            lote=origem.lote,
                            produto=origem.produto,
                            cultivar=origem.cultivar,
                            peneira=origem.peneira,
                            categoria=origem.categoria,
                            tratamento=origem.tratamento,
                            especie=origem.especie,
                            endereco=novo_endereco,
                            az=az_destino,
                            entrada=Decimal('0'),
                            saida=Decimal('0'),
                            empenhado=Decimal('0'),
                            peso_unitario=origem.peso_unitario,
                            embalagem=origem.embalagem,
                            conferente=request.user,
                            empresa=origem.empresa,
                            cliente=origem.cliente,
                            observacao=origem.observacao,
                            status_sistemico=(
                                origem.status_sistemico
                            ),
                        )

                    # Entrada no destino.
                    destino.entrada = (
                        Decimal(
                            str(destino.entrada or 0)
                        )
                        + quantidade
                    )

                    # Salva normalmente para o model.save()
                    # recalcular campos derivados.
                    destino.save()

                    # Saída da origem.
                    origem.saida = (
                        Decimal(
                            str(origem.saida or 0)
                        )
                        + quantidade
                    )

                    origem.save()

                    # --------------------------------------------------------
                    # HISTÓRICO DA SAÍDA
                    # --------------------------------------------------------
                    HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        quantidade=quantidade,
                        tipo='Transferência (Saída)',
                        descricao=(
                            f'Transferido {quantidade} un '
                            f'de {endereco_origem or "-"} '
                            f'(AZ {az_origem or "-"}) para '
                            f'{novo_endereco} '
                            f'(AZ {az_destino or "-"}).'
                        )
                    )

                    # --------------------------------------------------------
                    # HISTÓRICO DA ENTRADA
                    # --------------------------------------------------------
                    HistoricoMovimentacao.objects.create(
                        estoque=destino,
                        usuario=request.user,
                        quantidade=quantidade,
                        tipo='Transferência (Entrada)',
                        descricao=(
                            f'Recebido {quantidade} un '
                            f'em {novo_endereco} '
                            f'(AZ {az_destino or "-"}), '
                            f'vindo de {endereco_origem or "-"} '
                            f'(AZ {az_origem or "-"}).'
                        )
                    )

                    # --------------------------------------------------------
                    # HISTÓRICO DO ITEM DO EMPENHO
                    # --------------------------------------------------------
                    HistoricoItemEmpenho.objects.create(
                        empenho=empenho,
                        item_empenho_id_original=item.id,
                        item_carga_id_original=item.item_carga_id,
                        cliente_solicitacao=item.cliente_solicitacao_snapshot or '',
                        codigo_produto=item.codigo_produto_snapshot or '',
                        descricao_produto=item.descricao_produto_snapshot or '',
                        estoque_origem=origem,
                        estoque_destino=destino,

                        # SNAPSHOT DO MOMENTO DO EMPENHO.
                        lote=(
                            item.lote
                            or origem.lote
                            or ''
                        ),

                        produto=(
                            item.produto_snapshot
                            or origem.produto
                            or ''
                        ),

                        cultivar=(
                            item.cultivar
                            or (
                                origem.cultivar.nome
                                if origem.cultivar
                                else ''
                            )
                        ),

                        peneira=(
                            item.peneira
                            or (
                                origem.peneira.nome
                                if origem.peneira
                                else ''
                            )
                        ),

                        categoria=(
                            item.categoria
                            or (
                                origem.categoria.nome
                                if origem.categoria
                                else ''
                            )
                        ),

                        tratamento=(
                            item.tratamento_snapshot
                            or (
                                origem.tratamento.nome
                                if origem.tratamento
                                else ''
                            )
                        ),

                        especie=(
                            item.especie_snapshot
                            or (
                                origem.especie.nome
                                if origem.especie
                                else ''
                            )
                        ),

                        embalagem=(
                            item.embalagem_snapshot
                            or origem.embalagem
                            or ''
                        ),

                        empresa=(
                            item.empresa_snapshot
                            or origem.empresa
                            or ''
                        ),

                        cliente=(
                            item.cliente_snapshot
                            or origem.cliente
                            or ''
                        ),

                        endereco_origem=(
                            item.endereco_origem
                            or origem.endereco
                            or ''
                        ),

                        az_origem=(
                            item.az_origem
                            or origem.az
                            or ''
                        ),

                        saldo_anterior=(
                            item.saldo_anterior
                            or 0
                        ),

                        peso_unitario=(
                            item.peso_unitario_snapshot
                            or origem.peso_unitario
                            or 0
                        ),

                        observacao_origem=(
                            item.observacao_snapshot
                            or ''
                        ),

                        conferente=(
                            item.conferente_snapshot
                            or ''
                        ),

                        # Dado da movimentação posterior.
                        endereco_destino=novo_endereco,

                        quantidade=quantidade,
                        tipo='transferencia',

                        # Observação digitada na transferência.
                        observacao=observacao,

                        processado_por=request.user,
                    )

                    descricao_feed = (
                        f'Transferido {quantidade} un '
                        f'de {endereco_origem or "-"} '
                        f'(AZ {az_origem or "-"}) para '
                        f'{novo_endereco} '
                        f'(AZ {az_destino or "-"}).'
                    )

                    if observacao:
                        descricao_feed += (
                            f' Observação: {observacao}'
                        )

                # ============================================================
                # EXPEDIÇÃO
                # ============================================================
                else:
                    endereco_origem = (
                        origem.endereco or ''
                    )

                    az_origem = (
                        origem.az or ''
                    )

                    # Em uma carga cada linha pode pertencer a um cliente
                    # diferente. O cliente cadastrado no item da solicitação
                    # prevalece sobre qualquer campo global da expedição.
                    cliente_movimentacao_item = (
                        item.cliente_solicitacao_snapshot
                        or cliente_expedicao
                        or origem.cliente
                        or ''
                    )

                    origem.saida = (
                        Decimal(
                            str(origem.saida or 0)
                        )
                        + quantidade
                    )

                    origem.save()

                    descricao_movimentacao = (
                        f'Expedido {quantidade} un '
                        f'do lote {origem.lote}, '
                        f'endereço {endereco_origem or "-"}, '
                        f'AZ {az_origem or "-"}.'
                    )

                    if numero_carga:
                        descricao_movimentacao += (
                            f' Carga: {numero_carga}.'
                        )

                    if cliente_movimentacao_item:
                        descricao_movimentacao += (
                            f' Cliente: {cliente_movimentacao_item}.'
                        )

                    if motorista_expedicao:
                        descricao_movimentacao += (
                            f' Motorista: {motorista_expedicao}.'
                        )

                    if placa:
                        descricao_movimentacao += (
                            f' Placa: {placa}.'
                        )

                    if observacao:
                        descricao_movimentacao += (
                            f' Observação: {observacao}'
                        )

                    HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        quantidade=quantidade,
                        tipo='Expedição',
                        descricao=descricao_movimentacao,
                        numero_carga=(
                            numero_carga or None
                        ),
                        cliente=cliente_movimentacao_item,
                        motorista=motorista_expedicao or None,
                        placa=placa or None,
                        origem_carga='GERADA',
                    )

                    HistoricoItemEmpenho.objects.create(
                        empenho=empenho,
                        item_empenho_id_original=item.id,
                        item_carga_id_original=item.item_carga_id,
                        cliente_solicitacao=item.cliente_solicitacao_snapshot or '',
                        codigo_produto=item.codigo_produto_snapshot or '',
                        descricao_produto=item.descricao_produto_snapshot or '',
                        estoque_origem=origem,

                        # SNAPSHOT DO MOMENTO DO EMPENHO.
                        lote=(
                            item.lote
                            or origem.lote
                            or ''
                        ),

                        produto=(
                            item.produto_snapshot
                            or origem.produto
                            or ''
                        ),

                        cultivar=(
                            item.cultivar
                            or (
                                origem.cultivar.nome
                                if origem.cultivar
                                else ''
                            )
                        ),

                        peneira=(
                            item.peneira
                            or (
                                origem.peneira.nome
                                if origem.peneira
                                else ''
                            )
                        ),

                        categoria=(
                            item.categoria
                            or (
                                origem.categoria.nome
                                if origem.categoria
                                else ''
                            )
                        ),

                        tratamento=(
                            item.tratamento_snapshot
                            or (
                                origem.tratamento.nome
                                if origem.tratamento
                                else ''
                            )
                        ),

                        especie=(
                            item.especie_snapshot
                            or (
                                origem.especie.nome
                                if origem.especie
                                else ''
                            )
                        ),

                        embalagem=(
                            item.embalagem_snapshot
                            or origem.embalagem
                            or ''
                        ),

                        empresa=(
                            item.empresa_snapshot
                            or origem.empresa
                            or ''
                        ),

                        # Cliente abaixo é o cliente original do empenho.
                        # O cliente informado na expedição continua no
                        # HistoricoMovimentacao/feed.
                        cliente=(
                            item.cliente_snapshot
                            or origem.cliente
                            or ''
                        ),

                        endereco_origem=(
                            item.endereco_origem
                            or origem.endereco
                            or ''
                        ),

                        az_origem=(
                            item.az_origem
                            or origem.az
                            or ''
                        ),

                        saldo_anterior=(
                            item.saldo_anterior
                            or 0
                        ),

                        peso_unitario=(
                            item.peso_unitario_snapshot
                            or origem.peso_unitario
                            or 0
                        ),

                        observacao_origem=(
                            item.observacao_snapshot
                            or ''
                        ),

                        conferente=(
                            item.conferente_snapshot
                            or ''
                        ),

                        quantidade=quantidade,
                        tipo='expedicao',

                        # Observação da operação.
                        observacao=observacao,

                        numero_carga=numero_carga or '',
                        placa=placa or '',
                        processado_por=request.user,
                    )

                    descricao_feed = (
                        f'Expedido {quantidade} un '
                        f'de {endereco_origem or "-"} '
                        f'(AZ {az_origem or "-"}).'
                    )

                    if numero_carga:
                        descricao_feed += (
                            f' Carga: {numero_carga}.'
                        )

                    if cliente_movimentacao_item:
                        descricao_feed += (
                            f' Cliente: {cliente_movimentacao_item}.'
                        )

                    if motorista_expedicao:
                        descricao_feed += (
                            f' Motorista: {motorista_expedicao}.'
                        )

                    if placa:
                        descricao_feed += (
                            f' Placa: {placa}.'
                        )

                    if observacao:
                        descricao_feed += (
                            f' Observação: {observacao}'
                        )

                # ============================================================
                # SOMAR MOVIMENTAÇÃO
                # ============================================================
                total_movimentado_unidades += quantidade

                total_movimentado_kg += (
                    quantidade
                    * peso_unitario
                )

                # ------------------------------------------------------------
                # HISTÓRICO DO CARD
                #
                # Para solicitação em KG, registra a quantidade em KG.
                # ------------------------------------------------------------
                if (
                    solicitacao.unidade_controle
                    == 'QUILOGRAMA'
                ):
                    quantidade_historico = (
                        quantidade
                        * peso_unitario
                    )
                    unidade_historico = 'KG'
                else:
                    quantidade_historico = quantidade
                    unidade_historico = 'BAG'

                HistoricoCard.objects.create(
                    solicitacao=solicitacao,
                    usuario=request.user,
                    acao=(
                        'TRANSFERENCIA'
                        if acao == 'transferir'
                        else 'EXPEDICAO'
                    ),
                    lote=origem.lote,
                    quantidade=quantidade_historico,
                    unidade=unidade_historico,
                    observacao=descricao_feed,
                )

                # ------------------------------------------------------------
                # EXCLUIR ITEM DO EMPENHO
                #
                # Executa o delete personalizado e libera a reserva
                # existente em Estoque.empenhado.
                # ------------------------------------------------------------
                item.delete()

            # ================================================================
            # QUANTIDADE MOVIMENTADA NESTA OPERAÇÃO
            # ================================================================
            if (
                solicitacao.unidade_controle
                == 'QUILOGRAMA'
            ):
                quantidade_movimentada_agora = (
                    total_movimentado_kg
                )
            else:
                quantidade_movimentada_agora = (
                    total_movimentado_unidades
                )

            solicitacao.quantidade_movimentada = (
                Decimal(
                    str(
                        solicitacao.quantidade_movimentada
                        or 0
                    )
                )
                + quantidade_movimentada_agora
            )

            # ================================================================
            # RECALCULAR QUANTIDADE AINDA EMPENHADA
            # ================================================================
            if (
                solicitacao.unidade_controle
                == 'QUILOGRAMA'
            ):
                total_restante_kg = Decimal('0')

                itens_restantes = (
                    ItemEmpenho.objects
                    .filter(
                        empenho_id=empenho.id
                    )
                    .values(
                        'quantidade',
                        'estoque__peso_unitario',
                    )
                )

                for item_restante in itens_restantes:
                    quantidade_restante = Decimal(
                        str(
                            item_restante.get(
                                'quantidade'
                            )
                            or 0
                        )
                    )

                    peso_restante = Decimal(
                        str(
                            item_restante.get(
                                'estoque__peso_unitario'
                            )
                            or 0
                        )
                    )

                    total_restante_kg += (
                        quantidade_restante
                        * peso_restante
                    )

                solicitacao.quantidade_empenhada = (
                    total_restante_kg
                )

            else:
                total_restante_unidades = (
                    empenho.itens.aggregate(
                        total=Sum('quantidade')
                    )['total']
                    or 0
                )

                solicitacao.quantidade_empenhada = (
                    Decimal(
                        str(total_restante_unidades)
                    )
                )

            # ================================================================
            # ATUALIZAR STATUS DA SOLICITAÇÃO
            # ================================================================
            quantidade_solicitada = Decimal(
                str(
                    solicitacao.quantidade_solicitada
                    or 0
                )
            )

            quantidade_movimentada = Decimal(
                str(
                    solicitacao.quantidade_movimentada
                    or 0
                )
            )

            if (
                quantidade_movimentada
                >= quantidade_solicitada
            ):
                solicitacao.quantidade_movimentada = (
                    quantidade_solicitada
                )

                solicitacao.status = 'CONCLUIDO'

                evento = (
                    'TRANSFERENCIA_COMPLETA'
                    if acao == 'transferir'
                    else 'EXPEDICAO_COMPLETA'
                )

            elif quantidade_movimentada > 0:
                solicitacao.status = (
                    'MOVIMENTACAO_PARCIAL'
                )

                evento = 'MOVIMENTACAO_PARCIAL'

            else:
                evento = None

            solicitacao.save(
                update_fields=[
                    'quantidade_movimentada',
                    'quantidade_empenhada',
                    'status',
                    'data_atualizacao',
                ]
            )

            # ================================================================
            # EXECUTAR WORKFLOW
            # ================================================================
            if evento:
                avaliar_workflow(
                    solicitacao,
                    evento,
                    request.user
                )

            # ================================================================
            # LIMPAR CACHE
            # ================================================================
            from django.core.cache import cache

            cache.delete(
                'cards_version_hash'
            )

            # ================================================================
            # COLUNA DO KANBAN
            #
            # Ela é buscada somente agora, depois dos bloqueios.
            # ================================================================
            coluna_kanban_nome = ''

            if solicitacao.coluna_kanban_id:
                coluna_kanban_nome = (
                    ColunaKanban.objects
                    .filter(
                        id=solicitacao.coluna_kanban_id
                    )
                    .values_list(
                        'nome',
                        flat=True
                    )
                    .first()
                    or ''
                )

            return JsonResponse(
                {
                    'success': True,

                    'message': (
                        f'{len(itens)} item(ns) '
                        f'{"transferido(s)" if acao == "transferir" else "expedido(s)"} '
                        f'com sucesso.'
                    ),

                    'movimentado_agora': float(
                        quantidade_movimentada_agora
                    ),

                    'total_movimentado': float(
                        solicitacao.quantidade_movimentada
                    ),

                    'quantidade_empenhada': float(
                        solicitacao.quantidade_empenhada
                    ),

                    'quantidade_solicitada': float(
                        solicitacao.quantidade_solicitada
                    ),

                    'percentual': float(
                        solicitacao.percentual_movimentado
                    ),

                    'status': solicitacao.status,

                    'concluido': (
                        solicitacao.status
                        == 'CONCLUIDO'
                    ),

                    'coluna_kanban': (
                        coluna_kanban_nome
                    ),
                }
            )

    except Solicitacao.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Solicitação não encontrada.'
            },
            status=404
        )

    except Estoque.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': (
                    'O estoque de um dos itens '
                    'não foi encontrado.'
                )
            },
            status=404
        )

    except ValueError as erro:
        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=400
        )

    except Exception as erro:
        logger.exception(
            'Erro ao movimentar a solicitação %s',
            solicitacao_id
        )

        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=500
        )


@login_required
def api_dados_impressao_solicitacao(
    request,
    solicitacao_id
):
    """
    Dados para:
    - impressão da Solicitação;
    - modal de Transferência/Expedição.

    REGRA DE AUDITORIA:
    os dados exibidos representam o estado do lote no momento
    do EMPENHO.

    Nunca usamos o endereço de destino da transferência como
    endereço original do item.
    """

    solicitacao = get_object_or_404(
        Solicitacao.objects.select_related(
            'criador',
            'armazem',
            'especie',
        ),
        id=solicitacao_id
    )

    empenho = (
        Empenho.objects
        .filter(
            solicitacao_id=solicitacao.id
        )
        .order_by('-data_criacao')
        .first()
    )

    itens_pendentes = []
    itens_processados = []

    def nome_usuario(usuario):
        if not usuario:
            return ''

        return (
            usuario.get_full_name()
            or usuario.username
            or ''
        )

    produto_config_cache = {}

    def produto_config_por_codigo(codigo):
        chave = str(codigo or '').strip().upper()
        if not chave:
            return None
        if chave not in produto_config_cache:
            produto_config_cache[chave] = (
                Produto.objects
                .select_related('categoria', 'peneira')
                .filter(codigo__iexact=chave)
                .first()
            )
        return produto_config_cache[chave]

    if empenho:
        # ----------------------------------------------------
        # PENDENTES
        #
        # A FK estoque continua disponível para operação
        # física, mas a exibição usa prioritariamente snapshot.
        # ----------------------------------------------------
        itens = (
            ItemEmpenho.objects
            .filter(empenho__solicitacao_id=solicitacao.id)
            .select_related(
                'estoque',
                'estoque__cultivar',
                'estoque__peneira',
                'estoque__categoria',
                'estoque__especie',
                'estoque__tratamento',
                'estoque__conferente',
                'item_carga',
            )
            .order_by('empenho_id', 'id')
        )

        for item in itens:
            estoque = item.estoque

            peso_unitario = Decimal(
                str(
                    item.peso_unitario_snapshot
                    or 0
                )
            )

            if (
                peso_unitario <= 0
                and estoque
            ):
                peso_unitario = Decimal(
                    str(
                        estoque.peso_unitario
                        or 0
                    )
                )

            saldo_no_empenho = Decimal(
                str(
                    item.saldo_anterior
                    or 0
                )
            )

            endereco_empenho = (
                item.endereco_origem
                or (
                    estoque.endereco
                    if estoque
                    else ''
                )
            )

            armazem_empenho = (
                item.az_origem
                or (
                    estoque.az
                    if estoque
                    else ''
                )
            )

            produto_empenho = (
                item.produto_snapshot
                or (
                    estoque.produto
                    if estoque
                    else ''
                )
            )

            especie_empenho = (
                item.especie_snapshot
                or (
                    estoque.especie.nome
                    if (
                        estoque
                        and estoque.especie
                    )
                    else ''
                )
            )

            tratamento_empenho = (
                item.tratamento_snapshot
                or (
                    estoque.tratamento.nome
                    if (
                        estoque
                        and estoque.tratamento
                    )
                    else ''
                )
            )

            embalagem_empenho = (
                item.embalagem_snapshot
                or (
                    estoque.embalagem
                    if estoque
                    else ''
                )
            )

            empresa_empenho = (
                item.empresa_snapshot
                or (
                    estoque.empresa
                    if estoque
                    else ''
                )
            )

            cliente_empenho = (
                item.cliente_snapshot
                or (
                    estoque.cliente
                    if estoque
                    else ''
                )
            )

            observacao_empenho = (
                item.observacao_snapshot
                or item.observacao
                or ''
            )

            conferente_empenho = (
                item.conferente_snapshot
                or (
                    nome_usuario(
                        estoque.conferente
                    )
                    if estoque
                    else ''
                )
            )

            quantidade = Decimal(
                str(
                    item.quantidade
                    or 0
                )
            )

            codigo_impressao = (
                (item.item_carga.codigo if item.item_carga else '')
                or item.codigo_produto_snapshot
                or produto_empenho
            )
            produto_config = produto_config_por_codigo(codigo_impressao)
            descricao_impressao = (
                (produto_config.descricao if produto_config else '')
                or item.descricao_produto_snapshot
                or (item.item_carga.descricao if item.item_carga else '')
                or ''
            )
            # Categoria e peneira pertencem ao LOTE EMPENHADO.
            # Configurações é consultada somente para a descrição.
            categoria_impressao = (
                item.categoria
                or (estoque.categoria.nome if estoque and estoque.categoria else '')
                or ''
            )
            peneira_impressao = (
                item.peneira
                or (estoque.peneira.nome if estoque and estoque.peneira else '')
                or ''
            )
            cliente_impressao = (
                item.cliente_solicitacao_snapshot
                or (item.item_carga.cliente if item.item_carga else '')
                or cliente_empenho
            )
            if solicitacao.tipo_solicitacao != 'CARGA':
                cliente_impressao = solicitacao.cliente or 'CS'

            itens_pendentes.append({
                'item_id': item.id,
                'item_carga_id': item.item_carga_id,
                'codigo': codigo_impressao,
                'descricao': descricao_impressao,

                'lote': (
                    item.lote
                    or (
                        estoque.lote
                        if estoque
                        else ''
                    )
                ),

                'quantidade': float(
                    quantidade
                ),

                # "saldo_atual" é mantido por compatibilidade
                # com o JS antigo, mas agora significa
                # SALDO NO MOMENTO DO EMPENHO.
                'saldo_atual': float(
                    saldo_no_empenho
                ),

                'saldo_empenho': float(
                    saldo_no_empenho
                ),

                'endereco': endereco_empenho,

                # Dois nomes para compatibilidade.
                'az': armazem_empenho,
                'armazem': armazem_empenho,

                'produto': produto_empenho,

                'cultivar': (
                    item.cultivar
                    or (
                        estoque.cultivar.nome
                        if (
                            estoque
                            and estoque.cultivar
                        )
                        else ''
                    )
                ),

                'peneira': peneira_impressao,

                'categoria': categoria_impressao,

                'especie': especie_empenho,
                'tratamento': tratamento_empenho,
                'embalagem': embalagem_empenho,
                'empresa': empresa_empenho,
                'cliente': cliente_impressao,

                'peso_unitario': str(
                    peso_unitario
                ),

                'peso_total': str(
                    quantidade
                    * peso_unitario
                ),

                'observacao': (
                    observacao_empenho
                ),

                'conferente': (
                    conferente_empenho
                ),

                'situacao': 'pendente',

                'data_empenho': (
                    timezone.localtime(item.data_criacao).strftime(
                        '%d/%m/%Y %H:%M'
                    )
                    if item.data_criacao
                    else ''
                ),
                'data_ultima_movimentacao': (
                    timezone.localtime(estoque.data_ultima_movimentacao).strftime('%d/%m/%Y %H:%M')
                    if estoque and estoque.data_ultima_movimentacao
                    else ''
                ),
            })

        # ----------------------------------------------------
        # PROCESSADOS
        #
        # Estes registros já são históricos. Não usamos
        # estoque_destino para substituir o endereço original.
        # ----------------------------------------------------
        historicos = (
            HistoricoItemEmpenho.objects
            .filter(empenho__solicitacao_id=solicitacao.id)
            .select_related(
                'estoque_origem',
                'estoque_origem__conferente',
            )
            .order_by(
                'processado_em',
                'id',
            )
        )

        for historico in historicos:
            origem_legada = (
                historico.estoque_origem
            )

            peso_unitario = Decimal(
                str(
                    historico.peso_unitario
                    or 0
                )
            )

            if (
                peso_unitario <= 0
                and origem_legada
            ):
                peso_unitario = Decimal(
                    str(
                        origem_legada.peso_unitario
                        or 0
                    )
                )

            saldo_no_empenho = Decimal(
                str(
                    historico.saldo_anterior
                    or 0
                )
            )

            armazem_empenho = (
                historico.az_origem
                or (
                    origem_legada.az
                    if origem_legada
                    else ''
                )
            )

            observacao_origem = (
                historico.observacao_origem
                or ''
            )

            quantidade = Decimal(
                str(
                    historico.quantidade
                    or 0
                )
            )

            codigo_impressao = historico.codigo_produto or historico.produto or ''
            produto_config = produto_config_por_codigo(codigo_impressao)
            descricao_impressao = (
                (produto_config.descricao if produto_config else '')
                or historico.descricao_produto
                or ''
            )
            categoria_impressao = historico.categoria or ''
            peneira_impressao = historico.peneira or ''
            cliente_impressao = historico.cliente_solicitacao or historico.cliente or ''
            if solicitacao.tipo_solicitacao != 'CARGA':
                cliente_impressao = solicitacao.cliente or 'CS'

            itens_processados.append({
                'item_id': historico.id,
                'item_carga_id': historico.item_carga_id_original,
                'codigo': codigo_impressao,
                'descricao': descricao_impressao,

                'lote': (
                    historico.lote
                    or ''
                ),

                'quantidade': float(
                    quantidade
                ),

                'saldo_atual': float(
                    saldo_no_empenho
                ),

                'saldo_empenho': float(
                    saldo_no_empenho
                ),

                # ORIGEM DO EMPENHO.
                'endereco': (
                    historico.endereco_origem
                    or ''
                ),

                'az': armazem_empenho,
                'armazem': armazem_empenho,

                'produto': (
                    historico.produto
                    or ''
                ),

                'cultivar': (
                    historico.cultivar
                    or ''
                ),

                'peneira': peneira_impressao,

                'categoria': categoria_impressao,

                'especie': (
                    historico.especie
                    or ''
                ),

                'tratamento': (
                    historico.tratamento
                    or ''
                ),

                'embalagem': (
                    historico.embalagem
                    or ''
                ),

                'empresa': (
                    historico.empresa
                    or ''
                ),

                'cliente': cliente_impressao,

                'peso_unitario': str(
                    peso_unitario
                ),

                'peso_total': str(
                    quantidade
                    * peso_unitario
                ),

                # Observação original do lote no empenho.
                'observacao': (
                    observacao_origem
                ),

                # Observação digitada na operação.
                'observacao_movimentacao': (
                    historico.observacao
                    or ''
                ),

                'conferente': (
                    historico.conferente
                    or ''
                ),

                'tipo': (
                    historico.get_tipo_display()
                ),

                'processado_em': (
                    timezone.localtime(historico.processado_em).strftime(
                        '%d/%m/%Y %H:%M'
                    )
                    if historico.processado_em
                    else ''
                ),
                'data_ultima_movimentacao': (
                    timezone.localtime(historico.processado_em).strftime('%d/%m/%Y %H:%M')
                    if historico.processado_em
                    else ''
                ),

                'situacao': (
                    'transferido'
                    if (
                        historico.tipo
                        == 'transferencia'
                    )
                    else 'expedido'
                ),

                # Destino continua disponível separadamente
                # para auditoria, mas NÃO substitui endereço.
                'endereco_destino': (
                    historico.endereco_destino
                    if (
                        historico.tipo
                        == 'transferencia'
                    )
                    else ''
                ),
            })

    return JsonResponse({
        'success': True,
        'emitido_em': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),

        'empenho_id': (
            empenho.id
            if empenho
            else None
        ),

        'solicitacao': {
            'id': solicitacao.id,
            'titulo': solicitacao.titulo,
            'tipo_solicitacao': solicitacao.tipo_solicitacao,
            'tipo_solicitacao_display': solicitacao.get_tipo_solicitacao_display(),

            'criador': (
                solicitacao.criador.get_full_name()
                or solicitacao.criador.username
            ),

            'data_criacao': (
                timezone.localtime(solicitacao.data_criacao).strftime(
                    '%d/%m/%Y %H:%M'
                )
                if solicitacao.data_criacao else ''
            ),

            'data_atualizacao': (
                timezone.localtime(solicitacao.data_atualizacao).strftime(
                    '%d/%m/%Y %H:%M'
                )
                if solicitacao.data_atualizacao
                else ''
            ),

            'data_finalizacao': (
                timezone.localtime(solicitacao.data_finalizacao).strftime(
                    '%d/%m/%Y %H:%M'
                )
                if getattr(
                    solicitacao,
                    'data_finalizacao',
                    None
                )
                else ''
            ),

            'quantidade_solicitada': float(
                solicitacao.quantidade_solicitada
            ),

            'quantidade_empenhada': float(
                solicitacao.quantidade_empenhada
            ),

            'quantidade_movimentada': float(
                solicitacao.quantidade_movimentada
            ),

            'unidade_controle': (
                solicitacao.unidade_controle
            ),

            'status': solicitacao.status,
            'status_display': solicitacao.get_status_display(),

            'destino': (
                getattr(
                    solicitacao,
                    'destino',
                    ''
                )
                or ''
            ),

            'motorista': (
                getattr(solicitacao, 'motorista', '')
                or ''
            ),

            'placa': (
                getattr(solicitacao, 'placa', '')
                or ''
            ),

            'observacao': (
                solicitacao.observacao
                or ''
            ),

            'criterios': {
                'armazem': (
                    solicitacao.armazem.nome
                    if solicitacao.armazem
                    else ''
                ),

                'produto': (
                    solicitacao.produto
                    or ''
                ),

                'especie': (
                    solicitacao.especie.nome
                    if solicitacao.especie
                    else ''
                ),

                'cliente': (
                    solicitacao.cliente
                    or ''
                ),
            },
        },

        'itens_pendentes': (
            itens_pendentes
        ),

        'itens_processados': (
            itens_processados
        ),
    })

# ============================================================================
# ============================================================================


# BLOCO COMPLETO PARA sapp/views.py
# Remova/substitua as versões antigas das funções com o mesmo nome.

import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import (
    ColunaKanban,
    Empenho,
    HistoricoCard,
    HistoricoItemEmpenho,
    ItemEmpenho,
    Solicitacao,
    TagKanban,
)


def _formatar_data(valor):
    if not valor:
        return ''
    return timezone.localtime(valor).strftime('%d/%m/%Y %H:%M')


def _nome_usuario(usuario):
    if not usuario:
        return ''
    return usuario.get_full_name() or usuario.username


def _lotes_da_solicitacao(solicitacao):
    """
    Retorna lotes pendentes e já processados usando o vínculo
    Empenho.solicitacao. Não depende do título do card.
    """
    lotes = set()

    for empenho in solicitacao.empenhos.all():
        for item in empenho.itens.all():
            lote = str(item.lote or '').strip()
            if lote:
                lotes.add(lote)

        for item in empenho.historico_itens.all():
            lote = str(item.lote or '').strip()
            if lote:
                lotes.add(lote)

    return sorted(lotes)


def _serializar_tag(tag):
    return {
        'id': tag.id,
        'nome': tag.nome,
        'icone': tag.icone,
        'cor': tag.cor,
        'cor_texto': tag.cor_texto,
    }


def _serializar_card(solicitacao):
    if solicitacao.unidade_controle == 'QUILOGRAMA':
        qtd_empenhada_display = (
            solicitacao.quantidade_empenhada_kg
            or Decimal('0')
        )
    else:
        qtd_empenhada_display = Decimal(
            str(solicitacao.quantidade_empenhada or 0)
        )

    quantidade_solicitada = Decimal(
        str(solicitacao.quantidade_solicitada or 0)
    )

    percentual = (
        (qtd_empenhada_display / quantidade_solicitada) * 100
        if quantidade_solicitada > 0
        else (
            Decimal('100')
            if solicitacao.tipo_solicitacao == 'CARGA' and qtd_empenhada_display > 0
            else Decimal('0')
        )
    )

    embalagens = set()

    for empenho in solicitacao.empenhos.all():

        for item in empenho.itens.all():
            embalagem = str(
                getattr(
                    item,
                    'embalagem_snapshot',
                    ''
                )
                or ''
            ).strip().upper()

            if embalagem:
                embalagens.add(embalagem)

        for historico in empenho.historico_itens.all():
            embalagem = str(
                historico.embalagem
                or ''
            ).strip().upper()

            if embalagem:
                embalagens.add(embalagem)
                
    return {
        'id': solicitacao.id,
        'titulo': solicitacao.titulo,
        'tipo_solicitacao': solicitacao.tipo_solicitacao,
        'tipo_solicitacao_display': solicitacao.get_tipo_solicitacao_display(),
        'itens_carga': [
            {
                'id': item.id,
                'cliente': item.cliente,
                'codigo': item.codigo,
                'descricao': item.descricao,
                'categoria': item.categoria,
                'peneira': item.peneira,
                'quantidade_solicitada': float(item.quantidade_solicitada or 0),
            }
            for item in solicitacao.itens_carga.all()
        ],
        'observacao': solicitacao.observacao or '',
        'destino': solicitacao.destino or '',
        'motorista': getattr(solicitacao, 'motorista', '') or '',
        'placa': getattr(solicitacao, 'placa', '') or '',
        'criador_nome': _nome_usuario(solicitacao.criador),
        'responsavel_nome': _nome_usuario(solicitacao.responsavel),
        'data_criacao': _formatar_data(solicitacao.data_criacao),
        'data_finalizacao': (
            _formatar_data(solicitacao.data_finalizacao)
            if solicitacao.status == 'CONCLUIDO'
            else ''
        ),
        'status': solicitacao.status,
        'status_display': (
            solicitacao.get_status_display()
            if hasattr(solicitacao, 'get_status_display')
            else solicitacao.status
        ),
        'unidade_controle': solicitacao.unidade_controle,
        'quantidade_solicitada': float(quantidade_solicitada),
        'quantidade_empenhada': float(
            solicitacao.quantidade_empenhada or 0
        ),
        'quantidade_empenhada_display': float(
            qtd_empenhada_display
        ),
        'quantidade_movimentada': float(
            solicitacao.quantidade_movimentada or 0
        ),
        'percentual_empenhado': float(percentual),
        'percentual_movimentado': float(
            solicitacao.percentual_movimentado
        ),
        'prioridade': solicitacao.prioridade,
        'coluna_id': solicitacao.coluna_kanban_id,
        'coluna_nome': (
            solicitacao.coluna_kanban.nome
            if solicitacao.coluna_kanban
            else ''
        ),
        'criterios': {
            'armazem': (
                solicitacao.armazem.nome
                if solicitacao.armazem else ''
            ),
            'produto': solicitacao.produto or '',
            'especie': (
                solicitacao.especie.nome
                if solicitacao.especie else ''
            ),
            'cliente': (
                (solicitacao.cliente or 'CS')
                if solicitacao.tipo_solicitacao != 'CARGA'
                else ''
            ),
            'destino': solicitacao.destino or '',
            'motorista': getattr(solicitacao, 'motorista', '') or '',
            'placa': getattr(solicitacao, 'placa', '') or '',
        },
        'lotes': _lotes_da_solicitacao(solicitacao),


        'embalagens': sorted(
            embalagens
        ),

        'tags': [
            _serializar_tag(tag)
            for tag in solicitacao.tags_kanban.all()
        ],
    }


def _queryset_kanban():
    return (
        Solicitacao.objects
        .select_related(
            'criador',
            'responsavel',
            'armazem',
            'especie',
            'coluna_kanban',
        )
        .prefetch_related(
            'tags_kanban',
            'itens_carga',
            Prefetch(
                'empenhos',
                queryset=(
                    Empenho.objects
                    .prefetch_related('itens', 'historico_itens')
                    .order_by('id')
                ),
            ),
        )
    )


@login_required
def pagina_kanban(request):
    return render(
        request,
        'sapp/kanban.html',
        {
            'tags_kanban': TagKanban.objects.filter(
                ativa=True
            ).order_by('ordem', 'nome'),
        },
    )


@login_required
@require_GET
def api_kanban_dados(request):
    colunas = list(
        ColunaKanban.objects
        .filter(ativa=True)
        .order_by('ordem', 'nome')
    )

    solicitacoes = list(
        _queryset_kanban()
        .filter(coluna_kanban__in=colunas)
        .order_by('-prioridade', '-data_criacao')
    )

    por_coluna = {coluna.id: [] for coluna in colunas}

    for solicitacao in solicitacoes:
        if solicitacao.coluna_kanban_id in por_coluna:
            por_coluna[solicitacao.coluna_kanban_id].append(
                _serializar_card(solicitacao)
            )

    # Cargas avulsas concluídas também aparecem na faixa de Expedição. Elas
    # são cards somente de consulta e nunca se confundem com cargas GERADAS.
    coluna_concluida = next(
        (c for c in colunas if 'CONCLU' in str(c.nome or '').upper()),
        (colunas[-1] if colunas else None),
    )
    if coluna_concluida:
        grupos_avulsos = {}
        movimentos_avulsos = (
            HistoricoMovimentacao.objects
            .filter(origem_carga='AVULSA')
            .select_related('estoque', 'usuario')
            .order_by('-data_hora', '-id')[:1500]
        )
        for mov in movimentos_avulsos:
            nome = ' '.join(str(mov.nome_carga_avulsa or '').strip().split())
            numero = ' '.join(str(mov.numero_carga or '').strip().split())
            chave_base = normalizar_texto_cadastro(nome) if nome else normalizar_texto_cadastro(numero)
            if not chave_base:
                chave_base = f'REGISTRO-{mov.id}'
            chave = f'AVULSA:{chave_base}'
            grupo = grupos_avulsos.setdefault(chave, {
                'nome': nome or (f'CARGA {numero}' if numero else 'CARGA AVULSA'),
                'numero': numero,
                'data': mov.data_hora,
                'cliente': set(),
                'placa': set(),
                'motorista': set(),
                'lotes': set(),
                'qtd': Decimal('0'),
                'embalagens': set(),
                'usuario': mov.usuario,
            })
            grupo['qtd'] += Decimal(str(mov.quantidade or 0))
            if mov.cliente: grupo['cliente'].add(str(mov.cliente).strip())
            if mov.placa: grupo['placa'].add(str(mov.placa).strip().upper())
            if mov.motorista: grupo['motorista'].add(str(mov.motorista).strip())
            lote = str(mov.lote_ref or (mov.estoque.lote if mov.estoque else '') or '').strip()
            if lote: grupo['lotes'].add(lote)
            emb = str(mov.estoque.embalagem if mov.estoque else '').strip().upper()
            if emb: grupo['embalagens'].add(emb)

        for chave, grupo in grupos_avulsos.items():
            card = {
                'id': chave,
                'synthetic_avulsa': True,
                'titulo': grupo['nome'],
                'tipo_solicitacao': 'CARGA',
                'tipo_solicitacao_display': 'Carga avulsa',
                'origem_carga': 'AVULSA',
                'itens_carga': [],
                'observacao': '',
                'destino': '',
                'motorista': ' / '.join(sorted(grupo['motorista'])),
                'placa': ' / '.join(sorted(grupo['placa'])),
                'criador_nome': _nome_usuario(grupo['usuario']),
                'responsavel_nome': '',
                'data_criacao': _formatar_data(grupo['data']),
                'data_finalizacao': _formatar_data(grupo['data']),
                'status': 'CONCLUIDO',
                'status_display': 'Concluído',
                'unidade_controle': 'EMBALAGEM',
                'quantidade_solicitada': float(grupo['qtd']),
                'quantidade_empenhada': float(grupo['qtd']),
                'quantidade_empenhada_display': float(grupo['qtd']),
                'quantidade_movimentada': float(grupo['qtd']),
                'percentual_empenhado': 100.0,
                'percentual_movimentado': 100.0,
                'prioridade': 'MEDIA',
                'coluna_id': coluna_concluida.id,
                'coluna_nome': coluna_concluida.nome,
                'criterios': {
                    'cliente': ' / '.join(sorted(grupo['cliente'])),
                    'destino': '',
                    'motorista': ' / '.join(sorted(grupo['motorista'])),
                    'placa': ' / '.join(sorted(grupo['placa'])),
                },
                'lotes': sorted(grupo['lotes']),
                'embalagens': sorted(grupo['embalagens']),
                'tags': [],
            }
            por_coluna[coluna_concluida.id].append(card)

    return JsonResponse({
        'success': True,
        'colunas': [
            {
                'id': coluna.id,
                'nome': coluna.nome,
                'cor': coluna.cor,
                'total': len(por_coluna[coluna.id]),
                'cards': por_coluna[coluna.id],
            }
            for coluna in colunas
        ],
        'colunas_disponiveis': [
            {
                'id': coluna.id,
                'nome': coluna.nome,
                'cor': coluna.cor,
            }
            for coluna in colunas
        ],
        'tags_disponiveis': [
            _serializar_tag(tag)
            for tag in TagKanban.objects.filter(
                ativa=True
            ).order_by('ordem', 'nome')
        ],
        'timestamp': timezone.now().isoformat(),
    })


@login_required
@require_GET
def api_pesquisar_kanban(request):
    termo = request.GET.get('q', '').strip()

    if len(termo) < 2:
        return JsonResponse({
            'success': True,
            'resultados': [],
        })

    queryset = (
        _queryset_kanban()
        .filter(
            Q(titulo__icontains=termo)
            | Q(observacao__icontains=termo)
            | Q(destino__icontains=termo)
            | Q(cliente__icontains=termo)
            | Q(produto__icontains=termo)
            | Q(empenhos__itens__lote__icontains=termo)
            | Q(
                empenhos__historico_itens__lote__icontains=termo
            )
        )
        .distinct()
        .order_by('-data_criacao')[:50]
    )

    return JsonResponse({
        'success': True,
        'resultados': [
            {
                'id': solicitacao.id,
                'titulo': solicitacao.titulo,
                'status': solicitacao.status,
                'coluna_id': solicitacao.coluna_kanban_id,
                'coluna_nome': (
                    solicitacao.coluna_kanban.nome
                    if solicitacao.coluna_kanban else ''
                ),
                'lotes': _lotes_da_solicitacao(solicitacao),
                'destino': solicitacao.destino or '',
                'data_criacao': _formatar_data(
                    solicitacao.data_criacao
                ),
            }
            for solicitacao in queryset
        ],
    })


# views.py (ou api_views.py)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
import json
from .models import Solicitacao, ColunaKanban, HistoricoCard

@login_required
@require_POST
@csrf_protect
def mover_card_kanban(request, solicitacao_id):
    try:
        data = json.loads(request.body)
        coluna_id = data.get('coluna_id')
        observacao = data.get('observacao', '')

        if not coluna_id:
            return JsonResponse({'success': False, 'error': 'ID da coluna não informado.'}, status=400)

        solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)
        coluna_destino = get_object_or_404(ColunaKanban, pk=coluna_id, ativa=True)

        coluna_anterior = solicitacao.coluna_kanban.nome if solicitacao.coluna_kanban else 'Nenhuma'

        # Atualiza a coluna
        solicitacao.coluna_kanban = coluna_destino
        solicitacao.save(update_fields=['coluna_kanban', 'data_atualizacao'])

        # Registra no histórico
        HistoricoCard.objects.create(
            solicitacao=solicitacao,
            usuario=request.user,
            acao='MOVIMENTACAO_KANBAN',
            coluna_anterior=coluna_anterior,
            coluna_nova=coluna_destino.nome,
            observacao=observacao,
        )

        return JsonResponse({
            'success': True,
            'coluna_nova': coluna_destino.nome,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def api_atualizar_tags_card(request, solicitacao_id):
    try:
        dados = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'JSON inválido.'},
            status=400,
        )

    ids = dados.get('tags_ids', [])

    if not isinstance(ids, list):
        return JsonResponse(
            {'success': False, 'error': 'Lista de tags inválida.'},
            status=400,
        )

    ids_validos = [
        int(valor)
        for valor in ids
        if str(valor).isdigit()
    ]

    solicitacao = get_object_or_404(
        Solicitacao,
        id=solicitacao_id,
    )

    tags = TagKanban.objects.filter(
        id__in=ids_validos,
        ativa=True,
    )

    solicitacao.tags_kanban.set(tags)

    return JsonResponse({
        'success': True,
        'tags': [
            _serializar_tag(tag)
            for tag in solicitacao.tags_kanban.all()
        ],
    })


@login_required
@require_POST
def api_criar_tag_kanban(request):
    try:
        dados = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': 'JSON inválido.'},
            status=400,
        )

    nome = str(dados.get('nome', '')).strip()
    icone = str(dados.get('icone', '')).strip()
    cor = str(dados.get('cor', '#2f8f4e')).strip()

    if not nome:
        return JsonResponse(
            {'success': False, 'error': 'Informe o texto da tag.'},
            status=400,
        )

    tag, criada = TagKanban.objects.get_or_create(
        nome=nome,
        defaults={
            'icone': icone,
            'cor': cor,
            'cor_texto': '#ffffff',
            'ativa': True,
        },
    )

    if not criada:
        tag.icone = icone
        tag.cor = cor
        tag.ativa = True
        tag.save(
            update_fields=['icone', 'cor', 'ativa']
        )

    return JsonResponse({
        'success': True,
        'tag': _serializar_tag(tag),
    })


# ============================================================================
# EXCLUIR SOLICITAÇÃO
# ============================================================================
@login_required
def api_excluir_solicitacao(
    request,
    solicitacao_id
):
    """
    Exclui somente cards sem movimentação e sem histórico
    processado.

    Cards concluídos permanecem preservados para auditoria.
    """
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'Método não permitido.'
            },
            status=405
        )

    try:
        with transaction.atomic():
            solicitacao = (
                Solicitacao.objects
                .select_for_update()
                .get(id=solicitacao_id)
            )

            empenhos = list(
                Empenho.objects
                .select_for_update()
                .filter(
                    solicitacao_id=solicitacao.id
                )
            )

            possui_historico_processado = any(
                empenho.historico_itens.exists()
                for empenho in empenhos
            )

            if solicitacao.status in [
                'CONCLUIDO',
                'CANCELADO',
            ]:
                raise ValueError(
                    'Cards concluídos ou cancelados não '
                    'podem ser excluídos. Eles devem '
                    'permanecer no histórico.'
                )

            if solicitacao.quantidade_movimentada > 0:
                raise ValueError(
                    'Este card possui movimentações e não '
                    'pode ser excluído.'
                )

            if possui_historico_processado:
                raise ValueError(
                    'Este card possui itens transferidos ou '
                    'expedidos e não pode ser excluído.'
                )

            titulo = solicitacao.titulo

            # Importante:
            # removemos um item por vez para executar
            # ItemEmpenho.delete() e liberar Estoque.empenhado.
            for empenho in empenhos:
                for item in list(empenho.itens.all()):
                    item.delete()

                empenho.delete()

            HistoricoCard.objects.filter(
                solicitacao=solicitacao
            ).delete()

            solicitacao.delete()

            from django.core.cache import cache
            cache.delete('cards_version_hash')

            return JsonResponse({
                'success': True,
                'message': (
                    f'Card "{titulo}" excluído com sucesso!'
                )
            })

    except Solicitacao.DoesNotExist:
        return JsonResponse(
            {
                'success': False,
                'error': 'Card não encontrado.'
            },
            status=404
        )

    except ValueError as erro:
        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=400
        )

    except Exception as erro:
        logger.exception(
            'Erro ao excluir solicitação %s',
            solicitacao_id
        )

        return JsonResponse(
            {
                'success': False,
                'error': str(erro)
            },
            status=500
        )

# ============================================================================
# CONFIGURAÇÃO DO WORKFLOW
# ============================================================================
@login_required
def api_config_workflow(request):
    """GET: Retorna configurações. POST: Salva configurações."""
    if request.method == 'GET':
        colunas = ColunaKanban.objects.filter(ativa=True).order_by('ordem')
        regras = RegraWorkflow.objects.select_related('coluna').all()
        
        return JsonResponse({
            'success': True,
            'workflow': {
                'colunas': [{'id': c.id, 'nome': c.nome, 'cor': c.cor, 'ordem': c.ordem, 'ativa': c.ativa} for c in colunas],
                'regras': [{'id': r.id, 'coluna_id': r.coluna.id, 'coluna_nome': r.coluna.nome, 'evento': r.evento, 'evento_display': r.get_evento_display(), 'status_resultante': r.status_resultante, 'movimentacao_automatica': r.movimentacao_automatica} for r in regras],
                'eventos_disponiveis': [{'value': e[0], 'label': e[1]} for e in RegraWorkflow.EVENTO_CHOICES],
                'status_disponiveis': ['AGUARDANDO_EMPENHO', 'EMPENHO_PARCIAL', 'EMPENHO_COMPLETO', 'MOVIMENTACAO_PARCIAL', 'CONCLUIDO', 'CANCELADO'],
            }
        })
    
    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            
            # Processar colunas
            if 'colunas' in payload:
                for col_data in payload['colunas']:
                    col_id = col_data.get('id')
                    
                    if col_id and int(col_id) > 0 and ColunaKanban.objects.filter(id=col_id).exists():
                        coluna = ColunaKanban.objects.get(id=col_id)
                        if 'nome' in col_data: coluna.nome = col_data['nome']
                        if 'cor' in col_data: coluna.cor = col_data['cor']
                        if 'ordem' in col_data: coluna.ordem = col_data['ordem']
                        if 'ativa' in col_data: coluna.ativa = col_data['ativa']
                        coluna.save()
                    else:
                        nome = col_data.get('nome', 'Nova Coluna')
                        if not ColunaKanban.objects.filter(nome=nome).exists():
                            ColunaKanban.objects.create(
                                nome=nome, cor=col_data.get('cor', '#6c757d'),
                                ordem=col_data.get('ordem', ColunaKanban.objects.count() + 1),
                                ativa=col_data.get('ativa', True)
                            )
            
            # Excluir colunas
            if 'colunas_excluir' in payload:
                for col_id in payload['colunas_excluir']:
                    if int(col_id) > 0:
                        ColunaKanban.objects.filter(id=col_id).delete()
            
            # Processar regras
            if 'regras' in payload:
                regra_ids_enviados = [int(r.get('id')) for r in payload['regras'] if r.get('id') and int(r.get('id')) > 0]
                if regra_ids_enviados:
                    RegraWorkflow.objects.exclude(id__in=regra_ids_enviados).delete()
                else:
                    RegraWorkflow.objects.all().delete()
                
                for regra_data in payload['regras']:
                    coluna_id = regra_data.get('coluna_id')
                    if not coluna_id: continue
                    
                    try:
                        coluna = ColunaKanban.objects.get(id=int(coluna_id))
                    except (ValueError, ColunaKanban.DoesNotExist):
                        continue
                    
                    evento = regra_data.get('evento', 'CRIACAO')
                    status_resultante = regra_data.get('status_resultante', 'AGUARDANDO_EMPENHO')
                    auto = regra_data.get('movimentacao_automatica', True)
                    if isinstance(auto, str): auto = auto.lower() in ['true', '1', 'yes', 'on']
                    
                    regra_id = regra_data.get('id')
                    if regra_id and int(regra_id) > 0:
                        try:
                            regra = RegraWorkflow.objects.get(id=int(regra_id))
                            regra.coluna = coluna
                            regra.evento = evento
                            regra.status_resultante = status_resultante
                            regra.movimentacao_automatica = auto
                            regra.save()
                        except RegraWorkflow.DoesNotExist:
                            RegraWorkflow.objects.get_or_create(
                                coluna=coluna, evento=evento,
                                defaults={'status_resultante': status_resultante, 'movimentacao_automatica': auto}
                            )
                    else:
                        RegraWorkflow.objects.get_or_create(
                            coluna=coluna, evento=evento,
                            defaults={'status_resultante': status_resultante, 'movimentacao_automatica': auto}
                        )
            
            return JsonResponse({'success': True, 'message': 'Workflow salvo com sucesso!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# FEED DE ATUALIZAÇÕES
# ============================================================================
@login_required
def api_atualizacoes_recentes(request):
    """Retorna o feed de atualizações recentes"""
    limite = int(request.GET.get('limite', 20))
    desde = request.GET.get('desde')
    
    query = HistoricoCard.objects.select_related('usuario', 'solicitacao')
    
    if desde:
        query = query.filter(id__gt=int(desde))
    
    atualizacoes = query.order_by('-data')[:limite]
    
    data = []
    for a in atualizacoes:
        data.append({
            'id': a.id,
            'usuario': a.usuario.get_full_name() or a.usuario.username,
            'acao': a.get_acao_display(),
            'descricao': a.descricao_completa(),
            'lote': a.lote,
            'quantidade': float(a.quantidade) if a.quantidade else None,
            'unidade': a.unidade,
            'card_id': a.solicitacao.id,
            'card_titulo': a.solicitacao.titulo,
            'data': a.data.strftime('%d/%m/%Y %H:%M:%S'),
            'data_iso': a.data.isoformat(),
        })
    
    return JsonResponse({'success': True, 'atualizacoes': data, 'total': len(data)})

# ============================================================================
# GESTÃO DE CARGAS - consulta e correções auditáveis
# ============================================================================
@login_required
def gestao_cargas(request):
    from collections import OrderedDict

    data_inicio = (request.GET.get('data_inicio') or '').strip()
    data_fim = (request.GET.get('data_fim') or '').strip()
    origem = (request.GET.get('origem') or '').strip().upper()
    busca = (request.GET.get('q') or '').strip()

    qs = (
        HistoricoMovimentacao.objects
        .filter(Q(tipo__icontains='Expedi'))
        .select_related('estoque', 'usuario')
        .order_by('-data_hora', '-id')
    )
    if data_inicio:
        qs = qs.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_hora__date__lte=data_fim)
    if origem in {'GERADA', 'AVULSA'}:
        qs = qs.filter(origem_carga=origem)
    if busca:
        qs = qs.filter(
            Q(numero_carga__icontains=busca)
            | Q(nome_carga_avulsa__icontains=busca)
            | Q(cliente__icontains=busca)
            | Q(placa__icontains=busca)
            | Q(motorista__icontains=busca)
            | Q(lote_ref__icontains=busca)
        )

    grupos = OrderedDict()
    for mov in qs[:3000]:
        origem_mov = str(mov.origem_carga or '').strip().upper() or 'LEGADO'
        nome_avulsa = ' '.join(str(mov.nome_carga_avulsa or '').strip().split())
        numero = ' '.join(str(mov.numero_carga or '').strip().split())
        if origem_mov == 'AVULSA':
            chave_base = normalizar_texto_cadastro(nome_avulsa) if nome_avulsa else normalizar_texto_cadastro(numero)
            chave = f'AVULSA:{chave_base or mov.id}'
            titulo = nome_avulsa or (f'CARGA {numero}' if numero else 'CARGA AVULSA')
        elif origem_mov == 'GERADA':
            chave = f'GERADA:{normalizar_texto_cadastro(numero) or mov.id}'
            titulo = f'CARGA {numero}' if numero and not numero.upper().startswith('CARGA ') else (numero or 'CARGA GERADA')
        else:
            chave = f'LEGADO:{normalizar_texto_cadastro(numero) or mov.id}'
            titulo = f'CARGA {numero}' if numero and not numero.upper().startswith('CARGA ') else (numero or 'EXPEDIÇÃO LEGADA')

        grupo = grupos.setdefault(chave, {
            'chave': chave,
            'titulo': titulo,
            'origem': origem_mov,
            'numero': numero,
            'nome_avulsa': nome_avulsa,
            'data': mov.data_hora,
            'quantidade': Decimal('0'),
            'clientes': set(),
            'placas': set(),
            'motoristas': set(),
            'lotes': set(),
            'movimentos': [],
        })
        grupo['quantidade'] += Decimal(str(mov.quantidade or 0))
        if mov.cliente: grupo['clientes'].add(str(mov.cliente).strip())
        if mov.placa: grupo['placas'].add(str(mov.placa).strip().upper())
        if mov.motorista: grupo['motoristas'].add(str(mov.motorista).strip())
        lote = str(mov.lote_ref or (mov.estoque.lote if mov.estoque else '') or '').strip()
        if lote: grupo['lotes'].add(lote)
        grupo['movimentos'].append(mov)

    grupos_lista = []
    for grupo in grupos.values():
        grupo['clientes_txt'] = ' / '.join(sorted(grupo['clientes'])) or '--'
        grupo['placas_txt'] = ' / '.join(sorted(grupo['placas'])) or '--'
        grupo['motoristas_txt'] = ' / '.join(sorted(grupo['motoristas'])) or '--'
        grupo['lotes_txt'] = ', '.join(sorted(grupo['lotes'])) or '--'
        grupo['data_txt'] = timezone.localtime(grupo['data']).strftime('%d/%m/%Y') if grupo['data'] else '--'
        grupos_lista.append(grupo)

    estoque_opcoes = list(
        Estoque.objects
        .select_related('cultivar')
        .order_by('lote', 'endereco')
        .values('id', 'lote', 'endereco', 'saldo', 'embalagem')
    )

    # Evita uma tela enorme quando o período possui dezenas ou centenas de
    # cargas. A consulta e os filtros continuam considerando todo o período,
    # mas a interface mostra somente 10 cargas por página.
    total_grupos = len(grupos_lista)
    paginator = Paginator(grupos_lista, 10)
    page_obj = paginator.get_page(request.GET.get('page') or 1)

    query_sem_pagina = request.GET.copy()
    query_sem_pagina.pop('page', None)

    return render(request, 'sapp/gestao_cargas.html', {
        'grupos': list(page_obj.object_list),
        'page_obj': page_obj,
        'total_grupos': total_grupos,
        'filtros_query': query_sem_pagina.urlencode(),
        'estoque_opcoes': estoque_opcoes,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'origem': origem,
            'q': busca,
        },
    })


@login_required
@require_POST
def editar_movimento_carga(request, historico_id):
    """Corrige um item de carga preservando auditoria e coerência do saldo físico."""
    from datetime import datetime as dt
    from .models import CargaAjusteLog

    motivo = (request.POST.get('motivo') or '').strip()
    if not motivo:
        messages.error(request, 'Informe o motivo da correção.')
        return redirect('sapp:gestao_cargas')


    try:
        with transaction.atomic():
            hist = (
                HistoricoMovimentacao.objects
                .select_for_update()
                .select_related('estoque')
                .get(pk=historico_id)
            )
            if 'EXPEDI' not in str(hist.tipo or '').upper():
                raise ValueError('Este histórico não é uma expedição/carga.')

            estoque_antigo = (
                Estoque.objects.select_for_update().get(pk=hist.estoque_id)
                if hist.estoque_id else None
            )
            qtd_antiga = int(hist.quantidade or 0)
            novo_estoque_id = int(request.POST.get('estoque_id') or (hist.estoque_id or 0))
            qtd_nova = int(request.POST.get('quantidade') or qtd_antiga)
            if qtd_nova <= 0:
                raise ValueError('Quantidade deve ser maior que zero.')

            estoque_novo = (
                estoque_antigo
                if estoque_antigo and estoque_antigo.pk == novo_estoque_id
                else Estoque.objects.select_for_update().get(pk=novo_estoque_id)
            )

            antes = {
                'estoque_id': hist.estoque_id,
                'lote': hist.lote_ref,
                'quantidade': qtd_antiga,
                'data_hora': hist.data_hora.isoformat() if hist.data_hora else None,
                'numero_carga': hist.numero_carga or '',
                'nome_carga_avulsa': hist.nome_carga_avulsa or '',
                'origem_carga': hist.origem_carga or '',
                'cliente': hist.cliente or '',
                'placa': hist.placa or '',
                'motorista': hist.motorista or '',
            }

            # Reverte o efeito antigo e aplica o novo. Isso permite corrigir
            # quantidade/lote sem apagar o histórico original da auditoria.
            if estoque_antigo:
                nova_saida_antigo = int(estoque_antigo.saida or 0) - qtd_antiga
                if nova_saida_antigo < 0:
                    raise ValueError('Não é possível reverter esta movimentação: saída histórica inconsistente.')
                estoque_antigo.saida = nova_saida_antigo
                estoque_antigo.save()

            # Quando lote/endereço não mudou, usa o objeto já revertido. Quando
            # mudou, o destino foi travado separadamente.
            if estoque_antigo and estoque_novo.pk == estoque_antigo.pk:
                estoque_novo = estoque_antigo
            if estoque_novo.saldo < qtd_nova:
                raise ValueError(
                    f'Saldo insuficiente no lote/endereço escolhido. Disponível físico após reversão: {estoque_novo.saldo} {estoque_novo.embalagem}.'
                )
            estoque_novo.saida = int(estoque_novo.saida or 0) + qtd_nova
            estoque_novo.save()

            hist.estoque = estoque_novo
            hist.lote_ref = estoque_novo.lote
            hist.quantidade = qtd_nova
            hist.numero_carga = (request.POST.get('numero_carga') or '').strip() or None
            hist.nome_carga_avulsa = ' '.join((request.POST.get('nome_carga_avulsa') or '').strip().split())
            hist.cliente = (request.POST.get('cliente') or '').strip() or None
            hist.placa = (request.POST.get('placa') or '').strip().upper() or None
            hist.motorista = (request.POST.get('motorista') or '').strip() or None
            origem_post = (request.POST.get('origem_carga') or hist.origem_carga or '').strip().upper()
            if origem_post in {'GERADA', 'AVULSA'}:
                hist.origem_carga = origem_post
            hist.save(update_fields=[
                'estoque', 'lote_ref', 'quantidade', 'numero_carga',
                'nome_carga_avulsa', 'cliente', 'placa', 'motorista', 'origem_carga'
            ])

            data_txt = (request.POST.get('data_carga') or '').strip()
            if data_txt and hist.data_hora:
                nova_data = dt.strptime(data_txt, '%Y-%m-%d').date()
                hora_local = timezone.localtime(hist.data_hora).timetz().replace(tzinfo=None)
                nova_local = timezone.make_aware(dt.combine(nova_data, hora_local), timezone.get_current_timezone())
                HistoricoMovimentacao.objects.filter(pk=hist.pk).update(data_hora=nova_local)
                hist.data_hora = nova_local

            # Se for uma carga gerada, tenta manter o histórico do empenho e o
            # total movimentado do card alinhados com a correção física.
            if hist.origem_carga == 'GERADA' and hist.numero_carga:
                numero_limpo = str(hist.numero_carga).strip()
                titulo = numero_limpo if numero_limpo.upper().startswith('CARGA ') else f'CARGA {numero_limpo}'
                sol = Solicitacao.objects.filter(tipo_solicitacao='CARGA', titulo__iexact=titulo).first()
                if sol:
                    hie = (
                        HistoricoItemEmpenho.objects
                        .filter(
                            empenho__solicitacao=sol,
                            tipo='expedicao',
                            lote__iexact=antes['lote'],
                            quantidade=qtd_antiga,
                            numero_carga__iexact=numero_limpo,
                        )
                        .order_by('id')
                        .first()
                    )
                    if hie:
                        hie.lote = estoque_novo.lote
                        hie.quantidade = qtd_nova
                        if hist.cliente:
                            hie.cliente_solicitacao = hist.cliente
                        hie.save(update_fields=['lote', 'quantidade', 'cliente_solicitacao'])
                    total_mov = (
                        HistoricoItemEmpenho.objects
                        .filter(empenho__solicitacao=sol, tipo='expedicao')
                        .aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
                    )
                    sol.quantidade_movimentada = Decimal(str(total_mov))
                    sol.save(update_fields=['quantidade_movimentada', 'data_atualizacao'])

            depois = {
                'estoque_id': estoque_novo.id,
                'lote': estoque_novo.lote,
                'quantidade': qtd_nova,
                'data_hora': hist.data_hora.isoformat() if hist.data_hora else None,
                'numero_carga': hist.numero_carga or '',
                'nome_carga_avulsa': hist.nome_carga_avulsa or '',
                'origem_carga': hist.origem_carga or '',
                'cliente': hist.cliente or '',
                'placa': hist.placa or '',
                'motorista': hist.motorista or '',
            }
            CargaAjusteLog.objects.create(
                historico=hist,
                usuario=request.user,
                antes=antes,
                depois=depois,
                motivo=motivo,
            )

            # Correção manual também muda a versão do lote para que aparelhos
            # offline detectem conflito quando voltarem a sincronizar.
            from .models import LoteSyncState, LoteSyncEvento
            lotes_afetados = {str(antes.get('lote') or '').strip(), str(depois.get('lote') or '').strip()} - {''}
            for lote_sync in lotes_afetados:
                state, _ = LoteSyncState.objects.select_for_update().get_or_create(lote=lote_sync)
                state.versao = int(state.versao or 0) + 1
                state.atualizado_por = request.user
                state.save(update_fields=['versao', 'atualizado_por', 'atualizado_em'])
                LoteSyncEvento.objects.create(
                    lote=lote_sync,
                    versao=state.versao,
                    usuario=request.user,
                    historico=hist,
                    tipo='CORRECAO_CARGA',
                )

            messages.success(request, '✅ Movimento da carga corrigido e auditado com sucesso.')
    except Exception as exc:
        messages.error(request, f'❌ Não foi possível corrigir a carga: {exc}')

    return redirect('sapp:gestao_cargas')

@login_required
@require_POST
def remover_movimento_carga(request, historico_id):
    """Remove um lote/movimento de uma carga sem apagar a trilha de auditoria.

    A saída física é revertida e o histórico deixa de ser tratado como
    expedição ativa. Para cargas geradas, o histórico do item empenhado é
    marcado como removido e a quantidade movimentada da solicitação é
    recalculada.
    """
    from .models import CargaAjusteLog, LoteSyncState, LoteSyncEvento

    motivo = (request.POST.get('motivo') or '').strip()
    if not motivo:
        messages.error(request, 'Informe o motivo para excluir o lote da carga.')
        return redirect('sapp:gestao_cargas')

    try:
        with transaction.atomic():
            hist = (
                HistoricoMovimentacao.objects
                .select_for_update()
                .select_related('estoque')
                .get(pk=historico_id)
            )

            if 'EXPEDI' not in str(hist.tipo or '').upper():
                raise ValueError('Este lote não pertence mais a uma expedição ativa.')

            estoque = (
                Estoque.objects.select_for_update().get(pk=hist.estoque_id)
                if hist.estoque_id else None
            )
            quantidade = int(hist.quantidade or 0)
            if quantidade <= 0:
                raise ValueError('A movimentação possui quantidade inválida para reversão.')

            antes = {
                'estoque_id': hist.estoque_id,
                'lote': hist.lote_ref,
                'quantidade': quantidade,
                'data_hora': hist.data_hora.isoformat() if hist.data_hora else None,
                'numero_carga': hist.numero_carga or '',
                'nome_carga_avulsa': hist.nome_carga_avulsa or '',
                'origem_carga': hist.origem_carga or '',
                'cliente': hist.cliente or '',
                'placa': hist.placa or '',
                'motorista': hist.motorista or '',
                'tipo': hist.tipo or '',
            }

            # Devolve ao estoque apenas o que esta movimentação retirou.
            if estoque:
                nova_saida = int(estoque.saida or 0) - quantidade
                if nova_saida < 0:
                    raise ValueError(
                        'Não é possível excluir este lote: a saída atual do estoque é menor que a movimentação registrada.'
                    )
                estoque.saida = nova_saida
                estoque.save(update_fields=['saida'])

            # Carga gerada: preserva o histórico do item, mas ele deixa de
            # contar como expedição ativa. Isso mantém rastreabilidade sem
            # somar novamente o lote nos totais do card.
            solicitacao = None
            hie = None
            if str(hist.origem_carga or '').strip().upper() == 'GERADA' and hist.numero_carga:
                numero_limpo = str(hist.numero_carga).strip()
                titulo = numero_limpo if numero_limpo.upper().startswith('CARGA ') else f'CARGA {numero_limpo}'
                solicitacao = (
                    Solicitacao.objects
                    .select_for_update()
                    .filter(tipo_solicitacao='CARGA', titulo__iexact=titulo)
                    .first()
                )
                if solicitacao:
                    hie = (
                        HistoricoItemEmpenho.objects
                        .select_for_update()
                        .filter(
                            empenho__solicitacao=solicitacao,
                            tipo='expedicao',
                            lote__iexact=str(hist.lote_ref or ''),
                            quantidade=quantidade,
                            numero_carga__iexact=numero_limpo,
                        )
                        .order_by('id')
                        .first()
                    )
                    if hie:
                        observacao_remocao = (
                            f'[REMOVIDO DA CARGA em {timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")} '
                            f'por {request.user.get_full_name() or request.user.username}] {motivo}'
                        )
                        hie.tipo = 'removido'
                        hie.observacao = (
                            f'{hie.observacao}\n{observacao_remocao}'.strip()
                            if hie.observacao else observacao_remocao
                        )
                        hie.save(update_fields=['tipo', 'observacao'])

                    total_mov = (
                        HistoricoItemEmpenho.objects
                        .filter(empenho__solicitacao=solicitacao, tipo='expedicao')
                        .aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
                    )
                    solicitacao.quantidade_movimentada = Decimal(str(total_mov))
                    if (
                        solicitacao.status == 'CONCLUIDO'
                        and solicitacao.quantidade_movimentada < Decimal(str(solicitacao.quantidade_solicitada or 0))
                    ):
                        solicitacao.status = 'MOVIMENTACAO_PARCIAL' if solicitacao.quantidade_movimentada > 0 else 'AGUARDANDO_EMPENHO'
                    solicitacao.save(update_fields=['quantidade_movimentada', 'status', 'data_atualizacao'])

            # Em vez de apagar a linha, muda o tipo. Assim ela some das cargas
            # ativas e dos gráficos, mas continua disponível para auditoria.
            usuario_nome = request.user.get_full_name() or request.user.username
            marca_remocao = (
                f'Removido da carga em {timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")} '
                f'por {usuario_nome}. Motivo: {motivo}'
            )
            hist.tipo = 'Carga removida'
            hist.descricao = f'{hist.descricao or ""}\n{marca_remocao}'.strip()
            hist.save(update_fields=['tipo', 'descricao'])

            depois = {
                **antes,
                'tipo': 'Carga removida',
                'removido_da_carga': True,
                'estoque_saida_revertida': quantidade,
            }
            CargaAjusteLog.objects.create(
                historico=hist,
                usuario=request.user,
                antes=antes,
                depois=depois,
                motivo=f'EXCLUSÃO DE LOTE DA CARGA: {motivo}',
            )

            lote_sync = str(antes.get('lote') or '').strip()
            if lote_sync:
                state, _ = LoteSyncState.objects.select_for_update().get_or_create(lote=lote_sync)
                state.versao = int(state.versao or 0) + 1
                state.atualizado_por = request.user
                state.save(update_fields=['versao', 'atualizado_por', 'atualizado_em'])
                LoteSyncEvento.objects.create(
                    lote=lote_sync,
                    versao=state.versao,
                    usuario=request.user,
                    historico=hist,
                    tipo='REMOCAO_CARGA',
                )

            cache.delete('cards_version_hash')
            messages.success(request, '✅ Lote excluído da carga, estoque revertido e auditoria preservada.')

    except HistoricoMovimentacao.DoesNotExist:
        messages.error(request, '❌ Movimento da carga não encontrado.')
    except Exception as exc:
        messages.error(request, f'❌ Não foi possível excluir o lote da carga: {exc}')

    return redirect('sapp:gestao_cargas')

