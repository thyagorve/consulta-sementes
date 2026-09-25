# clientes/utils.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from .models import RelatorioFinanceiro

User = get_user_model()

def criar_revenda(username, email, senha, data_vencimento, valor_pago):
    revenda = User.objects.create_user(
        username=username,
        email=email,
        password=senha,
        tipo_usuario='revenda',
        data_vencimento=data_vencimento,
        valor_pago=valor_pago
    )
    revenda.save()  
    return revenda



import logging
import traceback
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)

def gerar_relatorio_financeiro(cliente, valor_servico, valor_pago=None, is_manual_entry=False, 
                                numero_renovacao=0, grupo_renovacao=None):
    """
    Função para gerar um relatório financeiro.
    """
    
    # 🔥 ANTI-DUPLICIDADE: Bloqueia relatório idêntico nos últimos 10 segundos
    from datetime import timedelta
    limite = timezone.now() - timedelta(seconds=10)
    
    duplicado = RelatorioFinanceiro.objects.filter(
        cliente=cliente,
        valor_pago=Decimal(valor_pago) if valor_pago is not None else Decimal(0),
        valor_servico=Decimal(valor_servico),
        is_manual=is_manual_entry,
        data_geracao__gte=limite
    ).exists()
    
    if duplicado:
        logger.warning(f"🛑 Relatório DUPLICADO bloqueado para {cliente.nome} "
                      f"(Valor: {valor_pago}, Custo: {valor_servico})")
        return Decimal(valor_pago or 0), Decimal(0)
    
    # ==========================================
    # CÓDIGO ORIGINAL CONTINUA AQUI
    # ==========================================
    
    valor_parcela = getattr(cliente, 'valor_a_pagar', Decimal(0)) or Decimal(0)
    saldo_atual = getattr(cliente, 'saldo', Decimal(0)) or Decimal(0)

    # --- Lógica de cálculo de valor_pago ---
    if valor_pago is None:
        if not is_manual_entry:
            if saldo_atual < 0:
                valor_pago = abs(saldo_atual) + valor_parcela
                saldo_atual = Decimal(0)
                cliente.saldo = Decimal(0)
            elif saldo_atual >= valor_parcela:
                valor_pago = Decimal(0)
                saldo_atual -= valor_parcela
                cliente.saldo -= valor_parcela
            else:
                valor_pago = valor_parcela - saldo_atual
                saldo_atual = Decimal(0)
                cliente.saldo = Decimal(0)
        else:
            valor_pago = Decimal(0)

    valor_pago = Decimal(valor_pago)
    valor_servico = Decimal(valor_servico)
    valor_liquido = valor_pago - valor_servico

    # --- Definir o nome do servidor ---
    if is_manual_entry:
        servidor_nome = 'Entrada/Saída Manual'
    else:
        plano_cliente = getattr(cliente, 'plano', None)
        servidor_nome = plano_cliente.nome if plano_cliente else 'Automático (Sem Plano)'

    # Cria o relatório
    relatorio = RelatorioFinanceiro.objects.create(
        cliente=cliente,
        valor_pago=valor_pago,
        valor_servico=valor_servico,
        valor_liquido=valor_liquido,
        servidor=servidor_nome,
        data_geracao=timezone.now(),
        is_manual=is_manual_entry,
        numero_rodada=numero_renovacao,
        grupo_renovacao=grupo_renovacao,
    )

    if not is_manual_entry and cliente.pk:
        cliente.save()

    return valor_pago, saldo_atual

def get_grupo_renovacao(cliente):
    """Gera chave única para o grupo de compartilhamento"""
    if cliente.login_externo and cliente.senha_leitura and cliente.plano and cliente.dono:
        return f"{cliente.plano.id}_{cliente.login_externo}_{cliente.senha_leitura}_{cliente.dono_id}"
    return None


