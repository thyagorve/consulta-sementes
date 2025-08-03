# sapp/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
import pandas as pd
import io # Para ler o texto como se fosse um arquivo
from django.core.paginator import Paginator

from django.http import JsonResponse # Para as views de API
from .forms import ConfiguracaoExibicaoForm # Importe apenas este, os outros foram substituídos
from .models import ProdutoCadastro, EstoqueLote, ConfiguracaoExibicao, HistoricoConsulta
from .filters import ProdutoFilter, LoteFilter 


# Em sapp/views.py

def normalizar_colunas(nomes_colunas):
    """Limpa e padroniza uma lista de nomes de colunas de forma mais flexível."""
    limpo = []
    # Palavras a serem ignoradas nos nomes das colunas
    palavras_ignoradas = ['mapa']

    for c in nomes_colunas:
        col = str(c).strip().lower()
        
        # Remove palavras ignoradas
        for palavra in palavras_ignoradas:
            col = col.replace(palavra, '')

        # Substituições de caracteres especiais
        replacements = {
            ' ': '', '_': '', '.': '', ',': '', 'ç': 'c', 'ã': 'a', 'á': 'a',
            'ó': 'o', 'é': 'e', 'í': 'i', 'ú': 'u', 'ê': 'e', 'ô': 'o',
            '(': '', ')': '', '-': ''
        }
        for old, new in replacements.items():
            col = col.replace(old, new)
        
        # Remove espaços duplos que possam ter sido criados
        col = col.strip()
        limpo.append(col)
        
    return limpo

# sapp/views.py

@login_required
def dashboard(request):
    # Ela não deve passar nenhum 'page_obj' ou 'filter'
    return render(request, 'sapp/dashboard.html') 




# VERSÃO NOVA - CORRETA
from django.shortcuts import render, redirect # Garanta que redirect está importado
from django.contrib.auth import logout       # Garanta que logout está importado

def logout_view(request):
    if request.method == 'POST':
        logout(request)
    # Redireciona para a página de login usando o namespace do app
    return redirect('sapp:login')

# --- View de Consulta ---
# Em sapp/views.py

# Em sapp/views.py

@login_required
def consulta_view(request):
    context = {
        'search_type': 'all',
        'termo_buscado': '',
        'resultados': []
    }

    origem_historico = request.GET.get('from_history') == 'true'

    if request.method == 'POST' or origem_historico:
        
        if request.method == 'POST':
            termo = request.POST.get('termo_busca', '').strip()
            search_type = request.POST.get('search_type', 'all')
        else:
            termo = request.GET.get('termo_busca', '').strip()
            search_type = request.GET.get('search_type', 'all') 
        
        context.update({'search_type': search_type, 'termo_buscado': termo})

        if len(termo) < 3: # Simplifiquei a condição, pois o tratamento de separador vem a seguir
            if not origem_historico:
                messages.warning(request, "Digite pelo menos 3 caracteres para buscar.")
            return render(request, 'sapp/consulta.html', context)

        cadastros = ProdutoCadastro.objects.none()
        lotes = EstoqueLote.objects.none()
        lote_filtro_exato = None

        try:
            # --- MUDANÇA PRINCIPAL AQUI ---
            # Verifica se o termo parece ser um QR Code (contém '|' ou '-')
            if '|' in termo or '-' in termo:
                # Substitui qualquer um dos separadores por um único separador padrão ('|')
                termo_normalizado = termo.replace('-', '|')
                
                partes = [x.strip() for x in termo_normalizado.split('|') if x.strip()]
                
                if len(partes) >= 2:
                    codigo, lote = partes[0], partes[1]
                    cadastros = ProdutoCadastro.objects.filter(codigo__iexact=codigo)
                    lotes = EstoqueLote.objects.filter(codigo__iexact=codigo, lote__iexact=lote)
                    lote_filtro_exato = lote
                else: # Se não conseguiu separar em duas partes, faz uma busca normal
                    # Isso evita erro se o usuário digitar algo como "produto-"
                    search_type = 'all' # Força a busca normal
            
            # --- FIM DA MUDANÇA ---
            
            # A lógica 'else' para busca normal só é executada se não for um QR Code válido
            if not (cadastros.exists() or lotes.exists()):
                if search_type == 'cadastro':
                    cadastros = ProdutoCadastro.objects.filter(Q(codigo__icontains=termo) | Q(descricao__icontains=termo))
                    if cadastros.exists():
                        codigos = cadastros.values_list('codigo', flat=True)
                        lotes = EstoqueLote.objects.filter(codigo__in=codigos)
                elif search_type == 'lote':
                    lotes = EstoqueLote.objects.filter(Q(lote__icontains=termo) | Q(endereco__icontains=termo))
                    if lotes.exists():
                        codigos = lotes.values_list('codigo', flat=True)
                        cadastros = ProdutoCadastro.objects.filter(codigo__in=codigos)
                        lote_filtro_exato = termo
                else:  # all
                    cadastros = ProdutoCadastro.objects.filter(Q(codigo__icontains=termo) | Q(descricao__icontains=termo))
                    lotes = EstoqueLote.objects.filter(Q(lote__icontains=termo) | Q(codigo__icontains=termo) | Q(endereco__icontains=termo))
                    if lotes.exists() and not cadastros.exists():
                        codigos = lotes.values_list('codigo', flat=True)
                        cadastros = ProdutoCadastro.objects.filter(codigo__in=codigos)

        except ValueError:
            messages.error(request, "Formato do QR Code inválido.")

        # O resto da sua view continua exatamente o mesmo...
        if cadastros.exists() or lotes.exists():
            # ... (lógica para montar os resultados) ...
            config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)
            campos_visiveis_produto = config.campos_visiveis_produto.split(',') if config.campos_visiveis_produto else []
            campos_visiveis_lote = config.campos_visiveis_lote.split(',') if config.campos_visiveis_lote else []

            if not campos_visiveis_produto:
                campos_visiveis_produto = ['codigo', 'descricao', 'cultivar', 'tecnologia']
            if not campos_visiveis_lote:
                campos_visiveis_lote = ['lote', 'codigo', 'qnte', 'dtvalidade', 'endereco', 'saldoliberado']

            resultados = []
            for produto in cadastros:
                lotes_relacionados = [l for l in lotes if l.codigo == produto.codigo]
                if lote_filtro_exato:
                    lotes_destaque = [l for l in lotes_relacionados if lote_filtro_exato.lower() in l.lote.lower()]
                    lotes_relacionados = lotes_destaque if lotes_destaque else lotes_relacionados
                resultados.append({
                    'produto': produto,
                    'detalhes_produto': [{'label': ProdutoCadastro._meta.get_field(f).verbose_name, 'valor': getattr(produto, f, None) or '--'} for f in campos_visiveis_produto if hasattr(produto, f)],
                    'lotes': [{'obj': lote, 'detalhes': [{'label': EstoqueLote._meta.get_field(c).verbose_name, 'valor': getattr(lote, c, None) or '--'} for c in campos_visiveis_lote if hasattr(lote, c)], 'destaque': (lote_filtro_exato and lote.lote.lower() == lote_filtro_exato.lower())} for lote in lotes_relacionados]
                })
            lotes_sem_produto = [l for l in lotes if not cadastros.filter(codigo=l.codigo).exists()]
            for lote in lotes_sem_produto:
                resultados.append({
                    'produto': None, 'detalhes_produto': [],
                    'lotes': [{'obj': lote, 'detalhes': [{'label': EstoqueLote._meta.get_field(c).verbose_name, 'valor': getattr(lote, c, None) or '--'} for c in campos_visiveis_lote if hasattr(lote, c)], 'destaque': (lote_filtro_exato and lote.lote.lower() == lote_filtro_exato.lower())}]
                })
            
            context['resultados'] = resultados
            
            if not origem_historico:
                HistoricoConsulta.objects.create(
                    termo_buscado=termo,
                    usuario=request.user,
                    resultados_encontrados=len(resultados)
                )

            messages.success(request, f"Encontrados {len(resultados)} resultado(s).")
        else:
            messages.error(request, f"Nenhum resultado encontrado para '{termo}'.")

    return render(request, 'sapp/consulta.html', context)


# --- View de Histórico ---
@login_required
def historico_view(request):
    return render(request, 'sapp/historico.html', {'historico': HistoricoConsulta.objects.all()})

# --- View de Configuração (com Formulário de exibição) ---
@login_required
def configuracao_view(request):
    config, _ = ConfiguracaoExibicao.objects.get_or_create(pk=1)

    if request.method == 'POST':
        # Processa o formulário de configuração de exibição
        form = ConfiguracaoExibicaoForm(request.POST)
        if form.is_valid():
            config.campos_visiveis_produto = ",".join(form.cleaned_data.get('campos_visiveis_produto', []))
            config.campos_visiveis_lote = ",".join(form.cleaned_data.get('campos_visiveis_lote', []))
            config.save()
            messages.success(request, "Configurações de exibição salvas com sucesso!")
        else:
            messages.error(request, "Erro ao salvar as configurações.")
        return redirect('sapp:configuracao') # Sempre redireciona para a mesma página

    # Prepara o formulário para ser exibido (GET request)
    form_config = ConfiguracaoExibicaoForm(initial={
        'campos_visiveis_produto': config.campos_visiveis_produto.split(',') if config.campos_visiveis_produto else [],
        'campos_visiveis_lote': config.campos_visiveis_lote.split(',') if config.campos_visiveis_lote else [],
    })

    context = {
        'form_config': form_config,
    }
    return render(request, 'sapp/configuracao.html', context)

# --- NOVA VIEW: Importação de Dados via Clipboard (em Lotes) ---
# Em sapp/views.py

@login_required
def importar_clipboard_em_lotes_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

    try:
        tipo_modelo = request.POST.get('tipo_modelo')
        dados_lote = request.POST.get('dados_lote')
        is_first_chunk = request.POST.get('is_first_chunk') == 'true'
        cabecalho = request.POST.get('cabecalho')

        if not tipo_modelo or not dados_lote or not cabecalho:
            return JsonResponse({'status': 'erro', 'mensagem': 'Dados incompletos.'}, status=400)

        colunas_normalizadas_clipboard = normalizar_colunas(cabecalho.split('\t'))
        
        # Prepara o DataFrame uma única vez
        dados_completos = cabecalho + '\n' + dados_lote
        dados_io = io.StringIO(dados_completos)
        df = pd.read_csv(dados_io, sep='\t', header=0, dtype=str)
        df.columns = normalizar_colunas(df.columns)

        if tipo_modelo == 'cadastro':
            model = ProdutoCadastro
            colunas_obrigatorias = ['codigo']
            
            # Validação
            colunas_faltando = [col for col in colunas_obrigatorias if col not in colunas_normalizadas_clipboard]
            if colunas_faltando:
                # ... (sua mensagem de erro)
                mensagem_erro = (f"Cabeçalho inválido para importação de '{tipo_modelo}'. "
                                 f"É necessário que a planilha contenha, no mínimo, a seguinte coluna: "
                                 f"{', '.join(colunas_obrigatorias).upper()}.")
                return JsonResponse({'status': 'erro', 'mensagem': mensagem_erro}, status=400)
            
            # Limpeza e conversão de tipos para CADASTRO (se houver alguma)
            # No momento não há, mas se precisar, coloque aqui.
            
        elif tipo_modelo == 'lotes':
            model = EstoqueLote
            colunas_obrigatorias = ['lote', 'codigo']
            
            # Validação
            colunas_faltando = [col for col in colunas_obrigatorias if col not in colunas_normalizadas_clipboard]
            if colunas_faltando:
                # ... (sua mensagem de erro)
                mensagem_erro = (f"Cabeçalho inválido para importação de '{tipo_modelo}'. "
                                 f"É necessário que a planilha contenha, no mínimo, as seguintes colunas: "
                                 f"{', '.join(colunas_obrigatorias).upper()}.")
                return JsonResponse({'status': 'erro', 'mensagem': mensagem_erro}, status=400)

            # --- LÓGICA DE CONVERSÃO DE TIPOS AGORA DENTRO DO BLOCO CORRETO ---
            numericas = ['qnte', 'pme', 'volume', 'quantsc', 'quantbg', 'saldoliberado', 'germinacao', 'vigor', 'qntebloq', 'volumebloq', 'quantidade_reserva', 'umidade']
            for col in numericas:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            for col in ['dtfabricacao', 'dtvalidade']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        else:
            return JsonResponse({'status': 'erro', 'mensagem': 'Tipo de modelo inválido.'}, status=400)
        
        # Se for o primeiro lote, limpa a tabela.
        if is_first_chunk:
            model.objects.all().delete()
            
        # --- Lógica comum de criação de objetos ---
        df.dropna(subset=colunas_obrigatorias, how='all', inplace=True)
        campos_modelo = {f.name for f in model._meta.get_fields()}
        objetos = []
        for _, row in df.iterrows():
            obj_data = {k: v for k, v in row.to_dict().items() if k in campos_modelo and pd.notna(v) and str(v).strip() != ''}
            if obj_data: # Só cria o objeto se houver dados válidos
                objetos.append(model(**obj_data))

        model.objects.bulk_create(objetos, ignore_conflicts=True, batch_size=500)
        
        return JsonResponse({'status': 'sucesso', 'registros_processados': len(objetos)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'erro', 'mensagem': f'Erro inesperado no processamento: {e}'}, status=500)





# sapp/views.py

# Adicione o import do seu novo arquivo de filtros no topo
# sapp/views.py

@login_required
def listar_produtos_view(request):
    """Exibe uma lista paginada e filtrável de Produtos Cadastrados."""
    produto_list = ProdutoCadastro.objects.all().order_by('codigo')
    produto_filter = ProdutoFilter(request.GET, queryset=produto_list)
    paginator = Paginator(produto_filter.qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- LÓGICA DE PREPARAÇÃO DE DADOS (A SOLUÇÃO) ---
    # Pega a lista de campos uma única vez
    campos = [field for field in ProdutoCadastro._meta.get_fields() if not field.is_relation and not field.name.startswith('_')]
    
    # Prepara os dados para o template
    linhas_de_dados = []
    for produto in page_obj: # Itera sobre os objetos da página atual
        linha = []
        for campo in campos:
            valor = getattr(produto, campo.name) # Pega o valor do atributo dinamicamente
            linha.append(valor)
        linhas_de_dados.append(linha)
    # --- FIM DA LÓGICA DE PREPARAÇÃO ---

    context = {
        'page_obj': page_obj,
        'filter': produto_filter,
        'titulo_pagina': 'Produtos Cadastrados',
        # Passa as listas pré-processadas para o template
        'cabecalhos': [campo.verbose_name.title() for campo in campos],
        'linhas_de_dados': linhas_de_dados,
    }
    return render(request, 'sapp/listar_dados.html', context)


@login_required
def listar_lotes_view(request):
    """Exibe uma lista paginada e filtrável de Lotes de Estoque."""
    lote_list = EstoqueLote.objects.all().order_by('codigo', 'lote')
    lote_filter = LoteFilter(request.GET, queryset=lote_list)
    paginator = Paginator(lote_filter.qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- LÓGICA DE PREPARAÇÃO DE DADOS ---
    campos = [field for field in EstoqueLote._meta.get_fields() if not field.is_relation and not field.name.startswith('_')]
    
    linhas_de_dados = []
    for lote in page_obj:
        linha = []
        for campo in campos:
            valor = getattr(lote, campo.name)
            linha.append(valor)
        linhas_de_dados.append(linha)
    # --- FIM DA LÓGICA DE PREPARAÇÃO ---

    context = {
        'page_obj': page_obj,
        'filter': lote_filter,
        'titulo_pagina': 'Lotes de Estoque',
        # Passa as listas pré-processadas
        'cabecalhos': [campo.verbose_name.title() for campo in campos],
        'linhas_de_dados': linhas_de_dados,
    }
    return render(request, 'sapp/listar_dados.html', context)