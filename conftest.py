from __future__ import annotations

import sys
import types
from pathlib import Path


def _add_src_subdirectories_to_path(root: Path) -> None:
    src_root = root / "src"
    if not src_root.exists():
        return

    for subdir in src_root.iterdir():
        if not subdir.is_dir():
            continue
        resolved = str(subdir.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


def _ensure_art_module() -> None:
    if "art" in sys.modules:
        return
    art_module = types.ModuleType("art")

    def _noop_tprint(*_args, **_kwargs) -> None:
        return None

    art_module.tprint = _noop_tprint  # type: ignore[attr-defined]
    sys.modules["art"] = art_module


_PROJECT_ROOT = Path(__file__).resolve().parent
_add_src_subdirectories_to_path(_PROJECT_ROOT)
_ensure_art_module()
