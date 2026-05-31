"""
Category normalization for Mobexpert sales data.

Problem: CATEGORIE column has 58 variants including 12+ misspellings
of "MOBILIER BAIE SI SANITARE" alone, plus 26.5% of rows have #null.

Solution: Normalize to 10 canonical categories using:
1. Direct CATEGORIE mapping (handles typos)
2. CLASA fallback (recovers null categories)

Canonical categories:
  ACCESORII                    — accessories, deco, decorations, gratare
  MOBILIER DE CASA             — general home furniture, mic mobilier, dormitoare, exotic
  CANAPELE SI FOTOLII          — sofas, armchairs, recliners
  SALTELE SI SOMIERE           — mattresses, bed bases
  MOBILIER BAIE SI SANITARE    — bathroom furniture, sanitary
  PATURI TAPITATE              — upholstered beds
  MOBILIER OFFICE              — office furniture, operational chairs
  MOBILIER BUCATARII           — kitchen furniture, countertops
  MOBILIER TERASA SI GRADINA   — outdoor, patio, garden furniture
  ALTELE                       — packaging, semi-finished, prototypes, special orders
"""

from typing import Optional


# -------------------------------------------------------------------
# CATEGORIE → canonical mapping
# Every value that appears in the raw data must be listed here.
# -------------------------------------------------------------------
CATEGORIE_MAP: dict[str, str] = {
    # Accessories
    "ACCESORII": "ACCESORII",
    "ACCESORI": "ACCESORII",
    "MOBILIER DE CASA - ACCESORII": "ACCESORII",
    "DECORATIUNI": "ACCESORII",
    "DECORATIUNI OUTDOOR": "ACCESORII",
    "GRATARE SI ACCESORII": "ACCESORII",
    "CUIER": "ACCESORII",

    # Home furniture (general)
    "MOBILIER DE CASA": "MOBILIER DE CASA",
    "MOBILIER CASA": "MOBILIER DE CASA",
    "MOBILIER GENERAL": "MOBILIER DE CASA",
    "MOBILIER": "MOBILIER DE CASA",
    "MOBILI": "MOBILIER DE CASA",
    "MIC MOBILIER": "MOBILIER DE CASA",
    "MOBILIER DE CASA - MIC MOBILIER": "MOBILIER DE CASA",
    "MOBILIERA DE CASA-MIC MOBILIER": "MOBILIER DE CASA",

    # Sofas and armchairs
    "CANAPELE SI FOTOLII": "CANAPELE SI FOTOLII",
    "CANAPEE SI FOTOLII": "CANAPELE SI FOTOLII",
    "SCAUNE SI FOTOLII": "CANAPELE SI FOTOLII",

    # Mattresses and bed bases
    "SALTELE SI SOMIERE": "SALTELE SI SOMIERE",

    # Bathroom furniture — all misspellings
    "MOBILIER BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANITRE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER  BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANIATRE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANIRAE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SSANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIER SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIOER BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBUILIER BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE BAIE": "MOBILIER BAIE SI SANITARE",
    "MOBILIE BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIUER BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANITARE .": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANITARE+": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE CASA - MOBILIER PENTRU BAIE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE IS SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE BAIE SI SANTRE": "MOBILIER BAIE SI SANITARE",
    "SANITARE BAIE": "MOBILIER BAIE SI SANITARE",

    # Upholstered beds
    "PATURI TAPITATE": "PATURI TAPITATE",

    # Office furniture
    "MOBILIER OFFICE": "MOBILIER OFFICE",
    "MOBILER OFFICE": "MOBILIER OFFICE",
    "MOBILIER BIROU": "MOBILIER OFFICE",
    "OFFICE": "MOBILIER OFFICE",
    "SCAUNE BIROU OPERATIONALE": "MOBILIER OFFICE",
    "SCAUN OPERATIONAL": "MOBILIER OFFICE",

    # Kitchen furniture
    "MOBILIER DE CASA - BUCATARII": "MOBILIER BUCATARII",
    "MOBILIER DE CASA-BUCATARII": "MOBILIER BUCATARII",
    "MOBILIER DE CASA -BUCATARII": "MOBILIER BUCATARII",

    # Outdoor / patio
    "MOBILIER TERASA SI GRADINA, INDOOR, ACCESORII": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GRADINA": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GARADINA": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GARDINA": "MOBILIER TERASA SI GRADINA",

    # Other / misc
    "BF 2022 PROMOTII": "ALTELE",
    "DEPOZITARE": "ALTELE",
}

# Junk values that need CLASA-based recovery
JUNK_CATEGORIES = {"#null", "-", " -", "", "."}


# -------------------------------------------------------------------
# CLASA → canonical mapping (for recovering null CATEGORIE rows)
# -------------------------------------------------------------------
CLASA_MAP: dict[str, str] = {
    "006   MOBILIER DE CASA - ACCESORII": "ACCESORII",
    "MM202   MOBILIER GRADINA - OUTDOOR": "MOBILIER TERASA SI GRADINA",
    "MM205   DECO & ACCESORII": "ACCESORII",
    "AMB   AMBALAJE": "ALTELE",
    "MM209   SANITARE BAIE": "MOBILIER BAIE SI SANITARE",
    "015   MOBILIER DE CASA - BUCATARII": "MOBILIER BUCATARII",
    "055   MESE SI SCAUNE": "MOBILIER DE CASA",
    "MM208   MOBILIER BAIE": "MOBILIER BAIE SI SANITARE",
    "MM207   MOBILIER INTERIOR - DECO & ACCESORII": "ACCESORII",
    "001   CANAPELE SI FOTOLII": "CANAPELE SI FOTOLII",
    "003   MOBILIER DE BIROU OPERATIONAL": "MOBILIER OFFICE",
    "017   MOBILIER DE CASA - MIC MOBILIER": "MOBILIER DE CASA",
    "027   PATURI TAPITATE": "PATURI TAPITATE",
    "SPEC   COMENZI SPECIALE": "ALTELE",
    "MM201   MOBILIER EXOTIC": "MOBILIER DE CASA",
    "012   MOBILIER DE CASA - DORMITOARE": "MOBILIER DE CASA",
    "014   MOBILIER EXOTIC SI RATAN": "MOBILIER DE CASA",
    "016   BLATURI COMPOZIT": "MOBILIER BUCATARII",
    "019   SCAUNE SI FOTOLII": "CANAPELE SI FOTOLII",
    "007   MOBILIER DE CASA - BIBLIOTECI": "MOBILIER DE CASA",
    "0011   CANAPELE SI FOTOLII CU RECLINER": "CANAPELE SI FOTOLII",
    "MM206   MOBILIER INTERIOR": "MOBILIER DE CASA",
    "0002   SEMIFABRICATE": "ALTELE",
    "011   MOBILIER DE CASA - SUFRAGERII": "MOBILIER DE CASA",
    "SFB900   SEMIFABRICATE": "ALTELE",
    "0001   PROTOTIPURI": "ALTELE",
    "010   MOBILIER DE CASA - CAMERE TINERET/ COPII": "MOBILIER DE CASA",
    "022   MOBILIER DE CASA - DRESSING": "MOBILIER DE CASA",
    "013   MOBILIER DE CASA - SOMIERE SI SALTELE - SERIE": "SALTELE SI SOMIERE",
}


def normalize_category(categorie: str, clasa: str) -> str:
    """
    Normalize a raw CATEGORIE value to a canonical category.

    Strategy:
    1. If CATEGORIE is a known value → map directly
    2. If CATEGORIE is junk (#null, -, etc.) → recover from CLASA
    3. If neither works → return "NECUNOSCUT" (unknown)

    Args:
        categorie: Raw CATEGORIE value from CSV
        clasa: Raw CLASA value from CSV (fallback)

    Returns:
        Canonical category string
    """
    cat = categorie.strip() if categorie else ""
    cls = clasa.strip() if clasa else ""

    # Step 1: Direct CATEGORIE lookup
    if cat and cat not in JUNK_CATEGORIES and cat in CATEGORIE_MAP:
        return CATEGORIE_MAP[cat]

    # Step 2: CLASA-based recovery
    if cls and cls in CLASA_MAP:
        return CLASA_MAP[cls]

    # Step 3: Fuzzy CLASA match — check if any CLASA key is a substring
    if cls:
        cls_lower = cls.lower()
        for clasa_key, canonical in CLASA_MAP.items():
            if clasa_key.lower() in cls_lower:
                return canonical

    # Step 4: If CATEGORIE has a value but we don't recognize it, flag it
    if cat and cat not in JUNK_CATEGORIES:
        return "NECUNOSCUT"

    return "NECUNOSCUT"


# -------------------------------------------------------------------
# Canonical category list (for validation)
# -------------------------------------------------------------------
CANONICAL_CATEGORIES = frozenset({
    "ACCESORII",
    "MOBILIER DE CASA",
    "CANAPELE SI FOTOLII",
    "SALTELE SI SOMIERE",
    "MOBILIER BAIE SI SANITARE",
    "PATURI TAPITATE",
    "MOBILIER OFFICE",
    "MOBILIER BUCATARII",
    "MOBILIER TERASA SI GRADINA",
    "ALTELE",
    "NECUNOSCUT",
})


def validate_mapping_completeness(csv_path: str) -> dict:
    """
    Run against the original CSV to check how many rows get normalized
    vs how many fall through to NECUNOSCUT.

    Returns dict with counts per canonical category + unmapped details.
    """
    import csv as csv_mod
    from collections import Counter
    from pathlib import Path

    counts = Counter()
    unmapped = Counter()

    with open(Path(csv_path), newline="", encoding="utf-8") as f:
        lines = [line for line in f.readlines() if line.strip()]
        reader = csv_mod.DictReader(iter(lines))

        for row in reader:
            date = row.get("DATA COMANDA", "").strip()
            if not date or date == "#null":
                continue

            cat = row.get("CATEGORIE", "").strip()
            cls = row.get("CLASA", "").strip()
            rev = float(row.get("VALOARE FACTURATA", "0").strip().replace(",", ".") or "0")
            qty = float(row.get("CANTITATE FACTURATA", "0").strip().replace(",", ".") or "0")

            combined = (cat + " " + cls).lower()
            if any(kw in combined for kw in ["transport", "livrare", "montaj", "discount", "servicii"]):
                continue
            if rev == 0.0 and qty >= 0:
                continue

            normalized = normalize_category(cat, cls)
            counts[normalized] += 1
            if normalized == "NECUNOSCUT":
                unmapped[(cat, cls)] += 1

    return {"counts": counts, "unmapped": unmapped}


if __name__ == "__main__":
    import sys
    from pathlib import Path

    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parent.parent.parent / "sales_2024_and_nulls.csv"
    )

    print(f"Validating category mapping against: {csv_path}\n")
    result = validate_mapping_completeness(csv_path)

    total = sum(result["counts"].values())
    mapped = total - result["counts"].get("NECUNOSCUT", 0)

    print(f"{'Category':<35} {'Rows':>8} {'%':>6}")
    print("-" * 52)
    for cat, count in result["counts"].most_common():
        pct = count / total * 100
        flag = " ← UNMAPPED" if cat == "NECUNOSCUT" else ""
        print(f"{cat:<35} {count:>8,} {pct:>5.1f}%{flag}")

    print("-" * 52)
    print(f"{'TOTAL':<35} {total:>8,}")
    print(f"\nMapped: {mapped:,} / {total:,} ({mapped/total*100:.2f}%)")

    if result["unmapped"]:
        print(f"\n⚠ UNMAPPED rows ({sum(result['unmapped'].values())}):")
        for (cat, cls), count in result["unmapped"].most_common(20):
            print(f"  {count:>4}x  CAT=|{cat}|  CLASA=|{cls}|")
