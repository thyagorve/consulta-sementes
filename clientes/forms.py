# clientes/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Servico, Tag, Atualizacao, Configuracao, Tutorial


User = get_user_model()
from django import forms
from .models import CustomUser, Tag, Servico

# clientes/forms.py
from decimal import Decimal

from django import forms
from .models import CustomUser, Servico
import uuid
from django import forms
from .models import CustomUser, Servico, Tag
from decimal import Decimal
import uuid
class ClienteForm(forms.ModelForm):
    """
    Formulário de cadastro/edição de cliente
    """
    
    login_externo = forms.CharField(
        max_length=150,
        required=False,
        label="Login do Serviço (IPTV)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Login de acesso ao serviço'
        }),
        help_text="Pode ser compartilhado entre vários clientes do mesmo plano"
    )
    
    senha_leitura = forms.CharField(
        required=False,
        label="Senha do Serviço (IPTV)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha de acesso ao serviço'
        })
    )
    
    pago = forms.BooleanField(required=False, label="Cliente pagou?", initial=False)

    class Meta:
        model = CustomUser
        fields = [
            'nome', 'tipo_usuario', 'login_externo', 'senha_leitura', 
            'data_vencimento', 'plano', 'whatsapp', 'observacao',
        ]
        widgets = {
            'data_vencimento': forms.DateInput(
                attrs={'type': 'date', 'placeholder': 'dd-mm-yyyy'}, 
                format='%Y-%m-%d'
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self._user = user
        is_editing = bool(self.instance.pk)
        
        # ==========================================
        # CAMPO TIPO DE USUÁRIO
        # ==========================================
        if user:
            if user.tipo_usuario == 'admin' or user.is_superuser:
                # Admin pode criar/editar como cliente ou revenda
                self.fields['tipo_usuario'] = forms.ChoiceField(
                    choices=[
                        ('cliente', 'Cliente'),
                        ('revenda', 'Revenda'),
                        ('admin', 'Admin'),
                    ],
                    initial=self.instance.tipo_usuario if is_editing else 'cliente',
                    required=False,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )
            elif user.tipo_usuario == 'revenda':
                # Revenda só pode criar clientes
                self.fields['tipo_usuario'] = forms.ChoiceField(
                    choices=[('cliente', 'Cliente')],
                    initial='cliente',
                    required=False,
                    widget=forms.HiddenInput()
                )
            else:
                self.fields['tipo_usuario'] = forms.ChoiceField(
                    choices=[('cliente', 'Cliente')],
                    initial='cliente',
                    required=False,
                    widget=forms.HiddenInput()
                )
        
        # ==========================================
        # CAMPOS DA INSTÂNCIA (EDIÇÃO)
        # ==========================================
        if is_editing:
            # Login externo
            if self.instance.login_externo:
                self.fields['login_externo'].initial = self.instance.login_externo
            
            # Senha leitura
            if self.instance.senha_leitura:
                self.fields['senha_leitura'].initial = self.instance.senha_leitura
            
            # Nome
            if self.instance.nome:
                self.fields['nome'].initial = self.instance.nome
            
            # WhatsApp
            if self.instance.whatsapp:
                self.fields['whatsapp'].initial = self.instance.whatsapp
            
            # Observação
            if self.instance.observacao:
                self.fields['observacao'].initial = self.instance.observacao
            
            # Data de vencimento
            if self.instance.data_vencimento:
                self.fields['data_vencimento'].initial = self.instance.data_vencimento
        
        # ==========================================
        # FILTRA PLANOS DO USUÁRIO LOGADO
        # ==========================================
        if user:
            self.fields['plano'].queryset = Servico.objects.filter(revenda=user)
            self.fields['plano'].required = False
            self.fields['plano'].widget.attrs.update({'class': 'form-control'})
        else:
            self.fields['plano'].queryset = Servico.objects.none()
        
        # ==========================================
        # CAMPOS DE VALOR (CHARFIELD)
        # ==========================================
        valor_servico_inicial = None
        valor_pagar_inicial = None
        
        if is_editing and self.instance:
            # Busca custo FIFO para mostrar
            if self.instance.plano and self.instance.plano.controlar_estoque and self.instance.plano.tipo_estoque in ['creditos', 'ambos']:
                from .models import LoteEstoque
                lote_fifo = LoteEstoque.objects.filter(
                    servico=self.instance.plano,
                    quantidade_restante__gt=0
                ).order_by('ordem').first()
                if lote_fifo:
                    valor_servico_inicial = str(lote_fifo.custo_unitario.quantize(Decimal('0.01')))
                elif self.instance.plano.custos and self.instance.plano.custos > 0:
                    valor_servico_inicial = str(self.instance.plano.custos.quantize(Decimal('0.01')))
                else:
                    valor_servico_inicial = str((self.instance.valor_servico or Decimal('0.00')).quantize(Decimal('0.01')))
            else:
                valor_servico_inicial = str((self.instance.valor_servico or Decimal('0.00')).quantize(Decimal('0.01')))
            
            valor_pagar_inicial = str((self.instance.valor_a_pagar or Decimal('0.00')).quantize(Decimal('0.01')))
        
        self.fields['valor_servico'] = forms.CharField(
            required=False,
            initial=valor_servico_inicial,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00'
            })
        )
        
        self.fields['valor_a_pagar'] = forms.CharField(
            required=False,
            initial=valor_pagar_inicial,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00'
            })
        )
        
        # ==========================================
        # CLASSES CSS PARA TODOS OS CAMPOS
        # ==========================================
        for field_name, field in self.fields.items():
            if field_name not in ['tipo_usuario', 'pago', 'login_externo', 'senha_leitura', 
                                   'valor_servico', 'valor_a_pagar', 'plano']:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs.update({'class': 'form-control'})
        
        # ==========================================
        # TORNA CAMPOS NÃO OBRIGATÓRIOS
        # ==========================================
        self.fields['nome'].required = True  # Nome é obrigatório
        self.fields['login_externo'].required = False
        self.fields['senha_leitura'].required = False
        self.fields['whatsapp'].required = False
        self.fields['observacao'].required = False
        self.fields['data_vencimento'].required = False
        self.fields['valor_servico'].required = False
        self.fields['valor_a_pagar'].required = False

    def clean(self):
        cleaned_data = super().clean()
        login_externo = cleaned_data.get('login_externo', '').strip()
        senha_leitura = cleaned_data.get('senha_leitura', '').strip()
        
        # Garante que login_externo e senha_leitura não sejam None
        if login_externo is None:
            cleaned_data['login_externo'] = ''
        if senha_leitura is None:
            cleaned_data['senha_leitura'] = ''
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # ==========================================
        # GERA USERNAME ÚNICO SE VAZIO
        # ==========================================
        if not user.username:
            import uuid
            user.username = f"user_{uuid.uuid4().hex[:10]}"
        
        # ==========================================
        # NOME COMPLETO
        # ==========================================
        nome = self.cleaned_data.get('nome', '').strip()
        if nome:
            user.nome = nome
            user.first_name = nome
        
        # ==========================================
        # LOGIN EXTERNO (IPTV)
        # ==========================================
        login_externo = self.cleaned_data.get('login_externo', '')
        if login_externo is not None:
            user.login_externo = login_externo.strip() if login_externo else ''
        
        # ==========================================
        # TIPO DE USUÁRIO
        # ==========================================
        if 'tipo_usuario' in self.cleaned_data and self.cleaned_data['tipo_usuario']:
            user.tipo_usuario = self.cleaned_data['tipo_usuario']
        elif not user.tipo_usuario:
            user.tipo_usuario = 'cliente'
        
        # ==========================================
        # SENHA DO SERVIÇO (IPTV)
        # ==========================================
        senha_leitura = self.cleaned_data.get('senha_leitura', '')
        if senha_leitura is not None:
            user.senha_leitura = senha_leitura.strip() if senha_leitura else ''
        
        # ==========================================
        # WHATSAPP
        # ==========================================
        whatsapp = self.cleaned_data.get('whatsapp', '')
        if whatsapp is not None:
            user.whatsapp = whatsapp.strip() if whatsapp else ''
        
        # ==========================================
        # OBSERVAÇÃO
        # ==========================================
        observacao = self.cleaned_data.get('observacao', '')
        if observacao is not None:
            user.observacao = observacao.strip() if observacao else ''
        
        # ==========================================
        # DATA DE VENCIMENTO
        # ==========================================
        data_vencimento = self.cleaned_data.get('data_vencimento')
        if data_vencimento is not None:
            user.data_vencimento = data_vencimento
        
        # ==========================================
        # PLANO
        # ==========================================
        plano = self.cleaned_data.get('plano')
        if plano is not None:
            user.plano = plano
        elif 'plano' in self.cleaned_data and self.cleaned_data['plano'] is None:
            # Permite remover o plano
            user.plano = None
        
        # ==========================================
        # VALOR DO SERVIÇO (CUSTO)
        # ==========================================
        valor_servico = self.cleaned_data.get('valor_servico', '')
        if valor_servico:
            if isinstance(valor_servico, str):
                valor_servico = valor_servico.replace(',', '.')
            try:
                user.valor_servico = Decimal(str(valor_servico)).quantize(Decimal('0.01'))
            except:
                user.valor_servico = Decimal('0.00')
        
        # ==========================================
        # VALOR A PAGAR
        # ==========================================
        valor_a_pagar = self.cleaned_data.get('valor_a_pagar', '')
        if valor_a_pagar:
            if isinstance(valor_a_pagar, str):
                valor_a_pagar = valor_a_pagar.replace(',', '.')
            try:
                user.valor_a_pagar = Decimal(str(valor_a_pagar)).quantize(Decimal('0.01'))
            except:
                user.valor_a_pagar = Decimal('0.00')
        
        # ==========================================
        # DONO (REVENDA)
        # ==========================================
        if self._user and not user.dono:
            user.dono = self._user
        
        # ==========================================
        # SALVA
        # ==========================================
        if commit:
            user.save()
            # Salva ManyToMany (tags são tratadas na view)
        
        return user

class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = [
            'nome', 'tipo_plano', 'valor', 'custos', 'cor', 'observacao',
            'controlar_estoque',  # ← Certifique-se que está aqui
            'multiplicador',
            'usuario_unico',
            'exigir_usuario', 'exigir_senha',
            'exigir_nome', 'exigir_email', 'exigir_cpf',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do plano'}),
            'tipo_plano': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'R$ 0,00', 'step': '0.01'}),
            'custos': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'R$ 0,00', 'step': '0.01'}),
            'cor': forms.TextInput(attrs={'type': 'color', 'class': 'form-control-color'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'controlar_estoque': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'multiplicador': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
            'usuario_unico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exigir_usuario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exigir_senha': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exigir_nome': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exigir_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exigir_cpf': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': 'Nome do Plano',
            'tipo_plano': 'Tipo de Plano',
            'valor': 'Valor de Venda (R$)',
            'custos': 'Custos (R$)',
            'cor': 'Cor do Plano',
            'observacao': 'Observação',
            'controlar_estoque': 'Controlar Estoque',
            'estoque': 'Quantidade em Estoque',
            'multiplicador': 'Multiplicador',
            'exigir_usuario': 'Exigir Usuário',
            'exigir_senha': 'Exigir Senha',
            'usuario_unico': 'Usuário Único',
            'exigir_nome': 'Exigir Nome',
            'exigir_email': 'Exigir E-mail',
            'exigir_cpf': 'Exigir CPF',
        }
        help_texts = {
            'multiplicador': 'Quantas vendas cada unidade de estoque permite',
            'usuario_unico': 'Se marcado, não permite usuários duplicados no sistema',
            'controlar_estoque': 'Ativa o controle de estoque para este plano',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos de estoque só aparecem se controlar_estoque estiver marcado
        # (isso será controlado via JavaScript no frontend)
        
        # Define valores padrão por tipo de plano
        if not self.instance.pk:  # Novo cadastro
            self.fields['tipo_plano'].initial = 'assinatura'

class UploadFileForm(forms.Form):
    arquivo = forms.FileField(label="Selecione o arquivo para upload")



# forms.py
from django import forms
from .models import Tag

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome da Tag'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Descrição da Tag'}),
        }



from django import forms
from .models import ConfiguracaoMensagem, MensagemConfigurada

class ConfiguracaoMensagemForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoMensagem
        fields = []  # Nenhum campo direto, pois está vinculado a MensagemConfigurada

class MensagemConfiguradaForm(forms.ModelForm):
    class Meta:
        model = MensagemConfigurada
        fields = ['criterio_dias', 'mensagem_texto', 'horario_envio']




from django.shortcuts import render, redirect
from .models import ConfiguracaoMensagem
from .forms import ConfiguracaoMensagemForm

def configuracao_mensagens(request):
    config = ConfiguracaoMensagem.objects.first()
    if request.method == "POST":
        form = ConfiguracaoMensagemForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            return redirect("configuracao_mensagens")
    else:
        form = ConfiguracaoMensagemForm(instance=config)
    return render(request, "configuracao_mensagens.html", {"form": form})





class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = [
            'mercado_pago_access_token', 
            'email', 
            'token_telegram',
            'chave_telegram',
            'numero_celular', 
            'senha',
        ]

    def __init__(self, *args, **kwargs):
        is_admin = kwargs.pop('is_admin', False)
        super(ConfiguracaoForm, self).__init__(*args, **kwargs)
        
        # Remove campos que não-admin não deve ver
        if not is_admin:
            self.fields.pop('mercado_pago_access_token', None)
        
        # Adiciona classes Bootstrap
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})







class AtualizacaoForm(forms.ModelForm):
    class Meta:
        model = Atualizacao
        fields = ['versao', 'titulo', 'tipo', 'descricao', 'imagem']
        widgets = {
            'versao': forms.TextInput(attrs={'class': 'form-control'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control'}),
        }


# forms.py
from django import forms
from .models import Tutorial

class TutorialForm(forms.ModelForm):
    class Meta:
        model = Tutorial
        fields = ['titulo', 'descricao', 'video_url']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Como criar uma planilha'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descreva o tutorial... (suporta Markdown)',
                'rows': 5
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
        }
        labels = {
            'titulo': 'Título do Tutorial',
            'descricao': 'Descrição',
            'video_url': 'URL do Vídeo do YouTube',
        }
        help_texts = {
            'video_url': 'Cole o link do vídeo do YouTube',
        }
    
    def clean_video_url(self):
        url = self.cleaned_data.get('video_url')
        if url:
            import re
            # Verifica se é uma URL válida do YouTube
            patterns = [
                r'youtube\.com/watch\?v=[a-zA-Z0-9_-]{11}',
                r'youtu\.be/[a-zA-Z0-9_-]{11}',
                r'youtube\.com/embed/[a-zA-Z0-9_-]{11}',
            ]
            valid = False
            for pattern in patterns:
                if re.search(pattern, url):
                    valid = True
                    break
            
            if not valid:
                raise forms.ValidationError('Insira uma URL válida do YouTube')
        
        return url


