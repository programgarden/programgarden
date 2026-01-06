"""
ProgramGarden - ExecutionContext

Workflow execution context protocol
- Data transfer between nodes
- Realtime data injection
- State management
"""

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from programgarden_core.expression import ExpressionContext


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
    ):
        self.job_id = job_id
        self.workflow_id = workflow_id
        self.context_params = context_params or {}

        # Secrets storage (never logged, separate from context_params)
        self._secrets: Dict[str, Any] = secrets or {}

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

        # Event handlers
        self._event_handlers: Dict[str, List[callable]] = {}

        # Logs
        self._logs: List[Dict[str, Any]] = []

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

    def start(self) -> None:
        """Start execution"""
        self._is_running = True
        self._is_paused = False

    def pause(self) -> None:
        """Pause execution"""
        self._is_paused = True

    def resume(self) -> None:
        """Resume execution"""
        self._is_paused = False

    def stop(self) -> None:
        """Stop execution"""
        self._is_running = False

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

    # === Logging ===

    def log(
        self,
        level: str,
        message: str,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record log entry"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "node_id": node_id,
            "data": data,
        }
        self._logs.append(log_entry)

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

        Converts all node outputs to be accessible in expressions
        """
        expr_context = ExpressionContext()

        # Add node outputs
        for node_id, outputs in self._outputs.items():
            for port_name, output in outputs.items():
                expr_context.set_node_output(node_id, port_name, output.value)

        # Add realtime data
        expr_context.variables.update(self._realtime_data)

        # Add context parameters
        expr_context.variables["context"] = self.context_params

        return expr_context
