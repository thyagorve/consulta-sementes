from django.contrib import admin
from .models import Item, Saida


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'quantidade', 'unidade', 'departamento', 'localizacao', 'estoque_minimo', 'ativo', 'created_at']
    list_filter = ['departamento', 'unidade', 'ativo', 'created_at']
    search_fields = ['codigo', 'nome', 'descricao', 'fornecedor']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['quantidade', 'estoque_minimo', 'ativo']
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome', 'descricao')
        }),
        ('Classificação', {
            'fields': ('departamento', 'unidade', 'fornecedor')
        }),
        ('Estoque', {
            'fields': ('quantidade', 'estoque_minimo', 'localizacao')
        }),
        ('Financeiro', {
            'fields': ('valor_unitario',)
        }),
        ('Imagem', {
            'fields': ('foto',)
        }),
        ('Status e Datas', {
            'fields': ('ativo', 'created_at', 'updated_at')
        }),
    )


@admin.register(Saida)
class SaidaAdmin(admin.ModelAdmin):
    list_display = ['data', 'hora', 'solicitante', 'departamento', 'item_codigo', 'item_nome', 'quantidade']
    list_filter = ['data', 'departamento', 'solicitante']
    search_fields = ['solicitante', 'item_nome', 'item_codigo']
    readonly_fields = ['created_at']
    date_hierarchy = 'data'