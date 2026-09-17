from django.db import migrations


def _normalizar_numero(valor):
    texto = str(valor or '').strip().upper()
    if not texto:
        return ''
    texto = texto.replace('-', ' ').replace(':', ' ')
    texto = ' '.join(texto.split())
    if texto.startswith('CARGA'):
        texto = texto[5:].strip()
    if not texto.isdigit():
        return ''
    return f"CARGA {texto.lstrip('0') or '0'}"


def normalizar_cargas_avulsas(apps, schema_editor):
    HistoricoMovimentacao = apps.get_model('sapp', 'HistoricoMovimentacao')
    qs = HistoricoMovimentacao.objects.filter(origem_carga='AVULSA').exclude(numero_carga__isnull=True).exclude(numero_carga='')
    for mov in qs.iterator(chunk_size=500):
        numero = _normalizar_numero(mov.numero_carga)
        if not numero:
            # Não inventa número para texto legado; fica disponível para correção manual.
            continue
        campos = []
        if mov.numero_carga != numero:
            mov.numero_carga = numero
            campos.append('numero_carga')
        if mov.nome_carga_avulsa:
            # Quando existe número, ele é a identidade oficial da avulsa.
            mov.nome_carga_avulsa = ''
            campos.append('nome_carga_avulsa')
        if campos:
            mov.save(update_fields=campos)


class Migration(migrations.Migration):
    dependencies = [
        ('sapp', '0043_offline_sync'),
    ]

    operations = [
        migrations.RunPython(normalizar_cargas_avulsas, migrations.RunPython.noop),
    ]
