from django.apps import AppConfig

class WhatsAppIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_integration'
    verbose_name = 'WhatsApp Integration'
    
    def ready(self):
        import whatsapp_integration.signals