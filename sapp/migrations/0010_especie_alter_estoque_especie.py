from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings 

def converter_dados_especie(apps, schema_editor):
    # Pega as versões históricas dos modelos
    Estoque = apps.get_model('sapp', 'Estoque')
    Especie = apps.get_model('sapp', 'Especie')

    # Itera sobre todos os itens
    for item in Estoque.objects.all():
        texto = item.especie_old # Pega o texto da coluna renomeada
        if texto:
            nome_limpo = str(texto).strip().upper()
            # Cria a espécie se não existir
            obj, created = Especie.objects.get_or_create(nome=nome_limpo)
            # Vincula ao novo campo
            item.especie = obj 
            item.save()

class Migration(migrations.Migration):

    dependencies = [
        # AQUI ESTÁ A DEPENDÊNCIA CORRETA DO SEU PROJETO:
        ('sapp', '0009_empenhostatus_alter_estoque_az_alter_estoque_cliente_and_more'),
        
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Cria a tabela Especie
        migrations.CreateModel(
            name='Especie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True)),
            ],
        ),
        
        # 2. Renomeia a coluna 'especie' (que tem texto) para 'especie_old'
        migrations.RenameField(
            model_name='estoque',
            old_name='especie',
            new_name='especie_old',
        ),

        # 3. Cria a nova coluna 'especie' (Chave Estrangeira) vazia
        migrations.AddField(
            model_name='estoque',
            name='especie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='sapp.especie'),
        ),

        # 4. Roda o script para converter os dados (Texto -> ID)
        migrations.RunPython(converter_dados_especie),

        # 5. Apagar a coluna 'especie_old' (texto)
        migrations.RemoveField(
            model_name='estoque',
            name='especie_old',
        ),
    ]