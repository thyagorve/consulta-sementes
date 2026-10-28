from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando legado mantido por compatibilidade; não envia mensagens externas.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'Alertas externos do Almoxarifado estão desativados. Nenhuma chamada de rede foi executada.'
        ))
