import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _isq():
    return json.loads((ROOT / "data" / "economy" / "isq-regions.json").read_text(encoding="utf-8"))


def test_lenquete_garde_les_mutuelles_hors_du_communautaire():
    data = _isq()
    assert "action communautaire" in data["perimetre"]
    quebec = data["quebec"]
    assert quebec["entreprises"] == 11360
    assert quebec["obnl"] == 8710
    assert quebec["cooperatives_non_financieres"] == 2420
    assert quebec["cooperatives_financieres"] == 210
    assert quebec["mutuelles"] == 30
    assert len(data["regions"]) == 16
    codes = []
    for region in data["regions"]:
        assert "mutuelles" not in region
        codes.extend(region["codes"])
    assert codes == [f"{index:02d}" for index in range(1, 18)]
    assert sum(region["entreprises"]["valeur"] for region in data["regions"]) == 11360


def test_les_fiches_publiant_la_part_des_subventions():
    regions = _isq()["regions"]
    montreal = next(region for region in regions if region["codes"] == ["06"])
    assert montreal["entreprises"]["valeur"] == 3120
    assert montreal["cooperatives_non_financieres"]["valeur"] == 710
    assert montreal["revenus"]["obnl"]["qualite"] == "x"
    centre = next(region for region in regions if region["codes"] == ["17"])
    assert centre["part_chiffre_affaires"]["cooperatives_et_mutuelles"]["valeur"] == 99.4
    assert centre["part_subventions"]["obnl"]["valeur"] == 50.6
    assert centre["part_subventions"]["cooperatives_et_mutuelles"] == {"valeur": 0.2, "qualite": "cv15"}
    estrie = next(region for region in regions if region["codes"] == ["05"])
    assert estrie["part_subventions"]["obnl"]["valeur"] == 51.9
    assert estrie["part_subventions"]["cooperatives_et_mutuelles"]["valeur"] == 1.9
    joint = next(region for region in regions if region["codes"] == ["09", "10"])
    assert joint["entreprises"]["valeur"] == 360
    chaudiere = next(region for region in regions if region["codes"] == ["12"])
    assert chaudiere["revenus"]["cooperatives_et_mutuelles"]["qualite"] == "cv25"


def test_les_dix_sept_contours():
    geo = json.loads((ROOT / "data" / "geo" / "regions.geojson").read_text(encoding="utf-8"))
    assert [feature["properties"]["code"] for feature in geo["features"]] == [
        f"{index:02d}" for index in range(1, 18)
    ]
    cote_nord = next(feature for feature in geo["features"] if feature["properties"]["code"] == "09")
    assert cote_nord["geometry"]["type"] == "MultiPolygon"
    assert len(cote_nord["geometry"]["coordinates"]) >= 2
    assert "SDA20K" in geo["source"]


def test_le_registre_garde_les_regions_vides():
    path = ROOT / "data" / "source" / "coop-non-financieres-actives_20251119.v4.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    vides = [row for row in rows if not (row.get("REGADMINP") or "").strip()]
    assert len(rows) == 2558
    assert len(vides) == 17


def test_la_page_annonce_la_carte():
    page = " ".join((ROOT / "web" / "index.html").read_text(encoding="utf-8").split())
    assert "régions administratives" in page
    assert "action communautaire" in page
    assert "mutuelles" in page
    assert "Institut de la statistique" in page
    assert "Côte-Nord et Nord-du-Québec" in page
    assert "ne l’additionne pas" in page or "On ne l’additionne pas" in page
