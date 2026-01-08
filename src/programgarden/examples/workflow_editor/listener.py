"""
SSE (Server-Sent Events) Listener for Flow Visualizer.

Implements ExecutionListener to broadcast workflow execution events
to connected browser clients via SSE.
"""

import asyncio
import json
from typing import Set, AsyncGenerator, Any
from datetime import datetime
from decimal import Decimal

from programgarden_core.bases.listener import (
    BaseExecutionListener,
    NodeStateEvent,
    EdgeStateEvent,
    LogEvent,
    JobStateEvent,
)


class SafeJSONEncoder(json.JSONEncoder):
    """JSON 인코더 - Pydantic 모델 및 특수 타입 처리"""
    
    def default(self, obj: Any) -> Any:
        # Pydantic BaseModel
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        # Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        # datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
        # dataclass
        if hasattr(obj, '__dataclass_fields__'):
            return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
        # 일반 객체는 str로 변환
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class SSEListener(BaseExecutionListener):
    """
    Server-Sent Events broadcast listener.
    
    Collects events from workflow execution and broadcasts them
    to all connected SSE clients.
    
    Usage:
        listener = SSEListener()
        job = await pg.run_async(workflow, listeners=[listener])
        
        # In FastAPI route:
        @app.get("/events")
        async def sse():
            return StreamingResponse(
                listener.stream(),
                media_type="text/event-stream"
            )
    """
    
    def __init__(self):
        self._queues: Set[asyncio.Queue] = set()
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe a new client. Returns queue for receiving events."""
        queue = asyncio.Queue()
        self._queues.add(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe a client."""
        self._queues.discard(queue)
    
    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._queues)
    
    async def _broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast event to all subscribed clients."""
        # Debug logging
        identifier = data.get('node_id') or data.get('job_id') or 'unknown'
        print(f"📤 Broadcasting {event_type}: {identifier} (clients: {len(self._queues)})")
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        for queue in self._queues.copy():
            try:
                await queue.put(message)
            except Exception:
                # Remove dead queues
                self._queues.discard(queue)
    
    # === ExecutionListener Implementation ===
    
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        """Broadcast node state change to clients."""
        await self._broadcast("node_state", {
            "job_id": event.job_id,
            "node_id": event.node_id,
            "node_type": event.node_type,
            "state": event.state.value,
            "outputs": event.outputs,
            "error": event.error,
            "duration_ms": event.duration_ms,
        })
    
    async def on_edge_state_change(self, event: EdgeStateEvent) -> None:
        """Broadcast edge state change to clients."""
        await self._broadcast("edge_state", {
            "job_id": event.job_id,
            "from_node": event.from_node_id,
            "from_port": event.from_port,
            "to_node": event.to_node_id,
            "to_port": event.to_port,
            "state": event.state.value,
            "data_preview": event.data_preview,
        })
    
    async def on_log(self, event: LogEvent) -> None:
        """Broadcast log entry to clients."""
        await self._broadcast("log", {
            "job_id": event.job_id,
            "level": event.level,
            "message": event.message,
            "node_id": event.node_id,
        })
    
    async def on_job_state_change(self, event: JobStateEvent) -> None:
        """Broadcast job state change to clients."""
        await self._broadcast("job_state", {
            "job_id": event.job_id,
            "status": event.state,
            "stats": event.stats,
        })
    
    # === SSE Stream Generator ===
    
    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Generate SSE event stream for a client.
        
        Usage in FastAPI:
            return StreamingResponse(listener.stream(), media_type="text/event-stream")
        """
        queue = self.subscribe()
        try:
            while True:
                try:
                    # Wait for event with timeout (for keep-alive)
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = message.get("type", "message")
                    # SSE format: event type + data (required for EventSource.addEventListener)
                    yield f"event: {event_type}\ndata: {json.dumps(message['data'], cls=SafeJSONEncoder)}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive comment
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe(queue)
