#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')
django.setup()

from sapp.models import Armazem, Endereco

# ============================================
# CONFIGURE AQUI EXATAMENTE OS ENDEREÇOS QUE VOCÊ QUER
# ============================================

ARMZ = "AZ-02"

ENDERECOS = [

    "R-C LN01 P01", "R-C LN01 P02", "R-C LN01 P03", "R-C LN01 P04", "R-C LN01 P05", "R-C LN01 P06",
    "R-C LN02 P01", "R-C LN02 P02", "R-C LN02 P03", "R-C LN02 P04", "R-C LN02 P05", "R-C LN02 P06",
    "R-C LN03 P01", "R-C LN03 P02", "R-C LN03 P03", "R-C LN03 P04", "R-C LN03 P05", "R-C LN03 P06",
    "R-C LN04 P01", "R-C LN04 P02", "R-C LN04 P03", "R-C LN04 P04", "R-C LN04 P05", "R-C LN04 P06",
    "R-C LN05 P01", "R-C LN05 P02", "R-C LN05 P03", "R-C LN05 P04", "R-C LN05 P05", "R-C LN05 P06",
    "R-C LN06 P01", "R-C LN06 P02", "R-C LN06 P03", "R-C LN06 P04", "R-C LN06 P05", "R-C LN06 P06",
    "R-C LN07 P01", "R-C LN07 P02", "R-C LN07 P03", "R-C LN07 P04", "R-C LN07 P05", "R-C LN07 P06",
    "R-C LN08 P01", "R-C LN08 P02", "R-C LN08 P03", "R-C LN08 P04", "R-C LN08 P05", "R-C LN08 P06",
    "R-C LN09 P01", "R-C LN09 P02", "R-C LN09 P03", "R-C LN09 P04", "R-C LN09 P05", "R-C LN09 P06",
    "R-C LN10 P01", "R-C LN10 P02", "R-C LN10 P03", "R-C LN10 P04", "R-C LN10 P05", "R-C LN10 P06",
    "R-C LN11 P01", "R-C LN11 P02", "R-C LN11 P03", "R-C LN11 P04", "R-C LN11 P05", "R-C LN11 P06",
    "R-C LN12 P01", "R-C LN12 P02", "R-C LN12 P03", "R-C LN12 P04", "R-C LN12 P05", "R-C LN12 P06",
    "R-C LN13 P01", "R-C LN13 P02", "R-C LN13 P03", "R-C LN13 P04", "R-C LN13 P05", "R-C LN13 P06",
    "R-C LN14 P01", "R-C LN14 P02", "R-C LN14 P03", "R-C LN14 P04", "R-C LN14 P05", "R-C LN14 P06",
    "R-C LN15 P01", "R-C LN15 P02", "R-C LN15 P03", "R-C LN15 P04", "R-C LN15 P05", "R-C LN15 P06",
    "R-C LN16 P01", "R-C LN16 P02", "R-C LN16 P03", "R-C LN16 P04", "R-C LN16 P05", "R-C LN16 P06",
    "R-C LN17 P01", "R-C LN17 P02", "R-C LN17 P03", "R-C LN17 P04", "R-C LN17 P05", "R-C LN17 P06",
    "R-C LN18 P01", "R-C LN18 P02", "R-C LN18 P03", "R-C LN18 P04", "R-C LN18 P05", "R-C LN18 P06",
    "R-C LN19 P01", "R-C LN19 P02", "R-C LN19 P03", "R-C LN19 P04", "R-C LN19 P05", "R-C LN19 P06",
    "R-C LN20 P01", "R-C LN20 P02", "R-C LN20 P03", "R-C LN20 P04", "R-C LN20 P05", "R-C LN20 P06",
    "R-C LN22 P01", "R-C LN22 P02", "R-C LN22 P03", "R-C LN22 P04", "R-C LN22 P05", "R-C LN22 P06",
    
    # R-D LN23 a LN48
    "R-D LN21 P01", "R-D LN21 P02", "R-D LN21 P03", "R-D LN21 P04", "R-D LN21 P05", "R-D LN21 P06",
    "R-D LN23 P01", "R-D LN23 P02", "R-D LN23 P03", "R-D LN23 P04", "R-D LN23 P05", "R-D LN23 P06",
    "R-D LN24 P01", "R-D LN24 P02", "R-D LN24 P03", "R-D LN24 P04", "R-D LN24 P05", "R-D LN24 P06",
    "R-D LN25 P01", "R-D LN25 P02", "R-D LN25 P03", "R-D LN25 P04", "R-D LN25 P05", "R-D LN25 P06",
    "R-D LN26 P01", "R-D LN26 P02", "R-D LN26 P03", "R-D LN26 P04", "R-D LN26 P05", "R-D LN26 P06",
    "R-D LN27 P01", "R-D LN27 P02", "R-D LN27 P03", "R-D LN27 P04", "R-D LN27 P05", "R-D LN27 P06",
    "R-D LN28 P01", "R-D LN28 P02", "R-D LN28 P03", "R-D LN28 P04", "R-D LN28 P05", "R-D LN28 P06",
    "R-D LN29 P01", "R-D LN29 P02", "R-D LN29 P03", "R-D LN29 P04", "R-D LN29 P05", "R-D LN29 P06",
    "R-D LN30 P01", "R-D LN30 P02", "R-D LN30 P03", "R-D LN30 P04", "R-D LN30 P05", "R-D LN30 P06",
    "R-D LN31 P01", "R-D LN31 P02", "R-D LN31 P03", "R-D LN31 P04", "R-D LN31 P05", "R-D LN31 P06",
    "R-D LN32 P01", "R-D LN32 P02", "R-D LN32 P03", "R-D LN32 P04", "R-D LN32 P05", "R-D LN32 P06",
    "R-D LN33 P01", "R-D LN33 P02", "R-D LN33 P03", "R-D LN33 P04", "R-D LN33 P05", "R-D LN33 P06",
    "R-D LN34 P01", "R-D LN34 P02", "R-D LN34 P03", "R-D LN34 P04", "R-D LN34 P05", "R-D LN34 P06",
    "R-D LN35 P01", "R-D LN35 P02", "R-D LN35 P03", "R-D LN35 P04", "R-D LN35 P05", "R-D LN35 P06",
    "R-D LN36 P01", "R-D LN36 P02", "R-D LN36 P03", "R-D LN36 P04", "R-D LN36 P05", "R-D LN36 P06",
    "R-D LN37 P01", "R-D LN37 P02", "R-D LN37 P03", "R-D LN37 P04", "R-D LN37 P05", "R-D LN37 P06",
    "R-D LN38 P01", "R-D LN38 P02", "R-D LN38 P03", "R-D LN38 P04", "R-D LN38 P05", "R-D LN38 P06",
    "R-D LN39 P01", "R-D LN39 P02", "R-D LN39 P03", "R-D LN39 P04", "R-D LN39 P05", "R-D LN39 P06",
    "R-D LN40 P01", "R-D LN40 P02", "R-D LN40 P03", "R-D LN40 P04", "R-D LN40 P05", "R-D LN40 P06",
    "R-D LN41 P01", "R-D LN41 P02", "R-D LN41 P03", "R-D LN41 P04", "R-D LN41 P05", "R-D LN41 P06",
    "R-D LN42 P01", "R-D LN42 P02", "R-D LN42 P03", "R-D LN42 P04", "R-D LN42 P05", "R-D LN42 P06",
    "R-D LN43 P01", "R-D LN43 P02", "R-D LN43 P03", "R-D LN43 P04", "R-D LN43 P05", "R-D LN43 P06",
    "R-D LN44 P01", "R-D LN44 P02", "R-D LN44 P03", "R-D LN44 P04", "R-D LN44 P05", "R-D LN44 P06",
    "R-D LN45 P01", "R-D LN45 P02", "R-D LN45 P03", "R-D LN45 P04", "R-D LN45 P05", "R-D LN45 P06",
    "R-D LN46 P01", "R-D LN46 P02", "R-D LN46 P03", "R-D LN46 P04", "R-D LN46 P05", "R-D LN46 P06",
    "R-D LN47 P01", "R-D LN47 P02", "R-D LN47 P03", "R-D LN47 P04", "R-D LN47 P05", "R-D LN47 P06",
    "R-D LN48 P01", "R-D LN48 P02", "R-D LN48 P03", "R-D LN48 P04", "R-D LN48 P05", "R-D LN48 P06",

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