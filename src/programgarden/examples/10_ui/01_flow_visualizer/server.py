"""
FastAPI server for Flow Visualizer.

Provides:
- Static file serving (HTML/CSS/JS)
- SSE endpoint for real-time events
- REST endpoints for workflow control
"""

import sys
from pathlib import Path
from typing import Optional

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parents[4]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
import uvicorn

# Import from same directory (absolute imports after path setup)
from workflow import get_demo_workflow
from listener import SSEListener

app = FastAPI(title="ProgramGarden Flow Visualizer")

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global listener (shared across all jobs)
sse_listener = SSEListener()

# Current running job
current_job = None


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve dashboard page."""
    html_path = static_dir / "index.html"
    return html_path.read_text()


@app.get("/workflow")
async def get_workflow():
    """Return workflow definition for UI rendering."""
    return JSONResponse(get_demo_workflow())


@app.get("/events")
async def sse_events(request: Request):
    """SSE event stream endpoint."""
    async def event_generator():
        async for event in sse_listener.stream():
            # Check if client disconnected
            if await request.is_disconnected():
                break
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.post("/run")
async def run_workflow():
    """Start workflow execution."""
    global current_job
    
    # Check if already running
    if current_job and current_job.status == "running":
        return JSONResponse(
            {"error": "Job already running", "jobId": current_job.job_id},
            status_code=400
        )
    
    try:
        from programgarden import ProgramGarden
        import traceback
        
        print("\n🚀 Starting workflow execution...")
        
        pg = ProgramGarden()
        
        # Run with SSE listener
        workflow = get_demo_workflow()
        print(f"📋 Workflow: {workflow.get('name', 'unknown')}")
        print(f"📋 Nodes: {[n.get('id') for n in workflow.get('nodes', [])]}")
        
        current_job = await pg.run_async(
            workflow,
            listeners=[sse_listener],
        )
        
        print(f"✅ Job started: {current_job.job_id}")
        return {"jobId": current_job.job_id, "status": "started"}
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error starting workflow:")
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@app.post("/stop")
async def stop_workflow():
    """Stop running workflow."""
    global current_job
    
    if not current_job:
        return JSONResponse(
            {"error": "No job running"},
            status_code=400
        )
    
    try:
        await current_job.stop()
        return {"jobId": current_job.job_id, "status": "stopped"}
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.get("/status")
async def get_status():
    """Get current job status."""
    if not current_job:
        return {"status": "idle", "job": None}
    
    return {
        "status": current_job.status,
        "job": current_job.get_state(),
    }


def main(host: str = "0.0.0.0", port: int = 8765):
    """Run the server."""
    print("\n" + "=" * 50)
    print("🌱 ProgramGarden Flow Visualizer")
    print("=" * 50)
    print(f"\n📍 Open http://localhost:{port} in your browser")
    print("   Press Ctrl+C to stop\n")
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
