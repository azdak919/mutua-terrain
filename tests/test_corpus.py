from datetime import date

from mutua_terrain.corpus import build_corpus, flux
from mutua_terrain.normalize import date_parts, infer_date


def test_formats_de_date():
    assert date_parts("1925-05-02 00:00:00.0")["date"].isoformat() == "1925-05-02"
    assert date_parts("5/2/25 00:00") == {"yy": 25, "mois": 5, "jour": 2, "complete": False}
    assert date_parts("25-05-02")["yy"] == 25
    assert infer_date(date_parts("83-08-13"), date(2025, 11, 19)) == "1983-08-13"
    assert infer_date(date_parts("00-02-29"), date(2021, 12, 1)) == "2000-02-29"


def test_citadelle_et_sollio_reprennent_le_siecle():
    corpus = build_corpus()
    by_name = {coop["nom"]: coop for coop in corpus["coops"]}
    citadelle = by_name["CITADELLE, COOPÉRATIVE DE PRODUCTEURS DE SIROP D'ÉRABLE"]
    assert citadelle["date_constitution"] == "1925-05-02"
    assert citadelle["date_confiance"] == "ancree"
    assert citadelle["date_source"] == "2021-12"
    assert any(obs["date_brute"].startswith("25-05-02") for obs in citadelle["historique"])

    sollio = by_name["SOLLIO GROUPE COOPÉRATIF"]
    assert sollio["date_constitution"] == "1922-12-22"
    assert sollio["date_confiance"] == "ancree"

    acef = by_name["ASSOCIATION COOPÉRATIVE D'ÉCONOMIE FAMILIALE DE L'EST DE MONTRÉAL"]
    assert acef["date_constitution"] == "1983-08-13"


def test_flux_aout_2024_novembre_2025():
    corpus = build_corpus()
    moved = flux(corpus, "2024-08", "2025-11")
    assert len(moved["entrees"]) == 85
    assert len(moved["sorties"]) == 221
    assert len(moved["categories"]) == 6
    assert corpus["extraits"][-1]["n"] == 2558
    assert corpus["extraits"][0]["n"] == 2715
