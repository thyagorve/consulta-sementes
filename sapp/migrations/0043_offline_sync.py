import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_lote_sync_states(apps, schema_editor):
    Estoque = apps.get_model('sapp', 'Estoque')
    LoteSyncState = apps.get_model('sapp', 'LoteSyncState')
    lotes = (
        Estoque.objects
        .exclude(lote__isnull=True)
        .exclude(lote='')
        .values_list('lote', flat=True)
        .distinct()
    )
    LoteSyncState.objects.bulk_create(
        [LoteSyncState(lote=str(lote).strip(), versao=0) for lote in lotes if str(lote).strip()],
        ignore_conflicts=True,
        batch_size=1000,
    )


def noop_reverse(apps, schema_editor):
    pass



class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0042_configuracao_proximo_numero_carga'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='historicomovimentacao',
            name='origem_carga',
            field=models.CharField(blank=True, db_index=True, default='', help_text='GERADA para carga do card; AVULSA para expedição avulsa.', max_length=20),
        ),
        migrations.AddField(
            model_name='historicomovimentacao',
            name='nome_carga_avulsa',
            field=models.CharField(blank=True, db_index=True, default='', help_text='Nome usado para agrupar várias baixas da mesma carga avulsa.', max_length=180),
        ),
        migrations.CreateModel(
            name='CargaAjusteLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('antes', models.JSONField(default=dict)),
                ('depois', models.JSONField(default=dict)),
                ('motivo', models.TextField(blank=True, default='')),
                ('historico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ajustes_carga', to='sapp.historicomovimentacao')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ajustes_carga', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Ajuste de carga', 'verbose_name_plural': 'Ajustes de cargas', 'ordering': ['-criado_em']},
        ),
        migrations.CreateModel(
            name='LoteSyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lote', models.CharField(db_index=True, max_length=100, unique=True)),
                ('versao', models.PositiveBigIntegerField(default=0)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('atualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lotes_sync_atualizados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Estado de sincronização do lote', 'verbose_name_plural': 'Estados de sincronização dos lotes'},
        ),
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(db_index=True, max_length=120)),
                ('recebido_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('payload', models.JSONField(default=dict)),
                ('aceitos', models.JSONField(default=list)),
                ('rejeitados', models.JSONField(default=list)),
                ('conflitos', models.JSONField(default=list)),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sync_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-recebido_em']},
        ),
        migrations.CreateModel(
            name='SyncOperation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operacao_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('device_id', models.CharField(db_index=True, max_length=120)),
                ('tipo', models.CharField(db_index=True, max_length=60)),
                ('lote', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('base_lote_versao', models.PositiveBigIntegerField(default=0)),
                ('criado_local_em', models.DateTimeField(blank=True, null=True)),
                ('recebido_em', models.DateTimeField(auto_now_add=True)),
                ('processado_em', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('ACEITA', 'Aceita'), ('CONFLITO', 'Conflito'), ('REJEITADA', 'Rejeitada'), ('CANCELADA', 'Cancelada')], db_index=True, default='PENDENTE', max_length=20)),
                ('payload', models.JSONField(default=dict)),
                ('resultado', models.JSONField(blank=True, default=dict)),
                ('motivo', models.TextField(blank=True, default='')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sync_operacoes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-recebido_em']},
        ),
        migrations.CreateModel(
            name='LoteSyncEvento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lote', models.CharField(db_index=True, max_length=100)),
                ('versao', models.PositiveBigIntegerField(db_index=True)),
                ('tipo', models.CharField(blank=True, default='', max_length=80)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('historico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_sync', to='sapp.historicomovimentacao')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_sync_lote', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['lote', 'versao']},
        ),
        migrations.CreateModel(
            name='SyncConflict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lote', models.CharField(db_index=True, max_length=100)),
                ('base_versao', models.PositiveBigIntegerField(default=0)),
                ('versao_atual', models.PositiveBigIntegerField(default=0)),
                ('contexto_servidor', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('APLICADA', 'Aplicada'), ('AJUSTADA', 'Ajustada'), ('CANCELADA', 'Cancelada')], db_index=True, default='PENDENTE', max_length=20)),
                ('resolucao', models.JSONField(blank=True, default=dict)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('resolvido_em', models.DateTimeField(blank=True, null=True)),
                ('operacao', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='conflito', to='sapp.syncoperation')),
                ('resolvido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conflitos_sync_resolvidos', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-criado_em']},
        ),
        migrations.AddConstraint(
            model_name='lotesyncevento',
            constraint=models.UniqueConstraint(fields=('lote', 'versao'), name='uniq_lote_sync_versao'),
        ),
        migrations.RunPython(seed_lote_sync_states, noop_reverse),
    ]
