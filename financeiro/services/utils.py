# financeiro/services/utils.py
from decimal import Decimal, InvalidOperation

def converter_valor_br_para_decimal(valor_str):
    """
    Converte string de valor no formato brasileiro para Decimal
    Exemplos: "1.000,50" -> Decimal("1000.50"), "150,00" -> Decimal("150.00")
    """
    if not valor_str:
        return Decimal('0')
    
    valor_str = valor_str.replace('R$', '').replace(' ', '').strip()
    
    if not valor_str:
        return Decimal('0')
    
    if ',' in valor_str:
        if '.' in valor_str:
            partes = valor_str.split(',')
            if len(partes) == 2:
                inteiro = partes[0].replace('.', '')
                decimal = partes[1]
                valor_str = f"{inteiro}.{decimal}"
        else:
            valor_str = valor_str.replace(',', '.')
    
    try:
        return Decimal(valor_str)
    except InvalidOperation:
        return Decimal('0')