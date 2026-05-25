# almoxarifado/management/commands/verificar_estoque_almoxarifado.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from almoxarifado.models import ConfiguracaoNotificacao
from almoxarifado.services import notificacao_service

class Command(BaseCommand):
    help = 'Verifica estoque do almoxarifado e envia notificações'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Iniciando verificação de estoque...")
        
        config = ConfiguracaoNotificacao.get_config()
        
        if not config.ativo or not config.verificar_agendado:
            self.stdout.write("⚠️ Sistema de notificações desativado ou verificação agendada desligada")
            return
        
        # Verificar se está no horário (opcional)
        from datetime import datetime
        agora = datetime.now().time()
        
        if config.horario_verificacao:
            # Verificar se passou do horário (considerando margem de 15 minutos)
            from datetime import timedelta
            inicio = datetime.combine(datetime.today(), config.horario_verificacao)
            fim = inicio + timedelta(minutes=15)
            hora_atual = datetime.combine(datetime.today(), agora)
            
            if not (inicio <= hora_atual <= fim):
                self.stdout.write(f"⏰ Fora do horário de verificação ({config.horario_verificacao})")
                return
        
        # Executar verificação
        resultados = notificacao_service.verificar_todos_itens()
        
        total_notificacoes = sum(len(r['resultados']) for r in resultados)
        self.stdout.write(f"✅ Verificação concluída! {total_notificacoes} notificações enviadas.")