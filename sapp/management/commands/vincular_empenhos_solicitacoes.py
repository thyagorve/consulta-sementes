from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from sapp.models import (
    Empenho,
    Solicitacao,
)


class Command(BaseCommand):
    help = (
        'Vincula empenhos antigos às solicitações sem usar '
        'automaticamente títulos duplicados.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--aplicar',
            action='store_true',
            help=(
                'Aplica os vínculos seguros. Sem esta opção, '
                'executa somente uma simulação.'
            ),
        )

    def handle(self, *args, **options):
        aplicar = options['aplicar']

        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING(
                'MODO: '
                + (
                    'APLICAÇÃO REAL'
                    if aplicar
                    else 'SOMENTE SIMULAÇÃO'
                )
            )
        )
        self.stdout.write('')

        solicitacoes_por_titulo = defaultdict(list)

        for solicitacao in (
            Solicitacao.objects
            .all()
            .order_by('data_criacao', 'id')
        ):
            titulo = self.normalizar(
                solicitacao.titulo
            )

            solicitacoes_por_titulo[titulo].append(
                solicitacao
            )

        total_empenhos = 0
        vinculados = 0
        ja_vinculados = 0
        ambiguos = 0
        sem_card = 0

        empenhos = (
            Empenho.objects
            .select_related(
                'solicitacao',
                'status',
                'usuario',
            )
            .prefetch_related(
                'itens',
                'historico_itens',
            )
            .order_by(
                'data_criacao',
                'id',
            )
        )

        for empenho in empenhos:
            total_empenhos += 1

            if empenho.solicitacao_id:
                ja_vinculados += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'[JÁ VINCULADO] '
                        f'Empenho #{empenho.id} -> '
                        f'Solicitação '
                        f'#{empenho.solicitacao_id}'
                    )
                )
                continue

            titulo = self.normalizar(
                empenho.observacao
            )

            if not titulo:
                sem_card += 1

                self.stdout.write(
                    self.style.ERROR(
                        f'[SEM TÍTULO] Empenho '
                        f'#{empenho.id}'
                    )
                )
                continue

            candidatas = solicitacoes_por_titulo.get(
                titulo,
                []
            )

            if not candidatas:
                sem_card += 1

                self.stdout.write(
                    self.style.ERROR(
                        f'[SEM CARD] Empenho '
                        f'#{empenho.id} | '
                        f'Observação: {titulo}'
                    )
                )
                continue

            if len(candidatas) == 1:
                solicitacao = candidatas[0]

                self.vincular(
                    empenho=empenho,
                    solicitacao=solicitacao,
                    aplicar=aplicar,
                )

                vinculados += 1
                continue

            candidatura = self.encontrar_por_data(
                empenho=empenho,
                candidatas=candidatas,
            )

            if candidatura:
                self.vincular(
                    empenho=empenho,
                    solicitacao=candidatura,
                    aplicar=aplicar,
                )

                vinculados += 1
                continue

            ambiguos += 1

            ids = ', '.join(
                f'#{solicitacao.id}'
                for solicitacao in candidatas
            )

            quantidade_itens = empenho.itens.count()
            quantidade_historicos = (
                empenho.historico_itens.count()
            )

            self.stdout.write(
                self.style.WARNING(
                    f'[AMBÍGUO] Empenho '
                    f'#{empenho.id} | '
                    f'Título: {titulo} | '
                    f'Criado: {empenho.data_criacao} | '
                    f'Itens pendentes: '
                    f'{quantidade_itens} | '
                    f'Itens processados: '
                    f'{quantidade_historicos} | '
                    f'Candidatas: {ids}'
                )
            )

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            f'Total de empenhos: {total_empenhos}'
        )
        self.stdout.write(
            f'Já vinculados: {ja_vinculados}'
        )
        self.stdout.write(
            f'Vínculos seguros encontrados: {vinculados}'
        )
        self.stdout.write(
            f'Ambíguos: {ambiguos}'
        )
        self.stdout.write(
            f'Sem solicitação correspondente: {sem_card}'
        )
        self.stdout.write('=' * 70)

        if not aplicar:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    'Nenhuma alteração foi salva. '
                    'Para aplicar os vínculos seguros, rode:'
                )
            )
            self.stdout.write(
                'python manage.py '
                'vincular_empenhos_solicitacoes '
                '--aplicar'
            )

    @staticmethod
    def normalizar(valor):
        return ' '.join(
            str(valor or '')
            .strip()
            .upper()
            .split()
        )

    def encontrar_por_data(
        self,
        empenho,
        candidatas
    ):
        """
        Só vincula automaticamente quando existe uma única
        solicitação criada antes do empenho e nenhuma dúvida
        razoável entre cards com o mesmo nome.
        """
        anteriores = [
            solicitacao
            for solicitacao in candidatas
            if (
                solicitacao.data_criacao
                <= empenho.data_criacao
            )
        ]

        if len(anteriores) == 1:
            return anteriores[0]

        if not anteriores:
            return None

        anteriores.sort(
            key=lambda solicitacao: (
                solicitacao.data_criacao,
                solicitacao.id,
            ),
            reverse=True,
        )

        mais_proxima = anteriores[0]

        # Se o empenho tem históricos, não arriscamos quando
        # existem vários cards anteriores com o mesmo nome.
        if empenho.historico_itens.exists():
            return None

        # Se há apenas uma solicitação ainda não concluída
        # criada antes do empenho, ela pode ser identificada.
        ativas = [
            solicitacao
            for solicitacao in anteriores
            if solicitacao.status not in [
                'CONCLUIDO',
                'CANCELADO',
            ]
        ]

        if len(ativas) == 1:
            return ativas[0]

        # Em qualquer outra situação, exige correção manual.
        return None

    def vincular(
        self,
        empenho,
        solicitacao,
        aplicar
    ):
        texto = (
            f'Empenho #{empenho.id} -> '
            f'Solicitação #{solicitacao.id} '
            f'({solicitacao.titulo})'
        )

        if aplicar:
            with transaction.atomic():
                empenho.solicitacao = solicitacao

                if not empenho.observacao:
                    empenho.observacao = (
                        solicitacao.titulo
                    )

                empenho.save(
                    update_fields=[
                        'solicitacao',
                        'observacao',
                        'data_atualizacao',
                    ]
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'[VINCULADO] {texto}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[SIMULAÇÃO] {texto}'
                )
            )