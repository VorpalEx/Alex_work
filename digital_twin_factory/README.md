# Digital Twin Factory

> Écosystème logiciel Parent/Enfant pour la modélisation et le monitoring de jumeaux numériques d'entreprise.

## Architecture

```
digital_twin_factory/
├── shared_logic/           # Modèles de données et utilitaires partagés
│   ├── models.py           # Dataclasses : TwinModel, GraphNode, AnomalyEvent…
│   ├── graph_schema.py     # Sérialisation JSON ↔ NetworkX
│   └── crypto.py           # AES-256-GCM + PBKDF2 pour la base auth SQLite
│
├── parent/                 # LOGICIEL PARENT — Builder (L'Usine)
│   ├── main.py             # Point d'entrée PyQt6
│   ├── core/
│   │   ├── pdf_processor.py    # Ingestion PDF via LangChain + heuristiques
│   │   ├── graph_builder.py    # CRUD sur le graphe NetworkX
│   │   ├── saas_connector.py   # Connecteurs Zapier / Make / n8n
│   │   └── build_engine.py     # Pipeline PyInstaller → .exe enfant
│   └── ui/
│       ├── main_window.py      # Fenêtre principale (4 onglets)
│       ├── pdf_ingestion_panel.py
│       ├── saas_config_panel.py
│       ├── graph_view_panel.py
│       ├── build_panel.py
│       └── styles.py           # Dark mode industriel partagé
│
├── child_template/         # LOGICIEL ENFANT — Sentinel (La Tour de Contrôle)
│   ├── main.py             # Point d'entrée (lit config.json injecté)
│   ├── config.json         # Remplacé lors du build par l'Usine
│   ├── core/
│   │   ├── monitoring_engine.py   # Thread T-1min : poll SaaS vs SLA
│   │   ├── anomaly_detector.py    # Log + déduplication des anomalies
│   │   ├── simulation_engine.py   # Analyse what-if (désactivation nœuds)
│   │   └── auth_manager.py        # RBAC SQLite chiffré (ADMIN/OPERATOR/ANALYST)
│   └── ui/
│       ├── main_window.py         # Fenêtre principale (3 onglets)
│       ├── login_dialog.py        # Dialog d'authentification
│       ├── graph_view.py          # Vue graphe temps réel (clignotement anomalies)
│       ├── monitoring_panel.py    # KPIs + graphe live
│       ├── anomaly_panel.py       # Tableau historique anomalies
│       └── simulation_panel.py    # Interface what-if
│
└── scripts/
    └── build_child.py      # CLI pour générer le .exe depuis un config.json
```

## Flux de travail

### Phase 1 — Modélisation (Parent)
1. Lancer le Parent : `python -m digital_twin_factory.parent.main`
2. **Onglet 1** : Importer un PDF → extraction automatique des étapes + SLAs
3. **Onglet 2** : Configurer les clés API Zapier / Make / n8n + mapper les nœuds
4. **Onglet 3** : Visualiser et ajuster le graphe du jumeau
5. **Onglet 4** : Cliquer "Générer .exe Enfant" → `DigitalTwin_<Entreprise>.exe` produit

### Phase 2 — Monitoring (Enfant / Sentinel)
1. Livrer l'`.exe` à l'entreprise cliente
2. L'application démarre avec un écran de connexion (RBAC)
3. **Onglet 1** : Monitoring en temps réel (T-1min), noeuds clignotants en rouge si anomalie
4. **Onglet 2** : Historique des anomalies détectées
5. **Onglet 3** *(ANALYST/ADMIN)* : Simuler des scénarios what-if

## Installation

```bash
# Cloner le dépôt
cd digital_twin_factory
pip install -r requirements.txt

# Lancer le Parent (Builder)
python -m digital_twin_factory.parent.main

# Lancer le Sentinel en mode dev (avec config.json de démo)
python -m digital_twin_factory.child_template.main

# Build CLI (sans UI)
python -m digital_twin_factory.scripts.build_child \
    --config path/to/config.json \
    --output ./dist/
```

## Sécurité

- La base de données auth (`auth.db`) utilise **AES-256-GCM** via la librairie `cryptography`.
- Les mots de passe sont stockés sous forme de hash **PBKDF2-HMAC-SHA256** avec sel aléatoire.
- Un compte `admin / admin1234` est créé automatiquement au premier démarrage — **à changer immédiatement en production**.

## Rôles RBAC

| Rôle     | Monitoring | Anomalies | Simulateur | Config seuils |
|----------|:----------:|:---------:|:----------:|:-------------:|
| ADMIN    | ✓          | ✓         | ✓          | ✓             |
| OPERATOR | ✓          | ✓         | ✗          | ✗             |
| ANALYST  | ✓          | ✓         | ✓          | ✗             |

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.11 (typage fort) |
| UI | PyQt6 — Dark Mode industriel |
| IA / RAG | LangChain + PyPDF |
| Graphe | NetworkX |
| SaaS | REST (Zapier / Make / n8n) |
| Sécurité | cryptography (AES-256-GCM) + SQLite |
| Packaging | PyInstaller |
