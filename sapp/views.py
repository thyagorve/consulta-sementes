# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
# Adicione no topo com os outros imports
import datetime
# Python imports
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import random

# App imports
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario
)
from .forms import (
    NovaEntradaForm, ConfiguracaoForm, CultivarForm, PeneiraForm, 
    CategoriaForm, TratamentoForm, NovoConferenteUserForm, MudarSenhaForm
)

# Pandas e outros imports
import pandas as pd
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
import json
from django.db import transaction
import tempfile
import os

# No início de views.py, com os outros imports de models
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario,
    # Adicione estes:
    Empenho, ItemEmpenho, EmpenhoStatus
)





# ================================================================
# FUNÇÕES AUXILIARES (ADICIONAR NO TOPO DO ARQUIVO views.py)
# ================================================================

def processar_inteiro(valor, default=0):
    """Converte valor para inteiro com segurança"""
    if valor is None or valor == '':
        return default
    
    try:
        if isinstance(valor, str):
            # Remove caracteres não numéricos, mantendo ponto decimal para conversão
            valor_limpo = ''
            for char in valor:
                if char.isdigit() or char in '.,':
                    valor_limpo += char
            valor = valor_limpo.replace(',', '.')
            
            if '.' in valor:
                # Se tiver decimal, arredonda para baixo
                return int(float(valor))
            else:
                return int(valor) if valor else default
        else:
            return int(valor)
    except (ValueError, TypeError, AttributeError):
        return default

def processar_decimal(valor, default=Decimal('0.00')):
    """Converte valor para Decimal com segurança"""
    if valor is None:
        return default
    
    try:
        if isinstance(valor, str):
            valor = valor.replace(',', '.')
            # Remove caracteres não numéricos, mantendo ponto decimal
            valor = ''.join(c for c in valor if c.isdigit() or c == '.' or c == '-')
            if not valor:
                return default
        
        # Converte para Decimal, limitando casas decimais
        return Decimal(str(valor)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return default
# ================================================================
# FUNÇÕES AUXILIARES
# ================================================================

def safe_get(row, column, default=''):
    """Extrai valor de forma segura"""
    if not column or column not in row:
        return default
    value = row[column]
    if pd.isna(value) or value is None:
        return default
    return str(value).strip()

def extrair_numero(row, column_key, default=0):
    """Extrai número de forma segura"""
    if not column_key:
        return default
    
    value = row.get(column_key)
    if value is None or pd.isna(value):
        return default
    
    try:
        if isinstance(value, str):
            value = ''.join(c for c in value if c.isdigit() or c in ',.')
            value = value.replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return default

def mapear_colunas_protheus_inteligente(colunas_encontradas):
    """Mapeamento INTELIGENTE com fallbacks seguros"""
    mapping = {}
    
    print(f"🔍 [MAPEAMENTO] Colunas encontradas: {colunas_encontradas}")
    
    # Mapeamento DIRETO baseado nas colunas do Protheus
    mapeamento_direto = {
        'Lote': 'lote',
        'Quantidade': 'quantidade',
        'Endereco': 'endereco',
        'Cultivar': 'cultivar',
        'Peneira': 'peneira',
        'Categoria': 'categoria',
        'Tp. Tratame.': 'tratamento',
        'Unidade': 'unidade',
        'Peso Med Ens': 'peso_med_ens',
        'Empenho': 'empresa',
        'Armazem': 'az',
        'Cultura': 'cultura'
    }
    
    for coluna_original, campo in mapeamento_direto.items():
        if coluna_original in colunas_encontradas:
            mapping[campo] = coluna_original
            print(f"   ✅ MAPEADO: {campo} -> {coluna_original}")
    
    # Verificar campos obrigatórios
    campos_obrigatorios = ['lote', 'quantidade', 'endereco']
    for campo in campos_obrigatorios:
        if campo not in mapping:
            print(f"   ❌ CAMPO OBRIGATÓRIO FALTANDO: {campo}")
    
    print(f"🎯 [MAPEAMENTO FINAL]: {mapping}")
    return mapping

def converter_unidade(quantidade_original, unidade, peso_med_ens):
    """Converte unidades usando peso_med_ens COM TRATAMENTO DE SEGURANÇA"""
    if not unidade or peso_med_ens <= 0:
        return quantidade_original, 1
    
    # Garantir que os valores são numéricos
    try:
        quantidade_original = float(quantidade_original)
        peso_med_ens = float(peso_med_ens)
    except (ValueError, TypeError):
        return quantidade_original, 1
    
    unidade = unidade.upper()
    
    try:
        if unidade in ['KG', 'QUILO', 'QUILOS']:
            quantidade_convertida = quantidade_original / peso_med_ens
            return round(quantidade_convertida), peso_med_ens
        elif unidade in ['TON', 'TONELADA']:
            quantidade_convertida = (quantidade_original * 1000) / peso_med_ens
            return round(quantidade_convertida), peso_med_ens / 1000
        elif unidade in ['MLH', 'MILHEIRO']:
            quantidade_convertida = quantidade_original * 1000
            return quantidade_convertida, 0.001
        elif unidade in ['SC', 'SACO', 'BAG', 'BAGS', 'UN', 'UNID', 'UNIDADE']:
            return quantidade_original, 1
        else:
            return quantidade_original, 1
    except Exception:
        return quantidade_original, 1

def identificar_embalagem_por_unidade(unidade):
    """Identifica embalagem baseado na unidade"""
    if not unidade:
        return 'BAG'
    
    unidade = str(unidade).upper().strip()
    
    mapeamento_direto = {
        'SC': 'SC', 'SACO': 'SC', 'SACOS': 'SC',
        'BAG': 'BAG', 'BAGS': 'BAG', 'BIG BAG': 'BAG',
        'KG': 'BAG', 'QUILO': 'BAG', 'TON': 'BAG',
        'MLH': 'BAG', 'UN': 'BAG', 'UNIDADE': 'BAG'
    }
    
    if unidade in mapeamento_direto:
        return mapeamento_direto[unidade]
    
    for padrao, embalagem in mapeamento_direto.items():
        if padrao in unidade:
            return embalagem
    
    return 'BAG'

# No importar_estoque, na parte do processamento, adicione:
def buscar_tratamento_categoria_avancado(tratamento_nome, categoria_nome):
    """Busca ou cria tratamento e categoria COM TRUNCAMENTO"""
    tratamento_obj = None
    categoria_obj = None
    
    # 🔥 TRUNCAR TRATAMENTO PARA 8 CARACTERES (igual ao banco)
    if tratamento_nome and str(tratamento_nome).strip():
        try:
            tratamento_nome_limpo = str(tratamento_nome).strip()
            
            # 🔥 SEMPRE TRUNCAR PARA 8 CARACTERES
            if len(tratamento_nome_limpo) > 8:
                tratamento_nome_limpo = tratamento_nome_limpo[:8]
                print(f"✂️ Tratamento truncado para 8 caracteres: '{tratamento_nome}' → '{tratamento_nome_limpo}'")
            
            # Buscar pelo nome TRUNCADO
            tratamento_obj = Tratamento.objects.filter(
                nome__iexact=tratamento_nome_limpo
            ).first()
            
            if not tratamento_obj:
                tratamento_obj = Tratamento.objects.create(
                    nome=tratamento_nome_limpo
                )
                print(f"✅ Criado novo tratamento: '{tratamento_nome_limpo}'")
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar/criar tratamento '{tratamento_nome}': {e}")
    
    if categoria_nome and str(categoria_nome).strip():
        try:
            categoria_nome_limpo = str(categoria_nome).strip()
            
            categoria_obj = Categoria.objects.filter(
                nome__iexact=categoria_nome_limpo
            ).first()
            
            if not categoria_obj:
                categoria_obj = Categoria.objects.create(
                    nome=categoria_nome_limpo
                )
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar/criar categoria '{categoria_nome}': {e}")
    
    return tratamento_obj, categoria_obj


@login_required
def debug_comparacao_endereco(request):
    """Debug específico para comparação de endereços"""
    print("🔍 [DEBUG COMPARAÇÃO ENDEREÇO]")
    print("=" * 80)
    
    # Testar lotes específicos do seu exemplo
    lotes_teste = ["PQH00208", "UCS0357-25", "UCS0163-25"]
    
    for lote_teste in lotes_teste:
        print(f"\n📦 TESTANDO LOTE: {lote_teste}")
        
        # Buscar no banco
        itens = Estoque.objects.filter(lote=lote_teste).select_related('peneira', 'cultivar', 'tratamento')
        
        print(f"   Encontrados {itens.count()} itens no banco:")
        
        for i, item in enumerate(itens):
            print(f"   --- Item {i+1} ---")
            print(f"      ID: {item.id}")
            print(f"      Endereço BD: '{item.endereco}'")
            print(f"      Endereço BD (Upper): '{item.endereco.upper().strip() if item.endereco else ''}'")
            print(f"      Peneira: '{item.peneira.nome if item.peneira else 'None'}'")
            print(f"      Cultivar: '{item.cultivar.nome if item.cultivar else 'None'}'")
            print(f"      Tratamento: '{item.tratamento.nome if item.tratamento else 'None'}'")
            print(f"      Saldo: {item.saldo}")
            print(f"      Peso Unitário: {item.peso_unitario}")
    
    print("\n" + "=" * 80)
    print("🎯 TESTE DE COMPARAÇÃO MANUAL:")
    
    # Teste manual de comparação
    lote_manual = "PQH00208"
    endereco_arquivo = "R05 LN10 P06"
    
    print(f"Lote: {lote_manual}")
    print(f"Endereço do arquivo: '{endereco_arquivo}'")
    
    item_bd = Estoque.objects.filter(lote=lote_manual).first()
    if item_bd:
        endereco_bd = item_bd.endereco.upper().strip() if item_bd.endereco else ''
        endereco_arq = endereco_arquivo.upper().strip()
        
        print(f"Endereço BD: '{endereco_bd}'")
        print(f"Endereço Arquivo (Upper): '{endereco_arq}'")
        print(f"São iguais? {endereco_bd == endereco_arq}")
        print(f"Tamanho BD: {len(endereco_bd)}, Tamanho Arquivo: {len(endereco_arq)}")
    else:
        print("Lote não encontrado no banco!")
    
    return JsonResponse({'success': True, 'message': 'Check console para debug'})


@login_required
def debug_importacao(request):
    """Debug completo do processo de importação"""
    print("🔍 [DEBUG IMPORTAÇÃO COMPLETA]")
    print("=" * 80)
    
    # Verificar tratamentos no banco
    tratamentos = Tratamento.objects.all().values('id', 'nome')
    print("TRATAMENTOS NO BANCO:")
    for t in tratamentos:
        print(f"  {t['id']}: '{t['nome']}' (tamanho: {len(t['nome'])})")
    
    # Verificar cultivares
    cultivares = Cultivar.objects.all().values('id', 'nome')[:10]
    print(f"\nPRIMEIROS 10 CULTIVARES:")
    for c in cultivares:
        print(f"  {c['id']}: '{c['nome']}'")
    
    # Verificar lotes específicos
    lotes_teste = ["PQH00208", "UCS0357-25", "UCS0163-25"]
    
    for lote in lotes_teste:
        print(f"\n--- LOTE: {lote} ---")
        itens = Estoque.objects.filter(lote=lote).select_related('peneira', 'cultivar', 'tratamento')
        
        for item in itens:
            print(f"  ID: {item.id}")
            print(f"  Endereço: '{item.endereco}'")
            print(f"  Peneira: '{item.peneira.nome}'")
            print(f"  Cultivar: '{item.cultivar.nome}'")
            print(f"  Tratamento: '{item.tratamento.nome if item.tratamento else 'None'}'")
            print(f"  Saldo: {item.saldo}")
            print(f"  Peso Unit: {item.peso_unitario}")
    
    return JsonResponse({'success': True, 'message': 'Debug completo no console'})



def comparar_com_estoque_atual_com_produto(dados_importados):
    """
    COMPARAÇÃO ROBUSTA - Encontra registros existentes mesmo com mudanças
    """
    print("🔍 [COMPARAÇÃO ROBUSTA] Iniciando...")
    
    comparacao = {
        'novos_lotes': [],
        'lotes_alterados': [],
        'lotes_iguais': [],
        'resumo': {'novos': 0, 'atualizados': 0, 'iguais': 0}
    }
    
    # Buscar TODOS os registros do banco (não apenas por lote)
    estoque_atual = Estoque.objects.all().select_related('cultivar', 'peneira', 'categoria', 'tratamento')
    
    print(f"📊 Total de registros no banco: {estoque_atual.count()}")
    print(f"📊 Itens para importar: {len(dados_importados)}")
    
    # Criar índice completo do banco
    banco_index = {}
    for item in estoque_atual:
        # 🔥 MÚLTIPLAS CHAVES para busca flexível
        chaves = [
            # Chave principal: Lote + Produto (mais confiável)
            f"LOTE_PRODUTO:{item.lote}|{item.produto or ''}",
            # Chave alternativa: apenas Lote
            f"LOTE:{item.lote}",
            # Chave com endereço antigo (para detectar mudanças)
            f"LOTE_ENDERECO:{item.lote}|{item.endereco or ''}",
        ]
        
        for chave in chaves:
            if chave not in banco_index:
                banco_index[chave] = []
            banco_index[chave].append(item)
    
    # Processar cada item importado
    for i, item_importado in enumerate(dados_importados):
        lote = item_importado.get('lote', '').strip()
        produto_importado = item_importado.get('produto', '').strip()
        endereco_importado = item_importado.get('endereco', '').strip().upper()
        az_importado = normalizar_az(item_importado.get('az', ''))
        quantidade_importada = float(item_importado.get('quantidade', 0))
        
        print(f"\n--- Item {i+1}: {lote} ---")
        print(f"   🏷️  Produto: '{produto_importado}'")
        print(f"   📍 Endereço (novo): '{endereco_importado}'")
        print(f"   🏭 AZ (novo): '{az_importado}'")
        print(f"   🔢 Quantidade: {quantidade_importada}")
        
        # 🔥 BUSCA INTELIGENTE: Tentar encontrar o registro correto
        item_estoque = None
        motivo_busca = ""
        
        # 1. Buscar por LOTE + PRODUTO (mais preciso)
        chave_lote_produto = f"LOTE_PRODUTO:{lote}|{produto_importado}"
        if chave_lote_produto in banco_index:
            item_estoque = banco_index[chave_lote_produto][0]
            motivo_busca = "Lote + Produto"
        
        # 2. Se não encontrou, buscar apenas por LOTE
        if not item_estoque:
            chave_lote = f"LOTE:{lote}"
            if chave_lote in banco_index:
                # Se houver múltiplos com mesmo lote, pegar o mais recente
                itens_mesmo_lote = banco_index[chave_lote]
                item_estoque = itens_mesmo_lote[0]  # Pega o primeiro (ou ordenar por ID)
                motivo_busca = f"Apenas Lote ({len(itens_mesmo_lote)} encontrados)"
        
        if item_estoque:
            print(f"   ✅ ENCONTRADO no banco por: {motivo_busca}")
            print(f"   📊 Dados atuais no banco:")
            print(f"      Lote: '{item_estoque.lote}'")
            print(f"      Produto: '{item_estoque.produto}'")
            print(f"      Endereço: '{item_estoque.endereco}'")
            print(f"      AZ: '{item_estoque.az}'")
            print(f"      Quantidade: {item_estoque.saldo}")
            
            # 🔥 DETECTAR MUDANÇAS
            diferencas = []
            mudou_endereco = False
            mudou_az = False
            
            # 1. Verificar mudança de ENDEREÇO
            endereco_bd = (item_estoque.endereco or '').strip().upper()
            if endereco_bd != endereco_importado:
                diferencas.append(f"endereco: '{endereco_bd}' → '{endereco_importado}'")
                mudou_endereco = True
                print(f"   📍 MUDANÇA DE ENDEREÇO DETECTADA!")
            
            # 2. Verificar mudança de AZ
            az_bd = normalizar_az(item_estoque.az)
            if az_bd != az_importado:
                diferencas.append(f"az: '{item_estoque.az}' → '{az_importado}'")
                mudou_az = True
                print(f"   🏭 MUDANÇA DE AZ DETECTADA!")
            
            # 3. Verificar mudança de QUANTIDADE
            quantidade_bd = float(item_estoque.saldo or 0)
            if abs(quantidade_bd - quantidade_importada) > 0.001:
                diferencas.append(f"quantidade: {quantidade_bd} → {quantidade_importada}")
                print(f"   🔢 MUDANÇA DE QUANTIDADE DETECTADA!")
            
            # 4. Verificar outros campos
            campos_comparacao = [
                ('peneira', 'peneira', item_estoque.peneira.nome if item_estoque.peneira else ''),
                ('cultivar', 'cultivar', item_estoque.cultivar.nome if item_estoque.cultivar else ''),
                ('tratamento', 'tratamento', item_estoque.tratamento.nome if item_estoque.tratamento else ''),
                ('peso_unitario', 'peso_unitario', float(item_estoque.peso_unitario or 0)),
                ('embalagem', 'embalagem', item_estoque.embalagem or ''),
            ]
            
            for campo_nome, campo_importado, valor_bd in campos_comparacao:
                valor_importado = item_importado.get(campo_importado, '')
                
                if campo_nome in ['peso_unitario']:
                    valor_importado = float(valor_importado or 0)
                    if abs(float(valor_bd or 0) - valor_importado) > 0.001:
                        diferencas.append(f"{campo_nome}: {valor_bd} → {valor_importado}")
                else:
                    valor_bd_str = str(valor_bd or '').strip()
                    valor_importado_str = str(valor_importado or '').strip()
                    if valor_bd_str != valor_importado_str:
                        if valor_importado_str not in ['', 'None', 'nan']:
                            diferencas.append(f"{campo_nome}: '{valor_bd_str}' → '{valor_importado_str}'")
            
            # 🔥 DECISÃO: Atualizar ou considerar novo?
            if diferencas:
                print(f"   🔄 {len(diferencas)} MUDANÇAS DETECTADAS - Marcando para ATUALIZAR")
                
                # Se mudou endereço ou AZ, é uma TRANSFERÊNCIA, não um novo lote
                if mudou_endereco or mudou_az:
                    print(f"   🚛 TRANSFERÊNCIA DETECTADA: Endereço/AZ modificado")
                
                comparacao['lotes_alterados'].append({
                    'lote': lote,
                    'endereco': endereco_importado,
                    'az': az_importado,
                    'endereco_original': item_estoque.endereco,
                    'az_original': item_estoque.az,
                    'divergencias': diferencas,
                    'dados_novos': item_importado,
                    'dados_atuais': {
                        'id': item_estoque.id,
                        'saldo': item_estoque.saldo,
                        'endereco': item_estoque.endereco,
                        'az': item_estoque.az,
                        'peneira_id': item_estoque.peneira.id,
                        'cultivar_id': item_estoque.cultivar.id,
                        'tratamento_id': item_estoque.tratamento.id if item_estoque.tratamento else None,
                        'peso_unitario': item_estoque.peso_unitario,
                        'embalagem': item_estoque.embalagem
                    }
                })
                comparacao['resumo']['atualizados'] += 1
            else:
                print(f"   ✅ SEM MUDANÇAS - Idêntico")
                comparacao['lotes_iguais'].append({
                    'lote': lote,
                    'endereco': endereco_importado,
                    'az': az_importado,
                    'dados': item_importado
                })
                comparacao['resumo']['iguais'] += 1
                
        else:
            print(f"   🆕 NÃO ENCONTRADO - Novo lote")
            comparacao['novos_lotes'].append({
                'lote': lote,
                'endereco': endereco_importado,
                'az': az_importado,
                'dados': item_importado
            })
            comparacao['resumo']['novos'] += 1
    
    print(f"\n📊 RESUMO FINAL:")
    print(f"   🆕 Novos: {comparacao['resumo']['novos']}")
    print(f"   🔄 Para atualizar: {comparacao['resumo']['atualizados']}")
    print(f"   ✅ Idênticos: {comparacao['resumo']['iguais']}")
    
    return comparacao

def normalizar_az(az_value):
    """Normaliza o valor do AZ removendo .0 e espaços"""
    if not az_value:
        return ''
    
    az_str = str(az_value).strip()
    
    # Remover .0 do final
    if az_str.endswith('.0'):
        az_str = az_str[:-2]
    elif '.' in az_str:
        # Verificar se a parte decimal é só zeros
        partes = az_str.split('.')
        if len(partes) == 2 and partes[1].replace('0', '') == '':
            az_str = partes[0]
    
    return az_str.upper()




@login_required
def debug_tratamentos(request):
    """Debug: mostra todos os tratamentos existentes no banco"""
    tratamentos = Tratamento.objects.all().values('id', 'nome')
    estoque_com_tratamento = Estoque.objects.filter(tratamento__isnull=False).select_related('tratamento')
    
    print("🔍 [DEBUG TRATAMENTOS]")
    print("Tratamentos cadastrados:")
    for t in tratamentos:
        print(f"  {t['id']}: '{t['nome']}'")
    
    print("\nEstoque com tratamento:")
    for e in estoque_com_tratamento:
        print(f"  Lote: {e.lote}, Tratamento: '{e.tratamento.nome if e.tratamento else 'None'}'")
    
    return JsonResponse({'success': True, 'message': 'Check console for debug info'})





# ================================================================
# FUNÇÕES DE COMPARAÇÃO
# ================================================================




def comparar_com_estoque_atual_precisa(novos_dados):
    """
    COMPARAÇÃO SUPER PRECISA com debug detalhado
    """
    comparacao = {
        'novos_lotes': [],
        'lotes_alterados': [],
        'lotes_iguais': [],
        'resumo': {'novos': 0, 'atualizados': 0, 'iguais': 0}
    }
    
    print("🎯 [COMPARAÇÃO SUPER PRECISA] Iniciando...")
    
    for i, novo_item in enumerate(novos_dados):
        lote = novo_item.get('lote', '')
        peneira_nova = novo_item.get('peneira', '')
        cultivar_novo = novo_item.get('cultivar', '')
        tratamento_novo = novo_item.get('tratamento', '')
        
        print(f"\n🔍 [ITEM {i+1}] {lote}")
        print(f"   ARQUIVO -> Peneira: '{peneira_nova}', Cultivar: '{cultivar_novo}', Tratamento: '{tratamento_novo}'")
        
        # Buscar TODOS os registros com este lote no banco para debug
        itens_bd = Estoque.objects.filter(lote=lote).select_related('peneira', 'cultivar', 'tratamento')
        
        if itens_bd:
            print(f"   📊 ENCONTRADO(S) {itens_bd.count()} registro(s) no banco:")
            for j, item_bd in enumerate(itens_bd):
                print(f"      BD {j+1} -> Peneira: '{item_bd.peneira.nome if item_bd.peneira else 'None'}', "
                      f"Cultivar: '{item_bd.cultivar.nome if item_bd.cultivar else 'None'}', "
                      f"Tratamento: '{item_bd.tratamento.nome if item_bd.tratamento else 'None'}'")
        
        # Agora buscar pelo match exato
        encontrado = False
        for item_bd in itens_bd:
            peneira_bd = item_bd.peneira.nome if item_bd.peneira else ''
            cultivar_bd = item_bd.cultivar.nome if item_bd.cultivar else ''
            tratamento_bd = item_bd.tratamento.nome if item_bd.tratamento else ''
            
            # 🔥 COMPARAÇÃO PRECISA
            peneira_match = (peneira_bd == peneira_nova)
            cultivar_match = (cultivar_bd == cultivar_novo)
            
            # Comparação FLEXÍVEL de tratamento
            tratamento_match = comparar_tratamentos_flexivel(tratamento_bd, tratamento_novo)
            
            if peneira_match and cultivar_match and tratamento_match:
                print(f"   ✅ MATCH EXATO ENCONTRADO!")
                encontrado = True
                
                # Comparar endereço e quantidade
                endereco_bd = item_bd.endereco
                endereco_novo = novo_item.get('endereco', '')
                quantidade_bd = item_bd.saldo
                quantidade_novo = novo_item.get('quantidade', 0)
                
                print(f"   📍 Endereço: BD '{endereco_bd}' vs Arquivo '{endereco_novo}'")
                print(f"   🔢 Quantidade: BD {quantidade_bd} vs Arquivo {quantidade_novo}")
                
                if endereco_bd == endereco_novo and quantidade_bd == quantidade_novo:
                    print("   ✅ TUDO IGUAL - Marcando como IGUAL")
                    comparacao['lotes_iguais'].append({
                        'lote': lote,
                        'endereco': endereco_novo,
                        'dados': novo_item,
                        'dados_atuais': {
                            'id': item_bd.id,
                            'saldo': quantidade_bd,
                            'endereco': endereco_bd
                        }
                    })
                    comparacao['resumo']['iguais'] += 1
                else:
                    print("   🔄 DIFERENÇAS - Marcando para ATUALIZAR")
                    divergencias = []
                    if endereco_bd != endereco_novo:
                        divergencias.append(f'Endereço: {endereco_bd} → {endereco_novo}')
                    if quantidade_bd != quantidade_novo:
                        divergencias.append(f'Quantidade: {quantidade_bd} → {quantidade_novo}')
                    
                    comparacao['lotes_alterados'].append({
                        'lote': lote,
                        'endereco': endereco_novo,
                        'endereco_original': endereco_bd,
                        'divergencias': divergencias,
                        'dados_novos': novo_item,
                        'dados_atuais': {
                            'id': item_bd.id,
                            'saldo': quantidade_bd,
                            'endereco': endereco_bd,
                            'peneira_id': item_bd.peneira.id,
                            'cultivar_id': item_bd.cultivar.id,
                            'tratamento_id': item_bd.tratamento.id if item_bd.tratamento else None
                        }
                    })
                    comparacao['resumo']['atualizados'] += 1
                break
        
        if not encontrado:
            print("   🆕 NENHUM MATCH ENCONTRADO - Marcando como NOVO")
            comparacao['novos_lotes'].append({
                'lote': lote,
                'endereco': novo_item.get('endereco', ''),
                'dados': novo_item
            })
            comparacao['resumo']['novos'] += 1
    
    print(f"\n📊 RESUMO FINAL:")
    print(f"   ✅ Iguais: {comparacao['resumo']['iguais']}")
    print(f"   🔄 Para atualizar: {comparacao['resumo']['atualizados']}")
    print(f"   🆕 Novos: {comparacao['resumo']['novos']}")
    
    return comparacao

def comparar_tratamentos_flexivel(tratamento_bd, tratamento_arquivo):
    """Comparação FLEXÍVEL de tratamentos"""
    if not tratamento_bd and not tratamento_arquivo:
        return True
    
    if not tratamento_bd or not tratamento_arquivo:
        # Se um é vazio e o outro é "SEM TRATAMENTO", considerar iguais
        if (not tratamento_bd and str(tratamento_arquivo).upper() in ['', 'SEM TRATAMENTO', 'NAN']) or \
           (not tratamento_arquivo and str(tratamento_bd).upper() in ['', 'SEM TRATAMENTO', 'NAN']):
            return True
        return False
    
    # Normalizar ambos
    bd_normalizado = str(tratamento_bd).strip().upper()
    arquivo_normalizado = str(tratamento_arquivo).strip().upper()
    
    # Remover 'NAN'
    if arquivo_normalizado == 'NAN':
        arquivo_normalizado = ''
    if bd_normalizado == 'NAN':
        bd_normalizado = ''
    
    # Mapear equivalentes
    equivalentes = {
        '': ['SEM TRATAMENTO', 'SEM TRAT', 'NONE', 'NULL'],
        'SEM TRATAMENTO': ['', 'SEM TRAT', 'NONE', 'NULL']
    }
    
    # Verificar igualdade direta
    if bd_normalizado == arquivo_normalizado:
        return True
    
    # Verificar equivalentes
    for base, sinonimos in equivalentes.items():
        if bd_normalizado == base and arquivo_normalizado in sinonimos:
            return True
        if arquivo_normalizado == base and bd_normalizado in sinonimos:
            return True
    
    return False


def normalizar_tratamento(tratamento):
    """Normaliza valores de tratamento para comparação"""
    if not tratamento or str(tratamento).strip() in ['', 'nan', 'NaN', 'None', 'null']:
        return 'SEM TRATAMENTO'
    
    tratamento_str = str(tratamento).strip()
    
    # Mapear sinônimos
    if tratamento_str.upper() in ['SEM TRATAMENTO', 'SEM TRAT', 'SEM TRAT.']:
        return 'SEM TRATAMENTO'
    
    return tratamento_str


@login_required
def limpar_lotes_duplicados(request):
    """Limpa lotes duplicados do banco"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Encontrar lotes duplicados
                from django.db.models import Count
                duplicados = Estoque.objects.values('lote', 'endereco').annotate(
                    total=Count('id')
                ).filter(total__gt=1)
                
                print(f"🔍 Encontrados {len(duplicados)} lotes duplicados")
                
                for dup in duplicados:
                    lote = dup['lote']
                    endereco = dup['endereco']
                    
                    # Manter apenas o mais recente
                    registros = Estoque.objects.filter(lote=lote, endereco=endereco).order_by('-id')
                    manter = registros.first()
                    excluir = registros[1:]
                    
                    for reg in excluir:
                        print(f"🗑️  Excluindo duplicado: {lote} -> {endereco} (ID: {reg.id})")
                        reg.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Lotes duplicados limpos: {len(duplicados)}'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao limpar duplicados: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# ================================================================
# VIEWS PRINCIPAIS
# ================================================================

@login_required
def dashboard(request):
    """Dashboard com métricas reais"""
    total_itens = Estoque.objects.count()
    itens_ativos = Estoque.objects.filter(saldo__gt=0).count()
    itens_esgotados = total_itens - itens_ativos
    
    total_bag = Estoque.objects.filter(embalagem='BAG', saldo__gt=0).aggregate(
        total=Sum('saldo'))['total'] or 0
    total_sc = Estoque.objects.filter(embalagem='SC', saldo__gt=0).aggregate(
        total=Sum('saldo'))['total'] or 0
    total_sc_convertido = (total_bag * 25) + total_sc
    
    peso_total = Estoque.objects.filter(saldo__gt=0).aggregate(
        total=Sum('peso_total'))['total'] or Decimal('0.00')
    
    hoje = timezone.now()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    movimentacao_mes = HistoricoMovimentacao.objects.filter(
        data_hora__gte=inicio_mes
    ).count()
    
    top_cultivares = list(Estoque.objects.filter(saldo__gt=0).values(
        'cultivar__nome'
    ).annotate(
        total_saldo=Sum('saldo')
    ).order_by('-total_saldo')[:10])
    
    categorias_distribuicao = list(Estoque.objects.filter(saldo__gt=0).values(
        'peneira__nome'  # Alterado de categoria__nome para peneira__nome
    ).annotate(
        total=Sum('saldo')
    ).order_by('-total')[:10])
    
    capacidade_armazem = list(Estoque.objects.filter(
        saldo__gt=0,
        az__isnull=False  # Filtra apenas itens com AZ definido
    ).exclude(
        az=''  # Remove valores vazios
    ).values(
        'az'  # ✅ CORRETO: agora usa o campo AZ
    ).annotate(
        total_sc=Sum('saldo'),
        total_lotes=Count('id'),
        peso_total=Sum('peso_total')
    ).order_by('az'))  # Ordena por AZ
    
    movimentacao_recente = list(HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')[:10])
    
    context = {
        'total_sc_convertido': total_sc_convertido,
        'total_bag': total_bag,
        'total_sc': total_sc,
        'peso_total': peso_total,
        'itens_ativos': itens_ativos,
        'itens_esgotados': itens_esgotados,
        'movimentacao_mes': movimentacao_mes,
        'top_cultivares': top_cultivares,
        'categorias_distribuicao': categorias_distribuicao,
        'capacidade_armazem': capacidade_armazem,
        'movimentacao_recente': movimentacao_recente,
    }
    
    return render(request, 'sapp/dashboard.html', context)

# NO VIEWS.PY - Na função gestao_estoque, faça estas correções:

# CORREÇÃO NO VIEWS.PY - Na função gestao_estoque:

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum
# Importe seu modelo
from .models import Estoque 

@login_required
def gestao_estoque(request):
    """
    View completa para Gestão de Estoque com Filtros Avançados no Backend.
    """
    
    # 1. QuerySet Base (Apenas itens com saldo positivo)
    qs = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    ).order_by('endereco', 'lote')

    # --- 2. APLICAÇÃO DOS FILTROS VINDOS DA URL ---
    
    # Busca Global (Input de texto)
    busca = request.GET.get('busca', '').strip()
    if busca:
        qs = qs.filter(
            Q(lote__icontains=busca) |
            Q(cultivar__nome__icontains=busca) |
            Q(endereco__icontains=busca) |
            Q(peneira__nome__icontains=busca) |
            Q(cliente__icontains=busca) |
            Q(empresa__icontains=busca)
        )

    # Filtros de Coluna (Múltipla Escolha)
    # As chaves DEVEM ser idênticas ao 'data-column' do HTML
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'status': 'status__in',
        'conferente': 'conferente__username__in'
    }

    # Aplica os filtros de lista (ex: &cultivar=Soja&cultivar=Milho)
    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        values = [v for v in values if v.strip()] # Remove vazios
        if values:
            qs = qs.filter(**{lookup: values})

    # Filtros Numéricos (Min e Max)
    numeric_fields = ['saldo', 'peso_unitario', 'peso_total']
    for field in numeric_fields:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        
        if min_val:
            qs = qs.filter(**{f'{field}__gte': min_val})
        if max_val:
            qs = qs.filter(**{f'{field}__lte': max_val})

    # --- 3. CÁLCULO DE TOTAIS (Baseado no resultado filtrado) ---
    total_itens = qs.count()
    
    # Agregações
    resumo = qs.aggregate(
        total_saldo=Sum('saldo'),
        total_peso=Sum('peso_total')
    )
    
    # Lógica de BAG vs SC
    bags_count = qs.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
    sc_fisico = qs.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
    
    # Conversão: 1 BAG = 25 SC
    total_sc_equivalente = (bags_count * 25) + sc_fisico
    
    clientes_unicos = qs.exclude(cliente__isnull=True).exclude(cliente='').values('cliente').distinct().count()

    # --- 4. PREPARAÇÃO DAS OPÇÕES PARA O FILTRO (Backend -> Frontend) ---
    # Pegamos uma base SEM filtros de coluna para mostrar todas as opções disponíveis
    # Isso resolve o problema de "Sem opções disponíveis"
    base_options_qs = Estoque.objects.filter(saldo__gt=0)
    
    def get_options_list(field_lookup):
        """Retorna lista de strings únicas para o filtro"""
        # Extrai valores distintos, remove nulos/vazios e ordena
        vals = base_options_qs.values_list(field_lookup, flat=True).distinct().order_by(field_lookup)
        # Converte TUDO para string para evitar erro no JSON
        return [str(v) for v in vals if v is not None and str(v).strip() != '']

    filter_options = {
        'az': get_options_list('az'),
        'lote': get_options_list('lote'),
        'cultivar': get_options_list('cultivar__nome'),
        'peneira': get_options_list('peneira__nome'),
        'categoria': get_options_list('categoria__nome'),
        'endereco': get_options_list('endereco'),
        'especie': get_options_list('especie'),
        'tratamento': get_options_list('tratamento__nome'),
        'embalagem': get_options_list('embalagem'),
        'cliente': get_options_list('cliente'),
        'empresa': get_options_list('empresa'),
        'status': get_options_list('status'),
        'conferente': get_options_list('conferente__username') # ou conferente__first_name
    }

    # --- 5. PAGINAÇÃO ---
    page_size = request.GET.get('page_size', 25)
    try:
        page_size = int(page_size)
    except ValueError:
        page_size = 25

    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)

    try:
        estoque_page = paginator.page(page_number)
    except PageNotAnInteger:
        estoque_page = paginator.page(1)
    except EmptyPage:
        estoque_page = paginator.page(paginator.num_pages)

    # --- 6. URL PARAMS PARA PAGINAÇÃO ---
    # Preserva os filtros atuais nos links de próxima página
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    url_params = query_params.urlencode()

    context = {
        'estoque': estoque_page,
        'total_itens': total_itens,
        'total_sc': total_sc_equivalente,
        'total_bags': bags_count,
        'total_sc_fisico': sc_fisico,
        'clientes_unicos': clientes_unicos,
        # Dados essenciais para o filtro funcionar:
        'filter_options': filter_options, 
        'url_params': url_params,
        'page_sizes': [10, 25, 50, 100],
        'page_size': page_size,
        'busca': busca,
    }

    return render(request, 'sapp/gestao_estoque.html', context)


@login_required
def importar_estoque(request):
    """Importação de estoque COMPLETA - todos os campos igual à exportação"""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            excel_file = request.FILES['excel_file']
            
            print("=" * 80)
            print("🔍 [IMPORTAÇÃO COMPLETA] INICIANDO PROCESSAMENTO")
            print("=" * 80)
            
            # Ler o arquivo Excel
            try:
                df = pd.read_excel(excel_file, dtype=str)  # Ler tudo como string
                print("✅ Arquivo lido com dtype=str para todas as colunas")
            except Exception as e:
                print(f"⚠️ Erro ao ler com dtype=str: {e}")
                df = pd.read_excel(excel_file)
            
            print(f"📊 Arquivo lido - {len(df)} linhas, {len(df.columns)} colunas")
            print(f"🔍 Colunas encontradas: {list(df.columns)}")
            
            # Verificar colunas obrigatórias e criar mapping automático
            colunas_esperadas = [
                'Lote', 'Produto', 'Cultivar', 'Peneira', 'Categoria', 'Endereço',
                'Saldo', 'Peso Unitário (kg)', 'Peso Total (kg)', 'Tratamento',
                'Embalagem', 'Conferente', 'Data Entrada', 'AZ', 'Origem/Destino',
                'Empresa', 'Espécie', 'Lote Anterior', 'Observação'
            ]
            
            # Mapeamento baseado nos nomes das colunas do Excel exportado
            mapping = {}
            for coluna in colunas_esperadas:
                for coluna_arquivo in df.columns:
                    if coluna.lower() in coluna_arquivo.lower() or coluna_arquivo.lower() in coluna.lower():
                        mapping[coluna] = coluna_arquivo
                        print(f"   ✅ MAPEADO: '{coluna_arquivo}' → '{coluna}'")
                        break
                if coluna not in mapping:
                    print(f"   ⚠️ COLUNA NÃO ENCONTRADA: '{coluna}'")
            
            # Processar dados
            processed_data = []
            linhas_com_erro = 0
            
            for index, row in df.iterrows():
                try:
                    # Extrair dados com fallback para valores padrão
                    item_data = {
                        'lote': str(row.get(mapping.get('Lote', ''), '')).strip(),
                        'produto': str(row.get(mapping.get('Produto', ''), '')).strip(),
                        'cultivar': str(row.get(mapping.get('Cultivar', ''), '')).strip(),
                        'peneira': str(row.get(mapping.get('Peneira', ''), '')).strip(),
                        'categoria': str(row.get(mapping.get('Categoria', ''), '')).strip(),
                        'endereco': str(row.get(mapping.get('Endereço', ''), '')).strip().upper(),
                        'saldo': 0,
                        'peso_unitario': 0.0,
                        'peso_total': 0.0,
                        'tratamento': str(row.get(mapping.get('Tratamento', ''), '')).strip(),
                        'embalagem': str(row.get(mapping.get('Embalagem', ''), '')).strip(),
                        'conferente': str(row.get(mapping.get('Conferente', ''), '')).strip(),
                        'data_entrada': str(row.get(mapping.get('Data Entrada', ''), '')).strip(),
                        'az': str(row.get(mapping.get('AZ', ''), '')).strip(),
                        'origem_destino': str(row.get(mapping.get('Origem/Destino', ''), '')).strip(),
                        'empresa': str(row.get(mapping.get('Empresa', ''), '')).strip(),
                        'especie': str(row.get(mapping.get('Espécie', ''), 'SOJA')).strip(),
                       
                        'observacao': str(row.get(mapping.get('Observação', ''), '')).strip()
                    }
                    
                    # Processar valores numéricos
                    try:
                        saldo_raw = row.get(mapping.get('Saldo', ''))
                        if not pd.isna(saldo_raw) and saldo_raw not in [None, '']:
                            item_data['saldo'] = float(str(saldo_raw).replace(',', '.'))
                    except:
                        item_data['saldo'] = 0
                    
                    try:
                        peso_unit_raw = row.get(mapping.get('Peso Unitário (kg)', ''))
                        if not pd.isna(peso_unit_raw) and peso_unit_raw not in [None, '']:
                            item_data['peso_unitario'] = float(str(peso_unit_raw).replace(',', '.'))
                    except:
                        item_data['peso_unitario'] = 0.0
                    
                    try:
                        peso_total_raw = row.get(mapping.get('Peso Total (kg)', ''))
                        if not pd.isna(peso_total_raw) and peso_total_raw not in [None, '']:
                            item_data['peso_total'] = float(str(peso_total_raw).replace(',', '.'))
                    except:
                        item_data['peso_total'] = 0.0
                    
                    # Validar dados obrigatórios
                    if not item_data['lote'] or not item_data['endereco']:
                        print(f"⚠️ Linha {index + 2}: Lote ou endereço vazio - pulando")
                        linhas_com_erro += 1
                        continue
                    
                    if item_data['saldo'] <= 0:
                        print(f"⚠️ Linha {index + 2}: Saldo <= 0 - pulando")
                        linhas_com_erro += 1
                        continue
                    
                    # Normalizar embalagem
                    if item_data['embalagem']:
                        emb = item_data['embalagem'].upper()
                        if 'SACO' in emb or 'SC' in emb:
                            item_data['embalagem'] = 'SC'
                        elif 'BAG' in emb or 'BIG' in emb:
                            item_data['embalagem'] = 'BAG'
                    
                    # Tratamento de datas
                    if item_data['data_entrada']:
                        try:
                            # Tentar converter várias formatos de data
                            if isinstance(item_data['data_entrada'], str):
                                # Remove hora se existir
                                item_data['data_entrada'] = item_data['data_entrada'].split()[0]
                        except:
                            item_data['data_entrada'] = timezone.now().strftime('%d/%m/%Y')
                    else:
                        item_data['data_entrada'] = timezone.now().strftime('%d/%m/%Y')
                    
                    # Buscar/crear objetos relacionados
                    # Cultivar
                    if item_data['cultivar']:
                        cultivar_obj, _ = Cultivar.objects.get_or_create(
                            nome=item_data['cultivar'],
                            defaults={'nome': item_data['cultivar']}
                        )
                        item_data['cultivar_id'] = cultivar_obj.id
                    else:
                        cultivar_padrao, _ = Cultivar.objects.get_or_create(
                            nome='CULTIVAR NÃO ESPECIFICADO',
                            defaults={'nome': 'CULTIVAR NÃO ESPECIFICADO'}
                        )
                        item_data['cultivar_id'] = cultivar_padrao.id
                    
                    # Peneira
                    if item_data['peneira']:
                        peneira_obj, _ = Peneira.objects.get_or_create(
                            nome=item_data['peneira'],
                            defaults={'nome': item_data['peneira']}
                        )
                        item_data['peneira_id'] = peneira_obj.id
                    else:
                        peneira_padrao, _ = Peneira.objects.get_or_create(
                            nome='PENEIRA NÃO ESPECIFICADA',
                            defaults={'nome': 'PENEIRA NÃO ESPECIFICADA'}
                        )
                        item_data['peneira_id'] = peneira_padrao.id
                    
                    # Categoria
                    if item_data['categoria']:
                        categoria_obj, _ = Categoria.objects.get_or_create(
                            nome=item_data['categoria'],
                            defaults={'nome': item_data['categoria']}
                        )
                        item_data['categoria_id'] = categoria_obj.id
                    else:
                        categoria_padrao, _ = Categoria.objects.get_or_create(
                            nome='CATEGORIA NÃO ESPECIFICADA',
                            defaults={'nome': 'CATEGORIA NÃO ESPECIFICADA'}
                        )
                        item_data['categoria_id'] = categoria_padrao.id
                    
                    # Tratamento
                    if item_data['tratamento'] and item_data['tratamento'].lower() not in ['', 'nan', 'none', 'sem tratamento']:
                        # Truncar para 8 caracteres se necessário
                        tratamento_nome = item_data['tratamento'][:8] if len(item_data['tratamento']) > 8 else item_data['tratamento']
                        tratamento_obj, _ = Tratamento.objects.get_or_create(
                            nome=tratamento_nome,
                            defaults={'nome': tratamento_nome}
                        )
                        item_data['tratamento_id'] = tratamento_obj.id
                    else:
                        item_data['tratamento_id'] = None
                    
                    # Conferente (usuário)
                    if item_data['conferente']:
                        # Tentar encontrar usuário pelo nome
                        user = User.objects.filter(
                            Q(first_name__icontains=item_data['conferente']) |
                            Q(username__icontains=item_data['conferente'])
                        ).first()
                        if user:
                            item_data['conferente_id'] = user.id
                        else:
                            item_data['conferente_id'] = request.user.id
                    else:
                        item_data['conferente_id'] = request.user.id
                    
                    print(f"✅ Processado: {item_data['lote']} | {item_data['endereco']} | Saldo: {item_data['saldo']}")
                    processed_data.append(item_data)
                    
                except Exception as e:
                    print(f"❌ Erro na linha {index + 2}: {e}")
                    import traceback
                    traceback.print_exc()
                    linhas_com_erro += 1
                    continue
            
            print(f"📊 Total processado: {len(processed_data)} itens")
            print(f"⚠️ Linhas com erro: {linhas_com_erro}")
            
            if not processed_data:
                return JsonResponse({
                    'success': False,
                    'error': 'Nenhum dado válido encontrado no arquivo.'
                })
            
            # Usar comparação robusta
            comparacao = comparar_com_estoque_atual_com_produto(processed_data)
            
            return JsonResponse({
                'success': True,
                'processed_count': len(processed_data),
                'error_count': linhas_com_erro,
                'comparacao': comparacao,
                'message': f'✅ Importação concluída! {len(processed_data)} itens processados, {linhas_com_erro} erros'
            })
            
        except Exception as e:
            print(f"💥 Erro geral na importação: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'error': f'Erro ao processar arquivo: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# 🔥 FUNÇÃO AUXILIAR PARA LIMPAR PRODUTO
def limpar_codigo_produto(produto_raw):
    """Remove .0 e formata códigos de produto"""
    if pd.isna(produto_raw) or produto_raw is None:
        return ''
    
    produto_str = str(produto_raw).strip()
    
    # Casos comuns de .0 no final
    if produto_str.endswith('.0'):
        produto_str = produto_str[:-2]
    
    # Remover espaços extras
    produto_str = produto_str.strip()
    
    # Se ficou vazio ou é inválido
    if not produto_str or produto_str.lower() in ['nan', 'none', 'null']:
        return ''
    
    return produto_str

# No loop de processamento, use:


def comparar_com_estoque_atual_com_produto(dados_importados):
    """
    COMPARAÇÃO COMPLETA - Considera Lote + Produto + Endereço + AZ como chave única
    """
    print("🔍 [COMPARAÇÃO COMPLETA] Iniciando...")
    
    comparacao = {
        'novos_lotes': [],
        'lotes_alterados': [],
        'lotes_iguais': [],
        'resumo': {'novos': 0, 'atualizados': 0, 'iguais': 0}
    }
    
    # Coletar todos os lotes únicos do arquivo
    lotes_importados = list(set([item.get('lote', '') for item in dados_importados if item.get('lote')]))
    
    print(f"📊 Lotes únicos no arquivo: {len(lotes_importados)}")
    
    # Buscar TODOS os registros do banco que correspondem aos lotes importados
    estoque_atual = Estoque.objects.filter(
        lote__in=lotes_importados
    ).select_related('cultivar', 'peneira', 'categoria', 'tratamento')
    
    print(f"📊 Registros encontrados no banco: {estoque_atual.count()}")
    
    # Criar dicionário para busca rápida por CHAVE COMPLETA
    estoque_dict = {}
    for item in estoque_atual:
        # 🔥 CHAVE COMPLETA: lote + produto + endereço + az
        chave_completa = f"{item.lote}|{item.produto or ''}|{item.endereco or ''}|{item.az or ''}"
        
        if chave_completa not in estoque_dict:
            estoque_dict[chave_completa] = []
        estoque_dict[chave_completa].append(item)
        
        # Também criar chave apenas por lote para fallback
        chave_lote = item.lote
        if chave_lote not in estoque_dict:
            estoque_dict[chave_lote] = []
        estoque_dict[chave_lote].append(item)
    
    # Processar cada item importado
    for i, item_importado in enumerate(dados_importados):
        lote = item_importado.get('lote', '')
        produto_importado = item_importado.get('produto', '')
        endereco_importado = item_importado.get('endereco', '').strip().upper()
        az_importado = item_importado.get('az', '').strip().upper()
        quantidade_importada = float(item_importado.get('quantidade', 0))
        
        print(f"\n--- Item {i+1}: {lote} ---")
        print(f"   📍 Endereço: '{endereco_importado}'")
        print(f"   🏭 Armazém: '{az_importado}'")
        print(f"   🏷️  Produto: '{produto_importado}'")
        print(f"   🔢 Quantidade: {quantidade_importada}")
        
        # 🔥 BUSCAR POR CHAVE COMPLETA primeiro
        chave_completa = f"{lote}|{produto_importado}|{endereco_importado}|{az_importado}"
        itens_correspondentes = estoque_dict.get(chave_completa, [])
        
        if itens_correspondentes:
            item_estoque = itens_correspondentes[0]  # Pega o primeiro
            
            print(f"   ✅ ENCONTRADO por chave completa")
            print(f"   📍 Endereço BD: '{item_estoque.endereco}'")
            print(f"   🏭 Armazém BD: '{item_estoque.az}'")
            print(f"   🔢 Quantidade BD: {item_estoque.saldo}")
            
            # 🔥 COMPARAÇÃO DETALHADA
            diferencas = []
            
            # 1. COMPARAR QUANTIDADE (sempre comparar)
            quantidade_bd = float(item_estoque.saldo or 0)
            if abs(quantidade_bd - quantidade_importada) > 0.001:
                diferencas.append(f"quantidade: {quantidade_bd} → {quantidade_importada}")
                print(f"   🔢 DIFERENÇA DE QUANTIDADE!")
            
            # 2. COMPARAR OUTROS CAMPOS (apenas se houver diferença)
            campos_comparacao = [
                ('peneira', 'peneira', item_estoque.peneira.nome if item_estoque.peneira else ''),
                ('cultivar', 'cultivar', item_estoque.cultivar.nome if item_estoque.cultivar else ''),
                ('tratamento', 'tratamento', item_estoque.tratamento.nome if item_estoque.tratamento else ''),
                ('peso_unitario', 'peso_unitario', float(item_estoque.peso_unitario or 0)),
                ('embalagem', 'embalagem', item_estoque.embalagem or ''),
            ]
            
            for campo_nome, campo_importado, valor_bd in campos_comparacao:
                valor_importado = item_importado.get(campo_importado, '')
                
                if campo_nome in ['peso_unitario']:
                    # Campo numérico
                    valor_importado = float(valor_importado or 0)
                    if abs(float(valor_bd or 0) - valor_importado) > 0.001:
                        diferencas.append(f"{campo_nome}: {valor_bd} → {valor_importado}")
                else:
                    # Campo textual
                    valor_bd_str = str(valor_bd or '').strip()
                    valor_importado_str = str(valor_importado or '').strip()
                    if valor_bd_str != valor_importado_str:
                        if valor_importado_str not in ['', 'None', 'nan']:
                            diferencas.append(f"{campo_nome}: '{valor_bd_str}' → '{valor_importado_str}'")
            
            if diferencas:
                print(f"   🔄 DIFERENÇAS ENCONTRADAS: {len(diferencas)}")
                comparacao['lotes_alterados'].append({
                    'lote': lote,
                    'endereco': endereco_importado,
                    'az': az_importado,
                    'endereco_original': item_estoque.endereco,
                    'az_original': item_estoque.az,
                    'divergencias': diferencas,
                    'dados_novos': item_importado,
                    'dados_atuais': {
                        'id': item_estoque.id,
                        'saldo': item_estoque.saldo,
                        'endereco': item_estoque.endereco,
                        'az': item_estoque.az,
                        'peneira_id': item_estoque.peneira.id,
                        'cultivar_id': item_estoque.cultivar.id,
                        'tratamento_id': item_estoque.tratamento.id if item_estoque.tratamento else None,
                        'peso_unitario': item_estoque.peso_unitario,
                        'embalagem': item_estoque.embalagem
                    }
                })
                comparacao['resumo']['atualizados'] += 1
            else:
                print(f"   ✅ SEM DIFERENÇAS")
                comparacao['lotes_iguais'].append({
                    'lote': lote,
                    'endereco': endereco_importado,
                    'az': az_importado,
                    'dados': item_importado
                })
                comparacao['resumo']['iguais'] += 1
                
        else:
            # Não encontrou por chave completa - NOVO LOTE
            print(f"   🆕 NÃO ENCONTRADO - Novo lote (chave completa não encontrada)")
            comparacao['novos_lotes'].append({
                'lote': lote,
                'endereco': endereco_importado,
                'az': az_importado,
                'dados': item_importado
            })
            comparacao['resumo']['novos'] += 1
    
    print(f"\n📊 RESUMO FINAL:")
    print(f"   🆕 Novos: {comparacao['resumo']['novos']}")
    print(f"   🔄 Para atualizar: {comparacao['resumo']['atualizados']}")
    print(f"   ✅ Idênticos: {comparacao['resumo']['iguais']}")
    
    return comparacao

@login_required
def testar_comparacao(request):
    """Teste manual da comparação"""
    print("🧪 [TESTE COMPARAÇÃO]")
    
    # Dados de exemplo
    dados_teste = [
        {
            'lote': 'PQH00208',
            'endereco': 'R05 LN10 P06',  # Endereço diferente
            'quantidade': 10,
            'peneira': 'PENEIRA NÃO ESPECIFICADA', 
            'cultivar': 'CULTIVAR NÃO ESPECIFICADO',
            'tratamento': 'SEM TRATAMENTO',
            'peso_unitario': 0,
            'embalagem': 'BAG'
        },
        {
            'lote': 'UCS0357-25', 
            'endereco': 'GERAL',  # Mesmo endereço
            'quantidade': 15,     # Quantidade diferente
            'peneira': 'PENEIRA NÃO ESPECIFICADA',
            'cultivar': 'CULTIVAR NÃO ESPECIFICADO',
            'tratamento': 'SEM TRATAMENTO',
            'peso_unitario': 0,
            'embalagem': 'BAG'
        }
    ]
    
    resultado = comparar_com_estoque_atual_com_produto(dados_teste)
    
    return JsonResponse({
        'success': True,
        'resultado': resultado,
        'message': 'Teste de comparação concluído - verifique o console'
    })


def verificar_diferencas_estoque(item_estoque, item_importado):
    """
    Verifica diferenças entre item do estoque e dados importados
    """
    diferencas = []
    
    campos_para_comparar = [
        ('quantidade', 'quantidade'),
        ('endereco', 'endereco'),
        ('cultivar_id', 'cultivar_id'),
        ('peneira_id', 'peneira_id'),
        ('categoria_id', 'categoria_id'),
        ('tratamento_id', 'tratamento_id'),
        ('peso_unitario', 'peso_unitario'),
        ('embalagem', 'embalagem'),
        ('empresa', 'empresa'),
        ('az', 'az'),
        ('cultura', 'cultura')
    ]
    
    for campo_estoque, campo_importado in campos_para_comparar:
        valor_estoque = getattr(item_estoque, campo_estoque, None)
        valor_importado = item_importado.get(campo_importado, None)
        
        # Tratamento especial para campos numéricos
        if campo_estoque in ['quantidade', 'peso_unitario']:
            valor_estoque = float(valor_estoque or 0)
            valor_importado = float(valor_importado or 0)
            
            if abs(valor_estoque - valor_importado) > 0.001:  # Margem de erro para floats
                diferencas.append(f"{campo_estoque}: {valor_estoque} → {valor_importado}")
        
        # Para campos textuais
        elif str(valor_estoque or '').strip() != str(valor_importado or '').strip():
            diferencas.append(f"{campo_estoque}: '{valor_estoque}' → '{valor_importado}'")
    
    return diferencas

def comparacao_radical_simples(novos_dados):
    """
    COMPARAÇÃO RADICAL: Se o lote existe no banco, considera para ATUALIZAR
    (ignora peneira/cultivar/tratamento por enquanto)
    """
    comparacao = {
        'novos_lotes': [],
        'lotes_alterados': [],
        'lotes_iguais': [],
        'resumo': {'novos': 0, 'atualizados': 0, 'iguais': 0}
    }
    
    print("💥 [COMPARAÇÃO RADICAL] Apenas por lote")
    
    for i, novo_item in enumerate(novos_dados):
        lote = novo_item.get('lote', '')
        
        print(f"\n--- Item {i+1}: {lote} ---")
        
        # Buscar QUALQUER registro com este lote
        item_bd = Estoque.objects.filter(lote=lote).first()
        
        if item_bd:
            print(f"   ✅ LOTE EXISTE NO BANCO - Marcando para ATUALIZAR")
            comparacao['lotes_alterados'].append({
                'lote': lote,
                'endereco': novo_item.get('endereco', ''),
                'dados_novos': novo_item,
                'dados_atuais': {
                    'id': item_bd.id,
                    'saldo': item_bd.saldo,
                    'endereco': item_bd.endereco
                }
            })
            comparacao['resumo']['atualizados'] += 1
        else:
            print(f"   🆕 LOTE NÃO EXISTE - Marcando como NOVO")
            comparacao['novos_lotes'].append({
                'lote': lote,
                'endereco': novo_item.get('endereco', ''),
                'dados': novo_item
            })
            comparacao['resumo']['novos'] += 1
    
    return comparacao




@login_required
def aprovar_importacao(request):
    """IMPORTAÇÃO INCREMENTAL - Apenas atualiza e cria, NÃO REMOVE lotes"""
    if request.method == 'POST':
        try:
            print("🟡 [IMPORTAÇÃO INCREMENTAL] Iniciando processamento...")
            print("📢 MODO: Apenas atualiza/cria lotes da planilha. NÃO remove lotes existentes!")
            
            data = json.loads(request.body)
            user = request.user
            
            with transaction.atomic():
                modificacoes = data.get('modificacoes', [])
                
                aplicados_count = 0
                erros_count = 0
                novos_count = 0
                atualizados_count = 0
                
                print(f"📦 Total de modificações na planilha: {len(modificacoes)}")
                
                # Contar quantos lotes existem ANTES da importação
                total_antes = Estoque.objects.count()
                print(f"📊 Total de lotes no sistema antes: {total_antes}")
                
                for i, mod in enumerate(modificacoes):
                    print(f"\n🔄 Processando {i+1}/{len(modificacoes)}: {mod.get('tipo')} - {mod.get('lote')}")
                    
                    if mod['tipo'] == 'novo':
                        # CRIAR novo registro
                        try:
                            # Buscar/crear objetos relacionados
                            cultivar = Cultivar.objects.get(id=mod['cultivar_id'])
                            peneira = Peneira.objects.get(id=mod['peneira_id'])
                            categoria = Categoria.objects.get(id=mod['categoria_id'])
                            tratamento = Tratamento.objects.get(id=mod['tratamento_id']) if mod.get('tratamento_id') else None
                            conferente = User.objects.get(id=mod['conferente_id'])
                            
                            # Processar valores
                            # Por estas linhas:
                            def safe_int(val, default=0):
                                try:
                                    return int(float(val))
                                except:
                                    return default

                            def safe_decimal(val, default=Decimal('0.00')):
                                try:
                                    if isinstance(val, str):
                                        val = val.replace(',', '.')
                                    return Decimal(str(val)).quantize(Decimal('0.01'))
                                except:
                                    return default

                            entrada = safe_int(mod.get('saldo', 0), 0)
                            peso_unitario = safe_decimal(mod.get('peso_unitario', 0), Decimal('0.00'))
                            peso_total = safe_decimal(mod.get('peso_total', 0), Decimal('0.00'))
                            # Calcular peso total se não fornecido
                            if peso_total == 0 and entrada > 0 and peso_unitario > 0:
                                peso_total = Decimal(entrada) * peso_unitario
                                peso_total = peso_total.quantize(Decimal('0.01'))
                            
                            # Converter data
                            data_entrada = timezone.now()  # Usar data atual para novos
                            data_entrada_str = mod.get('data_entrada', '')
                            if data_entrada_str:
                                try:
                                    if '/' in data_entrada_str:
                                        dia, mes, ano = data_entrada_str.split('/')
                                        data_entrada = timezone.make_aware(
                                            datetime.datetime(int(ano), int(mes), int(dia))
                                        )
                                except:
                                    pass  # Usa data atual se houver erro
                            
                            # Verificar se já existe (por segurança)
                            existe = Estoque.objects.filter(
                                lote=mod['lote'],
                                endereco=mod['endereco'],
                                az=mod.get('az', ''),
                                produto=mod.get('produto', '')
                            ).first()
                            
                            if existe:
                                print(f"   ⚠️  Já existe no sistema (ID: {existe.id}) - convertendo para ATUALIZAR")
                                # Converter para atualização
                                item = existe
                                valores_antigos = {
                                    'saldo': item.saldo,
                                    'peso_unitario': item.peso_unitario,
                                    'peso_total': item.peso_total,
                                    'endereco': item.endereco,
                                    'az': item.az
                                }
                                
                                # Atualizar campos
                                item.saldo = entrada
                                item.entrada = entrada
                                item.peso_unitario = peso_unitario
                                item.peso_total = peso_total
                                item.endereco = mod['endereco']
                                item.az = mod.get('az', '')
                                item.produto = mod.get('produto', '')
                                item.observacao = f"Atualizado via importação em {timezone.now().strftime('%d/%m/%Y')}"
                                item.conferente = conferente
                                
                                # Atualizar FKs
                                item.cultivar = cultivar
                                item.peneira = peneira
                                item.categoria = categoria
                                item.tratamento = tratamento
                                
                                item.save()
                                
                                # Registrar histórico
                                HistoricoMovimentacao.objects.create(
                                    estoque=item,
                                    usuario=user,
                                    tipo='Importação (Atualização)',
                                    descricao=f"Lote atualizado na importação: Saldo {valores_antigos['saldo']} → {entrada}"
                                )
                                
                                atualizados_count += 1
                                print(f"   ✅ ATUALIZADO (existente): {mod['lote']}")
                                
                            else:
                                # Criar novo
                                novo_item = Estoque.objects.create(
                                    lote=mod['lote'],
                                    produto=mod.get('produto', ''),
                                    cultivar=cultivar,
                                    peneira=peneira,
                                    categoria=categoria,
                                    tratamento=tratamento,
                                    endereco=mod['endereco'],
                                    entrada=entrada,
                                    saida=0,
                                    saldo=entrada,
                                    conferente=conferente,
                                    origem_destino=mod.get('origem_destino', ''),
                                    data_entrada=data_entrada,
                                    especie=mod.get('especie', 'SOJA'),
                                    empresa=mod.get('empresa', ''),
                                    embalagem=mod.get('embalagem', 'BAG'),
                                    peso_unitario=peso_unitario,
                                    peso_total=peso_total,
                                    az=mod.get('az', ''),
                                    observacao=f"Criado via importação em {timezone.now().strftime('%d/%m/%Y')}",
                                    
                                )
                                
                                # Registrar histórico
                                HistoricoMovimentacao.objects.create(
                                    estoque=novo_item,
                                    usuario=user,
                                    tipo='Importação (Novo)',
                                    descricao=f"Lote criado via importação: {mod['lote']} | Endereço: {mod['endereco']} | Saldo: {entrada}"
                                )
                                
                                novos_count += 1
                                print(f"   ✅ NOVO criado: {mod['lote']}")
                            
                            aplicados_count += 1
                            
                        except Exception as e:
                            print(f"❌ Erro ao processar NOVO {mod['lote']}: {e}")
                            erros_count += 1
                    
                    elif mod['tipo'] == 'atualizar':
                        # ATUALIZAR registro existente
                        try:
                            item_id = mod.get('dados_atuais', {}).get('id')
                            if not item_id:
                                print(f"❌ ID não encontrado para atualização: {mod['lote']}")
                                erros_count += 1
                                continue
                            
                            item = Estoque.objects.get(id=item_id)
                            
                            # Registrar valores antigos
                            valores_antigos = {
                                'endereco': item.endereco,
                                'saldo': item.saldo,
                                'az': item.az,
                                'produto': item.produto,
                                'peso_unitario': item.peso_unitario,
                                'peso_total': item.peso_total,
                                'embalagem': item.embalagem
                            }
                            
                            print(f"   🔄 ATUALIZANDO registro ID: {item_id}")
                            
                            # Processar novos valores
                            novo_saldo = processar_inteiro(mod.get('saldo', 0), 0)
                            novo_peso_unitario = processar_decimal(mod.get('peso_unitario', 0), Decimal('0.00'))
                            novo_peso_total = processar_decimal(mod.get('peso_total', 0), Decimal('0.00'))
                            
                            # Calcular peso total se não fornecido
                            if novo_peso_total == 0 and novo_saldo > 0 and novo_peso_unitario > 0:
                                novo_peso_total = Decimal(novo_saldo) * novo_peso_unitario
                                novo_peso_total = novo_peso_total.quantize(Decimal('0.01'))
                            
                            # Atualizar campos
                            item.endereco = mod['endereco']
                            item.produto = mod.get('produto', '')
                            item.saldo = novo_saldo
                            item.entrada = novo_saldo
                            item.saida = 0
                            item.peso_unitario = novo_peso_unitario
                            item.peso_total = novo_peso_total
                            item.az = mod.get('az', '')
                            item.observacao = f"Atualizado via importação em {timezone.now().strftime('%d/%m/%Y')}"
                            item.empresa = mod.get('empresa', '')
                            item.origem_destino = mod.get('origem_destino', '')
                            item.especie = mod.get('especie', 'SOJA')
                            item.embalagem = mod.get('embalagem', 'BAG')
                          
                            
                            # Atualizar FKs
                            if mod.get('cultivar_id'):
                                item.cultivar = Cultivar.objects.get(id=mod['cultivar_id'])
                            if mod.get('peneira_id'):
                                item.peneira = Peneira.objects.get(id=mod['peneira_id'])
                            if mod.get('categoria_id'):
                                item.categoria = Categoria.objects.get(id=mod['categoria_id'])
                            if mod.get('tratamento_id'):
                                item.tratamento = Tratamento.objects.get(id=mod['tratamento_id'])
                            if mod.get('conferente_id'):
                                item.conferente = User.objects.get(id=mod['conferente_id'])
                            
                            # Converter data se fornecida
                            data_entrada_str = mod.get('data_entrada', '')
                            if data_entrada_str:
                                try:
                                    if '/' in data_entrada_str:
                                        dia, mes, ano = data_entrada_str.split('/')
                                        item.data_entrada = timezone.make_aware(
                                            datetime.datetime(int(ano), int(mes), int(dia))
                                        )
                                except:
                                    pass  # Mantém a data atual
                            
                            item.save()
                            
                            # Registrar diferenças
                            diferencas = []
                            for campo, valor_antigo in valores_antigos.items():
                                valor_novo = getattr(item, campo)
                                if str(valor_antigo or '') != str(valor_novo or ''):
                                    diferencas.append(f"{campo}: {valor_antigo} → {valor_novo}")
                            
                            if diferencas:
                                HistoricoMovimentacao.objects.create(
                                    estoque=item,
                                    usuario=user,
                                    tipo='Importação (Atualização)',
                                    descricao=f"Lote atualizado: {', '.join(diferencas[:3])}"  # Limitar a 3 mudanças
                                )
                            
                            aplicados_count += 1
                            atualizados_count += 1
                            print(f"   ✅ Lote ATUALIZADO: {mod['lote']}")
                            
                        except Estoque.DoesNotExist:
                            print(f"❌ Lote não encontrado para atualização: {mod['lote']}")
                            erros_count += 1
                        except Exception as e:
                            print(f"❌ Erro ao atualizar {mod['lote']}: {e}")
                            erros_count += 1
                
                # 🔥 **NÃO REMOVER NENHUM LOTE** - IMPORTAÇÃO INCREMENTAL
                print(f"\n📢 IMPORTANTE: Modo INCREMENTAL - Nenhum lote foi removido do sistema!")
                
                # Contar quantos lotes existem DEPOIS da importação
                total_depois = Estoque.objects.count()
                diferenca = total_depois - total_antes
                
                print(f"\n🎉 IMPORTAÇÃO INCREMENTAL CONCLUÍDA:")
                print(f"   📊 Lotes antes: {total_antes}")
                print(f"   📊 Lotes depois: {total_depois}")
                print(f"   📈 Diferença: {'+' if diferenca >= 0 else ''}{diferenca}")
                print(f"   ✅ Novos criados: {novos_count}")
                print(f"   🔄 Atualizados: {atualizados_count}")
                print(f"   ❌ Com erro: {erros_count}")
                print(f"   📋 Total processado: {len(modificacoes)}")
                
                return JsonResponse({
                    'success': True,
                    'message': f'Importação concluída! {novos_count} novos lotes criados, {atualizados_count} atualizados, {erros_count} erros. Nenhum lote removido.',
                    'stats': {
                        'novos': novos_count,
                        'atualizados': atualizados_count,
                        'erros': erros_count,
                        'total_antes': total_antes,
                        'total_depois': total_depois
                    }
                })
                
        except Exception as e:
            print(f"💥 Erro geral na importação: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'error': f'Erro ao processar importação: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})
@login_required
def lotes_para_remover(request):
    """Retorna os lotes que serão removidos (não estão na planilha atual)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lotes_na_planilha = data.get('lotes_na_planilha', [])
            processed_count = data.get('processed_count', 0)
            
            print(f"🔍 [LOTES PARA REMOVER] Buscando lotes fora da planilha...")
            print(f"📋 Lotes na planilha: {len(lotes_na_planilha)}")
            print(f"📊 Processados: {processed_count}")
            
            # Buscar todos os lotes do banco que NÃO estão na planilha
            if lotes_na_planilha:
                lotes_para_remover = Estoque.objects.exclude(
                    lote__in=lotes_na_planilha
                ).select_related('cultivar').values(
                    'lote', 'produto', 'endereco', 'az', 'saldo', 'cultivar__nome'
                )
            else:
                # Se não há lotes na planilha, todos serão removidos
                lotes_para_remover = Estoque.objects.all().select_related('cultivar').values(
                    'lote', 'produto', 'endereco', 'az', 'saldo', 'cultivar__nome'
                )
            
            lotes_list = []
            for lote in lotes_para_remover:
                lotes_list.append({
                    'lote': lote['lote'],
                    'produto': lote['produto'] or '',
                    'endereco': lote['endereco'] or '',
                    'az': lote['az'] or '',
                    'saldo': lote['saldo'],
                    'cultivar': lote['cultivar__nome'] or ''
                })
            
            print(f"🗑️  Lotes para remover encontrados: {len(lotes_list)}")
            
            return JsonResponse({
                'success': True,
                'lotes_para_remover': lotes_list,
                'total_remover': len(lotes_list)
            })
            
        except Exception as e:
            print(f"❌ Erro ao buscar lotes para remover: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def consolidar_lotes_duplicados(request):
    """Consolida lotes duplicados (mesmo lote + produto + endereço + AZ)"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Encontrar lotes duplicados exatos
                from django.db.models import Count
                
                duplicados = Estoque.objects.values(
                    'lote', 'produto', 'endereco', 'az'
                ).annotate(
                    total=Count('id')
                ).filter(total__gt=1)
                
                consolidados_count = 0
                
                for dup in duplicados:
                    lote = dup['lote']
                    produto = dup['produto']
                    endereco = dup['endereco']
                    az = dup['az']
                    
                    print(f"🔍 Consolidando: {lote} | {produto} | {endereco} | {az}")
                    
                    # Buscar todos os registros duplicados
                    registros = Estoque.objects.filter(
                        lote=lote,
                        produto=produto,
                        endereco=endereco,
                        az=az
                    ).order_by('id')
                    
                    if registros.count() > 1:
                        # Manter o primeiro e somar os outros
                        manter = registros.first()
                        excluir = registros[1:]
                        
                        total_saldo = manter.saldo
                        total_peso = manter.peso_total
                        
                        for reg in excluir:
                            print(f"   ➕ Somando: {reg.id} (Saldo: {reg.saldo})")
                            total_saldo += reg.saldo
                            total_peso += reg.peso_total
                            reg.delete()
                        
                        # Atualizar o registro mantido
                        manter.saldo = total_saldo
                        manter.peso_total = total_peso
                        manter.save()
                        
                        consolidados_count += 1
                        print(f"✅ Consolidado: {lote} | Saldo total: {total_saldo}")
                
                return JsonResponse({
                    'success': True,
                    'message': f'{consolidados_count} grupos de lotes consolidados!'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao consolidar lotes: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def debug_import_data(request):
    """Debug: mostra os dados que estão chegando na aprovação"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("🔍 [DEBUG IMPORT DATA]")
            print("Dados recebidos:", json.dumps(data, indent=2, ensure_ascii=False))
            
            return JsonResponse({
                'success': True,
                'received_data': data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


@login_required
def limpar_duplicados_manualmente(request):
    """Limpa registros duplicados manualmente"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Encontrar lotes duplicados
                from django.db.models import Count
                
                duplicados = Estoque.objects.values(
                    'lote', 'peneira_id', 'cultivar_id', 'tratamento_id'
                ).annotate(
                    total=Count('id')
                ).filter(total__gt=1)
                
                print(f"🔍 Encontrados {len(duplicados)} grupos de duplicados")
                
                total_excluidos = 0
                
                for dup in duplicados:
                    lote = dup['lote']
                    peneira_id = dup['peneira_id']
                    cultivar_id = dup['cultivar_id']
                    tratamento_id = dup['tratamento_id']
                    
                    # Manter apenas o mais recente
                    registros = Estoque.objects.filter(
                        lote=lote,
                        peneira_id=peneira_id,
                        cultivar_id=cultivar_id,
                        tratamento_id=tratamento_id
                    ).order_by('-id')
                    
                    manter = registros.first()
                    excluir = registros[1:]
                    
                    for reg in excluir:
                        print(f"🗑️  Excluindo duplicado: {lote} (ID: {reg.id})")
                        reg.delete()
                        total_excluidos += 1
                
                return JsonResponse({
                    'success': True,
                    'message': f'Duplicados limpos: {total_excluidos} registros excluídos'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao limpar duplicados: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# ================================================================
# OUTRAS VIEWS (mantenha as suas views existentes)
# ================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from .models import Estoque, Cultivar, Peneira, Categoria, Tratamento, HistoricoMovimentacao, FotoMovimentacao

@login_required
def lista_estoque(request):
    # 1. Query Base
    itens_queryset = Estoque.objects.all().select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento'
    ).order_by('-data_ultima_movimentacao')

    # 2. Filtros
    termo = request.GET.get('busca', '').strip()
    if termo:
        palavras = termo.split()
        query = Q()
        for palavra in palavras:
            query &= (
                Q(lote__icontains=palavra) |
                Q(produto__icontains=palavra) |
                Q(cultivar__nome__icontains=palavra) |
                Q(peneira__nome__icontains=palavra) |
                Q(endereco__icontains=palavra) |
                Q(empresa__icontains=palavra)
            )
        itens_queryset = itens_queryset.filter(query)

    status_filter = request.GET.get('status', '')
    if status_filter == 'disponivel':
        itens_queryset = itens_queryset.filter(saldo__gt=0)
    elif status_filter == 'esgotado':
        itens_queryset = itens_queryset.filter(saldo=0)

    # 3. CÁLCULO DETALHADO (BAG vs SC)
    def calcular_metricas(queryset, campo):
        # Soma quantidade física de BAGs
        qtd_bags = queryset.filter(embalagem='BAG').aggregate(t=Sum(campo))['t'] or 0
        # Soma quantidade física de Sacos
        qtd_sc_fisico = queryset.filter(embalagem='SC').aggregate(t=Sum(campo))['t'] or 0
        # Calcula total convertido (1 BAG = 25 SC) + Sacos físicos
        total_convertido = (qtd_bags * 25) + qtd_sc_fisico
        
        return {
            'bags': qtd_bags,
            'sc_fisico': qtd_sc_fisico,
            'total_sc': total_convertido
        }

    # Gera os dicionários de dados para os cards
    dados_entrada = calcular_metricas(itens_queryset, 'entrada')
    dados_saida = calcular_metricas(itens_queryset, 'saida')
    dados_saldo = calcular_metricas(itens_queryset, 'saldo')
    
    total_lotes = itens_queryset.count()

    # 4. Paginação
    page_size = int(request.GET.get('page_size', 25))
    paginator = Paginator(itens_queryset, page_size)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        'itens': page_obj,
        # Passando os dicionários completos para o template
        'dados_entrada': dados_entrada,
        'dados_saida': dados_saida,
        'dados_saldo': dados_saldo,
        'total_lotes': total_lotes,
        'busca': termo,
        'status': status_filter,
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
    }
    
    return render(request, 'sapp/tabela_estoque.html', context)
    
    
    
    
    
# No arquivo views.py

@login_required
def registrar_saida(request, id):
    item = get_object_or_404(Estoque, id=id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Captura de Dados
                qtd = int(request.POST.get('quantidade_saida', 0))
                carga = request.POST.get('numero_carga')
                motorista = request.POST.get('motorista')
                placa = request.POST.get('placa')
                cliente = request.POST.get('cliente')
                ordem = request.POST.get('ordem_entrega')
                obs = request.POST.get('observacao')
                fotos = request.FILES.getlist('fotos')

                # 2. Validação Rigorosa (Obrigatoriedade)
                erros = []
                if qtd <= 0: erros.append("Quantidade inválida.")
                if qtd > item.saldo: erros.append("Saldo insuficiente.")
                if not motorista: erros.append("Motorista é obrigatório.")
                if not placa: erros.append("Placa é obrigatória.")
                if not carga: erros.append("Número da Carga é obrigatório.")
                if not fotos: erros.append("Pelo menos uma foto é obrigatória na expedição.")

                if erros:
                    for e in erros: messages.error(request, f"❌ {e}")
                    return redirect('sapp:lista_estoque')

                # 3. Processamento
                saldo_anterior = item.saldo
                item.saida += qtd
                item.saldo = item.entrada - item.saida
                item.conferente = request.user
                item.save()

                # 4. Descrição Rica em HTML para o Histórico
                desc_html = f"""
                    <div class="d-flex flex-column gap-1">
                        <div class="d-flex justify-content-between border-bottom pb-1">
                            <span><strong>Qtd:</strong> <span class="text-danger">-{qtd}</span></span>
                            <span><strong>Saldo Restante:</strong> {item.saldo}</span>
                        </div>
                        <div class="small text-muted mt-1">
                            <i class="fas fa-truck"></i> <strong>Carga:</strong> {carga} | <strong>Placa:</strong> {placa}<br>
                            <i class="fas fa-id-card"></i> <strong>Motorista:</strong> {motorista}<br>
                            <i class="fas fa-building"></i> <strong>Cliente:</strong> {cliente or 'N/A'}<br>
                            <i class="fas fa-clipboard-list"></i> <strong>Ordem:</strong> {ordem or 'N/A'}
                        </div>
                        {f'<div class="mt-1 p-1 bg-light rounded small">Obs: {obs}</div>' if obs else ''}
                    </div>
                """

                historico = HistoricoMovimentacao.objects.create(
                    estoque=item,
                    usuario=request.user,
                    tipo='Expedição',
                    descricao=desc_html,
                    numero_carga=carga,
                    motorista=motorista,
                    placa=placa,
                    cliente=cliente,
                    ordem_entrega=ordem
                )

                # 5. Salvar Fotos
                for f in fotos:
                    FotoMovimentacao.objects.create(historico=historico, arquivo=f)

                messages.success(request, f"✅ Expedição da Carga {carga} registrada com sucesso!")

        except Exception as e:
            messages.error(request, f"Erro crítico: {e}")
            
    return redirect('sapp:lista_estoque')

@login_required
def transferir(request, id):
    item_origem = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # --- 1. CAPTURA DOS DADOS BÁSICOS ---
                qtd = int(request.POST.get('quantidade'))
                novo_end = request.POST.get('novo_endereco').strip().upper()
                obs = request.POST.get('observacao', '')
                fotos = request.FILES.getlist('fotos')

                # --- 2. CAPTURA DOS DADOS EDITÁVEIS (PREENCHIDOS OU ORIGINAIS) ---
                # Se o campo vier vazio no POST, usamos o dado da origem como fallback
                novo_produto = request.POST.get('produto', item_origem.produto or '').strip()
                nova_empresa = request.POST.get('empresa', item_origem.empresa or '').strip()
                novo_az = request.POST.get('az', item_origem.az or '').strip()
                nova_embalagem = request.POST.get('embalagem', item_origem.embalagem)
                
                # Tratamento de Peso Unitário
                peso_raw = request.POST.get('peso_unitario', str(item_origem.peso_unitario))
                try:
                    peso_raw = str(peso_raw).replace(',', '.')
                    novo_peso_unitario = Decimal(peso_raw)
                except:
                    novo_peso_unitario = item_origem.peso_unitario

                # Tratamento de Foreign Keys (Cultivar, Peneira, etc)
                # Tenta pegar do POST, senão mantém o original
                try:
                    novo_cultivar_id = request.POST.get('cultivar')
                    obj_cultivar = Cultivar.objects.get(id=novo_cultivar_id) if novo_cultivar_id else item_origem.cultivar
                except: obj_cultivar = item_origem.cultivar

                try:
                    nova_peneira_id = request.POST.get('peneira')
                    obj_peneira = Peneira.objects.get(id=nova_peneira_id) if nova_peneira_id else item_origem.peneira
                except: obj_peneira = item_origem.peneira

                try:
                    nova_categoria_id = request.POST.get('categoria')
                    obj_categoria = Categoria.objects.get(id=nova_categoria_id) if nova_categoria_id else item_origem.categoria
                except: obj_categoria = item_origem.categoria

                try:
                    novo_tratamento_id = request.POST.get('tratamento')
                    if novo_tratamento_id:
                        obj_tratamento = Tratamento.objects.get(id=novo_tratamento_id)
                    else:
                        obj_tratamento = item_origem.tratamento
                except: obj_tratamento = item_origem.tratamento

                # --- 3. VALIDAÇÃO E SAÍDA DA ORIGEM ---
                if qtd > item_origem.saldo:
                    messages.error(request, f"Saldo insuficiente. Disponível: {item_origem.saldo}")
                    return redirect('sapp:lista_estoque')

                # Retira da Origem
                item_origem.saida += qtd
                item_origem.saldo = item_origem.entrada - item_origem.saida
                item_origem.save()

                # Histórico de Saída
                desc_saida = f"""
                    <strong>Saiu:</strong> <span class="text-danger">-{qtd}</span><br>
                    <strong>Destino:</strong> {novo_end}<br>
                    {f'<small class="text-muted">Obs: {obs}</small>' if obs else ''}
                """
                h_saida = HistoricoMovimentacao.objects.create(
                    estoque=item_origem,
                    usuario=request.user,
                    tipo='Transferência (Saída)',
                    descricao=desc_saida
                )
                for f in fotos: FotoMovimentacao.objects.create(historico=h_saida, arquivo=f)

                # --- 4. ENTRADA NO DESTINO (COM DADOS NOVOS/EDITADOS) ---
                
                # Procura se já existe um lote IDENTICO aos NOVOS DADOS no NOVO ENDEREÇO
                item_destino = Estoque.objects.filter(
                    lote=item_origem.lote,
                    endereco=novo_end,
                    cultivar=obj_cultivar,
                    peneira=obj_peneira,
                    categoria=obj_categoria,
                    tratamento=obj_tratamento,
                    produto=novo_produto, # Verifica também se o produto é o mesmo
                    az=novo_az
                ).first()

                desc_entrada = f"""
                    <strong>Entrou:</strong> <span class="text-success">+{qtd}</span><br>
                    <strong>Origem:</strong> {item_origem.endereco}<br>
                """

                if item_destino:
                    # Se já existe exatamente igual, apenas soma
                    item_destino.entrada += qtd
                    item_destino.saldo += qtd # Recalcula saldo
                    # Atualiza dados secundários caso tenham mudado (opcional)
                    item_destino.peso_unitario = novo_peso_unitario 
                    item_destino.conferente = request.user
                    item_destino.save()
                    
                    HistoricoMovimentacao.objects.create(
                        estoque=item_destino, 
                        usuario=request.user, 
                        tipo='Transferência (Entrada)', 
                        descricao=desc_entrada
                    )
                else:
                    # Se não existe, CRIA UM NOVO com os dados editados
                    novo_item = Estoque.objects.create(
                        lote=item_origem.lote,
                        produto=novo_produto, # Dado Novo
                        cultivar=obj_cultivar, # Dado Novo
                        peneira=obj_peneira, # Dado Novo
                        categoria=obj_categoria, # Dado Novo
                        tratamento=obj_tratamento, # Dado Novo
                        az=novo_az, # Dado Novo
                        endereco=novo_end,
                        entrada=qtd,
                        saida=0,
                        saldo=qtd,
                        cliente=request.POST.get('cliente', item_origem.cliente), # Tenta pegar cliente novo ou usa antigo
                        origem_destino=f"Transf. de {item_origem.endereco}",
                        conferente=request.user,
                        especie=request.POST.get('especie', item_origem.especie),
                        empresa=nova_empresa, # Dado Novo
                        embalagem=nova_embalagem, # Dado Novo
                        peso_unitario=novo_peso_unitario, # Dado Novo
                        observacao=f"Transferido de {item_origem.endereco}. {obs}"
                    )
                    HistoricoMovimentacao.objects.create(
                        estoque=novo_item, 
                        usuario=request.user, 
                        tipo='Transferência (Entrada)', 
                        descricao=desc_entrada
                    )

                messages.success(request, f"✅ Transferência realizada para {novo_end}!")
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"Erro na transferência: {e}")
            
    return redirect('sapp:lista_estoque')

@login_required
def nova_entrada(request):
    """Registra uma nova entrada no estoque - VERSÃO SIMPLIFICADA E CORRIGIDA"""
    if request.method == 'POST':
        try:
            print("🔔 [NOVA ENTRADA] Iniciando processamento...")
            
            # Captura dos dados básicos
            lote = request.POST.get('lote', '').strip()
            produto = request.POST.get('produto', '').strip()
            endereco = request.POST.get('endereco', '').strip().upper()
            quantidade = request.POST.get('entrada', '0').strip()
            especie = request.POST.get('especie', 'SOJA').strip()
            cliente = request.POST.get('cliente', '').strip()
            
            # Validações básicas
            erros = []
            if not lote:
                erros.append("O número do lote é obrigatório.")
            if not endereco:
                erros.append("O endereço é obrigatório.")
            
            try:
                quantidade_int = int(quantidade)
                if quantidade_int <= 0:
                    erros.append("A quantidade deve ser maior que zero.")
            except ValueError:
                erros.append("Quantidade inválida.")
            
            # Validar objetos relacionados
            try:
                cultivar_id = request.POST.get('cultivar')
                if not cultivar_id:
                    erros.append("O cultivar é obrigatório.")
                else:
                    cultivar = Cultivar.objects.get(id=cultivar_id)
            except (ValueError, Cultivar.DoesNotExist):
                erros.append("Cultivar inválido.")
            
            try:
                peneira_id = request.POST.get('peneira')
                if not peneira_id:
                    erros.append("A peneira é obrigatória.")
                else:
                    peneira = Peneira.objects.get(id=peneira_id)
            except (ValueError, Peneira.DoesNotExist):
                erros.append("Peneira inválida.")
            
            try:
                categoria_id = request.POST.get('categoria')
                if not categoria_id:
                    erros.append("A categoria é obrigatória.")
                else:
                    categoria = Categoria.objects.get(id=categoria_id)
            except (ValueError, Categoria.DoesNotExist):
                erros.append("Categoria inválida.")
            
            # Tratamento é opcional
            tratamento_id = request.POST.get('tratamento')
            tratamento = None
            if tratamento_id:
                try:
                    tratamento = Tratamento.objects.get(id=tratamento_id)
                except (ValueError, Tratamento.DoesNotExist):
                    pass  # Tratamento é opcional, não é erro
            
            # Processar peso unitário
            peso_raw = request.POST.get('peso_unitario', '0')
            try:
                peso_raw = str(peso_raw).replace(',', '.')
                peso_unitario = Decimal(peso_raw)
            except (InvalidOperation, ValueError):
                peso_unitario = Decimal('0.00')
            
            # Outros campos
            empresa = request.POST.get('empresa', '').strip()
            origem_destino = request.POST.get('origem_destino', '').strip()
            az = request.POST.get('az', '').strip()
            observacao = request.POST.get('observacao', '').strip()
            embalagem = request.POST.get('embalagem', 'BAG').strip()
            
            # Se houver erros, mostrar todos
            if erros:
                for erro in erros:
                    messages.error(request, f"❌ {erro}")
                return redirect('sapp:lista_estoque')
            
            # Verificar se já existe lote com mesmo endereço
            lote_existente = Estoque.objects.filter(
                lote=lote,
                endereco=endereco,
                cultivar=cultivar
            ).first()
            
            with transaction.atomic():
                historico = None
                
                if lote_existente:
                    print(f"✅ [NOVA ENTRADA] Lote existente encontrado: {lote}")
                    # Somar à entrada existente
                    entrada_anterior = lote_existente.entrada
                    saldo_anterior = lote_existente.saldo
                    
                    lote_existente.entrada += quantidade_int
                    lote_existente.conferente = request.user
                    
                    # Atualizar outros campos se fornecidos
                    if empresa:
                        lote_existente.empresa = empresa
                    if produto:
                        lote_existente.produto = produto
                    if cliente:
                        lote_existente.cliente = cliente
                    if peso_unitario > 0:
                        lote_existente.peso_unitario = peso_unitario
                    if origem_destino:
                        lote_existente.origem_destino = origem_destino
                    if az:
                        lote_existente.az = az
                    if observacao:
                        if lote_existente.observacao:
                            lote_existente.observacao += f"\n\n[ENTRADA ADICIONAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
                        else:
                            lote_existente.observacao = f"[ENTRADA ADICIONAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
                    
                    # Salvar para recalcular saldo automaticamente
                    lote_existente.save()
                    
                    # Criar histórico
                    historico = HistoricoMovimentacao.objects.create(
                        estoque=lote_existente,
                        usuario=request.user,
                        tipo='Entrada (Adição)',
                        descricao=(
                            f"<b>ENTRADA ADICIONAL</b><br>"
                            f"<b>Quantidade adicionada:</b> {quantidade_int}<br>"
                            f"<b>Entrada anterior:</b> {entrada_anterior}<br>"
                            f"<b>Saldo anterior:</b> {saldo_anterior}<br>"
                            f"<b>Novo saldo:</b> {lote_existente.saldo}<br>"
                            f"<b>Produto:</b> {produto or 'Não informado'}<br>"
                            f"<b>Observação:</b> {observacao or 'Nenhuma'}"
                        )
                    )
                    
                    msg = f"✅ {quantidade_int} unidades adicionadas ao lote existente {lote}!"
                    
                else:
                    print(f"✅ [NOVA ENTRADA] Criando novo lote: {lote}")
                    # Criar novo lote
                    novo_item = Estoque.objects.create(
                        lote=lote,
                        produto=produto,
                        cultivar=cultivar,
                        peneira=peneira,
                        categoria=categoria,
                        tratamento=tratamento,
                        endereco=endereco,
                        entrada=quantidade_int,
                        saida=0,
                        saldo=quantidade_int,  # Será recalculado no save()
                        conferente=request.user,
                        origem_destino=origem_destino,
                        especie=especie,
                        empresa=empresa,
                        embalagem=embalagem,
                        peso_unitario=peso_unitario,
                        az=az,
                        cliente=cliente,
                        observacao=observacao or f"Criado via sistema em {timezone.now().strftime('%d/%m/%Y %H:%M')}"
                    )
                    
                    # Criar histórico
                    historico = HistoricoMovimentacao.objects.create(
                        estoque=novo_item,
                        usuario=request.user,
                        tipo='Entrada (Novo)',
                        descricao=(
                            f"<b>NOVO LOTE CRIADO</b><br>"
                            f"<b>Quantidade inicial:</b> {quantidade_int}<br>"
                            f"<b>Endereço:</b> {endereco}<br>"
                            f"<b>Produto:</b> {produto or 'Não informado'}<br>"
                            f"<b>Cliente:</b> {cliente or 'Não informado'}<br>"
                            f"<b>Observação:</b> {observacao or 'Nenhuma'}"
                        )
                    )
                    
                    msg = f"✅ Novo lote {lote} criado com {quantidade_int} unidades!"
                
                # Salvar fotos se houver
                fotos = request.FILES.getlist('fotos')
                if fotos and historico:
                    for foto in fotos:
                        FotoMovimentacao.objects.create(historico=historico, arquivo=foto)
                        print(f"📸 Foto salva: {foto.name}")
                
                messages.success(request, msg)
                print(f"✅ [NOVA ENTRADA] Concluído: {msg}")
                
        except Exception as e:
            print(f"❌ [NOVA ENTRADA] Erro: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            messages.error(request, f"❌ Erro ao processar entrada: {str(e)}")
    
    return redirect('sapp:lista_estoque')

from django.db import transaction
from .models import FotoMovimentacao # e os outros models   
    


@login_required
def nova_saida(request):
    """Registra uma nova saída geral (para qualquer lote)"""
    if request.method == 'POST':
        try:
            lote_id = request.POST.get('lote_id')
            quantidade = int(request.POST.get('quantidade', 0))
            numero_carga = request.POST.get('numero_carga', '')
            motorista = request.POST.get('motorista', '')
            cliente = request.POST.get('cliente', '')
            observacao = request.POST.get('observacao', '')
            
            if not lote_id or quantidade <= 0:
                messages.error(request, "❌ Dados inválidos.")
                return redirect('sapp:lista_estoque')
            
            item = Estoque.objects.get(id=lote_id)
            
            if quantidade > item.saldo:
                messages.error(request, f"❌ Quantidade excede o saldo disponível ({item.saldo}).")
                return redirect('sapp:lista_estoque')
            
            # Salvar estado anterior
            saldo_anterior = item.saldo
            
            # Atualizar saída e saldo
            item.saida += quantidade  # CORRETO
            item.saldo = item.entrada - item.saida  # CORRETO
            
            # Recalcular peso total
            if item.peso_unitario:
                item.peso_total = Decimal(item.saldo) * Decimal(item.peso_unitario)
            
            # Atualizar data da última saída
            item.data_ultima_saida = timezone.now()
            
            # Atualizar observação
            if observacao:
                if item.observacao:
                    item.observacao += f"\n\n[EXPEDIÇÃO GERAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
                else:
                    item.observacao = f"[EXPEDIÇÃO GERAL {timezone.now().strftime('%d/%m/%Y %H:%M')}]: {observacao}"
            
            item.save()
            
            # Registrar histórico
            historico = HistoricoMovimentacao.objects.create(
                estoque=item,
                usuario=request.user,
                tipo='Expedição via Sistema',
                descricao=(
                    f"<b>📤 EXPEDIÇÃO REGISTRADA</b><br>"
                    f"<b>Método:</b> Formulário Geral<br>"
                    f"<b>Quantidade:</b> {quantidade} unidades<br>"
                    f"<b>Carga:</b> {numero_carga}<br>"
                    f"<b>Motorista:</b> {motorista}<br>"
                    f"<b>Cliente:</b> {cliente}<br>"
                    f"<b>Saldo anterior:</b> {saldo_anterior}<br>"
                    f"<b>Novo saldo:</b> {item.saldo}<br>"
                    f"<b>Observação:</b> {observacao or 'Nenhuma'}<br>"
                    f"<b>Responsável:</b> {request.user.get_full_name() or request.user.username}"
                ),
                numero_carga=numero_carga,
                motorista=motorista,
                cliente=cliente
            )
            
            # Salvar foto se existir
            if 'foto' in request.FILES:
                historico.foto = request.FILES['foto']
                historico.save()
            
            messages.success(request, f"✅ Expedição de {quantidade} unidades registrada para o lote {item.lote}!")
            
        except Estoque.DoesNotExist:
            messages.error(request, "❌ Lote não encontrado.")
        except Exception as e:
            messages.error(request, f"❌ Erro ao registrar expedição: {str(e)}")
            import traceback
            print(f"🔍 Erro detalhado: {traceback.format_exc()}")
    
    return redirect('sapp:lista_estoque')

@login_required
def relatorio_saidas(request):
    """Relatório detalhado de todas as saídas"""
    if request.method == 'POST':
        # Filtros por período
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        
        saidas = HistoricoMovimentacao.objects.filter(tipo__contains='Saída')
        
        if data_inicio:
            saidas = saidas.filter(data_hora__gte=data_inicio)
        if data_fim:
            saidas = saidas.filter(data_hora__lte=data_fim)
        
        # Agrupar por destino
        saidas_por_destino = saidas.values('descricao').annotate(
            total=Count('id'),
            ultima_data=Max('data_hora')
        )
        
        context = {
            'saidas': saidas,
            'saidas_por_destino': saidas_por_destino,
            'total_saidas': saidas.count(),
            'periodo': f"{data_inicio} a {data_fim}" if data_inicio and data_fim else "Todos os períodos"
        }
        
        return render(request, 'sapp/relatorio_saidas.html', context)
    
    return render(request, 'sapp/relatorio_saidas.html')

        

@login_required
def limpar_cache_importacao(request):
    """Limpa cache de importação"""
    from django.core.cache import cache
    cache_keys = cache.keys('*importacao*')
    for key in cache_keys:
        cache.delete(key)
    return JsonResponse({'success': True, 'message': 'Cache limpo'})


############################################################################

# NO VIEWS.PY - CORRIGIR A FUNÇÃO editar COMPLETAMENTE:

@login_required
def editar(request, id):
    """Edita um lote existente - VERSÃO CORRIGIDA"""
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. CAPTURA O ESTADO ANTIGO (Para histórico)
                antigo = {
                    'lote': item.lote,
                    'endereco': item.endereco,
                    'empresa': item.empresa or "",
                    'origem_destino': item.origem_destino or "",
                    'peso_unitario': item.peso_unitario,
                    'embalagem': item.embalagem,
                    'az': item.az or "",
                    'observacao': item.observacao or "",
                    'cliente': item.cliente or "",  # NOVO CAMPO
                    'cultivar': item.cultivar.nome if item.cultivar else "",
                    'peneira': item.peneira.nome if item.peneira else "",
                    'categoria': item.categoria.nome if item.categoria else "",
                    'conferente': item.conferente.username,
                    'tratamento': item.tratamento.nome if item.tratamento else "Sem Tratamento",
                    'produto': item.produto or "",  # Campo produto
                }

                # 2. CAPTURA OS NOVOS VALORES
                novo_lote = request.POST.get('lote', '').strip()
                novo_endereco = request.POST.get('endereco', '').strip()
                novo_empresa = request.POST.get('empresa', '').strip()
                novo_origem_destino = request.POST.get('origem_destino', '').strip()
                novo_produto = request.POST.get('produto', '').strip()
                novo_cliente = request.POST.get('cliente', '').strip()  # NOVO CAMPO
                
                # Tratamento do peso
                peso_raw = request.POST.get('peso_unitario', '0')
                try:
                    # Substituir vírgula por ponto
                    peso_raw = str(peso_raw).replace(',', '.')
                    # Se tiver mais de um ponto, pegar apenas o primeiro
                    if peso_raw.count('.') > 1:
                        partes = peso_raw.split('.')
                        peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                    novo_peso = Decimal(peso_raw)
                except (InvalidOperation, ValueError):
                    novo_peso = Decimal('0.00')
                
                novo_emb = request.POST.get('embalagem', 'BAG')
                novo_az = request.POST.get('az', '').strip()
                novo_obs = request.POST.get('observacao', '').strip()
                novo_especie = request.POST.get('especie', 'SOJA').strip()

                # 3. BUSCAR OBJETOS RELACIONADOS
                try:
                    obj_cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
                except:
                    obj_cultivar = item.cultivar
                    
                try:
                    obj_peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
                except:
                    obj_peneira = item.peneira
                    
                try:
                    obj_categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
                except:
                    obj_categoria = item.categoria
                
                # Tratamento é opcional
                tratamento_id = request.POST.get('tratamento')
                if tratamento_id:
                    try:
                        obj_tratamento = get_object_or_404(Tratamento, id=tratamento_id)
                    except:
                        obj_tratamento = item.tratamento
                else:
                    obj_tratamento = None

                # 4. COMPARAÇÃO DETALHADA
                mudancas = []
                
                # Comparar cada campo
                campos_para_comparar = [
                    ('lote', 'Lote', antigo['lote'], novo_lote),
                    ('endereco', 'Endereço', antigo['endereco'], novo_endereco),
                    ('empresa', 'Empresa', antigo['empresa'], novo_empresa),
                    ('origem_destino', 'Origem/Destino', antigo['origem_destino'], novo_origem_destino),
                    ('produto', 'Produto', antigo['produto'], novo_produto),
                    ('cliente', 'Cliente', antigo['cliente'], novo_cliente),  # NOVO
                    ('peso_unitario', 'Peso Unitário', antigo['peso_unitario'], novo_peso),
                    ('embalagem', 'Embalagem', antigo['embalagem'], novo_emb),
                    ('az', 'AZ', antigo['az'], novo_az),
                    ('observacao', 'Observação', antigo['observacao'], novo_obs),
                    ('cultivar', 'Cultivar', antigo['cultivar'], obj_cultivar.nome if obj_cultivar else ''),
                    ('peneira', 'Peneira', antigo['peneira'], obj_peneira.nome if obj_peneira else ''),
                    ('categoria', 'Categoria', antigo['categoria'], obj_categoria.nome if obj_categoria else ''),
                    ('tratamento', 'Tratamento', antigo['tratamento'], obj_tratamento.nome if obj_tratamento else 'Sem Tratamento'),
                ]
                
                for campo_nome, label, valor_antigo, valor_novo in campos_para_comparar:
                    if str(valor_antigo or '') != str(valor_novo or ''):
                        mudancas.append(f"{label}: {valor_antigo} → <b>{valor_novo}</b>")

                # 5. ATUALIZAR O OBJETO
                item.lote = novo_lote
                item.endereco = novo_endereco
                item.empresa = novo_empresa
                item.origem_destino = novo_origem_destino
                item.produto = novo_produto
                item.cliente = novo_cliente  # NOVO
                item.peso_unitario = novo_peso
                item.embalagem = novo_emb
                item.az = novo_az
                item.observacao = novo_obs
                item.especie = novo_especie
                
                item.cultivar = obj_cultivar
                item.peneira = obj_peneira
                item.categoria = obj_categoria
                item.tratamento = obj_tratamento
                item.conferente = request.user
                
                # 6. SALVAR E RECALCULAR
                item.save()  # Isso vai recalcular saldo e peso_total automaticamente

                # 7. REGISTRAR HISTÓRICO
                if mudancas:
                    descricao_html = "<br>".join(mudancas)
                    HistoricoMovimentacao.objects.create(
                        estoque=item,
                        usuario=request.user,
                        tipo='Edição de Lote',
                        descricao=f"<b>EDIÇÃO REALIZADA:</b><br>{descricao_html}"
                    )
                else:
                    HistoricoMovimentacao.objects.create(
                        estoque=item,
                        usuario=request.user,
                        tipo='Edição (Sem mudanças)',
                        descricao="Salvo sem alterações visíveis."
                    )

                messages.success(request, f"✅ Lote {item.lote} atualizado com sucesso!")
                
                # Redirecionar de volta para a lista de estoque
                return redirect('sapp:lista_estoque')
                
        except Exception as e:
            print(f"❌ ERRO NA EDIÇÃO: {e}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            messages.error(request, f"❌ Erro ao editar lote: {str(e)}")
            return redirect('sapp:lista_estoque')
    
    else:
        # GET request - mostrar formulário de edição
        # Vamos redirecionar para a página principal e abrir o modal via JS
        # Na prática, você pode criar uma view separada para o formulário ou usar AJAX
        
        # Para simplificar, vamos redirecionar com uma flag para abrir o modal
        return redirect(f"{reverse('sapp:lista_estoque')}?editar={id}")
    
    
    
@login_required
def excluir_lote(request, id):
    item = get_object_or_404(Estoque, id=id)
    if request.method == 'POST':
        HistoricoMovimentacao.objects.create(
            estoque=None, 
            lote_ref=f"{item.lote} (Excluído)",
            usuario=request.user,
            tipo='EXCLUSÃO',
            descricao=f"Lote <b>{item.lote}</b> do endereço <b>{item.endereco}</b> foi excluído."
        )
        item.delete()
        messages.success(request, "Lote excluído.")
    return redirect('sapp:lista_estoque')



def logout_view(request):
    """
    Realiza o logout e redireciona para o login.
    Aceita POST (padrão recomendado) ou GET se necessário.
    """
    logout(request)
    return redirect('sapp:login')


@login_required
def configuracoes(request):
    config = Configuracao.get_solo()
    # Lista de usuários que NÃO são superusers (Conferentes)
    usuarios_conferentes = User.objects.filter(is_superuser=False)

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'add_conferente_user':
            if not request.user.is_superuser:
                messages.error(request, "Apenas Administradores podem criar usuários.")
            else:
                form = NovoConferenteUserForm(request.POST)
                if form.is_valid():
                    try:
                        u = User.objects.create_user(
                            username=form.cleaned_data['username'], 
                            password='conceito', 
                            first_name=form.cleaned_data['first_name']
                        )
                        messages.success(request, f"Usuário '{u.username}' criado! Senha padrão: conceito")
                    except Exception as e:
                        messages.error(request, f"Erro ao criar usuário: {e}")

        elif acao == 'delete_conferente_user':
             if request.user.is_superuser:
                 try:
                     uid = request.POST.get('id_item')
                     u = User.objects.get(id=uid)
                     if not u.is_superuser: 
                         u.delete()
                         messages.success(request, "Usuário removido.")
                 except: pass

        elif acao == 'config_geral':
             form = ConfiguracaoForm(request.POST, instance=config)
             if form.is_valid(): form.save(); messages.success(request, "Salvo!")
        
        elif acao == 'add_cultivar':
             f = CultivarForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_peneira':
             f = PeneiraForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_categoria':
             f = CategoriaForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_tratamento':
             f = TratamentoForm(request.POST); 
             if f.is_valid(): f.save()
        
        elif acao == 'delete_item':
             tipo = request.POST.get('tipo_item')
             uid = request.POST.get('id_item')
             try:
                 if tipo == 'cultivar': Cultivar.objects.get(id=uid).delete()
                 elif tipo == 'peneira': Peneira.objects.get(id=uid).delete()
                 elif tipo == 'categoria': Categoria.objects.get(id=uid).delete()
                 elif tipo == 'tratamento': Tratamento.objects.get(id=uid).delete()
                 messages.success(request, "Item removido.")
             except: messages.error(request, "Erro ao remover item.")

        return redirect('sapp:configuracoes')

    context = {
        'form_config': ConfiguracaoForm(instance=config),
        'cultivares': Cultivar.objects.all(),
        'peneiras': Peneira.objects.all(),
        'categorias': Categoria.objects.all(),
        'tratamentos': Tratamento.objects.all(),
        'usuarios_conferentes': usuarios_conferentes,
        'form_conf_user': NovoConferenteUserForm(),
    }
    return render(request, 'sapp/configuracoes.html', context)


# views.py - mantenha como estava
@login_required
def historico_geral(request):
    """Histórico completo para DataTables"""
    historico_completo = HistoricoMovimentacao.objects.all().select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')
    
    context = {
        'historico_lista': historico_completo,
    }
    
    return render(request, 'sapp/historico_geral.html', context)





# Adicione isso no TOPO junto com os outros imports


@login_required
def mudar_senha(request):
    if request.method == 'POST':
        form = MudarSenhaForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['nova_senha'])
            request.user.save()
            try:
                # Atualiza perfil se existir
                perfil = request.user.perfil
                perfil.primeiro_acesso = False
                perfil.save()
            except: pass
            
            update_session_auth_hash(request, request.user)
            messages.success(request, "Senha atualizada com sucesso!")
            return redirect('sapp:lista_estoque')
    else:
        form = MudarSenhaForm()
    return render(request, 'sapp/mudar_senha.html', {'form': form})




def exportar_excel(request):
    estoque = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    )
    
    # Criar DataFrame
    data = []
    for item in estoque:
        data.append({
            'Lote': item.lote,
            'Produto': item.produto or '',  # 🔥 NOVO CAMPO
            'Cultivar': item.cultivar.nome,
            'Peneira': item.peneira.nome,
            'Categoria': item.categoria.nome,
            'Endereço': item.endereco,
            'Saldo': item.saldo,
            'Peso Unitário (kg)': float(item.peso_unitario),
            'Peso Total (kg)': float(item.peso_total),
            'Tratamento': item.tratamento.nome if item.tratamento else '',
            'Embalagem': item.get_embalagem_display(),
            'Conferente': item.conferente.first_name,
            'Data Entrada': item.data_entrada.strftime('%d/%m/%Y'),
            'AZ': item.az or '',
            'Origem/Destino': item.origem_destino,
            'Empresa': item.empresa,
            'Espécie': item.especie,
            'Observação': item.observacao or ''
        })
    
    df = pd.DataFrame(data)
    
    # Criar resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="estoque_sementes.xlsx"'
    
    # Exportar para Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Estoque', index=False)
        
        # Formatar a planilha
        workbook = writer.book
        worksheet = writer.sheets['Estoque']
        
        # Ajustar largura das colunas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return response

def exportar_pdf(request):
    estoque = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    )[:100]  # Limitar para não sobrecarregar o PDF
    
    # Criar buffer para o PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Título
    title = Paragraph("RELATÓRIO DE ESTOQUE - SEMENTES", styles['Title'])
    elements.append(title)
    elements.append(Paragraph(f"Data: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph("<br/>", styles['Normal']))
    
    # Dados da tabela ATUALIZADOS
    data = [['Lote', 'Produto', 'Cultivar', 'Peneira', 'Endereço', 'Saldo', 'Peso Total']]  # 🔥 ADICIONADO PRODUTO
    
    for item in estoque:
        data.append([
            item.lote,
            item.produto or '',  # 🔥 NOVO CAMPO
            item.cultivar.nome,
            item.peneira.nome,
            item.endereco,
            str(item.saldo),
            f"{item.peso_total:.2f} kg"
        ])
    
    # Criar tabela
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f8f4e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    
    # Rodapé
    elements.append(Paragraph(f"<br/>Total de itens: {estoque.count()}", styles['Normal']))
    
    # Gerar PDF
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="estoque_sementes.pdf"'
    
    return response

################ DEBUG #####################


@login_required
def debug_estoque_completo(request):
    """Debug COMPLETO do estoque atual"""
    estoque = Estoque.objects.all().select_related('peneira', 'cultivar', 'tratamento', 'categoria')
    
    print("🔍 [DEBUG COMPLETO DO ESTOQUE]")
    print("=" * 80)
    
    for item in estoque:
        print(f"Lote: {item.lote}")
        print(f"  Peneira: '{item.peneira.nome if item.peneira else 'None'}'")
        print(f"  Cultivar: '{item.cultivar.nome if item.cultivar else 'None'}'")
        print(f"  Tratamento: '{item.tratamento.nome if item.tratamento else 'None'}'")
        print(f"  Categoria: '{item.categoria.nome if item.categoria else 'None'}'")
        print(f"  Endereço: '{item.endereco}'")
        print(f"  Saldo: {item.saldo}")
        print("-" * 40)
    
    return JsonResponse({'success': True, 'message': 'Check console for debug info'})

@login_required
def debug_estoque_status(request):
    """Debug para ver status do estoque"""
    total_lotes = Estoque.objects.count()
    lotes_com_saldo = Estoque.objects.filter(saldo__gt=0).count()
    lotes_sem_saldo = Estoque.objects.filter(saldo=0).count()
    
    print("🔍 [DEBUG ESTOQUE STATUS]")
    print(f"📊 Total de lotes: {total_lotes}")
    print(f"✅ Com saldo > 0: {lotes_com_saldo}")
    print(f"❌ Com saldo = 0: {lotes_sem_saldo}")
    
    # Listar alguns lotes com saldo 0
    lotes_zerados = Estoque.objects.filter(saldo=0).values('lote', 'endereco', 'id')[:10]
    print("\n📝 Primeiros 10 lotes com saldo 0:")
    for lote in lotes_zerados:
        print(f"   Lote: {lote['lote']} | Endereço: {lote['endereco']} | ID: {lote['id']}")
    
    return JsonResponse({
        'success': True,
        'total_lotes': total_lotes,
        'com_saldo': lotes_com_saldo,
        'sem_saldo': lotes_sem_saldo
    })
    

################     API    ############################

# ========== APIs para frontend ==========

# No final do views.py
@login_required
def api_buscar_dados_lote(request):
    """API para buscar dados de um lote específico"""
    item_id = request.GET.get('item_id')
    
    if item_id:
        try:
            item = Estoque.objects.get(id=item_id)
            data = {
                'encontrado': True,
                'lote': item.lote,
                'produto': item.produto or '',
                'saldo': item.saldo,
                'az': item.az or '',
                'empresa': item.empresa or '',
                'cliente': item.cliente or '',
                'peso_unitario': str(item.peso_unitario) if item.peso_unitario else '0',
                'embalagem': item.embalagem or 'BAG',
                'especie': item.especie or 'SOJA',
                'observacao': item.observacao or '',
                # IDs para selects
                'cultivar_id': item.cultivar.id if item.cultivar else None,
                'peneira_id': item.peneira.id if item.peneira else None,
                'categoria_id': item.categoria.id if item.categoria else None,
                'tratamento_id': item.tratamento.id if item.tratamento else None,
            }
            return JsonResponse(data)
        except Estoque.DoesNotExist:
            pass
    
    return JsonResponse({'encontrado': False})

@login_required
def api_saldo_lote(request, id):
    """API para obter saldo de um lote específico"""
    try:
        item = get_object_or_404(Estoque, id=id)
        return JsonResponse({
            'success': True,
            'lote': item.lote,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'saida': item.saida,
            'cultivar': item.cultivar.nome if item.cultivar else '',
            'endereco': item.endereco,
            'embalagem': item.embalagem,
            'peso_unitario': float(item.peso_unitario) if item.peso_unitario else 0,
            'peso_total': float(item.peso_total) if item.peso_total else 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_buscar_lotes(request):
    """API para busca de lotes com autocomplete"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    lotes = Estoque.objects.filter(
        Q(lote__icontains=query) |
        Q(cultivar__nome__icontains=query) |
        Q(produto__icontains=query)
    ).filter(saldo__gt=0).values('id', 'lote', 'cultivar__nome', 'saldo', 'endereco')[:10]
    
    results = []
    for lote in lotes:
        results.append({
            'id': lote['id'],
            'lote': lote['lote'],
            'cultivar': lote['cultivar__nome'],
            'saldo': lote['saldo'],
            'endereco': lote['endereco']
        })
    
    return JsonResponse({'results': results})

@login_required
def api_buscar_lote_completo(request):
    """API para buscar todos os dados de um lote existente"""
    lote = request.GET.get('lote', '')
    
    if not lote:
        return JsonResponse({'encontrado': False, 'error': 'Lote não especificado'})
    
    # Buscar o último lote com esse código
    item = Estoque.objects.filter(lote=lote).order_by('-id').first()
    
    if item:
        data = {
            'encontrado': True,
            'lote': item.lote,
            'produto': item.produto or '',
            'cultivar_id': item.cultivar.id if item.cultivar else None,
            'peneira_id': item.peneira.id if item.peneira else None,
            'categoria_id': item.categoria.id if item.categoria else None,
            'tratamento_id': item.tratamento.id if item.tratamento else None,
            'empresa': item.empresa or '',
            'origem_destino': item.origem_destino or '',
            'especie': item.especie or 'SOJA',
            'peso_unitario': str(item.peso_unitario),
            'embalagem': item.embalagem or 'BAG',
            'az': item.az or '',
            'observacao': item.observacao or ''
        }
        return JsonResponse(data)
    
    return JsonResponse({'encontrado': False})

@login_required
def api_verificar_lote(request):
    """API para verificar se um lote existe"""
    lote = request.GET.get('lote', '')
    
    if not lote:
        return JsonResponse({'existe': False})
    
    existe = Estoque.objects.filter(lote=lote).exists()
    
    return JsonResponse({'existe': existe, 'lote': lote})

@login_required
def api_estoque_resumo(request):
    """API para resumo do estoque (usado no dashboard)"""
    total_lotes = Estoque.objects.count()
    lotes_ativos = Estoque.objects.filter(saldo__gt=0).count()
    lotes_esgotados = Estoque.objects.filter(saldo=0).count()
    total_entrada = Estoque.objects.aggregate(total=Sum('entrada'))['total'] or 0
    total_saida = Estoque.objects.aggregate(total=Sum('saida'))['total'] or 0
    
    # Top 5 cultivares
    top_cultivares = Estoque.objects.filter(saldo__gt=0).values(
        'cultivar__nome'
    ).annotate(
        total_saldo=Sum('saldo'),
        total_lotes=Count('id')
    ).order_by('-total_saldo')[:5]
    
    return JsonResponse({
        'success': True,
        'total_lotes': total_lotes,
        'lotes_ativos': lotes_ativos,
        'lotes_esgotados': lotes_esgotados,
        'total_entrada': total_entrada,
        'total_saida': total_saida,
        'top_cultivares': list(top_cultivares)
    })

@login_required
def api_ultimas_movimentacoes(request):
    """API para últimas movimentações"""
    movimentacoes = HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')[:10]
    
    data = []
    for mov in movimentacoes:
        data.append({
            'id': mov.id,
            'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M'),
            'tipo': mov.tipo,
            'descricao': mov.descricao,
            'usuario': mov.usuario.username if mov.usuario else 'Sistema',
            'lote': mov.lote_ref
        })
    
    return JsonResponse({
        'success': True,
        'movimentacoes': data
    })
    
    
    
    
# No sapp/views.py

# --- COLOQUE ISSO NO TOPO DO ARQUIVO SE AINDA NÃO TIVER ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Empenho, EmpenhoStatus, ItemEmpenho, Estoque
from django import forms
import json

# --- VIEW CORRIGIDA (COLE ALINHADA À ESQUERDA) ---
@login_required
def pagina_rascunho(request):
    mensagem = ''
    
    # Definição dos Forms
    class EmpenhoLoteForm(forms.Form):
        lote_id = forms.IntegerField(widget=forms.HiddenInput())
        quantidade = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
        nome_empenho = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
        observacao = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    
    class AcoesEmpenhoForm(forms.Form):
        acao = forms.ChoiceField(
            choices=[('transferir', 'Transferir'), ('expedir', 'Expedir'), ('editar', 'Editar'), ('excluir', 'Excluir')],
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        endereco_destino = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
        confirmar = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    # Lógica POST
    if request.method == 'POST':
        # 1. Empenhar
        if 'empenhar_lote' in request.POST:
            lote_id = request.POST.get('lote_id')
            quantidade = int(request.POST.get('quantidade', 0))
            nome_empenho = request.POST.get('nome_empenho', '').strip()
            observacao = request.POST.get('observacao', '')
            
            try:
                lote = Estoque.objects.get(id=lote_id)
                status_rascunho, _ = EmpenhoStatus.objects.get_or_create(nome='Rascunho')
                empenho, _ = Empenho.objects.get_or_create(
                    usuario=request.user, 
                    status=status_rascunho, 
                    observacao=nome_empenho,
                    defaults={'tipo_movimentacao': 'EXPEDICAO'}
                )
                ItemEmpenho.objects.create(
                    empenho=empenho, estoque=lote, quantidade=quantidade,
                    endereco_origem=lote.endereco, observacao=observacao
                )
                messages.success(request, "Lote empenhado com sucesso!")
                return redirect('sapp:pagina_rascunho')
            except Exception as e:
                messages.error(request, f"Erro: {str(e)}")

        # 2. Excluir (Corrigido para aceitar o POST da mesma página)
        elif 'excluir_empenho' in request.POST:
            empenho_id = request.POST.get('empenho_id')
            try:
                Empenho.objects.filter(id=empenho_id, usuario=request.user).delete()
                messages.success(request, "Empenho excluído!")
                return redirect('sapp:pagina_rascunho')
            except Exception as e:
                messages.error(request, "Erro ao excluir.")

    # Lógica GET (Filtros e Paginação)
    estoque_query = Estoque.objects.filter(saldo__gt=0).order_by('endereco')
    
    filtro_lote = request.GET.get('filtro_lote', '')
    busca = request.GET.get('busca', '')
    
    if filtro_lote: estoque_query = estoque_query.filter(lote__icontains=filtro_lote)
    if busca:
        # Busca por nome de empenho ou dados do lote
        ids_por_empenho = ItemEmpenho.objects.filter(empenho__observacao__icontains=busca).values_list('estoque_id', flat=True)
        estoque_query = estoque_query.filter(Q(lote__icontains=busca) | Q(id__in=ids_por_empenho))

    # Paginação
    paginator = Paginator(estoque_query, int(request.GET.get('page_size', 25)))
    estoque_page = paginator.get_page(request.GET.get('page', 1))

    # Montagem dos dados
    lotes_com_empenho = []
    # Otimização simples para evitar N+1 queries
    itens_empenhados = ItemEmpenho.objects.filter(
        estoque__in=estoque_page, 
        empenho__status__nome='Rascunho'
    ).select_related('empenho')

    for item in estoque_page:
        meus_itens = [i for i in itens_empenhados if i.estoque_id == item.id]
        qtd_emp = sum(i.quantidade for i in meus_itens)
        lotes_com_empenho.append({
            'lote': item,
            'saldo_total': item.saldo,
            'empenhado': qtd_emp,
            'disponivel': item.saldo - qtd_emp,
            'empenhos': meus_itens
        })

    # Contexto
    params = request.GET.copy()
    if 'page' in params: del params['page']
    
    context = {
        'lotes': lotes_com_empenho,
        'estoque': estoque_page,
        'todos_empenhos': Empenho.objects.filter(usuario=request.user, status__nome='Rascunho'),
        'form_empenho': EmpenhoLoteForm(),
        'form_acoes': AcoesEmpenhoForm(),
        'url_filtros': '&' + params.urlencode() if params else '',
        'filtro_lote': filtro_lote,
        'busca': busca,
        'total_lotes': estoque_query.count(),
        'total_saldo': estoque_query.aggregate(Sum('saldo'))['saldo__sum'] or 0,
    }
    

    return render(request, 'sapp/pagina_rascunho.html', context)



# Em sapp/views.py

@login_required
def api_autocomplete_nova_entrada(request):
    """
    Busca lotes pelo termo digitado e retorna TODOS os dados para preenchimento.
    """
    termo = request.GET.get('term', '').strip()
    
    if len(termo) < 2:
        return JsonResponse([], safe=False)
    
    # Busca lotes que contenham o texto digitado
    # Ordena por ID decrescente para pegar os mais recentes primeiro
    qs = Estoque.objects.filter(lote__icontains=termo).values(
        'lote', 'produto', 'cultivar__id', 'peneira__id', 'categoria__id', 
        'tratamento__id', 'empresa', 'origem_destino', 'cliente', 
        'peso_unitario', 'embalagem', 'az', 'especie', 'observacao'
    ).order_by('-id')
    
    # Filtra para não mostrar lotes repetidos na lista
    resultados = []
    lotes_vistos = set()
    
    for item in qs:
        if item['lote'] not in lotes_vistos:
            resultados.append({
                'label': item['lote'],
                'dados': item
            })
            lotes_vistos.add(item['lote'])
        
        if len(resultados) >= 10: # Limita a 10 resultados
            break
            
    return JsonResponse(resultados, safe=False)


