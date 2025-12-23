from django import forms
from .models import Empenho, ItemEmpenho, Estoque

class EmpenhoForm(forms.ModelForm):
    class Meta:
        model = Empenho
        fields = ['tipo_movimentacao', 'observacao', 'numero_carga', 'motorista', 'placa', 'cliente', 'ordem_entrega']
        widgets = {
            'tipo_movimentacao': forms.Select(attrs={
                'class': 'form-control',
                'id': 'tipo_movimentacao',
                'onchange': 'atualizarCamposTipo()'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações sobre o empenho...'
            }),
            'numero_carga': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da carga'
            }),
            'motorista': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do motorista'
            }),
            'placa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Placa do veículo'
            }),
            'cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cliente destino'
            }),
            'ordem_entrega': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ordem de entrega'
            }),
        }

class AdicionarItemEmpenhoForm(forms.Form):
    lote_id = forms.IntegerField(widget=forms.HiddenInput())
    quantidade = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantidade',
            'min': 1
        })
    )
    endereco_destino = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Endereço destino (para transferência)'
        })
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Observação do item'
        })
    )
    
    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        lote_id = self.data.get('lote_id')
        
        if lote_id:
            try:
                estoque = Estoque.objects.get(id=lote_id)
                if quantidade > estoque.saldo:
                    raise forms.ValidationError(
                        f"Quantidade excede o saldo disponível ({estoque.saldo})"
                    )
            except Estoque.DoesNotExist:
                raise forms.ValidationError("Lote não encontrado")
        
        return quantidade

class ConfirmarEmpenhoForm(forms.Form):
    confirmacao = forms.BooleanField(
        required=True,
        label="Confirmo que desejo executar esta movimentação",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )