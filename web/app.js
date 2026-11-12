const CATEGORIES = [
  ["consommateurs", "Consommateurs"],
  ["solidarite", "Solidarité"],
  ["travailleurs", "Travailleurs"],
  ["producteurs", "Producteurs"],
  ["travailleurs_actionnaire", "Travailleurs actionnaires"],
  ["regroupements", "Regroupements"],
];
const LABEL = Object.fromEntries(CATEGORIES);
const COLORS = {
  consommateurs: "#d6c7a1",
  solidarite: "#9dcc86",
  travailleurs: "#8eb8d4",
  producteurs: "#e4c27a",
  travailleurs_actionnaire: "#c7b2d6",
  regroupements: "#a39b8a",
};
const PAGE = 80;

const state = {
  corpus: null,
  left: "2024-08",
  right: "2025-11",
  q: "",
  cat: "",
  mode: "toutes",
  neq: "",
  adresse: "",
  scian: "",
  region: "",
  couche: "meie",
  territoire: null,
  geo: null,
  limite: PAGE,
};

const $ = (id) => document.getElementById(id);

function fold(value) {
  return (value || "").toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
}

function n(value) {
  return Number(value).toLocaleString("fr-CA");
}

function obsAt(coop, extractId) {
  return coop.historique.find((item) => item.ex === extractId) || null;
}

function addressKey(obs) {
  if (!obs || !obs.adresse) return "";
  return `${obs.adresse.toUpperCase().replace(/\s+/g, " ").trim()}|${(obs.cp || "").replace(/\s/g, "").toUpperCase()}`;
}

function movement(coop) {
  const before = obsAt(coop, state.left);
  const after = obsAt(coop, state.right);
  if (!before && after) return "entree";
  if (before && !after) return "sortie";
  if (before && after && before.nom !== after.nom) return "nom";
  if (before && after && before.cat !== after.cat) return "categorie";
  return "stable";
}

function visible() {
  const query = fold(state.q);
  return state.corpus.coops.filter((coop) => {
    const kind = movement(coop);
    if (kind === "stable" && !obsAt(coop, state.left) && !obsAt(coop, state.right)) return false;
    if (state.mode === "entrees" && kind !== "entree") return false;
    if (state.mode === "sorties" && kind !== "sortie") return false;
    if (state.mode === "renoms" && kind !== "nom") return false;
    if (state.mode === "categories" && kind !== "categorie") return false;
    if (state.mode === "toutes" && kind === "stable" && !obsAt(coop, state.right) && !obsAt(coop, state.left)) return false;
    if (state.cat && coop.cat !== state.cat && (obsAt(coop, state.right) || obsAt(coop, state.left) || {}).cat !== state.cat) {
      const side = obsAt(coop, state.right) || obsAt(coop, state.left);
      if (!side || side.cat !== state.cat) return false;
    }
    if (state.adresse) {
      const side = obsAt(coop, state.right) || obsAt(coop, state.left);
      if (addressKey(side) !== state.adresse) return false;
    }
    if (state.scian && !(coop.scian_no || "").startsWith(state.scian)) return false;
    if (state.region === "non-codee" && regionDe(coop) !== "") return false;
    if (state.region && state.region !== "non-codee" && regionDe(coop) !== state.region) return false;
    if (!query) return true;
    const blob = coop.historique.map((item) => [item.nom, item.ville, item.adresse, item.scian].join(" ")).join(" ");
    return fold(`${blob} ${coop.neq} ${coop.dossier}`).includes(query);
  });
}

function pairCounts() {
  const counts = { gauche: 0, droite: 0, entree: 0, sortie: 0, nom: 0, categorie: 0 };
  for (const coop of state.corpus.coops) {
    if (obsAt(coop, state.left)) counts.gauche += 1;
    if (obsAt(coop, state.right)) counts.droite += 1;
    const kind = movement(coop);
    if (counts[kind] !== undefined) counts[kind] += 1;
  }
  return counts;
}

function renderMetrics() {
  const counts = pairCounts();
  $("met-gauche").textContent = n(counts.gauche);
  $("met-droite").textContent = n(counts.droite);
  $("met-entrees").textContent = n(counts.entree);
  $("met-sorties").textContent = n(counts.sortie);
  $("met-noms").textContent = n(counts.nom);
}

function renderChart() {
  const extracts = state.corpus.extraits;
  const series = CATEGORIES.map(([key]) => extracts.map((extract) => {
    let count = 0;
    for (const coop of state.corpus.coops) {
      const obs = obsAt(coop, extract.id);
      if (obs && obs.cat === key) count += 1;
    }
    return count;
  }));
  const max = Math.max(1, ...series.flat());
  const svg = $("graphique");
  svg.replaceChildren();
  const ns = "http://www.w3.org/2000/svg";
  const width = 680;
  const height = 220;
  const left = 36;
  const plotW = width - 48;
  const plotH = 150;
  extracts.forEach((extract, index) => {
    const x = left + (index * plotW) / (extracts.length - 1);
    const label = document.createElementNS(ns, "text");
    label.setAttribute("x", x);
    label.setAttribute("y", 214);
    label.setAttribute("fill", extract.id === state.right ? "#e4c27a" : "#a39b8a");
    label.setAttribute("font-size", "12");
    label.setAttribute("text-anchor", "middle");
    label.textContent = extract.libelle;
    svg.append(label);
  });
  series.forEach((values, seriesIndex) => {
    const [key] = CATEGORIES[seriesIndex];
    const points = values.map((value, index) => {
      const x = left + (index * plotW) / (extracts.length - 1);
      const y = 20 + plotH - (value / max) * plotH;
      return `${x},${y}`;
    }).join(" ");
    const line = document.createElementNS(ns, "polyline");
    line.setAttribute("points", points);
    line.setAttribute("fill", "none");
    line.setAttribute("stroke", COLORS[key]);
    line.setAttribute("stroke-width", "2");
    svg.append(line);
  });

  const head = $("serie-head");
  const body = $("serie-body");
  head.replaceChildren();
  body.replaceChildren();
  const corner = document.createElement("th");
  corner.textContent = "Catégorie";
  head.append(corner);
  for (const extract of extracts) {
    const cell = document.createElement("th");
    cell.textContent = extract.libelle;
    head.append(cell);
  }
  CATEGORIES.forEach(([key, label], seriesIndex) => {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    name.textContent = label;
    row.append(name);
    series[seriesIndex].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = n(value);
      row.append(cell);
    });
    body.append(row);
  });
}

function renderList(rows) {
  const liste = $("liste");
  liste.replaceChildren();
  for (const coop of rows.slice(0, state.limite)) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    if (coop.neq === state.neq) button.classList.add("is-on");
    const kind = movement(coop);
    const badge = document.createElement("span");
    badge.className = `badge ${kind === "entree" ? "entree" : kind === "sortie" ? "sortie" : "nom"}`;
    badge.textContent = { entree: "Entrée", sortie: "Sortie", nom: "Nom modifié", categorie: "Catégorie modifiée", stable: "" }[kind];
    const title = document.createElement("strong");
    const shown = obsAt(coop, state.right) || obsAt(coop, state.left);
    title.textContent = shown ? shown.nom : coop.nom;
    const meta = document.createElement("small");
    meta.textContent = `${LABEL[shown.cat] || "catégorie inconnue"} · ${shown.ville || "ville non indiquée"} · ${shown.region || "région non codée"} · NEQ ${coop.neq}`;
    button.append(badge, title, meta);
    button.addEventListener("click", () => {
      state.neq = coop.neq;
      render();
    });
    item.append(button);
    liste.append(item);
  }
  const suite = $("suite");
  const rest = rows.length - Math.min(rows.length, state.limite);
  suite.hidden = rest <= 0;
  suite.textContent = `Afficher les ${n(rest)} autres`;
}

function line(text, className) {
  const p = document.createElement("p");
  p.textContent = text;
  if (className) p.className = className;
  return p;
}

function clause(interdit, nom) {
  if (interdit === true) return `Les statuts interdisent les ${nom}.`;
  if (interdit === false) return `Les statuts n’interdisent pas les ${nom}.`;
  return `Le fichier ne dit pas si les statuts interdisent les ${nom}.`;
}

function contexte(scianNo) {
  const digits = (scianNo || "").replace(/\D/g, "");
  const firms = state.corpus.economie.entreprises.codes;
  const jobs = state.corpus.economie.emploi.codes;
  let firm = null;
  let used = "";
  for (const size of [digits.length, 4, 3, 2]) {
    const key = digits.slice(0, size);
    if (key && firms[key]) {
      firm = firms[key];
      used = key;
      break;
    }
  }
  return { firm, used, job: jobs[digits.slice(0, 2)] || null, two: digits.slice(0, 2) };
}

function renderFiche() {
  const fiche = $("fiche");
  fiche.replaceChildren();
  const coop = state.corpus.coops.find((item) => item.neq === state.neq);
  if (!coop) {
    const empty = document.createElement("p");
    empty.className = "fiche-vide";
    empty.textContent = "Choisis une coopérative. Sa fiche aligne les quatre observations et le secteur autour d’elle.";
    fiche.append(empty);
    return;
  }
  const latest = obsAt(coop, state.right) || obsAt(coop, state.left) || coop.historique.at(-1);
  const title = document.createElement("h2");
  title.textContent = latest.nom;
  fiche.append(title);
  fiche.append(line(`${LABEL[latest.cat] || "Catégorie inconnue"} · ${latest.secteur || "secteur non indiqué"}`));
  fiche.append(line(`NEQ ${coop.neq} · dossier ${coop.dossier}`));
  const confiance = coop.date_confiance === "ancree"
    ? `Constituée le ${coop.date_constitution}. Année ancrée sur l’extrait ${coop.date_source}.`
    : `Constituée le ${coop.date_constitution || "date illisible"}. Siècle inféré, sans année complète dans les extraits de 2021 et 2023.`;
  fiche.append(line(confiance));
  const raw = document.createElement("ul");
  for (const obs of coop.historique) {
    const item = document.createElement("li");
    item.textContent = `${obs.ex} · date brute ${obs.date_brute}`;
    raw.append(item);
  }
  fiche.append(raw);

  const before = obsAt(coop, state.left);
  const after = obsAt(coop, state.right);
  if (!before && after) fiche.append(line(`Entrée dans l’extrait ${state.right}.`, "clause"));
  if (before && !after) fiche.append(line(`Absente de l’extrait ${state.right}. Elle était active au ${state.left}.`, "clause"));
  if (before && after) {
    const fields = [
      ["nom", "Nom"],
      ["cat", "Catégorie"],
      ["secteur", "Secteur"],
      ["ville", "Ville"],
      ["adresse", "Adresse"],
      ["loi", "Loi"],
      ["scian_no", "SCIAN"],
    ];
    const changes = fields.filter(([key]) => before[key] !== after[key]);
    fiche.append(line(changes.length
      ? `Entre ${state.left} et ${state.right} : ${changes.map(([, label]) => label.toLowerCase()).join(", ")} ${changes.length > 1 ? "changent" : "change"}.`
      : `Entre ${state.left} et ${state.right}, le nom, la catégorie, le secteur, la ville, l’adresse, la loi et le SCIAN sont identiques.`));
  }

  const grid = document.createElement("div");
  grid.className = "temps";
  for (const extract of state.corpus.extraits) {
    const card = document.createElement("article");
    const heading = document.createElement("h3");
    heading.textContent = extract.libelle;
    card.append(heading);
    const obs = obsAt(coop, extract.id);
    if (!obs) {
      card.append(line("Absente"));
      card.classList.add("absent");
    } else {
      card.append(line(LABEL[obs.cat] || ""));
      card.append(line([obs.ville, obs.region].filter(Boolean).join(" · ") || "lieu non indiqué"));
    }
    grid.append(card);
  }
  fiche.append(grid);

  const interets = line(clause(latest.interdit_interets, "intérêts sur le capital social"), "clause");
  const ristournes = line(clause(latest.interdit_ristournes, "ristournes"), "clause");
  fiche.append(interets, ristournes);
  if (latest.solidarite) {
    const members = Object.entries({
      producteur: "producteurs",
      consommateur: "consommateurs",
      travailleur: "travailleurs",
      soutien: "soutien",
    }).filter(([key]) => latest.solidarite[key]).map(([, label]) => label);
    fiche.append(line(members.length
      ? `Solidarité : membres prévus — ${members.join(", ")}.`
      : "Solidarité : aucun collège de membres coché."));
  }
  fiche.append(line(latest.objet || "Le fichier ne contient pas l’objet."));
  fiche.append(line([latest.adresse, latest.ville, latest.cp, latest.region].filter(Boolean).join(", ")));

  const economy = contexte(latest.scian_no);
  if (economy.firm) {
    const same = state.corpus.coops.filter((item) => obsAt(item, state.right) && (item.scian_no || "").startsWith(economy.used)).length;
    fiche.append(line(
      `SCIAN ${economy.used} — ${economy.firm.libelle}. ${n(economy.firm.entreprises_avec_employes)} entreprises avec employés au Québec (Statistique Canada, 33-10-1095-01, période 2025-07). ${n(same)} coopératives actives de ce préfixe dans l’extrait ${state.right}.`,
    ));
  } else {
    fiche.append(line("Pas de correspondance SCIAN dans le tableau des entreprises."));
  }
  if (economy.job) {
    fiche.append(line(
      `Emploi salarié du SCIAN ${economy.two}, secteur entier : ${n(economy.job.emploi_salarie)} personnes en ${economy.job.annee} (Statistique Canada, 14-10-0202-01).`,
    ));
  }
  const key = addressKey(latest);
  const housemates = key
    ? state.corpus.coops.filter((item) => addressKey(obsAt(item, state.right)) === key).length
    : 0;
  if (housemates > 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lien";
    button.textContent = `${n(housemates)} coopératives partagent cette adresse dans l’extrait de fin. Les afficher.`;
    button.addEventListener("click", () => {
      state.adresse = key;
      state.limite = PAGE;
      render();
    });
    fiche.append(button);
  }
}

function regionDe(coop) {
  const obs = obsAt(coop, state.right) || obsAt(coop, state.left);
  return obs ? (obs.region_code || "") : "";
}

function choisirRegion(code) {
  state.region = state.region === code ? "" : code;
  state.limite = PAGE;
  render();
}

const COUCHES = {
  meie: {
    titre: "Coopératives non financières du registre, dans l’extrait de droite.",
    couleur: "#9dcc86",
  },
  cnf: {
    titre: "Coopératives non financières, estimation de l’enquête pour 2022. On ne l’ajoute pas au registre.",
    couleur: "#8eb8d4",
  },
  fm: {
    titre: "Coopératives financières et mutuelles, ensemble. Les 30 mutuelles du Québec ne sont pas ventilées par région.",
    couleur: "#e4c27a",
  },
  obnl: {
    titre: "Organismes à but non lucratif qui entrent dans la Loi sur l’économie sociale. L’action communautaire autonome n’est pas dans cette couche.",
    couleur: "#d6c7a1",
  },
  "sub-obnl": {
    titre: "Part des subventions dans les revenus des OBNL d’économie sociale, 2022.",
    couleur: "#e08b74",
  },
  "sub-coop": {
    titre: "Part des subventions dans les revenus des coopératives et des mutuelles, 2022. Les ventes font presque tout le reste.",
    couleur: "#9dcc86",
  },
};

function ficheIsq(code) {
  if (!state.territoire) return null;
  return state.territoire.regions.find((region) => region.codes.includes(code)) || null;
}

function meieCompte(code) {
  const voulu = code === "non-codee" ? "" : code;
  let count = 0;
  for (const coop of state.corpus.coops) {
    const obs = obsAt(coop, state.right);
    if (obs && (obs.region_code || "") === voulu) count += 1;
  }
  return count;
}

function fluxRegion(code) {
  let entrees = 0;
  let sorties = 0;
  for (const coop of state.corpus.coops) {
    const before = obsAt(coop, state.left);
    const after = obsAt(coop, state.right);
    const voulu = code === "non-codee" ? "" : code;
    const left = before ? (before.region_code || "") : null;
    const right = after ? (after.region_code || "") : null;
    if (right === voulu && left !== voulu) entrees += 1;
    if (left === voulu && right !== voulu) sorties += 1;
  }
  return { entrees, sorties };
}

function mesure(code) {
  if (state.couche === "meie") return { valeur: meieCompte(code), qualite: null };
  const fiche = ficheIsq(code);
  if (!fiche) return { valeur: null, qualite: null };
  if (state.couche === "cnf") return fiche.cooperatives_non_financieres;
  if (state.couche === "fm") return fiche.cooperatives_financieres_et_mutuelles;
  if (state.couche === "obnl") return fiche.obnl;
  if (state.couche === "sub-obnl") return fiche.part_subventions.obnl;
  return fiche.part_subventions.cooperatives_et_mutuelles;
}

function argent(cell) {
  if (!cell || cell.dollars == null) return "non publié";
  const digits = cell.dollars >= 50_000_000_000
    ? `${(cell.dollars / 1e9).toLocaleString("fr-CA", { maximumFractionDigits: 1 })} G$`
    : `${(cell.dollars / 1e6).toLocaleString("fr-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} M$`;
  return `${digits}${marque(cell.qualite)}`;
}

function pourcent(cell) {
  if (!cell || cell.valeur == null) return "non publié";
  return `${cell.valeur.toLocaleString("fr-CA", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %${marque(cell.qualite)}`;
}

function effectif(cell) {
  if (!cell || cell.valeur == null) return "non publié";
  return `${n(cell.valeur)}${marque(cell.qualite)}`;
}

function marque(qualite) {
  if (qualite === "cv15") return " (CV 15–25 %)";
  if (qualite === "cv25") return " (CV > 25 %)";
  return "";
}

function mix(from, to, t) {
  const read = (hex) => [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16));
  const left = read(from);
  const right = read(to);
  const channel = left.map((value, index) => Math.round(value + (right[index] - value) * t));
  return `#${channel.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function renderBandeau() {
  const bandeau = $("bandeau");
  if (!state.corpus) return;
  const registre = state.corpus.extraits.find((extract) => extract.id === state.right);
  const isq = state.territoire;
  if (!isq) {
    bandeau.textContent = `Registre, extrait ${registre.libelle} : ${n(registre.n)} coopératives non financières. L’enquête régionale n’est pas chargée.`;
    return;
  }
  const qc = isq.quebec;
  bandeau.textContent = `Registre, ${registre.libelle} : ${n(registre.n)} coopératives non financières. Enquête 2022 : ${n(qc.entreprises)} entreprises d’économie sociale, dont ${n(qc.obnl)} OBNL, ${n(qc.cooperatives_non_financieres)} coopératives non financières, ${n(qc.cooperatives_financieres)} coopératives financières et ${n(qc.mutuelles)} mutuelles.`;
}

function chemin(rings, place) {
  return rings.map((ring) => ring.map((point, index) => {
    const [x, y] = place(point[0], point[1]);
    return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ") + "Z").join(" ");
}

function renderCarte() {
  const svg = $("carte");
  const titre = svg.querySelector("title");
  svg.replaceChildren(titre);
  $("couche-lire").textContent = COUCHES[state.couche].titre;
  if (!state.geo || !state.corpus) {
    $("carte-lecture").textContent = "Contours ou registre absents.";
    return;
  }
  const cos = Math.cos((50 * Math.PI) / 180);
  const project = (lon, lat) => [lon * cos, -lat];
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const feature of state.geo.features) {
    for (const polygon of feature.geometry.coordinates) {
      for (const ring of polygon) {
        for (const point of ring) {
          const [x, y] = project(point[0], point[1]);
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minY = Math.min(minY, y);
          maxY = Math.max(maxY, y);
        }
      }
    }
  }
  const width = 640;
  const mapHeight = 600;
  const height = 760;
  const pad = 16;
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const scale = Math.min((width - pad * 2) / spanX, (mapHeight - pad * 2) / spanY);
  const place = (lon, lat) => {
    const [x, y] = project(lon, lat);
    return [pad + (x - minX) * scale, pad + (y - minY) * scale];
  };
  const mesures = state.geo.features.map((feature) => mesure(feature.properties.code));
  const nombres = mesures.map((item) => item.valeur).filter((valeur) => valeur != null);
  const bas = Math.min(...nombres);
  const haut = Math.max(...nombres);
  const ns = "http://www.w3.org/2000/svg";
  const draw = (feature, placer, extraClass) => {
    const code = feature.properties.code;
    const item = mesure(code);
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", chemin(feature.geometry.coordinates.flatMap((polygon) => polygon.slice(0, 1)), placer));
    path.classList.add("region");
    if (extraClass) path.classList.add(extraClass);
    if (state.region === code) path.classList.add("is-on");
    const t = item.valeur == null || haut === bas ? 0.55 : (item.valeur - bas) / (haut - bas);
    path.setAttribute("fill", item.valeur == null ? "#2a2e28" : mix("#24302a", COUCHES[state.couche].couleur, 0.28 + t * 0.72));
    path.setAttribute("role", "button");
    path.setAttribute("tabindex", "0");
    const lu = item.valeur == null ? "non publié" : (state.couche.startsWith("sub") ? pourcent(item) : n(item.valeur));
    path.setAttribute("aria-label", `${feature.properties.nom}, ${lu}`);
    const tip = document.createElementNS(ns, "title");
    tip.textContent = `${feature.properties.nom} · ${lu}`;
    path.append(tip);
    path.addEventListener("click", () => choisirRegion(code));
    path.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        choisirRegion(code);
      }
    });
    path.addEventListener("pointerenter", () => {
      $("carte-lecture").textContent = `${feature.properties.nom} · ${lu}`;
    });
    return path;
  };
  // Un seul anneau extérieur : les trous sont rares à cette généralisation,
  // et un second anneau inversé n'est pas distingué ici.
  for (const feature of state.geo.features) svg.append(draw(feature, place));
  const insetCodes = new Set(["06", "13"]);
  const insetFeatures = state.geo.features.filter((feature) => insetCodes.has(feature.properties.code));
  let iMinX = Infinity;
  let iMinY = Infinity;
  let iMaxX = -Infinity;
  let iMaxY = -Infinity;
  for (const feature of insetFeatures) {
    for (const polygon of feature.geometry.coordinates) {
      for (const point of polygon[0]) {
        const [x, y] = place(point[0], point[1]);
        iMinX = Math.min(iMinX, x);
        iMaxX = Math.max(iMaxX, x);
        iMinY = Math.min(iMinY, y);
        iMaxY = Math.max(iMaxY, y);
      }
    }
  }
  const box = { x: 18, y: mapHeight + 8, w: 280, h: height - mapHeight - 16 };
  const frame = document.createElementNS(ns, "rect");
  frame.setAttribute("x", box.x);
  frame.setAttribute("y", box.y);
  frame.setAttribute("width", box.w);
  frame.setAttribute("height", box.h);
  frame.setAttribute("fill", "#10130f");
  frame.setAttribute("stroke", "#34382f");
  svg.append(frame);
  const iScale = Math.min((box.w - 16) / (iMaxX - iMinX || 1), (box.h - 28) / (iMaxY - iMinY || 1));
  const placeInset = (lon, lat) => {
    const [x, y] = place(lon, lat);
    return [box.x + 8 + (x - iMinX) * iScale, box.y + 20 + (y - iMinY) * iScale];
  };
  for (const feature of insetFeatures) svg.append(draw(feature, placeInset, "inset"));
  const label = document.createElementNS(ns, "text");
  label.setAttribute("x", box.x + 8);
  label.setAttribute("y", box.y + 14);
  label.setAttribute("fill", "#a39b8a");
  label.setAttribute("font-size", "11");
  label.textContent = "Montréal et Laval, agrandis";
  svg.append(label);
  const unite = state.couche.startsWith("sub") ? " %" : "";
  const gris = mesures.some((item) => item.valeur == null)
    ? " Une région grise n’est pas un zéro : la fiche ne publie pas le chiffre."
    : "";
  $("carte-legende").textContent = nombres.length
    ? `Plus c’est clair, plus le chiffre est élevé : ${bas.toLocaleString("fr-CA")}${unite} à ${haut.toLocaleString("fr-CA")}${unite}.${gris}`
    : "";
  if (!$("carte-lecture").textContent) {
    $("carte-lecture").textContent = "Choisir une région sur la carte ou dans le tableau.";
  }
}

function barre(classe, etiquette, part) {
  if (!part || part.valeur == null) return line(etiquette);
  const wrap = document.createElement("div");
  wrap.className = `barre ${classe}`;
  const caption = document.createElement("p");
  caption.textContent = etiquette;
  const track = document.createElement("span");
  const fill = document.createElement("i");
  fill.style.width = `${Math.max(0, Math.min(100, part.valeur))}%`;
  track.append(fill);
  wrap.append(caption, track);
  return wrap;
}

function renderRegionCard() {
  const card = $("region-card");
  card.replaceChildren();
  if (!state.corpus) return;
  if (state.region === "non-codee") {
    const title = document.createElement("h3");
    title.textContent = "Région non codée";
    card.append(title);
    card.append(line(`${n(meieCompte("non-codee"))} coopératives de l’extrait ${state.right} ont une ville et un code postal, mais le fichier laisse la région administrative vide. Elles ne sont pas dessinées.`));
    return;
  }
  if (!state.region) {
    const title = document.createElement("h3");
    title.textContent = "Québec";
    card.append(title);
    card.append(line("Choisir une région pour la poser à côté du registre et de l’enquête."));
    if (state.territoire) {
      const qc = state.territoire.quebec;
      card.append(line(`Enquête 2022 : ${argent(qc.revenus)} de revenus, ${n(qc.salaries)} personnes salariées, ${n(qc.membres)} membres. Les ventes font ${qc.part_chiffre_affaires.toLocaleString("fr-CA")} % des revenus, les subventions ${qc.part_subventions.toLocaleString("fr-CA")} %.`));
      card.append(line("Les mutuelles sont 30 au Québec. Aucune fiche régionale ne les sépare des coopératives financières.", "clause"));
    }
    const vides = meieCompte("");
    if (vides) card.append(line(`${n(vides)} coopératives de l’extrait de droite ont une ville, mais pas de région administrative. Elles restent hors de la carte.`));
    return;
  }
  const feature = state.geo && state.geo.features.find((item) => item.properties.code === state.region);
  const title = document.createElement("h3");
  title.textContent = feature ? feature.properties.nom : state.region;
  card.append(title);
  const stock = meieCompte(state.region);
  const mouvement = fluxRegion(state.region);
  card.append(line(`Registre, extrait ${state.right} : ${n(stock)} coopératives non financières.`));
  card.append(line(`Entre ${state.left} et ${state.right} : ${n(mouvement.entrees)} sont arrivées dans cette région, ${n(mouvement.sorties)} en sont parties ou ont quitté le registre. Une sortie n’est pas, à elle seule, une fermeture.`));
  const secteurs = new Map();
  let nord = 0;
  for (const coop of state.corpus.coops) {
    const obs = obsAt(coop, state.right);
    if (!obs || (obs.region_code || "") !== state.region) continue;
    secteurs.set(obs.secteur || "secteur non indiqué", (secteurs.get(obs.secteur || "secteur non indiqué") || 0) + 1);
    if (["travailleurs", "travailleurs_actionnaire", "solidarite"].includes(obs.cat)) nord += 1;
  }
  const top = [...secteurs.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
  if (top.length) {
    card.append(line(`Secteurs les plus nombreux dans le registre : ${top.map(([nom, count]) => `${nom} (${n(count)})`).join(", ")}.`));
    card.append(line(`Travailleurs, travailleurs actionnaires et solidarité : ${n(nord)} sur ${n(stock)}.`));
  }
  const fiche = ficheIsq(state.region);
  if (!fiche) {
    card.append(line("Pas d’estimation d’enquête pour cette région."));
    return;
  }
  if (fiche.codes.length > 1) {
    card.append(line("L’enquête publie Côte-Nord et Nord-du-Québec comme une seule estimation. Les chiffres qui suivent couvrent les deux régions, une fois.", "clause"));
  }
  card.append(line(`Enquête 2022, estimation : ${effectif(fiche.entreprises)} entreprises d’économie sociale, dont ${effectif(fiche.obnl)} OBNL, ${effectif(fiche.cooperatives_non_financieres)} coopératives non financières et ${effectif(fiche.cooperatives_financieres_et_mutuelles)} coopératives financières et mutuelles.`));
  card.append(line(`${effectif(fiche.salaries)} personnes salariées, ${effectif(fiche.membres)} membres. Population indiquée sur la fiche : ${n(fiche.population)}.`));
  card.append(line(`Revenus : OBNL ${argent(fiche.revenus.obnl)}, coopératives et mutuelles ${argent(fiche.revenus.cooperatives_et_mutuelles)}, ensemble ${argent(fiche.revenus.ensemble)}.`));
  card.append(line("Les coopératives financières sont dans le groupe « coopératives et mutuelles ». Le siège social emporte avec lui les filiales.", "clause"));
  card.append(barre("obnl", `Subventions, OBNL : ${pourcent(fiche.part_subventions.obnl)}. Ventes : ${pourcent(fiche.part_chiffre_affaires.obnl)}.`, fiche.part_subventions.obnl));
  card.append(barre("coop", `Subventions, coopératives et mutuelles : ${pourcent(fiche.part_subventions.cooperatives_et_mutuelles)}. Ventes : ${pourcent(fiche.part_chiffre_affaires.cooperatives_et_mutuelles)}.`, fiche.part_subventions.cooperatives_et_mutuelles));
}

function renderRegionsTable() {
  const body = $("regions-body");
  body.replaceChildren();
  if (!state.geo || !state.corpus) return;
  const colonne = { meie: 1, cnf: 2, fm: 3, obnl: 4, "sub-obnl": 5, "sub-coop": 6 }[state.couche];
  const head = $("regions").querySelectorAll("th");
  head.forEach((cell, index) => cell.classList.toggle("col-on", index === colonne));
  const rows = state.geo.features.map((feature) => feature.properties);
  const vides = meieCompte("non-codee");
  const lignes = vides ? rows.concat([{ code: "non-codee", nom: "Région non codée" }]) : rows;
  for (const region of lignes) {
    const fiche = region.code ? ficheIsq(region.code) : null;
    const afficherIsq = fiche && (fiche.codes[0] === region.code || fiche.codes.length === 1);
    const cells = [
      region.nom,
      n(meieCompte(region.code)),
      afficherIsq ? effectif(fiche.cooperatives_non_financieres) : (fiche ? "même fiche" : "—"),
      afficherIsq ? effectif(fiche.cooperatives_financieres_et_mutuelles) : (fiche ? "même fiche" : "—"),
      afficherIsq ? effectif(fiche.obnl) : (fiche ? "même fiche" : "—"),
      afficherIsq ? pourcent(fiche.part_subventions.obnl) : (fiche ? "même fiche" : "—"),
      afficherIsq ? pourcent(fiche.part_subventions.cooperatives_et_mutuelles) : (fiche ? "même fiche" : "—"),
    ];
    const tr = document.createElement("tr");
    if (state.region === region.code) tr.classList.add("is-on");
    cells.forEach((text, index) => {
      const td = document.createElement("td");
      td.classList.toggle("col-on", index === colonne);
      if (index === 0) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.addEventListener("click", () => choisirRegion(region.code));
        td.append(button);
      } else {
        td.textContent = text;
      }
      tr.append(td);
    });
    body.append(tr);
  }
}

function renderFilterChip() {
  const chip = $("filtre-actif");
  if (!state.adresse && !state.scian && !state.region) {
    chip.hidden = true;
    return;
  }
  chip.hidden = false;
  chip.replaceChildren();
  if (state.region) {
    const feature = state.geo && state.geo.features.find((item) => item.properties.code === state.region);
    const nom = state.region === "non-codee" ? "région non codée" : (feature ? feature.properties.nom : state.region);
    chip.append(`Filtre : ${nom}. `);
  } else {
    chip.append(state.adresse ? "Filtre : même adresse. " : "Filtre SCIAN. ");
  }
  const clear = document.createElement("button");
  clear.type = "button";
  clear.className = "lien";
  clear.textContent = "Retirer";
  clear.addEventListener("click", () => {
    state.adresse = "";
    state.scian = "";
    state.region = "";
    render();
  });
  chip.append(clear);
}

function render() {
  renderBandeau();
  renderCarte();
  renderRegionCard();
  renderRegionsTable();
  renderMetrics();
  renderChart();
  renderFilterChip();
  const rows = visible();
  renderList(rows);
  renderFiche();
}

function bind() {
  for (const id of ["de", "a"]) {
    $(id).addEventListener("change", () => {
      state.left = $("de").value;
      state.right = $("a").value;
      if (state.corpus.extraits.findIndex((item) => item.id === state.left)
        > state.corpus.extraits.findIndex((item) => item.id === state.right)) {
        [state.left, state.right] = [state.right, state.left];
        $("de").value = state.left;
        $("a").value = state.right;
      }
      state.limite = PAGE;
      render();
    });
  }
  $("q").addEventListener("input", (event) => {
    state.q = event.target.value;
    state.limite = PAGE;
    render();
  });
  $("categorie").addEventListener("change", (event) => {
    state.cat = event.target.value;
    state.limite = PAGE;
    render();
  });
  $("mode").addEventListener("change", (event) => {
    state.mode = event.target.value;
    state.limite = PAGE;
    render();
  });
  $("suite").addEventListener("click", () => {
    state.limite = Number.POSITIVE_INFINITY;
    render();
  });
  for (const input of document.querySelectorAll("input[name=couche]")) {
    input.addEventListener("change", () => {
      if (!input.checked) return;
      state.couche = input.value;
      render();
    });
  }
}

async function main() {
  bind();
  for (const [value, label] of CATEGORIES) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    $("categorie").append(option);
  }
  try {
    const response = await fetch("data/corpus.json");
    if (!response.ok) throw new Error(String(response.status));
    state.corpus = await response.json();
    const [territoire, geo] = await Promise.all([
      fetch("data/isq-regions.json").then((item) => (item.ok ? item.json() : null)),
      fetch("data/regions.geojson").then((item) => (item.ok ? item.json() : null)),
    ]);
    state.territoire = territoire;
    state.geo = geo;
    for (const extract of state.corpus.extraits) {
      for (const select of [$("de"), $("a")]) {
        const option = document.createElement("option");
        option.value = extract.id;
        option.textContent = `${extract.libelle} · ${n(extract.n)}`;
        select.append(option);
      }
    }
    $("de").value = state.left;
    $("a").value = state.right;
    $("statut").textContent = "Quatre extraits du MEIE. Les dates de Citadelle et de Sollio reprennent l’année complète de décembre 2021.";
    render();
  } catch (error) {
    $("statut").textContent = "Corpus absent. Depuis la racine : python scripts/build_snapshot.py puis python -m http.server -d web --bind 127.0.0.1 8765.";
  }
}

main();
