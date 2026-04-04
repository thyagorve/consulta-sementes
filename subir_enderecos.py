#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')
django.setup()

from sapp.models import Armazem, Endereco

# ============================================
# CONFIGURE AQUI EXATAMENTE OS ENDEREÇOS QUE VOCÊ QUER
# ============================================

ARMZ = "AZ-03"

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
    "R-E LN14 P01", "R-E LN14 P02", "R-E LN14 P03", "R-E LN14 P04", "R-E LN14 P05", "R-E LN14 P06",
    "R-E LN15 P01", "R-E LN15 P02", "R-E LN15 P03", "R-E LN15 P04", "R-E LN15 P05", "R-E LN15 P06",
    "R-E LN16 P01", "R-E LN16 P02", "R-E LN16 P03", "R-E LN16 P04", "R-E LN16 P05", "R-E LN16 P06",
    "R-E LN17 P01", "R-E LN17 P02", "R-E LN17 P03", "R-E LN17 P04", "R-E LN17 P05", "R-E LN17 P06",
    "R-E LN18 P01", "R-E LN18 P02", "R-E LN18 P03", "R-E LN18 P04", "R-E LN18 P05", "R-E LN18 P06",
    "R-E LN19 P01", "R-E LN19 P02", "R-E LN19 P03", "R-E LN19 P04", "R-E LN19 P05", "R-E LN19 P06",
    "R-E LN20 P01", "R-E LN20 P02", "R-E LN20 P03", "R-E LN20 P04", "R-E LN20 P05", "R-E LN20 P06",
    "R-E LN21 P01", "R-E LN21 P02", "R-E LN21 P03", "R-E LN21 P04", "R-E LN21 P05", "R-E LN21 P06",
    "R-E LN22 P01", "R-E LN22 P02", "R-E LN22 P03", "R-E LN22 P04", "R-E LN22 P05", "R-E LN22 P06",
    "R-E LN23 P01", "R-E LN23 P02", "R-E LN23 P03", "R-E LN23 P04", "R-E LN23 P05", "R-E LN23 P06",
    "R-E LN24 P01", "R-E LN24 P02", "R-E LN24 P03", "R-E LN24 P04", "R-E LN24 P05", "R-E LN24 P06",
    "R-E LN25 P01", "R-E LN25 P02", "R-E LN25 P03", "R-E LN25 P04", "R-E LN25 P05", "R-E LN25 P06",
    "R-E LN26 P01", "R-E LN26 P02", "R-E LN26 P03", "R-E LN26 P04", "R-E LN26 P05", "R-E LN26 P06",
    "R-E LN27 P01", "R-E LN27 P02", "R-E LN27 P03", "R-E LN27 P04", "R-E LN27 P05", "R-E LN27 P06",
    "R-E LN28 P01", "R-E LN28 P02", "R-E LN28 P03", "R-E LN28 P04", "R-E LN28 P05", "R-E LN28 P06",
    "R-E LN29 P01", "R-E LN29 P02", "R-E LN29 P03", "R-E LN29 P04", "R-E LN29 P05", "R-E LN29 P06",
    "R-E LN30 P01", "R-E LN30 P02", "R-E LN30 P03", "R-E LN30 P04", "R-E LN30 P05", "R-E LN30 P06",

    "R-F LN01 P01", "R-F LN01 P02", "R-F LN01 P03", "R-F LN01 P04", "R-F LN01 P05", "R-F LN01 P06",
    "R-F LN02 P01", "R-F LN02 P02", "R-F LN02 P03", "R-F LN02 P04", "R-F LN02 P05", "R-F LN02 P06",
    "R-F LN03 P01", "R-F LN03 P02", "R-F LN03 P03", "R-F LN03 P04", "R-F LN03 P05", "R-F LN03 P06",
    "R-F LN04 P01", "R-F LN04 P02", "R-F LN04 P03", "R-F LN04 P04", "R-F LN04 P05", "R-F LN04 P06",
    "R-F LN05 P01", "R-F LN05 P02", "R-F LN05 P03", "R-F LN05 P04", "R-F LN05 P05", "R-F LN05 P06",
    "R-F LN06 P01", "R-F LN06 P02", "R-F LN06 P03", "R-F LN06 P04", "R-F LN06 P05", "R-F LN06 P06",
    "R-F LN07 P01", "R-F LN07 P02", "R-F LN07 P03", "R-F LN07 P04", "R-F LN07 P05", "R-F LN07 P06",
    "R-F LN08 P01", "R-F LN08 P02", "R-F LN08 P03", "R-F LN08 P04", "R-F LN08 P05", "R-F LN08 P06",
    "R-F LN09 P01", "R-F LN09 P02", "R-F LN09 P03", "R-F LN09 P04", "R-F LN09 P05", "R-F LN09 P06",
    "R-F LN10 P01", "R-F LN10 P02", "R-F LN10 P03", "R-F LN10 P04", "R-F LN10 P05", "R-F LN10 P06",
    "R-F LN11 P01", "R-F LN11 P02", "R-F LN11 P03", "R-F LN11 P04", "R-F LN11 P05", "R-F LN11 P06",
    "R-F LN12 P01", "R-F LN12 P02", "R-F LN12 P03", "R-F LN12 P04", "R-F LN12 P05", "R-F LN12 P06",
    "R-F LN13 P01", "R-F LN13 P02", "R-F LN13 P03", "R-F LN13 P04", "R-F LN13 P05", "R-F LN13 P06",
    "R-F LN14 P01", "R-F LN14 P02", "R-F LN14 P03", "R-F LN14 P04", "R-F LN14 P05", "R-F LN14 P06",
    "R-F LN15 P01", "R-F LN15 P02", "R-F LN15 P03", "R-F LN15 P04", "R-F LN15 P05", "R-F LN15 P06",
    "R-F LN16 P01", "R-F LN16 P02", "R-F LN16 P03", "R-F LN16 P04", "R-F LN16 P05", "R-F LN16 P06",
    "R-F LN17 P01", "R-F LN17 P02", "R-F LN17 P03", "R-F LN17 P04", "R-F LN17 P05", "R-F LN17 P06",
    "R-F LN18 P01", "R-F LN18 P02", "R-F LN18 P03", "R-F LN18 P04", "R-F LN18 P05", "R-F LN18 P06",
    "R-F LN19 P01", "R-F LN19 P02", "R-F LN19 P03", "R-F LN19 P04", "R-F LN19 P05", "R-F LN19 P06",
    "R-F LN20 P01", "R-F LN20 P02", "R-F LN20 P03", "R-F LN20 P04", "R-F LN20 P05", "R-F LN20 P06",
    "R-F LN21 P01", "R-F LN21 P02", "R-F LN21 P03", "R-F LN21 P04", "R-F LN21 P05", "R-F LN21 P06",
    "R-F LN22 P01", "R-F LN22 P02", "R-F LN22 P03", "R-F LN22 P04", "R-F LN22 P05", "R-F LN22 P06",
    "R-F LN23 P01", "R-F LN23 P02", "R-F LN23 P03", "R-F LN23 P04", "R-F LN23 P05", "R-F LN23 P06",
    "R-F LN24 P01", "R-F LN24 P02", "R-F LN24 P03", "R-F LN24 P04", "R-F LN24 P05", "R-F LN24 P06",
    "R-F LN25 P01", "R-F LN25 P02", "R-F LN25 P03", "R-F LN25 P04", "R-F LN25 P05", "R-F LN25 P06",
    "R-F LN26 P01", "R-F LN26 P02", "R-F LN26 P03", "R-F LN26 P04", "R-F LN26 P05", "R-F LN26 P06",
    "R-F LN27 P01", "R-F LN27 P02", "R-F LN27 P03", "R-F LN27 P04", "R-F LN27 P05", "R-F LN27 P06",
    "R-F LN28 P01", "R-F LN28 P02", "R-F LN28 P03", "R-F LN28 P04", "R-F LN28 P05", "R-F LN28 P06",
    "R-F LN29 P01", "R-F LN29 P02", "R-F LN29 P03", "R-F LN29 P04", "R-F LN29 P05", "R-F LN29 P06",
    "R-F LN30 P01", "R-F LN30 P02", "R-F LN30 P03", "R-F LN30 P04", "R-F LN30 P05", "R-F LN30 P06",

    "R-G LN01 P01", "R-G LN01 P02", "R-G LN01 P03", "R-G LN01 P04", "R-G LN01 P05", "R-G LN01 P06",
    "R-G LN02 P01", "R-G LN02 P02", "R-G LN02 P03", "R-G LN02 P04", "R-G LN02 P05", "R-G LN02 P06",
    "R-G LN03 P01", "R-G LN03 P02", "R-G LN03 P03", "R-G LN03 P04", "R-G LN03 P05", "R-G LN03 P06",
    "R-G LN04 P01", "R-G LN04 P02", "R-G LN04 P03", "R-G LN04 P04", "R-G LN04 P05", "R-G LN04 P06",
    "R-G LN05 P01", "R-G LN05 P02", "R-G LN05 P03", "R-G LN05 P04", "R-G LN05 P05", "R-G LN05 P06",
    "R-G LN06 P01", "R-G LN06 P02", "R-G LN06 P03", "R-G LN06 P04", "R-G LN06 P05", "R-G LN06 P06",
    "R-G LN07 P01", "R-G LN07 P02", "R-G LN07 P03", "R-G LN07 P04", "R-G LN07 P05", "R-G LN07 P06",
    "R-G LN08 P01", "R-G LN08 P02", "R-G LN08 P03", "R-G LN08 P04", "R-G LN08 P05", "R-G LN08 P06",
    "R-G LN09 P01", "R-G LN09 P02", "R-G LN09 P03", "R-G LN09 P04", "R-G LN09 P05", "R-G LN09 P06",
    "R-G LN10 P01", "R-G LN10 P02", "R-G LN10 P03", "R-G LN10 P04", "R-G LN10 P05", "R-G LN10 P06",
    "R-G LN11 P01", "R-G LN11 P02", "R-G LN11 P03", "R-G LN11 P04", "R-G LN11 P05", "R-G LN11 P06",
    "R-G LN12 P01", "R-G LN12 P02", "R-G LN12 P03", "R-G LN12 P04", "R-G LN12 P05", "R-G LN12 P06",
    "R-G LN13 P01", "R-G LN13 P02", "R-G LN13 P03", "R-G LN13 P04", "R-G LN13 P05", "R-G LN13 P06",
    "R-G LN14 P01", "R-G LN14 P02", "R-G LN14 P03", "R-G LN14 P04", "R-G LN14 P05", "R-G LN14 P06",
    "R-G LN15 P01", "R-G LN15 P02", "R-G LN15 P03", "R-G LN15 P04", "R-G LN15 P05", "R-G LN15 P06",
    "R-G LN16 P01", "R-G LN16 P02", "R-G LN16 P03", "R-G LN16 P04", "R-G LN16 P05", "R-G LN16 P06",
    "R-G LN17 P01", "R-G LN17 P02", "R-G LN17 P03", "R-G LN17 P04", "R-G LN17 P05", "R-G LN17 P06",
    "R-G LN18 P01", "R-G LN18 P02", "R-G LN18 P03", "R-G LN18 P04", "R-G LN18 P05", "R-G LN18 P06",
    "R-G LN19 P01", "R-G LN19 P02", "R-G LN19 P03", "R-G LN19 P04", "R-G LN19 P05", "R-G LN19 P06",
    "R-G LN20 P01", "R-G LN20 P02", "R-G LN20 P03", "R-G LN20 P04", "R-G LN20 P05", "R-G LN20 P06",
    "R-G LN21 P01", "R-G LN21 P02", "R-G LN21 P03", "R-G LN21 P04", "R-G LN21 P05", "R-G LN21 P06",
    "R-G LN22 P01", "R-G LN22 P02", "R-G LN22 P03", "R-G LN22 P04", "R-G LN22 P05", "R-G LN22 P06",
    "R-G LN23 P01", "R-G LN23 P02", "R-G LN23 P03", "R-G LN23 P04", "R-G LN23 P05", "R-G LN23 P06",
    "R-G LN24 P01", "R-G LN24 P02", "R-G LN24 P03", "R-G LN24 P04", "R-G LN24 P05", "R-G LN24 P06",
    "R-G LN25 P01", "R-G LN25 P02", "R-G LN25 P03", "R-G LN25 P04", "R-G LN25 P05", "R-G LN25 P06",
    "R-G LN26 P01", "R-G LN26 P02", "R-G LN26 P03", "R-G LN26 P04", "R-G LN26 P05", "R-G LN26 P06",
    "R-G LN27 P01", "R-G LN27 P02", "R-G LN27 P03", "R-G LN27 P04", "R-G LN27 P05", "R-G LN27 P06",
    "R-G LN28 P01", "R-G LN28 P02", "R-G LN28 P03", "R-G LN28 P04", "R-G LN28 P05", "R-G LN28 P06",
    "R-G LN29 P01", "R-G LN29 P02", "R-G LN29 P03", "R-G LN29 P04", "R-G LN29 P05", "R-G LN29 P06",
    "R-G LN30 P01", "R-G LN30 P02", "R-G LN30 P03", "R-G LN30 P04", "R-G LN30 P05", "R-G LN30 P06",


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