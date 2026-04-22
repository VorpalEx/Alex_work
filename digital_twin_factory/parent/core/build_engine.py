"""
Build Engine: clones the child_template, injects config.json,
then invokes PyInstaller to produce a standalone .exe.
"""
from __future__ import annotations

import datetime
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from ...shared_logic.graph_schema import twin_to_dict
from ...shared_logic.models import TwinModel


# Root of the whole project
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CHILD_TEMPLATE = _PROJECT_ROOT / "digital_twin_factory" / "child_template"
_DIST_BASE = _PROJECT_ROOT / "dist"


class BuildEngine:
    """
    Orchestrates:
    1. Copying child_template to a build workspace.
    2. Injecting config.json.
    3. Running PyInstaller.
    """

    def __init__(
        self,
        model: TwinModel,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.model = model
        self.output_dir: Path = output_dir or _DIST_BASE
        self.progress = progress_callback or (lambda msg: print(msg))

    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        self.progress(msg)

    # ------------------------------------------------------------------
    def _workspace_path(self) -> Path:
        safe_name = self.model.company_name.replace(" ", "_").lower() or "client"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return _DIST_BASE / f"build_{safe_name}_{ts}"

    # ------------------------------------------------------------------
    def _copy_template(self, workspace: Path) -> None:
        self._log(f"[1/4] Copie du template enfant vers {workspace} …")
        if workspace.exists():
            shutil.rmtree(workspace)
        shutil.copytree(_CHILD_TEMPLATE, workspace)

    # ------------------------------------------------------------------
    def _inject_config(self, workspace: Path) -> None:
        self._log("[2/4] Injection de config.json …")
        config_data = twin_to_dict(self.model)
        config_data["build_timestamp"] = datetime.datetime.now().isoformat()
        config_path = workspace / "config.json"
        config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    def _run_pyinstaller(self, workspace: Path) -> Path:
        self._log("[3/4] Lancement de PyInstaller …")
        safe_name = self.model.company_name.replace(" ", "_") or "Sentinel"
        exe_name = f"DigitalTwin_{safe_name}"
        spec_path = workspace / "build.spec"

        spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['{(workspace / "main.py").as_posix()}'],
    pathex=['{workspace.as_posix()}'],
    binaries=[],
    datas=[
        ('{(workspace / "config.json").as_posix()}', '.'),
        ('{(workspace / "assets").as_posix()}', 'assets'),
    ],
    hiddenimports=['PyQt6', 'networkx', 'requests', 'cryptography'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""
        spec_path.write_text(spec_content, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", str(spec_path)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"PyInstaller a échoué:\n{result.stderr}")

        # Locate the produced binary
        dist_dir = workspace / "dist"
        suffix = ".exe" if platform.system() == "Windows" else ""
        binary = dist_dir / f"{exe_name}{suffix}"
        return binary

    # ------------------------------------------------------------------
    def _copy_output(self, binary: Path, workspace: Path) -> Path:
        self._log("[4/4] Déplacement du binaire vers le dossier de sortie …")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        dest = self.output_dir / binary.name
        shutil.copy2(binary, dest)
        self._log(f"[OK] Executable produit : {dest}")
        return dest

    # ------------------------------------------------------------------
    def build(self) -> Path:
        """Run the full build pipeline. Returns path to the produced binary."""
        workspace = self._workspace_path()
        try:
            self._copy_template(workspace)
            self._inject_config(workspace)
            binary = self._run_pyinstaller(workspace)
            final = self._copy_output(binary, workspace)
            return final
        except Exception as exc:
            self._log(f"[ERREUR] Build échoué: {exc}")
            raise
