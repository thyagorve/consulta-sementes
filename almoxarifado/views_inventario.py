# almoxarifado/views_inventario.py

import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from .models import (
    DadosValidadeItem,
    ImportacaoInventario,
    Item,
    RegraNotificacaoAlmoxarifado,
)

from .services_inventario import (
    aplicar_linha,
    criar_comparacao,
)


# ============================================================
# PERMISSÕES
# ============================================================

def _pode_ver(user):
    return (
        user.is_superuser
        or user.has_perm(
            'almoxarifado.'
            'pode_ver_almoxarifado'
        )
        or user.has_perm(
            'almoxarifado.'
            'pode_gerenciar_almoxarifado'
        )
    )


def _pode_gerenciar(user):
    return (
        user.is_superuser
        or user.has_perm(
            'almoxarifado.'
            'pode_gerenciar_almoxarifado'
        )
    )


# ============================================================
# HELPERS
# ============================================================

def _parse_date(valor):
    if not valor:
        return None

    try:
        return datetime.strptime(
            str(valor)[:10],
            '%Y-%m-%d',
        ).date()

    except ValueError:
        raise ValueError(
            'Data inválida. '
            'Use AAAA-MM-DD.'
        )


def _foto_url(item):
    if item is None:
        return ''

    foto = getattr(
        item,
        'foto',
        None,
    )

    try:
        return (
            foto.url
            if foto
            else ''
        )

    except Exception:
        return ''


# ============================================================
# PÁGINA
# ============================================================

@login_required
def inventario_comparacao(
    request
):
    if not _pode_ver(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    return render(
        request,
        (
            'almoxarifado/'
            'inventario/'
            'comparacao.html'
        ),
        {
            'importacoes':
                (
                    ImportacaoInventario
                    .objects
                    .select_related(
                        'criado_por'
                    )[:20]
                ),

            'regras':
                (
                    RegraNotificacaoAlmoxarifado
                    .objects
                    .all()
                ),
        },
    )


# ============================================================
# VALIDADE DE UM ITEM
# ============================================================

@login_required
@require_GET
def api_item_validade(
    request,
    item_id,
):
    if not _pode_ver(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    item = get_object_or_404(
        Item,
        pk=item_id,
    )

    validade = (
        DadosValidadeItem
        .objects
        .filter(
            item=item
        )
        .first()
    )

    return JsonResponse({
        'success':
            True,

        'item_id':
            item.id,

        'data_fabricacao':
            (
                validade
                .data_fabricacao
                .isoformat()
                if (
                    validade
                    and validade
                    .data_fabricacao
                )
                else ''
            ),

        'data_vencimento':
            (
                validade
                .data_vencimento
                .isoformat()
                if (
                    validade
                    and validade
                    .data_vencimento
                )
                else ''
            ),

        'dias_para_vencer':
            (
                validade
                .dias_para_vencer
                if validade
                else None
            ),

        'status_vencimento':
            (
                validade
                .status_vencimento
                if validade
                else 'sem_data'
            ),
    })


@login_required
@require_POST
def api_salvar_item_validade(
    request,
    item_id,
):
    if not _pode_gerenciar(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    item = get_object_or_404(
        Item,
        pk=item_id,
    )

    try:
        payload = json.loads(
            request.body.decode(
                'utf-8'
            )
            or '{}'
        )

        fabricacao = _parse_date(
            payload.get(
                'data_fabricacao'
            )
        )

        vencimento = _parse_date(
            payload.get(
                'data_vencimento'
            )
        )

        if (
            fabricacao
            and vencimento
            and fabricacao
            > vencimento
        ):
            return JsonResponse(
                {
                    'success': False,
                    'error':
                        (
                            'A fabricação '
                            'não pode ser '
                            'posterior ao '
                            'vencimento.'
                        ),
                },
                status=400,
            )

        objeto, _ = (
            DadosValidadeItem
            .objects
            .get_or_create(
                item=item
            )
        )

        objeto.data_fabricacao = (
            fabricacao
        )

        objeto.data_vencimento = (
            vencimento
        )

        objeto.save(
            update_fields=[
                'data_fabricacao',
                'data_vencimento',
                'atualizado_em',
            ]
        )

        return JsonResponse({
            'success':
                True,

            'item_id':
                item.id,

            'data_fabricacao':
                (
                    fabricacao
                    .isoformat()
                    if fabricacao
                    else ''
                ),

            'data_vencimento':
                (
                    vencimento
                    .isoformat()
                    if vencimento
                    else ''
                ),

            'dias_para_vencer':
                objeto
                .dias_para_vencer,

            'status_vencimento':
                objeto
                .status_vencimento,
        })

    except ValueError as exc:
        return JsonResponse(
            {
                'success': False,
                'error': str(
                    exc
                ),
            },
            status=400,
        )

    except Exception as exc:
        return JsonResponse(
            {
                'success': False,
                'error': str(
                    exc
                ),
            },
            status=500,
        )


# ============================================================
# IMPORTAÇÃO / COMPARAÇÃO
# ============================================================

@login_required
@require_POST
def api_importar_comparacao(
    request
):
    if not _pode_gerenciar(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    arquivo = request.FILES.get(
        'arquivo'
    )

    if not arquivo:
        return JsonResponse(
            {
                'success': False,
                'error':
                    'Selecione um arquivo.',
            },
            status=400,
        )

    try:
        importacao = criar_comparacao(
            arquivo,
            request.user,
            modo=request.POST.get(
                'modo',
                'COM_LOTE',
            ),
            tipo=request.POST.get(
                'tipo',
                'PLANILHA',
            ),
        )

        return JsonResponse({
            'success':
                True,

            'importacao_id':
                importacao.id,

            'total':
                importacao
                .total_linhas,

            'resumo':
                importacao
                .resumo,
        })

    except Exception as exc:
        return JsonResponse(
            {
                'success': False,
                'error': str(
                    exc
                ),
            },
            status=400,
        )


# ============================================================
# LISTA DA COMPARAÇÃO
# ============================================================

@login_required
@require_GET
def api_linhas_comparacao(
    request,
    importacao_id,
):
    if not _pode_ver(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    importacao = get_object_or_404(
        ImportacaoInventario,
        pk=importacao_id,
    )

    qs = (
        importacao
        .linhas
        .select_related(
            'item'
        )
    )

    status = (
        request.GET
        .get(
            'status',
            '',
        )
        .strip()
    )

    if status:
        qs = qs.filter(
            status=status
        )

    linhas = []

    for linha in qs[
        :5000
    ]:

        item = linha.item

        # ----------------------------------------------------
        # CANDIDATOS QUANDO É AMBÍGUO
        # ----------------------------------------------------
        candidatos = []

        if (
            linha.status
            == 'AMBIGUO'
            and not linha.item_id
        ):

            candidatos_qs = (
                Item.objects
                .filter(
                    ativo=True,
                    codigo=linha.codigo,
                )
            )

            if (
                importacao
                .modo_comparacao
                == 'COM_LOTE'
            ):
                candidatos_qs = (
                    candidatos_qs
                    .filter(
                        lote=linha.lote
                    )
                )

            for candidato in (
                candidatos_qs
                .order_by(
                    'nome',
                    'id',
                )
            ):

                candidatos.append({
                    'id':
                        candidato.id,

                    'codigo':
                        getattr(
                            candidato,
                            'codigo',
                            '',
                        )
                        or '',

                    'nome':
                        getattr(
                            candidato,
                            'nome',
                            '',
                        )
                        or '',

                    'lote':
                        getattr(
                            candidato,
                            'lote',
                            '',
                        )
                        or '',

                    'quantidade':
                        float(
                            getattr(
                                candidato,
                                'quantidade',
                                0,
                            )
                            or 0
                        ),

                    'unidade':
                        getattr(
                            candidato,
                            'unidade',
                            '',
                        )
                        or '',

                    'localizacao':
                        getattr(
                            candidato,
                            'localizacao',
                            '',
                        )
                        or '',

                    'departamento':
                        getattr(
                            candidato,
                            'departamento',
                            '',
                        )
                        or '',

                    'foto_url':
                        _foto_url(
                            candidato
                        ),
                })

        linhas.append({
            'id':
                linha.id,

            'item_id':
                linha.item_id,

            'codigo':
                linha.codigo,

            'lote':
                linha.lote,

            'nome':
                (
                    getattr(
                        item,
                        'nome',
                        '',
                    )
                    if item
                    else linha.nome_arquivo
                ),

            'nome_arquivo':
                linha.nome_arquivo,

            'quantidade_sistema':
                (
                    float(
                        linha
                        .quantidade_sistema
                    )
                    if (
                        linha
                        .quantidade_sistema
                        is not None
                    )
                    else None
                ),

            'quantidade_arquivo':
                (
                    float(
                        linha
                        .quantidade_arquivo
                    )
                    if (
                        linha
                        .quantidade_arquivo
                        is not None
                    )
                    else None
                ),

            'unidade_sistema':
                linha
                .unidade_sistema,

            'unidade_arquivo':
                linha
                .unidade_arquivo,

            'status':
                linha.status,

            'acao':
                linha.acao,

            'aplicado':
                linha.aplicado,

            'mensagem':
                linha.mensagem,

            'foto_url':
                (
                    _foto_url(
                        item
                    )
                    if item
                    else ''
                ),

            'dados_arquivo':
                linha.dados_arquivo,

            'candidatos':
                candidatos,
        })

    return JsonResponse({
        'success':
            True,

        'importacao': {
            'id':
                importacao.id,

            'arquivo':
                importacao
                .nome_arquivo,

            'tipo':
                importacao.tipo,

            'modo':
                importacao
                .modo_comparacao,

            'status':
                importacao.status,

            'total':
                importacao
                .total_linhas,

            'resumo':
                importacao
                .resumo,
        },

        'linhas':
            linhas,
    })


# ============================================================
# APLICAR DECISÕES
# ============================================================

@login_required
@require_POST
def api_aplicar_decisoes(
    request,
    importacao_id,
):
    if not _pode_gerenciar(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    importacao = get_object_or_404(
        ImportacaoInventario,
        pk=importacao_id,
    )

    try:
        payload = json.loads(
            request.body.decode(
                'utf-8'
            )
            or '{}'
        )

        decisoes = payload.get(
            'decisoes',
            [],
        )

    except Exception as exc:
        return JsonResponse(
            {
                'success': False,
                'error':
                    (
                        'JSON inválido: '
                        f'{exc}'
                    ),
            },
            status=400,
        )

    if not isinstance(
        decisoes,
        list,
    ):
        return JsonResponse(
            {
                'success': False,
                'error':
                    (
                        'Decisões precisa '
                        'ser uma lista.'
                    ),
            },
            status=400,
        )

    aplicadas = 0
    erros = []

    for decisao in decisoes:

        linha_id = decisao.get(
            'linha_id'
        )

        acao = decisao.get(
            'acao'
        )

        item_id = decisao.get(
            'item_id'
        )

        try:
            linha = (
                importacao
                .linhas
                .select_related(
                    'item'
                )
                .get(
                    pk=linha_id
                )
            )

            # ------------------------------------------------
            # SE O USUÁRIO ESCOLHEU UM CANDIDATO AMBÍGUO
            # ------------------------------------------------
            if item_id:

                item = get_object_or_404(
                    Item,
                    pk=item_id,
                    ativo=True,
                )

                # Confirma o código.
                if (
                    str(
                        getattr(
                            item,
                            'codigo',
                            '',
                        )
                        or ''
                    ).strip().upper()
                    !=
                    str(
                        linha.codigo
                        or ''
                    ).strip().upper()
                ):
                    raise ValueError(
                        'O item escolhido '
                        'possui código '
                        'diferente da '
                        'linha comparada.'
                    )

                # Confirma o lote quando
                # o modo usa lote.
                if (
                    importacao
                    .modo_comparacao
                    == 'COM_LOTE'
                ):

                    if (
                        str(
                            getattr(
                                item,
                                'lote',
                                '',
                            )
                            or ''
                        ).strip().upper()
                        !=
                        str(
                            linha.lote
                            or ''
                        ).strip().upper()
                    ):
                        raise ValueError(
                            'O item escolhido '
                            'possui lote '
                            'diferente da '
                            'linha comparada.'
                        )

                linha.item = item

                # Atualiza os dados visuais
                # do "lado sistema" também.
                linha.quantidade_sistema = (
                    getattr(
                        item,
                        'quantidade',
                        0,
                    )
                    or 0
                )

                linha.unidade_sistema = (
                    getattr(
                        item,
                        'unidade',
                        '',
                    )
                    or ''
                )

                linha.save(
                    update_fields=[
                        'item',
                        'quantidade_sistema',
                        'unidade_sistema',
                    ]
                )

            aplicar_linha(
                linha,
                acao,
            )

            aplicadas += 1

        except Exception as exc:

            try:
                linha_info = (
                    importacao
                    .linhas
                    .filter(
                        pk=linha_id
                    )
                    .values(
                        'id',
                        'codigo',
                        'lote',
                        'status',
                        'item_id',
                    )
                    .first()
                )

            except Exception:
                linha_info = None

            erro = {
                'linha_id':
                    linha_id,

                'acao':
                    acao,

                'item_id':
                    item_id,

                'tipo_erro':
                    (
                        exc
                        .__class__
                        .__name__
                    ),

                'erro':
                    str(
                        exc
                    ),

                'linha':
                    linha_info,
            }

            erros.append(
                erro
            )

            print(
                '\n'
                '======================'
            )

            print(
                'ERRO INVENTÁRIO'
            )

            print(
                'Importação:',
                importacao_id,
            )

            print(
                'Linha:',
                linha_id,
            )

            print(
                'Ação:',
                acao,
            )

            print(
                'Item escolhido:',
                item_id,
            )

            print(
                'Dados:',
                linha_info,
            )

            print(
                'Tipo:',
                (
                    exc
                    .__class__
                    .__name__
                ),
            )

            print(
                'Erro:',
                str(
                    exc
                ),
            )

            print(
                '======================'
                '\n'
            )

    pendentes = (
        importacao
        .linhas
        .filter(
            aplicado=False
        )
        .count()
    )

    if pendentes == 0:

        importacao.status = (
            'APLICADA'
        )

        importacao.aplicado_em = (
            timezone.now()
        )

        importacao.save(
            update_fields=[
                'status',
                'aplicado_em',
            ]
        )

    return JsonResponse({
        'success':
            len(
                erros
            ) == 0,

        'aplicadas':
            aplicadas,

        'erros':
            erros,

        'total_erros':
            len(
                erros
            ),

        'pendentes':
            pendentes,
    })


# ============================================================
# REGRAS DE ALERTA
# ============================================================

@login_required
@require_POST
def api_salvar_regra(
    request
):
    if not _pode_gerenciar(
        request.user
    ):
        return JsonResponse(
            {
                'success': False,
                'error': 'Sem permissão.',
            },
            status=403,
        )

    try:
        payload = json.loads(
            request.body.decode(
                'utf-8'
            )
            or '{}'
        )

        regra_id = payload.get(
            'id'
        )

        if regra_id:
            regra = get_object_or_404(
                RegraNotificacaoAlmoxarifado,
                pk=regra_id,
            )

        else:
            regra = (
                RegraNotificacaoAlmoxarifado()
            )

        regra.nome = (
            payload.get(
                'nome'
            )
            or 'Regra'
        )

        regra.tipo = (
            payload.get(
                'tipo'
            )
            or 'ESTOQUE_BAIXO'
        )

        regra.ativo = bool(
            payload.get(
                'ativo',
                True,
            )
        )

        regra.quantidade_limite = (
            payload.get(
                'quantidade_limite'
            )
            or None
        )

        regra.dias_antes_vencimento = (
            payload.get(
                'dias_antes_vencimento'
            )
            or []
        )

        regra.departamentos = (
            payload.get(
                'departamentos'
            )
            or []
        )

        regra.repetir = bool(
            payload.get(
                'repetir',
                False,
            )
        )

        regra.intervalo_repeticao_horas = int(
            payload.get(
                'intervalo_repeticao_horas'
            )
            or 24
        )

        if payload.get(
            'template_mensagem'
        ):
            regra.template_mensagem = (
                payload[
                    'template_mensagem'
                ]
            )

        regra.full_clean()
        regra.save()

        return JsonResponse({
            'success':
                True,

            'id':
                regra.id,
        })

    except Exception as exc:
        return JsonResponse(
            {
                'success': False,
                'error': str(
                    exc
                ),
            },
            status=400,
        )
