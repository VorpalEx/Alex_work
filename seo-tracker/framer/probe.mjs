// Sonde Framer : affiche les collections et la structure d'un item.
// Sert à découvrir les NOMS de collections et les champs (slug/title) réels.
//
// Env attendus : FRAMER_PROJECT_URL, FRAMER_API_KEY (ou FRAMER_API_TOKEN).
import { connect } from "framer-api";

const url = process.env.FRAMER_PROJECT_URL;
const key = process.env.FRAMER_API_KEY || process.env.FRAMER_API_TOKEN;

if (!url) { console.error("FRAMER_PROJECT_URL manquant."); process.exit(2); }
if (!key) { console.error("FRAMER_API_KEY / FRAMER_API_TOKEN manquant."); process.exit(2); }

const framer = await connect(url, key);
try {
  const collections = await framer.getCollections();
  console.log(`== ${collections.length} collection(s) ==`);
  for (const c of collections) {
    let items = [];
    try { items = await c.getItems(); } catch (e) { console.log(`  (getItems a échoué: ${e?.message})`); }
    console.log(`\n• name=${JSON.stringify(c.name)}  id=${c.id ?? "?"}  slug=${c.slug ?? "?"}  items=${items.length}`);
    if (items.length) {
      const it = items[0];
      console.log("  clés item :", Object.keys(it));
      // Champs fréquents
      for (const f of ["id", "slug", "title", "name", "path"]) {
        if (it[f] !== undefined) console.log(`    ${f} = ${JSON.stringify(it[f])}`);
      }
      // Dump partiel (sérialisable) pour voir la structure
      try {
        console.log("  item (JSON, tronqué) :\n" + JSON.stringify(it, null, 2).slice(0, 1800));
      } catch { /* items non sérialisables : les clés ci-dessus suffisent */ }
    }
  }
} finally {
  await framer.disconnect();
}
