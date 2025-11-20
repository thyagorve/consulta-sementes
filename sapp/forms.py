from django import forms
from .models import Estoque, Cultivar, Peneira, Categoria, Configuracao, Tratamento
from django.contrib.auth.models import User

# --- Entrada ---
class NovaEntradaForm(forms.ModelForm):
    class Meta:
        model = Estoque
        exclude = ['saida', 'saldo', 'peso_total', 'historico', 'conferente']
        widgets = {
            'data_entrada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ['ocultar_esgotados']
        widgets = {'ocultar_esgotados': forms.CheckboxInput(attrs={'class': 'form-check-input'})}

# --- Cadastros Auxiliares ---
class CultivarForm(forms.ModelForm):
    class Meta: model = Cultivar; fields = '__all__'

class PeneiraForm(forms.ModelForm):
    class Meta: model = Peneira; fields = '__all__'

class CategoriaForm(forms.ModelForm):
    class Meta: model = Categoria; fields = '__all__'

class TratamentoForm(forms.ModelForm):
    class Meta: model = Tratamento; fields = '__all__'

# --- Form para Adicionar Usuário (Login) ---
class NovoConferenteUserForm(forms.Form):
    username = forms.CharField(max_length=150, label="Login", widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=150, label="Nome Completo", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

# --- Senha ---
class MudarSenhaForm(forms.Form):
    nova_senha = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Nova Senha")
    confirmar_senha = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Confirmar Senha")

    def clean(self):
        cleaned_data = super().clean()
        s1 = cleaned_data.get("nova_senha")
        s2 = cleaned_data.get("confirmar_senha")
        if s1 and s2 and s1 != s2:
            raise forms.ValidationError("As senhas não conferem.")
        return cleaned_data

# --- Ações ---
class TransferenciaForm(forms.Form):
    quantidade = forms.IntegerField(min_value=1, label="Quantidade")
    novo_endereco = forms.CharField(max_length=50, label="Novo Endereço")

class EdicaoForm(forms.ModelForm):
    class Meta:
        model = Estoque
        fields = '__all__'