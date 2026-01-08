# Flow Visualizer Example

Web-based workflow visualization dashboard demonstrating the ExecutionListener callback system.

## Features

- **Flow Dashboard**: Visual representation of workflow nodes and edges
- **Real-time Animation**: Node states change color during execution (pending → running → completed)
- **Edge Animation**: Data flow shown with animated transitions
- **Log Panel**: Real-time log output at the bottom

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (index.html)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Flow Canvas (SVG/CSS)                   │   │
│  │    [Start] ──→ [Schedule] ──→ [Watchlist] ──→ ...   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Log Panel                               │   │
│  │  10:00:01 [start] Workflow started                  │   │
│  │  10:00:02 [broker] Connected to LS Securities       │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ SSE (Server-Sent Events)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Server (server.py)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           SSEListener (listener.py)                  │   │
│  │  - on_node_state_change() → broadcast to clients    │   │
│  │  - on_edge_state_change() → broadcast to clients    │   │
│  │  - on_log() → broadcast to clients                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           ProgramGarden Executor                     │   │
│  │  job = await pg.run_async(workflow, listeners=[...]) │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### 1. Install dependencies

```bash
cd src/programgarden
poetry install
poetry add fastapi uvicorn sse-starlette
```

### 2. Run the server

```bash
cd src/programgarden
poetry run python -m examples.10_ui.01_flow_visualizer.run
```

### 3. Open browser

Navigate to http://localhost:8765

### 4. Click "Run" button

Watch the workflow execute with real-time visualization!

## Files

| File | Description |
|------|-------------|
| `workflow.py` | Demo workflow definition (JSON) |
| `listener.py` | SSEListener - ExecutionListener implementation |
| `server.py` | FastAPI + SSE server |
| `run.py` | Entry point script |
| `static/index.html` | Dashboard HTML |
| `static/styles.css` | Dashboard styles |
| `static/app.js` | Frontend JavaScript (SSE client + rendering) |

## Callback Flow

1. User clicks "Run" button → `POST /run`
2. Server creates `SSEListener` and passes to `pg.run_async()`
3. Executor calls `notify_node_state()` → `SSEListener.on_node_state_change()`
4. SSEListener broadcasts event via SSE to all connected clients
5. Browser receives event → updates node color/animation

## Extending

To create your own listener (e.g., for WebSocket, database logging):

```python
from programgarden_core.bases.listener import BaseExecutionListener, NodeStateEvent

class MyListener(BaseExecutionListener):
    async def on_node_state_change(self, event: NodeStateEvent) -> None:
        # Save to database, send WebSocket message, etc.
        await self.db.insert({
            "job_id": event.job_id,
            "node_id": event.node_id,
            "state": event.state.value,
            "timestamp": event.timestamp,
        })
```
