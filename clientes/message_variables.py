# -*- coding: utf-8 -*-

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional, Set

from django.utils import timezone


# ============================================================
# FUNÇÕES INTERNAS
# ============================================================

def _decimal_seguro(valor: Any) -> Decimal:
    """
    Converte qualquer valor numérico para Decimal.

    Valores inválidos, vazios ou nulos retornam Decimal('0.00'),
    evitando que uma mensagem deixe de ser enviada.
    """

    if valor in (None, ""):
        return Decimal("0.00")

    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _formatar_moeda(valor: Any) -> str:
    """
    Formata valores monetários no padrão brasileiro.

    Exemplos:
        1234.50  -> R$ 1.234,50
        30       -> R$ 30,00
        None     -> R$ 0,00
    """

    valor_decimal = _decimal_seguro(valor)

    return (
        f"R$ {valor_decimal:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def _formatar_data(valor: Any) -> str:
    """
    Formata datas no padrão DD/MM/AAAA.
    """

    if not valor:
        return ""

    try:
        return valor.strftime("%d/%m/%Y")
    except (AttributeError, TypeError, ValueError):
        return str(valor)


def _obter_saudacao() -> str:
    """
    Retorna a saudação conforme o horário local configurado no Django.
    """

    agora = timezone.localtime()

    if 5 <= agora.hour < 12:
        return "Bom dia"

    if 12 <= agora.hour < 18:
        return "Boa tarde"

    return "Boa noite"


def _texto_seguro(valor: Any, padrao: str = "") -> str:
    """
    Converte um valor para texto sem retornar 'None'.
    """

    if valor is None:
        return padrao

    return str(valor)


# ============================================================
# CONTEXTO CENTRAL DAS MENSAGENS
# ============================================================

def obter_contexto_mensagem(
    cliente: Any,
    variaveis_extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Retorna todas as variáveis disponíveis para as mensagens.

    Esta deve ser a única fonte oficial de variáveis do sistema.

    Parâmetros:
        cliente:
            Instância de CustomUser ou outro objeto compatível.

        variaveis_extras:
            Dicionário opcional para acrescentar ou sobrescrever variáveis.

            Exemplo:

            {
                "dias_antes_vencimento": 5,
                "codigo_pix": "000201..."
            }

    Retorno:
        Dicionário contendo as variáveis sem as chaves.

        Exemplo:

        {
            "nome": "João",
            "saldo": "R$ 10,00"
        }
    """

    if cliente is None:
        raise ValueError(
            "Não foi possível gerar as variáveis: cliente não informado."
        )

    saudacao = _obter_saudacao()

    # ========================================================
    # DADOS PESSOAIS
    # ========================================================

    nome = (
        getattr(cliente, "nome", "")
        or getattr(cliente, "first_name", "")
        or getattr(cliente, "username", "")
        or "Cliente"
    )

    primeiro_nome = (
        nome.split()[0]
        if nome and nome.split()
        else "Cliente"
    )

    usuario = (
        getattr(cliente, "login_externo", "")
        or getattr(cliente, "username", "")
        or ""
    )

    senha = (
        getattr(cliente, "senha_leitura", "")
        or ""
    )

    whatsapp = (
        getattr(cliente, "whatsapp", "")
        or ""
    )

    telefone = (
        getattr(cliente, "telefone", "")
        or whatsapp
    )

    email = (
        getattr(cliente, "email", "")
        or ""
    )

    observacao = (
        getattr(cliente, "observacao", "")
        or ""
    )

    # ========================================================
    # PLANO
    # ========================================================

    plano_obj = getattr(cliente, "plano", None)

    plano_nome = (
        getattr(plano_obj, "nome", "")
        if plano_obj
        else ""
    ) or ""

    # ========================================================
    # DATAS
    # ========================================================

    data_vencimento = getattr(
        cliente,
        "data_vencimento",
        None,
    )

    data_vencimento_formatada = _formatar_data(
        data_vencimento
    )

    hoje = timezone.localdate()

    dias_para_vencimento = ""

    if data_vencimento:
        try:
            dias_para_vencimento = (
                data_vencimento - hoje
            ).days
        except (TypeError, AttributeError):
            dias_para_vencimento = ""

    # ========================================================
    # VALORES FINANCEIROS
    # ========================================================

    valor_servico = _decimal_seguro(
        getattr(cliente, "valor_servico", 0)
    )

    valor_a_pagar = _decimal_seguro(
        getattr(cliente, "valor_a_pagar", 0)
    )

    saldo_bruto = _decimal_seguro(
        getattr(cliente, "saldo", 0)
    )

    # Se valor_a_pagar estiver preenchido, ele representa
    # a parcela atual. Caso contrário, utiliza valor_servico.
    parcela_atual = (
        valor_a_pagar
        if valor_a_pagar > Decimal("0.00")
        else valor_servico
    )

    # Saldo negativo representa débito acumulado.
    if saldo_bruto < Decimal("0.00"):
        saldo_disponivel = Decimal("0.00")
        debitos = abs(saldo_bruto)
        valor_total = parcela_atual + debitos

    else:
        saldo_disponivel = saldo_bruto
        debitos = Decimal("0.00")

        valor_total = max(
            Decimal("0.00"),
            parcela_atual - saldo_disponivel,
        )

    # ========================================================
    # CONTEXTO OFICIAL
    # ========================================================

    contexto: Dict[str, Any] = {
        # Saudação
        "saudacao": saudacao,

        # Nome
        "nome": nome,
        "nome_completo": nome,
        "primeiro_nome": primeiro_nome,

        # Login
        "usuario": usuario,
        "login": usuario,
        "login_externo": usuario,

        # Senha
        "senha": senha,

        # Plano
        "plano": plano_nome,

        # Datas
        "data_vencimento": data_vencimento_formatada,
        "dias_para_vencimento": dias_para_vencimento,

        # Contato
        "whatsapp": whatsapp,
        "telefone": telefone,
        "numero_contato": whatsapp or telefone,
        "email": email,

        # Observação
        "observacao": observacao,

        # Valores
        "valor_servico": _formatar_moeda(
            valor_servico
        ),

        "valor_a_pagar": _formatar_moeda(
            parcela_atual
        ),

        "saldo": _formatar_moeda(
            saldo_disponivel
        ),

        "saldo_bruto": _formatar_moeda(
            saldo_bruto
        ),

        "debitos": _formatar_moeda(
            debitos
        ),

        "valor_total_a_pagar": _formatar_moeda(
            valor_total
        ),
    }

    # ========================================================
    # VARIÁVEIS EXTRAS
    # ========================================================

    if variaveis_extras:
        for chave, valor in variaveis_extras.items():
            chave_limpa = str(chave).strip()

            # Permite passar tanto:
            # "nome_variavel"
            # quanto:
            # "{nome_variavel}"
            if (
                chave_limpa.startswith("{")
                and chave_limpa.endswith("}")
            ):
                chave_limpa = chave_limpa[1:-1].strip()

            contexto[chave_limpa] = valor

    # Converte tudo para string.
    return {
        str(chave): _texto_seguro(valor)
        for chave, valor in contexto.items()
    }


# ============================================================
# SUBSTITUIÇÃO DE VARIÁVEIS
# ============================================================

def substituir_variaveis_mensagem(
    texto: str,
    cliente: Any,
    variaveis_extras: Optional[Dict[str, Any]] = None,
    remover_desconhecidas: bool = False,
) -> str:
    """
    Substitui todas as variáveis presentes na mensagem.

    Aceita formatos como:

        {nome}
        { nome }
        {valor_total_a_pagar}

    Parâmetros:
        texto:
            Template da mensagem.

        cliente:
            Cliente utilizado para criar o contexto.

        variaveis_extras:
            Variáveis específicas de um fluxo.

            Exemplo:

            {
                "dias_antes_vencimento": 5
            }

        remover_desconhecidas:
            False:
                Mantém variáveis desconhecidas na mensagem.

            True:
                Remove variáveis que não existem no contexto.

    Exemplo:

        substituir_variaveis_mensagem(
            "Olá {nome}, faltam {dias_antes_vencimento} dias.",
            cliente,
            variaveis_extras={
                "dias_antes_vencimento": 5
            }
        )
    """

    if not texto:
        return ""

    contexto = obter_contexto_mensagem(
        cliente=cliente,
        variaveis_extras=variaveis_extras,
    )

    mensagem_final = str(texto)

    # Procura variáveis com ou sem espaços internos.
    # Exemplos:
    # {nome}
    # { nome }
    padrao_variavel = re.compile(
        r"\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}"
    )

    def substituir(match: re.Match) -> str:
        chave = match.group(1)

        if chave in contexto:
            return contexto[chave]

        if remover_desconhecidas:
            return ""

        # Mantém exatamente como estava.
        return match.group(0)

    mensagem_final = padrao_variavel.sub(
        substituir,
        mensagem_final,
    )

    return mensagem_final.strip()


# ============================================================
# DIAGNÓSTICO E VALIDAÇÃO
# ============================================================

def encontrar_variaveis_no_texto(
    texto: str,
) -> Set[str]:
    """
    Retorna o conjunto de variáveis encontradas na mensagem.

    Exemplo:

        "Olá {nome}, saldo {saldo}"

    Retorno:

        {"nome", "saldo"}
    """

    if not texto:
        return set()

    padrao_variavel = re.compile(
        r"\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}"
    )

    return {
        resultado.group(1)
        for resultado in padrao_variavel.finditer(
            str(texto)
        )
    }


def encontrar_variaveis_desconhecidas(
    texto: str,
    cliente: Any,
    variaveis_extras: Optional[Dict[str, Any]] = None,
) -> Set[str]:
    """
    Retorna variáveis usadas na mensagem que não existem no contexto.

    Útil para validar templates antes de salvar ou enviar.
    """

    variaveis_texto = encontrar_variaveis_no_texto(
        texto
    )

    contexto = obter_contexto_mensagem(
        cliente=cliente,
        variaveis_extras=variaveis_extras,
    )

    return variaveis_texto.difference(
        contexto.keys()
    )


def listar_variaveis_disponiveis() -> Iterable[str]:
    """
    Retorna os nomes das variáveis oficiais.

    Não necessita de um cliente porque essa lista serve para
    montar botões, documentação e validações.
    """

    return (
        "saudacao",
        "nome",
        "nome_completo",
        "primeiro_nome",
        "usuario",
        "login",
        "login_externo",
        "senha",
        "plano",
        "data_vencimento",
        "dias_para_vencimento",
        "whatsapp",
        "telefone",
        "numero_contato",
        "email",
        "observacao",
        "valor_servico",
        "valor_a_pagar",
        "saldo",
        "saldo_bruto",
        "debitos",
        "valor_total_a_pagar",
    )