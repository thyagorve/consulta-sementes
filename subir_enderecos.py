#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')
django.setup()

from sapp.models import Armazem, Endereco

# ============================================
# CONFIGURE AQUI EXATAMENTE OS ENDEREÇOS QUE VOCÊ QUER
# ============================================

ARMZ = "AZ-01"

ENDERECOS = [
    # RUA A
    "R-A LN04 P04", "R-A LN04 P05", "R-A LN04 P06",
    "R-A LN05 P01", "R-A LN05 P02", "R-A LN05 P03", "R-A LN05 P04", "R-A LN05 P05", "R-A LN05 P06",
    "R-A LN06 P01", "R-A LN06 P02", "R-A LN06 P03", "R-A LN06 P04", "R-A LN06 P05", "R-A LN06 P06",
    "R-A LN07 P01", "R-A LN07 P02", "R-A LN07 P03", "R-A LN07 P04", "R-A LN07 P05", "R-A LN07 P06",
    "R-A LN08 P01", "R-A LN08 P02", "R-A LN08 P03", "R-A LN08 P04", "R-A LN08 P05", "R-A LN08 P06",
    "R-A LN09 P01", "R-A LN09 P02", "R-A LN09 P03", "R-A LN09 P04", "R-A LN09 P05", "R-A LN09 P06",
    "R-A LN10 P01", "R-A LN10 P02", "R-A LN10 P03", "R-A LN10 P04", "R-A LN10 P05", "R-A LN10 P06",
    "R-A LN11 P01", "R-A LN11 P02", "R-A LN11 P03", "R-A LN11 P04", "R-A LN11 P05", "R-A LN11 P06",
    "R-A LN12 P01", "R-A LN12 P02", "R-A LN12 P03", "R-A LN12 P04", "R-A LN12 P05", "R-A LN12 P06",
    "R-A LN13 P01", "R-A LN13 P02", "R-A LN13 P03", "R-A LN13 P04", "R-A LN13 P05", "R-A LN13 P06",
    "R-A LN14 P01", "R-A LN14 P02", "R-A LN14 P03", "R-A LN14 P04", "R-A LN14 P05", "R-A LN14 P06",
    "R-A LN15 P01", "R-A LN15 P02", "R-A LN15 P03", "R-A LN15 P04", "R-A LN15 P05", "R-A LN15 P06",
    "R-A LN16 P01", "R-A LN16 P02", "R-A LN16 P03", "R-A LN16 P04", "R-A LN16 P05", "R-A LN16 P06",
    "R-A LN17 P01", "R-A LN17 P02", "R-A LN17 P03", "R-A LN17 P04", "R-A LN17 P05", "R-A LN17 P06",
    "R-A LN18 P01", "R-A LN18 P02", "R-A LN18 P03", "R-A LN18 P04", "R-A LN18 P05", "R-A LN18 P06",
    "R-A LN19 P01", "R-A LN19 P02", "R-A LN19 P03", "R-A LN19 P04", "R-A LN19 P05", "R-A LN19 P06",
    "R-B LN20 P01", "R-B LN20 P02", "R-B LN20 P03", "R-B LN20 P04", "R-B LN20 P05", "R-B LN20 P06",
    "R-B LN21 P01", "R-B LN21 P02", "R-B LN21 P03", "R-B LN21 P04", "R-B LN21 P05", "R-B LN21 P06",
    "R-B LN22 P01", "R-B LN22 P02", "R-B LN22 P03", "R-B LN22 P04", "R-B LN22 P05", "R-B LN22 P06",
    "R-B LN23 P01", "R-B LN23 P02", "R-B LN23 P03", "R-B LN23 P04", "R-B LN23 P05", "R-B LN23 P06",
    "R-B LN24 P01", "R-B LN24 P02", "R-B LN24 P03", "R-B LN24 P04", "R-B LN24 P05", "R-B LN24 P06",
    "R-B LN25 P01", "R-B LN25 P02", "R-B LN25 P03", "R-B LN25 P04", "R-B LN25 P05", "R-B LN25 P06",
    "R-B LN26 P01", "R-B LN26 P02", "R-B LN26 P03", "R-B LN26 P04", "R-B LN26 P05", "R-B LN26 P06",
    "R-B LN27 P01", "R-B LN27 P02", "R-B LN27 P03", "R-B LN27 P04", "R-B LN27 P05", "R-B LN27 P06",
    "R-B LN28 P01", "R-B LN28 P02", "R-B LN28 P03", "R-B LN28 P04", "R-B LN28 P05", "R-B LN28 P06",
    "R-B LN29 P01", "R-B LN29 P02", "R-B LN29 P03", "R-B LN29 P04", "R-B LN29 P05", "R-B LN29 P06",
    "R-B LN30 P01", "R-B LN30 P02", "R-B LN30 P03", "R-B LN30 P04", "R-B LN30 P05", "R-B LN30 P06",
    "R-B LN31 P01", "R-B LN31 P02", "R-B LN31 P03", "R-B LN31 P04", "R-B LN31 P05", "R-B LN31 P06",
    "R-B LN32 P01", "R-B LN32 P02", "R-B LN32 P03", "R-B LN32 P04", "R-B LN32 P05", "R-B LN32 P06",
    "R-B LN33 P01", "R-B LN33 P02", "R-B LN33 P03", "R-B LN33 P04", "R-B LN33 P05", "R-B LN33 P06",
    "R-B LN34 P01", "R-B LN34 P02", "R-B LN34 P03", "R-B LN34 P04", "R-B LN34 P05", "R-B LN34 P06",
    "R-B LN35 P01", "R-B LN35 P02", "R-B LN35 P03", "R-B LN35 P04", "R-B LN35 P05", "R-B LN35 P06",
    "R-B LN36 P01", "R-B LN36 P02", "R-B LN36 P03", "R-B LN36 P04", "R-B LN36 P05", "R-B LN36 P06",
    "R-B LN37 P01", "R-B LN37 P02", "R-B LN37 P03", "R-B LN37 P04", "R-B LN37 P05", "R-B LN37 P06",
    "R-B LN39 P01", "R-B LN39 P02", "R-B LN39 P03", "R-B LN39 P04", "R-B LN39 P05", "R-B LN39 P06",
   


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