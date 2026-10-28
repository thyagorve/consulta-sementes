"""Backend de autenticação que ignora permissões herdadas por grupos.

O INFINITY STOCK usa permissões individuais como fonte de verdade. Grupos são
mantidos apenas por compatibilidade histórica e não devem elevar privilégios.
"""
from django.contrib.auth.backends import ModelBackend


class DirectPermissionBackend(ModelBackend):
    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        if not getattr(user_obj, 'is_active', False) or getattr(user_obj, 'is_anonymous', True):
            return set()
        if getattr(user_obj, 'is_superuser', False):
            return super().get_all_permissions(user_obj, obj=obj)
        return self.get_user_permissions(user_obj, obj=obj)
