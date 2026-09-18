from django.core.management.base import BaseCommand
from django.db.models import Sum

from sapp.models import Estoque, ItemEmpenho


class Command(BaseCommand):
    help = (
        'Audita, sem alterar dados, as invariantes do estoque: saldo físico, '
        'empenho por endereço e rastreabilidade pelos ItemEmpenho.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--fail',
            action='store_true',
            help='Retorna código de erro quando encontrar inconsistências.',
        )

    def handle(self, *args, **options):
        inconsistencias = []

        reservas = {
            row['estoque_id']: int(row['total'] or 0)
            for row in (
                ItemEmpenho.objects
                .values('estoque_id')
                .annotate(total=Sum('quantidade'))
            )
        }

        qs = Estoque.objects.all().order_by('lote', 'endereco', 'id')
        total = qs.count()

        for estoque in qs.iterator(chunk_size=500):
            entrada = int(estoque.entrada or 0)
            saida = int(estoque.saida or 0)
            saldo = int(estoque.saldo or 0)
            empenhado = int(estoque.empenhado or 0)
            rastreado = int(reservas.get(estoque.id, 0))
            esperado = entrada - saida

            problemas = []
            if saldo != esperado:
                problemas.append(f'saldo={saldo}, mas entrada-saida={esperado}')
            if saldo < 0:
                problemas.append(f'saldo negativo ({saldo})')
            if empenhado < 0:
                problemas.append(f'empenhado negativo ({empenhado})')
            if empenhado > saldo:
                problemas.append(f'empenhado ({empenhado}) maior que físico ({saldo})')
            if empenhado != rastreado:
                problemas.append(
                    f'contador empenhado={empenhado}, mas itens rastreados somam {rastreado}'
                )

            if problemas:
                inconsistencias.append((estoque, problemas))

        if not inconsistencias:
            self.stdout.write(
                self.style.SUCCESS(
                    f'OK: {total} registro(s) auditado(s), nenhuma inconsistência encontrada.'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'{len(inconsistencias)} inconsistência(s) em {total} registro(s) de estoque:'
            )
        )
        for estoque, problemas in inconsistencias:
            self.stdout.write(
                f'- ID {estoque.id} | lote {estoque.lote} | endereço {estoque.endereco}: '
                + '; '.join(problemas)
            )

        self.stdout.write(
            self.style.WARNING(
                'Auditoria somente leitura: nenhum dado foi alterado automaticamente.'
            )
        )
        if options['fail']:
            raise SystemExit(1)
