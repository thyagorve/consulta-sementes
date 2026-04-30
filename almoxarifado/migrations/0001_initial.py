from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Código')),
                ('nome', models.CharField(max_length=200, verbose_name='Nome do Item')),
                ('descricao', models.TextField(blank=True, null=True, verbose_name='Descrição')),
                ('departamento', models.CharField(choices=[('ADM', 'Administrativo'), ('PROD', 'Produção'), ('MAN', 'Manutenção'), ('TI', 'Tecnologia'), ('MKT', 'Marketing'), ('VEND', 'Vendas'), ('RH', 'Recursos Humanos'), ('FIN', 'Financeiro'), ('JUR', 'Jurídico'), ('LOG', 'Logística'), ('QUAL', 'Qualidade'), ('PESQ', 'Pesquisa'), ('OUT', 'Outros')], default='OUT', max_length=4, verbose_name='Departamento')),
                ('quantidade', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Quantidade')),
                ('unidade', models.CharField(choices=[('UN', 'Unidade'), ('CX', 'Caixa'), ('PCT', 'Pacote'), ('KG', 'Quilograma'), ('G', 'Grama'), ('L', 'Litro'), ('ML', 'Mililitro'), ('M', 'Metro'), ('CM', 'Centímetro'), ('PAR', 'Par'), ('DZ', 'Dúzia'), ('RL', 'Rolo'), ('FL', 'Folha')], default='UN', max_length=3, verbose_name='Unidade de Medida')),
                ('localizacao', models.CharField(blank=True, max_length=100, null=True, verbose_name='Localização')),
                ('estoque_minimo', models.IntegerField(default=5, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Estoque Mínimo')),
                ('valor_unitario', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Valor Unitário (R$)')),
                ('fornecedor', models.CharField(blank=True, max_length=200, null=True, verbose_name='Fornecedor')),
                ('foto', models.ImageField(blank=True, null=True, upload_to='itens_fotos/', verbose_name='Foto')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Item',
                'verbose_name_plural': 'Itens',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Saida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_nome', models.CharField(max_length=200, verbose_name='Nome do Item')),
                ('item_codigo', models.CharField(blank=True, max_length=20, null=True, verbose_name='Código')),
                ('solicitante', models.CharField(max_length=200, verbose_name='Solicitante')),
                ('departamento', models.CharField(blank=True, choices=[('ADM', 'Administrativo'), ('PROD', 'Produção'), ('MAN', 'Manutenção'), ('TI', 'Tecnologia'), ('MKT', 'Marketing'), ('VEND', 'Vendas'), ('RH', 'Recursos Humanos'), ('FIN', 'Financeiro'), ('JUR', 'Jurídico'), ('LOG', 'Logística'), ('QUAL', 'Qualidade'), ('PESQ', 'Pesquisa'), ('OUT', 'Outros')], max_length=4, null=True, verbose_name='Departamento')),
                ('quantidade', models.IntegerField(verbose_name='Quantidade')),
                ('data', models.DateField(verbose_name='Data')),
                ('hora', models.TimeField(verbose_name='Hora')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saidas', to='almoxarifado.item', verbose_name='Item')),
            ],
            options={
                'verbose_name': 'Saída',
                'verbose_name_plural': 'Saídas',
                'ordering': ['-data', '-hora'],
            },
        ),
    ]