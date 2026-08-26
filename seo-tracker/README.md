# SEO Tracker — Dillygence

Outil de suivi des performances SEO des articles de **dillygence.com**.
Il récupère chaque jour les données de **Google Search Console** (mots-clés,
positions, clics, impressions) et de **Google Analytics 4** (vues, temps passé,
conversions), les **joint par URL d'article**, et met à jour deux bases **Notion**.

## Ce que tu obtiens dans Notion

Page **SEO Tracking** → https://app.notion.com/p/3c798ae1fbe080f7882aed48efb94975

| Base | Contenu | Lien |
|------|---------|------|
| **SEO — Articles** | 1 ligne par article : vues, temps moyen, conversions, clics, impressions, position moyenne, nombre de mots-clés, meilleur mot-clé | https://app.notion.com/p/c0b3d33bb3464831ae1575a96cd8f585 |
| **SEO — Mots-clés** | **Le listing complet** : 1 ligne par couple *mot-clé × article*, avec clics, impressions, CTR et position | https://app.notion.com/p/5ff559cab4b64fe5b6af9235a3f31e9c |

Les deux bases sont reliées entre elles, et la base *Articles* peut être reliée
à ta base éditoriale existante **« Articles and Contents »**.

## D'où viennent les données (important)

> ⚠️ **GA4 ne fournit PAS les mots-clés de positionnement.** Les mots-clés,
> positions et impressions viennent de **Google Search Console**. GA4 ne sert
> qu'aux vues, au temps passé et aux conversions. L'outil combine les deux.

```
Google Search Console ──(mots-clés, position, clics, impressions)──┐
                                                                    ├──► fusion par URL ──► Notion
Google Analytics 4 ──────(vues, temps sur page, conversions)───────┘
```

---

## Mode « dashboard autonome » (sans Notion)

Si tu n'as pas encore les accès Notion, tu peux visualiser tes données dans un
**tableau de bord HTML autonome** — il ne dépend **que des accès Google**.

```bash
cd seo-tracker
pip install -r requirements.txt
python -m seo_tracker.report out          # -> out/dashboard.html + out/articles.csv + out/keywords.csv
```

Ouvre `out/dashboard.html` dans un navigateur : tuiles KPI, top articles, listing
complet des mots-clés (triable + recherche), quick wins (positions 5–15).

En automatique : le workflow **`.github/workflows/seo-dashboard.yml`** (quotidien +
manuel) génère le dashboard et le publie comme **artefact téléchargeable** dans
l'onglet *Actions → le run → Artifacts*. Il ne requiert que les secrets
`GOOGLE_CREDENTIALS_JSON`, `GSC_SITE_URL`, `GA4_PROPERTY_ID`.

> Le dashboard et la synchro Notion partagent la même collecte de données : quand
> les accès Notion seront prêts, active simplement le workflow *SEO Tracker*.

## Inventaire complet des articles via Framer (optionnel mais recommandé)

Google Search Console ne liste **que les pages ayant eu des impressions**. Pour
voir **TOUS** les articles publiés (y compris ceux sans trafic — justement ceux
à travailler), on utilise **Framer comme source d'inventaire** (Server API).

1. Dans Framer : réglages du projet → génère un **token API** (plan payant requis).
2. Trouve les **IDs de collections** et la structure des items :
   ```bash
   FRAMER_API_TOKEN=... python -m seo_tracker.framer
   ```
   (ou lance le workflow **Framer Probe** dans GitHub Actions et lis les logs).
3. Renseigne `FRAMER_COLLECTIONS` avec le mapping `id=prefixe`, ex. :
   `FRAMER_COLLECTIONS=col_news=/news,col_blog=/blog,col_cases=/use-case`
4. Ajuste si besoin `FRAMER_SLUG_FIELD` / `FRAMER_TITLE_FIELD` selon tes champs.

Résultat : chaque article de l'inventaire apparaît dans le dashboard/Notion, avec
ses métriques GSC+GA4 (ou 0 s'il n'a pas encore de trafic) et son vrai titre.
Sans token Framer, l'outil retombe sur le mode piloté par Search Console.

## Installation (à faire une fois)

### 1. Google Cloud — compte de service

1. Va sur https://console.cloud.google.com/ → crée (ou choisis) un projet.
2. **APIs & Services → Library** : active **Google Search Console API** *et*
   **Google Analytics Data API**.
3. **APIs & Services → Credentials → Create credentials → Service account**.
   Donne-lui un nom (ex. `seo-tracker`).
4. Sur le compte de service créé → onglet **Keys → Add key → JSON**.
   Un fichier `.json` se télécharge : **c'est la clé** (à garder secrète).
5. Note l'**email** du compte de service (ex. `seo-tracker@ton-projet.iam.gserviceaccount.com`).

### 2. Donner accès à ce compte de service

- **Search Console** (https://search.google.com/search-console) → propriété
  *dillygence.com* → **Paramètres → Utilisateurs et autorisations → Ajouter** →
  colle l'email du compte de service, rôle **Restreint** (lecture) suffit.
- **GA4** (https://analytics.google.com) → **Admin → Gestion des accès à la
  propriété → +** → ajoute le même email, rôle **Lecteur**.
- Récupère l'**ID de propriété GA4** : *Admin → Paramètres de la propriété* →
  un nombre type `123456789`.

### 3. Notion — intégration

1. Va sur https://www.notion.so/my-integrations → **New integration** (interne).
   Copie le **token** (`ntn_...` / `secret_...`).
2. Ouvre chaque base (**SEO — Articles** et **SEO — Mots-clés**) → menu `•••`
   en haut à droite → **Connexions → Connecter à** → choisis ton intégration.
   *(Sans ce partage, le script ne peut pas écrire dans les bases.)*

### 4. Fournir les secrets

**En local** : copie `.env.example` en `.env` et remplis les valeurs.

**En automatique (GitHub Actions, recommandé)** : dans le repo GitHub,
**Settings → Secrets and variables → Actions**.

*Secrets* (onglet « Secrets ») :

| Secret | Valeur |
|--------|--------|
| `GOOGLE_CREDENTIALS_JSON` | tout le contenu du fichier `.json` de la clé |
| `GSC_SITE_URL` | `sc-domain:dillygence.com` (propriété Domaine) ou `https://dillygence.com/` (préfixe d'URL) |
| `GA4_PROPERTY_ID` | l'ID numérique GA4 |
| `NOTION_TOKEN` | le token de l'intégration Notion |
| `NOTION_DB_ARTICLES` | `c0b3d33b-b346-4831-ae15-75a96cd8f585` |
| `NOTION_DB_KEYWORDS` | `5ff559ca-b4b6-4fe5-b6af-9235a3f31e9c` |

*Variables* (onglet « Variables », optionnel — ajuste le comportement) :
`ARTICLE_URL_REGEX`, `LOOKBACK_DAYS`, `MIN_IMPRESSIONS`,
`MAX_KEYWORDS_PER_ARTICLE`, `PRUNE_STALE`.

---

## Lancer

**En local :**

```bash
cd seo-tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m seo_tracker.main
```

**En automatique :** le workflow `.github/workflows/seo-tracker.yml` tourne
tous les jours à 06:00 UTC. Tu peux aussi le déclencher à la main depuis
l'onglet **Actions → SEO Tracker → Run workflow**.

---

## Configuration

| Variable | Défaut | Rôle |
|----------|--------|------|
| `GSC_SITE_URL` | — | Propriété Search Console (`sc-domain:...` ou URL) |
| `GA4_PROPERTY_ID` | — | ID numérique de la propriété GA4 |
| `LOOKBACK_DAYS` | `28` | Fenêtre d'analyse glissante (en jours) |
| `ARTICLE_URL_REGEX` | *(vide)* | Filtre les URLs considérées comme articles (ex. `/blog/`). Vide = tout inclure |
| `MIN_IMPRESSIONS` | `1` | Seuil d'impressions pour retenir un mot-clé |
| `MAX_KEYWORDS_PER_ARTICLE` | `0` | Limite de mots-clés par article (0 = illimité) |
| `PRUNE_STALE` | `false` | Archive dans Notion les lignes qui ne remontent plus |

> **Astuce filtrage** : au premier lancement, laisse `ARTICLE_URL_REGEX` vide
> pour voir toutes les pages qui rankent. Une fois la structure d'URL du blog
> connue (ex. `/blog/`), renseigne-la pour ne garder que les articles.

---

## Détails techniques

- **Position moyenne par article** : moyenne des positions *pondérée par les
  impressions* (plus représentative qu'une moyenne simple).
- **Temps moyen sur page** : `userEngagementDuration / vues` (approximation GA4).
- **Jointure GSC ↔ GA4** : sur le **chemin d'URL normalisé** (sans query string,
  sans slash final).
- **Latence GSC** : la fenêtre s'arrête à J-3 (données consolidées).
- **Idempotent** : ré-exécuter met à jour les lignes existantes (clé = URL pour
  les articles, couple *mot-clé + URL* pour les mots-clés).

## Suites possibles (non incluses en v1)

- **Phase 2 — Recherche de mots-clés** pour de nouveaux articles
  (Google Ads Keyword Planner API, ou outil type Ahrefs/SEMrush).
- **Phase 3 — Publication vers Framer** (API CMS Framer) depuis Notion.
- **Funnels / parcours** de conversion (exploration GA4 approfondie).
- **Analyse concurrentielle** (autres sites positionnés sur les mêmes mots-clés)
  — nécessite un outil tiers, non disponible via Google seul.
