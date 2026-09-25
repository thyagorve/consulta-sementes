from whatsapp_integration.management.commands.processar_envio_massa import Command
from sapp.models import CustomUser

# Pegue um cliente existente
cliente = (
    CustomUser.objects
    .filter(whatsapp__isnull=False)
    .exclude(whatsapp="")
    .first()
)

if not cliente:
    print("Nenhum cliente encontrado.")
    raise SystemExit

cmd = Command()

mensagem = """
{saudacao} {nome}

Usuário: {usuario}
Senha: {senha}

Plano: {plano}
Valor do plano: {valor_servico}

Saldo: {saldo}
Débitos: {debitos}
Valor a pagar: {valor_total_a_pagar}

Vencimento: {data_vencimento}

Observação:
{observacao}

WhatsApp: {whatsapp}
"""

print("=" * 70)
print("CLIENTE:")
print(cliente.nome)
print("=" * 70)

resultado = cmd.substituir_variaveis(
    mensagem,
    cliente
)

print(resultado)

print("=" * 70)