# seu_app/templatetags/markdown_filters.py
from django import template # <-- Importe template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import markdown # <-- Importe markdown

register = template.Library() # <-- ESSA LINHA REGISTRA A BIBLIOTECA

@register.filter(name='markdown') # <-- ESTE DECORADOR REGISTRA O FILTRO
def markdown_format(text):
    """
    Converte texto Markdown em HTML.
    """
    if text is None: # Tratar caso o texto seja None
         return ""
    # Usa mark_safe para dizer ao Django que o HTML gerado é seguro
    return mark_safe(markdown.markdown(escape(str(text))))