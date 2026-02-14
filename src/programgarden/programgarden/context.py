"""
ProgramGarden - ExecutionContext

Workflow execution context protocol
- Data transfer between nodes
- Realtime data injection
- State management
- Event system for realtime updates
- Persistent node lifecycle management
"""

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable, Callable, Awaitable, TYPE_CHECKING, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque
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
    WorkflowPnLEvent,
    PositionDetail,
    RiskEvent,
    LLMStreamEvent,
    TokenUsageEvent,
    AIToolCallEvent,
)
from programgarden_core.models.resilience import RetryEvent

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
        _resource_context: Resource management context (CPU/RAM/Disk throttling)
    """

    def __init__(
        self,
        job_id: str,
        workflow_id: str,
        context_params: Optional[Dict[str, Any]] = None,
        secrets: Optional[Dict[str, Any]] = None,
        workflow_inputs: Optional[Dict[str, Any]] = None,
        workflow_credentials: Optional[List[Dict[str, Any]]] = None,
        resource_context: Optional[Any] = None,  # ResourceContext (lazy import)
        # DAG 탐색용 워크플로우 구조 정보
        workflow_edges: Optional[List[Any]] = None,  # List[ResolvedEdge]
        workflow_nodes: Optional[Dict[str, Any]] = None,  # Dict[str, ResolvedNode]
        storage_dir: Optional[str] = None,
    ):
        self.job_id = job_id
        self.workflow_id = workflow_id
        self._storage_dir = storage_dir
        self.context_params = context_params or {}

        # Secrets storage (never logged, separate from context_params)
        self._secrets: Dict[str, Any] = secrets or {}
        
        # Workflow inputs schema (for {{ input.xxx }} expressions)
        self._workflow_inputs: Dict[str, Any] = workflow_inputs or {}
        
        # Workflow credentials (for credential_id resolution)
        # Format: [{"credential_id": "cred-id", "type": "http_bearer", "data": {"token": "..."}}]
        self._workflow_credentials: List[Dict[str, Any]] = workflow_credentials or []

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
        self._persistent_metadata: Dict[str, Dict[str, Any]] = {}  # node_id -> {key: value}
        
        # === New: Order Event Dispatcher ===
        # Multiple RealOrderEventNodes can subscribe to same TR codes
        # One master callback dispatches to all registered handlers
        # {product: {tr_cd: [(node_id, event_filter, handler)]}}
        self._order_event_handlers: Dict[str, Dict[str, List[tuple]]] = {}
        self._order_event_real_client: Dict[str, Any] = {}  # {product: real_client}
        
        # === New: Cleanup on flow end (stay_connected=False) ===
        # Stores trackers that should be cleaned up after each flow execution
        self._cleanup_on_flow_end: Dict[str, Any] = {}  # node_id -> tracker/connection
        
        # === New: Execution Listeners (for UI/Server callbacks) ===
        self._listeners: List[ExecutionListener] = []
        
        # === New: Workflow Position Tracker ===
        # Tracks workflow positions separately using FIFO for competition ranking
        self._workflow_position_tracker: Optional[Any] = None  # WorkflowPositionTracker (lazy init)
        self._workflow_risk_tracker: Optional[Any] = None  # WorkflowRiskTracker (lazy init)
        self._workflow_broker_node_id: Optional[str] = None  # BrokerNode ID for PnL refresh
        self._workflow_product: str = "overseas_stock"  # Product type for PnL refresh

        # === New: WorkflowJob reference (for start datetime access) ===
        self._workflow_job: Optional[Any] = None  # WorkflowJob
        
        # === New: Resource Context (for CPU/RAM/Disk throttling) ===
        self._resource_context = resource_context
        
        # === New: DAG index for ancestor propagation ===
        # Reverse adjacency list: {to_node: [from_nodes]}
        self._reverse_adj: Dict[str, List[str]] = {}

        # === New: 반복 컨텍스트 ===
        # 자동 반복 실행 시 item, index, total 저장
        self._iteration_item: Optional[Any] = None
        self._iteration_index: int = 0
        self._iteration_total: int = 0
        # Node type mapping: {node_id: node_type}
        self._node_types: Dict[str, str] = {}
        self._build_dag_index(workflow_edges, workflow_nodes)

    # === Storage Directory ===

    def _resolve_db_path(self, db_filename: str) -> str:
        """DB 파일 경로를 결정한다.

        우선순위:
        1. storage_dir (외부 사용자 지정)
        2. /app/data (Docker 환경)
        3. ./app/data (로컬 fallback)
        """
        from pathlib import Path

        if self._storage_dir:
            db_dir = Path(self._storage_dir)
            db_dir.mkdir(parents=True, exist_ok=True)
            return str(db_dir / db_filename)

        db_dir = Path("/app/data")
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                db_dir = Path("./app/data")
                db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / db_filename)

    # === DAG Index Building ===

    def _build_dag_index(
        self,
        edges: Optional[List[Any]],
        nodes: Optional[Dict[str, Any]],
    ) -> None:
        """
        Build reverse adjacency list from edges and node type mapping.
        
        This enables efficient backward traversal to find ancestor nodes.
        
        Args:
            edges: List of ResolvedEdge or dict with from/to keys
            nodes: Dict of node_id -> ResolvedNode or dict with type key
        """
        if edges:
            for edge in edges:
                # ResolvedEdge 또는 dict 형태 모두 처리
                if hasattr(edge, 'from_node_id'):
                    from_node = edge.from_node_id
                    to_node = edge.to_node_id
                else:
                    from_node = edge.get("from") or edge.get("from_node_id")
                    to_node = edge.get("to") or edge.get("to_node_id")
                
                if to_node and from_node:
                    if to_node not in self._reverse_adj:
                        self._reverse_adj[to_node] = []
                    self._reverse_adj[to_node].append(from_node)
        
        if nodes:
            for node_id, node_data in nodes.items():
                # ResolvedNode 또는 dict 형태 모두 처리
                if hasattr(node_data, 'node_type'):
                    self._node_types[node_id] = node_data.node_type
                else:
                    self._node_types[node_id] = node_data.get("type", "")

    # === DAG Ancestor Propagation ===

    def find_parent_outputs(
        self,
        current_node_id: str,
        target_node_type: str,
    ) -> List[Tuple[str, int, Dict[str, Any]]]:
        """
        Find all ancestor nodes of a specific type using backward traversal.
        
        Traverses the DAG backwards from current_node_id to find all
        nodes of target_node_type, returning them sorted by distance.
        
        Args:
            current_node_id: The node to search from
            target_node_type: The node type to find (e.g., "BrokerNode")
            
        Returns:
            List of (node_id, distance, outputs) tuples, sorted by distance.
            Empty list if no matching ancestors found.
            
        Example:
            brokers = context.find_parent_outputs("watchlist", "BrokerNode")
            for node_id, dist, outputs in brokers:
                print(f"{node_id} (거리 {dist}): {outputs.get('product')}")
        """
        # DAG 인덱스가 없으면 기존 방식 fallback
        if not self._reverse_adj:
            legacy_result = self.get_upstream_output(target_node_type)
            if legacy_result:
                return [("unknown", 0, legacy_result)]
            return []
        
        results: List[Tuple[str, int, Dict[str, Any]]] = []
        found_nodes: set = set()  # 이미 결과에 추가된 노드 추적
        visited = set()
        queue = deque([(current_node_id, 0)])  # (node_id, distance)
        
        while queue:
            node_id, distance = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            
            # 이 노드의 상위 노드들 확인
            for parent_id in self._reverse_adj.get(node_id, []):
                parent_distance = distance + 1
                
                # 타입 매칭되고 아직 결과에 없으면 추가
                if self._node_types.get(parent_id) == target_node_type:
                    if parent_id not in found_nodes:
                        outputs = self._outputs.get(parent_id, {})
                        if outputs:
                            output_dict = {port: out.value for port, out in outputs.items()}
                            results.append((parent_id, parent_distance, output_dict))
                            found_nodes.add(parent_id)
                
                # 계속 탐색 (찾아도 멈추지 않고 더 상위로)
                if parent_id not in visited:
                    queue.append((parent_id, parent_distance))
        
        # 거리순 정렬
        results.sort(key=lambda x: x[1])
        return results

    def find_parent_output(
        self,
        current_node_id: str,
        target_node_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the closest ancestor node output (convenience method).
        
        Returns only the outputs of the closest matching ancestor.
        If multiple nodes are at the same distance, returns the first one.
        Use find_parent_outputs() if you need all ancestors.
        
        Args:
            current_node_id: The node to search from
            target_node_type: The node type to find (e.g., "BrokerNode")
            
        Returns:
            Output dict of the closest ancestor, or None if not found.
            
        Example:
            broker_info = context.find_parent_output("watchlist", "BrokerNode")
            if broker_info:
                product = broker_info.get("product")
        """
        results = self.find_parent_outputs(current_node_id, target_node_type)
        return results[0][2] if results else None

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

    def get_workflow_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """
        워크플로우 JSON의 credentials 섹션에서 credential 데이터 조회

        data가 list 형태 [{key, value, ...}, ...] 인 경우 dict로 변환하여 반환합니다.
        이를 통해 _inject_credentials() 로직과 호환성을 유지합니다.

        프로덕션 환경에서는 서버가 DB에서 암호화된 credentials를 복호화하여
        워크플로우 JSON의 credentials 배열에 값을 주입한 후 실행합니다.

        Args:
            credential_id: credentials 배열에서 찾을 id (예: "broker-cred")

        Returns:
            Credential data dict (예: {"appkey": "...", "appsecret": "..."}) or None
        """
        # List에서 해당 id를 가진 credential 찾기
        cred_ref = next(
            (c for c in self._workflow_credentials if c.get("credential_id") == credential_id),
            None
        )
        if not cred_ref:
            return None

        data = cred_ref.get("data", [])

        # dict 형태인 경우 그대로 반환
        if isinstance(data, dict):
            return data if data else None

        # list 형태인 경우 dict로 변환
        if isinstance(data, list):
            result = {}
            for item in data:
                if isinstance(item, dict) and "key" in item:
                    key = item["key"]
                    value = item.get("value")
                    if value is not None:
                        result[key] = value
            if result:
                return result

        return None

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

    def get_upstream_output(self, node_type: str) -> Optional[Dict[str, Any]]:
        """
        Get output from upstream node by node type.
        
        .. deprecated::
            Use `find_parent_outputs(current_node_id, target_node_type)` or
            `find_parent_output(current_node_id, target_node_type)` instead.
            This method uses name-based matching which is unreliable
            when multiple nodes of the same type exist in the workflow.
        
        Searches all stored outputs for a node whose id contains the node type.
        Returns the first matching node's outputs as a dict.
        
        Args:
            node_type: Node type to search for (e.g., "BrokerNode")
            
        Returns:
            Output dict if found, None otherwise
        """
        # node_id가 타입명을 포함하거나, 별도로 저장된 노드 타입 정보로 매칭
        for node_id, outputs in self._outputs.items():
            # 일반적인 패턴: node_id가 타입 기반이거나, 타입명을 포함
            # 예: "broker", "BrokerNode", "broker_1" 등
            node_id_lower = node_id.lower()
            type_lower = node_type.lower().replace("node", "")
            
            if type_lower in node_id_lower or node_id.endswith(node_type):
                # 모든 출력을 dict로 반환
                return {port: output.value for port, output in outputs.items()}
        
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

    def register_persistent(self, node_id: str, tracker: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a persistent tracker/connection
        
        Args:
            node_id: Node ID
            tracker: StockAccountTracker or similar object with start()/stop()
            metadata: Optional metadata (e.g., {"event_filter": "TC1"})
        """
        self._persistent_nodes[node_id] = tracker
        if metadata:
            self._persistent_metadata[node_id] = metadata
        logger.debug(f"Registered persistent node: {node_id}, metadata={metadata}")

    def get_persistent(self, node_id: str) -> Optional[Any]:
        """Get registered persistent tracker"""
        return self._persistent_nodes.get(node_id)

    def has_persistent(self, node_id: str) -> bool:
        """Check if node has persistent tracker"""
        return node_id in self._persistent_nodes
    
    def get_persistent_metadata(self, node_id: str, key: str) -> Optional[Any]:
        """Get metadata value for a persistent node"""
        metadata = self._persistent_metadata.get(node_id, {})
        return metadata.get(key)
    
    def set_node_state(self, node_id: str, key: str, value: Any) -> None:
        """
        Set a state value for a node (e.g., real_client, gsc, ovc)
        
        This is a convenient wrapper around persistent_metadata for storing
        node-specific runtime state like WebSocket clients.
        
        Args:
            node_id: Node ID
            key: State key (e.g., "real_client", "gsc", "subscribe_symbols")
            value: State value
        """
        if node_id not in self._persistent_metadata:
            self._persistent_metadata[node_id] = {}
        self._persistent_metadata[node_id][key] = value
        logger.debug(f"Node state set: {node_id}.{key}")
    
    def get_node_state(self, node_id: str, key: str) -> Optional[Any]:
        """
        Get a state value for a node
        
        Args:
            node_id: Node ID
            key: State key
            
        Returns:
            State value or None if not set
        """
        return self.get_persistent_metadata(node_id, key)
    
    def emit_realtime_update(self, node_id: str, data: Dict[str, Any]) -> None:
        """
        Emit a realtime update event from a node.
        
        Called by realtime nodes (RealMarketDataNode, RealAccountNode, etc.)
        when new tick data arrives. This can trigger downstream node execution
        or notify listeners of real-time data changes.
        
        Args:
            node_id: The node emitting the update
            data: The update payload (e.g., {"symbol": "AAPL", "price": 150.0})
        """
        # Log the realtime update
        logger.debug(f"Realtime update from {node_id}: {data}")
        
        # Notify listeners if any are registered
        if self._listener:
            try:
                # Create a log event for realtime updates (could be a dedicated event type later)
                self._listener.on_log(LogEvent(
                    node_id=node_id,
                    level="debug",
                    message=f"Realtime: {data.get('symbol', '')} price={data.get('price', '')} vol={data.get('volume', '')}",
                    extra=data,
                ))
            except Exception as e:
                logger.warning(f"Error notifying listener of realtime update: {e}")
        
        # TODO: Future enhancement - trigger downstream nodes in real-time
        # This would require an event-driven execution model where nodes
        # can be re-executed when their input data changes.
    
    async def cleanup_persistent(self, node_id: str) -> None:
        """
        Cleanup a single persistent node (e.g., when event_filter changes)
        
        Args:
            node_id: Node ID to cleanup
        """
        tracker = self._persistent_nodes.pop(node_id, None)
        if tracker:
            try:
                if hasattr(tracker, 'stop'):
                    if asyncio.iscoroutinefunction(tracker.stop):
                        await tracker.stop()
                    else:
                        tracker.stop()
                logger.debug(f"Stopped persistent node: {node_id}")
            except Exception as e:
                logger.warning(f"Error stopping persistent node {node_id}: {e}")
        
        # Cleanup background task
        task = self._persistent_tasks.pop(node_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.debug(f"Cancelled persistent task: {node_id}")
        
        # Cleanup metadata
        self._persistent_metadata.pop(node_id, None)
        
        # Cleanup order event handlers for this node
        self._remove_order_event_handler(node_id)

    def register_persistent_task(self, node_id: str, task: asyncio.Task) -> None:
        """Register background task for persistent node"""
        self._persistent_tasks[node_id] = task

    # === Order Event Dispatcher ===
    
    def register_order_event_handler(
        self,
        product: str,
        tr_cd: str,
        node_id: str,
        event_filter: str,
        handler: Callable,
    ) -> None:
        """
        Register a handler for order events.
        
        Multiple nodes can register handlers for the same TR code.
        The master callback will dispatch to all registered handlers.
        
        Args:
            product: 'overseas_futures' or 'overseas_stock'
            tr_cd: TR code (TC1, TC2, TC3 for futures; AS0~AS4 for stocks)
            node_id: Node ID
            event_filter: 'all' or specific TR code
            handler: Callback function(resp) -> None
        """
        if product not in self._order_event_handlers:
            self._order_event_handlers[product] = {}
        if tr_cd not in self._order_event_handlers[product]:
            self._order_event_handlers[product][tr_cd] = []
        
        # Remove existing handler for this node (if any)
        self._order_event_handlers[product][tr_cd] = [
            h for h in self._order_event_handlers[product][tr_cd]
            if h[0] != node_id
        ]
        
        # Add new handler
        self._order_event_handlers[product][tr_cd].append((node_id, event_filter, handler))
        logger.debug(f"Registered order event handler: product={product}, tr_cd={tr_cd}, node_id={node_id}, filter={event_filter}")
    
    def _remove_order_event_handler(self, node_id: str) -> None:
        """Remove all handlers for a specific node"""
        for product in self._order_event_handlers:
            for tr_cd in self._order_event_handlers[product]:
                self._order_event_handlers[product][tr_cd] = [
                    h for h in self._order_event_handlers[product][tr_cd]
                    if h[0] != node_id
                ]
    
    def get_order_event_handlers(self, product: str, tr_cd: str) -> List[tuple]:
        """Get all handlers for a specific product and TR code"""
        if product not in self._order_event_handlers:
            return []
        if tr_cd not in self._order_event_handlers[product]:
            return []
        return self._order_event_handlers[product][tr_cd]
    
    def has_order_event_subscription(self, product: str) -> bool:
        """Check if there's already a master subscription for this product"""
        return product in self._order_event_real_client
    
    def set_order_event_real_client(self, product: str, real_client: Any) -> None:
        """Store the real_client for a product (for master subscription)"""
        self._order_event_real_client[product] = real_client
    
    def get_order_event_real_client(self, product: str) -> Optional[Any]:
        """Get the real_client for a product"""
        return self._order_event_real_client.get(product)

    async def cleanup_persistent_nodes(self) -> None:
        """
        Cleanup all persistent nodes (call on job stop)
        """
        # 먼저 실시간 구독 해제 (gsc, ovc 등)
        for node_id in list(self._persistent_metadata.keys()):
            metadata = self._persistent_metadata.get(node_id, {})
            
            # GSC 구독 해제 (해외주식)
            gsc = metadata.get("gsc")
            subscribe_symbols = metadata.get("subscribe_symbols", [])
            if gsc and subscribe_symbols:
                try:
                    gsc.remove_gsc_symbols(symbols=subscribe_symbols)
                    logger.debug(f"Removed GSC subscription for {node_id}: {subscribe_symbols}")
                except Exception as e:
                    logger.warning(f"Error removing GSC symbols for {node_id}: {e}")
            
            # OVC 구독 해제 (해외선물)
            ovc = metadata.get("ovc")
            if ovc and subscribe_symbols:
                try:
                    ovc.remove_ovc_symbols(symbols=subscribe_symbols)
                    logger.debug(f"Removed OVC subscription for {node_id}: {subscribe_symbols}")
                except Exception as e:
                    logger.warning(f"Error removing OVC symbols for {node_id}: {e}")
        
        # Stop/Close all trackers (WebSocket clients 등)
        for node_id, tracker in self._persistent_nodes.items():
            try:
                # stop() 메서드 호출
                if hasattr(tracker, 'stop'):
                    if asyncio.iscoroutinefunction(tracker.stop):
                        await tracker.stop()
                    else:
                        tracker.stop()
                    logger.debug(f"Stopped persistent node: {node_id}")
                
                # close() 메서드 호출 (WebSocket 클라이언트)
                if hasattr(tracker, 'close'):
                    if asyncio.iscoroutinefunction(tracker.close):
                        await tracker.close()
                    else:
                        tracker.close()
                    logger.debug(f"Closed persistent node: {node_id}")
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
        self._persistent_metadata.clear()

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

    def set_workflow_job(self, job: Any) -> None:
        """
        Set workflow job reference for start datetime access.
        
        This enables notify_workflow_pnl to include workflow_start_datetime
        and workflow_elapsed_days in events.
        
        Args:
            job: WorkflowJob instance
        """
        self._workflow_job = job

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
        
        # 🆕 이벤트 루프에 제어권을 돌려줘서 SSE 스트림이 전송될 수 있도록 함
        await asyncio.sleep(0)

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
        
        # SSE 스트림 전송을 위해 이벤트 루프에 제어권 양보
        await asyncio.sleep(0)

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
        
        # SSE 스트림 전송을 위해 이벤트 루프에 제어권 양보
        await asyncio.sleep(0)

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
        
        # SSE 스트림 전송을 위해 이벤트 루프에 제어권 양보
        await asyncio.sleep(0)

    async def notify_output_update(
        self,
        node_id: str,
        node_type: str,
        outputs: Dict[str, Any],
    ) -> None:
        """
        Notify all listeners about realtime output update.
        
        Used for realtime nodes (RealAccountNode, RealMarketDataNode) to
        broadcast output changes without changing node state.
        """
        logger.debug(f"📡 notify_output_update: {node_id} outputs={list(outputs.keys())}")
        
        if not self._listeners:
            return
        
        # Use NodeStateEvent with 'running' state to indicate realtime update
        event = NodeStateEvent(
            job_id=self.job_id,
            node_id=node_id,
            node_type=node_type,
            state=NodeState.RUNNING,  # Still running (realtime mode)
            outputs=self._sanitize_outputs(outputs),
            error=None,
            duration_ms=None,
        )
        
        for listener in self._listeners:
            try:
                await listener.on_node_state_change(event)
            except Exception as e:
                logger.warning(f"Listener error on_output_update: {e}")

    async def notify_display_data(
        self,
        node_id: str,
        chart_type: str,
        title: Optional[str],
        data: Any,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        data_schema: Optional[Dict[str, Any]] = None,
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
            data_schema=data_schema,
        )
        
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_display_data'):
                    await listener.on_display_data(event)
            except Exception as e:
                logger.warning(f"Listener error on_display_data: {e}")

    async def notify_retry(self, event: RetryEvent) -> None:
        """
        Notify all listeners about retry event.

        UI에서 "재시도 중 (2/3)..." 표시용.

        Args:
            event: RetryEvent with attempt count, error type, next retry delay, etc.
        """
        if not self._listeners:
            return

        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_retry'):
                    await listener.on_retry(event)
            except Exception as e:
                logger.warning(f"Listener error on_retry: {e}")

    async def notify_llm_stream(self, event: LLMStreamEvent) -> None:
        """LLM 토큰 스트리밍 이벤트 전파. UI 실시간 타이핑 효과용."""
        if not self._listeners:
            return
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_llm_stream'):
                    await listener.on_llm_stream(event)
            except Exception as e:
                logger.warning(f"Listener error on_llm_stream: {e}")

    async def notify_token_usage(self, event: TokenUsageEvent) -> None:
        """토큰 사용량 이벤트 전파. 비용 추적 및 모니터링용."""
        if not self._listeners:
            return
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_token_usage'):
                    await listener.on_token_usage(event)
            except Exception as e:
                logger.warning(f"Listener error on_token_usage: {e}")

    async def notify_ai_tool_call(self, event: AIToolCallEvent) -> None:
        """AI Tool 호출 이벤트 전파. UI에서 Tool 호출 상태 표시용."""
        if not self._listeners:
            return
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_ai_tool_call'):
                    await listener.on_ai_tool_call(event)
            except Exception as e:
                logger.warning(f"Listener error on_ai_tool_call: {e}")

    async def notify_risk_event(self, event: RiskEvent) -> None:
        """위험 이벤트 전파. UI에서 위험 알림 표시용."""
        if not self._listeners:
            return
        for listener in self._listeners:
            try:
                if hasattr(listener, 'on_risk_event'):
                    await listener.on_risk_event(event)
            except Exception as e:
                logger.warning(f"Listener error on_risk_event: {e}")

    async def notify_workflow_pnl(
        self,
        broker_node_id: str,
        product: str,
        provider: str,
        current_prices: Dict[str, float],
        account_positions: Optional[Dict[str, Any]],
        currency: str = "USD",
    ) -> None:
        """Notify all listeners about workflow P&L update (확장 버전).
        
        BrokerNode의 AccountTracker에서 틱마다 호출됩니다.
        WorkflowPositionTracker를 사용하여 워크플로우 포지션과 그 외 포지션을 분리하고
        각각의 수익률을 계산하여 리스너에 전달합니다.
        
        리스너별로 다른 pnl_start_date를 적용하여 각각의 대회 기준 이벤트를 생성합니다.
        
        Args:
            broker_node_id: BrokerNode ID
            product: 상품 유형 (overseas_stock, overseas_futures)
            provider: 증권사 (ls-sec.co.kr)
            current_prices: 현재가 {symbol: price}
            account_positions: 계좌 전체 포지션 {symbol: {quantity, buy_price, current_price, pnl_rate}}
            currency: 통화 (기본 USD)
        """
        if not self._listeners:
            return

        # ━━━ Risk Tracker 실시간 가격 연동 ━━━
        if self._workflow_risk_tracker and current_prices:
            for symbol, price in current_prices.items():
                self._workflow_risk_tracker.update_price(
                    symbol=symbol,
                    exchange="",  # 거래소 정보는 이미 등록 시 저장됨
                    price=price,
                )

        # 메타 정보 준비
        from datetime import timezone
        now = datetime.now(timezone.utc)
        workflow_start = None
        elapsed_days = None
        
        if self._workflow_job is not None:
            workflow_start = getattr(self._workflow_job, 'workflow_start_datetime', None)
            if workflow_start:
                elapsed_days = (now - workflow_start).days
        
        # 1. 기본 워크플로우 수익률 계산 (전체 기간)
        base_workflow_result = self._calculate_workflow_pnl(
            current_prices=current_prices,
            all_positions=account_positions,
            product=product,
            start_date=None,  # 전체 기간
        )
        
        # 2. 계좌 전체 수익률 계산
        account_result = self._calculate_account_pnl(
            account_positions=account_positions,
            start_date=None,
        )
        
        # 3. 리스너별 이벤트 생성 및 전달
        for listener in self._listeners:
            try:
                if not hasattr(listener, 'on_workflow_pnl_update'):
                    continue
                
                # 리스너별 start_date 확인
                listener_start_date = getattr(listener, 'pnl_start_date', None)
                
                # 기본 이벤트 데이터
                event_data = {
                    "job_id": self.job_id,
                    "broker_node_id": broker_node_id,
                    "product": product,
                    "paper_trading": getattr(self, '_workflow_paper_trading', False),
                    "timestamp": now,
                    
                    # 워크플로우 기본 (전체)
                    "workflow_pnl_rate": base_workflow_result.get("workflow_pnl_rate", 0.0),
                    "workflow_eval_amount": base_workflow_result.get("workflow_eval_amount", 0.0),
                    "workflow_buy_amount": base_workflow_result.get("workflow_buy_amount", 0.0),
                    "workflow_pnl_amount": base_workflow_result.get("workflow_pnl_amount", 0.0),
                    
                    # 기존 other/total 필드
                    "other_pnl_rate": base_workflow_result.get("other_pnl_rate", 0.0),
                    "other_eval_amount": base_workflow_result.get("other_eval_amount", 0.0),
                    "other_buy_amount": base_workflow_result.get("other_buy_amount", 0.0),
                    "other_pnl_amount": base_workflow_result.get("other_pnl_amount", 0.0),
                    "total_pnl_rate": base_workflow_result.get("total_pnl_rate", 0.0),
                    "total_eval_amount": base_workflow_result.get("total_eval_amount", 0.0),
                    "total_buy_amount": base_workflow_result.get("total_buy_amount", 0.0),
                    "total_pnl_amount": base_workflow_result.get("total_pnl_amount", 0.0),
                    
                    "workflow_positions": base_workflow_result.get("workflow_positions", []),
                    "other_positions": base_workflow_result.get("other_positions", []),
                    "trust_score": base_workflow_result.get("trust_score", 0),
                    "anomaly_count": base_workflow_result.get("anomaly_count", 0),
                    "currency": currency,
                    
                    # 신규 필드: 워크플로우 상품별
                    "workflow_stock_pnl_rate": base_workflow_result.get("workflow_stock_pnl_rate"),
                    "workflow_stock_pnl_amount": base_workflow_result.get("workflow_stock_pnl_amount"),
                    "workflow_futures_pnl_rate": base_workflow_result.get("workflow_futures_pnl_rate"),
                    "workflow_futures_pnl_amount": base_workflow_result.get("workflow_futures_pnl_amount"),
                    
                    # 신규 필드: 계좌 전체/상품별
                    "account_total_pnl_rate": account_result.get("account_total_pnl_rate"),
                    "account_total_pnl_amount": account_result.get("account_total_pnl_amount"),
                    "account_total_eval_amount": account_result.get("account_total_eval_amount"),
                    "account_total_buy_amount": account_result.get("account_total_buy_amount"),
                    "account_stock_pnl_rate": account_result.get("account_stock_pnl_rate"),
                    "account_stock_pnl_amount": account_result.get("account_stock_pnl_amount"),
                    "account_futures_pnl_rate": account_result.get("account_futures_pnl_rate"),
                    "account_futures_pnl_amount": account_result.get("account_futures_pnl_amount"),

                    # 총 포지션 수 (AccountPnLEvent.position_count 대체)
                    "total_position_count": len(account_positions) if account_positions else 0,
                    
                    # 메타 정보
                    "workflow_start_datetime": workflow_start,
                    "workflow_elapsed_days": elapsed_days,
                }
                
                # 대회 기준 필드 (start_date가 있는 리스너만)
                if listener_start_date:
                    # 대회 기준 재계산
                    competition_workflow = self._calculate_workflow_pnl(
                        current_prices=current_prices,
                        all_positions=account_positions,
                        product=product,
                        start_date=listener_start_date,
                    )
                    competition_account = self._calculate_account_pnl(
                        account_positions=account_positions,
                        start_date=listener_start_date,
                    )
                    
                    event_data.update({
                        "competition_start_date": listener_start_date,
                        "competition_workflow_pnl_rate": competition_workflow.get("workflow_pnl_rate"),
                        "competition_workflow_pnl_amount": competition_workflow.get("workflow_pnl_amount"),
                        "competition_workflow_stock_pnl_rate": competition_workflow.get("workflow_stock_pnl_rate"),
                        "competition_workflow_stock_pnl_amount": competition_workflow.get("workflow_stock_pnl_amount"),
                        "competition_workflow_futures_pnl_rate": competition_workflow.get("workflow_futures_pnl_rate"),
                        "competition_workflow_futures_pnl_amount": competition_workflow.get("workflow_futures_pnl_amount"),
                        "competition_account_pnl_rate": competition_account.get("account_total_pnl_rate"),
                        "competition_account_pnl_amount": competition_account.get("account_total_pnl_amount"),
                        "competition_account_stock_pnl_rate": competition_account.get("account_stock_pnl_rate"),
                        "competition_account_stock_pnl_amount": competition_account.get("account_stock_pnl_amount"),
                        "competition_account_futures_pnl_rate": competition_account.get("account_futures_pnl_rate"),
                        "competition_account_futures_pnl_amount": competition_account.get("account_futures_pnl_amount"),
                    })
                
                event = WorkflowPnLEvent(**event_data)
                await listener.on_workflow_pnl_update(event)
                
            except Exception as e:
                logger.warning(f"Listener error on_workflow_pnl_update: {e}")
        
        # 디버그 로그
        wf_rate = base_workflow_result.get("workflow_pnl_rate", 0.0)
        logger.debug(f"📡 notify_workflow_pnl: {broker_node_id} ({product}) wf_rate={wf_rate:.2f}%")

    def _calculate_workflow_pnl(
        self,
        current_prices: Dict[str, float],
        all_positions: Optional[Dict[str, Any]],
        product: str = "overseas_stock",
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """워크플로우 수익률 계산 (start_date 필터 지원).
        
        Args:
            current_prices: 현재가 {symbol: price}
            all_positions: 전체 포지션
            product: 현재 상품 유형 (overseas_stock, overseas_futures)
            start_date: 필터 시작일 (YYYYMMDD)
        
        Returns:
            워크플로우 수익률 데이터 dict
        """
        # 트래커 없으면 기본값 (모든 포지션이 "other")
        if self._workflow_position_tracker is None:
            # 트래커 없음 = 모든 포지션이 "other"
            total_eval = 0.0
            total_buy = 0.0
            other_positions_list = []
            
            if all_positions:
                for symbol, pos in all_positions.items():
                    qty = pos.get("quantity", 0)
                    buy_price = pos.get("buy_price", 0)
                    current_price = pos.get("current_price", 0)
                    pnl_rate = pos.get("pnl_rate", 0)
                    
                    eval_amt = qty * current_price
                    buy_amt = qty * buy_price
                    pnl_amt = eval_amt - buy_amt
                    
                    total_eval += eval_amt
                    total_buy += buy_amt
                    
                    other_positions_list.append(PositionDetail(
                        symbol=symbol,
                        exchange=pos.get("exchange", ""),
                        quantity=qty,
                        avg_price=buy_price,
                        current_price=current_price,
                        pnl_amount=pnl_amt,
                        pnl_rate=pnl_rate,
                    ))
            
            total_pnl = total_eval - total_buy
            total_pnl_rate = (total_pnl / total_buy * 100) if total_buy > 0 else 0.0
            
            return {
                "workflow_pnl_rate": 0.0,
                "workflow_eval_amount": 0.0,
                "workflow_buy_amount": 0.0,
                "workflow_pnl_amount": 0.0,
                "other_pnl_rate": total_pnl_rate,
                "other_eval_amount": total_eval,
                "other_buy_amount": total_buy,
                "other_pnl_amount": total_pnl,
                "total_pnl_rate": total_pnl_rate,
                "total_eval_amount": total_eval,
                "total_buy_amount": total_buy,
                "total_pnl_amount": total_pnl,
                "workflow_positions": [],
                "other_positions": other_positions_list,
                "trust_score": 0,
                "anomaly_count": 0,
                # 상품별 필드는 tracker에서 채움 (여기서는 None)
                "workflow_stock_pnl_rate": None,
                "workflow_stock_pnl_amount": None,
                "workflow_futures_pnl_rate": None,
                "workflow_futures_pnl_amount": None,
            }
        
        # WorkflowPositionTracker로 FIFO 기반 분리 계산
        try:
            return self._workflow_position_tracker.calculate_pnl(
                current_prices=current_prices,
                all_positions=all_positions or {},
                start_date=start_date,  # 날짜 필터
            )
        except Exception as e:
            logger.warning(f"calculate_workflow_pnl failed: {e}")
            return {
                "workflow_pnl_rate": 0.0,
                "workflow_eval_amount": 0.0,
                "workflow_buy_amount": 0.0,
                "workflow_pnl_amount": 0.0,
                "other_pnl_rate": 0.0,
                "other_eval_amount": 0.0,
                "other_buy_amount": 0.0,
                "other_pnl_amount": 0.0,
                "total_pnl_rate": 0.0,
                "total_eval_amount": 0.0,
                "total_buy_amount": 0.0,
                "total_pnl_amount": 0.0,
                "workflow_positions": [],
                "other_positions": [],
                "trust_score": 0,
                "anomaly_count": 0,
            }

    def _calculate_account_pnl(
        self,
        account_positions: Optional[Dict[str, Any]],
        start_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """계좌 전체 수익률 계산.
        
        Args:
            account_positions: 계좌 전체 포지션
            start_date: 필터 시작일 (현재 미사용, 향후 확장)
        
        Returns:
            계좌 수익률 데이터 dict
        """
        if not account_positions:
            return {}
        
        # 상품별 분류
        stock_positions = {}
        futures_positions = {}
        
        for symbol, pos in account_positions.items():
            pos_product = pos.get("product", "overseas_stock")
            if pos_product == "overseas_stock":
                stock_positions[symbol] = pos
            elif pos_product == "overseas_futures":
                futures_positions[symbol] = pos
        
        # 상품별 수익률 계산
        def calc_pnl(positions: Dict[str, Any]) -> Dict[str, float]:
            total_eval = 0.0
            total_buy = 0.0
            for pos in positions.values():
                qty = pos.get("quantity", 0) or pos.get("qty", 0)
                buy_price = pos.get("buy_price", 0) or pos.get("avg_price", 0)
                current_price = pos.get("current_price", buy_price)
                total_eval += qty * current_price
                total_buy += qty * buy_price
            pnl_amount = total_eval - total_buy
            pnl_rate = (pnl_amount / total_buy * 100) if total_buy > 0 else 0.0
            return {
                "eval": total_eval,
                "buy": total_buy,
                "pnl_amount": pnl_amount,
                "pnl_rate": pnl_rate,
            }
        
        stock_result = calc_pnl(stock_positions)
        futures_result = calc_pnl(futures_positions)
        
        # 전체 합산
        total_eval = stock_result["eval"] + futures_result["eval"]
        total_buy = stock_result["buy"] + futures_result["buy"]
        total_pnl = total_eval - total_buy
        total_pnl_rate = (total_pnl / total_buy * 100) if total_buy > 0 else 0.0
        
        return {
            "account_total_pnl_rate": total_pnl_rate,
            "account_total_pnl_amount": total_pnl,
            "account_total_eval_amount": total_eval,
            "account_total_buy_amount": total_buy,
            "account_stock_pnl_rate": stock_result["pnl_rate"],
            "account_stock_pnl_amount": stock_result["pnl_amount"],
            "account_futures_pnl_rate": futures_result["pnl_rate"],
            "account_futures_pnl_amount": futures_result["pnl_amount"],
        }

    def init_workflow_position_tracker(
        self,
        broker_node_id: str,
        product: str = "overseas_stock",
        provider: str = "ls",
        paper_trading: bool = False,
    ) -> None:
        """Initialize workflow position tracker for FIFO-based position tracking.

        on_workflow_pnl_update 리스너가 등록된 경우에만 트래커를 초기화합니다.
        주문 발생 시 자동으로 포지션을 기록하고, 틱마다 워크플로우 수익률을 계산합니다.

        모의투자/실전투자 모드별로 데이터를 분리 저장하여, 모드 전환 시에도
        기존 수익률 데이터가 보존됩니다.

        Args:
            broker_node_id: BrokerNode ID (로그용)
            product: 상품 유형 (overseas_stock, overseas_futures)
            provider: 증권사 (ls, kiwoom, ...)
            paper_trading: 모의투자 모드 (True: 모의, False: 실전)
        """
        # 리스너 중 on_workflow_pnl_update를 구현한 것이 있는지 확인
        has_workflow_listener = any(
            hasattr(listener, 'on_workflow_pnl_update')
            and callable(getattr(listener, 'on_workflow_pnl_update', None))
            for listener in self._listeners
        )

        if not has_workflow_listener:
            logger.debug("No workflow_pnl listener registered, skipping tracker init")
            return

        if self._workflow_position_tracker is not None:
            logger.debug("Workflow position tracker already initialized")
            return

        try:
            from programgarden.database import WorkflowPositionTracker

            trading_mode = "paper" if paper_trading else "live"

            db_filename = f"{self.workflow_id or self.job_id}_workflow.db"
            db_path = self._resolve_db_path(db_filename)

            self._workflow_position_tracker = WorkflowPositionTracker(
                db_path=db_path,
                job_id=self.job_id,
                broker_node_id=broker_node_id,
                product=product,
                provider=provider,
                trading_mode=trading_mode,
            )

            # 거래 모드 메타데이터 기록 (데이터 초기화 없이 모드만 업데이트)
            self._workflow_position_tracker.update_trading_mode(trading_mode)

            # PnL refresh용 정보 저장
            self._workflow_broker_node_id = broker_node_id
            self._workflow_product = product
            self._workflow_provider = provider
            self._workflow_paper_trading = paper_trading

            identifier = f"{product}/{provider}"
            logger.info(f"Workflow position tracker initialized: {db_path} ({identifier}, trading_mode={trading_mode})")

        except Exception as e:
            logger.warning(f"Failed to init workflow position tracker: {e}")
            self._workflow_position_tracker = None

    # ============================================================
    # Risk Tracker
    # ============================================================

    @property
    def risk_tracker(self) -> Optional[Any]:
        """위험관리 추적기. 관련 노드/플러그인이 없으면 None."""
        return self._workflow_risk_tracker

    def init_risk_tracker(
        self,
        features: set,
        product: str,
        provider: str,
        paper_trading: bool,
    ) -> None:
        """선언된 feature 기반으로 RiskTracker 초기화.

        Args:
            features: 노드/플러그인이 선언한 risk feature 집합
            product: 상품 유형 (overseas_stock, overseas_futures)
            provider: 증권사 (ls, kiwoom, ...)
            paper_trading: 모의투자 모드
        """
        if not features:
            return
        if self._workflow_risk_tracker is not None:
            return

        try:
            from programgarden.database import WorkflowRiskTracker

            trading_mode = "paper" if paper_trading else "live"

            db_filename = f"{self.workflow_id or self.job_id}_workflow.db"
            db_path = self._resolve_db_path(db_filename)

            self._workflow_risk_tracker = WorkflowRiskTracker(
                db_path=db_path,
                job_id=self.job_id,
                product=product,
                provider=provider,
                trading_mode=trading_mode,
                features=features,
            )

            # 재시작 검증 (hwm feature + 기존 HWM 데이터가 있으면)
            if "hwm" in features and self._workflow_risk_tracker.has_hwm_data():
                if self._workflow_position_tracker:
                    results = self._workflow_risk_tracker.validate_hwm_on_restart(
                        self._workflow_position_tracker
                    )
                    for r in results:
                        if r.action != "kept" and "events" in features:
                            self._workflow_risk_tracker.record_risk_event(
                                event_type=f"hwm_{r.action}",
                                severity="info",
                                symbol=r.symbol,
                                details={
                                    "reason": r.reason,
                                    "old_hwm": str(r.old_hwm) if r.old_hwm else None,
                                    "new_hwm": str(r.new_hwm) if r.new_hwm else None,
                                },
                            )

            self._workflow_risk_tracker.start_flush_loop()

            logger.info(
                f"Risk tracker initialized: features={features}, "
                f"product={product}, trading_mode={trading_mode}"
            )

        except Exception as e:
            logger.warning(f"Failed to init risk tracker: {e}")
            self._workflow_risk_tracker = None

    def record_workflow_order(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        node_id: str,
    ) -> None:
        """Record workflow order for FIFO tracking.
        
        NewOrderNode에서 주문 성공 시 호출하여 주문을 기록합니다.
        나중에 체결 시 이 정보로 워크플로우 주문 여부를 판단합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 수량
            price: 가격
            node_id: 주문을 실행한 노드 ID
        """
        if self._workflow_position_tracker is None:
            return
        
        try:
            self._workflow_position_tracker.record_order(
                order_no=order_no,
                order_date=order_date,
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=quantity,
                price=price,
                job_id=self.job_id,
                node_id=node_id,
            )
            logger.debug(f"Recorded workflow order: {order_no} ({symbol} {side} {quantity})")

            # ━━━ Risk Tracker 체결 연동 ━━━
            if self._workflow_risk_tracker:
                if side == "buy":
                    self._workflow_risk_tracker.register_symbol(
                        symbol=symbol,
                        exchange=exchange,
                        entry_price=price,
                        qty=quantity,
                    )
                elif side == "sell":
                    # 전량 매도 시 HWM 해제
                    positions = self._workflow_position_tracker.get_workflow_positions()
                    pos = positions.get(symbol) if isinstance(positions, dict) else None
                    remaining = getattr(pos, 'quantity', 0) if pos else 0
                    if remaining <= 0:
                        self._workflow_risk_tracker.unregister_symbol(symbol)
        except Exception as e:
            logger.warning(f"Failed to record workflow order: {e}")

    def update_workflow_order_fill_price(
        self,
        order_no: str,
        order_date: str,
        fill_price: float,
    ) -> bool:
        """Update fill price for market orders.
        
        시장가 주문은 주문 시점에 가격을 알 수 없으므로,
        체결 이벤트 수신 시 실제 체결 가격으로 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            fill_price: 체결 가격
            
        Returns:
            업데이트 성공 여부
        """
        if self._workflow_position_tracker is None:
            return False
        
        try:
            return self._workflow_position_tracker.update_order_fill_price(
                order_no=order_no,
                order_date=order_date,
                fill_price=fill_price,
            )
        except Exception as e:
            logger.warning(f"Failed to update order fill price: {e}")
            return False

    async def record_workflow_fill(
        self,
        order_no: str,
        order_date: str,
        symbol: str,
        exchange: str,
        side: str,
        quantity: int,
        price: float,
        fill_time: str,
        commda_code: str = "40",
    ) -> str:
        """Record fill event for FIFO position tracking.
        
        체결 이벤트 수신 시 호출하여 포지션 로트를 생성/청산합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            symbol: 종목코드
            exchange: 거래소
            side: 매매구분 ("buy" | "sell")
            quantity: 체결 수량
            price: 체결 가격
            fill_time: 체결시각 (HHMMSSsss)
            commda_code: 매체구분코드 ("40"=OPEN API, 기타=수동)
            
        Returns:
            분류 결과: "workflow" | "manual" | "unknown_api" | "pending"
        """
        if self._workflow_position_tracker is None:
            logger.debug("Workflow position tracker not initialized, skipping record_fill")
            return "skipped"
        
        try:
            result = await self._workflow_position_tracker.record_fill(
                order_no=order_no,
                order_date=order_date,
                symbol=symbol,
                exchange=exchange,
                side=side,
                quantity=quantity,
                price=price,
                fill_time=fill_time,
                commda_code=commda_code,
            )
            logger.info(f"Recorded workflow fill: {order_no} ({symbol} {side} {quantity}@{price}) → {result}")

            # 체결 후 PnL refresh 트리거
            if result == "workflow" and self._workflow_broker_node_id:
                try:
                    # 현재가로 PnL 계산 (체결가 사용)
                    current_prices = {symbol: price}
                    await self.notify_workflow_pnl(
                        broker_node_id=self._workflow_broker_node_id,
                        product=self._workflow_product,
                        provider="ls-sec.co.kr",
                        current_prices=current_prices,
                        account_positions=None,  # 전체 포지션은 나중에 업데이트됨
                        currency="USD",
                    )
                    logger.info(f"PnL refresh triggered after fill: {symbol}")
                except Exception as pnl_err:
                    logger.warning(f"Failed to trigger PnL refresh: {pnl_err}")

            return result
        except Exception as e:
            logger.warning(f"Failed to record workflow fill: {e}")
            return "error"

    async def cancel_workflow_order(
        self,
        order_no: str,
        order_date: str,
    ) -> bool:
        """Cancel a workflow order (mark as cancelled).
        
        취소 완료 이벤트 수신 시 호출하여 주문 상태를 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            
        Returns:
            취소 성공 여부
        """
        if self._workflow_position_tracker is None:
            return False
        
        try:
            return self._workflow_position_tracker.cancel_order(order_no, order_date)
        except Exception as e:
            logger.warning(f"Failed to cancel workflow order: {e}")
            return False

    async def modify_workflow_order(
        self,
        order_no: str,
        order_date: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
    ) -> bool:
        """Modify a workflow order (update quantity/price).
        
        정정 완료 이벤트 수신 시 호출하여 주문 정보를 업데이트합니다.
        
        Args:
            order_no: 주문번호
            order_date: 주문일자 (YYYYMMDD)
            new_quantity: 새 수량 (None이면 변경 안함)
            new_price: 새 가격 (None이면 변경 안함)
            
        Returns:
            정정 성공 여부
        """
        if self._workflow_position_tracker is None:
            return False
        
        try:
            return self._workflow_position_tracker.modify_order(
                order_no, order_date, new_quantity, new_price
            )
        except Exception as e:
            logger.warning(f"Failed to modify workflow order: {e}")
            return False

    def get_workflow_orders_without_fill_price(self) -> list:
        """Get orders without fill price (for fallback sync).
        
        연결 끊김 등으로 체결 이벤트를 놓친 경우,
        체결내역 조회로 가격을 복구하기 위해 사용합니다.
        
        Returns:
            가격이 0인 주문 목록
        """
        if self._workflow_position_tracker is None:
            return []
        
        try:
            return self._workflow_position_tracker.get_orders_without_fill_price()
        except Exception as e:
            logger.warning(f"Failed to get orders without fill price: {e}")
            return []

    def sync_workflow_fill_prices_from_history(
        self,
        fill_history: list,
    ) -> int:
        """Sync fill prices from trade history API (fallback).
        
        체결내역 API 응답으로 시장가 주문의 가격을 복구합니다.
        
        Args:
            fill_history: 체결내역 리스트
                [{"order_no": "123", "order_date": "20260123", "fill_price": 2.82}, ...]
            
        Returns:
            업데이트된 주문 수
        """
        if self._workflow_position_tracker is None:
            return 0
        
        try:
            return self._workflow_position_tracker.sync_fill_prices_from_history(fill_history)
        except Exception as e:
            logger.warning(f"Failed to sync fill prices from history: {e}")
            return 0

    def sync_workflow_fills_from_history(
        self,
        fill_history: list,
    ) -> int:
        """Sync fills and create positions from trade history API (fallback).
        
        체결내역 API 응답으로 FIFO 포지션을 생성합니다.
        이 메서드는 실시간 체결 이벤트를 놓친 경우 fallback으로 사용합니다.
        
        Args:
            fill_history: 체결내역 리스트
                [{
                    "order_no": "123",
                    "order_date": "20260123",
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "side": "buy",
                    "quantity": 10,
                    "price": 192.50,
                    "fill_time": "093000000"
                }, ...]
            
        Returns:
            처리된 체결 수
        """
        if self._workflow_position_tracker is None:
            return 0
        
        try:
            return self._workflow_position_tracker.sync_fills_from_history(fill_history)
        except Exception as e:
            logger.warning(f"Failed to sync fills from history: {e}")
            return 0

    def _sanitize_outputs(self, outputs: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Remove sensitive information from outputs."""
        # None은 None으로 반환, 빈 딕셔너리 {}는 그대로 유지
        if outputs is None:
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
        - {{ nodes.nodeId.method() }}: Node output with method chaining 
        - {{ item }}, {{ item.field }}: Current iteration item 
        - {{ index }}, {{ total }}: Iteration context 
        - {{ input.xxx }}: Workflow input parameters
        - {{ context.xxx }}: Runtime context parameters
        """
        expr_context = ExpressionContext()

        # Add node outputs
        for node_id, outputs in self._outputs.items():
            for port_name, output in outputs.items():
                expr_context.set_node_output(node_id, port_name, output.value)

        # === 반복 컨텍스트 ===
        if self._iteration_item is not None:
            expr_context.set_iteration_context(
                self._iteration_item,
                self._iteration_index,
                self._iteration_total,
            )

        # Add realtime data
        expr_context.variables.update(self._realtime_data)

        # Add workflow inputs (merged: defaults + user overrides)
        merged_inputs = self._merge_inputs_with_defaults()
        expr_context.variables["input"] = merged_inputs

        # Add context parameters (for backward compatibility)
        expr_context.variables["context"] = self.context_params

        return expr_context

    def set_iteration_context(self, item: Any, index: int, total: int) -> None:
        """
        반복 컨텍스트 설정

        자동 반복 실행 시 Executor가 각 아이템마다 호출합니다.
        {{ item }}, {{ index }}, {{ total }} 표현식에서 사용됩니다.
        """
        self._iteration_item = item
        self._iteration_index = index
        self._iteration_total = total

    def clear_iteration_context(self) -> None:
        """반복 컨텍스트 초기화"""
        self._iteration_item = None
        self._iteration_index = 0
        self._iteration_total = 0

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

    # === Resource Management ===

    @property
    def resource(self):
        """
        Get resource context for throttling and resource management.
        
        Returns:
            ResourceContext or None if not configured
        """
        return self._resource_context
    
    def set_resource_context(self, resource_context) -> None:
        """
        Set resource context
        
        Args:
            resource_context: ResourceContext instance
        """
        self._resource_context = resource_context
    
    async def check_resources_before_task(
        self,
        task_type: str = "default",
        weight: float = 1.0,
        is_order: bool = False,
        timeout: Optional[float] = 30.0,
    ) -> Dict[str, Any]:
        """
        Check resources and acquire execution permission before running a task.
        
        This method should be called before executing CPU/memory intensive tasks
        like condition evaluation or backtesting.
        
        Args:
            task_type: Task/node type (e.g., "ConditionNode", "BacktestEngineNode")
            weight: Task weight (1.0=normal, 2.0=heavy)
            is_order: Whether this is an order-related task (gets priority)
            timeout: Maximum wait time in seconds
        
        Returns:
            Dict with:
                - can_proceed: bool
                - waited: float (seconds waited)
                - recommended_delay: float
                - recommended_batch_size: int
                - throttle_level: str
                - reason: str or None (if can_proceed=False)
        
        Example:
            >>> check = await context.check_resources_before_task("ConditionNode", weight=1.0)
            >>> if check["can_proceed"]:
            ...     # Apply recommended settings
            ...     batch_size = check["recommended_batch_size"]
            ...     await asyncio.sleep(check["recommended_delay"])
            ...     # Execute task
        """
        if self._resource_context:
            return await self._resource_context.before_task(
                task_type=task_type,
                weight=weight,
                is_order=is_order,
                timeout=timeout,
            )
        
        # No resource context - always allow
        return {
            "can_proceed": True,
            "waited": 0.0,
            "recommended_delay": 0.0,
            "recommended_batch_size": 10,
            "throttle_level": "none",
            "reason": None,
        }
    
    async def release_resources_after_task(
        self,
        task_type: str = "default",
        weight: float = 1.0,
    ) -> None:
        """
        Release resources after task completion.
        
        Must be called after check_resources_before_task() when task completes.
        
        Args:
            task_type: Task/node type (same as before_task)
            weight: Task weight (same as before_task)
        """
        if self._resource_context:
            await self._resource_context.after_task(
                task_type=task_type,
                weight=weight,
            )
    
    def get_resource_expression_context(self) -> Dict[str, Any]:
        """
        Get resource variables for expression evaluation.
        
        Available in expressions as {{ resource.xxx }}
        
        Returns:
            Dict with resource info (recommended_batch_size, max_symbols, etc.)
        """
        if self._resource_context:
            return self._resource_context.get_expression_context()
        
        # Default values when no resource context
        return {
            "recommended_batch_size": 10,
            "max_symbols": 100,
            "max_backtest_days": 1095,
            "max_workers": 4,
            "throttle_level": "none",
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "is_healthy": True,
        }
