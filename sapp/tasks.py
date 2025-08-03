# sapp/tasks.py
import pandas as pd
import io # Para ler o texto como se fosse um arquivo
from celery import shared_task
from .models import ProdutoCadastro, EstoqueLote

def normalizar_colunas(nomes_colunas):
    """Sua função de normalização, copiada de views.py."""
    limpo = []
    for c in nomes_colunas:
        col = str(c).strip().lower()
        replacements = {' ': '', '_': '', '.': '', ',': '', 'ç': 'c', 'ã': 'a', 'á': 'a', 'ó': 'o'}
        for old, new in replacements.items():
            col = col.replace(old, new)
        limpo.append(col)
    return limpo

@shared_task
def processar_importacao(tipo_modelo, dados_clipboard, key_cols):
    """
    Tarefa Celery para processar os dados da área de transferência.
    tipo_modelo: 'cadastro' ou 'lotes'
    dados_clipboard: O texto copiado do Excel
    key_cols: As colunas chave para identificar o cabeçalho
    """
    try:
        model = ProdutoCadastro if tipo_modelo == 'cadastro' else EstoqueLote
        
        # O truque: usar io.StringIO para que o Pandas leia a string como um arquivo.
        # Dados do Excel colados são separados por tabulação (\t)
        dados_io = io.StringIO(dados_clipboard)
        
        # Usamos read_csv porque o formato colado é texto delimitado, não um arquivo .xlsx
        df = pd.read_csv(dados_io, sep='\t', header=0, dtype=str) # Assumimos que a primeira linha é o cabeçalho
        
        # Se precisar de uma lógica mais robusta para encontrar o cabeçalho, pode adaptar
        # a sua lógica original com df_preview aqui. Por simplicidade, assumimos header=0.
        
        df.columns = normalizar_colunas(df.columns)
        df.dropna(subset=key_cols, how='all', inplace=True)

        if model == EstoqueLote:
            # Sua lógica de conversão de tipos
            numericas = ['qnte', 'pme', 'volume', 'quantsc', 'quantbg', 'saldoliberado', 'germinacao', 'vigor', 'qntebloq', 'volumebloq', 'quantidadereserva']
            for col in numericas:
                if col in df.columns: df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
            for col in ['dtfabricacao', 'dtvalidade']:
                if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # Limpa a tabela antes de importar
        model.objects.all().delete()
        
        campos_modelo = {f.name for f in model._meta.get_fields()}
        objetos = [
            model(**{k: v for k, v in row.to_dict().items() if k in campos_modelo and pd.notna(v) and str(v).strip() != ''})
            for _, row in df.iterrows()
        ]
        
        model.objects.bulk_create(objetos, ignore_conflicts=True, batch_size=500)
        
        return {'status': 'sucesso', 'registros': len(objetos)}

    except Exception as e:
        # É importante capturar a exceção para retornar uma mensagem de erro
        return {'status': 'erro', 'mensagem': str(e)}