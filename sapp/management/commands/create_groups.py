from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Mantém grupos legados vazios; o acesso é gerenciado por permissões individuais.'

    def handle(self, *args, **options):
        grupos = ['admin', 'conferente', 'almoxarife', 'operador']
        for nome in grupos:
            grupo, created = Group.objects.get_or_create(name=nome)
            grupo.permissions.clear()
            status = 'criado' if created else 'mantido'
            self.stdout.write(f'Grupo {nome}: {status}, sem permissões automáticas.')

        self.stdout.write(self.style.SUCCESS(
            'Permissões de acesso devem ser atribuídas individualmente pela tela de usuários.'
        ))
