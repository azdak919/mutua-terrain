"""Contrat de l'extrait épinglé du 19 novembre 2025.

Les totaux bougent quand on remplace le CSV. Les changer est une décision,
pas un effet de bord du normaliseur.
"""

from datetime import date
from pathlib import Path

from mutua_terrain.normalize import build_document, read_rows

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "source" / "coop-non-financieres-actives_20251119.v4.csv"
EXTRAIT = date(2025, 11, 19)


def _document():
    text = CSV.read_text(encoding="utf-8")
    return build_document(read_rows(text), EXTRAIT, {"organisme": "MEIE"})


def test_extrait_20251119():
    document = _document()
    coops = document["coops"]
    assert document["n"] == 2558
    assert len({coop["dossier"] for coop in coops}) == 2558
    assert len({coop["neq"] for coop in coops}) == 2558

    comptes: dict[str, int] = {}
    for coop in coops:
        comptes[coop["categorie"]] = comptes.get(coop["categorie"], 0) + 1
        assert coop["categorie"] is not None
        assert coop["interdit_interets"] in (True, False)
        assert coop["interdit_ristournes"] in (True, False)
        if coop["categorie"] == "solidarite":
            assert set(coop["solidarite"]) == {
                "producteur",
                "consommateur",
                "travailleur",
                "soutien",
            }
        else:
            assert coop["solidarite"] is None
        if coop["date_constitution"] is not None:
            assert coop["date_constitution"][4] == "-"

    assert comptes == {
        "consommateurs": 1468,
        "solidarite": 542,
        "travailleurs": 264,
        "producteurs": 232,
        "travailleurs_actionnaire": 32,
        "regroupements": 20,
    }
    assert sum(1 for coop in coops if coop["secteur"] == "Habitation") == 1288
    assert sum(1 for coop in coops if coop["objet"] == "") == 1135

    acef = next(
        coop
        for coop in coops
        if coop["nom"] == "ASSOCIATION COOPÉRATIVE D'ÉCONOMIE FAMILIALE DE L'EST DE MONTRÉAL"
    )
    assert acef["date_constitution"] == "1983-08-13"
    assert acef["interdit_interets"] is False
    assert acef["interdit_ristournes"] is False
    assert acef["siege"]["region"] == "Montréal"

    citadelle = next(
        coop
        for coop in coops
        if coop["nom"] == "CITADELLE, COOPÉRATIVE DE PRODUCTEURS DE SIROP D'ÉRABLE"
    )
    assert citadelle["date_constitution"] == "2025-05-02"
    assert citadelle["categorie"] == "producteurs"
    assert "titre II" in citadelle["loi"]
