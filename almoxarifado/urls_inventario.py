# almoxarifado/urls_inventario.py
#
# Se o seu arquivo já está assim,
# NÃO precisa alterar nada.

from django.urls import path

from . import views_inventario


app_name = 'inventario'


urlpatterns = [

    path(
        '',
        views_inventario
        .inventario_comparacao,
        name='comparacao',
    ),

    path(
        'api/item/<int:item_id>/validade/',
        views_inventario
        .api_item_validade,
        name='api_item_validade',
    ),

    path(
        'api/item/<int:item_id>/validade/salvar/',
        views_inventario
        .api_salvar_item_validade,
        name='api_salvar_item_validade',
    ),

    path(
        'api/importar/',
        views_inventario
        .api_importar_comparacao,
        name='api_importar',
    ),

    path(
        'api/<int:importacao_id>/linhas/',
        views_inventario
        .api_linhas_comparacao,
        name='api_linhas',
    ),

    path(
        'api/<int:importacao_id>/aplicar/',
        views_inventario
        .api_aplicar_decisoes,
        name='api_aplicar',
    ),

    path(
        'api/regras/salvar/',
        views_inventario
        .api_salvar_regra,
        name='api_salvar_regra',
    ),
]
