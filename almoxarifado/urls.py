from django.urls import path
from . import views

app_name = 'almoxarifado'

urlpatterns = [
    path('', views.lista_itens, name='lista_itens'),
    path('saidas/', views.saidas_list, name='saidas_list'),
    path('buscar/', views.buscar_itens_ajax, name='buscar_itens_ajax'),
    path('item/buscar-codigo/', views.buscar_por_codigo, name='buscar_por_codigo'),
    path('item/adicionar/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:pk>/detalhe/', views.detalhe_item, name='detalhe_item'),
    path('item/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('item/<int:pk>/baixa/', views.dar_baixa, name='dar_baixa'),
    path('item/<int:pk>/excluir/', views.excluir_item, name='excluir_item'),
    
    # Carrinho
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/', views.adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('carrinho/<int:pk>/remover/', views.remover_do_carrinho, name='remover_carrinho'),
    path('carrinho/finalizar/', views.finalizar_carrinho, name='finalizar_carrinho'),
    path('carrinho/limpar/', views.limpar_carrinho, name='limpar_carrinho'),
    
    # Excel
    path('exportar/', views.exportar_excel, name='exportar_excel'),
    path('importar/', views.importar_excel, name='importar_excel'),
    path('saidas/exportar/', views.exportar_saidas_excel, name='exportar_saidas_excel'),
    path('modelo/', views.baixar_modelo_excel, name='baixar_modelo_excel'),
]