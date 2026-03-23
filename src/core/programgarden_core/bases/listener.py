"""
ExecutionListener - Workflow execution state callback protocol

Protocol and event types for tracking workflow execution state.
Servers/UIs can implement ExecutionListener to receive real-time
callbacks when nodes execute, edges transmit data, or jobs change state.

Usage:
    class MyListener:
        async def on_node_state_change(self, event: NodeStateEvent) -> None:
            print(f"Node {event.node_id} is now {event.state}")
        
        async def on_edge_state_change(self, event: EdgeStateEvent) -> None:
            print(f"Edge {event.from_node_id} -> {event.to_node_id}: {event.state}")
        
        async def on_log(self, event: LogEvent) -> None:
            print(f"[{event.level}] {event.message}")
        
        async def on_job_state_change(self, event: JobStateEvent) -> None:
            print(f"Job {event.job_id} is now {event.state}")
    
    # Option A: Inject at creation
    job = await pg.run_async(workflow, listeners=[MyListener()])
    
    # Option B: Add after creation
    job = await pg.run_async(workflow)
    job.add_listener(MyListener())
"""

from typing import Protocol, Optional, Dict, Any, List, Union, runtime_checkable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from programgarden_core.models.resilience import RetryEvent


class NodeState(str, Enum):
    """Node execution state"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    THROTTLING = "throttling"


class EdgeState(str, Enum):
    """Edge data transmission state"""
    IDLE = "idle"
    TRANSMITTING = "transmitting"
    TRANSMITTED = "transmitted"


@dataclass
class NodeStateEvent:
    """
    Event emitted when a node's execution state changes.
    
    Attributes:
        job_id: Job identifier
        node_id: Node ID
        node_type: Node type (StartNode, ConditionNode, etc.)
        state: New state
        timestamp: Event timestamp
        outputs: Node outputs (only when completed)
        error: Error message (only when failed)
        duration_ms: Execution time in ms (only when completed/failed)
    """
    job_id: str
    node_id: str
    node_type: str
    state: NodeState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class EdgeStateEvent:
    """
    Event emitted when an edge's data transmission state changes.
    
    Attributes:
        job_id: Job identifier
        from_node_id: Source node ID
        from_port: Source port name
        to_node_id: Target node ID
        to_port: Target port name
        state: New state
        timestamp: Event timestamp
        data_preview: Truncated preview of transmitted data
    """
    job_id: str
    from_node_id: str
    from_port: str
    to_node_id: str
    to_port: str
    state: EdgeState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data_preview: Optional[str] = None


@dataclass
class LogEvent:
    """
    Event emitted when a log entry is created.
    
    Attributes:
        job_id: Job identifier
        level: Log level (debug, info, warning, error)
        message: Log message
        timestamp: Event timestamp
        node_id: Related node ID (optional)
        data: Additional data (optional)
    """
    job_id: str
    level: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    node_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class JobStateEvent:
    """
    Event emitted when a job's overall state changes.
    
    Attributes:
        job_id: Job identifier
        state: New state (pending, running, completed, failed, cancelled)
        timestamp: Event timestamp
        stats: Execution statistics (optional)
    """
    job_id: str
    state: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    stats: Optional[Dict[str, Any]] = None


@dataclass
class DisplayDataEvent:
    """
    Event emitted when a DisplayNode produces visualization data.

    Attributes:
        job_id: Job identifier
        node_id: DisplayNode ID
        chart_type: Type of chart (line, candlestick, bar, scatter, radar, heatmap, table)
        title: Chart title
        data: Chart data array
        x_label: X-axis label (optional)
        y_label: Y-axis label (optional)
        options: Additional chart options (optional)
        data_schema: Schema describing data array structure.
            Properties with 'resolved_by' indicate dynamic field names
            determined by node settings in options. (optional)
        timestamp: Event timestamp
    """
    job_id: str
    node_id: str
    chart_type: str
    title: Optional[str]
    data: Any  # List[Dict] or similar
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    data_schema: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PositionDetail:
    """
    Position detail for workflow P&L tracking.
    
    Attributes:
        symbol: Symbol code (e.g., "AAPL")
        exchange: Exchange code (e.g., "NASDAQ")
        quantity: Number of shares
        avg_price: Average buy price
        current_price: Current market price
        pnl_amount: P&L amount (current - buy)
        pnl_rate: P&L rate (%)
    """
    symbol: str
    exchange: str
    quantity: int
    avg_price: Union[Decimal, float]
    current_price: Union[Decimal, float]
    pnl_amount: Union[Decimal, float]
    pnl_rate: Union[Decimal, float]


@dataclass
class WorkflowPnLEvent:
    """
    Event emitted when workflow position P&L is updated.
    
    Unlike AccountPnLEvent which tracks the entire account,
    WorkflowPnLEvent separates workflow positions from manual positions
    using FIFO (First-In-First-Out) tracking.
    
    Used for competition ranking where only workflow-generated trades
    should be counted for official scoring.
    
    Attributes:
        job_id: Job identifier
        broker_node_id: BrokerNode ID
        product: Product type ("overseas_stock", "overseas_futures", or "korea_stock")
        
        # Workflow position P&L
        workflow_pnl_rate: Workflow position P&L rate (%)
        workflow_eval_amount: Workflow evaluation amount
        workflow_buy_amount: Workflow buy amount
        workflow_pnl_amount: Workflow P&L amount
        
        # Other (manual/unknown) position P&L
        other_pnl_rate: Other position P&L rate (%)
        other_eval_amount: Other evaluation amount
        other_buy_amount: Other buy amount
        other_pnl_amount: Other P&L amount
        
        # Total account P&L
        total_pnl_rate: Total P&L rate (%)
        total_eval_amount: Total evaluation amount
        total_buy_amount: Total buy amount
        total_pnl_amount: Total P&L amount
        
        # Position details
        workflow_positions: List of workflow position details
        other_positions: List of other position details
        
        # Trust metrics
        trust_score: Trust score (0-100)
        anomaly_count: Number of detected anomalies
        
        currency: Base currency
        timestamp: Event timestamp
    
    New Fields (v2.0):
        # Workflow product-specific P&L
        workflow_overseas_stock_pnl_rate: Overseas stock workflow P&L rate (%)
        workflow_overseas_stock_pnl_amount: Overseas stock workflow P&L amount
        workflow_overseas_futures_pnl_rate: Overseas futures workflow P&L rate (%)
        workflow_overseas_futures_pnl_amount: Overseas futures workflow P&L amount
        workflow_korea_stock_pnl_rate: Korea stock workflow P&L rate (%)
        workflow_korea_stock_pnl_amount: Korea stock workflow P&L amount

        # Account total P&L
        account_total_pnl_rate: Entire account P&L rate (%)
        account_total_pnl_amount: Entire account P&L amount
        account_total_eval_amount: Entire account evaluation amount
        account_total_buy_amount: Entire account buy amount
        total_position_count: Total number of held positions (replaces AccountPnLEvent.position_count)

        # Account product-specific P&L
        account_overseas_stock_pnl_rate: Overseas stock account P&L rate (%)
        account_overseas_stock_pnl_amount: Overseas stock account P&L amount
        account_overseas_futures_pnl_rate: Overseas futures account P&L rate (%)
        account_overseas_futures_pnl_amount: Overseas futures account P&L amount
        account_korea_stock_pnl_rate: Korea stock account P&L rate (%)
        account_korea_stock_pnl_amount: Korea stock account P&L amount

        # Metadata
        workflow_start_datetime: Job start datetime (fixed reference)
        workflow_elapsed_days: Days since workflow started

        # Competition fields (only if listener has start_date)
        competition_start_date: Competition start date (YYYYMMDD)
        competition_workflow_pnl_rate: Workflow P&L from competition start date
        competition_workflow_pnl_amount: Workflow P&L amount from competition start date
        competition_workflow_overseas_stock_pnl_rate: Overseas stock workflow P&L from competition start date
        competition_workflow_overseas_stock_pnl_amount: Overseas stock workflow P&L amount from competition start date
        competition_workflow_overseas_futures_pnl_rate: Overseas futures workflow P&L from competition start date
        competition_workflow_overseas_futures_pnl_amount: Overseas futures workflow P&L amount from competition start date
        competition_workflow_korea_stock_pnl_rate: Korea stock workflow P&L from competition start date
        competition_workflow_korea_stock_pnl_amount: Korea stock workflow P&L amount from competition start date
        competition_account_pnl_rate: Account P&L from competition start date
        competition_account_pnl_amount: Account P&L amount from competition start date
        competition_account_overseas_stock_pnl_rate: Overseas stock account P&L from competition start date
        competition_account_overseas_stock_pnl_amount: Overseas stock account P&L amount from competition start date
        competition_account_overseas_futures_pnl_rate: Overseas futures account P&L from competition start date
        competition_account_overseas_futures_pnl_amount: Overseas futures account P&L amount from competition start date
        competition_account_korea_stock_pnl_rate: Korea stock account P&L from competition start date
        competition_account_korea_stock_pnl_amount: Korea stock account P&L amount from competition start date
    
    Example:
        class CompetitionListener(BaseExecutionListener):
            def __init__(self):
                super().__init__(start_date="20260115")  # 대회 시작일
            
            async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
                # Use workflow_pnl_rate for official competition ranking
                await update_leaderboard(event.job_id, event.workflow_pnl_rate)
                # Use competition_workflow_pnl_rate if start_date filtering is needed
                if event.competition_workflow_pnl_rate is not None:
                    print(f"Competition P&L: {event.competition_workflow_pnl_rate}%")
    """
    job_id: str
    broker_node_id: str
    product: str  # "overseas_stock" | "overseas_futures" | "korea_stock"

    # Workflow position P&L
    workflow_pnl_rate: Union[Decimal, float]
    workflow_eval_amount: Union[Decimal, float]
    workflow_buy_amount: Union[Decimal, float]
    workflow_pnl_amount: Union[Decimal, float]
    
    # Other (manual/unknown) position P&L
    other_pnl_rate: Union[Decimal, float]
    other_eval_amount: Union[Decimal, float]
    other_buy_amount: Union[Decimal, float]
    other_pnl_amount: Union[Decimal, float]
    
    # Total account P&L
    total_pnl_rate: Union[Decimal, float]
    total_eval_amount: Union[Decimal, float]
    total_buy_amount: Union[Decimal, float]
    total_pnl_amount: Union[Decimal, float]
    
    # Position details
    workflow_positions: list = field(default_factory=list)  # List[PositionDetail]
    other_positions: list = field(default_factory=list)     # List[PositionDetail]
    
    # Trust metrics
    trust_score: int = 100  # 0-100, starts at 100
    anomaly_count: int = 0

    # Trading mode
    paper_trading: bool = False  # True: 모의투자, False: 실전투자

    # Metadata
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # ========== NEW FIELDS (v2.0) ==========

    # Workflow product-specific P&L
    workflow_overseas_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    workflow_overseas_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    workflow_overseas_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    workflow_overseas_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    workflow_korea_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    workflow_korea_stock_pnl_amount: Optional[Union[Decimal, float]] = None

    # Account total P&L (all brokers combined)
    account_total_pnl_rate: Optional[Union[Decimal, float]] = None
    account_total_pnl_amount: Optional[Union[Decimal, float]] = None
    account_total_eval_amount: Optional[Union[Decimal, float]] = None
    account_total_buy_amount: Optional[Union[Decimal, float]] = None

    # Total position count (replaces AccountPnLEvent.position_count)
    total_position_count: int = 0

    # Account product-specific P&L
    account_overseas_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    account_overseas_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    account_overseas_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    account_overseas_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    account_korea_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    account_korea_stock_pnl_amount: Optional[Union[Decimal, float]] = None

    # Workflow metadata
    workflow_start_datetime: Optional[datetime] = None  # Job start time (fixed)
    workflow_elapsed_days: Optional[int] = None  # Days since workflow started

    # Competition fields (calculated when listener has start_date)
    competition_start_date: Optional[str] = None  # YYYYMMDD format

    # Competition workflow P&L
    competition_workflow_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_workflow_overseas_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_overseas_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_workflow_overseas_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_overseas_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_workflow_korea_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_korea_stock_pnl_amount: Optional[Union[Decimal, float]] = None

    # Competition account P&L
    competition_account_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_account_overseas_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_overseas_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_account_overseas_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_overseas_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_account_korea_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_korea_stock_pnl_amount: Optional[Union[Decimal, float]] = None


# ============================================================
# Risk 이벤트
# ============================================================

@dataclass
class RiskEvent:
    """위험 임계값 초과 시 발생하는 이벤트."""
    job_id: str
    event_type: str     # "trailing_stop_triggered" | "drawdown_alert" | ...
    severity: str       # "info" | "warning" | "critical"
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    action_hint: str = "advisory"  # "advisory" | "halt_orders" (M-10)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================
# AI Agent 이벤트
# ============================================================

@dataclass
class LLMStreamEvent:
    """
    LLM 토큰 스트리밍 이벤트.

    AI Agent 노드가 LLM 응답을 스트리밍할 때 발생.
    UI에서 실시간 타이핑 효과 표시에 사용.

    Attributes:
        job_id: Job 식별자
        node_id: AIAgentNode ID
        token: 수신된 토큰 텍스트
        is_final: 마지막 토큰 여부
        timestamp: 이벤트 시각
    """
    job_id: str
    node_id: str
    token: str
    is_final: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TokenUsageEvent:
    """
    토큰 사용량 이벤트.

    AI Agent 노드의 LLM 호출 완료 후 발생.
    비용 추적 및 사용량 모니터링에 사용.

    Attributes:
        job_id: Job 식별자
        node_id: AIAgentNode ID
        model: 사용된 LLM 모델명
        input_tokens: 입력 토큰 수
        output_tokens: 출력 토큰 수
        total_tokens: 총 토큰 수
        cost_usd: 예상 비용 (USD)
        timestamp: 이벤트 시각
    """
    job_id: str
    node_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float = 0.0
    accumulated_tokens: int = 0  # 워크플로우 내 누적 총 토큰 수 (M-3)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIToolCallEvent:
    """
    AI Tool 호출 이벤트.

    AI Agent가 tool 엣지로 연결된 노드를 호출할 때 발생.
    UI에서 "🛠️ get_price(AAPL) 호출 중" 표시에 사용.

    Attributes:
        job_id: Job 식별자
        node_id: AIAgentNode ID
        tool_name: 호출된 Tool 이름
        tool_node_id: Tool로 사용된 노드의 ID
        tool_input: Tool에 전달된 인자
        tool_output: Tool 실행 결과 (완료 시)
        duration_ms: 실행 시간 (ms, 완료 시)
        timestamp: 이벤트 시각
    """
    job_id: str
    node_id: str
    tool_name: str
    tool_node_id: str
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_output: Any = None
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================
# Notification 이벤트
# ============================================================

class NotificationCategory(str, Enum):
    """알림 카테고리 — 변화가 있을 때만 발행되는 공지"""
    SIGNAL_TRIGGERED = "signal_triggered"       # 전략 시그널 발생 (분석 결과)
    RISK_ALERT = "risk_alert"                   # 리스크 경고 (drawdown 등)
    RISK_HALT = "risk_halt"                     # Kill Switch / 긴급 정지
    WORKFLOW_STARTED = "workflow_started"        # 워크플로우 시작
    WORKFLOW_COMPLETED = "workflow_completed"    # 워크플로우 완료
    WORKFLOW_FAILED = "workflow_failed"          # 워크플로우 실패
    RETRY_EXHAUSTED = "retry_exhausted"         # 재시도 모두 소진 (최종 실패)
    SCHEDULE_STARTED = "schedule_started"       # 스케줄 사이클 시작


class NotificationSeverity(str, Enum):
    """알림 심각도"""
    INFO = "info"           # 정보 (시작/완료, 시그널)
    WARNING = "warning"     # 주의 (리스크 경고, 재시도 소진)
    CRITICAL = "critical"   # 긴급 (Kill Switch, 워크플로우 실패)


@dataclass
class NotificationEvent:
    """
    투자자 알림 이벤트.

    on_log는 개발/디버깅용, on_notification은 투자자에게 전달할 핵심 정보.
    소비자: (1) 투자자, (2) 외부 메시징 (텔레그램/카톡), (3) 외부 AI 모델.

    Attributes:
        job_id: Job 식별자
        category: 알림 카테고리
        severity: 심각도
        title: 짧은 제목
        message: 상세 내용
        node_id: 관련 노드 ID (optional)
        node_type: 관련 노드 타입 (optional)
        data: 구조화된 데이터 (카테고리별, AI 소비용)
        timestamp: 이벤트 시각
    """
    job_id: str
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    message: str
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RestartEvent:
    """워크플로우 복구 시 발생하는 이벤트.

    checkpoint에서 복원하거나 복구 실패 시 발행됩니다.

    Attributes:
        job_id: Job 식별자
        restart_reason: 복구 사유 ("checkpoint_restore" | "restore_failed")
        checkpoint_age_sec: 체크포인트 경과 시간 (초)
        workflow_type: 워크플로우 유형 ("oneshot" | "realtime")
        skipped_nodes: 스킵된 완료 노드 목록
        data_gap_warning: 데이터 갭 경고 메시지 (없으면 None)
        timestamp: 이벤트 시각
    """
    job_id: str
    restart_reason: str
    checkpoint_age_sec: float
    workflow_type: str
    skipped_nodes: List[str] = field(default_factory=list)
    data_gap_warning: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class ExecutionListener(Protocol):
    """
    Protocol for receiving workflow execution state callbacks.

    Implement this protocol to receive real-time updates about
    node execution, edge data transmission, and job state changes.

    Methods:
        on_node_state_change: Called when node state changes
        on_edge_state_change: Called when edge state changes
        on_log: Called when log entry is created
        on_job_state_change: Called when job state changes
        on_display_data: Called when DisplayNode produces visualization data
        on_workflow_pnl_update: Called when workflow P&L is updated (realtime)
        on_retry: Called when a node retry is attempted
    """
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        """
        Called when a node's execution state changes.
        
        Args:
            event: NodeStateEvent with node_id, state, outputs, etc.
        """
        ...
    
    async def on_edge_state_change(self, event: EdgeStateEvent) -> None:
        """
        Called when an edge's data transmission state changes.
        
        Args:
            event: EdgeStateEvent with from/to node IDs, state, etc.
        """
        ...
    
    async def on_log(self, event: LogEvent) -> None:
        """
        Called when a log entry is created.
        
        Args:
            event: LogEvent with level, message, node_id, etc.
        """
        ...
    
    async def on_job_state_change(self, event: JobStateEvent) -> None:
        """
        Called when the job's overall state changes.
        
        Args:
            event: JobStateEvent with job_id, state, stats, etc.
        """
        ...
    
    async def on_display_data(self, event: 'DisplayDataEvent') -> None:
        """
        Called when a DisplayNode produces visualization data.
        
        Args:
            event: DisplayDataEvent with chart_type, data, etc.
        """
        ...

    async def on_workflow_pnl_update(self, event: 'WorkflowPnLEvent') -> None:
        """
        Called when workflow position P&L is updated (realtime tracking).

        Tracks both workflow-generated positions and manual positions separately
        using FIFO tracking. Includes total account P&L and position count.
        Use this for competition ranking.

        Args:
            event: WorkflowPnLEvent with workflow-specific P&L data.
        """
        ...

    async def on_retry(self, event: 'RetryEvent') -> None:
        """
        Called when a node retry is attempted.

        UI에서 "재시도 중 (2/3)..." 표시용.

        Args:
            event: RetryEvent with attempt count, error type, next retry delay, etc.
        """
        ...

    async def on_llm_stream(self, event: LLMStreamEvent) -> None:
        """
        Called when LLM produces a streaming token.

        UI에서 실시간 타이핑 효과 표시용.

        Args:
            event: LLMStreamEvent with token text and is_final flag.
        """
        ...

    async def on_token_usage(self, event: TokenUsageEvent) -> None:
        """
        Called when LLM call completes with token usage info.

        비용 추적 및 사용량 모니터링용.

        Args:
            event: TokenUsageEvent with model, token counts, cost.
        """
        ...

    async def on_ai_tool_call(self, event: AIToolCallEvent) -> None:
        """
        Called when AI Agent calls a tool (node connected via tool edge).

        UI에서 Tool 호출 상태 표시용.

        Args:
            event: AIToolCallEvent with tool name, input, output.
        """
        ...

    async def on_risk_event(self, event: 'RiskEvent') -> None:
        """
        Called when a risk threshold is breached.

        위험 임계값 초과, 트레일링 스탑 트리거 등 위험관리 이벤트 발생 시.

        Args:
            event: RiskEvent with event_type, severity, symbol, details.
        """
        ...

    async def on_restart(self, event: 'RestartEvent') -> None:
        """
        Called when workflow is restored from checkpoint.

        서버 재시작 후 체크포인트 복구 시 발생.

        Args:
            event: RestartEvent with restart_reason, skipped_nodes, data_gap_warning.
        """
        ...

    async def on_notification(self, event: 'NotificationEvent') -> None:
        """
        Called when an important notification is emitted for the investor.

        투자자에게 전달할 핵심 정보 (시그널, 리스크, 워크플로우 상태 등).
        on_log와 달리 변화가 있을 때만 발행되는 공지 성격.

        Args:
            event: NotificationEvent with category, severity, title, message, data.
        """
        ...


class BaseExecutionListener:
    """
    Base implementation of ExecutionListener with no-op methods.
    Subclass this to implement only the callbacks you need.
    
    Args:
        start_date: Optional competition start date (YYYYMMDD format).
                    If provided, competition_* fields in WorkflowPnLEvent
                    will be calculated from this date.
    
    Example:
        class MyListener(BaseExecutionListener):
            def __init__(self):
                super().__init__(start_date="20260115")  # 대회 시작일
            
            async def on_node_state_change(self, event):
                if event.state == NodeState.COMPLETED:
                    print(f"✓ {event.node_id} completed")
    """
    
    def __init__(self, start_date: Optional[str] = None):
        """
        Initialize the listener.
        
        Args:
            start_date: Competition start date (YYYYMMDD format).
                       Used to filter P&L calculation from this date.
        """
        self.pnl_start_date = start_date
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        """Default implementation: do nothing"""
        pass
    
    async def on_edge_state_change(self, event: EdgeStateEvent) -> None:
        """Default implementation: do nothing"""
        pass
    
    async def on_log(self, event: LogEvent) -> None:
        """Default implementation: do nothing"""
        pass
    
    async def on_job_state_change(self, event: JobStateEvent) -> None:
        """Default implementation: do nothing"""
        pass
    
    async def on_display_data(self, event: DisplayDataEvent) -> None:
        """Default implementation: do nothing"""
        pass

    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """Default implementation: do nothing"""
        pass

    async def on_retry(self, event: 'RetryEvent') -> None:
        """Default implementation: do nothing"""
        pass

    async def on_llm_stream(self, event: LLMStreamEvent) -> None:
        """Default implementation: do nothing"""
        pass

    async def on_token_usage(self, event: TokenUsageEvent) -> None:
        """Default implementation: do nothing"""
        pass

    async def on_ai_tool_call(self, event: AIToolCallEvent) -> None:
        """Default implementation: do nothing"""
        pass

    async def on_risk_event(self, event: 'RiskEvent') -> None:
        """Default implementation: do nothing"""
        pass

    async def on_restart(self, event: 'RestartEvent') -> None:
        """Default implementation: do nothing"""
        pass

    async def on_notification(self, event: 'NotificationEvent') -> None:
        """Default implementation: do nothing"""
        pass


class ConsoleExecutionListener(BaseExecutionListener):
    """
    Listener that prints all events to console for debugging.
    
    Example:
        job = await pg.run_async(workflow, listeners=[ConsoleExecutionListener()])
    """
    
    def __init__(self, verbose: bool = False, start_date: Optional[str] = None):
        """
        Args:
            verbose: If True, also print edge events. If False, only node/job events.
            start_date: Optional competition start date (YYYYMMDD format).
        """
        super().__init__(start_date=start_date)
        self.verbose = verbose
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        state_emoji = {
            NodeState.PENDING: "⏳",
            NodeState.RUNNING: "🔄",
            NodeState.COMPLETED: "✅",
            NodeState.FAILED: "❌",
            NodeState.SKIPPED: "⏭️",
        }
        emoji = state_emoji.get(event.state, "❓")
        
        msg = f"{emoji} [{event.node_id}] {event.state.value}"
        if event.duration_ms:
            msg += f" ({event.duration_ms:.1f}ms)"
        if event.error:
            msg += f" - {event.error}"
        
        print(msg)
    
    async def on_edge_state_change(self, event: EdgeStateEvent) -> None:
        if not self.verbose:
            return
        
        state_emoji = {
            EdgeState.IDLE: "⚪",
            EdgeState.TRANSMITTING: "🔵",
            EdgeState.TRANSMITTED: "🟢",
        }
        emoji = state_emoji.get(event.state, "❓")
        
        print(f"{emoji} {event.from_node_id}.{event.from_port} → {event.to_node_id}.{event.to_port}")
    
    async def on_log(self, event: LogEvent) -> None:
        level_color = {
            "debug": "\033[90m",    # Gray
            "info": "\033[92m",     # Green
            "warning": "\033[93m",  # Yellow
            "error": "\033[91m",    # Red
        }
        reset = "\033[0m"
        color = level_color.get(event.level, "")
        
        node_tag = f"[{event.node_id}] " if event.node_id else ""
        print(f"{color}{event.level.upper():>7}{reset} {node_tag}{event.message}")
    
    async def on_job_state_change(self, event: JobStateEvent) -> None:
        state_emoji = {
            "pending": "⏳",
            "running": "🚀",
            "completed": "🎉",
            "failed": "💥",
            "cancelled": "🛑",
            "stopping": "🔻",
        }
        emoji = state_emoji.get(event.state, "❓")
        
        print(f"\n{emoji} Job [{event.job_id}] → {event.state}")
        if event.stats:
            print(f"   Stats: {event.stats}")

    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """Print workflow P&L update for debugging"""
        wf_pnl = float(event.workflow_pnl_rate)
        total_pnl = float(event.total_pnl_rate)

        wf_emoji = "📈" if wf_pnl >= 0 else "📉"
        wf_color = "\033[92m" if wf_pnl >= 0 else "\033[91m"
        reset = "\033[0m"

        trust_badge = "🟢" if event.trust_score >= 80 else "🟡" if event.trust_score >= 50 else "🔴"

        print(f"{wf_emoji} [{event.broker_node_id}] Workflow: {wf_color}{wf_pnl:+.2f}%{reset} "
              f"| Total: {total_pnl:+.2f}% | Positions: {event.total_position_count} "
              f"| Trust: {trust_badge} {event.trust_score}")

    async def on_retry(self, event: 'RetryEvent') -> None:
        """Print retry event for debugging"""
        from programgarden_core.models.resilience import RetryEvent as _RetryEvent

        yellow = "\033[93m"
        reset = "\033[0m"

        print(f"{yellow}⚠️  [{event.node_id}] {event.error_type.value} 발생, "
              f"재시도 중 ({event.attempt}/{event.max_retries})... "
              f"{event.next_retry_in:.1f}초 후{reset}")

    async def on_risk_event(self, event: 'RiskEvent') -> None:
        """Print risk event with severity-based coloring"""
        severity_style = {
            "info": ("\033[94m", "ℹ️"),       # Blue
            "warning": ("\033[93m", "⚠️"),    # Yellow
            "critical": ("\033[91m", "🚨"),   # Red
        }
        reset = "\033[0m"
        color, emoji = severity_style.get(event.severity, ("\033[0m", "❓"))

        symbol_tag = f" [{event.symbol}]" if event.symbol else ""
        print(f"{color}{emoji} RISK {event.severity.upper()}{symbol_tag} "
              f"{event.event_type}: {event.details}{reset}")

    async def on_notification(self, event: 'NotificationEvent') -> None:
        """Print notification event with severity-based coloring"""
        severity_style = {
            "info": ("\033[94m", "ℹ️"),       # Blue
            "warning": ("\033[93m", "⚠️"),    # Yellow
            "critical": ("\033[91m", "🚨"),   # Red
        }
        reset = "\033[0m"
        sev = event.severity.value if isinstance(event.severity, Enum) else event.severity
        color, emoji = severity_style.get(sev, ("\033[0m", "❓"))

        cat = event.category.value if isinstance(event.category, Enum) else event.category
        node_tag = f" [{event.node_id}]" if event.node_id else ""
        print(f"{color}{emoji} NOTIFY {cat.upper()}{node_tag} {event.title}{reset}")
        if event.message:
            print(f"   {event.message}")
