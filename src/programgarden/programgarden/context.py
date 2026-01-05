"""
ProgramGarden - ExecutionContext

워크플로우 실행 컨텍스트 프로토콜
- 노드 간 데이터 전달
- 실시간 데이터 주입
- 상태 관리
"""

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@runtime_checkable
class DataProvider(Protocol):
    """데이터 제공자 프로토콜"""

    async def get_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        ...

    async def get_ohlcv(
        self, symbol: str, period: str, count: int
    ) -> Optional[List[Dict[str, Any]]]:
        """OHLCV 데이터 조회"""
        ...


@runtime_checkable
class AccountProvider(Protocol):
    """계좌 정보 제공자 프로토콜"""

    async def get_balance(self) -> Dict[str, Any]:
        """잔고 조회"""
        ...

    async def get_positions(self) -> Dict[str, Any]:
        """보유 포지션 조회"""
        ...

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """미체결 주문 조회"""
        ...


@runtime_checkable
class OrderExecutor(Protocol):
    """주문 실행자 프로토콜"""

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """주문 제출"""
        ...

    async def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """주문 정정"""
        ...

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """주문 취소"""
        ...


@dataclass
class NodeOutput:
    """노드 출력 값"""

    node_id: str
    port_name: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ExecutionContext:
    """
    워크플로우 실행 컨텍스트

    노드 간 데이터 전달, 실시간 데이터 주입, 상태 관리를 담당.
    """

    def __init__(
        self,
        job_id: str,
        workflow_id: str,
        context_params: Optional[Dict[str, Any]] = None,
    ):
        self.job_id = job_id
        self.workflow_id = workflow_id
        self.context_params = context_params or {}

        # 노드 출력 저장소
        self._outputs: Dict[str, Dict[str, NodeOutput]] = {}

        # 실시간 데이터 버퍼
        self._realtime_data: Dict[str, Any] = {}

        # 프로바이더
        self._data_provider: Optional[DataProvider] = None
        self._account_provider: Optional[AccountProvider] = None
        self._order_executor: Optional[OrderExecutor] = None

        # 상태
        self._is_running = False
        self._is_paused = False

        # 이벤트 핸들러
        self._event_handlers: Dict[str, List[callable]] = {}

        # 로그
        self._logs: List[Dict[str, Any]] = []

    # === 프로바이더 설정 ===

    def set_data_provider(self, provider: DataProvider) -> None:
        """데이터 프로바이더 설정"""
        self._data_provider = provider

    def set_account_provider(self, provider: AccountProvider) -> None:
        """계좌 프로바이더 설정"""
        self._account_provider = provider

    def set_order_executor(self, executor: OrderExecutor) -> None:
        """주문 실행자 설정"""
        self._order_executor = executor

    # === 노드 출력 관리 ===

    def set_output(
        self,
        node_id: str,
        port_name: str,
        value: Any,
    ) -> None:
        """노드 출력 설정"""
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
        """노드 출력 조회"""
        node_outputs = self._outputs.get(node_id, {})

        if port_name:
            output = node_outputs.get(port_name)
            return output.value if output else None

        # 포트 이름 없으면 첫 번째 출력 반환
        if node_outputs:
            first_output = list(node_outputs.values())[0]
            return first_output.value

        return None

    def get_input(
        self,
        from_node_id: str,
        from_port: Optional[str],
    ) -> Optional[Any]:
        """엣지를 통해 연결된 입력 값 조회"""
        return self.get_output(from_node_id, from_port)

    # === 실시간 데이터 ===

    def update_realtime_data(self, key: str, value: Any) -> None:
        """실시간 데이터 업데이트"""
        self._realtime_data[key] = value

    def get_realtime_data(self, key: str) -> Optional[Any]:
        """실시간 데이터 조회"""
        return self._realtime_data.get(key)

    # === 데이터 조회 (프로바이더 위임) ===

    async def get_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        if self._data_provider:
            return await self._data_provider.get_price(symbol)
        return None

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "1d",
        count: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """OHLCV 데이터 조회"""
        if self._data_provider:
            return await self._data_provider.get_ohlcv(symbol, period, count)
        return None

    async def get_balance(self) -> Dict[str, Any]:
        """잔고 조회"""
        if self._account_provider:
            return await self._account_provider.get_balance()
        return {}

    async def get_positions(self) -> Dict[str, Any]:
        """보유 포지션 조회"""
        if self._account_provider:
            return await self._account_provider.get_positions()
        return {}

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """미체결 주문 조회"""
        if self._account_provider:
            return await self._account_provider.get_open_orders()
        return []

    # === 주문 실행 (실행자 위임) ===

    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """주문 제출"""
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
        """주문 정정"""
        if self._order_executor:
            return await self._order_executor.modify_order(
                order_id=order_id,
                price=price,
                quantity=quantity,
            )
        return {"error": "Order executor not configured"}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """주문 취소"""
        if self._order_executor:
            return await self._order_executor.cancel_order(order_id)
        return {"error": "Order executor not configured"}

    # === 상태 관리 ===

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def start(self) -> None:
        """실행 시작"""
        self._is_running = True
        self._is_paused = False

    def pause(self) -> None:
        """일시정지"""
        self._is_paused = True

    def resume(self) -> None:
        """재개"""
        self._is_paused = False

    def stop(self) -> None:
        """정지"""
        self._is_running = False

    # === 이벤트 ===

    def on(self, event_type: str, handler: callable) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def emit(self, event_type: str, data: Any = None) -> None:
        """이벤트 발행"""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)

    # === 로깅 ===

    def log(
        self,
        level: str,
        message: str,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """로그 기록"""
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
        """로그 조회"""
        logs = self._logs

        if level:
            logs = [l for l in logs if l["level"] == level]
        if node_id:
            logs = [l for l in logs if l["node_id"] == node_id]

        return logs[-limit:]
