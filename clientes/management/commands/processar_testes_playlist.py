import time
from django.core.management.base import BaseCommand
from clientes.playlist_test_service import processar_testes_vencidos


class Command(BaseCommand):
    help = 'Desativa testes de playlist vencidos. Use --watch para manter o processo rodando.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')
        parser.add_argument('--interval', type=int, default=30)

    def handle(self, *args, **options):
        watch = options['watch']
        interval = max(10, options['interval'])
        while True:
            resultados = processar_testes_vencidos()
            if resultados:
                self.stdout.write(self.style.SUCCESS(f'{len(resultados)} teste(s) processado(s).'))
            if not watch:
                break
            time.sleep(interval)
