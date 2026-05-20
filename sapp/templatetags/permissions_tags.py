# sapp/templatetags/permissions_tags.py
from django import template
from django.contrib.auth.models import Permission

register = template.Library()

@register.filter
def has_perm(user, perm):
    """Verifica se o usuário tem uma permissão específica"""
    if user.is_superuser:
        return True
    return user.has_perm(perm)

@register.simple_tag(takes_context=True)
def check_permission(context, permission):
    """Template tag para verificar permissão no template"""
    request = context.get('request')
    if request and request.user.is_authenticated:
        if request.user.is_superuser:
            return True
        return request.user.has_perm(permission)
    return False