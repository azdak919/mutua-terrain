# AGENTS.md — mutua-terrain

> Instructions pour agents IA (Grok, Claude, Cursor, Codex, etc.).

## ⛔ RÈGLE DURE — branche + tests avant `main`

**Source de vérité multi-outils :**
[`../../GIT-AND-TEST-SAFETY.md`](../../GIT-AND-TEST-SAFETY.md)

**Interdit** : commit/push non testé sur `main`.

**Obligatoire** :

1. Baseline locale sur `main` **avant** de créer la branche (repro / smoke).
2. Branche `fix|feat|chore/...` → **vérif locale** verte → push → **PR**.
3. **Lien PR cliquable** dans la réponse (l’humain regarde, puis dit **merge and delete**).
4. Merger **seulement** sur cet ordre, après checks CI verts + `--delete-branch`.

**Push ≠ livré.** Ne pas merger sans ordre humain.

## Quality Gate

- Workflow : `.github/workflows/verification.yml` nommé **Vérification** (job **`test`**).
- Local avant push : `pytest` (Python 3.11+, `pip install pytest`).
- UI : ouvrir `web/` via `python -m http.server -d web 8765` après `python scripts/build_snapshot.py`. Playwright pas encore branché. Ne pas déclarer l’interface livrée sans l’avoir ouverte.

## Carte / contexte projet

Side project de Mutua, **dépôt à part** : <https://github.com/azdak919/mutua-terrain>.

Lecture seule du CSV MEIE des coopératives non financières actives.
Le hub Mutua (droit, statuts, Studio) ne se branche pas ici sans une demande séparée.

Ne pas casser :

- `O` sur `VERSE_INT` / `AUCUNRIST` = interdiction statutaire, jamais « verse ».
- La date retenue vient de l’année complète (extraits 2021 et 2023) quand elle existe. Citadelle = 1925-05-02, Sollio = 1922-12-22. Ne pas réafficher le siècle inféré du fichier 2025 pour ces deux-là.
- Le contexte StatCan décrit le secteur, pas la coopérative.
- Le bloc `solidarite` n’existe que pour la catégorie solidarité.
- Les données restent attribuées au MEIE (CC-BY 4.0). Ne pas les relicencier.
- La carte ne mélange pas le registre et l’enquête. L’action communautaire autonome n’y est pas. Les OBNL affichés sont ceux du périmètre de la Loi sur l’économie sociale, pas « le communautaire ».
- Côte-Nord et Nord-du-Québec : une seule estimation ISQ. Ne pas la répartir. Les mutuelles ne sont pas séparées des coopératives financières dans les fiches régionales (30 et 210 seulement au Québec).
- Les 17 coopératives sans `REGADMINP` restent dans le décompte, hors polygone.

## Ledger

- Playwright : pas encore. À ajouter avant de traiter l’UI comme un gate.
- Licence du code : MPL-2.0 ([`LICENSE.md`](LICENSE.md)). Les CSV, l’enquête et les contours gardent la licence de leur source.
