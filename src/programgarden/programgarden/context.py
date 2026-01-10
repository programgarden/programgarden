"""
ProgramGarden - ExecutionContext

Workflow execution context protocol
- Data transfer between nodes
- Realtime data injection
- State management
- Event system for realtime updates
- Persistent node lifecycle management
"""

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable, Callable, Awaitable, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging

from programgarden_core.expression import ExpressionContext
from programgarden_core.bases.listener import (
    ExecutionListener,
    NodeState,
    EdgeState,
    NodeStateEvent,
    EdgeStateEvent,
    LogEvent,
    JobStateEvent,
    DisplayDataEvent,
)

logger = logging.getLogger("programgarden.context")


@runtime_checkable
class DataProvider(Protocol):
    """Data provider protocol"""

    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        ...

    async def get_ohlcv(
        self, symbol: str, period: str, count: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Get OHLCV data"""
        ...


@runtime_checkable
class AccountProvider(Protocol):
    """Account information provider protocol"""

    async def get_balance(self) -> Dict[str, Any]:
        """Get balance"""
        ...

    async def get_positions(self) -> Dict[str, Any]:
        """Get positions"""
        ...

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get open orders"""
        ...


@runtime_checkable
class OrderExecutor(Protocol):
    """Order executor protocol"""

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Submit order"""
        ...

    async def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Modify order"""
        ...

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        ...


@dataclass
class NodeOutput:
    """Node output value"""

    node_id: str
    port_name: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowEvent:
    """Event for realtime updates and triggers"""
    
    type: str  # "realtime_update" | "schedule_tick" | "order_filled" | etc.
    source_node_id: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trigger_nodes: List[str] = field(default_factory=list)  # Nodes to trigger on this event


class ExecutionContext:
    """
    Workflow execution context

    Handles data transfer between nodes, realtime data injection, and state management.

    Attributes:
        context_params: Runtime parameters (symbols, dry_run, backtest options, etc.)
        _secrets: Sensitive credentials (appkey, appsecret, etc.) - never logged
    """

    def __init__(
        self,
        job_id: str,
        workflow_id: str,
        context_params: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        workflow_inputs: Optional[Dict[str, Any]] = None,
    ):
        self.job_id = job_id
        self.workflow_id = workflow_id
        self.context_params = context_params or {}

        # Secrets storage (never logged, separate from context_params)
        self._secrets: Dict[str, Any] = secrets or {}
        
        # Workflow inputs schema (for {{ input.xxx }} expressions)
        self._workflow_inputs: Dict[str, Any] = workflow_inputs or {}

        # Node output storage
        self._outputs: Dict[str, Dict[str, NodeOutput]] = {}

        # Realtime data buffer
        self._realtime_data: Dict[str, Any] = {}

        # Providers
        self._data_provider: Optional[DataProvider] = None
        self._account_provider: Optional[AccountProvider] = None
        self._order_executor: Optional[OrderExecutor] = None

        # State
        self._is_running = False
        self._is_paused = False
        self._is_failed = False
        self._failure_reason: Optional[str] = None

        # Event handlers
        self._event_handlers: Dict[str, List[callable]] = {}

        # Logs
        self._logs: List[Dict[str, Any]] = []
        
        # === New: Event Queue for realtime updates ===
        self._event_queue: asyncio.Queue[WorkflowEvent] = asyncio.Queue()
        
        # === New: Persistent node management ===
        # Stores trackers/connections that should stay alive between flow executions
        self._persistent_nodes: Dict[str, Any] = {}  # node_id -> tracker/connection
        self._persistent_tasks: Dict[str, asyncio.Task] = {}  # node_id -> background task
        
        # === New: Cleanup on flow end (stay_connected=False) ===
        # Stores trackers that should be cleaned up after each flow execution
        self._cleanup_on_flow_end: Dict[str, Any] = {}  # node_id -> tracker/connection
        
        # === New: Execution Listeners (for UI/Server callbacks) ===
        self._listeners: List[ExecutionListener] = []

    # === Provider Configuration ===

    def set_data_provider(self, provider: DataProvider) -> None:
        """Set data provider"""
        self._data_provider = provider

    def set_account_provider(self, provider: AccountProvider) -> None:
        """Set account provider"""
        self._account_provider = provider

    def set_order_executor(self, executor: OrderExecutor) -> None:
        """Set order executor"""
        self._order_executor = executor

    # === Secrets Management ===

    def get_secret(self, key: str) -> Optional[Any]:
        """
        Get secret value by key

        Args:
            key: Secret key (e.g., 'credential_id', 'telegram_token')

        Returns:
            Secret value or None
        """
        return self._secrets.get(key)

    def set_secret(self, key: str, value: Any) -> None:
        """
        Set secret value

        Args:
            key: Secret key (e.g., 'credential_id')
            value: Secret value (e.g., {'appkey': '...', 'appsecret': '...'})
        """
        self._secrets[key] = value

    def get_credential(self, credential_id: str = "credential_id") -> Optional[Dict[str, Any]]:
        """
        Get credential (appkey, appsecret) by credential_id

        Args:
            credential_id: Credential identifier (default: 'credential_id')

        Returns:
            Dict with 'appkey', 'appsecret' or None
        """
        return self._secrets.get(credential_id)

    def has_secret(self, key: str) -> bool:
        """Check if secret exists"""
        return key in self._secrets

    # === Node Output Management ===

    def set_output(
        self,
        node_id: str,
        port_name: str,
        value: Any,
    ) -> None:
        """Set node output"""
        if node_id not in self._outputs:
            self._outputs[node_id] = {}

        self._outputs[node_id][port_name] = NodeOutput(
            node_id=node_id,
            port_name=port_name,
            value=value,
        )

    def get_output(
        self,
        node_id: str,
        port_name: Optional[str] = None,
    ) -> Optional[Any]:
        """Get node output"""
        node_outputs = self._outputs.get(node_id, {})

        if port_name:
            output = node_outputs.get(port_name)
            return output.value if output else None

        # Return first output if no port name specified
        if node_outputs:
            first_output = list(node_outputs.values())[0]
            return first_output.value

        return None

    def get_all_outputs(self, node_id: str) -> Dict[str, Any]:
        """Get all outputs for a node as {port_name: value} dict"""
        node_outputs = self._outputs.get(node_id, {})
        return {port: output.value for port, output in node_outputs.items()}

    def get_input(
        self,
        from_node_id: str,
        from_port: Optional[str],
    ) -> Optional[Any]:
        """Get input value connected via edge"""
        return self.get_output(from_node_id, from_port)

    # === Realtime Data ===

    def update_realtime_data(self, key: str, value: Any) -> None:
        """Update realtime data"""
        self._realtime_data[key] = value

    def get_realtime_data(self, key: str) -> Optional[Any]:
        """Get realtime data"""
        return self._realtime_data.get(key)

    # === Data Query (Provider Delegation) ===

    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        if self._data_provider:
            return await self._data_provider.get_price(symbol)
        return None

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get OHLCV data"""
        if self._data_provider:
            return await self._data_provider.get_ohlcv(symbol, period, count)
        return None

    async def get_balance(self) -> Dict[str, Any]:
        """Get balance"""
        if self._account_provider:
            return await self._account_provider.get_balance()
        return {}

    async def get_positions(self) -> Dict[str, Any]:
        """Get positions"""
        if self._account_provider:
            return await self._account_provider.get_positions()
        return {}

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get open orders"""
        if self._account_provider:
            return await self._account_provider.get_open_orders()
        return []

    # === Order Execution (Executor Delegation) ===

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Submit order"""
        if self._order_executor:
            return await self._order_executor.submit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
            )
        return {"error": "Order executor not configured"}

    async def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Modify order"""
        if self._order_executor:
            return await self._order_executor.modify_order(
                order_id=order_id,
                price=price,
                quantity=quantity,
            )
        return {"error": "Order executor not configured"}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        if self._order_executor:
            return await self._order_executor.cancel_order(order_id)
        return {"error": "Order executor not configured"}

    # === State Management ===

    @property
    def secrets(self) -> Dict[str, Any]:
        """Get all secrets (read-only access)"""
        return self._secrets

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_failed(self) -> bool:
        return self._is_failed

    @property
    def failure_reason(self) -> Optional[str]:
        return self._failure_reason

    def start(self) -> None:
        """Start execution"""
        self._is_running = True
        self._is_paused = False
        self._is_failed = False
        self._failure_reason = None

    def pause(self) -> None:
        """Pause execution"""
        self._is_paused = True

    def resume(self) -> None:
        """Resume execution"""
        self._is_paused = False

    def stop(self) -> None:
        """Stop execution"""
        self._is_running = False

    def fail(self, reason: str) -> None:
        """Mark execution as failed"""
        self._is_failed = True
        self._is_running = False
        self._failure_reason = reason
        self.log("error", f"Job failed: {reason}")

    # === Event Queue (for realtime updates) ===

    async def emit_event(
        self,
        event_type: str,
        source_node_id: str,
        data: Any = None,
        trigger_nodes: Optional[List[str]] = None,
    ) -> None:
        """
        Emit event to the queue (for realtime updates)
        
        Args:
            event_type: Type of event (e.g., "realtime_update", "schedule_tick")
            source_node_id: Node that generated the event
            data: Event payload
            trigger_nodes: List of node IDs to trigger (from edge trigger: "on_update")
        """
        event = WorkflowEvent(
            type=event_type,
            source_node_id=source_node_id,
            data=data,
            trigger_nodes=trigger_nodes or [],
        )
        await self._event_queue.put(event)

    async def wait_for_event(self, timeout: Optional[float] = None) -> Optional[WorkflowEvent]:
        """
        Wait for next event from queue
        
        Args:
            timeout: Max seconds to wait (None = wait forever)
            
        Returns:
            WorkflowEvent or None if timeout
        """
        try:
            if timeout:
                return await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=timeout,
                )
            return await self._event_queue.get()
        except asyncio.TimeoutError:
            return None

    def has_pending_events(self) -> bool:
        """Check if there are pending events"""
        return not self._event_queue.empty()

    # === Persistent Node Management ===

    def register_persistent(self, node_id: str, tracker: Any) -> None:
        """
        Register a persistent tracker/connection
        
        Args:
            node_id: Node ID
            tracker: StockAccountTracker or similar object with start()/stop()
        """
        self._persistent_nodes[node_id] = tracker
        logger.debug(f"Registered persistent node: {node_id}")

    def get_persistent(self, node_id: str) -> Optional[Any]:
        """Get registered persistent tracker"""
        return self._persistent_nodes.get(node_id)

    def has_persistent(self, node_id: str) -> bool:
        """Check if node has persistent tracker"""
        return node_id in self._persistent_nodes

    def register_persistent_task(self, node_id: str, task: asyncio.Task) -> None:
        """Register background task for persistent node"""
        self._persistent_tasks[node_id] = task

    async def cleanup_persistent_nodes(self) -> None:
        """
        Cleanup all persistent nodes (call on job stop)
        """
        # Stop all trackers
        for node_id, tracker in self._persistent_nodes.items():
            try:
                if hasattr(tracker, 'stop'):
                    if asyncio.iscoroutinefunction(tracker.stop):
                        await tracker.stop()
                    else:
                        tracker.stop()
                logger.debug(f"Stopped persistent node: {node_id}")
            except Exception as e:
                logger.warning(f"Error stopping persistent node {node_id}: {e}")
        
        # Cancel all background tasks
        for node_id, task in self._persistent_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.debug(f"Cancelled persistent task: {node_id}")
        
        self._persistent_nodes.clear()
        self._persistent_tasks.clear()

    # === Cleanup on Flow End (stay_connected=False) ===

    def register_cleanup_on_flow_end(self, node_id: str, tracker: Any) -> None:
        """
        Register a tracker to be cleaned up after each flow execution.
        
        Used for RealAccountNode with stay_connected=False:
        - WebSocket 연결은 하지만, 플로우가 끝나면 종료
        - persistent와 달리 스케줄 사이에는 유지되지 않음
        
        Args:
            node_id: Node ID
            tracker: StockAccountTracker or similar object with start()/stop()
        """
        self._cleanup_on_flow_end[node_id] = tracker
        logger.debug(f"Registered cleanup_on_flow_end node: {node_id}")

    async def cleanup_flow_end_nodes(self) -> None:
        """
        Cleanup nodes registered for flow-end cleanup.
        
        Called after each flow execution (before entering event loop).
        """
        if not self._cleanup_on_flow_end:
            return
        
        logger.info(f"Cleaning up {len(self._cleanup_on_flow_end)} flow-end nodes")
        
        for node_id, tracker in self._cleanup_on_flow_end.items():
            try:
                if hasattr(tracker, 'stop'):
                    if asyncio.iscoroutinefunction(tracker.stop):
                        await tracker.stop()
                    else:
                        tracker.stop()
                logger.debug(f"Stopped flow-end node: {node_id}")
            except Exception as e:
                logger.warning(f"Error stopping flow-end node {node_id}: {e}")
        
        self._cleanup_on_flow_end.clear()

    # === Events ===

    def on(self, event_type: str, handler: callable) -> None:
        """Register event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def emit(self, event_type: str, data: Any = None) -> None:
        """Emit event"""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)

    # === Execution Listeners ===

    def add_listener(self, listener: ExecutionListener) -> None:
        """
        Register an execution listener for state callbacks.
        
        Args:
            listener: ExecutionListener implementation
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: ExecutionListener) -> None:
        """
        Remove a registered execution listener.
        
        Args:
            listener: Listener to remove
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def set_listeners(self, listeners: Optional[List[ExecutionListener]]) -> None:
        """
        Set listener list (replaces existing).
        
        Args:
            listeners: New listener list
        """
        self._listeners = list(listeners) if listeners else []

    async def notify_node_state(
        self,
        node_id: str,
        node_type: str,
        state: NodeState,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Notify all listeners about node state change."""
        logger.info(f"📡 notify_node_state: {node_id} ({node_type}) → {state.value}")
        
        if not self._listeners:
            logger.warning(f"⚠️ No listeners registered for node state notification!")
            return
        
        event = NodeStateEvent(
            job_id=self.job_id,
            node_id=node_id,
            node_type=node_type,
            state=state,
            outputs=self._sanitize_outputs(outputs),
            error=error,
            duration_ms=duration_ms,
        )
        
        for listener in self._listeners:
            try:
                await listener.on_node_state_change(event)
            except Exception as e:
                logger.warning(f"Listener error on_node_state_change: {e}")

    async def notify_edge_state(
        self,
        from_node_id: str,
        from_port: str,
        to_node_id: str,
        to_port: str,
        state: EdgeState,
        data: Any = None,
    ) -> None:
        """Notify all listeners about edge state change."""
        logger.debug(f"📡 notify_edge_state: {from_node_id}.{from_port} → {to_node_id}.{to_port} ({state.value})")
        
        if not self._listeners:
            return
        
        # Truncate data preview for security
        data_preview = None
        if data is not None:
            preview = str(data)
            data_preview = preview[:200] + "..." if len(preview) > 200 else preview
        
        event = EdgeStateEvent(
            job_id=self.job_id,
            from_node_id=from_node_id,
            from_port=from_port,
            to_node_id=to_node_id,
            to_port=to_port,
            state=state,
            data_preview=data_preview,
        )
        
        for listener in self._listeners:
            try:
                await listener.on_edge_state_change(event)
            except Exception as e:
                logger.warning(f"Listener error on_edge_state_change: {e}")

    async def notify_log(
        self,
        level: str,
        message: str,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Notify all listeners about log entry."""
        if not self._listeners:
            return
        
        event = LogEvent(
            job_id=self.job_id,
            level=level,
            message=message,
            node_id=node_id,
            data=data,
        )
        
        for listener in self._listeners:
            try:
                await listener.on_log(event)
            except Exception as e:
                logger.warning(f"Listener error on_log: {e}")

    async def notify_job_state(self, state: str, stats: Optional[Dict[str, Any]] = None) -> None:
        """Notify all listeners about job state change."""
        if not self._listeners:
            return
        
        event = JobStateEvent(
            job_id=self.job_id,
            state=state,
            stats=stats,
        )
        
        for listener in self._listeners:
            try:
                await listener.on_job_state_change(event)
            except Exception as e:
                logger.warning(f"Listener error on_job_state_change: {e}")

    async def notify_display_data(
        self,
        node_id: str,
        chart_type: str,
        title: Optional[str],
        data: Any,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Notify all listeners about display data from DisplayNode."""
        logger.debug(f"📡 notify_display_data: {node_id} ({chart_type})")
        
        if not self._listeners:
            return
        
        event = DisplayDataEvent(
            job_id=self.job_id,
            node_id=node_id,
            chart_type=chart_type,
            title=title,
            data=data,
            x_label=x_label,
            y_label=y_label,
            options=options,
        )
        
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_display_data'):
                    await listener.on_display_data(event)
            except Exception as e:
                logger.warning(f"Listener error on_display_data: {e}")

    def _sanitize_outputs(self, outputs: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove sensitive information from outputs."""
        if not outputs:
            return None
        
        # Filter sensitive keywords
        sensitive_keys = {"appkey", "appsecret", "secret", "password", "token", "api_key"}
        sanitized = {}
        
        for k, v in outputs.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_outputs(v)
            else:
                sanitized[k] = v
        
        return sanitized

    # === Logging ===

    def log(
        self,
        level: str,
        message: str,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record log entry and notify listeners"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "node_id": node_id,
            "data": data,
        }
        self._logs.append(log_entry)
        
        # Notify listeners (async, fire-and-forget)
        if self._listeners:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.notify_log(level, message, node_id, data))
            except RuntimeError:
                pass  # No event loop running

    def get_logs(
        self,
        level: Optional[str] = None,
        node_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get logs"""
        logs = self._logs

        if level:
            logs = [l for l in logs if l["level"] == level]
        if node_id:
            logs = [l for l in logs if l["node_id"] == node_id]

        return logs[-limit:]

    # === Expression Context ===

    def get_expression_context(self) -> ExpressionContext:
        """
        Create expression evaluation context

        Converts all node outputs to be accessible in expressions.
        Also provides `input` variable for workflow inputs.
        
        Available variables in expressions:
        - {{ nodeId.port }}: Node output values
        - {{ input.xxx }}: Workflow input parameters
        - {{ context.xxx }}: Runtime context parameters
        """
        expr_context = ExpressionContext()

        # Add node outputs
        for node_id, outputs in self._outputs.items():
            for port_name, output in outputs.items():
                expr_context.set_node_output(node_id, port_name, output.value)

        # Add realtime data
        expr_context.variables.update(self._realtime_data)

        # Add workflow inputs (merged: defaults + user overrides)
        merged_inputs = self._merge_inputs_with_defaults()
        expr_context.variables["input"] = merged_inputs

        # Add context parameters (for backward compatibility)
        expr_context.variables["context"] = self.context_params

        return expr_context

    def _merge_inputs_with_defaults(self) -> Dict[str, Any]:
        """
        Merge workflow input defaults with user-provided context_params.
        
        Priority: context_params > inputs[].default
        """
        result = {}
        
        # 1. Extract defaults from workflow inputs schema
        for name, schema in self._workflow_inputs.items():
            if isinstance(schema, dict):
                default_value = schema.get("default")
                if default_value is not None:
                    result[name] = default_value
        
        # 2. Override with user-provided context_params
        result.update(self.context_params)
        
        return result
