# financeiro/views/api.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from clientes.models import RelatorioFinanceiro


@login_required
def api_relatorio_financeiro(request, id):
    """API para obter dados de relatório financeiro"""
    try:
        relatorio = get_object_or_404(RelatorioFinanceiro, id=id)
        
        usuario = request.user
        tipo_usuario = getattr(usuario, 'tipo_usuario', 'cliente')
        
        permitido = False
        if usuario.is_superuser:
            permitido = True
        elif tipo_usuario in ['admin', 'revenda']:
            from clientes.models import CustomUser
            clientes_permitidos = CustomUser.objects.filter(dono=usuario)
            permitido = relatorio.cliente in clientes_permitidos
        else:
            permitido = relatorio.cliente == usuario
        
        if not permitido:
            return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
        
        data = {
            'success': True,
            'data': {
                'id': relatorio.id,
                'servidor': relatorio.servidor or '',
                'valor_pago': str(relatorio.valor_pago),
                'valor_servico': str(relatorio.valor_servico),
                'data_geracao': relatorio.data_geracao.strftime('%Y-%m-%dT%H:%M'),
            }
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)