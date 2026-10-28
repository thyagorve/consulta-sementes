from django.db import migrations


def disable_external_api(apps, schema_editor):
    ConfiguracaoWhatsApp = apps.get_model('almoxarifado', 'ConfiguracaoWhatsApp')
    InstanciaWhatsApp = apps.get_model('almoxarifado', 'InstanciaWhatsApp')
    AgendamentoNotificacao = apps.get_model('almoxarifado', 'AgendamentoNotificacao')
    CarrinhoSolicitacao = apps.get_model('almoxarifado', 'CarrinhoSolicitacao')

    ConfiguracaoWhatsApp.objects.all().update(
        ativo=False,
        api_url='',
        api_key=None,
        instance_name=None,
        numeros_padrao=None,
        numeros_por_departamento={},
    )
    AgendamentoNotificacao.objects.all().update(ativo=False)
    InstanciaWhatsApp.objects.all().delete()
    # Carrinhos antigos sem dono autenticado podiam ser compartilhados entre usuários.
    CarrinhoSolicitacao.objects.filter(usuario='anonimo').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('almoxarifado', '0023_alter_dadosvalidadeitem_options_and_more'),
    ]

    operations = [
        migrations.RunPython(disable_external_api, migrations.RunPython.noop),
    ]
