from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Estoque, Cultivar, Peneira, Categoria, Tratamento, 
    Configuracao, Especie, Produto, ArmazemLayout
)
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User

class NovaEntradaForm(forms.ModelForm):
    class Meta:
        model = Estoque
        fields = [
            'lote', 'produto', 'cultivar', 'peneira', 'categoria', 
            'tratamento', 'endereco', 'entrada', 'embalagem', 
            'peso_unitario', 'empresa', 'origem_destino', 'az',
            'cliente', 'observacao'
        ]
        widgets = {
            'lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: ABC12345',
                'required': True
            }),
            'produto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do produto'
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: P-01-02-03',
                'required': True
            }),
            'entrada': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'required': True
            }),
            'peso_unitario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00'
            }),
            'empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da empresa'
            }),
            'origem_destino': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Origem/Destino'
            }),
            'az': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do armazém'
            }),
            'cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cliente/Dono do bag'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações importantes...'
            }),
            'cultivar': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'peneira': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'tratamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'embalagem': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean_lote(self):
        lote = self.cleaned_data.get('lote', '').strip()
        if not lote:
            raise ValidationError("O número do lote é obrigatório.")
        return lote
    
    def clean_endereco(self):
        endereco = self.cleaned_data.get('endereco', '').strip().upper()
        if not endereco:
            raise ValidationError("O endereço é obrigatório.")
        return endereco
    
    def clean_entrada(self):
        entrada = self.cleaned_data.get('entrada', 0)
        if entrada <= 0:
            raise ValidationError("A quantidade deve ser maior que zero.")
        return entrada
    
    def clean_peso_unitario(self):
        peso = self.cleaned_data.get('peso_unitario')
        if peso:
            try:
                if isinstance(peso, str):
                    peso = peso.replace(',', '.')
                return Decimal(str(peso))
            except (InvalidOperation, ValueError):
                return Decimal('0.00')
        return Decimal('0.00')
    
    def clean(self):
        cleaned_data = super().clean()
        lote = cleaned_data.get('lote')
        endereco = cleaned_data.get('endereco')
        cultivar = cleaned_data.get('cultivar')
        
        if lote and endereco and cultivar:
            existe = Estoque.objects.filter(
                lote=lote,
                endereco=endereco,
                cultivar=cultivar
            ).exists()
            
            if existe and not self.instance.pk:
                raise ValidationError(
                    f"Já existe um lote '{lote}' no endereço '{endereco}' com o mesmo cultivar."
                )
        
        return cleaned_data

class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ['ocultar_esgotados']
        widgets = {
            'ocultar_esgotados': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }
        labels = {
            'ocultar_esgotados': 'Ocultar lotes esgotados nas consultas'
        }

class CultivarForm(forms.ModelForm):
    class Meta:
        model = Cultivar
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do cultivar',
                'required': True,
                'autofocus': True
            }),
        }
        labels = {
            'nome': 'Nome do Cultivar'
        }

class PeneiraForm(forms.ModelForm):
    class Meta:
        model = Peneira
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da peneira',
                'required': True,
                'autofocus': True
            }),
        }
        labels = {
            'nome': 'Nome da Peneira'
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da categoria',
                'required': True,
                'autofocus': True
            }),
        }
        labels = {
            'nome': 'Nome da Categoria'
        }

class TratamentoForm(forms.ModelForm):
    class Meta:
        model = Tratamento
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do tratamento',
                'required': True,
                'autofocus': True
            }),
        }
        labels = {
            'nome': 'Nome do Tratamento'
        }

class NovoConferenteUserForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Login de Acesso",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ex: joao.silva',
            'required': True,
            'autofocus': True
        })
    )
    first_name = forms.CharField(
        max_length=150,
        label="Nome de Exibição",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome Completo',
            'required': True
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Este nome de usuário já está em uso.")
        return username

class MudarSenhaForm(forms.Form):
    senha_atual = forms.CharField(
        label="Senha Atual",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    nova_senha = forms.CharField(
        label="Nova Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )
    confirmar_senha = forms.CharField(
        label="Confirmar Nova Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get('nova_senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        
        if nova_senha and confirmar_senha and nova_senha != confirmar_senha:
            raise forms.ValidationError("As senhas não coincidem.")
        
        return cleaned_data

class ArmazemLayoutForm(forms.ModelForm):
    class Meta:
        model = ArmazemLayout
        fields = ['numero', 'nome', 'largura_canvas', 'altura_canvas', 'ativo']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do armazém'
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do armazém'
            }),
            'largura_canvas': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Largura em pixels'
            }),
            'altura_canvas': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Altura em pixels'
            }),
        }
        labels = {
            'numero': 'Número',
            'nome': 'Nome',
            'largura_canvas': 'Largura do Canvas',
            'altura_canvas': 'Altura do Canvas',
            'ativo': 'Ativo'
        }
    
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if not self.instance.pk and ArmazemLayout.objects.filter(numero=numero).exists():
            raise ValidationError(f"Já existe um armazém com o número {numero}.")
        return numero

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['cultivar', 'tipo', 'codigo', 'descricao', 'peneira', 
                  'empresa', 'especie', 'categoria', 'tratamento', 'ativo']
        widgets = {
            'cultivar': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'tipo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'soja, milho, trigo...'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '4604000001',
                'required': True
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição completa do produto...',
                'required': True
            }),
            'peneira': forms.Select(attrs={
                'class': 'form-control'
            }),
            'empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Conceito Sementes'
            }),
            'especie': forms.Select(attrs={
                'class': 'form-control'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tratamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'cultivar': 'Cultivar *',
            'tipo': 'Tipo',
            'codigo': 'Código do Produto *',
            'descricao': 'Descrição *',
            'peneira': 'Peneira',
            'empresa': 'Empresa',
            'especie': 'Espécie',
            'categoria': 'Categoria',
            'tratamento': 'Tratamento',
            'ativo': 'Produto Ativo'
        }
    
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip().upper()
        if not codigo:
            raise ValidationError("O código do produto é obrigatório.")
        
        if not self.instance.pk and Produto.objects.filter(codigo=codigo).exists():
            raise ValidationError(f"Já existe um produto com o código '{codigo}'.")
        
        return codigo
    
    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao', '').strip()
        if not descricao:
            raise ValidationError("A descrição do produto é obrigatória.")
        return descricao