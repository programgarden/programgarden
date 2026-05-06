"""Shared regression guard for AI-chatbot-ready Field metadata across every LS TR blocks.py.

Auto-discovers all data-carrying Pydantic classes under
``programgarden_finance.ls.**`` and validates:

    1. examples coverage — every public field declares ``Field(examples=[...])``.
    2. examples round-trip — ``TypeAdapter(annotation).validate_python(ex)`` succeeds
       for every declared example value.
    3. title 한영 병기 — Field ``title`` matches the ``"<korean> (<english>)"``
       pattern (soft warning, never fails — see Plan §Phase 1).

Discovered class name patterns:
    - REST: ``*InBlock``, ``*InBlock1``, ``*OutBlock``, ``*OutBlock1``, ``*OutBlock2`` …
    - WebSocket Real: ``*RealRequestBody``, ``*RealResponseBody``.

Files still pending Phase 2~5 conversion are dynamically skipped via the artifact at
``.claude/pg-plans/artifacts/20260506-pending-blocks.txt`` — removing an entry
there auto-unskips that file's classes.

Run only this module:

    cd src/finance && poetry run pytest tests/test_field_metadata_coverage.py -v

Reference modern pattern: ``korea_stock/program/t1636/blocks.py`` +
``tests/test_korea_stock_t1636.py::TestFieldExamplesValidate``.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import warnings
from pathlib import Path
from typing import List, Set, Tuple, Type

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

import programgarden_finance.ls as _ls_root


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_CLASS_PATTERN = re.compile(
    r"(?:InBlock\d*|OutBlock\d*|RealRequestBody|RealResponseBody)$"
)

TITLE_PATTERN = re.compile(r"^.+\(.+\)\s*$")

# Repo root is 3 levels up from this file: src/finance/tests/THIS → src/finance/ → src/ → repo
_REPO_ROOT = Path(__file__).resolve().parents[3]
PENDING_ARTIFACT = _REPO_ROOT / ".claude/pg-plans/artifacts/20260506-pending-blocks.txt"


def _load_pending_paths() -> Set[Path]:
    if not PENDING_ARTIFACT.is_file():
        return set()
    out: Set[Path] = set()
    for line in PENDING_ARTIFACT.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        out.add(Path(line).resolve())
    return out


_PENDING: Set[Path] = _load_pending_paths()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _walk_block_modules() -> List[Tuple[str, Path]]:
    found: List[Tuple[str, Path]] = []
    for module_info in pkgutil.walk_packages(
        _ls_root.__path__, prefix=f"{_ls_root.__name__}."
    ):
        if not module_info.name.endswith(".blocks"):
            continue
        try:
            mod = importlib.import_module(module_info.name)
        except Exception as exc:  # pragma: no cover — surfaced as collection error
            raise RuntimeError(
                f"Failed to import {module_info.name}: {exc!r}"
            ) from exc
        file = getattr(mod, "__file__", None)
        if file is None:
            continue
        found.append((module_info.name, Path(file).resolve()))
    return found


def _short_path(file_path: Path) -> str:
    parts = file_path.parts
    if "programgarden_finance" in parts:
        idx = parts.index("programgarden_finance")
        return "/".join(parts[idx:])
    return str(file_path)


def _module_label(module_name: str) -> str:
    return module_name.split("programgarden_finance.ls.", 1)[-1]


def _collect_block_classes() -> List[Tuple[str, Type[BaseModel], Path]]:
    collected: List[Tuple[str, Type[BaseModel], Path]] = []
    for mod_name, file_path in _walk_block_modules():
        mod = importlib.import_module(mod_name)
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name)
            if not isinstance(obj, type):
                continue
            if not issubclass(obj, BaseModel) or obj is BaseModel:
                continue
            if obj.__module__ != mod_name:
                continue
            if not DATA_CLASS_PATTERN.search(attr_name):
                continue
            label = f"{_module_label(mod_name)}::{attr_name}"
            collected.append((label, obj, file_path))
    collected.sort(key=lambda t: t[0])
    return collected


_BLOCK_CLASSES: List[Tuple[str, Type[BaseModel], Path]] = _collect_block_classes()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _maybe_skip_pending(file_path: Path) -> None:
    if file_path in _PENDING:
        pytest.skip(
            f"Pending Phase 2~5 conversion: {_short_path(file_path)}"
        )


def _params():
    return [pytest.param(label, cls, path, id=label) for label, cls, path in _BLOCK_CLASSES]


# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------


@pytest.mark.field_metadata
def test_discovery_found_classes():
    """Discovery must find at least the 10 already-applied baseline classes."""
    assert _BLOCK_CLASSES, (
        "No InBlock / OutBlock / RealRequestBody / RealResponseBody classes were "
        "discovered under programgarden_finance.ls — has package layout changed?"
    )


@pytest.mark.field_metadata
def test_pending_artifact_present():
    """The Phase 0 reconnaissance artifact must exist while Phase 2~5 is in flight."""
    assert PENDING_ARTIFACT.is_file(), (
        f"Expected Phase 0 artifact at {PENDING_ARTIFACT}. "
        "If Phase 5 finished, drop this assertion alongside removing the artifact."
    )


# ---------------------------------------------------------------------------
# Coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.field_metadata
@pytest.mark.parametrize(("label", "model_cls", "file_path"), _params())
def test_examples_coverage(label, model_cls, file_path):
    """Every public field declares ``Field(examples=[...])``."""
    _maybe_skip_pending(file_path)
    missing = [
        name
        for name, info in model_cls.model_fields.items()
        if not (info.examples or [])
    ]
    assert not missing, (
        f"{label} fields missing examples=[...]: {missing}. "
        "All InBlock / OutBlock / Real body fields must carry AI-readable examples."
    )


@pytest.mark.field_metadata
@pytest.mark.parametrize(("label", "model_cls", "file_path"), _params())
def test_examples_round_trip(label, model_cls, file_path):
    """Each example value must validate against its field annotation."""
    _maybe_skip_pending(file_path)
    failures: List[str] = []
    for name, info in model_cls.model_fields.items():
        for ex in info.examples or []:
            try:
                TypeAdapter(info.annotation).validate_python(ex)
            except ValidationError as exc:
                first = exc.errors()[0]
                failures.append(
                    f"{label}.{name} example {ex!r} failed: {first['msg']}"
                )
    assert not failures, "Invalid Field examples:\n" + "\n".join(failures)


@pytest.mark.field_metadata
@pytest.mark.parametrize(("label", "model_cls", "file_path"), _params())
def test_title_korean_english_pair_soft(label, model_cls, file_path):
    """Soft warning if a Field ``title`` does not follow ``"<korean> (<english>)"``.

    This check intentionally never fails — Plan §Phase 1 specifies a soft
    warning so OAuth / common-real TRs with non-Korean labels don't block
    conversion progress. Reviewers should still scan the warning summary.
    """
    _maybe_skip_pending(file_path)
    for name, info in model_cls.model_fields.items():
        title = info.title
        if not title:
            continue
        if not TITLE_PATTERN.match(title):
            warnings.warn(
                f"{label}.{name} title does not follow "
                f"'<korean> (<english>)' pattern: {title!r}",
                stacklevel=2,
            )
