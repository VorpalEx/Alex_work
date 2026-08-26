// Récupère l'inventaire complet des articles Framer et l'écrit en JSON.
//
// Env :
//   FRAMER_PROJECT_URL    (ex: https://framer.com/projects/XXXX)
//   FRAMER_API_KEY | FRAMER_API_TOKEN
//   FRAMER_COLLECTIONS    "News=/news,Blog=/blog,Use Cases=/use-case"
//                         (nom exact de la collection = préfixe d'URL)
//   SITE_BASE_URL         (défaut https://dillygence.com)
//   FRAMER_INVENTORY_FILE (défaut framer_inventory.json)
//   FRAMER_USE_BASE_SLUG  "true" -> utilise le slug de base (EN) au lieu du slug localisé
//   FRAMER_INCLUDE_DRAFTS "true" -> inclut aussi les brouillons (défaut: publiés seulement)
import { connect } from "framer-api";
import { writeFileSync } from "node:fs";

const url = process.env.FRAMER_PROJECT_URL;
const key = process.env.FRAMER_API_KEY || process.env.FRAMER_API_TOKEN;
const site = (process.env.SITE_BASE_URL || "https://dillygence.com").replace(/\/+$/, "");
const outFile = process.env.FRAMER_INVENTORY_FILE || "framer_inventory.json";
const useBaseSlug = (process.env.FRAMER_USE_BASE_SLUG || "").toLowerCase() === "true";
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

// Un champ Framer = { type, value, valueByLocale?: { <locale>: { value } } }.
// On privilégie la valeur localisée (FR) si présente, sinon la valeur de base.
function localized(fieldOrSlugMap, baseValue) {
  if (fieldOrSlugMap && typeof fieldOrSlugMap === "object") {
    const byLocale = fieldOrSlugMap.valueByLocale || fieldOrSlugMap;
    for (const k in byLocale) {
      const v = byLocale[k]?.value;
      if (v) return v;
    }
  }
  return baseValue ?? "";
}

// Titre : champ "title" si présent, sinon 1er champ de type "string" non vide.
function titleOf(item) {
  const fd = item.fieldData || {};
  if (fd.title) return localized(fd.title, fd.title.value);
  for (const k of Object.keys(fd)) {
    const f = fd[k];
    if (f && f.type === "string") {
      const v = localized(f, f.value);
      if (v) return v;
    }
  }
  return item.slug || "";
}

// Slug : version localisée (FR) si présente, sinon slug de base (EN).
function slugOf(item) {
  if (!useBaseSlug) {
    const bl = item.slugByLocale || {};
    for (const k in bl) {
      const v = bl[k]?.value;
      if (v) return v;
    }
  }
  return item.slug || "";
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
      const slug = String(slugOf(it) || "").replace(/^\/+|\/+$/g, "");
      if (!slug) continue;
      const path = `${prefix}/${slug}`;
      inventory.push({
        title: String(titleOf(it) || slug),
        slug,
        path,
        url: `${site}${path}`,
        collection: coll.name,
      });
      kept++;
    }
    console.log(`${coll.name} → ${kept}/${items.length} items publiés (préfixe ${prefix})`);
  }
} finally {
  await framer.disconnect();
}

writeFileSync(outFile, JSON.stringify(inventory, null, 2), "utf-8");
console.log(`✅ ${inventory.length} articles écrits dans ${outFile}`);
