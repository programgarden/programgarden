"""
실시간 콜백 누수 수정 테스트

테스트 대상: context.py, executor.py
- shutdown flag로 콜백 차단
- cleanup_persistent_nodes에서 S3_/K3_ 구독 해제
- GSC/OVC 콜백 제거 실패 시 로그
- master callback SDK 레벨 해제
- BrokerNode fill subscription cleanup
- stop/cancel/force_stop 종료 경로 통합

실행:
    cd src/programgarden && poetry run pytest tests/test_realtime_callback_cleanup.py -v
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from programgarden.context import ExecutionContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def context():
    """기본 ExecutionContext 생성."""
    ctx = ExecutionContext(
        job_id="test-job-001",
        workflow_id="test-workflow-001",
    )
    return ctx


# ---------------------------------------------------------------------------
# Phase 1: shutdown flag + 콜백 가드
# ---------------------------------------------------------------------------


class TestShutdownFlag:
    """shutdown flag 기본 동작 테스트."""

    def test_initial_shutdown_false(self, context):
        """초기 상태에서 shutdown은 False."""
        assert context.is_shutdown is False
        assert context._shutdown is False

    def test_stop_sets_shutdown(self, context):
        """stop() 호출 시 shutdown flag가 True로 설정됨."""
        context.stop()
        assert context.is_shutdown is True

    @pytest.mark.asyncio
    async def test_shutdown_blocks_notify_output_update(self, context):
        """shutdown 상태에서 notify_output_update는 즉시 반환."""
        listener = MagicMock()
        listener.on_node_state_change = AsyncMock()
        context.add_listener(listener)

        context._shutdown = True

        await context.notify_output_update(
            node_id="test-node",
            node_type="TestNode",
            outputs={"data": [1, 2, 3]},
        )

        listener.on_node_state_change.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_blocks_emit_event(self, context):
        """shutdown 상태에서 emit_event는 이벤트 큐에 추가하지 않음."""
        context._shutdown = True

        await context.emit_event(
            event_type="market_data",
            source_node_id="test-node",
            data={"price": 100},
        )

        assert context._event_queue.empty()

    @pytest.mark.asyncio
    async def test_normal_notify_output_update_works(self, context):
        """shutdown이 아닌 상태에서는 정상 동작."""
        listener = MagicMock()
        listener.on_node_state_change = AsyncMock()
        context.add_listener(listener)

        await context.notify_output_update(
            node_id="test-node",
            node_type="TestNode",
            outputs={"data": [1, 2, 3]},
        )

        listener.on_node_state_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_normal_emit_event_works(self, context):
        """shutdown이 아닌 상태에서 emit_event는 정상 동작."""
        await context.emit_event(
            event_type="market_data",
            source_node_id="test-node",
            data={"price": 100},
        )

        assert not context._event_queue.empty()


# ---------------------------------------------------------------------------
# Phase 2: cleanup_persistent_nodes 개선
# ---------------------------------------------------------------------------


class TestCleanupPersistentNodes:
    """cleanup_persistent_nodes 동작 테스트."""

    @pytest.mark.asyncio
    async def test_cleanup_sets_shutdown_flag(self, context):
        """cleanup_persistent_nodes 호출 시 shutdown flag가 설정됨."""
        assert context.is_shutdown is False
        await context.cleanup_persistent_nodes()
        assert context.is_shutdown is True

    @pytest.mark.asyncio
    async def test_cleanup_drains_event_queue(self, context):
        """cleanup 후 이벤트 큐가 비어있음."""
        # 이벤트 추가 (shutdown 전에)
        await context._event_queue.put("event1")
        await context._event_queue.put("event2")
        assert not context._event_queue.empty()

        await context.cleanup_persistent_nodes()

        assert context._event_queue.empty()

    @pytest.mark.asyncio
    async def test_gsc_callback_removal_runtime_error_logged(self, context):
        """GSC on_remove_gsc_message RuntimeError 시 debug 로그."""
        mock_gsc = MagicMock()
        mock_gsc.remove_gsc_symbols = MagicMock()
        mock_gsc.on_remove_gsc_message = MagicMock(side_effect=RuntimeError("WebSocket not connected"))

        context._persistent_metadata["real-market-1"] = {
            "gsc": mock_gsc,
            "subscribe_symbols": ["NASDAAPL"],
        }

        with patch("programgarden.context.logger") as mock_logger:
            await context.cleanup_persistent_nodes()

            # RuntimeError는 debug 레벨로 로그
            mock_logger.debug.assert_any_call(
                "GSC callback already detached (WebSocket disconnected): real-market-1"
            )

    @pytest.mark.asyncio
    async def test_ovc_callback_removal_exception_logged(self, context):
        """OVC on_remove_ovc_message 일반 예외 시 warning 로그."""
        mock_ovc = MagicMock()
        mock_ovc.remove_ovc_symbols = MagicMock()
        mock_ovc.on_remove_ovc_message = MagicMock(side_effect=ValueError("unexpected"))

        context._persistent_metadata["real-market-2"] = {
            "ovc": mock_ovc,
            "subscribe_symbols": ["CME6AH26"],
        }

        with patch("programgarden.context.logger") as mock_logger:
            await context.cleanup_persistent_nodes()

            mock_logger.warning.assert_any_call(
                "Failed to remove OVC callback for real-market-2: unexpected"
            )

    @pytest.mark.asyncio
    async def test_korea_stock_s3_k3_cleanup(self, context):
        """국내주식 S3_/K3_ 구독 해제 및 콜백 제거."""
        mock_s3 = MagicMock()
        mock_s3.remove_s3__symbols = MagicMock()
        mock_s3.on_remove_s3__message = MagicMock()

        mock_k3 = MagicMock()
        mock_k3.remove_k3__symbols = MagicMock()
        mock_k3.on_remove_k3__message = MagicMock()

        context._persistent_metadata["korea-real-market-1"] = {
            "s3": mock_s3,
            "k3": mock_k3,
            "subscribe_symbols": ["005930", "000660"],
        }

        await context.cleanup_persistent_nodes()

        mock_s3.remove_s3__symbols.assert_called_once_with(symbols=["005930", "000660"])
        mock_s3.on_remove_s3__message.assert_called_once()
        mock_k3.remove_k3__symbols.assert_called_once_with(symbols=["005930", "000660"])
        mock_k3.on_remove_k3__message.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_clears_metadata(self, context):
        """cleanup 후 persistent 관련 딕셔너리가 비어있음."""
        context._persistent_metadata["node-1"] = {"gsc": MagicMock()}
        context._persistent_nodes["node-1"] = MagicMock(stop=MagicMock(), close=MagicMock())

        await context.cleanup_persistent_nodes()

        assert len(context._persistent_metadata) == 0
        assert len(context._persistent_nodes) == 0
        assert len(context._persistent_tasks) == 0


# ---------------------------------------------------------------------------
# Phase 3: master callback SDK 해제
# ---------------------------------------------------------------------------


class TestMasterCallbackSdkRemoval:
    """Order event master callback SDK 레벨 해제 테스트."""

    @pytest.mark.asyncio
    async def test_overseas_stock_as0_removed(self, context):
        """해외주식 AS0 master callback SDK 해제."""
        mock_as0 = MagicMock()
        mock_as0.on_remove_as0_message = MagicMock()

        mock_real_client = MagicMock()
        mock_real_client.AS0 = MagicMock(return_value=mock_as0)

        context._order_event_real_client["overseas_stock"] = mock_real_client

        await context.cleanup_persistent_nodes()

        mock_as0.on_remove_as0_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_overseas_futures_tc_removed(self, context):
        """해외선물 TC1/TC2/TC3 master callback SDK 해제."""
        mock_tc1 = MagicMock()
        mock_tc2 = MagicMock()
        mock_tc3 = MagicMock()

        mock_real_client = MagicMock()
        mock_real_client.TC1 = MagicMock(return_value=mock_tc1)
        mock_real_client.TC2 = MagicMock(return_value=mock_tc2)
        mock_real_client.TC3 = MagicMock(return_value=mock_tc3)

        context._order_event_real_client["overseas_futures"] = mock_real_client

        await context.cleanup_persistent_nodes()

        mock_tc1.on_remove_tc1_message.assert_called_once()
        mock_tc2.on_remove_tc2_message.assert_called_once()
        mock_tc3.on_remove_tc3_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_korea_stock_sc0_removed(self, context):
        """국내주식 SC0 master callback SDK 해제."""
        mock_sc0 = MagicMock()
        mock_sc0.on_remove_sc0_message = MagicMock()

        mock_real_client = MagicMock()
        mock_real_client.SC0 = MagicMock(return_value=mock_sc0)

        context._order_event_real_client["korea_stock"] = mock_real_client

        await context.cleanup_persistent_nodes()

        mock_sc0.on_remove_sc0_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_order_event_real_client_cleared(self, context):
        """cleanup 후 _order_event_real_client가 비어있음."""
        mock_real_client = MagicMock()
        mock_real_client.AS0 = MagicMock(return_value=MagicMock())
        context._order_event_real_client["overseas_stock"] = mock_real_client

        await context.cleanup_persistent_nodes()

        assert len(context._order_event_real_client) == 0
        assert len(context._order_event_handlers) == 0

    @pytest.mark.asyncio
    async def test_master_callback_runtime_error_ignored(self, context):
        """SDK 해제 시 RuntimeError는 무시."""
        mock_as0 = MagicMock()
        mock_as0.on_remove_as0_message = MagicMock(side_effect=RuntimeError("already detached"))

        mock_real_client = MagicMock()
        mock_real_client.AS0 = MagicMock(return_value=mock_as0)
        context._order_event_real_client["overseas_stock"] = mock_real_client

        # RuntimeError가 전파되지 않아야 함
        await context.cleanup_persistent_nodes()
        assert context.is_shutdown is True


# ---------------------------------------------------------------------------
# Phase 4: BrokerNode fill subscription cleanup
# ---------------------------------------------------------------------------


class TestBrokerFillSubscriptionCleanup:
    """BrokerNodeExecutor fill subscription cleanup 테스트."""

    @pytest.mark.asyncio
    async def test_cleanup_fill_subscriptions(self):
        """fill_subscription 타입의 콜백이 정리됨."""
        from programgarden.executor import BrokerNodeExecutor

        mock_as0 = MagicMock()
        mock_as1 = MagicMock()
        mock_real = MagicMock()
        mock_real.AS0 = MagicMock(return_value=mock_as0)
        mock_real.AS1 = MagicMock(return_value=mock_as1)

        executor = BrokerNodeExecutor()
        executor._active_trackers["job-1_broker_fill_sub"] = {
            "real": mock_real,
            "type": "fill_subscription",
        }

        await executor.cleanup_fill_subscriptions("job-1")

        mock_as0.on_remove_as0_message.assert_called_once()
        mock_as1.on_remove_as1_message.assert_called_once()
        assert "job-1_broker_fill_sub" not in executor._active_trackers

    @pytest.mark.asyncio
    async def test_cleanup_only_matches_job_id(self):
        """다른 job의 fill subscription은 정리하지 않음."""
        from programgarden.executor import BrokerNodeExecutor

        executor = BrokerNodeExecutor()
        executor._active_trackers["job-1_broker_fill_sub"] = {
            "real": MagicMock(),
            "type": "fill_subscription",
        }
        executor._active_trackers["job-2_broker_fill_sub"] = {
            "real": MagicMock(),
            "type": "fill_subscription",
        }

        await executor.cleanup_fill_subscriptions("job-1")

        assert "job-1_broker_fill_sub" not in executor._active_trackers
        assert "job-2_broker_fill_sub" in executor._active_trackers

        # cleanup
        del executor._active_trackers["job-2_broker_fill_sub"]

    @pytest.mark.asyncio
    async def test_cleanup_runtime_error_ignored(self):
        """SDK 콜백 해제 RuntimeError는 무시됨."""
        from programgarden.executor import BrokerNodeExecutor

        mock_as0 = MagicMock()
        mock_as0.on_remove_as0_message = MagicMock(side_effect=RuntimeError("not connected"))
        mock_real = MagicMock()
        mock_real.AS0 = MagicMock(return_value=mock_as0)
        mock_real.AS1 = MagicMock(return_value=MagicMock())

        executor = BrokerNodeExecutor()
        executor._active_trackers["job-3_broker_fill_sub"] = {
            "real": mock_real,
            "type": "fill_subscription",
        }

        await executor.cleanup_fill_subscriptions("job-3")
        assert "job-3_broker_fill_sub" not in executor._active_trackers
