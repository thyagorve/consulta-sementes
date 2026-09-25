# financeiro/views/relatorios.py
from datetime import datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from clientes.models import CustomUser, MovimentacaoCaixa, RelatorioFinanceiro


@login_required
def relatorio_financeiro(request):
    """
    RELATÓRIO FINANCEIRO COMPLETO COM FILTROS ENCADEADOS
    """
    usuario = request.user
    hoje = timezone.localdate()

    tipo_usuario = getattr(usuario, "tipo_usuario", "cliente")
    is_admin = tipo_usuario == "admin"
    is_revenda = tipo_usuario == "revenda"

    # Usuários visíveis
    if tipo_usuario in ['admin', 'revenda']:
        clientes_visiveis = CustomUser.objects.filter(dono=usuario)
    else:
        clientes_visiveis = CustomUser.objects.filter(id=usuario.id)

    usuarios_caixa = CustomUser.objects.filter(id=usuario.id)

    # Bases de dados COMPLETAS (sem filtro ainda)
    relatorios_base = RelatorioFinanceiro.objects.filter(
        cliente__in=clientes_visiveis
    ).select_related('cliente')
    
    caixa_base = MovimentacaoCaixa.objects.filter(
        usuario__in=usuarios_caixa
    ).select_related('usuario')

    # ==========================================
    # OBTER ANOS DISPONÍVEIS (baseado nos dados reais)
    # ==========================================
    anos_relatorios = relatorios_base.dates('data_geracao', 'year')
    anos_caixa = caixa_base.dates('data', 'year')
    
    anos_disponiveis = set()
    for d in anos_relatorios:
        anos_disponiveis.add(d.year)
    for d in anos_caixa:
        anos_disponiveis.add(d.year)
    
    # Sempre permitir o ano atual e os 5 anteriores, mesmo sem movimento.
    # Anos mais antigos existentes no banco continuam disponíveis.
    ano_atual = timezone.localdate().year
    anos_disponiveis.update(range(ano_atual, ano_atual - 6, -1))
    anos_disponiveis = sorted(anos_disponiveis, reverse=True)

    # ==========================================
    # PARÂMETROS DE FILTRO
    # ==========================================
    filtro_periodo = request.GET.get('periodo', 'all')
    filtro_tipo = request.GET.get('tipo', 'all')
    filtro_origem = request.GET.get('origem', 'all')
    filtro_categoria = request.GET.get('categoria', 'all')
    filtro_ordem = request.GET.get('ordem', '-data')
    
    # Para mês específico - usar valores padrão baseados nos dados
    mes_default = str(timezone.now().month)
    ano_default = str(anos_disponiveis[0]) if anos_disponiveis else str(timezone.now().year)
    
    mes_especifico = request.GET.get('mes', mes_default)
    ano_especifico = request.GET.get('ano', ano_default)
    # ==========================================
    # MESES DISPONÍVEIS
    # ==========================================
    # O filtro deve permitir qualquer mês do ano escolhido. Se não houver
    # movimento, o resultado correto é uma lista vazia, não trocar o mês.
    try:
        ano_ref = int(ano_especifico)
    except (TypeError, ValueError):
        ano_ref = ano_atual
        ano_especifico = str(ano_ref)
    meses_disponiveis = list(range(1, 13))

    # ==========================================
    # OBTER CATEGORIAS DISPONÍVEIS (baseado nos dados)
    # ==========================================
    categorias_caixa = caixa_base.values_list('categoria', flat=True).distinct()
    categorias_disponiveis = set()
    
    # Adicionar 'servico' se houver relatórios
    if relatorios_base.exists():
        categorias_disponiveis.add('servico')
    
    # Adicionar categorias do caixa
    for cat in categorias_caixa:
        if cat:
            categorias_disponiveis.add(cat)
    
    categorias_disponiveis = sorted(list(categorias_disponiveis))
    
    if not categorias_disponiveis:
        categorias_disponiveis = ['venda', 'servico', 'despesa', 'investimento', 'outros']

    # ==========================================
    # APLICAR FILTRO DE PERÍODO
    # ==========================================
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    if filtro_periodo == 'today':
        relatorios_base = relatorios_base.filter(data_geracao__date=hoje)
        caixa_base = caixa_base.filter(data__date=hoje)
    elif filtro_periodo == 'yesterday':
        ontem = hoje - timedelta(days=1)
        relatorios_base = relatorios_base.filter(data_geracao__date=ontem)
        caixa_base = caixa_base.filter(data__date=ontem)
    elif filtro_periodo == 'week':
        relatorios_base = relatorios_base.filter(
            data_geracao__date__gte=inicio_semana, 
            data_geracao__date__lte=fim_semana
        )
        caixa_base = caixa_base.filter(
            data__date__gte=inicio_semana, 
            data__date__lte=fim_semana
        )
    elif filtro_periodo == 'last_week':
        inicio_semana_passada = hoje - timedelta(days=hoje.weekday() + 7)
        fim_semana_passada = inicio_semana_passada + timedelta(days=6)
        relatorios_base = relatorios_base.filter(
            data_geracao__date__gte=inicio_semana_passada,
            data_geracao__date__lte=fim_semana_passada
        )
        caixa_base = caixa_base.filter(
            data__date__gte=inicio_semana_passada,
            data__date__lte=fim_semana_passada
        )
    elif filtro_periodo == 'month':
        inicio_mes = hoje.replace(day=1)
        relatorios_base = relatorios_base.filter(
            data_geracao__date__gte=inicio_mes, 
            data_geracao__date__lte=hoje
        )
        caixa_base = caixa_base.filter(
            data__date__gte=inicio_mes, 
            data__date__lte=hoje
        )
    elif filtro_periodo == 'last_month':
        primeiro_dia_mes_passado = hoje.replace(day=1) - timedelta(days=1)
        inicio_mes_passado = primeiro_dia_mes_passado.replace(day=1)
        relatorios_base = relatorios_base.filter(
            data_geracao__date__gte=inicio_mes_passado,
            data_geracao__date__lte=primeiro_dia_mes_passado
        )
        caixa_base = caixa_base.filter(
            data__date__gte=inicio_mes_passado,
            data__date__lte=primeiro_dia_mes_passado
        )
    elif filtro_periodo == 'last_3_months':
        tres_meses_atras = hoje - relativedelta(months=3)
        relatorios_base = relatorios_base.filter(data_geracao__date__gte=tres_meses_atras)
        caixa_base = caixa_base.filter(data__date__gte=tres_meses_atras)
    elif filtro_periodo == 'last_6_months':
        seis_meses_atras = hoje - relativedelta(months=6)
        relatorios_base = relatorios_base.filter(data_geracao__date__gte=seis_meses_atras)
        caixa_base = caixa_base.filter(data__date__gte=seis_meses_atras)
    elif filtro_periodo == 'year':
        inicio_ano = hoje.replace(month=1, day=1)
        relatorios_base = relatorios_base.filter(
            data_geracao__date__gte=inicio_ano, 
            data_geracao__date__lte=hoje
        )
        caixa_base = caixa_base.filter(
            data__date__gte=inicio_ano, 
            data__date__lte=hoje
        )
    elif filtro_periodo == 'custom_month':
        try:
            mes = int(mes_especifico)
            ano = int(ano_especifico)
            data_inicio = datetime(ano, mes, 1).date()
            if mes == 12:
                data_fim = datetime(ano + 1, 1, 1).date() - timedelta(days=1)
            else:
                data_fim = datetime(ano, mes + 1, 1).date() - timedelta(days=1)
            
            relatorios_base = relatorios_base.filter(
                data_geracao__date__gte=data_inicio,
                data_geracao__date__lte=data_fim
            )
            caixa_base = caixa_base.filter(
                data__date__gte=data_inicio,
                data__date__lte=data_fim
            )
        except (ValueError, TypeError):
            pass

    # ==========================================
    # APLICAR FILTRO DE TIPO
    # ==========================================
    if filtro_tipo == 'entrada':
        caixa_base = caixa_base.filter(tipo='entrada')
        relatorios_base = relatorios_base.filter(valor_pago__gt=0)
    elif filtro_tipo == 'saida':
        caixa_base = caixa_base.filter(tipo='saida')
        relatorios_base = relatorios_base.filter(valor_pago__lt=0)

    # ==========================================
    # APLICAR FILTRO DE ORIGEM
    # ==========================================
    if filtro_origem == 'servico':
        caixa_base = caixa_base.none()
    elif filtro_origem == 'caixa':
        relatorios_base = relatorios_base.none()

    # ==========================================
    # APLICAR FILTRO DE CATEGORIA
    # ==========================================
    if filtro_categoria != 'all':
        if filtro_categoria == 'servico':
            caixa_base = caixa_base.none()
        else:
            caixa_base = caixa_base.filter(categoria=filtro_categoria)
            relatorios_base = relatorios_base.none()

    # ==========================================
    # COMBINAR DADOS
    # ==========================================
    dados_combinados = []

    for rel in relatorios_base:
        valor_pago = rel.valor_pago if rel.valor_pago > 0 else Decimal('0')
        valor_servico = abs(rel.valor_pago) if rel.valor_pago < 0 else (rel.valor_servico or Decimal('0'))
        valor_liquido = valor_pago - valor_servico
        
        dados_combinados.append({
            'tipo': 'relatorio',
            'id': rel.id,
            'cliente_nome': rel.cliente.nome or rel.cliente.username,
            'descricao': rel.servidor or 'Sem descrição',
            'valor_pago': valor_pago,
            'valor_servico': valor_servico,
            'valor_liquido': valor_liquido,
            'data': rel.data_geracao,
            'tipo_transacao': 'entrada' if valor_liquido >= 0 else 'saida',
            'origem': 'servico',
            'categoria': 'servico',
        })

    for mov in caixa_base:
        if mov.tipo == 'entrada':
            vp = mov.valor
            vs = Decimal('0')
            vl = mov.valor
        else:
            vp = Decimal('0')
            vs = mov.valor
            vl = -mov.valor
        
        dados_combinados.append({
            'tipo': 'caixa',
            'id': mov.id,
            'cliente_nome': mov.usuario.nome or mov.usuario.username,
            'descricao': mov.descricao or 'Movimentação de caixa',
            'valor_pago': vp,
            'valor_servico': vs,
            'valor_liquido': vl,
            'data': mov.data,
            'tipo_transacao': mov.tipo,
            'origem': 'caixa',
            'categoria': mov.categoria or 'outros',
        })

    # ==========================================
    # ORDENAÇÃO
    # ==========================================
    if filtro_ordem == 'data':
        dados_combinados.sort(key=lambda x: x['data'])
    elif filtro_ordem == '-valor_liquido':
        dados_combinados.sort(key=lambda x: x['valor_liquido'], reverse=True)
    elif filtro_ordem == 'valor_liquido':
        dados_combinados.sort(key=lambda x: x['valor_liquido'])
    elif filtro_ordem == 'valor_pago':
        dados_combinados.sort(key=lambda x: x['valor_pago'])
    elif filtro_ordem == '-valor_pago':
        dados_combinados.sort(key=lambda x: x['valor_pago'], reverse=True)
    elif filtro_ordem == 'valor_servico':
        dados_combinados.sort(key=lambda x: x['valor_servico'])
    elif filtro_ordem == '-valor_servico':
        dados_combinados.sort(key=lambda x: x['valor_servico'], reverse=True)
    else:
        # Padrão: mais recente primeiro
        dados_combinados.sort(key=lambda x: x['data'], reverse=True)

    # ==========================================
    # CÁLCULOS
    # ==========================================
    total_entradas = sum(item['valor_pago'] for item in dados_combinados)
    total_saidas = sum(item['valor_servico'] for item in dados_combinados)
    saldo_liquido = total_entradas - total_saidas
    total_valor_pago = total_entradas
    total_custo_servico = total_saidas
    total_lucro_liquido = saldo_liquido
    total_transacoes = len(dados_combinados)
    
    if total_transacoes > 0:
        media_transacao = (total_entradas / Decimal(str(total_transacoes))).quantize(Decimal('0.01'))
    else:
        media_transacao = Decimal('0')

    # ==========================================
    # PAGINAÇÃO
    # ==========================================
    paginator = Paginator(dados_combinados, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # ==========================================
    # CONTEXTO
    # ==========================================
    context = {
        'user': usuario,
        'is_admin': is_admin,
        'is_revenda': is_revenda,
        'page_obj': page_obj,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_liquido': saldo_liquido,
        'total_transacoes': total_transacoes,
        'media_transacao': media_transacao,
        'total_valor_pago': total_valor_pago,
        'total_custo_servico': total_custo_servico,
        'total_lucro_liquido': total_lucro_liquido,
        'filtro_periodo': filtro_periodo,
        'filtro_tipo': filtro_tipo,
        'filtro_origem': filtro_origem,
        'filtro_categoria': filtro_categoria,
        'filtro_ordem': filtro_ordem,
        'mes_especifico': mes_especifico,
        'ano_especifico': ano_especifico,
        'anos_disponiveis': anos_disponiveis,
        'meses_disponiveis': meses_disponiveis,
        'categorias_disponiveis': categorias_disponiveis,
    }

    return render(request, "financeiro/dashboard_financeiro.html", context)

@login_required
def adicionar_lancamento_manual(request):
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente_id')
            tipo_lancamento = request.POST.get('tipo_lancamento')
            valor = request.POST.get('valor')
            servidor = request.POST.get('servidor', '')
            observacoes = request.POST.get('observacoes', '')
            
            if not cliente_id or not tipo_lancamento or not valor:
                messages.error(request, 'Preencha todos os campos obrigatórios.')
                return redirect('financeiro:relatorio_financeiro')
            
            cliente = get_object_or_404(CustomUser, id=cliente_id)
            valor_decimal = Decimal(valor.replace(',', '.'))
            valor_pago = valor_decimal if tipo_lancamento == 'entrada' else -valor_decimal
            
            RelatorioFinanceiro.objects.create(
                cliente=cliente,
                valor_pago=valor_pago,
                valor_servico=Decimal('0.00'),
                valor_liquido=valor_pago,
                servidor=f"{servidor} | {observacoes}" if observacoes else servidor,
                is_manual=True
            )
            
            messages.success(request, 'Lançamento adicionado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro: {str(e)}')
        return redirect('financeiro:relatorio_financeiro')
    return redirect('financeiro:relatorio_financeiro')


@login_required
def editar_relatorio_financeiro(request, id):
    if request.method == 'POST':
        try:
            relatorio = get_object_or_404(RelatorioFinanceiro, id=id)
            usuario = request.user
            
            if relatorio.cliente.dono != usuario and relatorio.cliente != usuario:
                messages.error(request, 'Permissão negada.')
                return redirect('financeiro:relatorio_financeiro')
            
            relatorio.servidor = request.POST.get('servidor', '')
            valor_pago_str = request.POST.get('valor_pago', str(relatorio.valor_pago)).replace(',', '.')
            valor_servico_str = request.POST.get('valor_servico', str(relatorio.valor_servico)).replace(',', '.')
            
            try:
                relatorio.valor_pago = Decimal(valor_pago_str)
                relatorio.valor_servico = Decimal(valor_servico_str)
            except:
                pass
            
            data_str = request.POST.get('data_geracao')
            if data_str:
                try:
                    relatorio.data_geracao = timezone.make_aware(datetime.strptime(data_str, '%Y-%m-%dT%H:%M'))
                except:
                    pass
            
            relatorio.valor_liquido = relatorio.valor_pago - relatorio.valor_servico
            relatorio.save()
            messages.success(request, 'Relatório atualizado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar relatório: {str(e)}')
        return redirect('financeiro:relatorio_financeiro')
    return redirect('financeiro:relatorio_financeiro')


@login_required
def excluir_relatorio_financeiro(request, id):
    if request.method == 'POST':
        try:
            relatorio = get_object_or_404(RelatorioFinanceiro, id=id)
            usuario = request.user
            
            if relatorio.cliente.dono != usuario and relatorio.cliente != usuario:
                messages.error(request, 'Permissão negada.')
                return redirect('financeiro:relatorio_financeiro')
            
            relatorio.delete()
            messages.success(request, 'Relatório excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir relatório: {str(e)}')
    return redirect('financeiro:relatorio_financeiro')


@login_required
def relatorio_financeiro_export(request):
    messages.info(request, 'Exportação em desenvolvimento.')
    return redirect('financeiro:relatorio_financeiro')


@login_required
def relatorio_financeiro_delete(request, tipo, id):
    if request.method == 'POST':
        try:
            if tipo == 'relatorio':
                item = get_object_or_404(RelatorioFinanceiro, id=id)
            elif tipo == 'caixa':
                item = get_object_or_404(MovimentacaoCaixa, id=id)
            else:
                return JsonResponse({'success': False, 'error': 'Tipo inválido'})
            item.delete()
            return JsonResponse({'success': True, 'message': 'Excluído com sucesso!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método não permitido'})