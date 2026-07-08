"""CodeNode subprocess isolation — fixed worker pool (Layer 4).

CodeNode runs untrusted Python. This module always executes that code in a
**credential-free child process** so it can never touch the parent's in-memory
app keys, broker sessions, or token cache. Design constraints (plan §2 Layer 4):

  * ALWAYS on — there is no public switch to run CodeNode in-process. The only
    exception is a no-spawn environment (some serverless/embedded runtimes),
    where a loudly-warned in-process fallback runs (Layers 1-3 still hold).
  * Fixed, long-lived worker pool (spawn start method) — NOT spawn-per-exec, to
    avoid K8s OOMKill / per-call memory churn.
  * 🔴 Contract 1 (isolation integrity): the child receives only a scrubbed,
    credential-free snapshot (data/params/ctx_snapshot). App keys, broker, and
    session objects are never serialized into the task.
  * 🔴 Contract 2 (safe deserialization): the child returns a JSON **string**
    only. The parent json-loads it — it never unpickles an arbitrary object
    graph from the untrusted child (which would be an RCE back into the parent).
  * Fresh exec namespace every run (no cross-CodeNode state leak); the process
    is reused, the namespace is not. Crash/timeout → kill + respawn.
  * auto-iterate is batched: CodeNode receives the whole upstream array in
    `data` and loops in-code, so N items = one IPC round-trip, not N.

⚠️ Residual risk (be honest): the child is a plain spawn subprocess. It does not
inherit the parent's memory (app keys live only in the parent), and this module
scrubs secret-looking env vars from the child. But a Python-level sandbox escape
that reaches the OS could still read world-readable files (mount a per-user pod
and keep secrets like `sandbox/secret.env` out of it / restrict file perms) or
open the network (apply a no-egress NetworkPolicy). True containment of hostile
code is an OS/infra concern (namespaces, seccomp, egress policy), not something
this pool guarantees. The AST screen (core) is hardened defense-in-depth.

All user-facing error envelopes are English (chatbot consumer contract).
"""
from __future__ import annotations

import json
import logging
import multiprocessing
import os
import queue
import threading
import traceback
from typing import Any, Dict, List, Optional

logger = logging.getLogger("programgarden.code_worker")

# Per-call wall-clock limit (infinite-loop guard). Overridable via env.
_DEFAULT_TIMEOUT_SEC = float(os.environ.get("PG_CODE_NODE_TIMEOUT", "30"))
# Fixed pool size. Small by default (memory bound, not a parallelism win under
# a shared pod CPU quota). Overridable via env.
_DEFAULT_WORKERS = max(1, int(os.environ.get("PG_CODE_NODE_WORKERS", "2")))


# ─────────────────────────────────────────────────────────────────────────
# Child side
# ─────────────────────────────────────────────────────────────────────────

class _SandboxedContext:
    """Read-only context handed to CodeNode `execute(data, params, context)`.

    Exposes ONLY safe helper namespaces (mirroring expression bindings), a
    risk-tracker read snapshot, and non-secret workflow meta. It deliberately
    has NO get_credential / _secrets / broker / executor — the credential
    access path simply does not exist here (structural capability removal), and
    the process itself holds no app keys anyway.
    """

    __slots__ = ("date", "finance", "stats", "format", "lst", "_risk",
                 "job_id", "dry_run", "iteration_index", "iteration_total")

    def __init__(self, snapshot: Dict[str, Any]):
        from programgarden_core.expression.evaluator import (
            DateNamespace, FinanceNamespace, StatsNamespace,
            FormatNamespace, ListNamespace,
        )
        self.date = DateNamespace()
        self.finance = FinanceNamespace()
        self.stats = StatsNamespace()
        self.format = FormatNamespace()
        self.lst = ListNamespace()
        self._risk: Dict[str, Any] = snapshot.get("risk", {}) or {}
        self.job_id = snapshot.get("job_id")
        self.dry_run = bool(snapshot.get("dry_run", False))
        self.iteration_index = int(snapshot.get("iteration_index", 0) or 0)
        self.iteration_total = int(snapshot.get("iteration_total", 0) or 0)

    def get_hwm(self, symbol: str) -> Optional[float]:
        """High-water-mark price for a symbol (read-only snapshot), or None."""
        return (self._risk.get("hwm", {}) or {}).get(symbol, {}).get("hwm_price")

    def get_drawdown(self, symbol: str) -> Optional[float]:
        """Current drawdown % for a symbol (read-only snapshot), or None."""
        return (self._risk.get("hwm", {}) or {}).get(symbol, {}).get("drawdown_pct")

    def risk_snapshot(self) -> Dict[str, Any]:
        """Full read-only risk snapshot (copy)."""
        return dict(self._risk)


def _error_envelope(error_code: str, message: str, *, suggestion: Optional[str] = None,
                    line: Optional[int] = None, tb: Optional[str] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error_code": error_code,
        "message": message,
        "suggestion": suggestion,
        "line": line,
        "traceback": tb,
    }


def _run_one(task: Dict[str, Any], compile_cache: Dict[int, Any]) -> str:
    """Execute one CodeNode task inside the child; return a JSON envelope string.

    NEVER returns a Python object across the pipe (Contract 2) — always a str.
    """
    import inspect

    code = task["code"]
    node_id = task["node_id"]
    data = task.get("data")
    params = task.get("params") or {}
    ctx_snapshot = task.get("ctx_snapshot") or {}
    allowed_imports = set(task.get("allowed_imports") or [])

    from programgarden_core.code_node import compile_code_node, build_restricted_builtins

    # Compile (cached per worker by the FULL source string — never hash(code),
    # which can collide and return a wrong, never-re-screened code object).
    # Screen again here — the worker is the last line before exec, and the
    # share-gate reuses the same scanner, so double-screening is cheap.
    if len(compile_cache) > 256:
        compile_cache.clear()  # bound memory across many distinct sources
    key = code
    code_object = compile_cache.get(key)
    if code_object is None:
        screen = compile_code_node(code, node_id, screen=True,
                                   allowed_imports=allowed_imports or None)
        if not screen.ok:
            return json.dumps(_error_envelope(
                screen.error_code or "CODE_NODE_SYNTAX_ERROR",
                screen.message or "CodeNode failed to compile",
                suggestion=screen.suggestion, line=screen.line,
            ))
        code_object = screen.code_object
        compile_cache[key] = code_object

    # Fresh namespace every run → no state leak between CodeNode executions.
    restricted = build_restricted_builtins(allowed_imports or None)
    g: Dict[str, Any] = {"__builtins__": restricted, "__name__": "__code_node__"}

    try:
        exec(code_object, g)  # noqa: S102 — sandboxed: restricted builtins + AST-screened
    except Exception:
        return json.dumps(_error_envelope(
            "CODE_NODE_EXEC_ERROR",
            "CodeNode module-level code raised during import.",
            suggestion="Move side-effecting logic inside execute(); keep module level to defs/imports.",
            tb=_short_tb(),
        ))

    fn = g.get("execute")
    if fn is None or not callable(fn):
        return json.dumps(_error_envelope(
            "CODE_NODE_NO_EXECUTE",
            "CodeNode code must define a callable named 'execute'.",
            suggestion="Define async def execute(data, params, context):",
        ))

    context = _SandboxedContext(ctx_snapshot)

    try:
        result = fn(data, params, context)
        if inspect.iscoroutine(result):
            import asyncio
            result = asyncio.run(result)
        elif inspect.isawaitable(result):
            import asyncio

            async def _await_any(x):
                return await x

            result = asyncio.run(_await_any(result))
    except Exception:
        return json.dumps(_error_envelope(
            "CODE_NODE_EXEC_ERROR",
            "CodeNode execute() raised an exception.",
            suggestion="Fix the runtime error shown in the traceback.",
            tb=_short_tb(),
        ))

    # Contract 2: serialize the raw return to JSON here. `allow_nan=False`
    # rejects NaN/Infinity (which json.dumps would otherwise emit as invalid
    # `NaN`/`Infinity` tokens that quietly round-trip) — surface a clear
    # structured error rather than silently passing a bad value.
    try:
        return json.dumps({"ok": True, "value": result}, allow_nan=False)
    except (TypeError, ValueError):
        return json.dumps(_error_envelope(
            "CODE_NODE_EXEC_ERROR",
            "CodeNode return value is not JSON-serializable (custom object, set, datetime, or NaN/Infinity).",
            suggestion="Return only finite JSON-safe data (dict/list/str/number/bool/None).",
        ))


def _short_tb(limit: int = 6) -> str:
    """Traceback tail with the worker frames trimmed for a readable summary."""
    tb = traceback.format_exc()
    lines = tb.strip().splitlines()
    if len(lines) > limit * 2:
        lines = lines[:2] + ["    ..."] + lines[-(limit * 2):]
    return "\n".join(lines)


# Env var name fragments that likely carry secrets. Scrubbed from the child's
# environment at startup so an in-child escape cannot read app keys / tokens
# from os.environ (blast-radius reduction — NOT a containment guarantee; file
# and network access still require OS-level isolation at the infra layer).
_SECRET_ENV_FRAGMENTS = (
    "SECRET", "TOKEN", "PASSWORD", "PASSWD", "APPKEY", "APPSECRET",
    "APP_KEY", "APP_SECRET", "PYPI", "CREDENTIAL", "PRIVATE", "API_KEY",
    "APIKEY", "ACCESS_KEY", "AUTH", "SESSION", "COOKIE", "AWS_", "GCP_",
    "AZURE_", "LS_",
)


def _scrub_child_env() -> None:
    """Delete secret-looking env vars in this (child) process. Best-effort."""
    for k in list(os.environ.keys()):
        ku = k.upper()
        if any(frag in ku for frag in _SECRET_ENV_FRAGMENTS):
            try:
                del os.environ[k]
            except Exception:
                pass


def _worker_main(conn, ready_evt=None) -> None:
    """Child entry point: loop reading tasks, exec, send back a JSON string."""
    _scrub_child_env()
    compile_cache: Dict[str, Any] = {}
    try:
        while True:
            try:
                task = conn.recv()
            except (EOFError, KeyboardInterrupt):
                break
            if task is None or (isinstance(task, dict) and task.get("cmd") == "shutdown"):
                break
            try:
                payload = _run_one(task, compile_cache)
            except Exception:
                # Last-resort guard — the worker must always reply with a str.
                payload = json.dumps(_error_envelope(
                    "CODE_NODE_EXEC_ERROR",
                    "CodeNode worker encountered an internal error.",
                    tb=_short_tb(),
                ))
            conn.send(payload)  # always a str (Contract 2)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────
# Parent side
# ─────────────────────────────────────────────────────────────────────────

class _Worker:
    __slots__ = ("proc", "conn")

    def __init__(self, proc, conn):
        self.proc = proc
        self.conn = conn


class CodeWorkerPool:
    """Fixed pool of long-lived spawn workers with a thread-safe free-list."""

    def __init__(self, num_workers: int = _DEFAULT_WORKERS):
        self._num = max(1, num_workers)
        self._ctx = multiprocessing.get_context("spawn")
        self._free: "queue.Queue[_Worker]" = queue.Queue()
        self._all: List[_Worker] = []
        self._lock = threading.Lock()
        self._started = False
        self._usable = True

    def _spawn_worker(self) -> _Worker:
        parent_conn, child_conn = self._ctx.Pipe(duplex=True)
        proc = self._ctx.Process(
            target=_worker_main, args=(child_conn,), daemon=True,
            name="pg-code-worker",
        )
        proc.start()
        # The parent keeps only its end of the pipe.
        try:
            child_conn.close()
        except Exception:
            pass
        return _Worker(proc, parent_conn)

    def start(self) -> bool:
        """Start the pool. Returns False if spawn is unavailable (→ fallback)."""
        with self._lock:
            if self._started:
                return self._usable
            try:
                for _ in range(self._num):
                    w = self._spawn_worker()
                    self._all.append(w)
                    self._free.put(w)
                self._started = True
                self._usable = True
                logger.info("CodeNode worker pool started (%d spawn workers)", self._num)
            except Exception as e:
                self._usable = False
                self._started = True
                logger.error("CodeNode worker pool failed to start: %s", e)
            return self._usable

    @property
    def usable(self) -> bool:
        return self._usable

    def _replace(self, worker: _Worker) -> None:
        """Terminate a dead/timed-out worker and put a fresh one on the free-list."""
        try:
            worker.proc.terminate()
        except Exception:
            pass
        try:
            worker.conn.close()
        except Exception:
            pass
        with self._lock:
            if worker in self._all:
                self._all.remove(worker)
            try:
                nw = self._spawn_worker()
                self._all.append(nw)
                self._free.put(nw)
            except Exception as e:
                logger.error("CodeNode worker respawn failed: %s", e)
                self._usable = False

    def run(self, task: Dict[str, Any], timeout: float = _DEFAULT_TIMEOUT_SEC) -> Dict[str, Any]:
        """Run one task on an idle worker (blocking). Returns an envelope dict.

        Enforces Contract 2 (payload must be a JSON string) and the per-call
        timeout (kill + respawn on overrun).
        """
        if not self._usable:
            return _error_envelope(
                "CODE_NODE_EXEC_ERROR",
                "CodeNode worker pool is not usable in this environment.",
                suggestion="Run in an environment that supports process spawning.",
            )
        # Acquire an idle worker with a bounded wait. A plain blocking get()
        # would deadlock a caller forever if a respawn failure has permanently
        # drained the free-list; time out into a structured error instead.
        acquire_timeout = timeout * 2 + 30
        try:
            worker = self._free.get(timeout=acquire_timeout)
        except queue.Empty:
            return _error_envelope(
                "CODE_NODE_EXEC_ERROR",
                "CodeNode worker pool is saturated or drained (no worker available).",
                suggestion="Reduce concurrent CodeNode load; a worker may have failed to respawn.",
            )
        try:
            worker.conn.send(task)
            if not worker.conn.poll(timeout):
                logger.warning("CodeNode '%s' timed out after %ss — restarting worker",
                               task.get("node_id"), timeout)
                self._replace(worker)
                return _error_envelope(
                    "CODE_NODE_EXEC_ERROR",
                    f"CodeNode timed out after {timeout:g}s.",
                    suggestion="Avoid unbounded loops / heavy work; the worker was restarted.",
                )
            payload = worker.conn.recv()
        except (EOFError, BrokenPipeError, OSError, ConnectionError):
            logger.warning("CodeNode '%s' worker crashed — restarting", task.get("node_id"))
            self._replace(worker)
            return _error_envelope(
                "CODE_NODE_EXEC_ERROR",
                "CodeNode worker process crashed.",
                suggestion="Check for native crashes / memory exhaustion in the code; the worker was restarted.",
            )

        # Contract 2 guard: we must only ever json.loads a string.
        if not isinstance(payload, str):
            self._replace(worker)
            return _error_envelope(
                "CODE_NODE_EXEC_ERROR",
                "CodeNode worker returned a non-JSON payload.",
                suggestion="Internal isolation error; the worker was restarted.",
            )
        self._free.put(worker)  # healthy → back to the pool
        try:
            return json.loads(payload)
        except (TypeError, ValueError):
            return _error_envelope(
                "CODE_NODE_EXEC_ERROR",
                "CodeNode worker returned malformed JSON.",
            )

    def shutdown(self) -> None:
        with self._lock:
            for w in self._all:
                try:
                    w.conn.send({"cmd": "shutdown"})
                except Exception:
                    pass
                try:
                    w.proc.terminate()
                except Exception:
                    pass
            self._all.clear()
            self._started = False


# ── Module singleton + high-level entry ────────────────────────────────────

_POOL: Optional[CodeWorkerPool] = None
_POOL_LOCK = threading.Lock()


def get_code_worker_pool() -> CodeWorkerPool:
    global _POOL
    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                _POOL = CodeWorkerPool()
                _POOL.start()
    return _POOL


def _run_in_process_fallback(task: Dict[str, Any]) -> Dict[str, Any]:
    """Layers 1-3 without the process boundary. Used ONLY when spawn is
    unavailable. Loudly warned — this is not a normal-path toggle."""
    logger.warning(
        "CodeNode '%s' running IN-PROCESS (spawn unavailable). Layers 1-3 "
        "(scrubbed context + restricted builtins + AST screen) still apply, but "
        "the subprocess memory boundary (Layer 4) is NOT active. Only expected "
        "on no-spawn runtimes.", task.get("node_id"),
    )
    cache: Dict[int, Any] = {}
    payload = _run_one(task, cache)
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return _error_envelope("CODE_NODE_EXEC_ERROR", "CodeNode returned malformed JSON.")


def run_code_node_sandboxed(
    *,
    code: str,
    node_id: str,
    data: Any,
    params: Dict[str, Any],
    ctx_snapshot: Dict[str, Any],
    allowed_imports: Optional[List[str]] = None,
    timeout: float = _DEFAULT_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """Run CodeNode code in the isolated worker pool (or in-process fallback).

    Returns an envelope dict:
      {"ok": True, "value": <raw return>}
      {"ok": False, "error_code": ..., "message": ..., "suggestion": ..., "line": ..., "traceback": ...}
    """
    task: Dict[str, Any] = {
        "code": code,
        "node_id": node_id,
        "data": data,
        "params": params or {},
        "ctx_snapshot": ctx_snapshot or {},
        "allowed_imports": list(allowed_imports) if allowed_imports else None,
    }
    pool = get_code_worker_pool()
    if pool.usable:
        return pool.run(task, timeout=timeout)
    return _run_in_process_fallback(task)
