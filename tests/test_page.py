from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_la_page_dit_les_limites():
    page = " ".join((ROOT / "web" / "index.html").read_text(encoding="utf-8").split())
    assert "pas un avis juridique" in page
    assert "statuts ne les interdisent pas" in page
    assert "CC-BY 4.0" in page
    assert "19 novembre 2025" in page
    assert "Données Québec" in page
    script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "Les statuts interdisent les" in script
    assert "Les statuts n’interdisent pas les" in script
