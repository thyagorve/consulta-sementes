# sapp/filters.py

import django_filters
from django import forms
from django.db.models import Q
from .models import ProdutoCadastro, EstoqueLote

# ===================================================================
# FILTRO PARA A PÁGINA DE PRODUTOS
# ===================================================================
class ProdutoFilter(django_filters.FilterSet):
    
    # --- CAMPO DE BUSCA GERAL ---
    # Este campo de texto busca em várias colunas ao mesmo tempo.
    # Você pode customizar o label e o placeholder.
    busca_geral = django_filters.CharFilter(
        method='filtro_geral_produto', # Conecta ao método abaixo
        label="Busca Rápida",
        widget=forms.TextInput(attrs={'placeholder': 'Código, descrição, cultivar...'})
    )

    class Meta:
        model = ProdutoCadastro
        
        # --- CAMPOS DE FILTRO (DROPDOWNS) ---
        # AQUI VOCÊ ESCOLHE QUAIS CAMPOS DO SEU MODELO 'ProdutoCadastro'
        # VÃO APARECER COMO FILTROS DE SELEÇÃO (DROPDOWNS).
        # Basta adicionar ou remover os nomes dos campos da lista.
        #
        # Exemplos:
        # fields = ['tecnologia', 'tratamento', 'tipo', 'marca']
        #
        # Para começar, vamos deixar apenas 'tecnologia' e 'tipo'.
        
        fields = ['tecnologia', 'tipo']

    # Método que define o que a "Busca Rápida" faz.
    # Adicione ou remova campos da busca aqui.
    def filtro_geral_produto(self, queryset, name, value):
        return queryset.filter(
            Q(codigo__icontains=value) | 
            Q(descricao__icontains=value) |
            Q(cultivar__icontains=value) |
            Q(marca__icontains=value)
        )


# ===================================================================
# FILTRO PARA A PÁGINA DE LOTES
# ===================================================================
class LoteFilter(django_filters.FilterSet):

    # --- CAMPO DE BUSCA GERAL ---
    busca_geral = django_filters.CharFilter(
        method='filtro_geral_lote',
        label="Busca Rápida",
        widget=forms.TextInput(attrs={'placeholder': 'Lote, código, endereço...'})
    )
    
    # --- FILTRO DE INTERVALO DE DATAS ---
    # Este filtro cria dois campos de data "de" e "até".
    # O 'name' aqui ('dtvalidade') deve ser o nome exato do campo no seu models.py
    dtvalidade = django_filters.DateFromToRangeFilter(
        label="Validade entre",
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )

    class Meta:
        model = EstoqueLote
        
        # --- CAMPOS DE FILTRO (DROPDOWNS) ---
        # AQUI VOCÊ ESCOLHE QUAIS CAMPOS DO SEU MODELO 'EstoqueLote'
        # VÃO APARECER COMO FILTROS DE SELEÇÃO (DROPDOWNS).
        #
        # Exemplos:
        # fields = ['filial', 'categoria', 'tecnologia', 'tratamento']
        #
        # Vamos deixar apenas 'filial' e 'categoria' para começar.
        
        fields = ['filial', 'categoria']

    # Método que define o que a "Busca Rápida" de lotes faz.
    def filtro_geral_lote(self, queryset, name, value):
        return queryset.filter(
            Q(lote__icontains=value) |
            Q(codigo__icontains=value) |
            Q(endereco__icontains=value) |
            Q(produto__icontains=value)
        )