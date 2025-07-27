# sapp/templatetags/sapp_filters.py

from django import template

register = template.Library()

@register.filter(name='getattribute')
def getattribute(value, arg):
    """
    Permite acessar um atributo de um objeto usando uma variável no template.
    Exemplo: {{ meu_objeto|getattribute:nome_do_campo_como_string }}
    """
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    return None

@register.filter(name='replace')
def replace(value, args):
    """
    Substitui uma string por outra em um texto.
    Uso: {{ minha_string|replace:"antigo,novo" }}
    """
    if isinstance(value, str) and isinstance(args, str):
        try:
            # Tenta dividir a string de argumentos em duas partes
            old_string, new_string = args.split(',', 1) # O '1' garante que só vai dividir uma vez
            return value.replace(old_string, new_string)
        except ValueError:
            # Se não conseguir dividir, retorna o valor original sem erro
            return value
    return value