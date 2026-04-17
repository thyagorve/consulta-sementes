#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')
django.setup()

from sapp.models import Armazem, Endereco

# ============================================
# CONFIGURE AQUI EXATAMENTE OS ENDEREÇOS QUE VOCÊ QUER
# ============================================

ARMZ = "03"

ENDERECOS = [

    "R-E LN01 P01", "R-E LN01 P02", "R-E LN01 P03", "R-E LN01 P04", "R-E LN01 P05", "R-E LN01 P06",
    "R-E LN02 P01", "R-E LN02 P02", "R-E LN02 P03", "R-E LN02 P04", "R-E LN02 P05", "R-E LN02 P06",
    "R-E LN03 P01", "R-E LN03 P02", "R-E LN03 P03", "R-E LN03 P04", "R-E LN03 P05", "R-E LN03 P06",
    "R-E LN04 P01", "R-E LN04 P02", "R-E LN04 P03", "R-E LN04 P04", "R-E LN04 P05", "R-E LN04 P06",
    "R-E LN05 P01", "R-E LN05 P02", "R-E LN05 P03", "R-E LN05 P04", "R-E LN05 P05", "R-E LN05 P06",
    "R-E LN06 P01", "R-E LN06 P02", "R-E LN06 P03", "R-E LN06 P04", "R-E LN06 P05", "R-E LN06 P06",
    "R-E LN07 P01", "R-E LN07 P02", "R-E LN07 P03", "R-E LN07 P04", "R-E LN07 P05", "R-E LN07 P06",
    "R-E LN08 P01", "R-E LN08 P02", "R-E LN08 P03", "R-E LN08 P04", "R-E LN08 P05", "R-E LN08 P06",
    "R-E LN09 P01", "R-E LN09 P02", "R-E LN09 P03", "R-E LN09 P04", "R-E LN09 P05", "R-E LN09 P06",
    "R-E LN10 P01", "R-E LN10 P02", "R-E LN10 P03", "R-E LN10 P04", "R-E LN10 P05", "R-E LN10 P06",
    "R-E LN11 P01", "R-E LN11 P02", "R-E LN11 P03", "R-E LN11 P04", "R-E LN11 P05", "R-E LN11 P06",
    "R-E LN12 P01", "R-E LN12 P02", "R-E LN12 P03", "R-E LN12 P04", "R-E LN12 P05", "R-E LN12 P06",
    "R-E LN13 P01", "R-E LN13 P02", "R-E LN13 P03", "R-E LN13 P04", "R-E LN13 P05", "R-E LN13 P06",
    


]



# ============================================
# EXECUTA
# ============================================

def main():
    armazem, _ = Armazem.objects.get_or_create(nome=ARMZ)
    print(f"\n📦 Armazém: {armazem.nome}")
    print(f"🚀 Criando {len(ENDERECOS)} endereços...\n")
    
    for i, end in enumerate(ENDERECOS, 1):
        obj, created = Endereco.objects.get_or_create(
            codigo=end.upper(),
            defaults={'armazem': armazem}
        )
        status = "✅ CRIADO" if created else "⚠️  EXISTE"
        print(f"[{i:3d}] {status}: {end}")
    
    print(f"\n✅ Concluído!")

if __name__ == "__main__":
    main()