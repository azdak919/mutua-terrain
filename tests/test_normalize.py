from datetime import date
from pathlib import Path

from mutua_terrain.normalize import (
    build_document,
    interdit,
    parse_date_constitution,
    read_rows,
)

EXTRAIT = date(2025, 11, 19)
FIXTURE = Path(__file__).parent / "fixtures" / "mini.csv"
SOURCE = {"organisme": "test"}


def test_siecle_selon_lextrait():
    assert parse_date_constitution("83-08-13", EXTRAIT) == "1983-08-13"
    assert parse_date_constitution("00-01-01", EXTRAIT) == "2000-01-01"
    assert parse_date_constitution("25-05-02", EXTRAIT) == "2025-05-02"
    assert parse_date_constitution("26-01-01", EXTRAIT) == "1926-01-01"
    assert parse_date_constitution("99-13-40", EXTRAIT) is None
    assert parse_date_constitution("", EXTRAIT) is None
    # L'année charnière suit l'extrait, pas la date du jour.
    assert parse_date_constitution("26-06-01", date(2026, 6, 1)) == "2026-06-01"


def test_o_veut_dire_interdiction_pas_versement():
    assert interdit("O") is True
    assert interdit("N") is False
    assert interdit("") is None
    assert interdit("oui") is None


def test_fixture_separe_solidarite_et_statuts():
    document = build_document(read_rows(FIXTURE.read_text(encoding="utf-8")), EXTRAIT, SOURCE)
    by_dossier = {coop["dossier"]: coop for coop in document["coops"]}

    travail = by_dossier["1001"]
    assert travail["categorie"] == "travailleurs"
    assert travail["date_constitution"] == "1983-08-13"
    assert travail["interdit_interets"] is True
    assert travail["interdit_ristournes"] is False
    assert travail["solidarite"] is None
    assert travail["siege"]["region_code"] == "11"
    assert travail["siege"]["region"] == "Gaspésie–Îles-de-la-Madeleine"

    solidarite = by_dossier["1002"]
    assert solidarite["solidarite"] == {
        "producteur": True,
        "consommateur": False,
        "travailleur": True,
        "soutien": True,
    }
    assert solidarite["interdit_ristournes"] is True
    assert solidarite["interdit_interets"] is False

    habitation = by_dossier["1003"]
    assert habitation["objet"] == ""
    assert habitation["categorie"] == "consommateurs"
    assert habitation["solidarite"] is None

    illisible = by_dossier["1004"]
    assert illisible["date_constitution"] is None
    assert illisible["loi"] == "Loi sur les COOP titre II"
