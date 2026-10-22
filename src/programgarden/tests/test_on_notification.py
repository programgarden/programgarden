"""
on_notification 콜백 통합 테스트

ExecutionContext의 notify_notification / send_notification 메서드와
RISK_ALERT 자동 래핑 동작을 검증합니다.
"""

import pytest
import asyncio
from programgarden_core.bases.listener import (
    BaseExecutionListener,
    NotificationEvent,
    NotificationCategory,
    NotificationSeverity,
    RiskEvent,
)
from programgarden.context import ExecutionContext


# ============================================================
# 테스트용 Mock Listener
# ============================================================

class MockListener(BaseExecutionListener):
    """알림 이벤트를 수집하는 테스트 리스너"""

    def __init__(self):
        super().__init__()
        self.notifications: list[NotificationEvent] = []

    async def on_notification(self, event: NotificationEvent) -> None:
        self.notifications.append(event)


class ErrorListener(BaseExecutionListener):
    """on_notification에서 예외를 발생시키는 리스너"""

    async def on_notification(self, event: NotificationEvent) -> None:
        raise RuntimeError("listener error")


class NoNotificationListener(BaseExecutionListener):
    """on_notification이 없는 리스너 (부모의 no-op 상속)"""
    pass


def make_context(job_id: str = "test-job-001") -> ExecutionContext:
    """테스트용 ExecutionContext 생성 헬퍼"""
    return ExecutionContext(job_id=job_id, workflow_id="wf-test-001")


def make_event(
    job_id: str = "test-job-001",
    category: NotificationCategory = NotificationCategory.SIGNAL_TRIGGERED,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    title: str = "테스트 알림",
    message: str = "테스트 메시지",
) -> NotificationEvent:
    """테스트용 NotificationEvent 생성 헬퍼"""
    return NotificationEvent(
        job_id=job_id,
        category=category,
        severity=severity,
        title=title,
        message=message,
    )


# ============================================================
# 1. notify_notification: 다중 listener 전파
# ============================================================

class TestNotifyNotificationPropagation:
    """notify_notification 전파 동작 검증"""

    @pytest.mark.asyncio
    async def test_single_listener_receives_event(self):
        """단일 리스너에 이벤트 전파"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        event = make_event()
        await ctx.notify_notification(event)

        assert len(listener.notifications) == 1
        assert listener.notifications[0] is event

    @pytest.mark.asyncio
    async def test_multiple_listeners_all_receive_event(self):
        """다중 리스너 모두에 이벤트 전파"""
        ctx = make_context()
        l1 = MockListener()
        l2 = MockListener()
        l3 = MockListener()
        ctx._listeners = [l1, l2, l3]

        event = make_event()
        await ctx.notify_notification(event)

        assert len(l1.notifications) == 1
        assert len(l2.notifications) == 1
        assert len(l3.notifications) == 1
        # 세 리스너 모두 동일한 이벤트 객체를 받음
        assert l1.notifications[0] is l2.notifications[0] is l3.notifications[0]

    @pytest.mark.asyncio
    async def test_event_attributes_preserved(self):
        """전파된 이벤트의 속성 값이 원본과 동일"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        event = NotificationEvent(
            job_id="job-abc",
            category=NotificationCategory.RISK_HALT,
            severity=NotificationSeverity.CRITICAL,
            title="Kill Switch",
            message="최대 손실 초과",
            node_id="portfolio-node",
            node_type="PortfolioNode",
            data={"drawdown": -0.15},
        )
        await ctx.notify_notification(event)

        received = listener.notifications[0]
        assert received.job_id == "job-abc"
        assert received.category == NotificationCategory.RISK_HALT
        assert received.severity == NotificationSeverity.CRITICAL
        assert received.title == "Kill Switch"
        assert received.message == "최대 손실 초과"
        assert received.node_id == "portfolio-node"
        assert received.node_type == "PortfolioNode"
        assert received.data["drawdown"] == -0.15

    @pytest.mark.asyncio
    async def test_multiple_events_accumulated(self):
        """여러 번 호출 시 이벤트 순서대로 누적"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        for i in range(5):
            event = make_event(title=f"알림 {i}")
            await ctx.notify_notification(event)

        assert len(listener.notifications) == 5
        for i, notif in enumerate(listener.notifications):
            assert notif.title == f"알림 {i}"


# ============================================================
# 2. notify_notification: 예외 격리
# ============================================================

class TestNotifyNotificationExceptionIsolation:
    """리스너 예외 격리 — 한 리스너 오류가 다른 리스너에 영향 안 줌"""

    @pytest.mark.asyncio
    async def test_error_listener_does_not_block_next_listener(self):
        """에러 리스너 다음에 정상 리스너도 호출됨"""
        ctx = make_context()
        error_listener = ErrorListener()
        good_listener = MockListener()
        ctx._listeners = [error_listener, good_listener]

        event = make_event()
        # 예외가 외부로 전파되지 않아야 함
        await ctx.notify_notification(event)

        # good_listener는 정상 수신
        assert len(good_listener.notifications) == 1

    @pytest.mark.asyncio
    async def test_error_listener_before_and_after_good_listeners(self):
        """에러 리스너가 중간에 있어도 나머지 리스너는 모두 호출됨"""
        ctx = make_context()
        l1 = MockListener()
        error_listener = ErrorListener()
        l2 = MockListener()
        ctx._listeners = [l1, error_listener, l2]

        event = make_event()
        await ctx.notify_notification(event)

        assert len(l1.notifications) == 1, "첫 번째 리스너는 정상 수신"
        assert len(l2.notifications) == 1, "세 번째 리스너도 정상 수신"

    @pytest.mark.asyncio
    async def test_notify_does_not_raise_on_listener_error(self):
        """리스너 예외 발생 시 notify_notification 자체는 예외 미발생"""
        ctx = make_context()
        ctx._listeners = [ErrorListener()]

        event = make_event()
        try:
            await ctx.notify_notification(event)
        except Exception:
            pytest.fail("notify_notification이 예외를 전파해서는 안 됨")


# ============================================================
# 3. notify_notification: listener 없을 때 early return
# ============================================================

class TestNotifyNotificationEarlyReturn:
    """listener 없을 때 early return 동작"""

    @pytest.mark.asyncio
    async def test_empty_listeners_no_error(self):
        """리스너 없을 때 예외 없이 통과"""
        ctx = make_context()
        ctx._listeners = []

        event = make_event()
        await ctx.notify_notification(event)  # 예외 없이 완료

    @pytest.mark.asyncio
    async def test_default_context_no_listeners(self):
        """기본 생성 컨텍스트는 리스너 없이 동작"""
        ctx = make_context()

        event = make_event()
        await ctx.notify_notification(event)  # 예외 없이 완료


# ============================================================
# 4. send_notification: 편의 메서드
# ============================================================

class TestSendNotification:
    """send_notification 편의 메서드로 NotificationEvent 생성 + 전파"""

    @pytest.mark.asyncio
    async def test_send_creates_and_propagates_event(self):
        """send_notification이 NotificationEvent를 생성하여 전파"""
        ctx = make_context("send-test-job")
        listener = MockListener()
        ctx._listeners = [listener]

        await ctx.send_notification(
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="워크플로우 시작",
            message="실행이 시작되었습니다",
        )

        assert len(listener.notifications) == 1
        event = listener.notifications[0]
        assert event.job_id == "send-test-job"
        assert event.category == NotificationCategory.WORKFLOW_STARTED
        assert event.severity == NotificationSeverity.INFO
        assert event.title == "워크플로우 시작"
        assert event.message == "실행이 시작되었습니다"

    @pytest.mark.asyncio
    async def test_send_uses_context_job_id(self):
        """send_notification이 context.job_id를 이벤트 job_id로 사용"""
        ctx = make_context("ctx-job-xyz")
        listener = MockListener()
        ctx._listeners = [listener]

        await ctx.send_notification(
            category=NotificationCategory.WORKFLOW_COMPLETED,
            severity=NotificationSeverity.INFO,
            title="완료",
            message="워크플로우 정상 완료",
        )

        assert listener.notifications[0].job_id == "ctx-job-xyz"

    @pytest.mark.asyncio
    async def test_send_with_node_id_and_node_type(self):
        """node_id, node_type 파라미터 전달 시 이벤트에 포함"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        await ctx.send_notification(
            category=NotificationCategory.RETRY_EXHAUSTED,
            severity=NotificationSeverity.WARNING,
            title="재시도 소진",
            message="API 호출 실패",
            node_id="http-1",
            node_type="HTTPRequestNode",
        )

        event = listener.notifications[0]
        assert event.node_id == "http-1"
        assert event.node_type == "HTTPRequestNode"

    @pytest.mark.asyncio
    async def test_send_with_data_payload(self):
        """`data` 파라미터 전달 시 이벤트에 포함"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        payload = {"symbol": "AAPL", "rsi": 28.5}
        await ctx.send_notification(
            category=NotificationCategory.SIGNAL_TRIGGERED,
            severity=NotificationSeverity.INFO,
            title="RSI 시그널",
            message="과매도 구간",
            data=payload,
        )

        event = listener.notifications[0]
        assert event.data["symbol"] == "AAPL"
        assert event.data["rsi"] == 28.5

    @pytest.mark.asyncio
    async def test_send_data_default_empty_dict(self):
        """`data` 미전달 시 빈 dict로 설정"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        await ctx.send_notification(
            category=NotificationCategory.SCHEDULE_STARTED,
            severity=NotificationSeverity.INFO,
            title="스케줄 시작",
            message="사이클 실행",
        )

        event = listener.notifications[0]
        assert event.data == {}

    @pytest.mark.asyncio
    async def test_send_no_listeners_no_error(self):
        """리스너 없을 때 send_notification도 예외 없이 통과"""
        ctx = make_context()
        ctx._listeners = []

        await ctx.send_notification(
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="시작",
            message="시작 메시지",
        )  # 예외 없이 완료

    @pytest.mark.asyncio
    async def test_send_is_type_notification_event(self):
        """send_notification이 생성한 이벤트는 NotificationEvent 타입"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        await ctx.send_notification(
            category=NotificationCategory.WORKFLOW_FAILED,
            severity=NotificationSeverity.CRITICAL,
            title="실패",
            message="오류 발생",
        )

        assert isinstance(listener.notifications[0], NotificationEvent)


# ============================================================
# 5. RISK_ALERT 자동 래핑
# ============================================================

class TestRiskAlertAutoWrapping:
    """notify_risk_event 호출 시 on_notification도 RISK_ALERT 카테고리로 자동 호출"""

    @pytest.mark.asyncio
    async def test_risk_event_triggers_notification(self):
        """RiskEvent 발생 시 on_notification도 호출됨"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="drawdown_alert",
            severity="warning",
        )
        await ctx.notify_risk_event(risk_event)

        assert len(listener.notifications) == 1

    @pytest.mark.asyncio
    async def test_risk_alert_category_set(self):
        """자동 래핑된 알림의 category는 RISK_ALERT"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="trailing_stop_triggered",
            severity="warning",
        )
        await ctx.notify_risk_event(risk_event)

        notification = listener.notifications[0]
        assert notification.category == NotificationCategory.RISK_ALERT

    @pytest.mark.asyncio
    async def test_severity_critical_mapped(self):
        """RiskEvent severity='critical' → NotificationSeverity.CRITICAL"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="kill_switch_activated",
            severity="critical",
        )
        await ctx.notify_risk_event(risk_event)

        assert listener.notifications[0].severity == NotificationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_severity_warning_mapped(self):
        """RiskEvent severity='warning' → NotificationSeverity.WARNING"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="drawdown_alert",
            severity="warning",
        )
        await ctx.notify_risk_event(risk_event)

        assert listener.notifications[0].severity == NotificationSeverity.WARNING

    @pytest.mark.asyncio
    async def test_severity_info_mapped(self):
        """RiskEvent severity='info' → NotificationSeverity.INFO"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="hwm_updated",
            severity="info",
        )
        await ctx.notify_risk_event(risk_event)

        assert listener.notifications[0].severity == NotificationSeverity.INFO

    @pytest.mark.asyncio
    async def test_risk_notification_contains_symbol_tag(self):
        """symbol이 있으면 title에 포함"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="trailing_stop_triggered",
            severity="warning",
            symbol="AAPL",
            exchange="NASDAQ",
        )
        await ctx.notify_risk_event(risk_event)

        notification = listener.notifications[0]
        assert "AAPL" in notification.title

    @pytest.mark.asyncio
    async def test_risk_notification_no_symbol_no_tag(self):
        """symbol이 없으면 title에 symbol 태그 없음"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="portfolio_drawdown",
            severity="warning",
        )
        await ctx.notify_risk_event(risk_event)

        notification = listener.notifications[0]
        assert "[" not in notification.title

    @pytest.mark.asyncio
    async def test_risk_notification_data_fields(self):
        """래핑된 알림의 data 필드에 위험 정보 포함"""
        ctx = make_context()
        listener = MockListener()
        ctx._listeners = [listener]

        risk_event = RiskEvent(
            job_id="test-job-001",
            event_type="drawdown_alert",
            severity="critical",
            symbol="NVDA",
            exchange="NASDAQ",
            details={"drawdown": -0.12},
            action_hint="halt_orders",
        )
        await ctx.notify_risk_event(risk_event)

        data = listener.notifications[0].data
        assert data["event_type"] == "drawdown_alert"
        assert data["severity"] == "critical"
        assert data["symbol"] == "NVDA"
        assert data["exchange"] == "NASDAQ"
        assert data["details"]["drawdown"] == -0.12
        assert data["action_hint"] == "halt_orders"


# ============================================================
# 6. re-export: programgarden 패키지에서 직접 import 가능
# ============================================================

class TestProgramgardenReexport:
    """programgarden 패키지 최상위에서 NotificationCategory 등 import 가능"""

    def test_notification_category_importable(self):
        """programgarden에서 NotificationCategory import"""
        from programgarden import NotificationCategory
        assert NotificationCategory is not None

    def test_notification_severity_importable(self):
        """programgarden에서 NotificationSeverity import"""
        from programgarden import NotificationSeverity
        assert NotificationSeverity is not None

    def test_notification_event_importable(self):
        """programgarden에서 NotificationEvent import"""
        from programgarden import NotificationEvent
        assert NotificationEvent is not None

    def test_all_notification_types_same_class(self):
        """programgarden에서 import한 클래스와 core에서 import한 클래스가 동일"""
        from programgarden import NotificationCategory as PG_Category
        from programgarden import NotificationSeverity as PG_Severity
        from programgarden import NotificationEvent as PG_Event
        from programgarden_core.bases.listener import (
            NotificationCategory as Core_Category,
            NotificationSeverity as Core_Severity,
            NotificationEvent as Core_Event,
        )

        assert PG_Category is Core_Category
        assert PG_Severity is Core_Severity
        assert PG_Event is Core_Event

    def test_context_has_notify_notification(self):
        """ExecutionContext에 notify_notification 메서드 존재"""
        from programgarden.context import ExecutionContext
        assert hasattr(ExecutionContext, "notify_notification")

    def test_context_has_send_notification(self):
        """ExecutionContext에 send_notification 메서드 존재"""
        from programgarden.context import ExecutionContext
        assert hasattr(ExecutionContext, "send_notification")
