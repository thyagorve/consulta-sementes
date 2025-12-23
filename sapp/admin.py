# sapp/admin.py
from django.contrib import admin
from .models import Empenho, ItemEmpenho, EmpenhoStatus

@admin.register(Empenho)
class EmpenhoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo_movimentacao', 'status', 'data_criacao')
    list_filter = ('status', 'tipo_movimentacao', 'data_criacao')
    search_fields = ('usuario__username', 'numero_carga', 'observacao')

@admin.register(ItemEmpenho)
class ItemEmpenhoAdmin(admin.ModelAdmin):
    list_display = ('lote', 'quantidade', 'endereco_origem', 'endereco_destino')
    list_filter = ('empenho__status',)
    search_fields = ('lote', 'cultivar')

@admin.register(EmpenhoStatus)
class EmpenhoStatusAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')