# clientes/management/commands/executar_backups.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from clientes.models import BackupSchedule
from clientes.views_backup import executar_backup_agendado
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Executa backups automáticos agendados'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Verificando backups agendados...')
        
        # Usa a função centralizada do views_backup
        executar_backup_agendado()
        
        self.stdout.write(self.style.SUCCESS('✅ Verificação de backups concluída!'))