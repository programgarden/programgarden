"""
NotificationEvent Core 단위 테스트

NotificationCategory, NotificationSeverity, NotificationEvent dataclass 및
BaseExecutionListener / ConsoleExecutionListener / ExecutionListener Protocol 검증.
"""

import dataclasses
import pytest


# ============================================================
# 1. NotificationCategory Enum
# ============================================================

class TestNotificationCategory:
    """NotificationCategory Enum 검증"""

    def test_import(self):
        """programgarden_core.bases.listener에서 import 가능"""
        from programgarden_core.bases.listener import NotificationCategory
        assert NotificationCategory is not None

    def test_import_from_bases(self):
        """programgarden_core.bases (짧은 경로)에서도 import 가능"""
        from programgarden_core.bases import NotificationCategory
        assert NotificationCategory is not None

    def test_has_eight_values(self):
        """정확히 8개의 카테고리 값을 가짐"""
        from programgarden_core.bases.listener import NotificationCategory
        assert len(NotificationCategory) == 8

    def test_all_expected_values(self):
        """8개 카테고리 값 모두 존재"""
        from programgarden_core.bases.listener import NotificationCategory

        expected = {
            "signal_triggered",
            "risk_alert",
            "risk_halt",
            "workflow_started",
            "workflow_completed",
            "workflow_failed",
            "retry_exhausted",
            "schedule_started",
        }
        actual = {c.value for c in NotificationCategory}
        assert actual == expected

    def test_is_str_enum(self):
        """str 서브클래스 Enum 이므로 문자열처럼 동작"""
        from programgarden_core.bases.listener import NotificationCategory

        cat = NotificationCategory.SIGNAL_TRIGGERED
        assert cat == "signal_triggered"
        assert isinstance(cat, str)

    def test_signal_triggered_value(self):
        """SIGNAL_TRIGGERED 값 확인"""
        from programgarden_core.bases.listener import NotificationCategory
        assert NotificationCategory.SIGNAL_TRIGGERED.value == "signal_triggered"

    def test_risk_halt_value(self):
        """RISK_HALT 값 확인"""
        from programgarden_core.bases.listener import NotificationCategory
        assert NotificationCategory.RISK_HALT.value == "risk_halt"

    def test_retry_exhausted_value(self):
        """RETRY_EXHAUSTED 값 확인"""
        from programgarden_core.bases.listener import NotificationCategory
        assert NotificationCategory.RETRY_EXHAUSTED.value == "retry_exhausted"


# ============================================================
# 2. NotificationSeverity Enum
# ============================================================

class TestNotificationSeverity:
    """NotificationSeverity Enum 검증"""

    def test_import(self):
        """programgarden_core.bases.listener에서 import 가능"""
        from programgarden_core.bases.listener import NotificationSeverity
        assert NotificationSeverity is not None

    def test_import_from_bases(self):
        """programgarden_core.bases (짧은 경로)에서도 import 가능"""
        from programgarden_core.bases import NotificationSeverity
        assert NotificationSeverity is not None

    def test_has_three_values(self):
        """정확히 3개의 심각도 값을 가짐"""
        from programgarden_core.bases.listener import NotificationSeverity
        assert len(NotificationSeverity) == 3

    def test_all_expected_values(self):
        """3개 심각도 값 모두 존재"""
        from programgarden_core.bases.listener import NotificationSeverity

        expected = {"info", "warning", "critical"}
        actual = {s.value for s in NotificationSeverity}
        assert actual == expected

    def test_is_str_enum(self):
        """str 서브클래스 Enum"""
        from programgarden_core.bases.listener import NotificationSeverity

        sev = NotificationSeverity.INFO
        assert sev == "info"
        assert isinstance(sev, str)

    def test_info_value(self):
        from programgarden_core.bases.listener import NotificationSeverity
        assert NotificationSeverity.INFO.value == "info"

    def test_warning_value(self):
        from programgarden_core.bases.listener import NotificationSeverity
        assert NotificationSeverity.WARNING.value == "warning"

    def test_critical_value(self):
        from programgarden_core.bases.listener import NotificationSeverity
        assert NotificationSeverity.CRITICAL.value == "critical"


# ============================================================
# 3. NotificationEvent dataclass
# ============================================================

class TestNotificationEvent:
    """NotificationEvent dataclass 생성 및 필드 검증"""

    def test_import(self):
        """import 가능"""
        from programgarden_core.bases.listener import NotificationEvent
        assert NotificationEvent is not None

    def test_import_from_bases(self):
        """programgarden_core.bases 짧은 경로 import"""
        from programgarden_core.bases import NotificationEvent
        assert NotificationEvent is not None

    def test_basic_creation(self):
        """필수 필드만으로 인스턴스 생성"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.SIGNAL_TRIGGERED,
            severity=NotificationSeverity.INFO,
            title="RSI 과매도 시그널",
            message="AAPL RSI 28.5 — 매수 검토",
        )

        assert event.job_id == "job-001"
        assert event.category == NotificationCategory.SIGNAL_TRIGGERED
        assert event.severity == NotificationSeverity.INFO
        assert event.title == "RSI 과매도 시그널"
        assert event.message == "AAPL RSI 28.5 — 매수 검토"

    def test_data_field_default_empty_dict(self):
        """`data` 필드 기본값은 빈 dict"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="워크플로우 시작",
            message="실행 시작됨",
        )

        assert event.data == {}
        assert isinstance(event.data, dict)

    def test_data_field_default_is_independent(self):
        """두 인스턴스의 data 기본값이 서로 독립적 (mutable default 검증)"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        e1 = NotificationEvent(
            job_id="j1",
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="t1",
            message="m1",
        )
        e2 = NotificationEvent(
            job_id="j2",
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="t2",
            message="m2",
        )
        e1.data["key"] = "value"
        assert "key" not in e2.data, "data 기본값이 공유되면 안 됨"

    def test_node_id_optional(self):
        """`node_id` 필드는 Optional — 기본값 None"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RISK_ALERT,
            severity=NotificationSeverity.WARNING,
            title="Drawdown 경고",
            message="-5% 도달",
        )
        assert event.node_id is None

    def test_node_type_optional(self):
        """`node_type` 필드는 Optional — 기본값 None"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RISK_ALERT,
            severity=NotificationSeverity.WARNING,
            title="경고",
            message="내용",
        )
        assert event.node_type is None

    def test_node_id_and_node_type_set(self):
        """`node_id`/`node_type` 명시 지정"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RETRY_EXHAUSTED,
            severity=NotificationSeverity.WARNING,
            title="재시도 소진",
            message="HTTPRequestNode 재시도 3회 모두 실패",
            node_id="http-node-1",
            node_type="HTTPRequestNode",
        )
        assert event.node_id == "http-node-1"
        assert event.node_type == "HTTPRequestNode"

    def test_timestamp_auto_set(self):
        """`timestamp` 필드가 생성 시 자동 설정됨"""
        from datetime import datetime
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.WORKFLOW_COMPLETED,
            severity=NotificationSeverity.INFO,
            title="완료",
            message="워크플로우 정상 완료",
        )
        assert isinstance(event.timestamp, datetime)

    def test_is_dataclass(self):
        """dataclass 여부 확인"""
        from programgarden_core.bases.listener import NotificationEvent
        assert dataclasses.is_dataclass(NotificationEvent)

    def test_required_fields(self):
        """필수 필드 이름 확인"""
        from programgarden_core.bases.listener import NotificationEvent

        field_names = {f.name for f in dataclasses.fields(NotificationEvent)}
        required = {"job_id", "category", "severity", "title", "message"}
        assert required.issubset(field_names)

    def test_optional_fields_present(self):
        """선택 필드 이름 확인"""
        from programgarden_core.bases.listener import NotificationEvent

        field_names = {f.name for f in dataclasses.fields(NotificationEvent)}
        optional = {"node_id", "node_type", "data", "timestamp"}
        assert optional.issubset(field_names)

    def test_data_with_custom_payload(self):
        """`data` 필드에 구조화 데이터 전달"""
        from programgarden_core.bases.listener import (
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        payload = {"symbol": "AAPL", "rsi": 28.5, "exchange": "NASDAQ"}
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.SIGNAL_TRIGGERED,
            severity=NotificationSeverity.INFO,
            title="RSI 시그널",
            message="과매도 구간 진입",
            data=payload,
        )
        assert event.data["symbol"] == "AAPL"
        assert event.data["rsi"] == 28.5


# ============================================================
# 4. BaseExecutionListener.on_notification
# ============================================================

class TestBaseExecutionListenerOnNotification:
    """BaseExecutionListener.on_notification no-op 테스트"""

    def test_has_on_notification(self):
        """BaseExecutionListener에 on_notification 메서드 존재"""
        from programgarden_core.bases.listener import BaseExecutionListener
        assert hasattr(BaseExecutionListener, "on_notification")

    @pytest.mark.asyncio
    async def test_on_notification_noop(self):
        """BaseExecutionListener.on_notification은 예외 없이 no-op"""
        from programgarden_core.bases.listener import (
            BaseExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = BaseExecutionListener()
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.WORKFLOW_STARTED,
            severity=NotificationSeverity.INFO,
            title="시작",
            message="워크플로우 실행 시작",
        )
        # 예외 없이 완료되어야 함
        result = await listener.on_notification(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_on_notification_all_categories(self):
        """모든 카테고리에 대해 no-op 동작"""
        from programgarden_core.bases.listener import (
            BaseExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = BaseExecutionListener()
        for category in NotificationCategory:
            event = NotificationEvent(
                job_id="job-001",
                category=category,
                severity=NotificationSeverity.INFO,
                title=f"{category.value} 이벤트",
                message="테스트",
            )
            await listener.on_notification(event)  # 예외 없이 통과


# ============================================================
# 5. ConsoleExecutionListener.on_notification
# ============================================================

class TestConsoleExecutionListenerOnNotification:
    """ConsoleExecutionListener.on_notification 출력 테스트"""

    def test_has_on_notification(self):
        """ConsoleExecutionListener에 on_notification 메서드 존재"""
        from programgarden_core.bases.listener import ConsoleExecutionListener
        assert hasattr(ConsoleExecutionListener, "on_notification")

    @pytest.mark.asyncio
    async def test_prints_category_and_title(self, capsys):
        """카테고리와 제목이 출력에 포함되는지 확인"""
        from programgarden_core.bases.listener import (
            ConsoleExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = ConsoleExecutionListener()
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.SIGNAL_TRIGGERED,
            severity=NotificationSeverity.INFO,
            title="RSI 시그널 발생",
            message="AAPL RSI=28.5",
        )
        await listener.on_notification(event)

        captured = capsys.readouterr()
        assert "signal_triggered" in captured.out.upper() or "SIGNAL_TRIGGERED" in captured.out
        assert "RSI 시그널 발생" in captured.out

    @pytest.mark.asyncio
    async def test_prints_message(self, capsys):
        """message 내용이 출력에 포함되는지 확인"""
        from programgarden_core.bases.listener import (
            ConsoleExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = ConsoleExecutionListener()
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RISK_HALT,
            severity=NotificationSeverity.CRITICAL,
            title="Kill Switch 활성화",
            message="최대 손실 한도 초과로 모든 주문 중단",
        )
        await listener.on_notification(event)

        captured = capsys.readouterr()
        assert "최대 손실 한도 초과로 모든 주문 중단" in captured.out

    @pytest.mark.asyncio
    async def test_warning_severity_output(self, capsys):
        """WARNING 심각도 이벤트가 출력됨"""
        from programgarden_core.bases.listener import (
            ConsoleExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = ConsoleExecutionListener()
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RETRY_EXHAUSTED,
            severity=NotificationSeverity.WARNING,
            title="재시도 소진",
            message="API 호출 3회 실패",
        )
        await listener.on_notification(event)

        captured = capsys.readouterr()
        assert len(captured.out) > 0

    @pytest.mark.asyncio
    async def test_node_id_in_output(self, capsys):
        """`node_id` 지정 시 출력에 포함"""
        from programgarden_core.bases.listener import (
            ConsoleExecutionListener,
            NotificationEvent,
            NotificationCategory,
            NotificationSeverity,
        )

        listener = ConsoleExecutionListener()
        event = NotificationEvent(
            job_id="job-001",
            category=NotificationCategory.RETRY_EXHAUSTED,
            severity=NotificationSeverity.WARNING,
            title="재시도 소진",
            message="실패",
            node_id="http-node-1",
        )
        await listener.on_notification(event)

        captured = capsys.readouterr()
        assert "http-node-1" in captured.out


# ============================================================
# 6. ExecutionListener Protocol
# ============================================================

class TestExecutionListenerProtocol:
    """ExecutionListener Protocol에 on_notification 존재 확인"""

    def test_protocol_has_on_notification(self):
        """ExecutionListener Protocol에 on_notification 메서드 존재"""
        from programgarden_core.bases.listener import ExecutionListener
        assert hasattr(ExecutionListener, "on_notification")

    def test_protocol_is_runtime_checkable(self):
        """Protocol이 runtime_checkable 데코레이터 적용됨"""
        from programgarden_core.bases.listener import (
            ExecutionListener,
            BaseExecutionListener,
        )
        # BaseExecutionListener는 Protocol을 구현하므로 isinstance 검사 통과
        listener = BaseExecutionListener()
        assert isinstance(listener, ExecutionListener)

    def test_all_key_methods_present(self):
        """Protocol에 핵심 메서드들 모두 존재"""
        from programgarden_core.bases.listener import ExecutionListener

        methods = [
            "on_node_state_change",
            "on_edge_state_change",
            "on_log",
            "on_job_state_change",
            "on_display_data",
            "on_workflow_pnl_update",
            "on_retry",
            "on_token_usage",
            "on_ai_tool_call",
            "on_risk_event",
            "on_restart",
            "on_notification",
        ]
        for method in methods:
            assert hasattr(ExecutionListener, method), f"Protocol에 {method} 없음"
