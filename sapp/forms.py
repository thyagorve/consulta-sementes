# sapp/forms.py

from django import forms
from .models import ProdutoCadastro, EstoqueLote

class ConfiguracaoExibicaoForm(forms.Form):
    # Função auxiliar para pegar as escolhas dos campos
    def _get_field_choices(model):
        choices = []
        # Percorre todos os campos do modelo
        for field in model._meta.get_fields():
            # Exclui campos de relacionamento e campos internos do Django que não queremos exibir
            if not field.is_relation and not field.name.startswith('_'):
                choices.append((field.name, field.verbose_name.title() or field.name.replace('_', ' ').title()))
        return sorted(choices, key=lambda x: x[1]) # Ordena por nome de exibição

    campos_visiveis_produto = forms.MultipleChoiceField(
        choices=_get_field_choices(ProdutoCadastro),
        widget=forms.CheckboxSelectMultiple,
        label="Campos para exibir de Produtos na Consulta",
        required=False
    )

    campos_visiveis_lote = forms.MultipleChoiceField(
        choices=_get_field_choices(EstoqueLote),
        widget=forms.CheckboxSelectMultiple,
        label="Campos para exibir de Lotes na Consulta",
        required=False
    )