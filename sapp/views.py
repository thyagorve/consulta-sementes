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
from django.core.serializers.json import DjangoJSONEncoder 
# Adicione no topo com os outros imports
import datetime
from django import forms  #
# Python imports
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import random

# App imports
from .models import (
    Estoque, HistoricoMovimentacao, Configuracao, Cultivar, 
    Peneira, Categoria, Tratamento, PerfilUsuario, Especie
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

from django.db import transaction
from .models import FotoMovimentacao # e os outros models   
    

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
    """Consolida lotes duplicados - AGORA CONSIDERA PESO UNITÁRIO"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                from django.db.models import Count
                
                # 🔥 MUDANÇA: Agrupar por lote + produto + endereço + az + peso_unitario
                duplicados = Estoque.objects.values(
                    'lote', 'produto', 'endereco', 'az', 'peso_unitario'  # 🔥 ADICIONADO peso_unitario
                ).annotate(
                    total=Count('id')
                ).filter(total__gt=1)
                
                consolidados_count = 0
                ignorados_count = 0
                
                for dup in duplicados:
                    lote = dup['lote']
                    produto = dup['produto']
                    endereco = dup['endereco']
                    az = dup['az']
                    peso_unitario = dup['peso_unitario']
                    
                    print(f"🔍 Consolidando: {lote} | {produto} | {endereco} | {az} | Peso: {peso_unitario}")
                    
                    # Buscar todos os registros com MESMO PESO
                    registros = Estoque.objects.filter(
                        lote=lote,
                        produto=produto,
                        endereco=endereco,
                        az=az,
                        peso_unitario=peso_unitario  # 🔥 AGORA FILTRA POR PESO
                    ).order_by('id')
                    
                    if registros.count() > 1:
                        # Manter o primeiro e somar os outros (todos com mesmo peso)
                        manter = registros.first()
                        excluir = registros[1:]
                        
                        total_saldo = manter.saldo
                        total_peso_total = manter.peso_total
                        
                        for reg in excluir:
                            print(f"   ➕ Somando: {reg.id} (Saldo: {reg.saldo}, Peso: {reg.peso_unitario})")
                            total_saldo += reg.saldo
                            total_peso_total += reg.peso_total
                            reg.delete()
                        
                        # Atualizar o registro mantido
                        manter.saldo = total_saldo
                        manter.peso_total = total_peso_total
                        manter.save()
                        
                        consolidados_count += 1
                        print(f"✅ Consolidado: {lote} | Saldo total: {total_saldo} | Peso unitário: {peso_unitario}")
                
                # 🔥 VERIFICAR LOTES COM MESMO CÓDIGO MAS PESOS DIFERENTES
                lotes_com_pesos_diferentes = Estoque.objects.values(
                    'lote', 'produto', 'endereco', 'az'
                ).annotate(
                    pesos_diferentes=Count('peso_unitario', distinct=True)
                ).filter(pesos_diferentes__gt=1)
                
                for item in lotes_com_pesos_diferentes:
                    print(f"⚠️ Lote {item['lote']} em {item['endereco']} tem múltiplos pesos - NÃO consolidado")
                    ignorados_count += 1
                
                mensagem = f'{consolidados_count} grupos de lotes consolidados!'
                if ignorados_count > 0:
                    mensagem += f' {ignorados_count} lotes ignorados (possuem pesos diferentes)'
                
                return JsonResponse({
                    'success': True,
                    'message': mensagem,
                    'consolidados': consolidados_count,
                    'ignorados': ignorados_count
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



from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from sapp.models import Estoque, Cultivar, Peneira, Categoria, Tratamento, Especie

@login_required
def lista_estoque(request, template_name='sapp/tabela_estoque.html'):
    """
    View para a página principal de estoque - MOSTRA TODOS OS LOTES
    """
    
    # QuerySet Base - TODOS os lotes (inclusive zerados) PARA EXIBIÇÃO
    qs = Estoque.objects.all().select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente'
    ).order_by('-data_ultima_movimentacao', '-id')
    
    # QuerySet Base para MÉTRICAS - TODOS os lotes
    qs_metrics = Estoque.objects.all()
    
    # FILTRO POR STATUS
    status = request.GET.get('status', 'todos')
    if status == 'disponivel':
        qs = qs.filter(saldo__gt=0)
    elif status == 'esgotado':
        qs = qs.filter(saldo=0)

    # Busca Global
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(especie__nome__icontains=termo) |
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo)
            )

    # Aplicar filtros sequenciais
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }

    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        values = [v for v in values if v.strip()]
        if values:
            qs = qs.filter(**{lookup: values})

    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            qs = qs.filter(**{f'{field}__gte': min_val})
        if max_val:
            qs = qs.filter(**{f'{field}__lte': max_val})

    # MÉTRICAS - Usando o queryset NÃO FILTRADO
    entradas_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('entrada'))['s'] or 0
    entradas_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('entrada'))['s'] or 0
    entradas_total_sc = (entradas_bags * 25) + entradas_sc
    
    saidas_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('saida'))['s'] or 0
    saidas_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('saida'))['s'] or 0
    saidas_total_sc = (saidas_bags * 25) + saidas_sc
    
    saldo_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_total_sc = (saldo_bags * 25) + saldo_sc

    dados_entrada = {'bags': entradas_bags, 'sc': entradas_sc, 'total_sc': entradas_total_sc}
    dados_saida = {'bags': saidas_bags, 'sc': saidas_sc, 'total_sc': saidas_total_sc}
    dados_saldo = {'bags': saldo_bags, 'sc': saldo_sc, 'total_sc': saldo_total_sc}

    # Opções de Filtro
    def get_options_list(field_lookup):
        vals = qs.values_list(field_lookup, flat=True).distinct().order_by(field_lookup)
        return [str(v) for v in vals if v is not None and str(v).strip() != '']

    filter_options = {
        'az': get_options_list('az'),
        'lote': get_options_list('lote'),
        'produto': get_options_list('produto'),
        'cultivar': get_options_list('cultivar__nome'),
        'peneira': get_options_list('peneira__nome'),
        'categoria': get_options_list('categoria__nome'),
        'endereco': get_options_list('endereco'),
        'especie': get_options_list('especie__nome'),
        'tratamento': get_options_list('tratamento__nome'),
        'embalagem': get_options_list('embalagem'),
        'cliente': get_options_list('cliente'),
        'empresa': get_options_list('empresa'),
        'conferente': get_options_list('conferente__username')
    }

    # Paginação
    page_size = request.GET.get('page_size', 25)
    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    total_itens = qs_metrics.count()
    clientes_unicos = qs_metrics.exclude(cliente__isnull=True).exclude(cliente='').values('cliente').distinct().count()

    context = {
        'estoque': page_obj,
        'itens': page_obj,
        'dados_entrada': dados_entrada,
        'dados_saida': dados_saida,
        'dados_saldo': dados_saldo,
        'status': status,
        'busca': busca,
        'total_itens': total_itens,
        'total_sc': saldo_total_sc,
        'total_bags': saldo_bags,
        'total_sc_fisico': saldo_sc,
        'clientes_unicos': clientes_unicos,
        'filter_options': filter_options,
        'url_params': query_params.urlencode(),
        'page_sizes': [10, 25, 50, 100, 200],
        'page_size': page_size,
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
        'all_especies': Especie.objects.all(),
    }
    
    return render(request, template_name, context)


@login_required
def gestao_estoque(request, template_name='sapp/gestao_estoque.html'):
    """
    View para gestão de estoque - MOSTRA APENAS LOTES COM SALDO > 0
    """
    
    # QuerySet Base - APENAS LOTES COM SALDO > 0
    qs = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente'
    ).order_by('-data_ultima_movimentacao', '-id')
    
    # QuerySet Base para MÉTRICAS - TODOS os lotes (para os cards superiores)
    qs_metrics = Estoque.objects.all()
    
    # FILTRO POR STATUS - adaptado para gestão
    status = request.GET.get('status', 'disponivel')
    if status == 'disponivel':
        qs = qs.filter(saldo__gt=0)
    elif status == 'todos':
        qs = Estoque.objects.all().select_related(
            'cultivar', 'peneira', 'categoria', 'tratamento', 'especie', 'conferente'
        ).order_by('-data_ultima_movimentacao', '-id')

    # Busca Global
    busca = request.GET.get('busca', '').strip()
    if busca:
        for termo in busca.split():
            qs = qs.filter(
                Q(lote__icontains=termo) | 
                Q(produto__icontains=termo) |
                Q(cultivar__nome__icontains=termo) | 
                Q(especie__nome__icontains=termo) |
                Q(endereco__icontains=termo) | 
                Q(cliente__icontains=termo) |
                Q(empresa__icontains=termo)
            )

    # Aplicar filtros sequenciais
    filter_map = {
        'az': 'az__in',
        'lote': 'lote__in',
        'produto': 'produto__in',
        'cultivar': 'cultivar__nome__in',
        'peneira': 'peneira__nome__in',
        'categoria': 'categoria__nome__in',
        'endereco': 'endereco__in',
        'especie': 'especie__nome__in',
        'tratamento': 'tratamento__nome__in',
        'embalagem': 'embalagem__in',
        'cliente': 'cliente__in',
        'empresa': 'empresa__in',
        'conferente': 'conferente__username__in'
    }

    for param, lookup in filter_map.items():
        values = request.GET.getlist(param)
        values = [v for v in values if v.strip()]
        if values:
            qs = qs.filter(**{lookup: values})

    # Filtros numéricos
    for field in ['saldo', 'peso_unitario', 'peso_total']:
        min_val = request.GET.get(f'min_{field}')
        max_val = request.GET.get(f'max_{field}')
        if min_val:
            qs = qs.filter(**{f'{field}__gte': min_val})
        if max_val:
            qs = qs.filter(**{f'{field}__lte': max_val})

    # MÉTRICAS - Usando o queryset NÃO FILTRADO (qs_metrics) para os cards
    entradas_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('entrada'))['s'] or 0
    entradas_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('entrada'))['s'] or 0
    entradas_total_sc = (entradas_bags * 25) + entradas_sc
    
    saidas_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('saida'))['s'] or 0
    saidas_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('saida'))['s'] or 0
    saidas_total_sc = (saidas_bags * 25) + saidas_sc
    
    saldo_bags = qs_metrics.filter(embalagem='BAG').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_sc = qs_metrics.filter(embalagem='SC').aggregate(s=Sum('saldo'))['s'] or 0
    saldo_total_sc = (saldo_bags * 25) + saldo_sc

    dados_entrada = {'bags': entradas_bags, 'sc': entradas_sc, 'total_sc': entradas_total_sc}
    dados_saida = {'bags': saidas_bags, 'sc': saidas_sc, 'total_sc': saidas_total_sc}
    dados_saldo = {'bags': saldo_bags, 'sc': saldo_sc, 'total_sc': saldo_total_sc}

    # Opções de Filtro (baseadas no queryset filtrado)
    def get_options_list(field_lookup):
        vals = qs.values_list(field_lookup, flat=True).distinct().order_by(field_lookup)
        return [str(v) for v in vals if v is not None and str(v).strip() != '']

    filter_options = {
        'az': get_options_list('az'),
        'lote': get_options_list('lote'),
        'produto': get_options_list('produto'),
        'cultivar': get_options_list('cultivar__nome'),
        'peneira': get_options_list('peneira__nome'),
        'categoria': get_options_list('categoria__nome'),
        'endereco': get_options_list('endereco'),
        'especie': get_options_list('especie__nome'),
        'tratamento': get_options_list('tratamento__nome'),
        'embalagem': get_options_list('embalagem'),
        'cliente': get_options_list('cliente'),
        'empresa': get_options_list('empresa'),
        'conferente': get_options_list('conferente__username')
    }

    # Paginação
    page_size = request.GET.get('page_size', 25)
    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    total_itens = qs.count()  # Conta apenas itens com saldo > 0
    clientes_unicos = qs.exclude(cliente__isnull=True).exclude(cliente='').values('cliente').distinct().count()

    context = {
        'estoque': page_obj,
        'itens': page_obj,
        'dados_entrada': dados_entrada,
        'dados_saida': dados_saida,
        'dados_saldo': dados_saldo,
        'status': status,
        'busca': busca,
        'total_itens': total_itens,
        'total_sc': saldo_total_sc,
        'total_bags': saldo_bags,
        'total_sc_fisico': saldo_sc,
        'clientes_unicos': clientes_unicos,
        'filter_options': filter_options,
        'url_params': query_params.urlencode(),
        'page_sizes': [10, 25, 50, 100, 200],
        'page_size': page_size,
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
        'all_especies': Especie.objects.all(),
    }
    
    return render(request, template_name, context)
    
    
# No arquivo views.py

@login_required
def registrar_saida(request, id):
    print("🔍 [REGISTRAR SAÍDA] Iniciando processamento da expedição")
    
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Captura de Dados
                qtd = int(request.POST.get('quantidade_saida', 0))
                carga = request.POST.get('numero_carga', '')
                motorista = request.POST.get('motorista', '')
                placa = request.POST.get('placa', '')
                cliente = request.POST.get('cliente', '')
                obs = request.POST.get('observacao', '')
                fotos = request.FILES.getlist('fotos')

                print(f"📦 Dados recebidos:")
                print(f"   Quantidade: {qtd}")
                print(f"   Carga: {carga}")
                print(f"   Motorista: {motorista}")
                print(f"   Placa: {placa}")
                print(f"   Cliente: {cliente}")
                print(f"   Obs: {obs}")
                print(f"   Fotos recebidas: {len(fotos)}")

                # 2. Validação Rigorosa
                erros = []
                if qtd <= 0: 
                    erros.append("❌ Quantidade inválida.")
                if qtd > item.saldo: 
                    erros.append(f"❌ Saldo insuficiente. Disponível: {item.saldo}.")
                if not motorista.strip(): 
                    erros.append("❌ Motorista é obrigatório.")
                if not placa.strip(): 
                    erros.append("❌ Placa é obrigatória.")
                if not carga.strip(): 
                    erros.append("❌ Número da Carga é obrigatório.")
                
                # Fotos são obrigatórias para expedição
                if len(fotos) == 0:
                    erros.append("❌ Pelo menos uma foto é obrigatória na expedição.")
                
                if erros:
                    for e in erros: 
                        print(f"⚠️ {e}")
                        messages.error(request, e)
                    return redirect('sapp:lista_estoque')

                # 3. Salvar estado anterior para histórico
                saldo_anterior = item.saldo
                print(f"💰 Saldo anterior: {saldo_anterior}")

                # 4. Processamento da Saída
                item.saida += qtd
                item.saldo = item.entrada - item.saida
                item.conferente = request.user
                item.data_ultima_saida = timezone.now()
                
                # Atualizar peso total
                if item.peso_unitario and item.peso_unitario > 0:
                    item.peso_total = Decimal(str(item.saldo)) * Decimal(str(item.peso_unitario))
                    item.peso_total = item.peso_total.quantize(Decimal('0.01'))
                
                # Atualizar observação
                obs_historico = f"[EXPEDIÇÃO {timezone.now().strftime('%d/%m/%Y %H:%M')}] Carga: {carga}, Motorista: {motorista}"
                if obs:
                    obs_historico += f" | Obs: {obs}"
                
                if item.observacao:
                    item.observacao += f"\n\n{obs_historico}"
                else:
                    item.observacao = obs_historico
                
                item.save()
                print(f"✅ Item atualizado: {item.lote} | Saldo anterior: {saldo_anterior} → Novo saldo: {item.saldo}")

                # 5. Descrição Rica em HTML para o Histórico
                desc_html = f"""
                    <div class="d-flex flex-column gap-1">
                        <div class="d-flex justify-content-between border-bottom pb-1">
                            <span><strong>Qtd Expedida:</strong> <span class="text-danger">-{qtd}</span></span>
                            <span><strong>Saldo Restante:</strong> {item.saldo}</span>
                        </div>
                        <div class="small text-muted mt-1">
                            <i class="fas fa-truck"></i> <strong>Carga:</strong> {carga} | <strong>Placa:</strong> {placa}<br>
                            <i class="fas fa-id-card"></i> <strong>Motorista:</strong> {motorista}<br>
                            <i class="fas fa-building"></i> <strong>Cliente:</strong> {cliente or 'N/A'}<br>
                            <i class="fas fa-user"></i> <strong>Responsável:</strong> {request.user.get_full_name() or request.user.username}<br>
                            <i class="fas fa-clock"></i> <strong>Data/Hora:</strong> {timezone.now().strftime('%d/%m/%Y %H:%M')}
                        </div>
                        {f'<div class="mt-1 p-1 bg-light rounded small"><strong>Obs:</strong> {obs}</div>' if obs else ''}
                    </div>
                """

                print(f"📝 Criando histórico de movimentação...")

                # 6. Criar histórico de movimentação
                historico = HistoricoMovimentacao.objects.create(
                    estoque=item,
                    usuario=request.user,
                    tipo='Expedição',
                    descricao=desc_html,
                    quantidade=qtd,
                    numero_carga=carga,
                    motorista=motorista,
                    placa=placa,
                    cliente=cliente
                )

                print(f"✅ Histórico criado: ID {historico.id}")

                # 7. **CORREÇÃO CRÍTICA: Salvar Fotos**
                fotos_salvas = 0
                for foto in fotos:
                    try:
                        # CORREÇÃO AQUI: Use o objeto 'historico' diretamente
                        FotoMovimentacao.objects.create(
                            historico=historico,  # Usando o objeto já salvo
                            arquivo=foto,
                            legenda=f"Expedição {carga} - {item.lote} - {timezone.now().strftime('%d/%m/%Y')}"
                        )
                        fotos_salvas += 1
                        print(f"📸 Foto salva: {foto.name} (ID: {historico.id})")
                    except Exception as foto_error:
                        print(f"⚠️ Erro ao salvar foto {foto.name}: {foto_error}")
                        # Não falha a operação por causa de uma foto

                print(f"✅ Fotos salvas: {fotos_salvas}/{len(fotos)}")

                # 8. Mensagem de sucesso
                mensagem_sucesso = f"✅ Expedição da Carga {carga} registrada com sucesso!"
                if fotos_salvas < len(fotos):
                    mensagem_sucesso += f" ({fotos_salvas}/{len(fotos)} fotos salvas)"
                
                messages.success(request, mensagem_sucesso)
                print(f"🎉 Expedição concluída com sucesso!")
                
                # 9. DEBUG: Verificar se fotos foram realmente salvas
                fotos_salvas_query = FotoMovimentacao.objects.filter(historico=historico).count()
                print(f"🔍 DEBUG - Fotos no banco para histórico {historico.id}: {fotos_salvas_query}")

        except Exception as e:
            import traceback
            print(f"💥 ERRO CRÍTICO NA EXPEDIÇÃO:")
            print(f"   Mensagem: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            messages.error(request, f"❌ Erro crítico ao registrar expedição: {str(e)}")
            
    return redirect('sapp:lista_estoque')


@login_required
def transferir(request, id):
    origem = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                qtd = int(request.POST.get('quantidade', 0))
                tipo_transferencia = request.POST.get('tipo_transferencia', 'normal')
                novo_end = request.POST.get('novo_endereco', '').strip().upper()
                
                # === VALIDAÇÕES BÁSICAS (COMUNS A AMBOS OS TIPOS) ===
                if qtd <= 0:
                    messages.error(request, "❌ Quantidade deve ser maior que zero!")
                    return redirect('sapp:lista_estoque')
                
                if qtd > origem.saldo:
                    messages.error(request, f"❌ Saldo insuficiente. Disponível: {origem.saldo}")
                    return redirect('sapp:lista_estoque')
                
                # Validação de endereço apenas para transferência normal
                if tipo_transferencia == 'normal' and not novo_end:
                    messages.error(request, "❌ Novo endereço é obrigatório para transferência normal!")
                    return redirect('sapp:lista_estoque')
                
                # === 1. SEMPRE DAR BAIXA NA ORIGEM ===
                origem.saida += qtd
                origem.save()  # Saldo é recalculado automaticamente no save()
                
                # === 2. PROCESSAMENTO POR TIPO DE TRANSFERÊNCIA ===
                if tipo_transferencia == 'beneficiamento':
                    # ============================================
                    # CASO 1: ENVIO PARA BENEFICIAMENTO
                    # ============================================
                    
                    # Criar histórico de beneficiamento (NÃO cria destino)
                    descricao_beneficiamento = f"Enviado para beneficiamento – Quantidade: {qtd} {origem.embalagem}"
                    if novo_end:
                        descricao_beneficiamento += f" | Destino referência: {novo_end}"
                    
                    historico_beneficiamento = HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        tipo='Beneficiamento',
                        descricao=descricao_beneficiamento
                    )
                    
                    # Salvar fotos no histórico de beneficiamento
                    for f in request.FILES.getlist('fotos'):
                        FotoMovimentacao.objects.create(historico=historico_beneficiamento, arquivo=f)
                    
                    messages.success(
                        request, 
                        f"✅ Lote enviado para beneficiamento! Quantidade baixada: {qtd} {origem.embalagem}"
                    )
                    
                else:  # tipo_transferencia == 'normal'
                    # ============================================
                    # CASO 2: TRANSFERÊNCIA NORMAL (FLUXO ORIGINAL)
                    # ============================================
                    
                    # BUSCAR OBJETOS RELACIONADOS
                    # Espécie
                    novo_especie_id = request.POST.get('especie')
                    if novo_especie_id and novo_especie_id.strip() != '':
                        obj_especie = get_object_or_404(Especie, id=novo_especie_id)
                    else:
                        obj_especie = origem.especie
                    
                    # Cultivar
                    cultivar_id = request.POST.get('cultivar')
                    if cultivar_id and cultivar_id.strip() != '':
                        obj_cultivar = get_object_or_404(Cultivar, id=cultivar_id)
                    else:
                        obj_cultivar = origem.cultivar
                    
                    # Peneira
                    peneira_id = request.POST.get('peneira')
                    if peneira_id and peneira_id.strip() != '':
                        obj_peneira = get_object_or_404(Peneira, id=peneira_id)
                    else:
                        obj_peneira = origem.peneira
                    
                    # Categoria
                    categoria_id = request.POST.get('categoria')
                    if categoria_id and categoria_id.strip() != '':
                        obj_categoria = get_object_or_404(Categoria, id=categoria_id)
                    else:
                        obj_categoria = origem.categoria
                    
                    # Tratamento
                    tratamento_id = request.POST.get('tratamento')
                    if tratamento_id and tratamento_id.strip() != '':
                        obj_tratamento = get_object_or_404(Tratamento, id=tratamento_id)
                    else:
                        obj_tratamento = origem.tratamento
                    
                    # Processar peso unitário
                    peso_raw = request.POST.get('peso_unitario', origem.peso_unitario or '0')
                    try:
                        peso_raw = str(peso_raw).replace(',', '.')
                        if peso_raw.count('.') > 1:
                            partes = peso_raw.split('.')
                            peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                        novo_peso = Decimal(peso_raw).quantize(Decimal('0.01'))
                    except:
                        novo_peso = origem.peso_unitario or Decimal('0.00')
                    
                    # 🔥 CORREÇÃO: Separar os filtros corretamente
                    # Primeiro, montar dicionário com todos os campos EXCETO saldo__gt
                    campos_base = {
                        'lote': origem.lote,
                        'cultivar': obj_cultivar,
                        'especie': obj_especie,
                        'peneira': obj_peneira,
                        'categoria': obj_categoria,
                        'tratamento': obj_tratamento,
                        'embalagem': request.POST.get('embalagem', origem.embalagem),
                        'empresa': request.POST.get('empresa', origem.empresa or ''),
                        'cliente': request.POST.get('cliente', origem.cliente or ''),
                        'endereco': novo_end,
                    }
                    
                    # Buscar registro existente com MESMO PESO
                    destino_existente = Estoque.objects.filter(
                        **campos_base,
                        peso_unitario=novo_peso,
                        saldo__gt=0  # 🔥 AGORA CORRETO: um único argumento saldo__gt
                    ).first()
                    
                    # 🔥 CORREÇÃO: Buscar registro com PESO DIFERENTE
                    destino_peso_diferente = None
                    if not destino_existente:
                        destino_peso_diferente = Estoque.objects.filter(
                            **campos_base,  # Mesmos campos base
                            saldo__gt=0  # 🔥 AGORA CORRETO
                        ).exclude(
                            peso_unitario=novo_peso  # Exclui quem tem o mesmo peso
                        ).first()
                    
                    if destino_existente:
                        # 🔥 CASO 1: MESMO PESO - PODE SOMAR
                        saldo_anterior = destino_existente.saldo
                        destino_existente.entrada += qtd
                        destino_existente.saldo += qtd
                        
                        # Atualizar campos que podem ter mudado
                        destino_existente.peso_unitario = novo_peso  # Mantém o mesmo peso
                        destino_existente.empresa = request.POST.get('empresa', destino_existente.empresa or '')
                        destino_existente.cliente = request.POST.get('cliente', destino_existente.cliente or '')
                        destino_existente.az = request.POST.get('az', destino_existente.az or '')
                        destino_existente.conferente = request.user
                        
                        # Atualizar observação
                        obs_atual = destino_existente.observacao or ''
                        nova_obs = request.POST.get('observacao', '')
                        if nova_obs:
                            if obs_atual:
                                destino_existente.observacao = f"{obs_atual}\n[TRANSFERÊNCIA {timezone.now().strftime('%d/%m %H:%M')}]: {nova_obs}"
                            else:
                                destino_existente.observacao = f"[TRANSFERÊNCIA {timezone.now().strftime('%d/%m %H:%M')}]: {nova_obs}"
                        
                        destino_existente.save()
                        
                        destino = destino_existente
                        mensagem_tipo = f"somado ao registro existente (Saldo anterior: {saldo_anterior}, Peso: {novo_peso} kg)"
                        
                        print(f"✅ Somando ao lote existente com mesmo peso: {origem.lote} | Peso: {novo_peso} kg")
                        
                    elif destino_peso_diferente:
                        # 🔥 CASO 2: PESO DIFERENTE - NÃO SOMA, CRIA NOVO REGISTRO
                        print(f"⚠️ Lote {origem.lote} já existe em {novo_end} com peso DIFERENTE ({destino_peso_diferente.peso_unitario} kg vs {novo_peso} kg)")
                        
                        # Avisar ao usuário
                        messages.warning(
                            request,
                            f"⚠️ Já existe um lote {origem.lote} em {novo_end} com peso {destino_peso_diferente.peso_unitario} kg. "
                            f"Como o peso é diferente ({novo_peso} kg), foi criado um NOVO registro."
                        )
                        
                        # Criar NOVO registro (não somar)
                        destino = Estoque.objects.create(
                            lote=origem.lote,
                            endereco=novo_end,
                            entrada=qtd,
                            saldo=qtd,
                            conferente=request.user,
                            origem_destino=f"Transferência de {origem.endereco}",
                            
                            # Campos de texto com fallback
                            produto=request.POST.get('produto', origem.produto or ''),
                            cliente=request.POST.get('cliente', origem.cliente or ''),
                            empresa=request.POST.get('empresa', origem.empresa or ''),
                            az=request.POST.get('az', origem.az or ''),
                            peso_unitario=novo_peso,  # Peso NOVO
                            embalagem=request.POST.get('embalagem', origem.embalagem),
                            observacao=request.POST.get('observacao', origem.observacao or '') + f" [Peso: {novo_peso} kg - DIFERENTE DO EXISTENTE]",
                            
                            # Foreign Keys (Objetos, não IDs)
                            especie=obj_especie,
                            cultivar=obj_cultivar,
                            peneira=obj_peneira,
                            categoria=obj_categoria,
                            tratamento=obj_tratamento,
                        )
                        mensagem_tipo = f"criado no novo endereço (peso diferente: {novo_peso} kg)"
                        
                    else:
                        # 🔥 CASO 3: NÃO EXISTE - CRIAR NOVO REGISTRO
                        destino = Estoque.objects.create(
                            lote=origem.lote,
                            endereco=novo_end,
                            entrada=qtd,
                            saldo=qtd,
                            conferente=request.user,
                            origem_destino=f"Transferência de {origem.endereco}",
                            
                            # Campos de texto com fallback
                            produto=request.POST.get('produto', origem.produto or ''),
                            cliente=request.POST.get('cliente', origem.cliente or ''),
                            empresa=request.POST.get('empresa', origem.empresa or ''),
                            az=request.POST.get('az', origem.az or ''),
                            peso_unitario=novo_peso,
                            embalagem=request.POST.get('embalagem', origem.embalagem),
                            observacao=request.POST.get('observacao', origem.observacao or ''),
                            
                            # Foreign Keys (Objetos, não IDs)
                            especie=obj_especie,
                            cultivar=obj_cultivar,
                            peneira=obj_peneira,
                            categoria=obj_categoria,
                            tratamento=obj_tratamento,
                        )
                        mensagem_tipo = "criado no novo endereço"
                    
                    # Históricos (Saída da origem)
                    hist_saida = HistoricoMovimentacao.objects.create(
                        estoque=origem,
                        usuario=request.user,
                        tipo='Transferência (Saída)',
                        descricao=f"Transferido para {novo_end} ({destino.lote}) - Quantidade: {qtd} {origem.embalagem} | {mensagem_tipo}"
                    )
                    
                    # Histórico (Entrada no destino)
                    hist_entrada = HistoricoMovimentacao.objects.create(
                        estoque=destino,
                        usuario=request.user,
                        tipo='Transferência (Entrada)',
                        descricao=f"Recebido de {origem.endereco} ({origem.lote}) - Quantidade: {qtd} {origem.embalagem} | Peso: {novo_peso} kg | Novo saldo: {destino.saldo}"
                    )
                    
                    # Salvar fotos na saída (origem)
                    for f in request.FILES.getlist('fotos'):
                        FotoMovimentacao.objects.create(historico=hist_saida, arquivo=f)
                    
                    messages.success(request, f"✅ Transferência concluída! {qtd} unidades {mensagem_tipo} em {novo_end}")
                
        except Exception as e:
            import traceback
            print(f"❌ ERRO NA TRANSFERÊNCIA: {e}")
            print(traceback.format_exc())
            messages.error(request, f"❌ Erro ao transferir: {str(e)}")
            
    return redirect('sapp:lista_estoque')



# No seu views.py
from django.http import JsonResponse

@login_required
def detalhes_estoque_api(request, id):
    """API para retornar dados de um item do estoque"""
    try:
        item = Estoque.objects.get(id=id)
        data = {
            'id': item.id,
            'lote': item.lote,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'produto': item.produto,
            'cliente': item.cliente,
            'empresa': item.empresa,
            'az': item.az,
            'peso_unitario': str(item.peso_unitario) if item.peso_unitario else '',
            'embalagem': item.embalagem,
            'observacao': item.observacao or '',
            'especie_id': item.especie.id if item.especie else '',
            'cultivar_id': item.cultivar.id if item.cultivar else '',
            'peneira_id': item.peneira.id if item.peneira else '',
            'categoria_id': item.categoria.id if item.categoria else '',
            'tratamento_id': item.tratamento.id if item.tratamento else '',
        }
        return JsonResponse(data)
    except Estoque.DoesNotExist:
        return JsonResponse({'error': 'Item não encontrado'}, status=404)

@login_required
def nova_entrada(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = request.POST.get('lote', '').strip()
                endereco = request.POST.get('endereco', '').strip().upper()
                produto = request.POST.get('produto', '').strip()  # 🔥 CAPTURAR PRODUTO
                qtd = int(request.POST.get('entrada', 0))
                
                # Processar peso unitário
                peso_raw = request.POST.get('peso_unitario', '0')
                try:
                    peso_raw = str(peso_raw).replace(',', '.')
                    if peso_raw.count('.') > 1:
                        partes = peso_raw.split('.')
                        peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                    novo_peso = Decimal(peso_raw).quantize(Decimal('0.01'))
                except:
                    novo_peso = Decimal('0.00')
                
                # CORREÇÃO AQUI: Buscar o Objeto Espécie pelo ID
                especie_id = request.POST.get('especie')
                if especie_id:
                    especie_obj = get_object_or_404(Especie, id=especie_id)
                else:
                    # Se não escolheu nada, cria/pega uma padrão 'SOJA'
                    especie_obj, _ = Especie.objects.get_or_create(nome='SOJA')

                # Tratamento de Cultivar/Peneira/Categoria (Obrigatórios)
                cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
                peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
                categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
                
                # Tratamento (Opcional)
                trat_id = request.POST.get('tratamento')
                tratamento = Tratamento.objects.filter(id=trat_id).first() if trat_id else None

                # 🔥 MUDANÇA CRÍTICA: Buscar item existente com MESMO LOTE, ENDEREÇO, PRODUTO, CULTIVAR E PESO
                item = Estoque.objects.filter(
                    lote=lote, 
                    endereco=endereco,
                    produto=produto,  # 🔥 ADICIONADO PRODUTO!
                    cultivar=cultivar,
                    peso_unitario=novo_peso
                ).first()
                
                if item:
                    # SOMA apenas se todos os campos forem iguais (incluindo PRODUTO)
                    item.entrada += qtd
                    item.observacao += f"\n[+ENTRADA {qtd} em {timezone.now().strftime('%d/%m')}]"
                    item.especie = especie_obj
                    msg = "adicionados ao lote existente (mesmo produto e peso)"
                    print(f"✅ Somando ao lote existente: {lote} | Produto: {produto} | Peso: {novo_peso} | Qtd: {qtd}")
                else:
                    # 🔥 Verificar se existe lote com mesmo código mas PRODUTO DIFERENTE
                    item_produto_diferente = Estoque.objects.filter(
                        lote=lote,
                        endereco=endereco,
                        cultivar=cultivar
                    ).exclude(produto=produto).first()
                    
                    if item_produto_diferente:
                        print(f"⚠️ Lote {lote} já existe com produto DIFERENTE ('{item_produto_diferente.produto}' vs '{produto}')")
                        messages.warning(
                            request, 
                            f"⚠️ Lote {lote} já existe no endereço {endereco} com produto '{item_produto_diferente.produto}'. "
                            f"Não foi possível somar (produto diferente). Criado como novo registro."
                        )
                    
                    # 🔥 Verificar se existe lote com mesmo código mas PESO DIFERENTE
                    item_peso_diferente = Estoque.objects.filter(
                        lote=lote,
                        endereco=endereco,
                        produto=produto,
                        cultivar=cultivar
                    ).exclude(peso_unitario=novo_peso).first()
                    
                    if item_peso_diferente:
                        print(f"⚠️ Lote {lote} já existe com peso DIFERENTE ({item_peso_diferente.peso_unitario} kg vs {novo_peso} kg)")
                        messages.warning(
                            request, 
                            f"⚠️ Lote {lote} já existe no endereço {endereco} com peso {item_peso_diferente.peso_unitario} kg. "
                            f"Não foi possível somar (peso diferente). Criado como novo registro."
                        )
                    
                    # CRIAÇÃO DO NOVO LOTE (sempre cria novo quando produto ou peso diferente)
                    item = Estoque(
                        lote=lote, 
                        endereco=endereco, 
                        entrada=qtd, 
                        saldo=qtd,
                        cultivar=cultivar, 
                        peneira=peneira, 
                        categoria=categoria, 
                        tratamento=tratamento,
                        especie=especie_obj,
                        conferente=request.user,
                        produto=produto,  # 🔥 USANDO O PRODUTO CAPTURADO
                        cliente=request.POST.get('cliente', ''),
                        empresa=request.POST.get('empresa', ''),
                        az=request.POST.get('az', ''),
                        origem_destino=request.POST.get('origem_destino', ''),
                        peso_unitario=novo_peso,
                        embalagem=request.POST.get('embalagem', 'BAG'),
                        observacao=request.POST.get('observacao', '')
                    )
                    msg = "criado com sucesso"
                    print(f"🆕 Novo lote criado: {lote} | Produto: {produto} | Peso: {novo_peso}")
                
                item.save()
                
                # Calcular peso total
                if item.peso_unitario and item.peso_unitario > 0:
                    item.peso_total = Decimal(str(item.saldo)) * item.peso_unitario
                    item.peso_total = item.peso_total.quantize(Decimal('0.01'))
                    item.save()
                
                # Histórico e Fotos
                descricao_historico = f"Entrada de {qtd} unidades. ({msg}) | Produto: {produto} | Peso unitário: {novo_peso} kg"
                hist = HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Entrada',
                    descricao=descricao_historico
                )
                
                for f in request.FILES.getlist('fotos'):
                    FotoMovimentacao.objects.create(historico=hist, arquivo=f)
                
                messages.success(request, f"✅ Lote {lote} {msg}! Produto: {produto} | Peso: {novo_peso} kg")
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f"Erro ao processar entrada: {str(e)}")
            
    return redirect('sapp:lista_estoque')



@login_required
def nova_saida(request):
    print("veio aqui na função  nova_saida")
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
                    'cliente': item.cliente or "", 
                    'cultivar': item.cultivar.nome if item.cultivar else "",
                    'peneira': item.peneira.nome if item.peneira else "",
                    'categoria': item.categoria.nome if item.categoria else "",
                    'especie': item.especie.nome if item.especie else "SOJA", # NOVO
                    'tratamento': item.tratamento.nome if item.tratamento else "Sem Tratamento",
                    'produto': item.produto or "", 
                }

                # 2. CAPTURA OS NOVOS VALORES
                novo_lote = request.POST.get('lote', '').strip()
                novo_endereco = request.POST.get('endereco', '').strip().upper() # Padronizar maiúsculo
                novo_empresa = request.POST.get('empresa', '').strip()
                novo_origem_destino = request.POST.get('origem_destino', '').strip()
                novo_produto = request.POST.get('produto', '').strip()
                novo_cliente = request.POST.get('cliente', '').strip()
                
                # Tratamento do peso
                peso_raw = request.POST.get('peso_unitario', '0')
                try:
                    peso_raw = str(peso_raw).replace(',', '.')
                    if peso_raw.count('.') > 1:
                        partes = peso_raw.split('.')
                        peso_raw = f"{partes[0]}.{''.join(partes[1:])}"
                    novo_peso = Decimal(peso_raw)
                except:
                    novo_peso = Decimal('0.00')
                
                novo_emb = request.POST.get('embalagem', 'BAG')
                novo_az = request.POST.get('az', '').strip()
                novo_obs = request.POST.get('observacao', '').strip()

                # 3. BUSCAR OBJETOS RELACIONADOS (CORREÇÃO DE ESPÉCIE AQUI)
                # Espécie (CORREÇÃO)
                novo_especie_id = request.POST.get('especie')
                if novo_especie_id:
                    # Busca o objeto Espécie pelo ID
                    obj_especie = get_object_or_404(Especie, id=novo_especie_id)
                else:
                    obj_especie = item.especie # Mantém o original se não mudar

                # Cultivar
                try:
                    obj_cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
                except:
                    obj_cultivar = item.cultivar
                    
                # Peneira
                try:
                    obj_peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
                except:
                    obj_peneira = item.peneira
                    
                # Categoria
                try:
                    obj_categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
                except:
                    obj_categoria = item.categoria
                
                # Tratamento
                tratamento_id = request.POST.get('tratamento')
                if tratamento_id:
                    try:
                        obj_tratamento = get_object_or_404(Tratamento, id=tratamento_id)
                    except:
                        obj_tratamento = item.tratamento
                else:
                    obj_tratamento = None

                # 4. COMPARAÇÃO DETALHADA PARA O HISTÓRICO
                mudancas = []
                campos_para_comparar = [
                    ('lote', 'Lote', antigo['lote'], novo_lote),
                    ('endereco', 'Endereço', antigo['endereco'], novo_endereco),
                    ('empresa', 'Empresa', antigo['empresa'], novo_empresa),
                    ('origem_destino', 'Origem/Destino', antigo['origem_destino'], novo_origem_destino),
                    ('produto', 'Produto', antigo['produto'], novo_produto),
                    ('cliente', 'Cliente', antigo['cliente'], novo_cliente),
                    ('peso_unitario', 'Peso Unitário', antigo['peso_unitario'], novo_peso),
                    ('embalagem', 'Embalagem', antigo['embalagem'], novo_emb),
                    ('az', 'AZ', antigo['az'], novo_az),
                    ('observacao', 'Observação', antigo['observacao'], novo_obs),
                    ('cultivar', 'Cultivar', antigo['cultivar'], obj_cultivar.nome),
                    ('peneira', 'Peneira', antigo['peneira'], obj_peneira.nome),
                    ('categoria', 'Categoria', antigo['categoria'], obj_categoria.nome),
                    ('especie', 'Espécie', antigo['especie'], obj_especie.nome if obj_especie else '-'), # NOVO
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
                item.cliente = novo_cliente
                item.peso_unitario = novo_peso
                item.embalagem = novo_emb
                item.az = novo_az
                item.observacao = novo_obs
                
                # Atualizando Foreign Keys (Objetos)
                item.cultivar = obj_cultivar
                item.peneira = obj_peneira
                item.categoria = obj_categoria
                item.tratamento = obj_tratamento
                item.especie = obj_especie # AGORA VAI FUNCIONAR (OBJETO)
                
                item.conferente = request.user
                
                # 6. SALVAR E RECALCULAR
                item.save()

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
                
        except Exception as e:
            import traceback
            print(f"❌ ERRO NA EDIÇÃO: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Erro ao editar lote: {str(e)}")
            
    return redirect('sapp:lista_estoque')
    
    
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


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, TratamentoForm
)

# views.py - ARQUIVO COMPLETO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto, Estoque,
    HistoricoMovimentacao, Empenho, ItemEmpenho,
    ArmazemLayout, ElementoMapa
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, 
    TratamentoForm, ProdutoForm, NovaEntradaForm
)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    Configuracao, Cultivar, Peneira, Categoria, 
    Tratamento, Especie, Produto, Estoque
)
from .forms import (
    ConfiguracaoForm, NovoConferenteUserForm,
    CultivarForm, PeneiraForm, CategoriaForm, 
    TratamentoForm, ProdutoForm
)

@login_required
def configuracoes(request):
    config = Configuracao.get_solo()
    usuarios_conferentes = User.objects.filter(is_superuser=False)
    
    produtos = Produto.objects.select_related(
        'cultivar', 'peneira', 'especie', 'categoria', 'tratamento'
    ).all().order_by('-data_cadastro')
    
    cultivares = Cultivar.objects.all().order_by('nome')
    peneiras = Peneira.objects.all().order_by('nome')
    especies = Especie.objects.all().order_by('nome')
    categorias = Categoria.objects.all().order_by('nome')
    tratamentos = Tratamento.objects.all().order_by('nome')

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        # ===== PRODUTOS =====
        if acao == 'add_produto':
            try:
                cultivar_id = request.POST.get('cultivar')
                codigo = request.POST.get('codigo', '').strip().upper()
                descricao = request.POST.get('descricao', '').strip()
                tipo = request.POST.get('tipo', '').strip()
                empresa = request.POST.get('empresa', '').strip()
                
                if not cultivar_id or not codigo or not descricao:
                    messages.error(request, "❌ Cultivar, Código e Descrição são obrigatórios!")
                elif Produto.objects.filter(codigo=codigo).exists():
                    messages.error(request, f"❌ Código '{codigo}' já existe!")
                else:
                    produto = Produto.objects.create(
                        cultivar_id=cultivar_id,
                        codigo=codigo,
                        descricao=descricao,
                        tipo=tipo if tipo else None,
                        empresa=empresa if empresa else None,
                        ativo=request.POST.get('ativo') == 'on'
                    )
                    
                    if request.POST.get('peneira'):
                        produto.peneira_id = request.POST.get('peneira')
                    if request.POST.get('especie'):
                        produto.especie_id = request.POST.get('especie')
                    if request.POST.get('categoria'):
                        produto.categoria_id = request.POST.get('categoria')
                    if request.POST.get('tratamento'):
                        produto.tratamento_id = request.POST.get('tratamento')
                    
                    produto.save()
                    messages.success(request, f"✅ Produto '{produto.codigo}' cadastrado com sucesso!")
                    
            except Exception as e:
                messages.error(request, f"❌ Erro ao cadastrar produto: {str(e)}")
        
        elif acao == 'delete_produto':
            try:
                produto_id = request.POST.get('id_item')
                produto = Produto.objects.get(id=produto_id)
                produto_codigo = produto.codigo
                produto.delete()
                messages.success(request, f"✅ Produto '{produto_codigo}' excluído!")
            except Produto.DoesNotExist:
                messages.error(request, "❌ Produto não encontrado!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao excluir: {str(e)}")
        
        # ===== USUÁRIOS =====
        elif acao == 'add_conferente_user':
            if not request.user.is_superuser:
                messages.error(request, "❌ Apenas Administradores podem criar usuários.")
            else:
                username = request.POST.get('username', '').strip()
                first_name = request.POST.get('first_name', '').strip()
                
                if not username or not first_name:
                    messages.error(request, "❌ Usuário e nome são obrigatórios!")
                elif User.objects.filter(username=username).exists():
                    messages.error(request, f"❌ Usuário '{username}' já existe!")
                else:
                    try:
                        u = User.objects.create_user(
                            username=username,
                            password='conceito',
                            first_name=first_name
                        )
                        messages.success(request, f"✅ Usuário '{u.username}' criado! Senha: conceito")
                    except Exception as e:
                        messages.error(request, f"❌ Erro ao criar usuário: {e}")

        elif acao == 'delete_conferente_user':
            if request.user.is_superuser:
                try:
                    uid = request.POST.get('id_item')
                    u = User.objects.get(id=uid)
                    if not u.is_superuser: 
                        u.delete()
                        messages.success(request, "✅ Usuário removido.")
                except:
                    messages.error(request, "❌ Erro ao remover usuário.")
        
        # ===== CONFIGURAÇÃO GERAL =====
        elif acao == 'config_geral':
            form = ConfiguracaoForm(request.POST, instance=config)
            if form.is_valid(): 
                form.save()
                messages.success(request, "✅ Configurações salvas!")
        
        # ===== CADASTROS AUXILIARES =====
        elif acao == 'add_cultivar':
            nome = request.POST.get('nome', '').strip()
            if nome:
                if not Cultivar.objects.filter(nome__iexact=nome).exists():
                    Cultivar.objects.create(nome=nome)
                    messages.success(request, f"✅ Cultivar '{nome}' adicionado!")
                else:
                    messages.warning(request, f"⚠️ Cultivar '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome do cultivar é obrigatório.")
        
        elif acao == 'add_especie':
            nome = request.POST.get('nome', '').strip().upper()
            if nome:
                if not Especie.objects.filter(nome__iexact=nome).exists():
                    Especie.objects.create(nome=nome)
                    messages.success(request, f"✅ Espécie '{nome}' adicionada!")
                else:
                    messages.warning(request, f"⚠️ Espécie '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome da espécie é obrigatório.")
        
        elif acao == 'add_peneira':
            nome = request.POST.get('nome', '').strip()
            if nome:
                if not Peneira.objects.filter(nome__iexact=nome).exists():
                    Peneira.objects.create(nome=nome)
                    messages.success(request, f"✅ Peneira '{nome}' adicionada!")
                else:
                    messages.warning(request, f"⚠️ Peneira '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome da peneira é obrigatório.")
        
        elif acao == 'add_categoria':
            nome = request.POST.get('nome', '').strip()
            if nome:
                if not Categoria.objects.filter(nome__iexact=nome).exists():
                    Categoria.objects.create(nome=nome)
                    messages.success(request, f"✅ Categoria '{nome}' adicionada!")
                else:
                    messages.warning(request, f"⚠️ Categoria '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome da categoria é obrigatório.")
        
        elif acao == 'add_tratamento':
            nome = request.POST.get('nome', '').strip()
            if nome:
                if not Tratamento.objects.filter(nome__iexact=nome).exists():
                    Tratamento.objects.create(nome=nome)
                    messages.success(request, f"✅ Tratamento '{nome}' adicionado!")
                else:
                    messages.warning(request, f"⚠️ Tratamento '{nome}' já existe!")
            else:
                messages.error(request, "❌ Nome do tratamento é obrigatório.")
        
        # ===== EXCLUSÃO DE ITENS =====
        elif acao == 'delete_item':
            tipo = request.POST.get('tipo_item')
            item_id = request.POST.get('id_item')
            
            try:
                if tipo == 'cultivar':
                    item = Cultivar.objects.get(id=item_id)
                    nome = item.nome
                    item.delete()
                    messages.success(request, f"✅ Cultivar '{nome}' removido!")
                elif tipo == 'especie':
                    item = Especie.objects.get(id=item_id)
                    nome = item.nome
                    item.delete()
                    messages.success(request, f"✅ Espécie '{nome}' removida!")
                elif tipo == 'peneira':
                    item = Peneira.objects.get(id=item_id)
                    nome = item.nome
                    item.delete()
                    messages.success(request, f"✅ Peneira '{nome}' removida!")
                elif tipo == 'categoria':
                    item = Categoria.objects.get(id=item_id)
                    nome = item.nome
                    item.delete()
                    messages.success(request, f"✅ Categoria '{nome}' removida!")
                elif tipo == 'tratamento':
                    item = Tratamento.objects.get(id=item_id)
                    nome = item.nome
                    item.delete()
                    messages.success(request, f"✅ Tratamento '{nome}' removido!")
                else:
                    messages.error(request, "❌ Tipo de item inválido!")
                    
            except Exception as e:
                messages.error(request, f"❌ Erro ao remover item: {str(e)}")

        return redirect('sapp:configuracoes')

    context = {
        'form_config': ConfiguracaoForm(instance=config),
        'cultivares': cultivares,
        'especies': especies,
        'peneiras': peneiras,
        'categorias': categorias,
        'tratamentos': tratamentos,
        'usuarios_conferentes': usuarios_conferentes,
        'form_conf_user': NovoConferenteUserForm(),
        'produtos': produtos,
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
    
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Q

from .models import (
    Estoque,
    Empenho,
    ItemEmpenho,
    EmpenhoStatus,
    HistoricoMovimentacao
)


@login_required
def pagina_rascunho(request):
    user = request.user
    MARCA_ORIGEM = "[REP]"

    # =====================================================
    # POST (AÇÕES)
    # =====================================================
    if request.method == 'POST':

        # -------------------------
        # EXCLUIR CARD
        # -------------------------
        if 'excluir_card' in request.POST:
            Empenho.objects.filter(
                id=request.POST.get('empenho_id'),
                usuario=user
            ).delete()
            messages.success(request, "Card excluído com sucesso.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # EXCLUIR ITEM DO CARD
        # -------------------------
        if 'excluir_item' in request.POST:
            ItemEmpenho.objects.filter(
                id=request.POST.get('item_id'),
                empenho__usuario=user
            ).delete()
            messages.success(request, "Item removido do rascunho.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # ADICIONAR AO RASCUNHO
        # -------------------------
        if 'empenhar_lote' in request.POST:
            lote_id = request.POST.get('lote_id')
            qtd = int(request.POST.get('quantidade', 0))
            nome_card = request.POST.get('nome_empenho', '').strip().upper()

            lote = get_object_or_404(Estoque, id=lote_id)

            if qtd <= 0:
                messages.error(request, "Quantidade inválida.")
                return redirect('sapp:pagina_rascunho')

            ja_empenhado = (
                ItemEmpenho.objects
                .filter(empenho__usuario=user, estoque=lote)
                .aggregate(total=models.Sum('quantidade'))['total'] or 0
            )

            if ja_empenhado + qtd > lote.saldo:
                messages.error(
                    request,
                    f"Saldo insuficiente. Disponível: {lote.saldo}. "
                    f"Já empenhado: {ja_empenhado}."
                )
                return redirect('sapp:pagina_rascunho')

            status, _ = EmpenhoStatus.objects.get_or_create(
                id=1, defaults={'nome': 'Rascunho'}
            )

            empenho, _ = Empenho.objects.get_or_create(
                usuario=user,
                observacao=nome_card,
                status=status
            )

            item, _ = ItemEmpenho.objects.get_or_create(
                empenho=empenho,
                estoque=lote,
                defaults={'quantidade': 0}
            )

            item.quantidade += qtd
            item.save()

            messages.success(request, "Lote adicionado ao rascunho.")
            return redirect('sapp:pagina_rascunho')

        # -------------------------
        # TRANSFERIR / EXPEDIR EM MASSA
        # -------------------------
        if request.POST.get('origem_acao') == 'cards':
            acao = request.POST.get('acao_tipo')
            empenho_id = request.POST.get('empenho_id')
            obs_global = request.POST.get('obs_global', '').strip()

            try:
                with transaction.atomic():

                    empenho = get_object_or_404(
                        Empenho, id=empenho_id, usuario=user
                    )

                    # 🔒 BLOQUEIO DE CONCORRÊNCIA + VALIDAÇÃO FINAL
                    itens = (
                        empenho.itens
                        .select_related('estoque')
                        .select_for_update()
                    )

                    for item in itens:
                        item.estoque.refresh_from_db()
                        if item.quantidade > item.estoque.saldo:
                            raise Exception(
                                f"Lote {item.estoque.lote} tem apenas "
                                f"{item.estoque.saldo} disponível "
                                f"(solicitado {item.quantidade})."
                            )

                    for item in itens:
                        origem = item.estoque
                        qtd = item.quantidade

                        # =====================
                        # TRANSFERÊNCIA
                        # =====================
                        if acao == 'transferir':
                            novo_end = request.POST.get('novo_endereco', '').strip().upper()
                            novo_az = request.POST.get('az', '').strip().upper() or origem.az

                            if not novo_end:
                                raise Exception("Novo endereço não informado.")

                            destino = Estoque.objects.filter(
                                lote=origem.lote,
                                produto=origem.produto,
                                cultivar=origem.cultivar,
                                peneira=origem.peneira,
                                categoria=origem.categoria,
                                tratamento=origem.tratamento,
                                especie=origem.especie,
                                endereco=novo_end,
                                az=novo_az,
                                empresa=origem.empresa,
                                embalagem=origem.embalagem
                            ).first()

                            if destino:
                                destino.entrada += qtd
                                destino.save()
                            else:
                                destino = Estoque.objects.create(
                                    lote=origem.lote,
                                    produto=origem.produto,
                                    cultivar=origem.cultivar,
                                    peneira=origem.peneira,
                                    categoria=origem.categoria,
                                    tratamento=origem.tratamento,
                                    especie=origem.especie,
                                    endereco=novo_end,
                                    az=novo_az,
                                    entrada=qtd,
                                    peso_unitario=origem.peso_unitario,
                                    embalagem=origem.embalagem,
                                    conferente=user,
                                    empresa=origem.empresa,
                                    cliente=origem.cliente,
                                    observacao=f"{MARCA_ORIGEM} {obs_global}"
                                )

                            origem.saida += qtd
                            origem.save()
                            HistoricoMovimentacao.objects.create(
                                estoque=origem,
                                usuario=user,
                                quantidade=qtd,  # <--- ADICIONADO
                                tipo='Transferência (Saída)',
                                descricao=f"{MARCA_ORIGEM} Transferido {qtd} un para {novo_end}."
                            )

                            HistoricoMovimentacao.objects.create(
                                estoque=destino,
                                usuario=user,
                                quantidade=qtd,  # <--- ADICIONADO
                                tipo='Transferência (Entrada)',
                                descricao=f"{MARCA_ORIGEM} Recebido {qtd} un de {origem.endereco}."
                            )

                            # 2. EXPEDIÇÃO (Correção: adicionar quantidade=qtd)
                        elif acao == 'expedir':
                                origem.saida += qtd
                                origem.save()

                                HistoricoMovimentacao.objects.create(
                                    estoque=origem,
                                    usuario=user,
                                    quantidade=qtd,  # <--- ADICIONADO
                                    tipo='Expedição',
                                    descricao=f"{MARCA_ORIGEM} Expedido {qtd} un. {obs_global}",
                                    numero_carga=request.POST.get('numero_carga'),
                                    cliente=request.POST.get('cliente'),
                                    placa=request.POST.get('placa')
                                )

                    empenho.delete()
                    messages.success(request, "Ação em lote realizada com sucesso.")

            except Exception as e:
                messages.error(request, f"Erro ao processar: {str(e)}")

            return redirect('sapp:pagina_rascunho')

    # =====================================================
    # GET (DADOS)
    # =====================================================
    ids_rascunhos = ItemEmpenho.objects.filter(
        empenho__usuario=user
    ).values_list('estoque_id', flat=True)

    estoque_qs = (
        Estoque.objects
        .filter(Q(saldo__gt=0) | Q(id__in=ids_rascunhos))
        .select_related('cultivar', 'peneira', 'categoria', 'tratamento', 'especie')
        .order_by('lote', 'endereco')
    )

    todos_itens = (
        ItemEmpenho.objects
        .filter(empenho__usuario=user)
        .select_related('empenho')
    )

    lotes_contexto = []

    for lote in estoque_qs:
        itens = [i for i in todos_itens if i.estoque_id == lote.id]
        empenhado = sum(i.quantidade for i in itens)

        for i in itens:
            i.inconsistente = i.quantidade > lote.saldo

        lotes_contexto.append({
            'lote': lote,
            'empenhado': empenhado,
            'disponivel': lote.saldo - empenhado,
            'itens_empenho': itens,
            'tem_inconsistencia': any(i.inconsistente for i in itens)
        })

    cards = (
        Empenho.objects
        .filter(usuario=user, status__id=1)
        .prefetch_related('itens', 'itens__estoque')
    )

    return render(request, 'sapp/pagina_rascunho.html', {
        'lotes': lotes_contexto,
        'cards': cards,
    })


@login_required
def api_buscar_dados_lote(request):
    """API única e robusta para buscar dados do lote para edição ou transferência"""
    item_id = request.GET.get('item_id')
    
    try:
        # Buscamos o item com todos os relacionamentos para evitar múltiplas consultas
        item = Estoque.objects.select_related(
            'cultivar', 'peneira', 'categoria', 'tratamento', 'especie'
        ).get(id=item_id)
        
        # O segredo é enviar os IDs brutos para os Selects e os valores formatados para os inputs de texto
        data = {
            'encontrado': True,
            'id': item.id,
            'lote': item.lote,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'entrada': item.entrada,
            'produto': item.produto or '',
            'cliente': item.cliente or '',
            'empresa': item.empresa or '',
            'az': item.az or '',
            'peso_unitario': str(item.peso_unitario).replace(',', '.') if item.peso_unitario else '0.00',
            'embalagem': item.embalagem,
            'observacao': item.observacao or '',
            
            # IDs essenciais para os campos <select> do modal
            'especie_id': item.especie.id if item.especie else '',
            'cultivar_id': item.cultivar.id if item.cultivar else '',
            'peneira_id': item.peneira.id if item.peneira else '',
            'categoria_id': item.categoria.id if item.categoria else '',
            'tratamento_id': item.tratamento.id if item.tratamento else '',
        }
        return JsonResponse(data)
    except Estoque.DoesNotExist:
        return JsonResponse({'encontrado': False, 'erro': 'Lote não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'encontrado': False, 'erro': str(e)}, status=500)


@login_required
def api_itens_empenhos(request):
    """API para buscar itens dos empenhos selecionados"""
    empenhos_ids = request.GET.get('empenhos_ids', '')
    
    if not empenhos_ids:
        return JsonResponse({'itens': []})
    
    ids_list = [int(id) for id in empenhos_ids.split(',') if id.isdigit()]
    
    itens = ItemEmpenho.objects.filter(
        empenho_id__in=ids_list,
        empenho__usuario=request.user
    ).select_related('estoque', 'empenho')
    
    itens_data = []
    for item in itens:
        itens_data.append({
            'lote': item.estoque.lote,
            'quantidade': item.quantidade,
            'empenho': item.empenho.observacao,
            'endereco': item.estoque.endereco
        })
    
    return JsonResponse({
        'itens': itens_data,
        'total': len(itens_data)
    })
    
    
    
@login_required
def api_autocomplete_nova_entrada(request):
    """
    Busca lotes pelo termo digitado e retorna TODOS os dados para preenchimento.
    """
    termo = request.GET.get('term', '').strip()
    
    if len(termo) < 2:
        return JsonResponse([], safe=False)
    
    # Busca lotes que contenham o texto digitado
    qs = Estoque.objects.filter(lote__icontains=termo).select_related(
        'especie', 'cultivar', 'peneira', 'categoria', 'tratamento'
    ).order_by('-id')
    
    resultados = []
    lotes_vistos = set()
    
    for item in qs:
        if item.lote not in lotes_vistos:
            # Prepara os dados manualmente para evitar erro de serialização
            dados_item = {
                'lote': item.lote,
                'produto': item.produto or '',
                'cultivar__id': item.cultivar.id if item.cultivar else None,
                'peneira__id': item.peneira.id if item.peneira else None,
                'categoria__id': item.categoria.id if item.categoria else None,
                'tratamento__id': item.tratamento.id if item.tratamento else None,
                
                # --- CORREÇÃO AQUI ---
                'especie__id': item.especie.id if item.especie else None,
                
                'empresa': item.empresa or '',
                'origem_destino': item.origem_destino or '',
                'cliente': item.cliente or '',
                'peso_unitario': str(item.peso_unitario),
                'embalagem': item.embalagem,
                'az': item.az or '',
                'observacao': item.observacao or ''
            }

            resultados.append({
                'label': item.lote,
                'dados': dados_item
            })
            lotes_vistos.add(item.lote)
        
        if len(resultados) >= 10: 
            break
            
    return JsonResponse(resultados, safe=False)

















from django.contrib.admin.views.decorators import staff_member_required 





@staff_member_required
def api_status_enderecos(request):
    enderecos = MapeamentoEndereco.objects.filter(ativo=True)
    resultado = {}
    
    for mapa in enderecos:
        tem_saldo = Estoque.objects.filter(
            endereco=mapa.endereco, 
            saldo__gt=0
        ).exists()
        
        resultado[mapa.endereco] = {
            'tem_saldo': tem_saldo,
            'cor_padrao': mapa.cor_padrao,
            'cor_positivo': mapa.cor_positivo
        }
    
    return JsonResponse(resultado)

    










# sapp/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ArmazemLayout, ElementoMapa, Estoque
import json


# ============================================================================
# APIs PARA O CANVAS (ADMIN APENAS)
# ============================================================================




def verificar_estoque_endereco(request, endereco):
    """API para verificar se existe estoque em um endereço"""
    if request.method == 'GET':
        try:
            # Decodifica o endereço (pode ter espaços ou caracteres especiais)
            endereco_decodificado = endereco
            
            # Verifica se há estoque
            tem_estoque = Estoque.objects.filter(
                endereco__iexact=endereco_decodificado,
                saldo__gt=0
            ).exists()
            
            # Verifica se existe cadastro (mesmo com saldo zero)
            existe_cadastro = Estoque.objects.filter(
                endereco__iexact=endereco_decodificado
            ).exists()
            
            return JsonResponse({
                'success': True,
                'endereco': endereco_decodificado,
                'tem_estoque': tem_estoque,
                'existe_cadastro': existe_cadastro,
                'mensagem': f'Endereço {endereco_decodificado} tem estoque' if tem_estoque else f'Endereço {endereco_decodificado} está vazio'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e),
                'endereco': endereco
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})



def exportar_mapa_json(request, armazem_numero):
    """Exporta o layout do mapa como JSON"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Acesso negado'}, status=403)
    
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero)
    elementos = armazem.elementos.all().order_by('ordem_z')
    
    dados = {
        'armazem': {
            'id': armazem.id,
            'numero': armazem.numero,
            'nome': armazem.nome,
            'largura_canvas': armazem.largura_canvas,
            'altura_canvas': armazem.altura_canvas,
        },
        'elementos': [
            {
                'id': elem.id,
                'tipo': elem.tipo,
                'pos_x': elem.pos_x,
                'pos_y': elem.pos_y,
                'largura': elem.largura,
                'altura': elem.altura,
                'cor_preenchimento': elem.cor_preenchimento,
                'cor_borda': elem.cor_borda,
                'espessura_borda': elem.espessura_borda,
                'conteudo_texto': elem.conteudo_texto,
                'fonte_nome': elem.fonte_nome,
                'fonte_tamanho': elem.fonte_tamanho,
                'texto_negrito': elem.texto_negrito,
                'texto_italico': elem.texto_italico,
                'texto_direcao': elem.texto_direcao,
                'linha_tipo': elem.linha_tipo,
                'identificador': elem.identificador,
                'ordem_z': elem.ordem_z,
            }
            for elem in elementos
        ],
        'total_elementos': elementos.count(),
        'exportado_em': timezone.now().isoformat()
    }
    
    return JsonResponse(dados, json_dumps_params={'indent': 2})

@staff_member_required
@csrf_exempt
def importar_mapa_json(request, armazem_numero):
    """Importa layout do mapa a partir de JSON"""
    if request.method == 'POST':
        try:
            armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero)
            data = json.loads(request.body)
            
            # Limpa elementos existentes
            ElementoMapa.objects.filter(armazem=armazem).delete()
            
            # Cria novos elementos
            elementos_criados = []
            for idx, elem_data in enumerate(data.get('elementos', [])):
                elemento = ElementoMapa.objects.create(
                    armazem=armazem,
                    tipo=elem_data.get('tipo', 'RETANGULO'),
                    pos_x=elem_data.get('pos_x', 0),
                    pos_y=elem_data.get('pos_y', 0),
                    largura=elem_data.get('largura', 100),
                    altura=elem_data.get('altura', 60),
                    cor_preenchimento=elem_data.get('cor_preenchimento', '#CCCCCC'),
                    cor_borda=elem_data.get('cor_borda', '#000000'),
                    espessura_borda=elem_data.get('espessura_borda', 2),
                    conteudo_texto=elem_data.get('conteudo_texto', ''),
                    fonte_nome=elem_data.get('fonte_nome', 'Arial'),
                    fonte_tamanho=elem_data.get('fonte_tamanho', 14),
                    texto_negrito=elem_data.get('texto_negrito', False),
                    texto_italico=elem_data.get('texto_italico', False),
                    texto_direcao=elem_data.get('texto_direcao', 'horizontal'),
                    linha_tipo=elem_data.get('linha_tipo', 'solida'),
                    identificador=elem_data.get('identificador', ''),
                    ordem_z=elem_data.get('ordem_z', idx + 1),
                )
                elementos_criados.append(elemento.id)
            
            return JsonResponse({
                'success': True,
                'message': f'Mapa importado com sucesso! {len(elementos_criados)} elementos criados.',
                'armazem': armazem.numero,
                'total_elementos': len(elementos_criados)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

# ============================================================================
# VIEW DE FALLBACK (para compatibilidade)
# ============================================================================




# sapp/views.py
def lista_armazens(request):
    """Lista todos os armazéns disponíveis"""
    armazens = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazens': armazens,
        'is_admin': request.user.is_staff,
        'titulo_pagina': 'Mapas dos Armazéns'
    }
    return render(request, 'sapp/lista_armazens.html', context)




@staff_member_required
def criar_armazem(request):
    """Cria um novo AZ e redireciona para o editor dele"""
    if request.method == 'POST':
        numero = request.POST.get('numero')
        nome = request.POST.get('nome')
        largura = request.POST.get('largura_canvas', 1200)
        altura = request.POST.get('altura_canvas', 800)
        
        novo_az = ArmazemLayout.objects.create(
            numero=numero,
            nome=nome,
            largura_canvas=largura,
            altura_canvas=altura
        )
        messages.success(request, f"Armazém {novo_az.numero} criado com sucesso!")
        return redirect('sapp:editor_avancado', armazem_numero=novo_az.numero)
    return redirect('sapp:lista_armazens')

@staff_member_required
def editar_config_armazem(request, armazem_id):
    """Edita as configurações (tamanho/nome) de um AZ existente"""
    if request.method == 'POST':
        armazem = get_object_or_404(ArmazemLayout, id=armazem_id)
        armazem.numero = request.POST.get('numero')
        armazem.nome = request.POST.get('nome')
        armazem.largura_canvas = request.POST.get('largura_canvas')
        armazem.altura_canvas = request.POST.get('altura_canvas')
        armazem.save()
        
        messages.success(request, "Configurações do mapa atualizadas!")
        return redirect('sapp:editor_avancado', armazem_numero=armazem.numero)
    return redirect('sapp:lista_armazens')


# sapp/views.py - ADICIONE/MODIFIQUE ESTAS FUNÇÕES

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import ArmazemLayout, ElementoMapa, Estoque
import json
from django.utils import timezone

# ============================================================================
# EDITOR DE MAPA (ADMIN)
# ============================================================================





# No arquivo sapp/views.py

@login_required
def mapa_ocupacao_canvas(request, armazem_numero=1):
    # 1. Busca Armazém e Elementos
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero, ativo=True)
    elementos_db = armazem.elementos.all().order_by('ordem_z')
    armazens_disponiveis = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    # 2. Busca Estoque com Saldo > 0
    itens_estoque = Estoque.objects.filter(saldo__gt=0)

    # 3. Mapeia Estoque (Normalizando Endereço: Tira espaços e põe Maiúsculo)
    dados_ocupacao = {}
    
    for item in itens_estoque:
        if item.endereco:
            # A MÁGICA: .strip().upper() garante que " a-01" seja igual a "A-01"
            chave = item.endereco.strip().upper()
            
            if chave not in dados_ocupacao:
                dados_ocupacao[chave] = []
            
            dados_ocupacao[chave].append({
                'lote': item.lote,
                'produto': str(item.produto or 'S/ Produto'),
                'qtd': float(item.saldo),
                'embalagem': str(item.embalagem),
                'cliente': str(item.cliente or '-')
            })

    # 4. Prepara Elementos para o Mapa (Já definindo a cor aqui)
    elementos_render = []
    
    for el in elementos_db:
        # Dados básicos
        item_dict = {
            'tipo': el.tipo,
            'x': el.pos_x, 'y': el.pos_y, 'w': el.largura, 'h': el.altura, 'rot': el.rotacao,
            'texto': el.conteudo_texto,
            'id': el.identificador
        }

        # SE FOR RETÂNGULO: Verifica se deve pintar
        if el.tipo == 'RETANGULO' and el.identificador:
            chave_mapa = el.identificador.strip().upper() # Normaliza também
            
            if chave_mapa in dados_ocupacao:
                # TEM ESTOQUE -> VERDE
                item_dict['cor'] = '#10b981' 
                item_dict['stroke'] = '#065f46'
                item_dict['ocupado'] = True
            else:
                # VAZIO -> CINZA (Ou a cor que você escolheu no editor)
                item_dict['cor'] = el.cor_preenchimento or '#f3f4f6'
                item_dict['stroke'] = el.cor_borda or '#9ca3af'
                item_dict['ocupado'] = False
        else:
            # TEXTOS e LINHAS -> Cor original
            item_dict['cor'] = el.cor_preenchimento
            item_dict['stroke'] = el.cor_borda
            item_dict['ocupado'] = False

        elementos_render.append(item_dict)

    # 5. Renderiza
    context = {
        'armazem': armazem,
        'armazens_disponiveis': armazens_disponiveis,
        'elementos_json': json.dumps(elementos_render, cls=DjangoJSONEncoder),
        'dados_ocupacao_json': json.dumps(dados_ocupacao, cls=DjangoJSONEncoder),
        'is_admin': request.user.is_staff,
    }
    
    return render(request, 'sapp/mapa_visualizacao.html', context)

@staff_member_required
@csrf_exempt
def salvar_todos_elementos(request):
    """
    API: Recebe o JSON completo do editor e salva no banco.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            armazem_id = data.get('armazem_id')
            elementos_data = data.get('elementos', [])
            
            armazem = ArmazemLayout.objects.get(id=armazem_id)
            
            # Estratégia Segura: 
            # 1. Limpar elementos atuais deste armazém (para remover os excluídos)
            # 2. Recriar tudo baseado no que veio do editor
            # Isso evita "lixo" no banco de dados.
            
            ElementoMapa.objects.filter(armazem=armazem).delete()
            
            novos_objetos = []
            for idx, item in enumerate(elementos_data):
                novo = ElementoMapa(
                    armazem=armazem,
                    tipo=item.get('tipo', 'RETANGULO'),
                    pos_x=item.get('pos_x'),
                    pos_y=item.get('pos_y'),
                    largura=item.get('largura'),
                    altura=item.get('altura'),
                    rotacao=item.get('rotacao', 0),
                    ordem_z=idx, # A ordem que vem do array é a ordem visual
                    
                    # Dados visuais
                    cor_preenchimento=item.get('cor_preenchimento'),
                    conteudo_texto=item.get('conteudo_texto', ''),
                    fonte_tamanho=item.get('fonte_tamanho', 14),
                    
                    # O MAIS IMPORTANTE: O ENDEREÇO
                    identificador=item.get('identificador', '').strip().upper() 
                )
                novos_objetos.append(novo)
            
            # Bulk create é muito mais rápido
            ElementoMapa.objects.bulk_create(novos_objetos)
            
            return JsonResponse({'success': True, 'total': len(novos_objetos)})
            
        except Exception as e:
            print(f"Erro ao salvar mapa: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Método inválido'})

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def lista_armazens(request):
    """Lista todos os armazéns disponíveis"""
    armazens = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazens': armazens,
        'is_admin': request.user.is_staff,
        'titulo_pagina': 'Mapas dos Armazéns'
    }
    return render(request, 'sapp/lista_armazens.html', context)

@staff_member_required
@csrf_exempt
def criar_armazens_automaticos(request):
    """API para criar armazéns automaticamente"""
    if request.method == 'POST':
        try:
            armazens_padrao = [
                {'numero': 1, 'nome': 'Armazém Principal', 'largura_canvas': 1200, 'altura_canvas': 800},
                {'numero': 2, 'nome': 'Armazém Secundário', 'largura_canvas': 1000, 'altura_canvas': 600},
                {'numero': 3, 'nome': 'Armazém de Reserva', 'largura_canvas': 800, 'altura_canvas': 500},
            ]
            
            criados = []
            for data in armazens_padrao:
                armazem, created = ArmazemLayout.objects.get_or_create(
                    numero=data['numero'],
                    defaults=data
                )
                if created:
                    criados.append(f"Armazém {armazem.numero} - {armazem.nome}")
            
            return JsonResponse({
                'success': True,
                'message': f'{len(criados)} armazéns criados com sucesso!',
                'armazens': criados
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


@staff_member_required
def editor_avancado(request, armazem_numero=1):
    armazem = get_object_or_404(ArmazemLayout, numero=armazem_numero, ativo=True)
    elementos = armazem.elementos.all().order_by('ordem_z')
    
    # ADICIONE ESTA LINHA ABAIXO se não tiver:
    armazens_disponiveis = ArmazemLayout.objects.filter(ativo=True).order_by('numero')
    
    context = {
        'armazem': armazem,
        'elementos': elementos,
        'armazens_disponiveis': armazens_disponiveis, # ENVIE PARA O CONTEXTO
        'titulo_pagina': f'Editor Gráfico - Armazém {armazem.numero}',
    }
    return render(request, 'sapp/editor_avancado.html', context)



# EM views.py - GARANTIR QUE ESTÁ CORRETO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # Se precisar de POST, mas GET não precisa normalmente
def api_buscar_produto(request):
    """
    API para buscar produto pelo código - BUSCA REAL DO BANCO DE DADOS
    Método: GET
    Parâmetro: codigo (string)
    Retorno: JSON com {encontrado: bool, dados: dict, erro: string}
    """
    try:
        # Log para debug
        print("=" * 50)
        print("API: Recebida requisição para buscar produto")
        print(f"API: Método: {request.method}")
        print(f"API: GET params: {dict(request.GET)}")
        
        # Apenas aceita GET
        if request.method != 'GET':
            return JsonResponse({
                'encontrado': False,
                'erro': 'Método não permitido. Use GET.'
            }, status=405)
        
        # Pegar código da query string
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            print("API: Erro - Código não fornecido")
            return JsonResponse({
                'encontrado': False, 
                'erro': 'Código não fornecido'
            }, status=400)
        
        print(f"API: Buscando produto com código: '{codigo}'")
        
        # Importar dentro da função para evitar problemas de importação circular
        from .models import Produto
        
        # Buscar produto ativo pelo código
        produto = Produto.objects.filter(codigo=codigo, ativo=True).first()
        
        if not produto:
            print(f"API: Produto '{codigo}' não encontrado ou inativo")
            return JsonResponse({
                'encontrado': False, 
                'erro': f'Produto "{codigo}" não encontrado ou inativo'
            })
        
        print(f"API: Produto encontrado - ID: {produto.id}, Código: {produto.codigo}")
        
        # Preparar dados para resposta - USANDO OS CAMPOS REAIS DO SEU MODELO
        dados = {
            'codigo': produto.codigo,
            'cultivar_id': str(produto.cultivar.id) if produto.cultivar else None,
            'cultivar_nome': produto.cultivar.nome if produto.cultivar else '',
            'peneira_id': str(produto.peneira.id) if produto.peneira else None,
            'peneira_nome': produto.peneira.nome if produto.peneira else '',
            'especie_id': str(produto.especie.id) if produto.especie else None,
            'especie_nome': produto.especie.nome if produto.especie else '',
            'categoria_id': str(produto.categoria.id) if produto.categoria else None,
            'categoria_nome': produto.categoria.nome if produto.categoria else '',
            'tratamento_id': str(produto.tratamento.id) if produto.tratamento else None,
            'tratamento_nome': produto.tratamento.nome if produto.tratamento else '',
            'empresa': produto.empresa or '',
            'tipo': produto.tipo or '',
            'descricao': produto.descricao or ''
        }
        
        print(f"API: Dados preparados para retorno: {json.dumps(dados, indent=2, ensure_ascii=False)}")
        
        # Criar resposta
        response_data = {
            'encontrado': True, 
            'dados': dados
        }
        
        print("API: Retornando dados com sucesso")
        print("=" * 50)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"API: ERRO INTERNO: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'encontrado': False, 
            'erro': f'Erro interno do servidor: {str(e)}'
        }, status=500)