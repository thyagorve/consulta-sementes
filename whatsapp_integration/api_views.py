# whatsapp_integration/api_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
import json
from clientes.models import CustomUser, Servico, Tag
from .models import MensagemMassa, HistoricoEnvioMassa
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST
def api_filter_clients(request):
    """Filtra clientes e retorna contagem/lista"""
    try:
        data = request.POST
        user = request.user
        
        # Base: Clientes do usuário
        clientes = CustomUser.objects.filter(dono=user)
        
        # Filtros
        status = data.get('status', '')
        if status == 'ativos':
            clientes = clientes.filter(is_active=True)
        elif status == 'vencidos':
            hoje = timezone.now().date()
            clientes = clientes.filter(is_active=True, data_vencimento__lt=hoje)
            dias = data.get('dias_vencido')
            if dias and dias.isdigit():
                limite = hoje - timezone.timedelta(days=int(dias))
                clientes = clientes.filter(data_vencimento__gte=limite)
        elif status == 'desativados':
            clientes = clientes.filter(is_active=False)

        if data.get('plano'):
            clientes = clientes.filter(plano_id=data.get('plano'))

        # Filtro Tags (JSON)
        tags_json = data.get('tags_json', '[]')
        try:
            tags_data = json.loads(tags_json)
            if tags_data:
                ids = [t['id'] for t in tags_data]
                clientes = clientes.filter(tags__id__in=ids).distinct()
        except:
            pass

        count = clientes.count()
        # Retorna apenas dados essenciais para o preview (limitado a 50)
        lista = list(clientes.values('id', 'nome', 'whatsapp')[:50])
        
        return JsonResponse({'success': True, 'count': count, 'clientes': lista})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def api_schedule_mass_message(request):
    """Agenda o envio (Salva no banco com status Agendada)"""
    try:
        data = request.POST
        user = request.user
        
        # Recupera dados
        msg_texto = data.get('mensagem')
        ids_json = data.get('clientes_ids', '[]')
        data_str = data.get('data_agendamento') # YYYY-MM-DD
        hora_str = data.get('hora_agendamento') # HH:MM
        
        if not msg_texto:
            return JsonResponse({'success': False, 'message': 'Mensagem vazia.'})

        # Processa Data
        data_final = timezone.now()
        if data_str and hora_str:
            dt_str = f"{data_str} {hora_str}"
            dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
            data_final = timezone.make_aware(dt_obj)

        # Processa Clientes
        try:
            client_ids = json.loads(ids_json)
        except:
            client_ids = []
            
        if not client_ids:
            return JsonResponse({'success': False, 'message': 'Nenhum cliente selecionado.'})

        # --- CRIAÇÃO CORRIGIDA ---
        mensagem_massa = MensagemMassa.objects.create(
            remetente=user,
            mensagem=msg_texto,
            data_agendamento=data_final, # Nome correto do campo
            agendada=True,
            status='agendada',
            total_destinatarios=len(client_ids)
        )

        # Salva anexo se houver
        if 'midia' in request.FILES:
            mensagem_massa.midia = request.FILES['midia'] # Nome correto do campo
            mensagem_massa.tipo_midia = request.FILES['midia'].content_type
            mensagem_massa.save()

        # Cria históricos individuais (Bulk Create para performance)
        historicos = []
        # Busca clientes para pegar whatsapp atualizado
        clientes_db = CustomUser.objects.filter(id__in=client_ids)
        
        for cli in clientes_db:
            historicos.append(HistoricoEnvioMassa(
                mensagem_massa=mensagem_massa,
                cliente=cli,
                whatsapp=cli.whatsapp or '',
                status='pendente'
            ))
        
        HistoricoEnvioMassa.objects.bulk_create(historicos)

        return JsonResponse({
            'success': True, 
            'message': f'Agendado para {len(historicos)} clientes!',
            'redirect_url': f'/whatsapp/mensagens/{mensagem_massa.id}/' # URL ajustada
        })

    except Exception as e:
        logger.error(f"Erro ao agendar: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
@require_POST
def api_save_mass_message_draft(request):
    """Salva como Rascunho"""
    try:
        data = request.POST
        user = request.user
        
        mensagem_massa = MensagemMassa.objects.create(
            remetente=user,
            mensagem=data.get('mensagem', ''),
            data_agendamento=timezone.now(), # Campo obrigatório no model
            agendada=False,
            status='rascunho',
            total_destinatarios=0
        )
        
        # Salva anexo se houver
        if 'midia' in request.FILES:
            mensagem_massa.midia = request.FILES['midia']
            mensagem_massa.save()

        return JsonResponse({
            'success': True, 
            'message': 'Rascunho salvo!',
            'redirect_url': f'/whatsapp/mensagens/{mensagem_massa.id}/'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)






@login_required
def api_get_message_status(request, message_id):
    """API para obter status de uma mensagem em massa"""
    try:
        mensagem = MensagemMassa.objects.get(
            id=message_id,
            remetente=request.user
        )
        
        historicos = mensagem.historicos.all()
        status_count = {
            'pendente': historicos.filter(status='pendente').count(),
            'enviado': historicos.filter(status='enviado').count(),
            'falha': historicos.filter(status='falha').count(),
            'entregue': historicos.filter(status='entregue').count(),
            'lido': historicos.filter(status='lido').count(),
        }
        
        return JsonResponse({
            'success': True,
            'status': mensagem.status,
            'status_display': mensagem.get_status_display(),
            'progresso': {
                'total': mensagem.total_destinatarios,
                'sucesso': mensagem.enviados_com_sucesso,
                'falha': mensagem.enviados_com_falha,
                'pendente': status_count['pendente']
            },
            'detalhes': status_count,
            'data_envio_inicio': mensagem.data_envio_inicio.isoformat() if mensagem.data_envio_inicio else None,
            'data_envio_fim': mensagem.data_envio_fim.isoformat() if mensagem.data_envio_fim else None,
        })
        
    except MensagemMassa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Mensagem não encontrada'
        }, status=404)
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao obter status: {str(e)}'
        }, status=500)