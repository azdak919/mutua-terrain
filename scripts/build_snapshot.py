#!/usr/bin/env python3
"""Écrit le corpus longitudinal (web/data/corpus.json)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mutua_terrain.corpus import build_corpus  # noqa: E402


def main() -> None:
    document = build_corpus()
    out = ROOT / "web" / "data" / "corpus.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(document['coops'])} coopératives, {len(document['extraits'])} extraits → {out}")
    copies = {
        ROOT / "data" / "economy" / "isq-regions.json": out.parent / "isq-regions.json",
        ROOT / "data" / "geo" / "regions.geojson": out.parent / "regions.geojson",
    }
    for source, dest in copies.items():
        if source.exists():
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"territoire → {dest}")


if __name__ == "__main__":
    main()
