"""Corpus longitudinal des quatre extraits MEIE, dates corrigées."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from mutua_terrain.normalize import (
    CATEGORIES,
    date_parts,
    infer_date,
    interdit,
    membre_prevu,
    parse_region,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "source"
ECONOMY = ROOT / "data" / "economy" / "contexte-scian.json"

EXTRACTS = (
    {
        "id": "2021-12",
        "date": "2021-12-01",
        "fichier": "20211201.csv",
        "libelle": "Décembre 2021",
    },
    {
        "id": "2023-04",
        "date": "2023-04-25",
        "fichier": "20230425.csv",
        "libelle": "Avril 2023",
    },
    {
        "id": "2024-08",
        "date": "2024-08-15",
        "fichier": "20240815.csv",
        "libelle": "Août 2024",
    },
    {
        "id": "2025-11",
        "date": "2025-11-19",
        "fichier": "coop-non-financieres-actives_20251119.v4.csv",
        "libelle": "Novembre 2025",
    },
)


def canon(row: dict[str, str]) -> dict[str, str]:
    return {key.upper().replace("_", ""): (value or "").strip() for key, value in row.items()}


def read_extract(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [canon(row) for row in csv.DictReader(handle)]


def _observation(row: dict[str, str], extract_id: str) -> dict:
    categorie = CATEGORIES.get(row.get("COOPCATEGORIE", ""))
    region = parse_region(row.get("REGADMINP", ""))
    solidarite = None
    if categorie == "solidarite":
        solidarite = {
            "producteur": membre_prevu(row.get("UTILPROD", "")),
            "consommateur": membre_prevu(row.get("UTILCONSO", "")),
            "travailleur": membre_prevu(row.get("TRAVAILLEURS", "")),
            "soutien": membre_prevu(row.get("SOUTIEN", "")),
        }
    return {
        "ex": extract_id,
        "nom": row.get("NOMLEGAL", ""),
        "cat": categorie,
        "secteur": row.get("SECTEUR", ""),
        "ville": row.get("VILLEP", ""),
        "region": region["nom"],
        "region_code": region["code"],
        "cp": row.get("CODEPOSTALP", ""),
        "adresse": row.get("ADRESSEP", ""),
        "loi": row.get("REGIEPAR", ""),
        "scian": row.get("SCIAN1", ""),
        "scian_no": row.get("SCIANNO", ""),
        "objet": row.get("OBJET", ""),
        "interdit_interets": interdit(row.get("VERSEINT", "")),
        "interdit_ristournes": interdit(row.get("AUCUNRIST", "")),
        "solidarite": solidarite,
        "date_brute": row.get("DATECONS", ""),
    }


def _resolve_date(rows_by_extract: list[tuple[dict, dict[str, str]]]) -> dict:
    first_seen = date.fromisoformat(rows_by_extract[0][0]["date"])
    anchor = None
    anchor_id = ""
    for meta, row in rows_by_extract:
        parts = date_parts(row.get("DATECONS", ""))
        if parts and parts.get("complete"):
            anchor = parts["date"]
            anchor_id = meta["id"]
            break
    if anchor is not None:
        return {
            "date_constitution": anchor.isoformat(),
            "date_confiance": "ancree",
            "date_source": anchor_id,
        }
    for meta, row in reversed(rows_by_extract):
        parts = date_parts(row.get("DATECONS", ""))
        if not parts:
            continue
        inferred = infer_date(parts, first_seen)
        if inferred:
            return {
                "date_constitution": inferred,
                "date_confiance": "inferee",
                "date_source": meta["id"],
            }
    return {"date_constitution": None, "date_confiance": "illisible", "date_source": ""}


def build_corpus(source: Path = SOURCE, economy_path: Path = ECONOMY) -> dict:
    loaded = []
    for meta in EXTRACTS:
        rows = read_extract(source / meta["fichier"])
        loaded.append((meta, rows))

    by_neq: dict[str, list[tuple[dict, dict[str, str]]]] = {}
    order: list[str] = []
    for meta, rows in loaded:
        for row in rows:
            neq = row.get("NEQ", "")
            if neq not in by_neq:
                by_neq[neq] = []
                order.append(neq)
            by_neq[neq].append((meta, row))

    coops = []
    for neq in order:
        series = by_neq[neq]
        resolved = _resolve_date(series)
        historique = [_observation(row, meta["id"]) for meta, row in series]
        latest = historique[-1]
        coops.append(
            {
                "neq": neq,
                "dossier": series[-1][1].get("NODOSSIER", ""),
                **resolved,
                "nom": latest["nom"],
                "cat": latest["cat"],
                "secteur": latest["secteur"],
                "ville": latest["ville"],
                "region": latest["region"],
                "region_code": latest["region_code"],
                "scian_no": latest["scian_no"],
                "historique": historique,
            }
        )
    coops.sort(key=lambda coop: (coop["nom"], coop["neq"]))

    counts = []
    for meta, rows in loaded:
        counts.append({"id": meta["id"], "n": len(rows)})

    economy = json.loads(economy_path.read_text(encoding="utf-8"))
    return {
        "producteur": "Ministère de l'Économie, de l'Innovation et de l'Énergie",
        "licence": "CC-BY 4.0",
        "page": "https://www.donneesquebec.ca/recherche/dataset/donnees-administratives-des-cooperatives-non-financieres",
        "extraits": [
            {
                "id": meta["id"],
                "date": meta["date"],
                "libelle": meta["libelle"],
                "fichier": meta["fichier"],
                "n": count["n"],
            }
            for (meta, _), count in zip(loaded, counts)
        ],
        "economie": economy,
        "coops": coops,
    }


def flux(corpus: dict, left: str, right: str) -> dict:
    def present(extract_id: str) -> dict[str, dict]:
        found = {}
        for coop in corpus["coops"]:
            for obs in coop["historique"]:
                if obs["ex"] == extract_id:
                    found[coop["neq"]] = obs
        return found

    a = present(left)
    b = present(right)
    entrees = sorted(set(b) - set(a))
    sorties = sorted(set(a) - set(b))
    communs = set(a) & set(b)
    renoms = sorted(neq for neq in communs if a[neq]["nom"] != b[neq]["nom"])
    categories = sorted(neq for neq in communs if a[neq]["cat"] != b[neq]["cat"])
    return {
        "entrees": entrees,
        "sorties": sorties,
        "renoms": renoms,
        "categories": categories,
    }
