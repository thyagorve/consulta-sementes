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


# views.py
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import json
from .models import Estoque, Cultivar, Peneira, Categoria, Tratamento
from django.db import transaction
import tempfile
import os



@login_required
def dashboard(request):
    """
    Dashboard com métricas, gráficos e KPIs baseados em dados reais
    """
    # Métricas Principais - DADOS REAIS
    total_itens = Estoque.objects.count()
    itens_ativos = Estoque.objects.filter(saldo__gt=0).count()
    itens_esgotados = total_itens - itens_ativos
    
    # Cálculo de totais convertidos - DADOS REAIS
    total_bag = Estoque.objects.filter(embalagem='BAG', saldo__gt=0).aggregate(
        total=Sum('saldo'))['total'] or 0
    total_sc = Estoque.objects.filter(embalagem='SC', saldo__gt=0).aggregate(
        total=Sum('saldo'))['total'] or 0
    total_sc_convertido = (total_bag * 25) + total_sc
    
    # Peso total em estoque - DADOS REAIS
    peso_total = Estoque.objects.filter(saldo__gt=0).aggregate(
        total=Sum('peso_total'))['total'] or Decimal('0.00')
    
    # Movimentação do mês - DADOS REAIS
    hoje = timezone.now()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    movimentacao_mes = HistoricoMovimentacao.objects.filter(
        data_hora__gte=inicio_mes
    ).count()
    
    # Top cultivares - DADOS REAIS
    top_cultivares = list(Estoque.objects.filter(saldo__gt=0).values(
        'cultivar__nome'
    ).annotate(
        total_saldo=Sum('saldo')
    ).order_by('-total_saldo')[:10])  # Top 10
    
    # Distribuição por categoria - DADOS REAIS
    categorias_distribuicao = list(Estoque.objects.filter(saldo__gt=0).values(
        'categoria__nome'
    ).annotate(
        total=Sum('saldo')
    ).order_by('-total')[:10])  # Top 10
    
    # NOVO: Capacidade por Armazém - DADOS REAIS
    # Extrai o número do armazém do campo endereco (ex: "R01 LN12 P02" -> armazém "01")
    from django.db.models import CharField
    from django.db.models.functions import Substr
    
    capacidade_armazem = list(Estoque.objects.filter(
        saldo__gt=0
    ).annotate(
        armazem_num=Substr('endereco', 2, 2, output_field=CharField())
    ).values(
        'armazem_num'
    ).annotate(
        total_sc=Sum('saldo'),
        total_lotes=Count('id'),
        peso_total=Sum('peso_total')
    ).order_by('armazem_num'))
    
    # NOVO: Movimentação Recente - DADOS REAIS
    movimentacao_recente = list(HistoricoMovimentacao.objects.select_related(
        'estoque', 'usuario'
    ).order_by('-data_hora')[:10])
    
    context = {
        # Métricas Principais
        'total_sc_convertido': total_sc_convertido,
        'total_bag': total_bag,
        'total_sc': total_sc,
        'peso_total': peso_total,
        'itens_ativos': itens_ativos,
        'itens_esgotados': itens_esgotados,
        'movimentacao_mes': movimentacao_mes,
        
        # Gráficos
        'top_cultivares': top_cultivares,
        'categorias_distribuicao': categorias_distribuicao,
        
        # Novos dados
        'capacidade_armazem': capacidade_armazem,
        'movimentacao_recente': movimentacao_recente,
    }
    
    return render(request, 'sapp/dashboard.html', context)

def logout_view(request):
    """
    Realiza o logout e redireciona para o login.
    Aceita POST (padrão recomendado) ou GET se necessário.
    """
    logout(request)
    return redirect('sapp:login')



#########################################################################


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

@login_required
def lista_estoque(request):
    termo = request.GET.get('busca', '')
    config = Configuracao.get_solo()
    itens = Estoque.objects.all().order_by('-id')

    if config.ocultar_esgotados:
        itens = itens.filter(saldo__gt=0)

    if termo:
        itens = itens.filter(
            Q(lote__icontains=termo) | 
            Q(cultivar__nome__icontains=termo) | 
            Q(endereco__icontains=termo)
        )

    total_bag = itens.filter(embalagem='BAG').aggregate(saldo=Sum('saldo'))['saldo'] or 0
    total_sc_fisico = itens.filter(embalagem='SC').aggregate(saldo=Sum('saldo'))['saldo'] or 0
    total_sc_convertido = (total_bag * 25) + total_sc_fisico

    context = {
        'itens': itens,
        'total_bag': total_bag,
        'total_sc': total_sc_convertido,
        'form_entrada': NovaEntradaForm(),
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
        # Conferentes agora são usuários, não passamos lista aqui para edição manual
    }
    return render(request, 'sapp/tabela_estoque.html', context)

@login_required
def nova_entrada(request):
    if request.method == 'POST':
        form = NovaEntradaForm(request.POST)
        if form.is_valid():
            novo_obj = form.save(commit=False)
            novo_obj.conferente = request.user # Automático
            
            lote_existente = Estoque.objects.filter(
                lote=novo_obj.lote,
                endereco=novo_obj.endereco,
                cultivar=novo_obj.cultivar,
                peneira=novo_obj.peneira,
                categoria=novo_obj.categoria,
                tratamento=novo_obj.tratamento,
                embalagem=novo_obj.embalagem,
                empresa=novo_obj.empresa
            ).first()

            if lote_existente:
                lote_existente.entrada += novo_obj.entrada
                lote_existente.conferente = request.user
                lote_existente.save()
                HistoricoMovimentacao.objects.create(
                    estoque=lote_existente, 
                    usuario=request.user, 
                    tipo='Entrada (Soma)',
                    descricao=f"Adicionado <b>{novo_obj.entrada}</b> unid. (Saldo atual: {lote_existente.saldo})"
                )
                messages.success(request, "Lote existente somado!")
            else:
                novo_obj.save()
                HistoricoMovimentacao.objects.create(
                    estoque=novo_obj, 
                    usuario=request.user, 
                    tipo='Entrada Inicial',
                    descricao=f"Entrada de <b>{novo_obj.entrada}</b> no endereço <b>{novo_obj.endereco}</b>."
                )
                messages.success(request, "Novo lote criado!")
        else:
            messages.error(request, "Erro no formulário.")
    return redirect('sapp:lista_estoque')

@login_required
def transferir(request, id):
    item_origem = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            qtd = int(request.POST.get('quantidade'))
            novo_end = request.POST.get('novo_endereco')
            
            if qtd <= 0 or qtd > item_origem.saldo:
                messages.error(request, "Quantidade inválida.")
                return redirect('sapp:lista_estoque')

            item_origem.saida += qtd
            item_origem.save()
            
            HistoricoMovimentacao.objects.create(
                estoque=item_origem,
                usuario=request.user,
                tipo='Transf. (Saída)',
                descricao=f"Enviado <b>{qtd}</b> para <b>{novo_end}</b>."
            )

            item_destino = Estoque.objects.filter(
                lote=item_origem.lote,
                endereco=novo_end,
                cultivar=item_origem.cultivar,
                peneira=item_origem.peneira,
                categoria=item_origem.categoria,
                tratamento=item_origem.tratamento,
                embalagem=item_origem.embalagem,
                empresa=item_origem.empresa
            ).first()

            if item_destino:
                item_destino.entrada += qtd
                item_destino.conferente = request.user
                item_destino.save()
                HistoricoMovimentacao.objects.create(
                    estoque=item_destino,
                    usuario=request.user,
                    tipo='Transf. (Entrada/Soma)',
                    descricao=f"Recebido <b>{qtd}</b> de <b>{item_origem.endereco}</b>."
                )
            else:
                novo_item = Estoque.objects.create(
                    lote=item_origem.lote, cultivar=item_origem.cultivar, peneira=item_origem.peneira, 
                    categoria=item_origem.categoria, az=item_origem.az, endereco=novo_end, 
                    entrada=qtd, saida=0, origem_destino=f"Transf. de {item_origem.endereco}", 
                    conferente=request.user, 
                    especie=item_origem.especie, empresa=item_origem.empresa, 
                    embalagem=item_origem.embalagem, peso_unitario=item_origem.peso_unitario, 
                    tratamento=item_origem.tratamento
                )
                HistoricoMovimentacao.objects.create(
                    estoque=novo_item,
                    usuario=request.user,
                    tipo='Transf. (Entrada)',
                    descricao=f"Recebido <b>{qtd}</b> de <b>{item_origem.endereco}</b>."
                )
            
            messages.success(request, "Transferência realizada!")
        except Exception as e:
            messages.error(request, f"Erro: {e}")

    return redirect('sapp:lista_estoque')

@login_required
def editar(request, id):
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            # 1. CAPTURA O ESTADO ANTIGO (Para comparação)
            antigo_lote = item.lote
            antigo_endereco = item.endereco
            antigo_empresa = item.empresa
            antigo_od = item.origem_destino
            antigo_peso = item.peso_unitario
            antigo_emb = item.embalagem
            antigo_az = item.az or ""
            antigo_obs = item.observacao or ""
            
            # Para FKs, pegamos o NOME para ficar legível no histórico
            antigo_cultivar = item.cultivar.nome
            antigo_peneira = item.peneira.nome
            antigo_categoria = item.categoria.nome
            antigo_conferente = item.conferente.username # ou .first_name
            antigo_tratamento = item.tratamento.nome if item.tratamento else "Sem Tratamento"

            # 2. CAPTURA OS NOVOS VALORES DO FORMULÁRIO
            novo_lote = request.POST.get('lote')
            novo_endereco = request.POST.get('endereco')
            novo_empresa = request.POST.get('empresa')
            novo_od = request.POST.get('origem_destino')
            novo_emb = request.POST.get('embalagem')
            novo_az = request.POST.get('az')
            novo_obs = request.POST.get('observacao')

            # Tratamento do Peso (Blindagem contra erro de formatação)
            peso_raw = request.POST.get('peso_unitario', '0')
            if peso_raw.count('.') > 1:
                partes = peso_raw.split('.')
                peso_raw = f"{partes[0]}.{partes[1]}"
            novo_peso = Decimal(peso_raw.replace(',', '.'))

            # Busca os Objetos Novos (FKs)
            obj_cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
            obj_peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
            obj_categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
            
            # Tratamento é opcional
            tid = request.POST.get('tratamento')
            if tid:
                obj_tratamento = get_object_or_404(Tratamento, id=tid)
                nome_novo_tratamento = obj_tratamento.nome
            else:
                obj_tratamento = None
                nome_novo_tratamento = "Sem Tratamento"

            # 3. COMPARAÇÃO E MONTAGEM DO LOG
            mudancas = []

            if antigo_lote != novo_lote: 
                mudancas.append(f"Lote: {antigo_lote} -> <b>{novo_lote}</b>")
            
            if antigo_endereco != novo_endereco: 
                mudancas.append(f"Endereço: {antigo_endereco} -> <b>{novo_endereco}</b>")
            
            if antigo_cultivar != obj_cultivar.nome:
                mudancas.append(f"Cultivar: {antigo_cultivar} -> <b>{obj_cultivar.nome}</b>")
            
            if antigo_peneira != obj_peneira.nome:
                mudancas.append(f"Peneira: {antigo_peneira} -> <b>{obj_peneira.nome}</b>")
            
            if antigo_categoria != obj_categoria.nome:
                mudancas.append(f"Categoria: {antigo_categoria} -> <b>{obj_categoria.nome}</b>")

            if antigo_tratamento != nome_novo_tratamento:
                mudancas.append(f"Tratamento: {antigo_tratamento} -> <b>{nome_novo_tratamento}</b>")

            if antigo_peso != novo_peso:
                mudancas.append(f"Peso: {antigo_peso} -> <b>{novo_peso}</b>")
            
            if antigo_emb != novo_emb:
                mudancas.append(f"Emb: {antigo_emb} -> <b>{novo_emb}</b>")
                
            if antigo_empresa != novo_empresa:
                mudancas.append(f"Empresa alterada.")

            if antigo_od != novo_od:
                mudancas.append(f"Origem/Dest alterado.")

            if antigo_obs != novo_obs:
                mudancas.append("Observação alterada.")

            # 4. ATUALIZA O OBJETO E SALVA
            item.lote = novo_lote
            item.endereco = novo_endereco
            item.empresa = novo_empresa
            item.origem_destino = novo_od
            item.peso_unitario = novo_peso
            item.embalagem = novo_emb
            item.az = novo_az
            item.observacao = novo_obs
            
            item.cultivar = obj_cultivar
            item.peneira = obj_peneira
            item.categoria = obj_categoria
            item.tratamento = obj_tratamento
            
            # Atualiza quem editou por último
            item.conferente = request.user 
            
            item.save()

            # 5. GRAVA O HISTÓRICO
            if mudancas:
                desc = "<br>".join(mudancas)
                HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Edição', 
                    descricao=f"Alterações:<br>{desc}"
                )
            else:
                # Se o usuário abriu o modal e clicou salvar sem mudar nada
                HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Edição', 
                    descricao="Salvo sem alterações visíveis."
                )

            messages.success(request, "Lote editado com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao editar: {e}")

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

@login_required
def historico_geral(request):
    lista = HistoricoMovimentacao.objects.all().order_by('-data_hora')
    paginator = Paginator(lista, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'sapp/historico_geral.html', {'page_obj': page_obj})

# Adicione isso no TOPO junto com os outros imports


from django.http import JsonResponse # <--- TEM QUE TER ESSA IMPORTAÇÃO NO TOPO

# ... (suas outras views) ...

# ... (No final do arquivo) ...
@login_required
def api_buscar_dados_lote(request):
    lote_buscado = request.GET.get('lote')
    item = Estoque.objects.filter(lote=lote_buscado).order_by('-id').first()
    
    if item:
        data = {
            'encontrado': True,
            'cultivar': item.cultivar.id,
            'peneira': item.peneira.id,
            'categoria': item.categoria.id,
            'tratamento': item.tratamento.id if item.tratamento else "",
            'endereco': item.endereco,
            'empresa': item.empresa,
            'origem_destino': item.origem_destino,
            'peso_unitario': str(item.peso_unitario),
            'embalagem': item.embalagem,
            'az': item.az or "",
            'observacao': item.observacao or ""
        }
    else:
        data = {'encontrado': False}
    return JsonResponse(data)




@login_required
def gestao_estoque(request):
    # Filtra apenas estoque com saldo > 0
    estoque_atual = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    ).order_by('endereco', 'lote')
    
    context = {
        'estoque': estoque_atual,
        'total_itens': estoque_atual.count(),
        'total_saldo': sum(item.saldo for item in estoque_atual),
    }
    return render(request, 'sapp/gestao_estoque.html', context)


# views.py - ADICIONAR ESTE IMPORT NO TOPO
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test




import pandas as pd
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

def exportar_excel(request):
    estoque = Estoque.objects.filter(saldo__gt=0).select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento', 'conferente'
    )
    
    # Criar DataFrame
    data = []
    for item in estoque:
        data.append({
            'Lote': item.lote,
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
            'Lote Anterior': item.lote_anterior or '',
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
    
    # Dados da tabela
    data = [['Lote', 'Cultivar', 'Peneira', 'Endereço', 'Saldo', 'Peso Total']]
    
    for item in estoque:
        data.append([
            item.lote,
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


# views.py - APENAS A VIEW, FUNÇÕES AUXILIARES ESTÃO NO TOPO DO ARQUIVO


def mapear_colunas_protheus_inteligente(colunas_encontradas):
    """
    Mapeamento INTELIGENTE que analisa padrões complexos nos cabeçalhos
    """
    mapping = {}
    
    # Converter todas as colunas para minúsculas e limpas para comparação
    colunas_limpas = [str(col).lower().strip().replace(' ', '').replace('_', '').replace('-', '').replace('.', '') 
                      for col in colunas_encontradas]
    
    print(f"🔍 Colunas encontradas no arquivo: {colunas_encontradas}")
    print(f"🔍 Colunas limpas para análise: {colunas_limpas}")
    
    # Dicionário de padrões com pesos (mais específicos primeiro)
    padroes_com_peso = {
        'lote': [
            'lote'
        ],
        'quantidade': [
            'quantidade', 'qtd', 'qde', 'saldo'
        ],
        'endereco': [
            'endereco', 'endreco'
        ],
        'cultivar': [
            'cultivar', 'variedade'
        ],
        'peneira': [
            'peneira', 'pen'
        ],
        'categoria': [
            'categoria', 'categ', 'cat'
        ],
        'cultura': [
            'cultura', 'cultur'
        ],
        'unidade': [
            'unidade', 'unit'
        ],
        'peso_med_ens': [
            'pesomedens', 'peso_med_ens', 'pesomedio','peso'
        ],
        'tratamento': [
            'tratamento', 'trat', 'treatment', 'trtm', 'tratament',
            'tratamentosemente', 'tptratame', 'tipotratamento'
        ],
        'empresa': [
            'empresa', 'company', 'emp', 'fornecedor', 'supplier'
        ],
        'origem_destino': [
            'origem', 'destino', 'origemdestino', 'origin', 'destination'
        ],
        'az': [
            'az', 'za', 'a/z', 'z/a', 'Armazem'
        ]
    }
    
    # Para cada campo, encontrar a melhor correspondência
    for campo, padroes in padroes_com_peso.items():
        melhor_pontuacao = 0
        melhor_coluna = None
        
        for i, coluna_limpa in enumerate(colunas_limpas):
            for padrao in padroes:
                # Verificar correspondência exata primeiro
                if coluna_limpa == padrao:
                    melhor_coluna = colunas_encontradas[i]
                    melhor_pontuacao = 100
                    break
                
                # Verificar se o padrão está contido na coluna
                elif padrao in coluna_limpa:
                    pontuacao = len(padrao) / len(coluna_limpa) * 100
                    if pontuacao > melhor_pontuacao:
                        melhor_pontuacao = pontuacao
                        melhor_coluna = colunas_encontradas[i]
            
            if melhor_pontuacao == 100:
                break
        
        mapping[campo] = melhor_coluna
    
    # CORREÇÃO ESPECÍFICA para "Tp. Tratame." e "Categoria"
    for i, coluna_original in enumerate(colunas_encontradas):
        coluna_lower = str(coluna_original).lower()
        
        # Tratamento específico para "Tp. Tratame."
        if 'tratame' in coluna_lower or 'tp.tratame' in coluna_lower.replace(' ', '').replace('.', ''):
            mapping['tratamento'] = coluna_original
            print(f"✅ Encontrado tratamento na coluna: {coluna_original}")
        
        # Tratamento específico para "Categoria"
        if coluna_lower == 'categoria' or 'categoria' in coluna_lower:
            mapping['categoria'] = coluna_original
            print(f"✅ Encontrado categoria na coluna: {coluna_original}")
    
    print(f"🎯 Mapeamento final encontrado: {mapping}")
    return mapping




def buscar_tratamento_categoria_avancado(tratamento_nome, categoria_nome):
    """
    Busca ou cria tratamento e categoria de forma inteligente
    SEM mapeamento fixo - usa apenas truncamento
    """
    tratamento_obj = None
    categoria_obj = None
    
    # BUSCAR TRATAMENTO - APENAS TRUNCAMENTO SIMPLES
    if tratamento_nome and str(tratamento_nome).strip():
        try:
            tratamento_nome_limpo = str(tratamento_nome).strip()
            
            # 🔥 APENAS TRUNCAR - SEM MAPEAMENTO FIXO
            if len(tratamento_nome_limpo) > 9:
                tratamento_nome_limpo = tratamento_nome_limpo[:9]
                print(f"✂️ Tratamento truncado para 8 caracteres: {tratamento_nome_limpo}")
            
            # Buscar pelo nome (truncado ou não)
            tratamento_obj = Tratamento.objects.filter(
                nome__iexact=tratamento_nome_limpo
            ).first()
            
            # Se não encontrou, criar novo
            if not tratamento_obj:
                tratamento_obj = Tratamento.objects.create(
                    nome=tratamento_nome_limpo
                )
                print(f"✅ Criado novo tratamento: {tratamento_nome_limpo}")
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar/criar tratamento '{tratamento_nome}': {e}")
    
    # BUSCAR CATEGORIA (sem alteração)
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
                print(f"✅ Criada nova categoria: {categoria_nome_limpo}")
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar/criar categoria '{categoria_nome}': {e}")
    
    return tratamento_obj, categoria_obj
    
    

def tratamentos_sao_equivalentes(trat1, trat2):
    """Verifica se dois tratamentos são equivalentes (um contém 100% do outro)"""
    if not trat1 and not trat2:
        return True  # Ambos vazios são equivalentes
    if not trat1 or not trat2:
        return False  # Um vazio e outro não são diferentes
    
    trat1_clean = str(trat1).strip().upper()
    trat2_clean = str(trat2).strip().upper()
    
    # Remover espaços extras para comparação mais precisa
    trat1_clean = ' '.join(trat1_clean.split())
    trat2_clean = ' '.join(trat2_clean.split())
    
    print(f"🔍 [DEBUG TRATAMENTO] Comparando: '{trat1_clean}' vs '{trat2_clean}'")
    print(f"🔍 [DEBUG TRATAMENTO] '{trat1_clean}' in '{trat2_clean}': {trat1_clean in trat2_clean}")
    print(f"🔍 [DEBUG TRATAMENTO] '{trat2_clean}' in '{trat1_clean}': {trat2_clean in trat1_clean}")
    
    # Se um está 100% contido no outro, são equivalentes
    resultado = (trat1_clean in trat2_clean or trat2_clean in trat1_clean)
    print(f"🔍 [DEBUG TRATAMENTO] Resultado: {resultado}")
    
    return resultado





    
    



def encontrar_coluna(colunas_encontradas, padroes):
    """
    Encontra a coluna que melhor corresponde aos padrões
    """
    colunas_lower = [str(col).lower().strip() for col in colunas_encontradas]
    
    for padrao in padroes:
        for i, coluna in enumerate(colunas_lower):
            if padrao in coluna:
                return colunas_encontradas[i]  # Retorna o nome original da coluna
    
    return None



def converter_unidade(quantidade_original, unidade, peso_med_ens):
    """
    Converte unidades usando APENAS peso_med_ens do arquivo
    """
    if not unidade or peso_med_ens <= 0:
        return quantidade_original, 1
    
    unidade = unidade.upper()
    
    # Se for KG e temos peso_med_ens, converter para unidades
    if unidade in ['KG', 'QUILO', 'QUILOS']:
        quantidade_convertida = quantidade_original / peso_med_ens
        return round(quantidade_convertida), peso_med_ens
    
    # Se for TONELADA
    elif unidade in ['TON', 'TONELADA']:
        quantidade_convertida = (quantidade_original * 1000) / peso_med_ens
        return round(quantidade_convertida), peso_med_ens / 1000
    
    # Se for MLH (milheiro) - 1 MLH = 1000 unidades
    elif unidade in ['MLH', 'MILHEIRO']:
        quantidade_convertida = quantidade_original * 1000
        return quantidade_convertida, 0.001
    
    # Para SC, BAG, UNIDADE - não converter, já está em unidades
    elif unidade in ['SC', 'SACO', 'BAG', 'BAGS', 'UN', 'UNID', 'UNIDADE']:
        return quantidade_original, 1
    
    # Unidade não reconhecida - não converter
    else:
        return quantidade_original, 1

def calcular_peso_unitario(unidade, peso_med_ens):
    """Calcula peso unitário APENAS com dados reais do arquivo"""
    # Usar APENAS o peso_med_ens do Protheus - não inventar nada
    if peso_med_ens and peso_med_ens > 0:
        return float(peso_med_ens)
    
    # Se não tem peso_med_ens, deixar None - NÃO INVENTAR
    return None

def identificar_embalagem_por_unidade(unidade):
    """Identifica embalagem de forma ASSERTIVA baseado na unidade"""
    if not unidade:
        return 'BAG'  # Default seguro
    
    unidade = str(unidade).upper().strip()
    
    # Mapeamento DIRETO e ASSERTIVO
    mapeamento_direto = {
        'SC': 'SC',
        'SACO': 'SC', 
        'SACOS': 'SC',
        'SACK': 'SC',
        'SACKS': 'SC',
        'BAG': 'BAG',
        'BAGS': 'BAG',
        'BIG BAG': 'BAG',
        'BIGBAG': 'BAG',
        'BULK': 'BAG',
        'KG': 'BAG',  # KG normalmente é Big Bag
        'QUILO': 'BAG',
        'QUILOS': 'BAG',
        'TON': 'BAG',  # Tonelada normalmente é Big Bag
        'TONELADA': 'BAG',
        'MLH': 'BAG',  # Milheiro normalmente é Big Bag
        'MILHEIRO': 'BAG',
        'UN': 'BAG',   # Unidade normalmente é Big Bag
        'UNID': 'BAG',
        'UNIDADE': 'BAG'
    }
    
    # Busca direta primeiro
    if unidade in mapeamento_direto:
        return mapeamento_direto[unidade]
    
    # Busca por contém (para casos como "SC 25KG", "BAG 1000KG", etc)
    for padrao, embalagem in mapeamento_direto.items():
        if padrao in unidade:
            return embalagem
    
    # Se não encontrou nenhum padrão, usar BAG como default
    return 'BAG'



def extrair_numero(row, column_key, default=0):
    """Extrai número de forma segura"""
    if not column_key:
        return default
    
    value = row.get(column_key)
    if value is None or pd.isna(value):
        return default
    
    try:
        # Tenta converter para float, remove caracteres não numéricos se necessário
        if isinstance(value, str):
            # Remove caracteres não numéricos exceto ponto e vírgula
            value = ''.join(c for c in value if c.isdigit() or c in ',.')
            # Substitui vírgula por ponto para conversão float
            value = value.replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return default

def calcular_peso_unitario(unidade, peso_med_ens):
    """Calcula peso unitário com proteção contra None"""
    if unidade is None or peso_med_ens is None:
        return 0
    
    try:
        # Sua lógica de cálculo aqui
        # Exemplo simples:
        if unidade and peso_med_ens > 0:
            return peso_med_ens  # ou sua lógica específica
        return 0
    except (TypeError, ValueError):
        return 0

def identificar_embalagem(valor_embalagem):
    """
    Identifica o tipo de embalagem baseado no valor
    """
    if not valor_embalagem:
        return 'BAG'
    
    valor_str = str(valor_embalagem).upper()
    
    if 'BAG' in valor_str or 'BIG' in valor_str or 'SACARIA' in valor_str:
        return 'BAG'
    elif 'SACO' in valor_str or 'SC' in valor_str or 'SACK' in valor_str:
        return 'SC'
    else:
        return 'BAG'  # Default





def extrair_texto_se_existir(row, coluna):
    """Extrai texto apenas se a coluna existir e tiver valor"""
    if not coluna or coluna not in row:
        return None
    valor = row[coluna]
    if pd.isna(valor) or valor is None:
        return None
    return str(valor).strip()

def calcular_peso_unitario_real(unidade, peso_med_ens, quantidade_original, quantidade_convertida):
    """Calcula peso unitário de forma realista"""
    if not unidade:
        return 60.0  # Default seguro
    
    unidade = unidade.upper()
    
    # Se for KG e temos peso_med_ens, usar ele
    if unidade in ['KG', 'QUILO'] and peso_med_ens > 0:
        return peso_med_ens
    
   
    
    # Se temos dados para calcular
    elif quantidade_original > 0 and quantidade_convertida > 0 and quantidade_original != quantidade_convertida:
        return quantidade_original / quantidade_convertida
    
    
    

###################CORRIGIDO###########################################################

@login_required
def importar_estoque(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            excel_file = request.FILES['excel_file']
            
            print("=" * 80)
            print("🔍 [DEBUG IMPORT] INICIANDO PROCESSAMENTO DO ARQUIVO")
            print("=" * 80)
            
            # Ler o arquivo Excel
            df = pd.read_excel(excel_file)
            print(f"📊 [DEBUG] Arquivo lido - {len(df)} linhas, colunas: {list(df.columns)}")
            
            # Verificar se tem mapeamento customizado
            custom_mapping_json = request.POST.get('custom_mapping')
            if custom_mapping_json:
                custom_mapping = json.loads(custom_mapping_json)
                column_mapping = custom_mapping
                print("🎯 [DEBUG] Usando mapeamento customizado:", column_mapping)
            else:
                # Usar mapeamento INTELIGENTE MELHORADO
                column_mapping = mapear_colunas_protheus_inteligente(df.columns.tolist())
                print("🎯 [DEBUG] Mapeamento inteligente encontrado:", column_mapping)
            
            # Verificar se encontramos os campos essenciais
            campos_obrigatorios = ['lote', 'quantidade', 'endereco']
            campos_faltantes = [campo for campo in campos_obrigatorios if not column_mapping.get(campo)]
            
            if campos_faltantes:
                print(f"❌ [DEBUG] Campos obrigatórios faltantes: {campos_faltantes}")
                return JsonResponse({
                    'success': False,
                    'error': f'Campos obrigatórios não identificados: {", ".join(campos_faltantes)}. Colunas encontradas: {", ".join(df.columns.tolist())}'
                })
            
            # Processar dados com mapeamento
            processed_data = []
            errors = []
            warnings = []
            
            print("🔄 [DEBUG] Processando linhas do arquivo...")
            
            for index, row in df.iterrows():
                item_errors = []
                item_warnings = []
                
                def safe_strip(value):
                    """Limpa valores de forma mais robusta"""
                    if value is None or pd.isna(value):
                        return ''
                    value_str = str(value).strip()
                    value_str = ' '.join(value_str.split())
                    value_str = value_str.replace('\u00A0', ' ')
                    value_str = value_str.replace('\r', '')
                    value_str = value_str.replace('\n', '')
                    value_str = value_str.replace('\t', ' ')
                    return value_str
                
                # Extrair dados básicos
                item_data = {
                    'row_number': index + 2,
                    'lote': safe_strip(row.get(column_mapping.get('lote'))),
                    'endereco': safe_strip(row.get(column_mapping.get('endereco'))),
                    'cultivar': safe_strip(row.get(column_mapping.get('cultivar'))) or '',
                    'peneira': safe_strip(row.get(column_mapping.get('peneira'))) or '',
                    'cultura': safe_strip(row.get(column_mapping.get('cultura'))) or 'SOJA',
                    'unidade': safe_strip(row.get(column_mapping.get('unidade'))) or '',
                    'quantidade_original': extrair_numero(row, column_mapping.get('quantidade'), 0),
                    'peso_med_ens': extrair_numero(row, column_mapping.get('peso_med_ens'), 0),
                    'tratamento': safe_strip(row.get(column_mapping.get('tratamento'))) or '',
                    'categoria_arquivo': safe_strip(row.get(column_mapping.get('categoria'))) or '',
                    'az': safe_strip(row.get(column_mapping.get('az'))) or '',
                    'origem_destino': safe_strip(row.get(column_mapping.get('origem_destino'))) or 'Importação',
                    'empresa': safe_strip(row.get(column_mapping.get('empresa'))) or '',
                }
                
                # DEBUG: Log da primeira linha
                if index == 0:
                    print("🔍 [DEBUG PRIMEIRA LINHA]:")
                    print(f"  Lote: {item_data['lote']}")
                    print(f"  Endereço: '{item_data['endereco']}'")
                    print(f"  Quantidade: {item_data['quantidade_original']}")
                
                # Validações básicas
                if not item_data['lote']:
                    item_errors.append('Lote é obrigatório')
                
                if item_data['quantidade_original'] <= 0:
                    item_errors.append('Quantidade deve ser maior que zero')
                
                if not item_data['endereco']:
                    item_errors.append('Endereço é obrigatório')
                
                # CONVERSÃO DE UNIDADES
                if item_data['unidade'] and item_data['peso_med_ens'] > 0:
                    quantidade_convertida, fator_conversao = converter_unidade(
                        item_data['quantidade_original'],
                        item_data['unidade'],
                        item_data['peso_med_ens']
                    )
                    item_data['quantidade'] = quantidade_convertida
                    item_data['fator_conversao'] = fator_conversao
                else:
                    item_data['quantidade'] = item_data['quantidade_original']
                    item_data['fator_conversao'] = 1
                
                # Identificar embalagem
                item_data['embalagem'] = identificar_embalagem_por_unidade(item_data['unidade'])
                
                # Calcular peso unitário
                try:
                    peso_calculado = calcular_peso_unitario(item_data['unidade'], item_data['peso_med_ens'])
                    item_data['peso_unitario'] = peso_calculado
                except (TypeError, ValueError) as e:
                    item_data['peso_unitario'] = None
                    item_warnings.append(f'Não foi possível calcular peso unitário')
                
                # Buscar tratamento e categoria
                tratamento_obj, categoria_obj = buscar_tratamento_categoria_avancado(
                    item_data['tratamento'],
                    item_data['categoria_arquivo']
                )
                
                item_data['tratamento_id'] = tratamento_obj.id if tratamento_obj else None
                item_data['categoria_id'] = categoria_obj.id if categoria_obj else None
                
                # Se não encontrou categoria, usar a padrão
                if not item_data['categoria_id'] and item_data['cultivar']:
                    try:
                        categoria_nome = f"{item_data['cultura']} - {item_data['cultivar']}"
                        categoria_padrao, created = Categoria.objects.get_or_create(
                            nome__iexact=categoria_nome,
                            defaults={'nome': categoria_nome}
                        )
                        item_data['categoria_id'] = categoria_padrao.id
                        if created:
                            item_warnings.append(f'Criada categoria padrão: {categoria_nome}')
                    except Exception as e:
                        item_errors.append(f'Erro ao criar categoria: {str(e)}')
                
                # Buscar cultivar
                if item_data['cultivar']:
                    try:
                        cultivar, created = Cultivar.objects.get_or_create(
                            nome__iexact=item_data['cultivar'],
                            defaults={'nome': item_data['cultivar']}
                        )
                        item_data['cultivar_id'] = cultivar.id
                    except Exception as e:
                        item_errors.append(f'Cultivar inválido: {str(e)}')
                else:
                    item_data['cultivar_id'] = None
                    item_warnings.append('Cultivar não especificado')
                
                # Buscar peneira
                if item_data['peneira']:
                    try:
                        peneira, created = Peneira.objects.get_or_create(
                            nome__iexact=item_data['peneira'],
                            defaults={'nome': item_data['peneira']}
                        )
                        item_data['peneira_id'] = peneira.id
                    except Exception as e:
                        item_errors.append(f'Peneira inválida: {str(e)}')
                else:
                    item_data['peneira_id'] = None
                    item_warnings.append('Peneira não especificada')
                
                if item_errors:
                    errors.append({
                        'row': item_data['row_number'],
                        'lote': item_data['lote'],
                        'errors': item_errors,
                        'warnings': item_warnings
                    })
                else:
                    processed_data.append(item_data)
                    if item_warnings:
                        warnings.append({
                            'row': item_data['row_number'],
                            'lote': item_data['lote'],
                            'warnings': item_warnings
                        })
            
            print(f"✅ [DEBUG] Processamento concluído - {len(processed_data)} itens válidos, {len(errors)} erros")
            
            # DEBUG do estoque atual
            def debug_estoque_atual():
                estoque_atual = Estoque.objects.all().values('lote', 'endereco', 'saldo', 'cultivar__nome')
                print("📋 [DEBUG] ESTOQUE ATUAL NO BANCO:")
                for item in estoque_atual[:10]:
                    print(f"  Lote: {item['lote']}, Endereço: {item['endereco']}, Saldo: {item['saldo']}, Cultivar: {item['cultivar__nome']}")
                print(f"  Total de itens no estoque: {estoque_atual.count()}")
            
            debug_estoque_atual()
            
            # Comparar com estoque atual
            print("🔄 [DEBUG] Iniciando comparação com estoque atual...")
            comparacao = comparar_com_estoque_atual_inteligente(processed_data)
            
            print("📊 [DEBUG] RESULTADO DA COMPARAÇÃO:")
            print(f"  - Novos lotes: {comparacao['resumo']['novos']}")
            print(f"  - Lotes alterados: {comparacao['resumo']['atualizados']}")
            print(f"  - Lotes iguais: {comparacao['resumo']['iguais']}")
            print(f"  - Múltiplos endereços: {comparacao['resumo']['multi_endereco']}")
            
            return JsonResponse({
                'success': True,
                'processed_count': len(processed_data),
                'error_count': len(errors),
                'warning_count': len(warnings),
                'comparacao': comparacao,
                'errors': errors,
                'warnings': warnings,
                'preview_data': processed_data[:10],
                'column_mapping': column_mapping,
                'colunas_encontradas': df.columns.tolist()
            })
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"❌ [ERRO DETALHADO] {error_traceback}")
            return JsonResponse({
                'success': False,
                'error': f'Erro ao processar arquivo: {str(e)}',
                'traceback': error_traceback
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido ou arquivo não enviado'})

def comparar_com_estoque_atual_inteligente(novos_dados):
    """Comparação INTELIGENTE que considera lote + endereço como chave única"""
    comparacao = {
        'novos_lotes': [],
        'lotes_alterados': [],
        'lotes_iguais': [],
        'lotes_multi_endereco': [],
        'resumo': {
            'novos': 0,
            'atualizados': 0,
            'iguais': 0,
            'multi_endereco': 0
        }
    }
    
    print("🔍 [DEBUG COMPARAÇÃO] Iniciando comparação...")
    print(f"📊 [DEBUG] {len(novos_dados)} itens para comparar")
    
    # Buscar TODOS os lotes existentes do banco
    estoque_existente = Estoque.objects.all().select_related(
        'cultivar', 'peneira', 'categoria', 'tratamento'
    )
    
    print(f"📊 [DEBUG] {estoque_existente.count()} itens no estoque atual")
    
    # Criar dicionário com chave: lote -> lista de objetos
    estoque_por_lote = {}
    
    for item in estoque_existente:
        if item.lote not in estoque_por_lote:
            estoque_por_lote[item.lote] = []
        
        estoque_por_lote[item.lote].append({
            'id': item.id,
            'endereco': item.endereco,
            'saldo': item.saldo,
            'cultivar': item.cultivar.nome if item.cultivar else '',
            'peneira': item.peneira.nome if item.peneira else '',
            'categoria': item.categoria.nome if item.categoria else '',
            'tratamento': item.tratamento.nome if item.tratamento else '',
            'peso_unitario': float(item.peso_unitario) if item.peso_unitario else None,
            'embalagem': item.embalagem,
            'empresa': item.empresa,
            'origem_destino': item.origem_destino,
            'az': item.az or ''
        })
    
    # DEBUG: Mostrar alguns lotes do estoque
    lotes_estoque = list(estoque_por_lote.keys())[:5]
    print(f"🔍 [DEBUG] Primeiros 5 lotes no estoque: {lotes_estoque}")
    
    for novo_item in novos_dados:
        lote = novo_item['lote']
        endereco_novo = novo_item['endereco']
        
        print(f"🔍 [DEBUG] Processando: Lote '{lote}', Endereço novo '{endereco_novo}'")
        
        # Verificar se o lote existe no estoque
        if lote in estoque_por_lote:
            itens_existentes = estoque_por_lote[lote]
            print(f"  ✅ Lote encontrado no estoque. {len(itens_existentes)} registro(s)")
            
            # Verificar se existe no MESMO endereço
            item_mesmo_endereco = None
            for item in itens_existentes:
                if item['endereco'] == endereco_novo:
                    item_mesmo_endereco = item
                    break
            
            if item_mesmo_endereco:
                print(f"  ✅ Encontrado no mesmo endereço: {endereco_novo}")
                
                # Verificação específica para PQH00208
                if lote == 'PQH00208':
                    print("🎯 [DEBUG PQH00208] VERIFICAÇÃO ESPECÍFICA:")
                    print(f"  Endereço no banco: '{item_mesmo_endereco['endereco']}'")
                    print(f"  Endereço no arquivo: '{endereco_novo}'")
                    print(f"  São iguais? {item_mesmo_endereco['endereco'] == endereco_novo}")
                    print(f"  Tipo endereço BD: {type(item_mesmo_endereco['endereco'])}")
                    print(f"  Tipo endereço arquivo: {type(endereco_novo)}")
                    print(f"  Endereço BD (repr): {repr(item_mesmo_endereco['endereco'])}")
                    print(f"  Endereço arquivo (repr): {repr(endereco_novo)}")
                    print(f"  Comprimento BD: {len(item_mesmo_endereco['endereco'])}")
                    print(f"  Comprimento arquivo: {len(endereco_novo)}")
                
                # Verificar se são idênticos
                if sao_identicos(item_mesmo_endereco, novo_item):
                    comparacao['lotes_iguais'].append({
                        'lote': lote,
                        'endereco': endereco_novo,
                        'dados': novo_item
                    })
                    comparacao['resumo']['iguais'] += 1
                    print(f"  ✅ Lote idêntico - marcado como igual")
                else:
                    # São diferentes - mostrar para atualização
                    divergencias = []
                    
                    # DEBUG DETALHADO: Log de todos os campos
                    print(f"  🔍 [DEBUG DETALHADO] Comparando lote {lote}:")
                    print(f"     Saldo: {item_mesmo_endereco['saldo']} (BD) vs {novo_item['quantidade']} (Arquivo)")
                    print(f"     Cultivar: '{item_mesmo_endereco['cultivar']}' (BD) vs '{novo_item['cultivar']}' (Arquivo)")
                    print(f"     Peneira: '{item_mesmo_endereco['peneira']}' (BD) vs '{novo_item['peneira']}' (Arquivo)")
                    print(f"     Endereço: '{item_mesmo_endereco['endereco']}' (BD) vs '{endereco_novo}' (Arquivo)")
                    print(f"     Tratamento: '{item_mesmo_endereco.get('tratamento', '')}' (BD) vs '{novo_item.get('tratamento', '')}' (Arquivo)")
                    print(f"     Embalagem: '{item_mesmo_endereco['embalagem']}' (BD) vs '{novo_item['embalagem']}' (Arquivo)")
                    print(f"     Peso: {item_mesmo_endereco.get('peso_unitario')} (BD) vs {novo_item.get('peso_unitario')} (Arquivo)")
                    
                    # Verificar cada campo individualmente
                    if item_mesmo_endereco['saldo'] != novo_item['quantidade']:
                        divergencias.append(f'Quantidade: {item_mesmo_endereco["saldo"]} → {novo_item["quantidade"]}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Quantidade")
                    
                    if item_mesmo_endereco['cultivar'] != novo_item['cultivar']:
                        divergencias.append(f'Cultivar: {item_mesmo_endereco["cultivar"]} → {novo_item["cultivar"]}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Cultivar")
                    
                    if item_mesmo_endereco['peneira'] != novo_item['peneira']:
                        divergencias.append(f'Peneira: {item_mesmo_endereco["peneira"]} → {novo_item["peneira"]}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Peneira")
                    
                    # VERIFICAÇÃO ESPECÍFICA DO ENDEREÇO
                    if item_mesmo_endereco['endereco'] != endereco_novo:
                        divergencias.append(f'Endereço: {item_mesmo_endereco["endereco"]} → {endereco_novo}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Endereço")
                    else:
                        print(f"     ❌ ENDEREÇO IGUAL: '{item_mesmo_endereco['endereco']}' = '{endereco_novo}'")
                    
                    # Tratamento
                    tratamento_existente = item_mesmo_endereco.get('tratamento', '')
                    tratamento_novo = novo_item.get('tratamento', '')
                    if not tratamentos_sao_equivalentes(tratamento_existente, tratamento_novo):
                        divergencias.append(f'Tratamento: {tratamento_existente} → {tratamento_novo}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Tratamento")
                    
                    # Peso unitário
                    peso_existente = item_mesmo_endereco.get('peso_unitario')
                    peso_novo = novo_item.get('peso_unitario')
                    
                    if peso_existente is not None and peso_novo is not None:
                        if abs(peso_existente - float(peso_novo)) > 0.01:
                            divergencias.append(f'Peso: {peso_existente} → {peso_novo}')
                            print(f"     ✅ DIFERENÇA ENCONTRADA: Peso")
                    elif peso_existente is not None and peso_novo is None:
                        divergencias.append(f'Peso: {peso_existente} → (sem peso)')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Peso (BD tem, arquivo não)")
                    elif peso_existente is None and peso_novo is not None:
                        divergencias.append(f'Peso: (sem peso) → {peso_novo}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Peso (Arquivo tem, BD não)")
                    
                    if item_mesmo_endereco['embalagem'] != novo_item['embalagem']:
                        divergencias.append(f'Embalagem: {item_mesmo_endereco["embalagem"]} → {novo_item["embalagem"]}')
                        print(f"     ✅ DIFERENÇA ENCONTRADA: Embalagem")
                    
                    # FORÇAR DETECÇÃO SE NÃO ENCONTROU DIFERENÇAS
                    if len(divergencias) == 0:
                        print(f"     ⚠️  NENHUMA DIFERENÇA ENCONTRADA - FORÇANDO DETECÇÃO")
                        # Forçar como alteração se está na lista mas não tem divergências
                        divergencias.append(f'Atualização forçada - dados podem ter diferenças não detectadas')
                        print(f"     🔥 DIFERENÇA FORÇADA")
                    
                    print(f"  📊 Total de divergências encontradas: {len(divergencias)}")
                    
                    comparacao['lotes_alterados'].append({
                        'lote': lote,
                        'endereco': endereco_novo,
                        'divergencias': divergencias,
                        'dados_novos': novo_item,
                        'dados_atuais': item_mesmo_endereco
                    })
                    comparacao['resumo']['atualizados'] += 1
                    print(f"  🔄 Lote alterado - {len(divergencias)} divergência(s)")
            
            else:
                # Lote existe mas em ENDEREÇO DIFERENTE
                comparacao['lotes_multi_endereco'].append({
                    'lote': lote,
                    'novo_endereco': endereco_novo,
                    'enderecos_existentes': [{'endereco': e, 'saldo': next(item for item in itens_existentes if item['endereco'] == e)['saldo']} for e in enderecos_existentes],
                    'dados_novos': novo_item,
                    'total_outros_enderecos': sum(item['saldo'] for item in itens_existentes),
                    'alerta': f'Lote já existe em {len(enderecos_existentes)} outro(s) endereço(s): {", ".join(enderecos_existentes)}'
                })
                comparacao['resumo']['multi_endereco'] += 1
                print(f"  📍 Múltiplos endereços: {enderecos_existentes}")
        
        else:
            # Lote COMPLETAMENTE NOVO
            print(f"  🆕 Lote completamente novo")
            comparacao['novos_lotes'].append({
                'lote': lote,
                'endereco': endereco_novo,
                'dados': novo_item
            })
            comparacao['resumo']['novos'] += 1
    
    print("✅ [DEBUG COMPARAÇÃO] Comparação concluída:")
    print(f"  Novos: {comparacao['resumo']['novos']}")
    print(f"  Alterados: {comparacao['resumo']['atualizados']}") 
    print(f"  Iguais: {comparacao['resumo']['iguais']}")
    print(f"  Múltiplos: {comparacao['resumo']['multi_endereco']}")
    
    return comparacao

def sao_identicos(item_existente, item_novo):
    """Compara todos os campos para verificar se são idênticos - VERSÃO TOLERANTE"""
    try:
        # Comparação tolerante para números
        if abs(item_existente['saldo'] - item_novo['quantidade']) > 1:
            return False
        
        # Campos textuais
        campos_texto = [
            ('cultivar', 'cultivar'),
            ('peneira', 'peneira'), 
            ('embalagem', 'embalagem'),
            ('empresa', 'empresa')
        ]
        
        for campo_existente, campo_novo in campos_texto:
            valor_existente = str(item_existente.get(campo_existente, '') or '').strip().upper()
            valor_novo = str(item_novo.get(campo_novo, '') or '').strip().upper()
            
            if valor_existente != valor_novo:
                if valor_existente and valor_novo:
                    if valor_existente not in valor_novo and valor_novo not in valor_existente:
                        return False
                else:
                    return False
        
        # Tratamento mais flexível
        tratamento_existente = str(item_existente.get('tratamento', '') or '').strip().upper()
        tratamento_novo = str(item_novo.get('tratamento', '') or '').strip().upper()
        
        if tratamento_existente and tratamento_novo:
            if not tratamentos_sao_equivalentes(tratamento_existente, tratamento_novo):
                return False
        elif tratamento_existente != tratamento_novo:
            return False
        
        # Categoria mais flexível
        categoria_existente = str(item_existente.get('categoria', '')).strip().upper()
        categoria_nova = f"{item_novo.get('cultura', '')} - {item_novo.get('cultivar', '')}".strip().upper()
        
        if categoria_existente and categoria_nova:
            if categoria_existente not in categoria_nova and categoria_nova not in categoria_existente:
                return False
        
        # Peso unitário mais tolerante
        peso_existente = item_existente.get('peso_unitario')
        peso_novo = item_novo.get('peso_unitario')
        
        if peso_existente is None and peso_novo is None:
            pass
        elif peso_existente is None and peso_novo is not None:
            if abs(peso_novo) > 0.01:
                return False
        elif peso_existente is not None and peso_novo is None:
            if abs(peso_existente) > 0.01:
                return False
        elif abs(float(peso_existente) - float(peso_novo)) > 0.1:
            return False
            
        return True
        
    except (ValueError, TypeError) as e:
        print(f"⚠️ [DEBUG] Erro na comparação de identidade: {e}")
        return False

@login_required
def importar_estoque(request):
    """Importação DIRETA - trata lotes duplicados somando quantidades"""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            excel_file = request.FILES['excel_file']
            df = pd.read_excel(excel_file)
            
            # Mapeamento DIRETO
            column_mapping = {
                'lote': 'Lote',
                'quantidade': 'Quantidade', 
                'endereco': 'Endereco',
                'cultivar': 'Cultivar',
                'peneira': 'Peneira',
                'categoria': 'Categoria',
                'tratamento': 'Tp. Tratame.',
                'unidade': 'Unidade',
                'peso_med_ens': 'Peso Med Ens',
                'cultura': 'Cultura',
                'empresa': 'Empenho',
                'az': 'Armazem'
            }
            
            # Processar dados
            processed_data = []
            
            for index, row in df.iterrows():
                # Extrair dados básicos
                lote = str(row.get(column_mapping['lote'])).strip() if pd.notna(row.get(column_mapping['lote'])) else ''
                endereco = str(row.get(column_mapping['endereco'])).strip() if pd.notna(row.get(column_mapping['endereco'])) else ''
                quantidade = float(row.get(column_mapping['quantidade'])) if pd.notna(row.get(column_mapping['quantidade'])) else 0
                cultivar = str(row.get(column_mapping['cultivar'])).strip() if pd.notna(row.get(column_mapping['cultivar'])) else ''
                peneira = str(row.get(column_mapping['peneira'])).strip() if pd.notna(row.get(column_mapping['peneira'])) else ''
                categoria = str(row.get(column_mapping['categoria'])).strip() if pd.notna(row.get(column_mapping['categoria'])) else ''
                tratamento = str(row.get(column_mapping['tratamento'])).strip() if pd.notna(row.get(column_mapping['tratamento'])) else ''
                
                # Validar campos obrigatórios
                if not lote or not endereco or quantidade <= 0:
                    continue
                
                # Buscar/crear objetos relacionados
                cultivar_obj, _ = Cultivar.objects.get_or_create(nome=cultivar, defaults={'nome': cultivar})
                peneira_obj, _ = Peneira.objects.get_or_create(nome=peneira, defaults={'nome': peneira})
                
                # Truncar tratamento para 8 caracteres se necessário
                if tratamento and len(tratamento) > 8:
                    tratamento = tratamento[:8]
                tratamento_obj, _ = Tratamento.objects.get_or_create(nome=tratamento, defaults={'nome': tratamento})
                
                # Criar categoria se não existir
                if not categoria and cultivar:
                    categoria = f"SOJA - {cultivar}"
                categoria_obj, _ = Categoria.objects.get_or_create(nome=categoria, defaults={'nome': categoria})
                
                # Identificar embalagem
                unidade = str(row.get(column_mapping['unidade'])).strip().upper() if pd.notna(row.get(column_mapping['unidade'])) else ''
                embalagem = 'BAG'
                if 'SC' in unidade or 'SACO' in unidade:
                    embalagem = 'SC'
                
                # Calcular peso
                peso_med_ens = float(row.get(column_mapping['peso_med_ens'])) if pd.notna(row.get(column_mapping['peso_med_ens'])) else None
                peso_unitario = peso_med_ens if peso_med_ens and peso_med_ens > 0 else None
                
                processed_data.append({
                    'lote': lote,
                    'endereco': endereco,
                    'quantidade': quantidade,
                    'cultivar_id': cultivar_obj.id,
                    'peneira_id': peneira_obj.id,
                    'categoria_id': categoria_obj.id,
                    'tratamento_id': tratamento_obj.id,
                    'embalagem': embalagem,
                    'peso_unitario': peso_unitario,
                    'empresa': str(row.get(column_mapping['empresa'])).strip() if pd.notna(row.get(column_mapping['empresa'])) else '',
                    'az': str(row.get(column_mapping['az'])).strip() if pd.notna(row.get(column_mapping['az'])) else '',
                    'cultura': str(row.get(column_mapping['cultura'])).strip() if pd.notna(row.get(column_mapping['cultura'])) else 'SOJA',
                })
            
            # Comparação DIRETA com estoque atual
            comparacao = {
                'novos_lotes': [],
                'lotes_alterados': [],
                'lotes_iguais': [],
                'lotes_duplicados': [],  # 🔥 NOVO: Lotes que serão consolidados
                'resumo': {'novos': 0, 'atualizados': 0, 'iguais': 0, 'duplicados': 0}
            }
            
            for novo_item in processed_data:
                lote = novo_item['lote']
                endereco = novo_item['endereco']
                
                # 🔥 VERIFICAR SE EXISTEM REGISTROS DUPLICADOS NO BANCO
                registros_duplicados = Estoque.objects.filter(lote=lote)
                total_duplicados = registros_duplicados.count()
                saldo_total_duplicados = sum([r.saldo for r in registros_duplicados])
                
                # Verificar se existe no banco (lote + endereço específico)
                existe_mesmo_endereco = Estoque.objects.filter(lote=lote, endereco=endereco).exists()
                
                if existe_mesmo_endereco:
                    # Buscar item existente para comparar
                    item_existente = Estoque.objects.filter(lote=lote, endereco=endereco).first()
                    
                    # Verificar se é IDÊNTICO
                    if (item_existente.saldo == novo_item['quantidade'] and
                        item_existente.cultivar_id == novo_item['cultivar_id'] and
                        item_existente.peneira_id == novo_item['peneira_id'] and
                        item_existente.categoria_id == novo_item['categoria_id'] and
                        item_existente.tratamento_id == novo_item['tratamento_id']):
                        
                        comparacao['lotes_iguais'].append({
                            'lote': lote,
                            'endereco': endereco,
                            'dados': novo_item
                        })
                        comparacao['resumo']['iguais'] += 1
                    else:
                        # DIFERENTE - marcar para ATUALIZAR
                        comparacao['lotes_alterados'].append({
                            'lote': lote,
                            'endereco': endereco,
                            'dados_novos': novo_item,
                            'dados_atuais': {
                                'saldo': item_existente.saldo,
                                'cultivar_id': item_existente.cultivar_id,
                                'peneira_id': item_existente.peneira_id,
                                'categoria_id': item_existente.categoria_id,
                                'tratamento_id': item_existente.tratamento_id,
                            }
                        })
                        comparacao['resumo']['atualizados'] += 1
                
                elif total_duplicados > 1:
                    # 🔥 CASO ESPECIAL: Lote existe em múltiplos endereços - CONSOLIDAR
                    enderecos_atuais = [r.endereco for r in registros_duplicados]
                    
                    comparacao['lotes_duplicados'].append({
                        'lote': lote,
                        'novo_endereco': endereco,
                        'enderecos_atuais': enderecos_atuais,
                        'saldo_total_atual': saldo_total_duplicados,
                        'nova_quantidade': novo_item['quantidade'],
                        'dados_novos': novo_item,
                        'alerta': f'Lote será consolidado: {len(enderecos_atuais)} endereços → 1 endereço'
                    })
                    comparacao['resumo']['duplicados'] += 1
                    
                elif total_duplicados == 1:
                    # Lote existe mas em ENDEREÇO DIFERENTE - MOVER
                    item_existente = registros_duplicados.first()
                    
                    comparacao['lotes_alterados'].append({
                        'lote': lote,
                        'endereco': endereco,
                        'dados_novos': novo_item,
                        'dados_atuais': {
                            'saldo': item_existente.saldo,
                            'endereco_original': item_existente.endereco,
                            'cultivar_id': item_existente.cultivar_id,
                            'peneira_id': item_existente.peneira_id,
                            'categoria_id': item_existente.categoria_id,
                            'tratamento_id': item_existente.tratamento_id,
                        },
                        'alerta': f'Mudança de endereço: {item_existente.endereco} → {endereco}'
                    })
                    comparacao['resumo']['atualizados'] += 1
                    
                else:
                    # NOVO - marcar para CRIAR
                    comparacao['novos_lotes'].append({
                        'lote': lote,
                        'endereco': endereco,
                        'dados': novo_item
                    })
                    comparacao['resumo']['novos'] += 1
            
            return JsonResponse({
                'success': True,
                'processed_count': len(processed_data),
                'comparacao': comparacao,
                'preview_data': processed_data[:5]
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao processar arquivo: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def aprovar_importacao(request):
    """APLICA as modificações - CONSOLIDA lotes duplicados"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = request.user
            
            with transaction.atomic():
                modificacoes = data.get('modificacoes', [])
                aplicados_count = 0
                
                for mod in modificacoes:
                    if mod['tipo'] == 'novo':
                        # CRIAR novo registro
                        Estoque.objects.create(
                            lote=mod['lote'],
                            cultivar_id=mod['cultivar_id'],
                            peneira_id=mod['peneira_id'],
                            categoria_id=mod['categoria_id'],
                            tratamento_id=mod['tratamento_id'],
                            endereco=mod['endereco'],
                            entrada=mod['quantidade'],
                            saida=0,
                            saldo=mod['quantidade'],
                            conferente=user,
                            origem_destino='Importação',
                            data_entrada=timezone.now(),
                            especie=mod.get('cultura', 'SOJA'),
                            empresa=mod.get('empresa', ''),
                            embalagem=mod.get('embalagem', 'BAG'),
                            peso_unitario=mod.get('peso_unitario'),
                            observacao=f"Importado em {timezone.now().strftime('%d/%m/%Y')}"
                        )
                        aplicados_count += 1
                    
                    elif mod['tipo'] == 'atualizar':
                        # ATUALIZAR registro existente
                        item = Estoque.objects.get(lote=mod['lote'], endereco=mod.get('endereco_original', mod['endereco']))
                        
                        item.cultivar_id = mod['cultivar_id']
                        item.peneira_id = mod['peneira_id']
                        item.categoria_id = mod['categoria_id']
                        item.tratamento_id = mod['tratamento_id']
                        item.endereco = mod['endereco']  # 🔥 Pode mudar o endereço
                        item.entrada = mod['quantidade']
                        item.saldo = mod['quantidade']
                        item.saida = 0
                        item.embalagem = mod.get('embalagem', 'BAG')
                        item.peso_unitario = mod.get('peso_unitario')
                        item.empresa = mod.get('empresa', '')
                        item.az = mod.get('az', '')
                        item.conferente = user
                        item.observacao = f"Atualizado em {timezone.now().strftime('%d/%m/%Y')}"
                        
                        item.save()
                        aplicados_count += 1
                    
                    elif mod['tipo'] == 'consolidar':
                        # 🔥 CONSOLIDAR lotes duplicados - EXCLUIR TODOS E CRIAR UM NOVO
                        # Primeiro, excluir todos os registros duplicados
                        Estoque.objects.filter(lote=mod['lote']).delete()
                        
                        # Criar um NOVO registro consolidado
                        Estoque.objects.create(
                            lote=mod['lote'],
                            cultivar_id=mod['cultivar_id'],
                            peneira_id=mod['peneira_id'],
                            categoria_id=mod['categoria_id'],
                            tratamento_id=mod['tratamento_id'],
                            endereco=mod['endereco'],
                            entrada=mod['quantidade'],
                            saida=0,
                            saldo=mod['quantidade'],
                            conferente=user,
                            origem_destino='Importação',
                            data_entrada=timezone.now(),
                            especie=mod.get('cultura', 'SOJA'),
                            empresa=mod.get('empresa', ''),
                            embalagem=mod.get('embalagem', 'BAG'),
                            peso_unitario=mod.get('peso_unitario'),
                            observacao=f"Consolidado de múltiplos endereços em {timezone.now().strftime('%d/%m/%Y')}"
                        )
                        aplicados_count += 1
                
                return JsonResponse({
                    'success': True,
                    'message': f'{aplicados_count} registros processados com sucesso'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro ao aplicar modificações: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})