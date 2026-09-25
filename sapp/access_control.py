"""Regras centrais de acesso do INFINITY STOCK.

O sistema usa permissões individuais como fonte de verdade. Grupos antigos
são tratados apenas na migração de compatibilidade e não participam da decisão
de rota inicial.
"""
from django.urls import reverse


PERMISSION_APP_MAP = {
    'pode_ver_dashboard': 'sapp',
    'pode_ver_estoque': 'sapp',
    'pode_movimentar_estoque': 'sapp',
    'pode_ver_empenhos': 'sapp',
    'pode_criar_empenhos': 'sapp',
    'pode_criar_solicitacao': 'sapp',
    'pode_empenhar_solicitacao': 'sapp',
    'pode_movimentar_solicitacao': 'sapp',
    'pode_cancelar_solicitacao': 'sapp',
    'pode_ver_mapa': 'sapp',
    'pode_gerenciar_usuarios': 'sapp',
    'pode_configuracoes': 'sapp',
    'pode_ver_almoxarifado': 'almoxarifado',
    'pode_gerenciar_almoxarifado': 'almoxarifado',
}


def split_permission(permission_name):
    if '.' in permission_name:
        return permission_name.split('.', 1)
    app_label = PERMISSION_APP_MAP.get(permission_name, 'sapp')
    return app_label, permission_name


def has_direct_permission(user, permission_name):
    """Checa somente permissões individuais, sem herança de grupos."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    app_label, codename = split_permission(permission_name)
    return user.user_permissions.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).exists()


def has_any_direct_permission(user, *permission_names):
    return any(has_direct_permission(user, name) for name in permission_names)


def first_allowed_url(user):
    """Retorna a rota inicial mais útil entre as permissões do usuário."""
    if getattr(user, 'is_superuser', False):
        return reverse('sapp:dashboard')

    # Dashboard só abre quando foi explicitamente liberado.
    if has_direct_permission(user, 'sapp.pode_ver_dashboard'):
        return reverse('sapp:dashboard')

    # Estoque.
    if has_direct_permission(user, 'sapp.pode_ver_estoque'):
        return reverse('sapp:lista_estoque')
    if has_direct_permission(user, 'sapp.pode_movimentar_estoque'):
        return reverse('sapp:gestao_estoque')

    # Solicitações.
    if has_direct_permission(user, 'sapp.pode_ver_empenhos'):
        return reverse('sapp:pagina_solicitacoes')
    if has_direct_permission(user, 'sapp.pode_criar_solicitacao'):
        return reverse('sapp:criar_solicitacao')
    if has_any_direct_permission(
        user,
        'sapp.pode_empenhar_solicitacao',
        'sapp.pode_movimentar_solicitacao',
        'sapp.pode_cancelar_solicitacao',
        'sapp.pode_criar_empenhos',
    ):
        return reverse('sapp:pagina_kanban')

    # Almoxarifado. Gerenciar também permite abrir a tela principal.
    if has_any_direct_permission(
        user,
        'almoxarifado.pode_ver_almoxarifado',
        'almoxarifado.pode_gerenciar_almoxarifado',
    ):
        return reverse('almoxarifado:lista_itens')

    if has_direct_permission(user, 'sapp.pode_ver_mapa'):
        return reverse('sapp:mapa_canvas', kwargs={'armazem_numero': 1})

    if has_direct_permission(user, 'sapp.pode_configuracoes'):
        return reverse('sapp:configuracoes')

    return None
