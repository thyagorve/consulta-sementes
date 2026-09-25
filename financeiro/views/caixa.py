# financeiro/views/caixa.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
from datetime import datetime

from clientes.models import MovimentacaoCaixa


def converter_valor_br_para_decimal(valor_str):
    """Converte string de valor brasileiro para Decimal"""
    if not valor_str:
        return Decimal('0')
    valor_str = valor_str.replace('R$', '').replace(' ', '').strip()
    if not valor_str:
        return Decimal('0')
    if ',' in valor_str:
        if '.' in valor_str:
            partes = valor_str.split(',')
            if len(partes) == 2:
                inteiro = partes[0].replace('.', '')
                decimal = partes[1]
                valor_str = f"{inteiro}.{decimal}"
        else:
            valor_str = valor_str.replace(',', '.')
    try:
        return Decimal(valor_str)
    except:
        return Decimal('0')


@login_required
def adicionar_movimentacao_caixa(request):
    """Adiciona uma nova movimentação de caixa"""
    if request.method == 'POST':
        try:
            usuario = request.user
            valor = converter_valor_br_para_decimal(request.POST.get('valor', '0'))
            tipo = request.POST.get('tipo', 'entrada')
            descricao = request.POST.get('descricao', '').strip()
            categoria = request.POST.get('categoria', 'outros')
            data_personalizada = request.POST.get('data_personalizada', None)
            
            if not descricao:
                messages.error(request, 'A descrição é obrigatória.')
                return redirect('financeiro:relatorio_financeiro')
            
            if valor <= Decimal('0'):
                messages.error(request, 'O valor deve ser maior que zero.')
                return redirect('financeiro:relatorio_financeiro')
            
            # Processar data personalizada
            if data_personalizada:
                try:
                    data_mov = datetime.strptime(data_personalizada, '%Y-%m-%dT%H:%M')
                    data_mov = timezone.make_aware(data_mov)
                except:
                    data_mov = timezone.now()
            else:
                data_mov = timezone.now()
            
            MovimentacaoCaixa.objects.create(
                usuario=usuario,
                valor=valor,
                tipo=tipo,
                descricao=descricao,
                categoria=categoria,
                data=data_mov
            )
            
            tipo_display = 'Entrada' if tipo == 'entrada' else 'Saída'
            messages.success(
                request, 
                f'{tipo_display} de R$ {valor:.2f} registrada com sucesso em {data_mov.strftime("%d/%m/%Y %H:%M")}!'
            )
        except Exception as e:
            messages.error(request, f'Erro ao registrar movimentação: {str(e)}')
    
    return redirect('financeiro:relatorio_financeiro')


@login_required
def editar_movimentacao_caixa(request, id):
    """Edita uma movimentação de caixa existente"""
    if request.method == 'POST':
        try:
            movimentacao = get_object_or_404(MovimentacaoCaixa, id=id, usuario=request.user)
            
            movimentacao.tipo = request.POST.get('tipo', movimentacao.tipo)
            movimentacao.valor = converter_valor_br_para_decimal(
                request.POST.get('valor', str(movimentacao.valor))
            )
            movimentacao.descricao = request.POST.get('descricao', movimentacao.descricao)
            movimentacao.categoria = request.POST.get('categoria', movimentacao.categoria)
            
            data_str = request.POST.get('data')
            if data_str:
                try:
                    data_mov = datetime.strptime(data_str, '%Y-%m-%dT%H:%M')
                    movimentacao.data = timezone.make_aware(data_mov)
                except:
                    pass
            
            movimentacao.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar movimentação: {str(e)}')
    
    return redirect('financeiro:relatorio_financeiro')


@login_required
def excluir_movimentacao_caixa(request, id):
    """Exclui uma movimentação de caixa"""
    if request.method == 'POST':
        try:
            movimentacao = get_object_or_404(MovimentacaoCaixa, id=id, usuario=request.user)
            movimentacao.delete()
            messages.success(request, 'Movimentação excluída com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir movimentação: {str(e)}')
    
    return redirect('financeiro:relatorio_financeiro')


@login_required
def api_movimentacao_caixa(request, id=None):
    """API para retornar dados de uma movimentação de caixa em JSON"""
    if id:
        try:
            movimentacao = get_object_or_404(MovimentacaoCaixa, id=id, usuario=request.user)
            return JsonResponse({
                'id': movimentacao.id,
                'tipo': movimentacao.tipo,
                'valor': str(movimentacao.valor),
                'descricao': movimentacao.descricao,
                'categoria': movimentacao.categoria or 'outros',
                'data': movimentacao.data.strftime('%Y-%m-%dT%H:%M'),
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'ID não fornecido'}, status=400)