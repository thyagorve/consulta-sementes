# teste_entrada.py
import os
import django
import sys

# Configure o Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')
django.setup()

from sapp.models import Cultivar, Peneira, Categoria, Tratamento, Estoque
from django.contrib.auth.models import User

def main():
    print("🧪 TESTE DE ENTRADA NO SISTEMA")
    print("=" * 50)
    
    # 1. Verificar se já existem dados básicos
    print("\n1. Verificando dados básicos...")
    
    cultivares = Cultivar.objects.all()
    peneiras = Peneira.objects.all()
    categorias = Categoria.objects.all()
    tratamentos = Tratamento.objects.all()
    usuarios = User.objects.all()
    
    print(f"   Cultivares encontrados: {cultivares.count()}")
    for c in cultivares:
        print(f"     - {c.nome}")
    
    print(f"   Peneiras encontradas: {peneiras.count()}")
    for p in peneiras:
        print(f"     - {p.nome}")
    
    print(f"   Categorias encontradas: {categorias.count()}")
    for cat in categorias:
        print(f"     - {cat.nome}")
    
    print(f"   Tratamentos encontrados: {tratamentos.count()}")
    for t in tratamentos:
        print(f"     - {t.nome}")
    
    print(f"   Usuários encontrados: {usuarios.count()}")
    for u in usuarios:
        print(f"     - {u.username} ({u.get_full_name()})")
    
    # 2. Criar dados se não existirem
    print("\n2. Criando dados básicos se necessário...")
    
    # Cultivar padrão
    cultivar, created = Cultivar.objects.get_or_create(
        nome='SOJA CONVENCIONAL',
        defaults={'nome': 'SOJA CONVENCIONAL'}
    )
    if created:
        print(f"   ✅ Cultivar criado: {cultivar.nome}")
    else:
        print(f"   ℹ️  Cultivar já existe: {cultivar.nome}")
    
    # Peneira padrão
    peneira, created = Peneira.objects.get_or_create(
        nome='6.0 MM',
        defaults={'nome': '6.0 MM'}
    )
    if created:
        print(f"   ✅ Peneira criada: {peneira.nome}")
    else:
        print(f"   ℹ️  Peneira já existe: {peneira.nome}")
    
    # Categoria padrão
    categoria, created = Categoria.objects.get_or_create(
        nome='SEMENTE COMUM',
        defaults={'nome': 'SEMENTE COMUM'}
    )
    if created:
        print(f"   ✅ Categoria criada: {categoria.nome}")
    else:
        print(f"   ℹ️  Categoria já existe: {categoria.nome}")
    
    # Tratamento padrão
    tratamento, created = Tratamento.objects.get_or_create(
        nome='TRATADO',
        defaults={'nome': 'TRATADO'}
    )
    if created:
        print(f"   ✅ Tratamento criado: {tratamento.nome}")
    else:
        print(f"   ℹ️  Tratamento já existe: {tratamento.nome}")
    
    # Usuário admin
    try:
        admin_user = User.objects.get(username='admin')
        print(f"   ℹ️  Usuário admin já existe: {admin_user.username}")
    except User.DoesNotExist:
        print("   ⚠️  Usuário admin não encontrado. Criando...")
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@sistema.com',
            password='admin123'
        )
        print(f"   ✅ Usuário admin criado: {admin_user.username}")
    
    # 3. Criar lote de teste
    print("\n3. Criando lote de teste...")
    
    try:
        # Verificar se lote já existe
        lote_existente = Estoque.objects.filter(lote='TESTE001').first()
        
        if lote_existente:
            print(f"   ℹ️  Lote TESTE001 já existe:")
            print(f"      - ID: {lote_existente.id}")
            print(f"      - Endereço: {lote_existente.endereco}")
            print(f"      - Saldo: {lote_existente.saldo}")
            
            # Atualizar se necessário
            lote_existente.entrada = 150
            lote_existente.save()
            print(f"   ✅ Lote atualizado: Saldo = {lote_existente.saldo}")
        else:
            # Criar novo lote
            novo_lote = Estoque.objects.create(
                lote='TESTE001',
                produto='SOJA PARA TESTE',
                cultivar=cultivar,
                peneira=peneira,
                categoria=categoria,
                tratamento=tratamento,
                endereco='R01-P01-C01',
                entrada=100,
                saida=0,
                conferente=admin_user,
                especie='SOJA',
                empresa='AGRICOLA TESTE LTDA',
                embalagem='BAG',
                peso_unitario=25.50,
                az='AZ-01',
                cliente='FAZENDA MODELO',
                observacao='Lote criado automaticamente para teste do sistema'
            )
            
            print(f"   ✅ NOVO LOTE CRIADO!")
            print(f"      - ID: {novo_lote.id}")
            print(f"      - Lote: {novo_lote.lote}")
            print(f"      - Endereço: {novo_lote.endereco}")
            print(f"      - Saldo: {novo_lote.saldo}")
            print(f"      - Peso Unitário: {novo_lote.peso_unitario} kg")
            print(f"      - Peso Total: {novo_lote.peso_total} kg")
            print(f"      - Cliente: {novo_lote.cliente}")
            print(f"      - Status: {novo_lote.status}")
    
    except Exception as e:
        print(f"   ❌ ERRO ao criar lote: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Verificar todos os lotes no sistema
    print("\n4. Resumo do estoque atual:")
    
    total_lotes = Estoque.objects.count()
    lotes_com_saldo = Estoque.objects.filter(saldo__gt=0).count()
    lotes_esgotados = Estoque.objects.filter(saldo=0).count()
    
    print(f"   Total de lotes: {total_lotes}")
    print(f"   Lotes com saldo: {lotes_com_saldo}")
    print(f"   Lotes esgotados: {lotes_esgotados}")
    
    if total_lotes > 0:
        print("\n   Últimos 5 lotes:")
        for lote in Estoque.objects.all().order_by('-id')[:5]:
            status_emoji = '✅' if lote.saldo > 0 else '❌'
            print(f"      {status_emoji} {lote.lote} | {lote.endereco} | {lote.saldo} unidades")
    
    print("\n" + "=" * 50)
    print("🧪 TESTE CONCLUÍDO!")
    print("\nAgora você pode:")
    print("1. Acessar http://localhost:8000/estoque/")
    print("2. Testar a 'Nova Entrada' no sistema")
    print("3. Ver o lote TESTE001 na lista")

if __name__ == '__main__':
    main()