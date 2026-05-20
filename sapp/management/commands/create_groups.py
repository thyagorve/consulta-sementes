# sapp/management/commands/create_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from sapp.models import Produto, Armazem, Endereco

class Command(BaseCommand):
    help = 'Cria grupos e permissões padrão do sistema'
    
    def handle(self, *args, **options):
        # Lista de permissões disponíveis
        permissions = [
            {'codename': 'pode_ver_estoque', 'name': 'Pode visualizar estoque'},
            {'codename': 'pode_movimentar_estoque', 'name': 'Pode movimentar estoque'},
            {'codename': 'pode_ver_almoxarifado', 'name': 'Pode visualizar almoxarifado'},
            {'codename': 'pode_gerenciar_almoxarifado', 'name': 'Pode gerenciar almoxarifado'},
            {'codename': 'pode_ver_empenhos', 'name': 'Pode visualizar empenhos'},
            {'codename': 'pode_criar_empenhos', 'name': 'Pode criar empenhos'},
            {'codename': 'pode_ver_mapa', 'name': 'Pode acessar mapa canvas'},
            {'codename': 'pode_gerenciar_usuarios', 'name': 'Pode gerenciar usuários'},
            {'codename': 'pode_configuracoes', 'name': 'Pode alterar configurações'},
        ]
        
        # Cria as permissões (associadas ao ContentType de Produto como referência)
        content_type = ContentType.objects.get_for_model(Produto)
        for perm in permissions:
            Permission.objects.get_or_create(
                codename=perm['codename'],
                content_type=content_type,
                defaults={'name': perm['name']}
            )
        
        # Define permissões por grupo
        grupos = {
            'admin': [p['codename'] for p in permissions],  # Todas
            'conferente': ['pode_ver_estoque', 'pode_movimentar_estoque', 'pode_ver_empenhos'],
            'almoxarife': ['pode_ver_estoque', 'pode_ver_almoxarifado', 'pode_gerenciar_almoxarifado', 'pode_ver_mapa'],
            'operador': ['pode_ver_estoque', 'pode_ver_empenhos', 'pode_ver_mapa'],
        }
        
        for group_name, perms in grupos.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Grupo "{group_name}" criado'))
            else:
                self.stdout.write(f'📌 Grupo "{group_name}" já existe')
            
            # Adiciona permissões ao grupo
            for perm_codename in perms:
                try:
                    perm = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'⚠️ Permissão "{perm_codename}" não encontrada'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Grupos e permissões configurados com sucesso!'))