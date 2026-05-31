"""V2 hierarchy normalization for richer multi-store Mobexpert exports.

The legacy normalizer only used CATEGORIE and CLASA. V2 files can carry useful
signal in SUBCLASA, GRUPA, RAION, and product names, especially for Pipera-style
exports where top-level category fields are blank.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


UNKNOWN = "NECUNOSCUT"

CANONICAL_CATEGORIES = frozenset(
    {
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
        UNKNOWN,
    }
)

CHANNEL_ONLY_VALUES = {
    "ONLINE",
    "OUTLET",
    "VANZARI DIRECTE",
    "VANZARI DIRECTE OFFICE",
    "SALARIATI",
}

JUNK_VALUES = {"", "#NULL", "-", ".", "NULL", "NAN", "NONE"}


@dataclass(frozen=True)
class HierarchyResult:
    category_norm: str
    category_source: str
    category_signal_status: str
    product_family_v2: str
    product_family_source: str
    product_family_signal_status: str


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def clean_key(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", "").strip().strip('"').strip()
    text = _strip_accents(text).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def _strip_numeric_code(value: str) -> str:
    value = clean_key(value)
    value = re.sub(r"^\d{1,4}\s+", "", value)
    return value.strip()


def _is_meaningful(value: object) -> bool:
    cleaned = clean_key(value)
    return cleaned not in JUNK_VALUES


def _family_from_value(value: object) -> str | None:
    if not _is_meaningful(value):
        return None
    family = _strip_numeric_code(str(value))
    family = re.sub(r"^TOTAL\s+", "", family)
    family = re.sub(r"\s+", " ", family).strip()
    if family in JUNK_VALUES or family in CHANNEL_ONLY_VALUES:
        return None
    return FAMILY_CANONICAL_MAP.get(family, family)


EXACT_CATEGORY_MAP = {
    "ACCESORII": "ACCESORII",
    "ACCESORI": "ACCESORII",
    "MOBILIER DE CASA - ACCESORII": "ACCESORII",
    "DECORATIUNI": "ACCESORII",
    "DECORATIUNI OUTDOOR": "ACCESORII",
    "DECO & ACCESORII": "ACCESORII",
    "MOBILIER INTERIOR - DECO & ACCESORII": "ACCESORII",
    "CORPURI DE ILUMINAT": "ACCESORII",
    "COVOR": "ACCESORII",
    "TABLETOP": "ACCESORII",
    "GOURMET": "ACCESORII",
    "GREEN PLANTE": "ACCESORII",
    "GREEN VAZE": "ACCESORII",
    "CHRISTMAS": "ACCESORII",
    "TAPET": "ACCESORII",
    "TEXTILE BAIE": "ACCESORII",
    "TEXTILE MASA": "ACCESORII",
    "TEXTILE PAT": "ACCESORII",
    "DECO FEREASTRA": "ACCESORII",
    "DECO PERETE": "ACCESORII",
    "ALTE DECO": "ACCESORII",
    "ODORIZANTE": "ACCESORII",
    "ACCESORII BAIE": "ACCESORII",
    "CUIER": "ACCESORII",
    "GRATARE SI ACCESORII": "ACCESORII",
    "MOBILIER DE CASA": "MOBILIER DE CASA",
    "MOBILIER CASA": "MOBILIER DE CASA",
    "MOBILIER GENERAL": "MOBILIER DE CASA",
    "MOBILIER": "MOBILIER DE CASA",
    "MOBILI": "MOBILIER DE CASA",
    "MIC MOBILIER": "MOBILIER DE CASA",
    "MOBILIER DE CASA - MIC MOBILIER": "MOBILIER DE CASA",
    "MOBILIERA DE CASA-MIC MOBILIER": "MOBILIER DE CASA",
    "MOBILIER CORP": "MOBILIER DE CASA",
    "TOTAL MOBILIER CASA": "MOBILIER DE CASA",
    "CAMERE COPII": "MOBILIER DE CASA",
    "CAMERE TINERET/ COPII": "MOBILIER DE CASA",
    "MOBILIER SCOLI SI GRADINITE": "MOBILIER DE CASA",
    "MESE SI SCAUNE": "MOBILIER DE CASA",
    "DEPOZITARE": "MOBILIER DE CASA",
    "LIVING": "MOBILIER DE CASA",
    "CASUTA": "MOBILIER DE CASA",
    "CASA FIXA": "MOBILIER DE CASA",
    "CASA MOBILA": "MOBILIER DE CASA",
    "CASUTA MOBILA": "MOBILIER DE CASA",
    "CANAPELE SI FOTOLII": "CANAPELE SI FOTOLII",
    "CANAPELE SI FOTOLII CU RECLINER": "CANAPELE SI FOTOLII",
    "CANAPEE SI FOTOLII": "CANAPELE SI FOTOLII",
    "CANAPELE SI FOTOLII ": "CANAPELE SI FOTOLII",
    "CANAPELE  SI FOTOLII": "CANAPELE SI FOTOLII",
    "SOFTMEX": "CANAPELE SI FOTOLII",
    "SALTELE SI SOMIERE": "SALTELE SI SOMIERE",
    "SERTA": "SALTELE SI SOMIERE",
    "SEALY": "SALTELE SI SOMIERE",
    "GENETICS": "SALTELE SI SOMIERE",
    "CULTURA SOMNULUI": "SALTELE SI SOMIERE",
    "PATURI TAPITATE": "PATURI TAPITATE",
    "MOBILIER BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANITRE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SI SANIATRE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE BAIE SI SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE SANITARE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER DE BAIE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER BAIE": "MOBILIER BAIE SI SANITARE",
    "SANITARE": "MOBILIER BAIE SI SANITARE",
    "SANITARE BAIE": "MOBILIER BAIE SI SANITARE",
    "MOBILIER OFFICE": "MOBILIER OFFICE",
    "MOBILER OFFICE": "MOBILIER OFFICE",
    "MOBILIER BIROU": "MOBILIER OFFICE",
    "OFFICE": "MOBILIER OFFICE",
    "TOTAL OFFICE": "MOBILIER OFFICE",
    "SCAUNE BIROU OPERATIONALE": "MOBILIER OFFICE",
    "SCAUNE BIROU MANAGERIALE": "MOBILIER OFFICE",
    "SCAUN OPERATIONAL": "MOBILIER OFFICE",
    "SCAUNE VIZITATOR": "MOBILIER OFFICE",
    "BIROURI MANAGERIALE": "MOBILIER OFFICE",
    "BIROURI OPERATIONALE": "MOBILIER OFFICE",
    "SALI CONSILIU": "MOBILIER OFFICE",
    "ZONA ASTEPTARE": "MOBILIER OFFICE",
    "MOBILIER DE CASA - BUCATARII": "MOBILIER BUCATARII",
    "MOBILIER DE CASA-BUCATARII": "MOBILIER BUCATARII",
    "MOBILIER DE CASA -BUCATARII": "MOBILIER BUCATARII",
    "BUCATARII": "MOBILIER BUCATARII",
    "APARATURA": "MOBILIER BUCATARII",
    "ELECTROCASNICE": "MOBILIER BUCATARII",
    "BLATURI COMPOZIT": "MOBILIER BUCATARII",
    "MOBILIER TERASA SI GRADINA, INDOOR, ACCESORII": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GRADINA": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GARADINA": "MOBILIER TERASA SI GRADINA",
    "MOBILIER TERASA SI GARDINA": "MOBILIER TERASA SI GRADINA",
    "MOBILIER GRADINA - OUTDOOR": "MOBILIER TERASA SI GRADINA",
    "MOBILIER OUTDOOR": "MOBILIER TERASA SI GRADINA",
    "OUTDOOR": "MOBILIER TERASA SI GRADINA",
    "AMBALAJE": "ALTELE",
    "SEMIFABRICATE": "ALTELE",
    "PROTOTIPURI": "ALTELE",
    "COMENZI SPECIALE": "ALTELE",
    "LICITATII": "ALTELE",
    "BF 2022 PROMOTII": "ALTELE",
}

FAMILY_CANONICAL_MAP = {
    "CANAPELE  SI FOTOLII": "CANAPELE SI FOTOLII",
    "CANAPEE SI FOTOLII": "CANAPELE SI FOTOLII",
    "MOBILIER GRADINA - OUTDOOR": "MOBILIER OUTDOOR",
    "MOBILIER DE CASA - BUCATARII": "BUCATARII",
    "MOBILIER DE CASA-BUCATARII": "BUCATARII",
    "MOBILIER DE CASA -BUCATARII": "BUCATARII",
    "MOBILIER DE CASA - ACCESORII": "ACCESORII",
    "MOBILIER INTERIOR - DECO & ACCESORII": "DECO & ACCESORII",
    "MOBILIER BAIE SI SANITRE": "MOBILIER BAIE SI SANITARE",
    "SANITARE BAIE": "SANITARE",
}

KEYWORD_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PATURI TAPITATE", ("PATURI TAPITATE", "PAT TAPITAT")),
    ("MOBILIER OFFICE", ("MOBILIER OFFICE", "MOBILER OFFICE", "OFFICE", "BIROU", "BIROURI", "SCAUNE BIROU", "OPERATIONAL", "MANAGERIAL", "VIZITATOR", "SALI CONSILIU", "ZONA ASTEPTARE", "GESTIUNEA CABLURILOR")),
    ("MOBILIER BUCATARII", ("BUCATAR", "APARATURA", "ELECTROCASNICE", "BLATURI COMPOZIT")),
    ("MOBILIER BAIE SI SANITARE", ("BAIE", "SANITARE")),
    ("MOBILIER TERASA SI GRADINA", ("TERASA", "GRADINA", "OUTDOOR", "RATAN")),
    ("SALTELE SI SOMIERE", ("SALTEA", "SALTELE", "SOMIER", "SERTA", "SEALY", "GENETICS", "CULTURA SOMNULUI", "PATSPRING")),
    ("CANAPELE SI FOTOLII", ("CANAPE", "FOTOLI", "RECLINER", "SOFTMEX", "COLTAR")),
    ("ACCESORII", ("DECORATIUNI", "DECOR", "DECO", "ACCESORII", "CORPURI DE ILUMINAT", "ILUMINAT", "COVOR", "COVOARE", "TEXTILE", "TABLETOP", "GOURMET", "GREEN", "CHRISTMAS", "TAPET", "ODORIZANTE", "PERDELE", "DRAPERII", "VAZE")),
    ("MOBILIER DE CASA", ("MOBILIER CASA", "MOBILIER DE CASA", "MOBILIER CORP", "CAMERE COPII", "TINERET", "COPII", "DORMITOARE", "SUFRAGERII", "BIBLIOTECI", "MIC MOBILIER", "MESE SI SCAUNE", "DEPOZITARE", "LIVING", "HOLURI", "DRESSING", "HORECA", "CASUTA", "SCOLI SI GRADINITE")),
    ("ALTELE", ("AMBALAJE", "SEMIFABRICATE", "PROTOTIPURI", "COMENZI SPECIALE", "LICITATII")),
)


def _map_category(value: object) -> str | None:
    if not _is_meaningful(value):
        return None
    cleaned = _strip_numeric_code(str(value))
    cleaned = re.sub(r"^TOTAL\s+", "", cleaned)
    if cleaned in EXACT_CATEGORY_MAP:
        return EXACT_CATEGORY_MAP[cleaned]
    for category, keywords in KEYWORD_RULES:
        if any(keyword in cleaned for keyword in keywords):
            return category
    return None


def normalize_hierarchy(
    category_raw: object = None,
    class_raw: object = None,
    subclass_raw: object = None,
    group_raw: object = None,
    raion_raw: object = None,
    product_name: object = None,
) -> HierarchyResult:
    """Normalize hierarchy using all available v2 metadata.

    Category/class/subclass/group/raion are observed fields. Product-name
    classification is an inferred fallback because it parses unstructured text.
    """
    observed_fields = (
        ("category_raw", category_raw),
        ("class_raw", class_raw),
        ("subclass_raw", subclass_raw),
        ("group_raw", group_raw),
        ("raion_raw", raion_raw if clean_key(raion_raw) not in CHANNEL_ONLY_VALUES else None),
    )

    category_norm = UNKNOWN
    category_source = "unknown"
    category_signal_status = "unknown"
    for source, value in observed_fields:
        category = _map_category(value)
        if category:
            category_norm = category
            category_source = source
            category_signal_status = "observed"
            break

    if category_norm == UNKNOWN:
        inferred = _map_category(product_name)
        if inferred:
            category_norm = inferred
            category_source = "product_name"
            category_signal_status = "inferred"

    product_family = None
    product_family_source = "unknown"
    product_family_signal_status = "unknown"
    for source, value in (
        ("group_raw", group_raw),
        ("subclass_raw", subclass_raw),
        ("class_raw", class_raw),
        ("category_raw", category_raw),
        ("raion_raw", raion_raw if clean_key(raion_raw) not in CHANNEL_ONLY_VALUES else None),
    ):
        family = _family_from_value(value)
        if family:
            product_family = family
            product_family_source = source
            product_family_signal_status = "observed"
            break

    if product_family is None:
        product_family = category_norm
        product_family_source = category_source
        product_family_signal_status = category_signal_status

    return HierarchyResult(
        category_norm=category_norm,
        category_source=category_source,
        category_signal_status=category_signal_status,
        product_family_v2=product_family or UNKNOWN,
        product_family_source=product_family_source,
        product_family_signal_status=product_family_signal_status,
    )

