# financeiro/views/dashboard.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum

from django.contrib.auth import get_user_model
from clientes.models import RelatorioFinanceiro, MovimentacaoCaixa

User = get_user_model()


@login_required
def dashboard_financeiro_premium(request):
    """Dashboard financeiro premium"""
    usuario = request.user
    hoje = timezone.now()
    
    # Hierarquia
    subordinados_ids = User.objects.filter(dono=usuario).values_list('id', flat=True)
    
    base_relatorios = RelatorioFinanceiro.objects.filter(cliente_id__in=subordinados_ids)
    base_caixa = MovimentacaoCaixa.objects.filter(usuario=usuario)

    # Períodos
    start_this_month = hoje.replace(day=1, hour=0, minute=0, second=0)
    last_month_end = start_this_month - timedelta(seconds=1)
    start_last_month = last_month_end.replace(day=1, hour=0, minute=0, second=0)
    start_this_year = hoje.replace(month=1, day=1, hour=0, minute=0, second=0)

    def get_metrics(queryset, caixa_qs, start_date, end_date=None):
        if end_date:
            rel = queryset.filter(data_geracao__gte=start_date, data_geracao__lte=end_date)
            cax = caixa_qs.filter(data__gte=start_date, data__lte=end_date)
        else:
            rel = queryset.filter(data_geracao__gte=start_date)
            cax = caixa_qs.filter(data__gte=start_date)
            
        receita = (rel.aggregate(s=Sum('valor_pago'))['s'] or 0) + (cax.filter(tipo='entrada').aggregate(s=Sum('valor'))['s'] or 0)
        custo = (rel.aggregate(s=Sum('valor_servico'))['s'] or 0) + (cax.filter(tipo='saida').aggregate(s=Sum('valor'))['s'] or 0)
        return float(receita), float(receita - custo)

    rec_atual, lucro_atual = get_metrics(base_relatorios, base_caixa, start_this_month)
    rec_passado, lucro_passado = get_metrics(base_relatorios, base_caixa, start_last_month, last_month_end)

    def diff_perc(atual, passado):
        if passado > 0: return ((atual - passado) / passado) * 100
        return 100 if atual > 0 else 0

    crescimento_rec = diff_perc(rec_atual, rec_passado)
    crescimento_lucro = diff_perc(lucro_atual, lucro_passado)

    # Gráfico
    labels_grafico = []
    dados_receita = []
    dados_lucro = []

    for i in range(11, -1, -1):
        target_date = hoje - timedelta(days=i*30)
        m_start = target_date.replace(day=1, hour=0, minute=0)
        m_name = m_start.strftime('%b')
        r, l = get_metrics(base_relatorios, base_caixa, m_start, m_start + timedelta(days=31))
        labels_grafico.append(m_name)
        dados_receita.append(r)
        dados_lucro.append(l)

    # Listagem
    lista_transacoes = base_relatorios.order_by('-data_geracao')
    paginator = Paginator(lista_transacoes, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'rec_atual': rec_atual,
        'lucro_atual': lucro_atual,
        'rec_passado': rec_passado,
        'lucro_passado': lucro_passado,
        'crescimento_rec': crescimento_rec,
        'crescimento_lucro': crescimento_lucro,
        'receita_anual': get_metrics(base_relatorios, base_caixa, start_this_year)[0],
        'ticket_medio': rec_atual / max(lista_transacoes.filter(data_geracao__gte=start_this_month).count(), 1),
        'labels_grafico': labels_grafico,
        'dados_receita': dados_receita,
        'dados_lucro': dados_lucro,
        'page_obj': page_obj,
    }
    return render(request, "dashboard_premium.html", context)