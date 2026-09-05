"""
CLI automation script: build a Child .exe from an existing config.json.

Usage:
    python -m digital_twin_factory.scripts.build_child \
        --config path/to/config.json \
        --output /path/to/dist/

This is the script equivalent of clicking "Générer .exe Enfant" in the Parent UI.
Useful for CI/CD pipelines.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Digital Twin Factory — CLI Build")
    parser.add_argument("--config", required=True, help="Chemin vers config.json")
    parser.add_argument("--output", default=str(Path.home() / "DigitalTwin_Output"), help="Dossier de sortie")
    args = parser.parse_args()

    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from digital_twin_factory.shared_logic.graph_schema import load_twin_config
    from digital_twin_factory.parent.core.build_engine import BuildEngine

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERREUR] Fichier config introuvable : {config_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Chargement de la configuration : {config_path}")
    model = load_twin_config(config_path)
    print(f"Entreprise : {model.company_name}  |  Nœuds : {len(model.nodes)}")

    engine = BuildEngine(
        model,
        output_dir=Path(args.output),
        progress_callback=print,
    )
    binary = engine.build()
    print(f"\n[SUCCESS] Exécutable prêt : {binary}")


if __name__ == "__main__":
    main()
