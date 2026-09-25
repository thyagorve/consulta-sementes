from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('relatorio/', views.relatorio_financeiro, name='relatorio_financeiro'),
    path('adicionar/', views.adicionar_relatorio, name='adicionar_relatorio'),
]
