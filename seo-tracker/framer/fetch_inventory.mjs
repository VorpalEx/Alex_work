// Récupère l'inventaire complet des articles Framer et l'écrit en JSON.
//
// Env :
//   FRAMER_PROJECT_URL    (ex: https://framer.com/projects/XXXX)
//   FRAMER_API_KEY | FRAMER_API_TOKEN
//   FRAMER_COLLECTIONS    "News=/news,Blog=/blog,Use Cases=/use-case"
//                         (nom exact de la collection = préfixe d'URL)
//   SITE_BASE_URL         (défaut https://dillygence.com)
//   FRAMER_INVENTORY_FILE (défaut framer_inventory.json)
//   FRAMER_USE_LOCALIZED_SLUG "true" -> slug localisé (FR) comme principal
//                             (défaut: slug de base/EN, = URLs live de dillygence.com)
//   FRAMER_INCLUDE_DRAFTS "true" -> inclut aussi les brouillons (défaut: publiés seulement)
//
// Chaque article émet `path` (URL principale) + `alt_paths` (autres slugs connus),
// pour que la jointure GSC/GA4 fonctionne quel que soit le slug utilisé en ligne.
import { connect } from "framer-api";
import { writeFileSync } from "node:fs";

const url = process.env.FRAMER_PROJECT_URL;
const key = process.env.FRAMER_API_KEY || process.env.FRAMER_API_TOKEN;
const site = (process.env.SITE_BASE_URL || "https://dillygence.com").replace(/\/+$/, "");
const outFile = process.env.FRAMER_INVENTORY_FILE || "framer_inventory.json";
const preferLocalized = (process.env.FRAMER_USE_LOCALIZED_SLUG || "").toLowerCase() === "true";
const includeDrafts = (process.env.FRAMER_INCLUDE_DRAFTS || "").toLowerCase() === "true";

if (!url) { console.error("FRAMER_PROJECT_URL manquant."); process.exit(2); }
if (!key) { console.error("FRAMER_API_KEY / FRAMER_API_TOKEN manquant."); process.exit(2); }

// Parse "Name=/prefix,Name2=/prefix2"
const mapping = new Map();
for (const pair of (process.env.FRAMER_COLLECTIONS || "").split(",")) {
  const t = pair.trim();
  const i = t.indexOf("=");
  if (i > 0) mapping.set(t.slice(0, i).trim().toLowerCase(), "/" + t.slice(i + 1).trim().replace(/^\/+|\/+$/g, ""));
}
if (mapping.size === 0) {
  console.error("FRAMER_COLLECTIONS manquant (ex: 'News=/news,Blog=/blog,Use Cases=/use-case').");
  process.exit(2);
}

const clean = (s) => String(s || "").replace(/^\/+|\/+$/g, "");

// Valeur localisée (FR) d'un champ, sinon valeur de base.
function localized(fieldObj, baseValue) {
  const byLocale = fieldObj?.valueByLocale;
  if (byLocale) for (const k in byLocale) { const v = byLocale[k]?.value; if (v) return v; }
  return baseValue ?? "";
}

// Titre : champ "title" si présent, sinon 1er champ de type "string" non vide.
function titleOf(item) {
  const fd = item.fieldData || {};
  if (fd.title) return localized(fd.title, fd.title.value);
  for (const k of Object.keys(fd)) {
    const f = fd[k];
    if (f && f.type === "string") { const v = localized(f, f.value); if (v) return v; }
  }
  return item.slug || "";
}

// Slugs candidats : base (EN) + localisé (FR) éventuel. Le principal dépend de la préférence.
function slugsOf(item) {
  const base = clean(item.slug);
  let loc = "";
  const bl = item.slugByLocale || {};
  for (const k in bl) { const v = bl[k]?.value; if (v) { loc = clean(v); break; } }
  const primary = preferLocalized && loc ? loc : base;
  const alts = [base, loc].filter((s) => s && s !== primary);
  return { primary, alts };
}

const framer = await connect(url, key);
const inventory = [];
try {
  const collections = await framer.getCollections();
  const byName = new Map(collections.map((c) => [String(c.name).toLowerCase(), c]));

  for (const [name, prefix] of mapping) {
    const coll = byName.get(name);
    if (!coll) { console.error(`⚠️  Collection introuvable: "${name}" (ignorée).`); continue; }
    const items = await coll.getItems();
    let kept = 0;
    for (const it of items) {
      if (!includeDrafts && it.draft === true) continue;
      const { primary, alts } = slugsOf(it);
      if (!primary) continue;
      const path = `${prefix}/${primary}`;
      inventory.push({
        title: String(titleOf(it) || primary),
        slug: primary,
        path,
        url: `${site}${path}`,
        collection: coll.name,
        alt_paths: alts.map((s) => `${prefix}/${s}`),
      });
      kept++;
    }
    console.log(`${coll.name} → ${kept}/${items.length} items publiés (préfixe ${prefix})`);
  }
} finally {
  await framer.disconnect();
}

writeFileSync(outFile, JSON.stringify(inventory, null, 2), "utf-8");
console.log(`✅ ${inventory.length} articles écrits dans ${outFile} (slug principal: ${preferLocalized ? "localisé/FR" : "base/EN"})`);
