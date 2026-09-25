from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0092_playlistremota_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracao",
            name="device_key_padrao",
            field=models.CharField(
                blank=True,
                help_text="Key usada automaticamente em novos cadastros de aplicativos quando nenhuma Key for informada.",
                max_length=180,
                null=True,
                verbose_name="Device Key padrão",
            ),
        ),
        migrations.AlterField(
            model_name="integracaoplaylistcliente",
            name="status",
            field=models.CharField(
                choices=[
                    ("nao_configurado", "Não configurado"),
                    ("configurado", "Configurado"),
                    ("aguardando_captcha", "Aguardando CAPTCHA"),
                    ("processando", "Processando"),
                    ("ativo", "Ativo"),
                    ("confirmacao_pendente", "Confirmação pendente"),
                    ("erro", "Erro"),
                    ("excluido", "Excluído"),
                ],
                default="nao_configurado",
                max_length=30,
            ),
        ),
    ]
