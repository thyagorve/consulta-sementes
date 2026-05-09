from django.contrib import admin
from .models import Item, Saida, EntradaNotaFiscal, ItemEntrada


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


@admin.register(EntradaNotaFiscal)
class EntradaNotaFiscalAdmin(admin.ModelAdmin):
    list_display = ('numero_nota', 'fornecedor_nome', 'data_emissao', 'valor_total', 'data_recebimento')
    search_fields = ('numero_nota', 'chave_acesso', 'fornecedor_nome')
    date_hierarchy = 'data_emissao'

# No arquivo almoxarifado/admin.py
@admin.register(ItemEntrada)
class ItemEntradaAdmin(admin.ModelAdmin):
    # Verifique se os nomes abaixo batem EXATAMENTE com o seu models.py
    list_display = ('nota_fiscal', 'item', 'quantidade_nota', 'preco_unitario') 
    list_filter = ('item',)