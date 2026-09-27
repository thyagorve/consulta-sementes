from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clientes', '0096_integracao_paineis_e_testes'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestePlaylist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('vence_em', models.DateTimeField()),
                ('status', models.CharField(choices=[('agendado', 'Agendado'), ('ativo', 'Ativo'), ('aguardando_auth', 'Aguardando autenticação'), ('desativado', 'Desativado'), ('convertido', 'Convertido em cliente'), ('erro', 'Erro')], default='agendado', max_length=30)),
                ('ultima_mensagem', models.TextField(blank=True, default='')),
                ('ultima_tentativa', models.DateTimeField(blank=True, null=True)),
                ('tentativas', models.PositiveIntegerField(default=0)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('valor_conversao', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('custo_conversao', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('cliente_convertido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='testes_playlist_convertidos', to=settings.AUTH_USER_MODEL)),
                ('dono', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='testes_playlist_criados', to=settings.AUTH_USER_MODEL)),
                ('origem_cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='testes_playlist_origem', to=settings.AUTH_USER_MODEL)),
                ('plano_conversao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='testes_playlist_convertidos', to='clientes.servico')),
                ('playlist', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='teste_playlist', to='clientes.playlistremota')),
            ],
            options={'ordering': ['-criado_em']},
        ),
        migrations.AddIndex(
            model_name='testeplaylist',
            index=models.Index(fields=['dono', 'status', 'vence_em'], name='clientes_te_dono_id_087f8d_idx'),
        ),
    ]
