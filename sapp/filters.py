# sapp/filters.py

import django_filters
from .models import Estoque

class EstoqueFilter(django_filters.FilterSet):
    """Filtro para o estoque"""
    
    # Filtros de texto
    lote = django_filters.CharFilter(lookup_expr='icontains')
    produto = django_filters.CharFilter(lookup_expr='icontains')
    endereco = django_filters.CharFilter(lookup_expr='icontains')
    cliente = django_filters.CharFilter(lookup_expr='icontains')
    empresa = django_filters.CharFilter(lookup_expr='icontains')
    az = django_filters.CharFilter(lookup_expr='icontains')
    
    # Filtros de escolha múltipla (para os checkboxes)
    cultivar = django_filters.CharFilter(method='filter_by_name')
    peneira = django_filters.CharFilter(method='filter_by_name')
    categoria = django_filters.CharFilter(method='filter_by_name')
    tratamento = django_filters.CharFilter(method='filter_by_name')
    especie = django_filters.CharFilter(method='filter_by_name')
    
    # Filtros numéricos
    min_saldo = django_filters.NumberFilter(field_name='saldo', lookup_expr='gte')
    max_saldo = django_filters.NumberFilter(field_name='saldo', lookup_expr='lte')
    min_peso_total = django_filters.NumberFilter(field_name='peso_total', lookup_expr='gte')
    max_peso_total = django_filters.NumberFilter(field_name='peso_total', lookup_expr='lte')
    
    class Meta:
        model = Estoque
        fields = []
    
    def filter_by_name(self, queryset, name, value):
        """Filtra por nome do campo relacionado"""
        if value:
            # Mapeia o campo para o relacionamento
            field_map = {
                'cultivar': 'cultivar__nome',
                'peneira': 'peneira__nome',
                'categoria': 'categoria__nome',
                'tratamento': 'tratamento__nome',
                'especie': 'especie__nome',
            }
            
            field_name = field_map.get(name, name)
            
            # Se o valor for '__null__', filtra por nulo
            if value == '__null__':
                return queryset.filter(**{f"{field_name}__isnull": True})
            
            return queryset.filter(**{field_name: value})
        
        return queryset