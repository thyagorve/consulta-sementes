# scripts/migrar_enderecos.py
from sapp.models import Estoque, Endereco, Rua, Linha, Armazem

def migrar_enderecos_existentes():
    """Converte endereços antigos para o novo modelo Endereco"""
    
    for estoque in Estoque.objects.all():
        # Se já tiver endereço no formato string, pula
        if hasattr(estoque, 'endereco') and estoque.endereco:
            continue
            
        # Tenta recuperar do formato antigo
        rua = getattr(estoque, 'rua', None)
        linha = getattr(estoque, 'linha', None)
        armazem = getattr(estoque, 'armazem', None)
        
        if rua and armazem:
            rua_nome = rua.nome if hasattr(rua, 'nome') else str(rua)
            linha_nome = linha.nome if linha and hasattr(linha, 'nome') else None
            
            if linha_nome:
                endereco_str = f"{rua_nome} {linha_nome}"
            else:
                endereco_str = f"{rua_nome} GERAL"
            
            # Cria o endereço no novo modelo
            endereco, created = Endereco.objects.get_or_create(
                codigo=endereco_str,
                defaults={
                    'rua': rua_nome,
                    'linha': linha_nome,
                    'tipo': 'LINHA' if linha_nome else 'GERAL',
                    'armazem': armazem if isinstance(armazem, Armazem) else Armazem.objects.first()
                }
            )
            
            estoque.endereco = endereco.codigo
            estoque.save()
            
            print(f"✅ Migrado: {estoque.lote} -> {endereco.codigo}")