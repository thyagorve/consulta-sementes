# financeiro/urls.py
from django.urls import path
from .views import relatorios, caixa, api

app_name = 'financeiro'

urlpatterns = [
    # Dashboard Financeiro (Principal)
    path('', relatorios.relatorio_financeiro, name='dashboard_financeiro'),
    path('relatorio/', relatorios.relatorio_financeiro, name='relatorio_financeiro'),
    path('relatorio/data/', relatorios.relatorio_financeiro, name='relatorio_financeiro_data'),
    path('relatorio/export/', relatorios.relatorio_financeiro_export, name='relatorio_financeiro_export'),
    
    # Lançamentos manuais
    path('relatorio/adicionar-lancamento/', relatorios.adicionar_lancamento_manual, name='adicionar_lancamento_manual'),
    
    # CRUD de relatórios
    path('relatorio/editar/<int:id>/', relatorios.editar_relatorio_financeiro, name='editar_relatorio_financeiro'),
    path('relatorio/excluir/<int:id>/', relatorios.excluir_relatorio_financeiro, name='excluir_relatorio_financeiro'),
    path('relatorio/json/<int:id>/', api.api_relatorio_financeiro, name='api_relatorio_financeiro'),
    path('relatorio/delete/<str:tipo>/<int:id>/', relatorios.relatorio_financeiro_delete, name='relatorio_financeiro_delete'),

    # Movimentações de Caixa
    path('caixa/adicionar/', caixa.adicionar_movimentacao_caixa, name='adicionar_movimentacao_caixa'),
    path('caixa/editar/<int:id>/', caixa.editar_movimentacao_caixa, name='editar_movimentacao_caixa'),
    path('caixa/excluir/<int:id>/', caixa.excluir_movimentacao_caixa, name='excluir_movimentacao_caixa'),
    path('caixa/json/<int:id>/', caixa.api_movimentacao_caixa, name='api_movimentacao_caixa'),
]