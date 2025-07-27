# sapp/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
import pandas as pd

from .forms import UploadPlanilhaCadastroForm, UploadPlanilhaLotesForm, ConfiguracaoExibicaoForm
from .models import ProdutoCadastro, EstoqueLote, ConfiguracaoExibicao, HistoricoConsulta

# --- Funções Auxiliares ---
def normalizar_colunas(df):
    """Limpa e padroniza os nomes das colunas de um DataFrame."""
    cols = [str(c).strip().lower() for c in df.columns]
    cols = [c.replace(' ', '').replace('_', '').replace('.', '').replace(',', '') for c in cols]
    cols = [c.replace(s, r) for s, r in [('ç', 'c'), ('ã', 'a'), ('á', 'a'), ('ó', 'o')] for c in cols]
    df.columns = cols
    return df

# --- Views de Autenticação e Navegação ---
@login_required
def dashboard(request): return render(request, 'sapp/dashboard.html')

def logout_view(request):
    if request.method == 'POST': logout(request)
    return redirect('login') 

# --- Views Principais ---
def consulta_view(request):
    context = {}
    if request.method == 'POST':
        termo_busca = request.POST.get('termo_busca', '').strip()
        search_type = request.POST.get('search_type', 'all') # Pega o tipo de busca, padrão é 'all'
        
        context['search_type'] = search_type # Envia o tipo de volta para o template

        if len(termo_busca) < 3 and '|' not in termo_busca:
            messages.warning(request, "Digite pelo menos 3 caracteres para buscar.")
        else:
            cadastros_encontrados = ProdutoCadastro.objects.none()
            lotes_encontrados = EstoqueLote.objects.none()

            # --- LÓGICA DE BUSCA REFEITA COM OPÇÕES ---
            if '|' in termo_busca:
                # Prioridade 1: QR Code sempre busca Lote + Cadastro
                try:
                    codigo, lote, *_ = [x.strip() for x in termo_busca.split('|')]
                    lotes_encontrados = EstoqueLote.objects.filter(lote=lote, codigo=codigo)
                    if lotes_encontrados.exists():
                        cadastros_encontrados = ProdutoCadastro.objects.filter(codigo=codigo)
                except ValueError: messages.error(request, "Formato do QR Code inválido.")
            
            elif search_type == 'cadastro':
                # Prioridade 2: Busca apenas no cadastro
                cadastros_encontrados = ProdutoCadastro.objects.filter(codigo__icontains=termo_busca)

            else: # Padrão ('all')
                # Prioridade 3: Busca em tudo
                lotes_encontrados = EstoqueLote.objects.filter(Q(lote__icontains=termo_busca) | Q(codigo__icontains=termo_busca))
                cadastros_encontrados = ProdutoCadastro.objects.filter(codigo__icontains=termo_busca)
            
            # --- LÓGICA DE APRESENTAÇÃO (sem alterações) ---
            if lotes_encontrados.exists() or cadastros_encontrados.exists():
                config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)
                campos_lote = config.campos_visiveis_lote.split(',') if config.campos_visiveis_lote else []
                campos_produto = config.campos_visiveis_produto.split(',') if config.campos_visiveis_produto else []
                context['lotes_detalhes'] = [{'lote': l, 'detalhes': [{'label': EstoqueLote._meta.get_field(c).verbose_name, 'valor': getattr(l, c, None) or '--'} for c in campos_lote]} for l in lotes_encontrados]
                context['cadastros_detalhes'] = [{'cadastro': c, 'detalhes': [{'label': ProdutoCadastro._meta.get_field(f).verbose_name, 'valor': getattr(c, f, None) or '--'} for f in campos_produto]} for c in cadastros_encontrados]
                HistoricoConsulta.objects.create(termo_buscado=termo_busca, usuario=request.user, resultados_encontrados=lotes_encontrados.count() + cadastros_encontrados.count())
            else:
                messages.error(request, f"Nenhum resultado encontrado para '{termo_busca}'.")

    return render(request, 'sapp/consulta.html', context)

@login_required
def historico_view(request):
    return render(request, 'sapp/historico.html', {'historico': HistoricoConsulta.objects.all()})

@login_required
def configuracao_view(request):
    # O código desta view continua o mesmo da versão funcional anterior.
    # Nenhuma alteração é necessária aqui.
    config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)
    if request.method == 'POST':
        if 'salvar_configuracao' in request.POST:
            form = ConfiguracaoExibicaoForm(request.POST)
            if form.is_valid():
                config.campos_visiveis_produto = ",".join(form.cleaned_data.get('campos_visiveis_produto', []))
                config.campos_visiveis_lote = ",".join(form.cleaned_data.get('campos_visiveis_lote', []))
                config.save(); messages.success(request, "Configurações salvas!")
            return redirect('configuracao')

        model, form_class, success_msg = (None, None, None)
        if 'upload_cadastro' in request.POST:
            model, form_class, success_msg = ProdutoCadastro, UploadPlanilhaCadastroForm, "produtos"
        elif 'upload_lotes' in request.POST:
            model, form_class, success_msg = EstoqueLote, UploadPlanilhaLotesForm, "lotes"
        
        if model:
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                try:
                    arquivo = next(iter(request.FILES.values()))
                    df_preview = pd.read_excel(arquivo, header=None, engine='openpyxl', nrows=20)
                    header_row_index = -1
                    key_cols = ['codigo'] if model == ProdutoCadastro else ['lote', 'codigo']
                    for i, row in df_preview.iterrows():
                        valores = [str(c).strip().lower().replace('ó', 'o') for c in row.values]
                        if all(k in valores for k in key_cols):
                            header_row_index = i
                            break
                    if header_row_index == -1: raise ValueError(f"Cabeçalho com {key_cols} não encontrado.")
                    
                    df = pd.read_excel(arquivo, header=header_row_index, engine='openpyxl', engine_kwargs={'data_only': True}, dtype=str)
                    df = normalizar_colunas(df)
                    df.dropna(subset=key_cols, how='all', inplace=True)

                    if model == EstoqueLote:
                        numericas = ['qnte', 'pme', 'volume', 'quantsc', 'quantbg', 'saldoliberado', 'germinacao', 'vigor', 'qntebloq', 'volumebloq', 'quantidadereserva']
                        for col in numericas:
                            if col in df.columns: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                        for col in ['dtfabricacao', 'dtvalidade']:
                            if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

                    model.objects.all().delete()
                    campos_modelo = {f.name for f in model._meta.get_fields()}
                    objetos = [model(**{k: v for k, v in row.to_dict().items() if k in campos_modelo and pd.notna(v) and str(v).strip() != ''}) for _, row in df.iterrows()]
                    model.objects.bulk_create(objetos, ignore_conflicts=True, batch_size=500)
                    messages.success(request, f"{len(objetos)} registros de {success_msg} importados.")
                except Exception as e:
                    messages.error(request, f"Erro ao processar planilha: {e}")
            return redirect('configuracao')
            
    context = {
        'form_cadastro': UploadPlanilhaCadastroForm(),
        'form_lotes': UploadPlanilhaLotesForm(),
        'form_config': ConfiguracaoExibicaoForm(initial={
            'campos_visiveis_produto': config.campos_visiveis_produto.split(','),
            'campos_visiveis_lote': config.campos_visiveis_lote.split(',')
        })
    }
    return render(request, 'sapp/configuracao.html', context)