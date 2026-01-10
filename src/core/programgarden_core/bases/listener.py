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

from typing import Protocol, Optional, Dict, Any, runtime_checkable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class NodeState(str, Enum):
    """Node execution state"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


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


class BaseExecutionListener:
    """
    Base implementation of ExecutionListener with no-op methods.
    Subclass this to implement only the callbacks you need.
    
    Example:
        class MyListener(BaseExecutionListener):
            async def on_node_state_change(self, event):
                if event.state == NodeState.COMPLETED:
                    print(f"✓ {event.node_id} completed")
    """
    
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


class ConsoleExecutionListener(BaseExecutionListener):
    """
    Listener that prints all events to console for debugging.
    
    Example:
        job = await pg.run_async(workflow, listeners=[ConsoleExecutionListener()])
    """
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: If True, also print edge events. If False, only node/job events.
        """
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
