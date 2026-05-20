from django.apps import AppConfig

class AlmoxarifadoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'almoxarifado'
    verbose_name = 'Almoxarifado'

    def ready(self):
        """Método chamado quando o app é carregado"""
        import almoxarifado.signals  # noqa