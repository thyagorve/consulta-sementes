from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando legado mantido por compatibilidade. A integração externa foi removida.'

    def add_arguments(self, parser):
        # Aceita argumentos antigos sem executar rede, evitando quebrar agendadores legados.
        parser.add_argument('--agendado', action='store_true')
        parser.add_argument('--agora', action='store_true')
        parser.add_argument('--tipo')
        parser.add_argument('--departamento')
        parser.add_argument('--testar-conexao', dest='testar_conexao')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'Integração externa/WhatsApp do Almoxarifado foi removida. Nenhuma chamada de rede foi executada.'
        ))
