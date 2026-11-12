#!/usr/bin/env python3
"""Construit le territoire : fiches ISQ 2022 et polygones des 17 régions.

Les PDF et le GeoJSON brut restent hors dépôt. Ce script écrit les deux
fichiers dérivés que la page charge.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FICHES = Path("/tmp/isq-fiches")
GEO_RAW = Path("/tmp/regions-admin.geojson")
ISQ_OUT = ROOT / "data" / "economy" / "isq-regions.json"
GEO_OUT = ROOT / "data" / "geo" / "regions.geojson"
WEB_DATA = ROOT / "web" / "data"

NOMS = {
    "01": "Bas-Saint-Laurent",
    "02": "Saguenay–Lac-Saint-Jean",
    "03": "Capitale-Nationale",
    "04": "Mauricie",
    "05": "Estrie",
    "06": "Montréal",
    "07": "Outaouais",
    "08": "Abitibi-Témiscamingue",
    "09": "Côte-Nord",
    "10": "Nord-du-Québec",
    "11": "Gaspésie–Îles-de-la-Madeleine",
    "12": "Chaudière-Appalaches",
    "13": "Laval",
    "14": "Lanaudière",
    "15": "Laurentides",
    "16": "Montérégie",
    "17": "Centre-du-Québec",
}

FICHE_SLUG = {
    "bas-saint-laurent": ["01"],
    "saguenay-lac-saint-jean": ["02"],
    "capitale-nationale": ["03"],
    "mauricie": ["04"],
    "estrie": ["05"],
    "montreal": ["06"],
    "outaouais": ["07"],
    "abitibi-temiscamingue": ["08"],
    "cote-nord-nord-du-quebec": ["09", "10"],
    "gaspesie-iles-de-la-madeleine": ["11"],
    "chaudiere-appalaches": ["12"],
    "laval": ["13"],
    "lanaudiere": ["14"],
    "laurentides": ["15"],
    "monteregie": ["16"],
    "centre-du-quebec": ["17"],
}

GEO_URL = (
    "https://services2.arcgis.com/RkhyeW7cqOfSjlQG/ArcGIS/rest/services/"
    "R%C3%A9gions_du_Qu%C3%A9bec/FeatureServer/3/query"
)
# Un seul espace (ou espace insécable) sépare les milliers. Les colonnes
# du PDF sont séparées par une plage d'espaces : il ne faut pas les confondre.
TOKEN = re.compile(
    "(?<!\\w)(?P<conf>x|—)(?!\\w)"
    "|(?P<num>\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+|\\d+)(?:,(?P<dec>\\d+))?"
    "(?:\\s*(?P<unit>M\\$|G\\$|%))?"
    "(?:\\s*(?P<star>\\*{1,2}))?"
)
MILLION = Decimal(1_000_000)
MILLIARD = Decimal(1_000_000_000)


def _qualite(star: str | None, confidential: bool) -> str | None:
    if confidential:
        return "x"
    if star == "*":
        return "cv15"
    if star == "**":
        return "cv25"
    return None


def _valeurs(line: str) -> list[dict]:
    found = []
    for match in TOKEN.finditer(line):
        if match.group("conf"):
            found.append({"dollars": None, "valeur": None, "qualite": "x", "unite": None})
            continue
        if not match.group("num"):
            continue
        # Un étoile seule ne doit pas recoller sur le jeton précédent : le
        # groupe star est optionnel et consommé avec le nombre.
        raw = match.group("num").replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
        if match.group("dec"):
            raw = f"{raw}.{match.group('dec')}"
        number = Decimal(raw)
        unit = match.group("unit")
        star = match.group("star")
        dollars = None
        valeur = None
        if unit == "M$":
            dollars = int((number * MILLION).to_integral_value(ROUND_HALF_UP))
        elif unit == "G$":
            dollars = int((number * MILLIARD).to_integral_value(ROUND_HALF_UP))
        elif unit == "%":
            valeur = float(number)
        else:
            valeur = int(number)
        found.append(
            {
                "dollars": dollars,
                "valeur": valeur,
                "qualite": _qualite(star, False),
                "unite": unit,
            }
        )
    return found


def _ligne(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        plat = re.sub(r"\s+", " ", line).strip()
        if plat.lower().startswith(prefix.lower()):
            return line
    return None


def _corps(line: str, prefix: str) -> str:
    """Retire le libellé et son appel de note (un chiffre collé, puis la colonne)."""
    at = line.lower().find(prefix.lower())
    if at < 0:
        raise ValueError(prefix)
    rest = line[at + len(prefix) :]
    return re.sub(r"^\d{1,2}(?=\s{2,})", "", rest, count=1)


def _apres(text: str, label: str) -> str | None:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.startswith(label):
            for follow in lines[index + 1 :]:
                if follow:
                    return follow
    return None


def _nombre(valeur: dict, attendu: str) -> dict:
    if valeur["qualite"] == "x":
        return {"valeur": None, "qualite": "x"}
    if valeur["unite"] not in (None, attendu):
        raise ValueError(f"unité {valeur['unite']} au lieu de {attendu}")
    return {"valeur": valeur["valeur"], "qualite": valeur["qualite"]}


def _argent(valeur: dict) -> dict:
    if valeur["qualite"] == "x":
        return {"dollars": None, "qualite": "x"}
    if valeur["unite"] not in ("M$", "G$"):
        raise ValueError(f"montant sans unité : {valeur}")
    return {"dollars": valeur["dollars"], "qualite": valeur["qualite"]}


def _quatre(line: str, caster) -> dict:
    valeurs = _valeurs(line)
    if len(valeurs) != 4:
        raise ValueError(f"{len(valeurs)} colonnes dans {line}")
    obnl, coops, ensemble, quebec = valeurs
    return {
        "obnl": caster(obnl),
        "cooperatives_et_mutuelles": caster(coops),
        "ensemble": caster(ensemble),
        "quebec": caster(quebec),
    }


def parse_fiche(path: Path, codes: list[str]) -> dict:
    full = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
    full = full.replace("’", "'")
    cut = full.split("\nÉvolution\n", 1)[0]
    nom = _apres(cut, "L'économie sociale")
    if not nom or nom == "en 2022":
        raise ValueError(f"nom illisible dans {path.name}")
    population = _apres(cut, "Population de la région")
    if not population or not population[0].isdigit():
        raise ValueError(f"population illisible dans {path.name}")

    def deux(prefix: str) -> list[dict]:
        line = _ligne(cut, prefix)
        if line is None:
            raise ValueError(f"{prefix} absent de {path.name}")
        valeurs = _valeurs(_corps(line, prefix))
        if len(valeurs) != 2:
            raise ValueError(f"{prefix} : {len(valeurs)} valeurs dans {line.strip()}")
        return valeurs

    entreprises, entreprises_qc = deux("Nombre approximatif d'entreprises d'économie sociale")
    obnl, obnl_qc = deux("OBNL")
    cnf, cnf_qc = deux("Coopératives non financières")
    fm, fm_qc = deux("Coopératives financières et mutuelles")
    membres, membres_qc = deux("Nombre approximatif de membres")
    salaries, salaries_qc = deux("Nombre approximatif de personnes salariées")
    remuneration, remuneration_qc = deux("Dépenses en matière de rémunération")

    slug = path.stem
    return {
        "codes": codes,
        "nom": nom,
        "nom_fiche": nom,
        "slug": slug,
        "fiche": f"https://statistique.quebec.ca/fr/fichier/economie-sociale-2022-{slug}.pdf",
        "population": int(population.replace(" ", "").replace("\u00a0", "")),
        "entreprises": _nombre(entreprises, ""),
        "obnl": _nombre(obnl, ""),
        "cooperatives_non_financieres": _nombre(cnf, ""),
        "cooperatives_financieres_et_mutuelles": _nombre(fm, ""),
        "membres": _nombre(membres, ""),
        "salaries": _nombre(salaries, ""),
        "remuneration": _argent(remuneration),
        "revenus": _quatre(_corps(_ligne(cut, "Revenus"), "Revenus"), _argent),
        "part_chiffre_affaires": _quatre(
            _corps(_ligne(cut, "Part du chiffre d'affaires"), "Part du chiffre d'affaires"),
            lambda v: _nombre(v, "%"),
        ),
        "part_subventions": _quatre(
            _corps(_ligne(cut, "Part des subventions"), "Part des subventions"),
            lambda v: _nombre(v, "%"),
        ),
        "actifs": _quatre(_corps(_ligne(cut, "Actifs"), "Actifs"), _argent),
        "proprietes": _quatre(
            _corps(_ligne(cut, "Valeur des propriétés"), "Valeur des propriétés"),
            _argent,
        ),
        "quebec_controle": {
            "entreprises": entreprises_qc["valeur"],
            "obnl": obnl_qc["valeur"],
            "cooperatives_non_financieres": cnf_qc["valeur"],
            "cooperatives_financieres_et_mutuelles": fm_qc["valeur"],
            "membres": membres_qc["valeur"],
            "salaries": salaries_qc["valeur"],
            "remuneration": _argent(remuneration_qc),
        },
    }


def build_isq() -> dict:
    regions = []
    for slug, codes in FICHE_SLUG.items():
        regions.append(parse_fiche(FICHES / f"{slug}.pdf", codes))
    regions.sort(key=lambda region: region["codes"][0])
    controle = regions[0]["quebec_controle"]
    for region in regions[1:]:
        if region["quebec_controle"]["entreprises"] != controle["entreprises"]:
            raise ValueError(f"total Québec divergent dans {region['slug']}")
    for region in regions:
        region.pop("quebec_controle")
        if region["codes"] == ["09", "10"]:
            region["nom"] = "Côte-Nord et Nord-du-Québec"
        else:
            region["nom"] = NOMS[region["codes"][0]]
    return {
        "producteur": "Institut de la statistique du Québec",
        "enquete": "Enquête auprès des organismes à but non lucratif, des coopératives et des mutuelles 2023",
        "annee_reference": 2022,
        "publication": "2025-07-11",
        "page": "https://statistique.quebec.ca/fr/document/leconomie-sociale-au-quebec-portrait-statistique",
        "recueil": "https://statistique.quebec.ca/fr/fichier/economie-sociale-au-quebec-recueil-statistique-2022.xlsx",
        "perimetre": (
            "Toutes les coopératives et toutes les mutuelles, plus les organismes "
            "à but non lucratif qui vendent des biens ou des services et qui "
            "répondent aux six principes de la Loi sur l'économie sociale. "
            "L'action communautaire autonome, enquêtée à part, n'est pas dans ce périmètre."
        ),
        "lecture": [
            "Les effectifs régionaux sont les estimations arrondies des fiches. Leur somme ne redonne pas exactement le total du Québec.",
            "Côte-Nord et Nord-du-Québec sont une seule estimation. Il ne faut pas la compter deux fois.",
            "Les mutuelles ne sont pas séparées des coopératives financières dans les fiches régionales.",
            "Les revenus et les actifs des « coopératives et mutuelles » comprennent les coopératives financières.",
            "Le registre du MEIE et l'enquête de l'ISQ ne se additionnent pas : années, périmètres et méthodes diffèrent.",
        ],
        "quebec": {
            "entreprises": 11360,
            "obnl": 8710,
            "cooperatives_non_financieres": 2420,
            "cooperatives_financieres": 210,
            "mutuelles": 30,
            "cooperatives_financieres_et_mutuelles": 240,
            "membres": controle["membres"],
            "salaries": controle["salaries"],
            "remuneration": controle["remuneration"],
            "revenus": {"dollars": 53_600_000_000, "qualite": None},
            "part_chiffre_affaires": 88.6,
            "part_subventions": 8.5,
            "actifs": {"dollars": 439_500_000_000, "qualite": None},
            "proprietes": {"dollars": 16_000_000_000, "qualite": None},
        },
        "regions": regions,
    }


def _download_geo() -> None:
    if GEO_RAW.exists() and GEO_RAW.stat().st_size > 1_000_000:
        return
    params = urllib.parse.urlencode(
        {
            "where": "1=1",
            "outFields": "RES_CO_REG,RES_NM_REG",
            "returnGeometry": "true",
            "f": "geojson",
            "outSR": "4326",
            "geometryPrecision": "4",
            "maxAllowableOffset": "0.012",
        }
    )
    urllib.request.urlretrieve(f"{GEO_URL}?{params}", GEO_RAW)


def _perp(point, start, end) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5


def _simplify(points: list, epsilon: float) -> list:
    if len(points) <= 6:
        return points
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        left, right = stack.pop()
        start, end = points[left], points[right]
        farthest = 0.0
        index = None
        for cursor in range(left + 1, right):
            distance = _perp(points[cursor], start, end)
            if distance > farthest:
                farthest = distance
                index = cursor
        if index is not None and farthest > epsilon:
            keep.add(index)
            stack.append((left, index))
            stack.append((index, right))
    simplified = [points[index] for index in sorted(keep)]
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return simplified


def _ring(ring: list) -> list:
    cleaned = [[round(point[0], 4), round(point[1], 4)] for point in ring]
    if len(cleaned) > 80:
        cleaned = _simplify(cleaned, 0.01)
    if cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    return cleaned


def build_geo() -> dict:
    _download_geo()
    raw = json.loads(GEO_RAW.read_text(encoding="utf-8"))
    by_code: dict[str, list] = {}
    for feature in raw["features"]:
        code = str(feature["properties"].get("RES_CO_REG") or "").zfill(2)
        if code not in NOMS:
            raise ValueError(f"code inattendu {code}")
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        by_code.setdefault(code, []).extend(polygons)
    features = []
    for code in sorted(NOMS):
        polygons = [[_ring(ring) for ring in polygon] for polygon in by_code[code]]
        features.append(
            {
                "type": "Feature",
                "properties": {"code": code, "nom": NOMS[code]},
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )
    return {
        "type": "FeatureCollection",
        "nom": "Régions administratives du Québec",
        "source": (
            "Couche Administratives du service public « Régions du Québec » "
            "(référence SDA20K, version V2022-02), généralisée et passée en WGS84."
        ),
        "url": GEO_URL,
        "features": features,
    }


def publish(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    web = WEB_DATA / path.name
    web.parent.mkdir(parents=True, exist_ok=True)
    web.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"{path} ({path.stat().st_size} o) → {web}")


def main() -> None:
    isq = build_isq()
    publish(isq, ISQ_OUT)
    geo = build_geo()
    publish(geo, GEO_OUT)
    print(f"{len(isq['regions'])} fiches, {len(geo['features'])} régions")


if __name__ == "__main__":
    main()
