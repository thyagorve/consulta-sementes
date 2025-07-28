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
def normalizar_colunas(nomes_colunas):
    """Limpa e padroniza uma lista de nomes de colunas de forma segura."""
    limpo = []
    for c in nomes_colunas:
        col = str(c).strip().lower()
        replacements = {' ': '', '_': '', '.': '', ',': '', 'ç': 'c', 'ã': 'a', 'á': 'a', 'ó': 'o'}
        for old, new in replacements.items():
            col = col.replace(old, new)
        limpo.append(col)
    return limpo

# --- Views de Autenticação e Navegação ---
@login_required
def dashboard(request): return render(request, 'sapp/dashboard.html')

def logout_view(request):
    if request.method == 'POST': logout(request)
    return redirect('login') 

from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render
from .models import ProdutoCadastro, EstoqueLote, ConfiguracaoExibicao, HistoricoConsulta

from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render
from .models import ProdutoCadastro, EstoqueLote, ConfiguracaoExibicao, HistoricoConsulta

def consulta_view(request):
    context = {
        'search_type': 'all',
        'termo_buscado': '',
        'resultados': []
    }

    if request.method == 'POST':
        termo = request.POST.get('termo_busca', '').strip()
        search_type = request.POST.get('search_type', 'all')
        context.update({'search_type': search_type, 'termo_buscado': termo})

        if len(termo) < 3 and '|' not in termo:
            messages.warning(request, "Digite pelo menos 3 caracteres para buscar.")
            return render(request, 'sapp/consulta.html', context)

        cadastros = ProdutoCadastro.objects.none()
        lotes = EstoqueLote.objects.none()
        lote_filtro_exato = None  # Para destacar se buscar por lote ou QR Code

        try:
            if '|' in termo:  # QR Code
                partes = [x.strip() for x in termo.split('|') if x.strip()]
                if len(partes) >= 2:
                    codigo, lote = partes[0], partes[1]  # Pega só os 2 primeiros
                    cadastros = ProdutoCadastro.objects.filter(codigo__iexact=codigo)
                    lotes = EstoqueLote.objects.filter(codigo__iexact=codigo, lote__iexact=lote)
                    lote_filtro_exato = lote

            else:
                if search_type == 'cadastro':
                    cadastros = ProdutoCadastro.objects.filter(codigo__icontains=termo)
                    if cadastros.exists():
                        codigos = cadastros.values_list('codigo', flat=True)
                        lotes = EstoqueLote.objects.filter(codigo__in=codigos)

                elif search_type == 'lote':
                    lotes = EstoqueLote.objects.filter(lote__icontains=termo)
                    if lotes.exists():
                        codigos = lotes.values_list('codigo', flat=True)
                        cadastros = ProdutoCadastro.objects.filter(codigo__in=codigos)
                        lote_filtro_exato = termo  # Para destaque

                else:  # all
                    cadastros = ProdutoCadastro.objects.filter(codigo__icontains=termo)
                    lotes = EstoqueLote.objects.filter(Q(lote__icontains=termo) | Q(codigo__icontains=termo))
                    if lotes.exists() and cadastros.count() == 0:
                        # Se só tem lotes, tenta trazer produto relacionado
                        codigos = lotes.values_list('codigo', flat=True)
                        cadastros = ProdutoCadastro.objects.filter(codigo__in=codigos)
                        if not cadastros.exists():
                            lote_filtro_exato = termo  # Pesquisa foi baseada em lote

        except ValueError:
            messages.error(request, "Formato do QR Code inválido.")

        if cadastros.exists() or lotes.exists():
            config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)
            campos_lote = config.campos_visiveis_lote.split(',') if config.campos_visiveis_lote else []
            campos_produto = config.campos_visiveis_produto.split(',') if config.campos_visiveis_produto else []

            resultados = []

            # Cria cards para cada produto
            for produto in cadastros:
                lotes_relacionados = [l for l in lotes if l.codigo == produto.codigo]

                # Se busca foi por lote, filtra destaque
                if lote_filtro_exato:
                    lotes_relacionados = [l for l in lotes_relacionados if lote_filtro_exato.lower() in l.lote.lower()] or lotes_relacionados

                resultados.append({
                    'produto': produto,
                    'detalhes_produto': [
                        {'label': ProdutoCadastro._meta.get_field(f).verbose_name, 'valor': getattr(produto, f, None) or '--'}
                        for f in campos_produto if hasattr(produto, f)
                    ],
                    'lotes': [
                        {
                            'obj': lote,
                            'detalhes': [
                                {'label': EstoqueLote._meta.get_field(c).verbose_name, 'valor': getattr(lote, c, None) or '--'}
                                for c in campos_lote if hasattr(lote, c)
                            ],
                            'destaque': (lote_filtro_exato and lote.lote.lower() == lote_filtro_exato.lower())
                        } for lote in lotes_relacionados
                    ]
                })

            # Caso exista lote sem cadastro vinculado → mostra como "lote órfão"
            lotes_sem_produto = [l for l in lotes if not cadastros.filter(codigo=l.codigo).exists()]
            for lote in lotes_sem_produto:
                resultados.append({
                    'produto': None,
                    'detalhes_produto': [],
                    'lotes': [{
                        'obj': lote,
                        'detalhes': [
                            {'label': EstoqueLote._meta.get_field(c).verbose_name, 'valor': getattr(lote, c, None) or '--'}
                            for c in campos_lote if hasattr(lote, c)
                        ],
                        'destaque': (lote_filtro_exato and lote.lote.lower() == lote_filtro_exato.lower())
                    }]
                })

            context['resultados'] = resultados

            HistoricoConsulta.objects.create(
                termo_buscado=termo,
                usuario=request.user,
                resultados_encontrados=len(resultados)
            )

            messages.success(request, f"Encontrados {len(resultados)} resultado(s).")
        else:
            messages.error(request, f"Nenhum resultado encontrado para '{termo}'.")

    return render(request, 'sapp/consulta.html', context)





@login_required
def historico_view(request):
    return render(request, 'sapp/historico.html', {'historico': HistoricoConsulta.objects.all()})

@login_required
def configuracao_view(request):
    config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)
    if request.method == 'POST':
        if 'salvar_configuracao' in request.POST:
            form = ConfiguracaoExibicaoForm(request.POST)
            if form.is_valid():
                config.campos_visiveis_produto = ",".join(form.cleaned_data.get('campos_visiveis_produto', []))
                config.campos_visiveis_lote = ",".join(form.cleaned_data.get('campos_visiveis_lote', []))
                config.save(); messages.success(request, "Configurações salvas!")
            return redirect('configuracao')

        model, form_class, success_msg, key_cols = (None, None, None, None)
        if 'upload_cadastro' in request.POST:
            form_instance, model, success_msg, key_cols = UploadPlanilhaCadastroForm(request.POST, request.FILES), ProdutoCadastro, "produtos", ['codigo']
        elif 'upload_lotes' in request.POST:
            form_instance, model, success_msg, key_cols = UploadPlanilhaLotesForm(request.POST, request.FILES), EstoqueLote, "lotes", ['lote', 'codigo']
        
        if form_instance and form_instance.is_valid():
            try:
                arquivo = next(iter(request.FILES.values()))
                df_preview = pd.read_excel(arquivo, header=None, engine='openpyxl', nrows=20, dtype=str)
                header_row_index = next((i for i, r in df_preview.iterrows() if all(k in [str(c).strip().lower().replace('ó', 'o') for c in r.values] for k in key_cols)), -1)
                if header_row_index == -1: raise ValueError(f"Cabeçalho com {key_cols} não encontrado.")

                df = pd.read_excel(arquivo, header=header_row_index, engine='openpyxl', engine_kwargs={'data_only': True}, dtype=str)
                df.columns = normalizar_colunas(df.columns)
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
        'form_config': ConfiguracaoExibicaoForm(initial={'campos_visiveis_produto': config.campos_visiveis_produto.split(','), 'campos_visiveis_lote': config.campos_visiveis_lote.split(',')})
    }
    return render(request, 'sapp/configuracao.html', context)