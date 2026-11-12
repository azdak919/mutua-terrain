# Mutua Terrain

Observatoire de lecture des **coopératives non financières actives au Québec**.
Side project de [Mutua](https://github.com/azdak919/mutua) : le terrain déjà constitué, pas l’outil qui rédige des statuts.

L’extrait épinglé est celui du **19 novembre 2025** (catalogue Données Québec, mis à jour le 20 janvier 2026) : 2 558 coopératives, 37 colonnes.

## À quoi ça sert

Une personne qui veut fonder une coopérative de travailleurs ou de solidarité peut voir qui existe déjà : catégorie, secteur, région, objet, clause sur les ristournes et les intérêts, numéro d’entreprise du Québec.

La page a deux étages.

1. **La carte** des 17 régions administratives. La couleur suit, au choix, le registre ou l’enquête. Cliquer une région filtre la liste.
2. **D’un extrait à l’autre.** Quatre recensements du même objet. La fiche énonce les clauses en français, sans laisser les codes `O` / `N` à l’écran.

## Deux sources, deux périmètres

| | Registre MEIE | Enquête ISQ |
|---|---|---|
| Quoi | Coopératives non financières actives, une ligne par personne morale | Coopératives, mutuelles, et OBNL qui vendent un bien ou un service et répondent aux six principes de la Loi sur l’économie sociale |
| Quand | Extraits 2021-12, 2023-04, 2024-08, 2025-11 | Année 2022, publié le 11 juillet 2025 |
| Grain | La coopérative | La région, en estimation arrondie |

On ne les additionne pas. L’action communautaire autonome n’est pas dans l’enquête, et elle n’est pas sur la carte.

Les fiches régionales ne séparent pas les mutuelles des coopératives financières (30 mutuelles et 210 coopératives financières au Québec). Côte-Nord et Nord-du-Québec sont une seule estimation : le tableau l’écrit « même fiche » pour ne pas la compter deux fois. Les revenus du groupe « coopératives et mutuelles » comprennent les coopératives financières, siège social et filiales.

## Ce que le registre ne contient pas

- les coopératives dissoutes, fusionnées ou radiées ;
- les coopératives financières (caisses, assurances) et les mutuelles ;
- le nombre de membres, les emplois, le chiffre d’affaires de *cette* coopérative.

L’objet est vide pour 1 135 fiches, surtout des coopératives de consommateurs en habitation (1 288 fiches au secteur Habitation, dont 1 202 de consommateurs).

## Deux pièges de lecture

**Dates.** `DATECONS` est sur deux chiffres (`83-08-13`). Terrain la replace selon l’année de l’extrait : pour 2025, `00`–`25` → 2000–2025 et `26`–`99` → 1926–1999.

**Ristournes et intérêts.** `O` veut dire que les statuts **interdisent** le versement. `N` veut dire qu’ils ne l’interdisent pas. Le dictionnaire de champs de 2019 décrit une clause. L’avis du ministère collé aux fichiers de 2026 lit `N` comme un versement réel. Terrain suit le dictionnaire : absence d’interdiction n’est pas la preuve qu’un chèque est parti.

Les indicateurs de membres (producteur, consommateur, travailleur, soutien) ne sont exposés que pour les coopératives de solidarité. Le dictionnaire dit qu’ils décrivent ce que l’objet a prévu, pas les membres réellement admis.

## Dates corrigées

L’extrait de novembre 2025 écrit `25-05-02`. Celui d’août 2024 écrit `5/2/25` (Excel). Ceux de 2021 et 2023 écrivent `1925-05-02 00:00:00.0`. Le corpus retient l’année complète dès qu’un extrait l’a. Citadelle revient au 2 mai 1925, Sollio au 22 décembre 1922. Sans année complète, le siècle est inféré et la fiche le dit.

## Contexte économique

Le SCIAN de la fiche est rapproché de deux tableaux ouverts de Statistique Canada, pour le Québec :

- 33-10-1095-01, entreprises avec employés, période 2025-07
- 14-10-0202-01, emploi salarié annuel, quand le code à deux chiffres y est publié

Ce sont les chiffres du secteur, pas ceux de la coopérative. Le fichier épinglé est `data/economy/contexte-scian.json`.

L’enquête régionale est dans `data/economy/isq-regions.json`, tirée des fiches PDF de l’ISQ. Les contours sont dans `data/geo/regions.geojson` (couche Administratives, SDA20K V2022-02, généralisée). `python scripts/build_territoire.py` reconstruit les deux si les PDF sont dans `/tmp/isq-fiches`. `build_snapshot.py` recopie ces fichiers vers `web/data/`.

## Lancer

```bash
pip install pytest
pytest
python scripts/build_snapshot.py
python -m http.server -d web 8765
```

Puis ouvrir `http://127.0.0.1:8765/`. Le JSON dérivé (`web/data/corpus.json`) n’est pas versionné. Les quatre CSV source le sont.

## Source

Ministère de l’Économie, de l’Innovation et de l’Énergie. *Données administratives des coopératives non financières*, [Jeu de données], dans Données Québec, 2019, mis à jour le 20 janvier 2026.

<https://www.donneesquebec.ca/recherche/dataset/donnees-administratives-des-cooperatives-non-financieres>

Licence des données : Attribution (CC-BY 4.0). Le code est sous MPL-2.0. Le détail, et les autres sources, sont dans [`LICENSE.md`](LICENSE.md).

## Place dans Mutua

Dossier frère de `mutua-studio` et `mutua-ops`. Il ne modifie pas le hub, le standard, ni les feuilles juridiques. Un lien depuis Studio (« pairs déjà constituées au Québec ») serait un changement du dépôt `mutua` / `mutua-studio`, à part.
