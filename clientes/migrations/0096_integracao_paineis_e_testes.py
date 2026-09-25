from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0095_configuracao_codigo_protecao_playlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='servico',
            name='integracao_ativa',
            field=models.BooleanField(default=False, verbose_name='Integração ativa'),
        ),
        migrations.AddField(
            model_name='servico',
            name='integracao_tipo',
            field=models.CharField(choices=[('nenhuma', 'Sem integração'), ('sigman', 'SIGMAN'), ('unitv', 'UniTV / Resell Media')], default='nenhuma', max_length=20, verbose_name='Tipo de painel'),
        ),
        migrations.AddField(
            model_name='servico',
            name='integracao_politica',
            field=models.CharField(choices=[('manual', 'Somente manual'), ('facultativa', 'Manual ou automático'), ('obrigatoria', 'Automático obrigatório')], default='manual', max_length=20, verbose_name='Política de renovação'),
        ),
        migrations.AddField(model_name='servico', name='integracao_url', field=models.URLField(blank=True, max_length=500, null=True, verbose_name='URL do painel/API')),
        migrations.AddField(model_name='servico', name='integracao_token', field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Token')),
        migrations.AddField(model_name='servico', name='integracao_api_key', field=models.CharField(blank=True, max_length=500, null=True, verbose_name='API Key')),
        migrations.AddField(model_name='servico', name='integracao_usuario', field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Usuário/identificador do painel')),
        migrations.AddField(model_name='servico', name='integracao_senha', field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Senha do painel')),
        migrations.AddField(model_name='servico', name='integracao_servidor_externo_id', field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID do servidor externo')),
        migrations.AddField(model_name='servico', name='integracao_pacote_1_mes', field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Pacote externo de 1 mês')),
        migrations.AddField(model_name='servico', name='integracao_pacote_teste', field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Pacote externo para teste')),
        migrations.AddField(model_name='servico', name='integracao_conexoes', field=models.PositiveIntegerField(default=1, verbose_name='Conexões/telas padrão')),
        migrations.AddField(model_name='servico', name='renovacao_manual_credito', field=models.CharField(choices=[('sempre', 'Sempre consumir crédito'), ('nunca', 'Nunca consumir crédito'), ('perguntar', 'Perguntar na renovação')], default='sempre', max_length=20, verbose_name='Crédito na renovação manual')),
        migrations.AddField(model_name='servico', name='integracao_config', field=models.JSONField(blank=True, default=dict, verbose_name='Configuração avançada da integração')),
        migrations.AddField(model_name='servico', name='integracao_status', field=models.CharField(blank=True, default='', max_length=20, verbose_name='Status da integração')),
        migrations.AddField(model_name='servico', name='integracao_erro', field=models.TextField(blank=True, default='', verbose_name='Último erro da integração')),
        migrations.AddField(model_name='servico', name='integracao_ultima_verificacao', field=models.DateTimeField(blank=True, null=True, verbose_name='Última verificação')),
        migrations.CreateModel(
            name='TestePainel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('whatsapp', models.CharField(blank=True, default='', max_length=30)),
                ('login_externo', models.CharField(blank=True, default='', max_length=255)),
                ('senha_leitura', models.CharField(blank=True, default='', max_length=255)),
                ('external_id', models.CharField(blank=True, default='', max_length=255)),
                ('data_vencimento', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('vencido', 'Vencido'), ('convertido', 'Convertido em cliente'), ('falha', 'Falha')], db_index=True, default='ativo', max_length=20)),
                ('dados_externos', models.JSONField(blank=True, default=dict)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('convertido_em', models.DateTimeField(blank=True, null=True)),
                ('cliente_convertido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='testes_convertidos', to=settings.AUTH_USER_MODEL)),
                ('revenda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='testes_painel_criados', to=settings.AUTH_USER_MODEL)),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='testes_painel', to='clientes.servico')),
            ],
            options={'ordering': ['-criado_em']},
        ),
        migrations.CreateModel(
            name='OperacaoIntegracaoPainel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('consulta', 'Consulta'), ('renovacao', 'Renovação'), ('teste', 'Criação de teste'), ('conversao_teste', 'Conversão de teste'), ('verificacao', 'Verificação')], max_length=30)),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('consultando', 'Consultando'), ('aceita', 'Aceita pelo painel'), ('concluida', 'Concluída'), ('verificar', 'Requer verificação'), ('falhou', 'Falhou')], db_index=True, default='pendente', max_length=20)),
                ('chave_idempotencia', models.CharField(db_index=True, max_length=120, unique=True)),
                ('login_externo', models.CharField(blank=True, default='', max_length=255)),
                ('external_id', models.CharField(blank=True, default='', max_length=255)),
                ('meses', models.PositiveIntegerField(default=1)),
                ('creditos_externos', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('creditos_locais', models.PositiveIntegerField(default=0)),
                ('custo_local', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('vencimento_anterior', models.DateTimeField(blank=True, null=True)),
                ('vencimento_novo', models.DateTimeField(blank=True, null=True)),
                ('requisicao_resumo', models.JSONField(blank=True, default=dict)),
                ('resposta_resumo', models.JSONField(blank=True, default=dict)),
                ('erro', models.TextField(blank=True, default='')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('concluido_em', models.DateTimeField(blank=True, null=True)),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operacoes_painel', to=settings.AUTH_USER_MODEL)),
                ('revenda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operacoes_integracao', to=settings.AUTH_USER_MODEL)),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='operacoes_integracao', to='clientes.servico')),
                ('teste', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operacoes', to='clientes.testepainel')),
            ],
            options={'ordering': ['-criado_em']},
        ),
        migrations.AddIndex(model_name='testepainel', index=models.Index(fields=['revenda', 'status'], name='clientes_te_revenda_2fb0bf_idx')),
        migrations.AddIndex(model_name='testepainel', index=models.Index(fields=['login_externo'], name='clientes_te_login_e_8db413_idx')),
        migrations.AddIndex(model_name='operacaointegracaopainel', index=models.Index(fields=['revenda', 'status'], name='clientes_op_revenda_a4c2b6_idx')),
        migrations.AddIndex(model_name='operacaointegracaopainel', index=models.Index(fields=['servico', 'login_externo', 'criado_em'], name='clientes_op_servico_e53908_idx')),
    ]
