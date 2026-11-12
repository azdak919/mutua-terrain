"""Normalise le CSV du MEIE (coopératives non financières actives).

Le fichier publie des dates sur deux chiffres et deux colonnes dont le O/N
est une interdiction statutaire, pas un versement observé.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

CATEGORIES = {
    "0- Regroupements": "regroupements",
    "1- Consommateurs": "consommateurs",
    "2- Producteurs": "producteurs",
    "3- Travailleurs": "travailleurs",
    "4- Travailleurs actionnaire": "travailleurs_actionnaire",
    "5- Solidarité": "solidarite",
}

_REGION = re.compile(r"^(\d{2})\s+(.+)$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_YYMMDD = re.compile(r"^(\d{2})-(\d{2})-(\d{2})$")
_FULL_DT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_US = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})")


def parse_date_constitution(value: str, extrait: date) -> str | None:
    """Replace l'année sur deux chiffres dans le siècle de l'extrait.

    Pour un extrait de 2025 : 00–25 → 2000–2025, 26–99 → 1926–1999.
    Une coop constituée l'année suivante n'est pas encore dans cet extrait.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    iso = _ISO.fullmatch(raw)
    short = _YYMMDD.fullmatch(raw)
    if iso:
        year, month, day = (int(part) for part in iso.groups())
    elif short:
        yy, month, day = (int(part) for part in short.groups())
        pivot = extrait.year % 100
        year = 2000 + yy if yy <= pivot else 1900 + yy
    else:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def date_parts(value: str) -> dict | None:
    """Découpe une date MEIE, complète ou amputée de son siècle.

    Formats vus dans les extraits : ``1925-05-02 00:00:00.0``,
    ``5/2/25 00:00`` (Excel, mois/jour/année) et ``25-05-02``.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    head = raw.split()[0]
    full = _FULL_DT.match(head)
    if full:
        year, month, day = (int(part) for part in full.groups())
        try:
            return {"date": date(year, month, day), "complete": True}
        except ValueError:
            return None
    short = _YYMMDD.fullmatch(head)
    us = _US.match(head)
    if short:
        yy, month, day = (int(part) for part in short.groups())
    elif us:
        month, day, year_raw = (int(part) for part in us.groups())
        if year_raw >= 100:
            try:
                return {"date": date(year_raw, month, day), "complete": True}
            except ValueError:
                return None
        yy = year_raw
    else:
        return None
    return {"yy": yy, "mois": month, "jour": day, "complete": False}


def infer_date(parts: dict, first_seen: date) -> str | None:
    """Choisit un siècle seulement si l'autre est impossible.

    Sans année complète, 2000+AA l'emporte quand cette date n'est pas
    postérieure au premier extrait qui contient la coopérative.
    Citadelle et Sollio ne passent pas par ici : leur année complète
    est dans les extraits de 2021 et 2023.
    """
    if parts.get("complete"):
        return parts["date"].isoformat()
    options = []
    for year in (2000 + parts["yy"], 1900 + parts["yy"]):
        try:
            options.append(date(year, parts["mois"], parts["jour"]))
        except ValueError:
            continue
    possible = [item for item in options if item <= first_seen]
    recent = [item for item in possible if item.year >= 2000]
    if recent:
        return recent[0].isoformat()
    if possible:
        return possible[0].isoformat()
    return None


def interdit(value: str) -> bool | None:
    """O = les statuts interdisent le versement. N = ils ne l'interdisent pas.

    Le dictionnaire de 2019 décrit une clause statutaire. L'avis du MEIE de
    2026 lit N comme un versement réel. Terrain garde le sens statutaire.
    """
    raw = (value or "").strip().upper()
    if raw == "O":
        return True
    if raw == "N":
        return False
    return None


def membre_prevu(value: str) -> bool | None:
    """O = la coop de solidarité a prévu ce collège de membres dans son objet."""
    raw = (value or "").strip().upper()
    if raw == "O":
        return True
    if raw == "N":
        return False
    return None


def parse_region(value: str) -> dict[str, str]:
    raw = (value or "").strip()
    match = _REGION.match(raw)
    if not match:
        return {"code": "", "nom": raw}
    return {"code": match.group(1), "nom": match.group(2)}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def normalize_row(row: dict[str, str], extrait: date) -> dict:
    categorie_source = _clean(row.get("COOP_CATEGORIE"))
    categorie = CATEGORIES.get(categorie_source)
    solidarite = None
    if categorie == "solidarite":
        solidarite = {
            "producteur": membre_prevu(row.get("UTILPROD", "")),
            "consommateur": membre_prevu(row.get("UTILCONSO", "")),
            "travailleur": membre_prevu(row.get("TRAVAILLEURS", "")),
            "soutien": membre_prevu(row.get("SOUTIEN", "")),
        }
    region = parse_region(row.get("REGADMINP", ""))
    return {
        "nom": _clean(row.get("NOMLEGAL")),
        "dossier": _clean(row.get("NODOSSIER")),
        "neq": _clean(row.get("NEQ")),
        "date_constitution": parse_date_constitution(row.get("DATECONS", ""), extrait),
        "categorie": categorie,
        "categorie_source": categorie_source,
        "secteur": _clean(row.get("SECTEUR")),
        "interdit_interets": interdit(row.get("VERSE_INT", "")),
        "interdit_ristournes": interdit(row.get("AUCUNRIST", "")),
        "solidarite": solidarite,
        "objet": _clean(row.get("OBJET")),
        "loi": _clean(row.get("REGIEPAR")),
        "scian": _clean(row.get("SCIAN1")),
        "scian_no": _clean(row.get("SCIANNO")),
        "siege": {
            "adresse": _clean(row.get("ADRESSEP")),
            "adresse2": _clean(row.get("ADRESSEP2")),
            "ville": _clean(row.get("VILLEP")),
            "arrondissement": _clean(row.get("ARRONDISSEMENTP")),
            "mrc": _clean(row.get("MRCP")),
            "region_code": region["code"],
            "region": region["nom"],
            "circonscription": _clean(row.get("CIRCELECTP")),
            "code_postal": _clean(row.get("CODEPOSTALP")),
            "province": _clean(row.get("PROVINCEP")),
        },
    }


def read_rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def build_document(rows: list[dict[str, str]], extrait: date, source: dict) -> dict:
    coops = [normalize_row(row, extrait) for row in rows]
    coops.sort(key=lambda coop: (coop["nom"], coop["dossier"]))
    return {
        "source": source,
        "extrait": extrait.isoformat(),
        "n": len(coops),
        "coops": coops,
    }
