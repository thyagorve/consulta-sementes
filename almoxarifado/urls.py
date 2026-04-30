from django.urls import path
from . import views

app_name = 'almoxarifado'

urlpatterns = [
    path('', views.lista_itens, name='lista_itens'),
    path('saidas/', views.saidas_list, name='saidas_list'),
    path('item/buscar-codigo/', views.buscar_por_codigo, name='buscar_por_codigo'),
    path('item/adicionar/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:pk>/detalhe/', views.detalhe_item, name='detalhe_item'),
    path('item/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('item/<int:pk>/baixa/', views.dar_baixa, name='dar_baixa'),
    path('item/<int:pk>/excluir/', views.excluir_item, name='excluir_item'),
    path('buscar/', views.buscar_itens_ajax, name='buscar_itens_ajax'),
]