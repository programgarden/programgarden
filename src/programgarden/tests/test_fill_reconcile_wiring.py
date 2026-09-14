"""재조정 주기 태스크가 실행기에 제대로 붙어 있는지.

순수 로직(test_fill_reconciler)과 별개로, **실제로 돌기는 하는가**를 본다. 붙이지 못하면
로직이 아무리 맞아도 원장은 계속 빈다.
"""
import asyncio
import types

import pytest

from programgarden.executor import BrokerNodeExecutor, WorkflowJob


class _Pos:
    def __init__(self, quantity, buy_price):
        self.quantity = quantity
        self.buy_price = buy_price


class _AcctTracker:
    def __init__(self, positions):
        self._positions = positions


@pytest.fixture(autouse=True)
def _clean_registry():
    """추적기 레지스트리는 BrokerNodeExecutor 의 **클래스 속성**(프로세스 전역)이다.
    테스트 간 누수를 막는다."""
    saved = dict(BrokerNodeExecutor._active_trackers)
    BrokerNodeExecutor._active_trackers.clear()
    yield
    BrokerNodeExecutor._active_trackers.clear()
    BrokerNodeExecutor._active_trackers.update(saved)


def _job(job_id="job-1"):
    """생성자를 타지 않고 재조정 관련 상태만 갖춘 최소 객체.

    🔴 `_active_trackers` 를 **여기서 만들지 않는다.** 종전 픽스처가
    `job._active_trackers = {}` 로 없는 속성을 지어내는 바람에, 실제로는
    `AttributeError: 'WorkflowJob' object has no attribute '_active_trackers'` 로
    매 주기 죽던 것을 prod 에서야 발견했다(2026-09-14). 테스트가 만든 세계에서만
    통과하는 코드였다.
    """
    job = WorkflowJob.__new__(WorkflowJob)
    job.job_id = job_id
    job._reconcile_task = None
    job.context = types.SimpleNamespace(_workflow_position_tracker=None)
    return job


def _register(job_id, node_id, entry):
    BrokerNodeExecutor._active_trackers[f"{job_id}_{node_id}"] = entry


# ── 계좌 스냅샷 ────────────────────────────────────────────────────────────

def test_snapshot_reads_quantity_and_avg_price():
    snap = WorkflowJob._account_positions_snapshot(
        _AcctTracker({"MARA": _Pos(1, 11.78), "NIO": _Pos(3, 4.19)})
    )
    assert snap == {"MARA": {"quantity": 1.0, "avg_price": 11.78},
                    "NIO": {"quantity": 3.0, "avg_price": 4.19}}


def test_empty_cache_is_unavailable_not_empty_holdings():
    """🔴 빈 dict 를 돌려주면 보유 중인 포지션이 전부 '밖에서 팔렸다' 로 기록된다."""
    assert WorkflowJob._account_positions_snapshot(_AcctTracker({})) is None
    assert WorkflowJob._account_positions_snapshot(types.SimpleNamespace()) is None


def test_unparsable_fields_do_not_crash_the_snapshot():
    snap = WorkflowJob._account_positions_snapshot(_AcctTracker({"X": _Pos("bad", "bad")}))
    assert snap == {"X": {"quantity": 0.0, "avg_price": None}}


# ── 추적기 선택 ────────────────────────────────────────────────────────────

def test_registry_lives_on_the_broker_executor_not_the_job():
    """이 결함의 정확한 형태 — WorkflowJob 에는 그 속성이 없다."""
    assert hasattr(BrokerNodeExecutor, "_active_trackers")
    assert not hasattr(WorkflowJob, "_active_trackers"), (
        "WorkflowJob 에 생기면 self._active_trackers 로 읽는 코드가 되살아난다"
    )


def test_picks_the_account_tracker_not_the_fill_subscription():
    job = _job()
    _register("job-1", "broker_fill_sub", {"type": "fill_subscription", "ls": object(), "real": object()})
    _register("job-1", "broker", {"type": "account_tracker", "tracker": _AcctTracker({}), "ls": object()})
    entry = job._find_account_tracker_entry()
    assert entry is not None and entry["type"] == "account_tracker"


def test_no_account_tracker_returns_none():
    job = _job()
    _register("job-1", "broker_fill_sub", {"type": "fill_subscription", "ls": object()})
    assert job._find_account_tracker_entry() is None


def test_another_jobs_tracker_is_not_borrowed():
    """레지스트리는 프로세스 전역이다 — 남의 계좌 잔고로 이 잡을 판정하면 조용히 틀린다."""
    job = _job("job-mine")
    _register("job-other", "broker", {"type": "account_tracker", "tracker": _AcctTracker({"X": _Pos(1, 1.0)}), "ls": object()})
    assert job._find_account_tracker_entry() is None
    _register("job-mine", "broker", {"type": "account_tracker", "tracker": _AcctTracker({}), "ls": object()})
    assert job._find_account_tracker_entry() is not None


# ── 한 주기 실행 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skips_quietly_without_a_ledger_tracker():
    job = _job()
    _register("job-1", "broker", {"type": "account_tracker", "tracker": _AcctTracker({}), "ls": object()})
    assert await job._reconcile_fills_once() is None


@pytest.mark.asyncio
async def test_skips_quietly_without_an_account_tracker():
    job = _job()
    job.context._workflow_position_tracker = object()
    assert await job._reconcile_fills_once() is None


# ── 루프 수명 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_loop_starts_once_and_stops_cleanly():
    job = _job()
    job._start_reconcile_loop()
    task = job._reconcile_task
    assert task is not None and not task.done()

    job._start_reconcile_loop()
    assert job._reconcile_task is task, "중복 기동되면 같은 체결을 두 번 확인한다"

    await job._stop_reconcile_loop()
    assert job._reconcile_task is None
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_stop_is_safe_when_never_started():
    job = _job()
    await job._stop_reconcile_loop()
    assert job._reconcile_task is None


@pytest.mark.asyncio
async def test_a_failing_cycle_does_not_kill_the_loop():
    """한 주기가 터져도 다음 주기가 살아 있어야 한다 — 아니면 조용히 재조정이 멈춘다."""
    job = _job()
    calls = []

    async def boom():
        calls.append(1)
        raise RuntimeError("broker down")

    job._reconcile_fills_once = boom
    job.RECONCILE_INTERVAL_SEC = 0.01
    job._start_reconcile_loop()
    await asyncio.sleep(0.08)
    running = not job._reconcile_task.done()
    await job._stop_reconcile_loop()

    assert len(calls) >= 2, "첫 실패 후 루프가 죽었다"
    assert running


def test_interval_is_above_the_account_tracker_cadence():
    """계좌 추적기가 60초마다 같은 앱키를 쓴다 — 그보다 촘촘하면 조회 예산을 잠식한다."""
    assert WorkflowJob.RECONCILE_INTERVAL_SEC >= 60.0
    assert WorkflowJob.RECONCILE_MIN_ORDER_AGE_SEC >= 10.0


# ── 소유자 검증 — 이 부류 결함을 통째로 잡는다 ────────────────────────────────
#
# 2026-09-14 하루에 **두 번** 같은 실수를 했다. executor.py 는 한 모듈에 클래스가 수십 개라
# `self.x` 가 어느 클래스의 것인지 눈으로 안 보인다:
#   · `self._active_trackers`              → 실제 소유자 BrokerNodeExecutor
#   · `self._query_overseas_stock_fills_by_date` → 실제 소유자 NewOrderNodeExecutor
# 둘 다 prod 에서 매 주기 AttributeError 로 죽고 나서야 발견했다. 단위 테스트는 일찍
# return 하는 경로만 타서 호출에 닿지 못했다.
#
# 그래서 개별 사례가 아니라 **규칙**을 검증한다 — 재조정 메서드가 참조하는 모든 `self.<이름>`
# 이 WorkflowJob 에 실재해야 한다. 새 메서드를 추가해도 자동으로 보호된다.

import ast
import inspect
import pathlib

_RECONCILE_METHODS = (
    "_reconcile_fills_once",
    "_find_account_tracker_entry",
    "_reconcile_loop",
    "_start_reconcile_loop",
    "_stop_reconcile_loop",
)


def _self_attribute_names(method_name: str) -> set[str]:
    """그 메서드가 읽는 `self.<이름>` 전부 (중첩 함수 포함)."""
    src = pathlib.Path(inspect.getsourcefile(WorkflowJob)).read_text()
    tree = ast.parse(src)
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "WorkflowJob"):
        for fn in cls.body:
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == method_name:
                return {
                    node.attr
                    for node in ast.walk(fn)
                    if isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                }
    raise AssertionError(f"WorkflowJob.{method_name} 를 못 찾음")


@pytest.mark.parametrize("method_name", _RECONCILE_METHODS)
def test_every_self_reference_exists_on_workflow_job(method_name):
    """`self.x` 가 WorkflowJob 에 없으면 런타임에 AttributeError 로 매 주기 죽는다."""
    # 인스턴스 속성(__init__ 에서 대입)까지 보려면 소스도 함께 훑어야 한다.
    src = pathlib.Path(inspect.getsourcefile(WorkflowJob)).read_text()
    tree = ast.parse(src)
    assigned: set[str] = set()
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "WorkflowJob"):
        for node in ast.walk(cls):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                    and node.value.id == "self" and isinstance(node.ctx, (ast.Store,)):
                assigned.add(node.attr)
        for item in cls.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assigned.add(item.name)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                assigned.add(item.target.id)
            elif isinstance(item, ast.Assign):
                for t in item.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)

    missing = sorted(
        name for name in _self_attribute_names(method_name)
        if name not in assigned and not hasattr(WorkflowJob, name)
    )
    assert not missing, (
        f"WorkflowJob.{method_name} 가 self.{{{', '.join(missing)}}} 를 쓰는데 "
        f"WorkflowJob 에 없다 — 다른 클래스 소유일 가능성이 높다"
    )


def _workflow_job_self_attrs() -> set[str]:
    """WorkflowJob 본문에서 **코드로** 읽는 `self.<이름>` 전부.

    문자열 검색이 아니라 AST 로 본다 — 주석·docstring 에 `self._active_trackers` 라고
    적어 둔 설명(왜 틀렸는지 남긴 기록)까지 걸려 오탐이 나기 때문이다. 그 기록은 남아야 한다.
    """
    src = pathlib.Path(inspect.getsourcefile(WorkflowJob)).read_text()
    tree = ast.parse(src)
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef) and cls.name == "WorkflowJob":
            return {
                n.attr for n in ast.walk(cls)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self"
            }
    raise AssertionError("WorkflowJob 클래스를 못 찾음")


@pytest.mark.parametrize("name,owner", [
    ("_active_trackers", "BrokerNodeExecutor"),
    ("_query_overseas_stock_fills_by_date", "NewOrderNodeExecutor"),
])
def test_known_misowned_members_are_not_read_off_self(name, owner):
    """실제로 틀렸던 두 이름을 못 박는다 — 되살아나면 즉시 깨진다."""
    assert name not in _workflow_job_self_attrs(), (
        f"{name} 은 {owner} 소유다 — WorkflowJob 에서 self 로 읽으면 매 주기 AttributeError"
    )
