from datetime import timedelta
# sapp/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone
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

# ---------------------------------------------------------------------------
# Ponto de restauração automático para toda movimentação de item empenhado.
# O ponto é criado independentemente de quem movimentou. A restauração em si
# é exposta apenas na Central Administrativa.
# ---------------------------------------------------------------------------
from sapp.models import HistoricoItemEmpenho, PontoRestauracaoMovimentacao


@receiver(post_save, sender=HistoricoItemEmpenho)
def criar_ponto_restauracao_movimentacao(sender, instance, created, **kwargs):
    if not created:
        return

    solicitacao = None
    try:
        solicitacao = instance.empenho.solicitacao
    except Exception:
        solicitacao = None

    estado = {}
    if solicitacao is not None:
        estado = {
            'status': solicitacao.status,
            'quantidade_solicitada': str(solicitacao.quantidade_solicitada or 0),
            'quantidade_empenhada': str(solicitacao.quantidade_empenhada or 0),
            'quantidade_movimentada': str(solicitacao.quantidade_movimentada or 0),
            'coluna_kanban_id': solicitacao.coluna_kanban_id,
            'data_finalizacao': (
                timezone.localtime(solicitacao.data_finalizacao).isoformat()
                if solicitacao.data_finalizacao else None
            ),
        }

    historicos_gerais_ids = []
    if instance.processado_em:
        inicio = instance.processado_em - timedelta(seconds=60)
        fim = instance.processado_em + timedelta(seconds=5)
        pares = []
        if instance.tipo == 'transferencia':
            pares = [
                (instance.estoque_origem_id, 'Transferência (Saída)'),
                (instance.estoque_destino_id, 'Transferência (Entrada)'),
            ]
        elif instance.tipo == 'expedicao':
            pares = [(instance.estoque_origem_id, 'Expedição')]

        for estoque_id, tipo_geral in pares:
            if not estoque_id:
                continue
            geral = (
                HistoricoMovimentacao.objects
                .filter(
                    estoque_id=estoque_id,
                    tipo=tipo_geral,
                    quantidade=instance.quantidade,
                    data_hora__gte=inicio,
                    data_hora__lte=fim,
                )
                .order_by('-data_hora', '-id')
                .first()
            )
            if geral:
                historicos_gerais_ids.append(geral.id)

    PontoRestauracaoMovimentacao.objects.get_or_create(
        historico=instance,
        defaults={
            'historico_id_original': instance.id,
            'solicitacao': solicitacao,
            'criado_por': instance.processado_por,
            'tipo': instance.tipo or '',
            'lote': instance.lote or '',
            'quantidade': instance.quantidade or 0,
            'endereco_origem': instance.endereco_origem or '',
            'endereco_destino': instance.endereco_destino or '',
            'descricao': (
                f'{instance.get_tipo_display()} do lote {instance.lote or "-"} '
                f'({instance.quantidade or 0})'
            ),
            'estado_solicitacao': estado,
            'historicos_gerais_ids': historicos_gerais_ids,
        },
    )
