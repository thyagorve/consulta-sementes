# sapp/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

@receiver(post_migrate)
def criar_grupos_padrao(sender, **kwargs):
    """Cria grupos padrão após as migrações (sem permissões automáticas)"""
    
    # Só executa para o app sapp
    if sender.name != 'sapp':
        return
    
    print("🔧 Configurando grupos padrão do sistema...")
    
    try:
        # Buscar o ContentType do Produto
        content_type = ContentType.objects.get(app_label='sapp', model='produto')
        
        # Mapeamento de permissões (apenas para referência)
        permissoes = {
            'pode_ver_estoque': Permission.objects.get(codename='pode_ver_estoque', content_type=content_type),
            'pode_movimentar_estoque': Permission.objects.get(codename='pode_movimentar_estoque', content_type=content_type),
            'pode_ver_dashboard': Permission.objects.get(codename='pode_ver_dashboard', content_type=content_type),
            'pode_ver_empenhos': Permission.objects.get(codename='pode_ver_empenhos', content_type=content_type),
            'pode_criar_empenhos': Permission.objects.get(codename='pode_criar_empenhos', content_type=content_type),
            'pode_ver_mapa': Permission.objects.get(codename='pode_ver_mapa', content_type=content_type),
            'pode_gerenciar_usuarios': Permission.objects.get(codename='pode_gerenciar_usuarios', content_type=content_type),
            'pode_configuracoes': Permission.objects.get(codename='pode_configuracoes', content_type=content_type),
        }
        
        # 🔥 APENAS CRIAR GRUPOS - SEM ADICIONAR PERMISSÕES AUTOMATICAMENTE
        grupos = ['admin', 'conferente', 'almoxarife', 'operador']
        
        for grupo_nome in grupos:
            group, created = Group.objects.get_or_create(name=grupo_nome)
            if created:
                print(f"   ✅ Grupo '{grupo_nome}' criado (sem permissões automáticas)")
            else:
                print(f"   📌 Grupo '{grupo_nome}' já existe")
            
            # 🔥 NÃO adiciona permissões automaticamente
            # As permissões serão gerenciadas individualmente pela interface
        
        print("   ✅ Grupos configurados! Permissões serão gerenciadas individualmente.")
        
    except Exception as e:
        print(f"   ❌ Erro ao configurar grupos: {e}")
# ---------------------------------------------------------------------------
# Versionamento de lote para sincronização offline.
# Toda movimentação criada online ou via sync incrementa a versão do lote.
# ---------------------------------------------------------------------------
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save
from sapp.models import HistoricoMovimentacao, LoteSyncState, LoteSyncEvento


@receiver(post_save, sender=HistoricoMovimentacao)
def versionar_lote_apos_movimentacao(sender, instance, created, **kwargs):
    if not created:
        return

    lote = str(instance.lote_ref or '').strip()
    if not lote and instance.estoque_id:
        lote = str(instance.estoque.lote or '').strip()
    if not lote:
        return

    # Transação curta. Em concorrência, o lock serializa a próxima versão.
    with transaction.atomic():
        state, _ = LoteSyncState.objects.select_for_update().get_or_create(
            lote=lote,
            defaults={
                'versao': 0,
                'atualizado_por': instance.usuario,
            },
        )
        state.versao = int(state.versao or 0) + 1
        state.atualizado_por = instance.usuario
        state.save(update_fields=['versao', 'atualizado_por', 'atualizado_em'])

        LoteSyncEvento.objects.create(
            lote=lote,
            versao=state.versao,
            usuario=instance.usuario,
            historico=instance,
            tipo=instance.tipo or '',
        )
