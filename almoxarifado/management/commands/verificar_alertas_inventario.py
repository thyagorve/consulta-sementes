# almoxarifado/management/commands/verificar_alertas_inventario.py
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import (
    DadosValidadeItem,
    DisparoRegraNotificacao,
    EstadoNotificacaoItem,
    Item,
    RegraNotificacaoAlmoxarifado,
)
from ...services import get_notificacao_service

try:
    from ...models import ConfiguracaoWhatsApp
except ImportError:
    ConfiguracaoWhatsApp = None


class Command(BaseCommand):
    help = 'Verifica regras de estoque/vencimento e envia WhatsApp.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoje = timezone.localdate()

        regras = RegraNotificacaoAlmoxarifado.objects.filter(ativo=True)
        itens = Item.objects.filter(ativo=True).select_related('dados_validade')

        if not regras.exists():
            self.stdout.write('Nenhuma regra ativa.')
            return

        if ConfiguracaoWhatsApp is None:
            self.stdout.write(self.style.ERROR('ConfiguracaoWhatsApp não encontrada.'))
            return

        config = ConfiguracaoWhatsApp.get_config()
        if not getattr(config, 'ativo', False):
            self.stdout.write(self.style.WARNING('WhatsApp desativado.'))
            return

        service = get_notificacao_service()
        enviados = 0

        for item in itens.iterator():
            qtd = Decimal(str(getattr(item, 'quantidade', 0) or 0))
            minimo = Decimal(str(getattr(item, 'estoque_minimo', 0) or 0))
            dept = str(getattr(item, 'departamento', '') or '')
            validade = getattr(item, 'dados_validade', None)
            venc = validade.data_vencimento if validade else None
            dias = (venc - hoje).days if venc else None

            estado, _ = EstadoNotificacaoItem.objects.get_or_create(
                item=item,
                defaults={'quantidade_anterior': qtd},
            )
            anterior = Decimal(str(estado.quantidade_anterior or 0))
            reposto = qtd > anterior

            for regra in regras:
                if regra.departamentos and dept not in regra.departamentos:
                    continue

                eventos = []

                if regra.tipo == 'ESTOQUE_BAIXO' and qtd > 0 and qtd <= minimo:
                    eventos.append(('estoque_baixo', f'baixo:{qtd}', '⚠️ Estoque abaixo do mínimo'))

                elif regra.tipo == 'ESTOQUE_ABAIXO_X':
                    lim = Decimal(str(regra.quantidade_limite or 0))
                    if qtd < lim:
                        eventos.append(('estoque_abaixo_x', f'abaixo:{lim}:{qtd}', f'⚠️ Estoque abaixo de {lim}'))

                elif regra.tipo == 'ESTOQUE_ZERADO' and qtd <= 0:
                    eventos.append(('estoque_zerado', 'zerado', '🚨 Estoque zerado'))

                elif regra.tipo == 'ESTOQUE_REPOSTO' and reposto:
                    eventos.append(('estoque_reposto', f'reposto:{anterior}:{qtd}', f'✅ Estoque reposto: {anterior} → {qtd}'))

                elif regra.tipo == 'VENCE_EM' and venc is not None:
                    for n in regra.dias_antes_vencimento or []:
                        try:
                            n = int(n)
                        except Exception:
                            continue
                        if dias == n:
                            eventos.append(('vence_em', f'vence:{venc}:dias:{n}', f'⏳ Vence em {n} dia(s)'))

                elif regra.tipo == 'VENCE_HOJE' and dias == 0:
                    eventos.append(('vence_hoje', f'vence:{venc}:hoje', '📅 Vence hoje'))

                elif regra.tipo == 'VENCIDO' and dias is not None and dias < 0:
                    eventos.append(('vencido', f'vencido:{venc}', f'❌ Produto vencido há {abs(dias)} dia(s)'))

                for _, chave, evento in eventos:
                    if not self._pode_disparar(regra, item, chave):
                        continue

                    numeros = config.get_numeros_destino(dept)
                    if not numeros:
                        continue

                    mensagem = self._mensagem(
                        regra,
                        item,
                        evento,
                        venc,
                        dias,
                    )

                    for numero in numeros:
                        if dry_run:
                            self.stdout.write(f'[DRY] {numero}: {mensagem[:80]}')
                            continue

                        sucesso, resposta = service.enviar_mensagem(numero, mensagem)
                        DisparoRegraNotificacao.objects.create(
                            regra=regra,
                            item=item,
                            chave_evento=chave,
                            destinatario=numero,
                            sucesso=bool(sucesso),
                            resposta=str(resposta)[:2000],
                        )
                        if sucesso:
                            enviados += 1

            estado.quantidade_anterior = qtd
            estado.save(update_fields=['quantidade_anterior', 'atualizado_em'])

        self.stdout.write(self.style.SUCCESS(f'Concluído. Envios: {enviados}'))

    def _pode_disparar(self, regra, item, chave):
        qs = DisparoRegraNotificacao.objects.filter(
            regra=regra,
            item=item,
            chave_evento=chave,
            sucesso=True,
        ).order_by('-enviado_em')

        ultimo = qs.first()
        if not ultimo:
            return True
        if not regra.repetir:
            return False

        limite = timezone.now() - timedelta(
            hours=max(1, regra.intervalo_repeticao_horas)
        )
        return ultimo.enviado_em <= limite

    def _mensagem(self, regra, item, evento, venc, dias):
        contexto = {
            'evento': evento,
            'nome': str(getattr(item, 'nome', '') or ''),
            'codigo': str(getattr(item, 'codigo', '') or ''),
            'lote': str(getattr(item, 'lote', '') or '-'),
            'quantidade': str(getattr(item, 'quantidade', 0) or 0),
            'minimo': str(getattr(item, 'estoque_minimo', 0) or 0),
            'unidade': str(getattr(item, 'unidade', '') or ''),
            'localizacao': str(getattr(item, 'localizacao', '') or '-'),
            'departamento': str(getattr(item, 'departamento', '') or '-'),
            'vencimento': venc.strftime('%d/%m/%Y') if venc else '-',
            'dias': dias if dias is not None else '-',
        }
        mensagem = regra.template_mensagem
        for chave, valor in contexto.items():
            mensagem = mensagem.replace('{' + chave + '}', str(valor))
        return mensagem
