from django.core.management.base import BaseCommand
from django.utils import timezone
from clientes.models import CustomUser
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Limpa avatares do WhatsApp expirados'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Número de dias para considerar expirado (padrão: 7)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Limpar avatares expirados
        expired_users = CustomUser.objects.filter(
            whatsapp_avatar_expires__lt=timezone.now(),
            whatsapp_avatar_status='found'
        )
        
        count = expired_users.count()
        
        for user in expired_users:
            user.whatsapp_avatar_status = 'pending'
            user.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Marcados {count} avatares como expirados')
        )
        logger.info(f'Marcados {count} avatares como expirados')