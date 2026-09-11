"""C24: 체결 확정 이벤트(on_order_fill) 발화 검증.

원장에 체결이 새로 확정될 때마다 ExecutionListener.on_order_fill 이 정확히 1회
발화하는지 확인한다 — 즉시(주문과 매칭) 경로와 pending→timeout(주문 미매칭)
경로 모두. 리스너가 없어도 무해해야 한다.
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from programgarden.context import ExecutionContext
from programgarden.database.workflow_position_tracker import WorkflowPositionTracker
from programgarden_core.bases.listener import BaseExecutionListener, OrderFillEvent


class _RecordingListener(BaseExecutionListener):
    """on_order_fill 이벤트를 수집하는 리스너."""

    def __init__(self):
        super().__init__()
        self.fills = []

    async def on_order_fill(self, event: OrderFillEvent) -> None:
        self.fills.append(event)


def _make_context_with_tracker(tmp_path, product="overseas_stock", provider="ls",
                               trading_mode="live", buffer_timeout=None):
    """실제 tracker 를 임시 DB 로 만들고 콜백을 연결한 컨텍스트 반환."""
    db_path = str(tmp_path / f"{product}_{trading_mode}_workflow.db")
    tracker = WorkflowPositionTracker(
        db_path=db_path,
        job_id="job-c24",
        broker_node_id="broker-1",
        product=product,
        provider=provider,
        trading_mode=trading_mode,
    )
    if buffer_timeout is not None:
        tracker.FILL_BUFFER_TIMEOUT = buffer_timeout

    ctx = ExecutionContext(job_id="job-c24", workflow_id="wf-c24")
    ctx._workflow_position_tracker = tracker
    ctx._workflow_product = product
    ctx._workflow_broker_node_id = "broker-1"
    # PnL refresh 는 이 테스트의 관심사가 아니므로 우회 (on_order_fill 은 독립 경로).
    ctx.notify_workflow_pnl = AsyncMock()
    tracker.set_fill_classified_callback(ctx._on_tracker_fill_classified)
    return ctx, tracker


class TestImmediateWorkflowFill:
    @pytest.mark.asyncio
    async def test_matched_fill_emits_once_with_identity(self, tmp_path):
        ctx, tracker = _make_context_with_tracker(tmp_path)
        listener = _RecordingListener()
        ctx.add_listener(listener)

        # 우리 주문을 먼저 기록 → 체결이 즉시 workflow 로 분류된다.
        tracker.record_order(
            order_no="123", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=10, price=190.0,
            job_id="job-c24", node_id="order_node_1",
        )

        result = await ctx.record_workflow_fill(
            order_no="123", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=10, price=190.0,
            fill_time="093000000", commda_code="40",
        )

        assert result == "workflow"
        assert len(listener.fills) == 1
        ev = listener.fills[0]
        assert ev.classification == "workflow"
        assert ev.node_id == "order_node_1"
        assert ev.job_id == "job-c24"
        assert ev.order_no == "123"
        assert ev.order_date == "20260912"
        assert ev.symbol == "AAPL"
        assert ev.exchange == "NASDAQ"
        assert ev.side == "buy"
        assert ev.quantity == 10
        assert ev.price == 190.0
        assert ev.product == "overseas_stock"
        assert ev.provider == "ls"
        assert ev.trading_mode == "live"
        assert ev.commda_code == "40"
        assert ev.fill_time == "093000000"
        # facts only — 금액/수익 계산 필드는 존재하지 않는다.
        assert not hasattr(ev, "pnl_amount")

    @pytest.mark.asyncio
    async def test_manual_human_media_fill_has_no_node_id(self, tmp_path):
        ctx, tracker = _make_context_with_tracker(tmp_path)
        listener = _RecordingListener()
        ctx.add_listener(listener)

        # 주문 미기록 + HTS(85) 매체코드 → manual 로 즉시 분류(버퍼 없음).
        result = await ctx.record_workflow_fill(
            order_no="777", order_date="20260912", symbol="MSFT",
            exchange="NASDAQ", side="buy", quantity=3, price=400.0,
            fill_time="100000000", commda_code="85",
        )

        assert result == "manual"
        assert len(listener.fills) == 1
        ev = listener.fills[0]
        assert ev.classification == "manual"
        assert ev.node_id is None


class TestPendingTimeoutFill:
    @pytest.mark.asyncio
    async def test_pending_resolves_to_unknown_api_and_emits(self, tmp_path):
        # 짧은 버퍼로 timeout 경로를 빠르게 확정.
        ctx, tracker = _make_context_with_tracker(tmp_path, buffer_timeout=0.05)
        listener = _RecordingListener()
        ctx.add_listener(listener)

        # 주문 미기록 + API(40) 매체코드 → 버퍼링(pending) 후 timeout 확정.
        result = await ctx.record_workflow_fill(
            order_no="999", order_date="20260912", symbol="TSLA",
            exchange="NASDAQ", side="buy", quantity=1, price=200.0,
            fill_time="093000000", commda_code="40",
        )
        assert result == "pending"
        # pending 시점엔 아직 발화 전.
        assert listener.fills == []

        await asyncio.sleep(0.05 + 0.25)

        assert len(listener.fills) == 1
        ev = listener.fills[0]
        assert ev.classification == "unknown_api"
        assert ev.node_id is None
        assert ev.symbol == "TSLA"
        assert ev.order_no == "999"

    @pytest.mark.asyncio
    async def test_pending_resolves_to_workflow_when_order_arrives(self, tmp_path):
        ctx, tracker = _make_context_with_tracker(tmp_path, buffer_timeout=0.05)
        listener = _RecordingListener()
        ctx.add_listener(listener)

        result = await ctx.record_workflow_fill(
            order_no="555", order_date="20260912", symbol="NVDA",
            exchange="NASDAQ", side="buy", quantity=2, price=120.0,
            fill_time="093000000", commda_code="40",
        )
        assert result == "pending"
        assert listener.fills == []

        await asyncio.sleep(0.05 + 0.25)

        assert len(listener.fills) == 1
        ev = listener.fills[0]
        # 버퍼 동안 주문이 안 왔으므로 unknown_api 로 확정(node_id None).
        assert ev.classification == "unknown_api"
        assert ev.node_id is None


class TestNoListenerHarmless:
    @pytest.mark.asyncio
    async def test_fill_without_listeners_does_not_raise(self, tmp_path):
        ctx, tracker = _make_context_with_tracker(tmp_path)
        # 리스너 없음.
        assert ctx._listeners == []

        tracker.record_order(
            order_no="1", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=1, price=1.0,
            job_id="job-c24", node_id="n1",
        )
        result = await ctx.record_workflow_fill(
            order_no="1", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=1, price=1.0,
            fill_time="093000000", commda_code="40",
        )
        assert result == "workflow"

    @pytest.mark.asyncio
    async def test_tracker_without_callback_still_records(self, tmp_path):
        # 콜백을 연결하지 않은 독립 tracker(서버/컨텍스트 밖 사용)도 무해.
        db_path = str(tmp_path / "standalone_workflow.db")
        tracker = WorkflowPositionTracker(
            db_path=db_path, job_id="j", broker_node_id="b",
            product="overseas_stock", provider="ls", trading_mode="live",
        )
        tracker.record_order(
            order_no="42", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=1, price=10.0,
            job_id="j", node_id="n",
        )
        result = await tracker.record_fill(
            order_no="42", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=1, price=10.0,
            fill_time="093000000", commda_code="40",
        )
        assert result == "workflow"


class TestOrderIdentityLookup:
    def test_lookup_matches_normalized_order_no(self, tmp_path):
        db_path = str(tmp_path / "lookup_workflow.db")
        tracker = WorkflowPositionTracker(
            db_path=db_path, job_id="jid", broker_node_id="b",
            product="overseas_stock", provider="ls", trading_mode="live",
        )
        tracker.record_order(
            order_no="0000123", order_date="20260912", symbol="AAPL",
            exchange="NASDAQ", side="buy", quantity=1, price=10.0,
            job_id="jid", node_id="node-x",
        )
        # 정확 일치
        assert tracker.lookup_order_identity("0000123", "20260912") == ("jid", "node-x")
        # 정규화(zero-strip) 일치
        assert tracker.lookup_order_identity("123", "20260912") == ("jid", "node-x")
        # 없는 주문
        assert tracker.lookup_order_identity("999", "20260912") is None
