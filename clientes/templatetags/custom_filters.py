# painel/clientes/templatetags/custom_filters.py
from django import template # Importa o módulo de template do Django

# Cria uma instância da biblioteca de template tags customizadas
register = template.Library()

# Filtro 1: Substitui caracteres específicos por underscores
@register.filter(name='replace_custom')
def replace_custom(value, chars_to_remove_str):
    """
    Substitui caracteres específicos por underscores (_) em uma string.
    Útil para gerar nomes de classe CSS válidos a partir de strings.
    Argumento: uma string contendo os caracteres a serem substituídos.
    Ex: "|replace_custom:' ,-'" substituirá espaços, vírgulas e hífens por underscores.
    """
    # Garante que o valor de entrada é uma string
    if not isinstance(value, str):
        # Se não for string, tenta converter ou retorna o valor original
        value = str(value) if value is not None else ""

    # Garante que o argumento de caracteres a remover é uma string
    if not isinstance(chars_to_remove_str, str):
         chars_to_remove_str = "" # Argumento inválido, não remove nada

    modified_value = value
    # Itera sobre os caracteres a serem substituídos e os substitui por underscore
    for char in chars_to_remove_str:
         modified_value = modified_value.replace(char, '_')

    # Opcional: remover múltiplos underscores consecutivos
    # modified_value = '_'.join(filter(None, modified_value.split('_')))

    # Opcional: remover underscores no início ou fim
    # modified_value = modified_value.strip('_')

    return modified_value

# Filtro 2: Substitui vírgula por ponto para formatação de números
@register.filter(name='replace_comma_with_dot')
def replace_comma_with_dot(value):
    """Substitui vírgula por ponto para formatação de números."""
    # Converte para string para garantir que o replace funcione
    # Trata None explicitamente para evitar erro
    if value is None:
        return ""
    try:
        # Garante que é string antes de substituir
        return str(value).replace(',', '.')
    except Exception:
        # Retorna o valor original em caso de erro
        return value


# Se você precisar de um filtro para formatar para BR (ponto milhar, vírgula decimal),
# você pode adicionar este (mas a template está usando o replace_comma_with_dot atualmente):
# @register.filter(name='format_decimal_br')
# def format_decimal_br(value, decimal_places=2):
#     """Formata um Decimal para o formato brasileiro (vírgula como separador decimal)."""
#     if value is None:
#         return ""
#     try:
#         # Converte o valor para decimal com o número de casas decimais especificado
#         from decimal import Decimal, InvalidOperation
#         if not isinstance(value, Decimal):
#             value = Decimal(str(value).replace(',', '.')) # Tenta converter, tratando vírgula como ponto inicial
#
#         # Formata com separador de milhar (não padrão no Python sem locale)
#         # e substitui o ponto decimal por vírgula
#         import locale
#         # Tente definir o locale para pt_BR (pode variar dependendo do sistema)
#         try:
#             locale.setlocale(locale.LC_NUMERIC, 'pt_BR.UTF-8') # Linux/macOS
#         except locale.Error:
#             try:
#                 locale.setlocale(locale.LC_NUMERIC, 'Portuguese_Brazil.1252') # Windows
#             except locale.Error:
#                 pass # Não foi possível definir o locale, usa formatação básica
#
#         # Formata o número usando o locale definido
#         formatted_value = locale.format_d(value, decimal_places, True)
#
#         # Reseta o locale para evitar afetar outras partes da aplicação
#         # try:
#         #     locale.setlocale(locale.LC_NUMERIC, 'C') # Ou outro locale padrão
#         # except locale.Error:
#         #     pass
#
#         return formatted_value
#
#     except (ValueError, InvalidOperation, Exception):
#         # Em caso de erro na conversão ou formatação, retorna o valor original (ou string vazia)
#         return str(value) if value is not None else ""