// Récupère l'inventaire complet des articles Framer et l'écrit en JSON.
//
// Env :
//   FRAMER_PROJECT_URL    (ex: https://framer.com/projects/XXXX)
//   FRAMER_API_KEY | FRAMER_API_TOKEN
//   FRAMER_COLLECTIONS    "News=/news,Blog=/blog,Use Cases=/use-case"
//                         (nom exact de la collection = préfixe d'URL)
//   SITE_BASE_URL         (défaut https://dillygence.com)
//   FRAMER_INVENTORY_FILE (défaut framer_inventory.json)
//   FRAMER_SLUG_FIELD     (défaut "slug")   FRAMER_TITLE_FIELD (défaut "title")
import { connect } from "framer-api";
import { writeFileSync } from "node:fs";

const url = process.env.FRAMER_PROJECT_URL;
const key = process.env.FRAMER_API_KEY || process.env.FRAMER_API_TOKEN;
const site = (process.env.SITE_BASE_URL || "https://dillygence.com").replace(/\/+$/, "");
const outFile = process.env.FRAMER_INVENTORY_FILE || "framer_inventory.json";
const slugField = process.env.FRAMER_SLUG_FIELD || "slug";
const titleField = process.env.FRAMER_TITLE_FIELD || "title";

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

// Extrait un champ d'un item, quelle que soit la forme (plat ou imbriqué).
function field(item, name) {
  for (const c of [item, item?.fieldData, item?.fields, item?.data]) {
    if (c && c[name] != null && c[name] !== "") {
      const v = c[name];
      return typeof v === "object" && "value" in v ? v.value : v;
    }
  }
  return "";
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
    for (const it of items) {
      const slug = String(field(it, slugField) || it.slug || "").replace(/^\/+|\/+$/g, "");
      if (!slug) continue;
      const path = `${prefix}/${slug}`;
      inventory.push({
        title: String(field(it, titleField) || it.name || slug),
        slug,
        path,
        url: `${site}${path}`,
        collection: coll.name,
      });
    }
    console.log(`${coll.name} → ${items.length} items (préfixe ${prefix})`);
  }
} finally {
  await framer.disconnect();
}

writeFileSync(outFile, JSON.stringify(inventory, null, 2), "utf-8");
console.log(`✅ ${inventory.length} articles écrits dans ${outFile}`);
