"""Regression guard for SetupOptions rate_limit_key + on_rate_limit coverage.

Scans every ``blocks.py`` under ``programgarden_finance/ls/`` and asserts that
every ``SetupOptions(...)`` literal declares ``rate_limit_key`` (so multiple
client instances of the same TR share a single rate limit counter) and
``on_rate_limit="wait"`` (so the client throttles instead of raising on
overflow).

Rationale (2026-05-12 AlphaWorks report): t8452 and 10 other Korea Stock TRs
shipped with bare ``SetupOptions(rate_limit_count=1, rate_limit_seconds=1)``,
defaulting ``on_rate_limit`` to ``"stop"`` and leaving ``rate_limit_key``
unset. Independent instances each held their own counter, allowing the
real LS server to be flooded with the per-TR limit × N concurrent callers,
producing ``IGW00201`` (호출 거래건수 초과 / HTTP 500) on legitimate workloads
(e.g. 45-symbol minute-bar polling).

This test fails CI if a new TR adds ``SetupOptions(...)`` without one of
the two required fields. To add a new TR safely, follow the t8451 pattern::

    options: SetupOptions = SetupOptions(
        rate_limit_count=...,
        rate_limit_seconds=...,
        on_rate_limit="wait",
        rate_limit_key="<tr_id>",
    )
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest

import programgarden_finance.ls as _ls_root


_LS_ROOT = Path(_ls_root.__file__).parent
_SETUP_RE = re.compile(r"SetupOptions\((.*?)\)", re.DOTALL)


def _iter_blocks_py() -> List[Path]:
    return sorted(_LS_ROOT.rglob("blocks.py"))


def _setup_options_literals(text: str) -> List[str]:
    """Return every SetupOptions(...) literal body found in the source text."""
    return _SETUP_RE.findall(text)


def test_blocks_py_discovery_nonzero():
    """Sanity: discovery must find blocks.py files (catches sys.path / refactor regressions)."""
    files = _iter_blocks_py()
    assert len(files) > 50, f"Expected many blocks.py under {_LS_ROOT}, found {len(files)}"


def test_every_setup_options_declares_rate_limit_key():
    """Every SetupOptions(...) literal must set rate_limit_key.

    Without rate_limit_key, parallel client instances of the same TR each
    maintain an independent counter and flood the LS server.
    """
    offenders: List[str] = []
    for path in _iter_blocks_py():
        text = path.read_text(encoding="utf-8")
        for literal in _setup_options_literals(text):
            if "rate_limit_key" not in literal:
                rel = path.relative_to(_LS_ROOT)
                offenders.append(f"{rel}: SetupOptions(...) missing rate_limit_key")
                break

    if offenders:
        msg = "\n  ".join([
            "The following blocks.py files declare SetupOptions(...) without",
            "rate_limit_key. Add rate_limit_key=\"<tr_id>\" (matches the TR's",
            "directory name) so parallel client instances share one counter.",
            "",
            *offenders,
        ])
        pytest.fail(msg)


def test_every_setup_options_uses_on_rate_limit_wait():
    """Every SetupOptions(...) literal must set on_rate_limit="wait".

    The SetupOptions default is "stop" (raise on overflow). For library-side
    rate limiting to actually throttle calls instead of surfacing transient
    errors to the caller, "wait" is required.
    """
    offenders: List[str] = []
    for path in _iter_blocks_py():
        text = path.read_text(encoding="utf-8")
        for literal in _setup_options_literals(text):
            if 'on_rate_limit="wait"' not in literal and "on_rate_limit='wait'" not in literal:
                rel = path.relative_to(_LS_ROOT)
                offenders.append(f"{rel}: SetupOptions(...) missing on_rate_limit=\"wait\"")
                break

    if offenders:
        msg = "\n  ".join([
            "The following blocks.py files declare SetupOptions(...) without",
            "on_rate_limit=\"wait\". The default (\"stop\") raises on overflow",
            "instead of throttling — set on_rate_limit=\"wait\" to honor the",
            "rate_limit_count/seconds you specified.",
            "",
            *offenders,
        ])
        pytest.fail(msg)
