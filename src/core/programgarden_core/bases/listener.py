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

from typing import Protocol, Optional, Dict, Any, Union, runtime_checkable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


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
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccountPnLEvent:
    """
    Event emitted when account P&L (profit and loss) is updated.
    
    Used for real-time account tracking when BrokerNode is present.
    Emitted on every tick received for held positions.
    
    Server developers can throttle these events as needed.
    
    Attributes:
        job_id: Job identifier
        broker_node_id: BrokerNode ID that owns this account
        product: Product type ("overseas_stock" or "overseas_futures")
        provider: Broker provider (e.g., "ls-sec.co.kr")
        account_pnl_rate: Account P&L rate (total_pnl / total_buy * 100)
        total_eval_amount: Total evaluation amount
        total_buy_amount: Total buy amount
        total_pnl_amount: Total P&L amount (eval - buy)
        position_count: Number of held positions
        currency: Base currency (e.g., "USD")
        timestamp: Event timestamp
    
    Example:
        class MyListener(BaseExecutionListener):
            async def on_account_pnl_update(self, event: AccountPnLEvent) -> None:
                print(f"Account P&L: {event.account_pnl_rate:.2f}%")
                # Save to DB for competition ranking
                await db.update_ranking(event.job_id, event.account_pnl_rate)
    """
    job_id: str
    broker_node_id: str
    product: str  # "overseas_stock" | "overseas_futures"
    provider: str  # "ls-sec.co.kr"
    
    # Account P&L data
    account_pnl_rate: Union[Decimal, float]  # Total P&L rate (%)
    total_eval_amount: Union[Decimal, float]  # Total evaluation amount
    total_buy_amount: Union[Decimal, float]   # Total buy amount
    total_pnl_amount: Union[Decimal, float]   # Total P&L amount
    
    # Metadata
    position_count: int  # Number of held positions
    currency: str = "USD"  # Base currency
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
        product: Product type ("overseas_stock" or "overseas_futures")
        
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
        workflow_stock_pnl_rate: Stock-only workflow P&L rate (%)
        workflow_stock_pnl_amount: Stock-only workflow P&L amount
        workflow_futures_pnl_rate: Futures-only workflow P&L rate (%)
        workflow_futures_pnl_amount: Futures-only workflow P&L amount
        
        # Account total P&L
        account_total_pnl_rate: Entire account P&L rate (%)
        account_total_pnl_amount: Entire account P&L amount
        account_total_eval_amount: Entire account evaluation amount
        account_total_buy_amount: Entire account buy amount
        
        # Account product-specific P&L
        account_stock_pnl_rate: Stock-only account P&L rate (%)
        account_stock_pnl_amount: Stock-only account P&L amount
        account_futures_pnl_rate: Futures-only account P&L rate (%)
        account_futures_pnl_amount: Futures-only account P&L amount
        
        # Metadata
        workflow_start_datetime: Job start datetime (fixed reference)
        workflow_elapsed_days: Days since workflow started
        
        # Competition fields (only if listener has start_date)
        competition_start_date: Competition start date (YYYYMMDD)
        competition_workflow_pnl_rate: Workflow P&L from competition start date
        competition_workflow_pnl_amount: Workflow P&L amount from competition start date
        competition_workflow_stock_pnl_rate: Stock workflow P&L from competition start date
        competition_workflow_stock_pnl_amount: Stock workflow P&L amount from competition start date
        competition_workflow_futures_pnl_rate: Futures workflow P&L from competition start date
        competition_workflow_futures_pnl_amount: Futures workflow P&L amount from competition start date
        competition_account_pnl_rate: Account P&L from competition start date
        competition_account_pnl_amount: Account P&L amount from competition start date
        competition_account_stock_pnl_rate: Stock account P&L from competition start date
        competition_account_stock_pnl_amount: Stock account P&L amount from competition start date
        competition_account_futures_pnl_rate: Futures account P&L from competition start date
        competition_account_futures_pnl_amount: Futures account P&L amount from competition start date
    
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
    product: str  # "overseas_stock" | "overseas_futures"
    
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
    
    # Metadata
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # ========== NEW FIELDS (v2.0) ==========
    
    # Workflow product-specific P&L
    workflow_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    workflow_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    workflow_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    workflow_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    
    # Account total P&L (all brokers combined)
    account_total_pnl_rate: Optional[Union[Decimal, float]] = None
    account_total_pnl_amount: Optional[Union[Decimal, float]] = None
    account_total_eval_amount: Optional[Union[Decimal, float]] = None
    account_total_buy_amount: Optional[Union[Decimal, float]] = None
    
    # Account product-specific P&L
    account_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    account_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    account_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    account_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    
    # Workflow metadata
    workflow_start_datetime: Optional[datetime] = None  # Job start time (fixed)
    workflow_elapsed_days: Optional[int] = None  # Days since workflow started
    
    # Competition fields (calculated when listener has start_date)
    competition_start_date: Optional[str] = None  # YYYYMMDD format
    
    # Competition workflow P&L
    competition_workflow_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_workflow_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_workflow_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_workflow_futures_pnl_amount: Optional[Union[Decimal, float]] = None
    
    # Competition account P&L
    competition_account_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_account_stock_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_stock_pnl_amount: Optional[Union[Decimal, float]] = None
    competition_account_futures_pnl_rate: Optional[Union[Decimal, float]] = None
    competition_account_futures_pnl_amount: Optional[Union[Decimal, float]] = None


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
        on_account_pnl_update: Called when account P&L is updated (realtime)
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
    
    async def on_account_pnl_update(self, event: 'AccountPnLEvent') -> None:
        """
        Called when account P&L is updated (realtime tracking).
        
        This event is emitted on every tick for held positions when
        a listener with this method is registered. Server developers
        can implement throttling as needed.
        
        Args:
            event: AccountPnLEvent with account P&L data.
        """
        ...
    
    async def on_workflow_pnl_update(self, event: 'WorkflowPnLEvent') -> None:
        """
        Called when workflow position P&L is updated (realtime tracking).
        
        Unlike on_account_pnl_update which tracks the entire account,
        this event separates workflow-generated positions from manual positions
        using FIFO tracking. Use this for competition ranking.
        
        Args:
            event: WorkflowPnLEvent with workflow-specific P&L data.
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
    
    async def on_account_pnl_update(self, event: AccountPnLEvent) -> None:
        """Default implementation: do nothing"""
        pass
    
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
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
    
    async def on_account_pnl_update(self, event: AccountPnLEvent) -> None:
        """Print account P&L update for debugging"""
        pnl_rate = float(event.account_pnl_rate)
        emoji = "📈" if pnl_rate >= 0 else "📉"
        color = "\033[92m" if pnl_rate >= 0 else "\033[91m"  # Green or Red
        reset = "\033[0m"
        
        print(f"{emoji} [{event.broker_node_id}] {color}{pnl_rate:+.2f}%{reset} "
              f"(eval: {float(event.total_eval_amount):,.2f} {event.currency}, "
              f"positions: {event.position_count})")
    
    async def on_workflow_pnl_update(self, event: WorkflowPnLEvent) -> None:
        """Print workflow P&L update for debugging"""
        wf_pnl = float(event.workflow_pnl_rate)
        total_pnl = float(event.total_pnl_rate)
        
        wf_emoji = "📈" if wf_pnl >= 0 else "📉"
        wf_color = "\033[92m" if wf_pnl >= 0 else "\033[91m"
        reset = "\033[0m"
        
        trust_badge = "🟢" if event.trust_score >= 80 else "🟡" if event.trust_score >= 50 else "🔴"
        
        print(f"{wf_emoji} [{event.broker_node_id}] Workflow: {wf_color}{wf_pnl:+.2f}%{reset} "
              f"| Total: {total_pnl:+.2f}% | Trust: {trust_badge} {event.trust_score}")
