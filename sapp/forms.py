# sapp/forms.py

from django import forms
from .models import ProdutoCadastro, EstoqueLote

class UploadPlanilhaCadastroForm(forms.Form):
    arquivo_cadastro = forms.FileField(label="Planilha de Cadastro de Produtos (.xlsx)")

class UploadPlanilhaLotesForm(forms.Form):
    arquivo_lotes = forms.FileField(label="Planilha de Mapa de Endereços/Estoque (.xlsx)")

class ConfiguracaoExibicaoForm(forms.Form):
    CAMPOS_PRODUTO_CHOICES = [(f.name, f.verbose_name.capitalize()) for f in ProdutoCadastro._meta.get_fields() if not f.is_relation]
    CAMPOS_LOTE_CHOICES = [(f.name, f.verbose_name.capitalize()) for f in EstoqueLote._meta.get_fields() if not f.is_relation]
    
    campos_visiveis_produto = forms.MultipleChoiceField(
        choices=sorted(CAMPOS_PRODUTO_CHOICES), widget=forms.CheckboxSelectMultiple,
        label="Campos do CADASTRO para Exibir", required=False
    )
    campos_visiveis_lote = forms.MultipleChoiceField(
        choices=sorted(CAMPOS_LOTE_CHOICES), widget=forms.CheckboxSelectMultiple,
        label="Campos do LOTE/ESTOQUE para Exibir", required=False
    )