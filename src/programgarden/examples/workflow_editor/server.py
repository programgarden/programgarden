"""
ProgramGarden Workflow Editor Server

10_ui 폴더의 메인 서버.
- React 기반 워크플로우 편집기 서빙
- 워크플로우 실행 및 SSE 이벤트 스트리밍
- NodeRegistry API 제공

실행:
    cd src/programgarden
    poetry run python examples/10_ui/server.py
"""

import sys
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parents[3]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

from listener import SSEListener
from workflows import get_all_workflows, get_workflow_by_id, get_all_categories, get_workflows_by_category

app = FastAPI(title="ProgramGarden Workflow Editor")

# Static files (React build output)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

# Global listener (shared across all jobs)
sse_listener = SSEListener()

# Current running job
current_job = None


# ========================================
# Pydantic Models
# ========================================

class WorkflowRunRequest(BaseModel):
    """Request body for inline workflow execution"""
    id: str = "inline-workflow"
    name: str = "Inline Workflow"
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


# ========================================
# Static File Serving (React SPA)
# ========================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve React app index.html"""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return HTMLResponse("""
        <html>
        <head><title>ProgramGarden Workflow Editor</title></head>
        <body style="font-family: sans-serif; padding: 2rem; background: #1f2937; color: white;">
            <h1>🌱 ProgramGarden Workflow Editor</h1>
            <p>Frontend not built yet. Run:</p>
            <pre style="background: #374151; padding: 1rem; border-radius: 8px;">
cd src/programgarden/examples/10_ui/frontend
npm install
npm run build</pre>
            <p>Then refresh this page.</p>
        </body>
        </html>
    """)


@app.get("/categories")
async def list_categories():
    """워크플로우 카테고리 목록 반환"""
    categories = get_all_categories()
    return JSONResponse({"categories": categories})


@app.get("/categories/{category_id}/workflows")
async def list_workflows_by_category(category_id: str):
    """카테고리별 워크플로우 목록 반환"""
    try:
        workflows = get_workflows_by_category(category_id)
        return JSONResponse({
            "category": category_id,
            "workflows": [
                {"id": wf["id"], "name": wf["name"], "description": wf["description"]}
                for wf in workflows
            ]
        })
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)


@app.get("/workflows")
async def list_workflows():
    """워크플로우 목록 반환 (카테고리 정보 포함)"""
    workflows = get_all_workflows()
    return JSONResponse({
        "workflows": [
            {
                "id": wf["id"],
                "name": wf["name"],
                "description": wf["description"],
                "category": wf.get("category"),
                "category_name": wf.get("category_name"),
            }
            for wf in workflows
        ]
    })


@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """특정 워크플로우 정의 반환"""
    try:
        workflow = get_workflow_by_id(workflow_id)
        return JSONResponse(workflow)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)


@app.get("/events")
async def sse_events(request: Request):
    """SSE event stream endpoint."""
    async def event_generator():
        async for event in sse_listener.stream():
            if await request.is_disconnected():
                break
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/run/{workflow_id}")
async def run_workflow(workflow_id: str):
    """워크플로우 실행"""
    global current_job
    
    # Check if already running
    if current_job and current_job.status == "running":
        return JSONResponse(
            {"error": "Job already running", "jobId": current_job.job_id},
            status_code=400
        )
    
    try:
        from programgarden import ProgramGarden
        
        print(f"\n🚀 Starting workflow: {workflow_id}")
        
        pg = ProgramGarden()
        workflow = get_workflow_by_id(workflow_id)
        
        print(f"📋 Workflow: {workflow.get('name', 'unknown')}")
        print(f"📋 Nodes: {len(workflow.get('nodes', []))}")
        
        current_job = await pg.run_async(
            workflow,
            listeners=[sse_listener],
        )
        
        print(f"✅ Job started: {current_job.job_id}")
        return {"jobId": current_job.job_id, "status": "started"}
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
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
    """실행 중인 워크플로우 중지"""
    global current_job
    
    if not current_job:
        return JSONResponse({"error": "No job running"}, status_code=400)
    
    try:
        await current_job.stop()
        return {"jobId": current_job.job_id, "status": "stopped"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/status")
async def get_status():
    """현재 Job 상태 조회"""
    if not current_job:
        return {"status": "idle", "job": None}
    
    return {
        "status": current_job.status,
        "job": current_job.get_state(),
    }


# ========================================
# Node Registry API
# ========================================

@app.get("/api/node-types")
async def get_node_types():
    """모든 노드 타입 스키마 반환"""
    import json
    
    def safe_serialize(obj):
        """Recursively convert objects to JSON-safe types"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [safe_serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items() if v is not None}
        if hasattr(obj, "model_dump"):
            try:
                return safe_serialize(obj.model_dump(exclude_unset=True, exclude_none=True))
            except:
                return str(obj)
        if hasattr(obj, "__dict__"):
            return safe_serialize(obj.__dict__)
        # For PydanticUndefinedType and other unknown types
        return None
    
    try:
        from programgarden_core.registry import NodeTypeRegistry
        
        registry = NodeTypeRegistry()
        schemas = registry.list_schemas()
        
        node_types = []
        for schema in schemas:
            try:
                node_type_dict = {
                    "node_type": str(getattr(schema, "node_type", "Unknown")),
                    "category": str(getattr(schema, "category", "group")),
                    "description": str(getattr(schema, "description", "") or ""),
                    "inputs": safe_serialize(getattr(schema, "inputs", []) or []),
                    "outputs": safe_serialize(getattr(schema, "outputs", []) or []),
                    "config_schema": safe_serialize(getattr(schema, "config_schema", {}) or {}),
                }
                node_types.append(node_type_dict)
            except Exception as e:
                node_types.append({
                    "node_type": str(getattr(schema, "node_type", "Unknown")),
                    "category": "group",
                    "description": "",
                    "inputs": [],
                    "outputs": [],
                    "config_schema": {},
                })
        
        return JSONResponse({"node_types": node_types})
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "node_types": []
        }, status_code=500)


@app.get("/api/node-types/{node_type}")
async def get_node_type_schema(node_type: str):
    """특정 노드 타입 스키마 반환"""
    try:
        from programgarden_core.registry import NodeTypeRegistry
        
        registry = NodeTypeRegistry()
        schema = registry.get_schema(node_type)
        
        if not schema:
            return JSONResponse({"error": f"Unknown node type: {node_type}"}, status_code=404)
        
        return JSONResponse(schema.model_dump())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/categories")
async def get_categories():
    """카테고리 목록 반환"""
    try:
        from programgarden_core.registry import NodeTypeRegistry
        
        registry = NodeTypeRegistry()
        categories = registry.list_categories()
        
        return JSONResponse({"categories": categories})
    except Exception as e:
        return JSONResponse({"error": str(e), "categories": []}, status_code=500)


# ========================================
# Credential API (n8n style)
# ========================================

class CredentialCreateRequest(BaseModel):
    """Request body for creating a credential"""
    name: str
    credential_type: str
    data: Dict[str, Any]
    user_id: str = "default"


class CredentialUpdateRequest(BaseModel):
    """Request body for updating a credential"""
    name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@app.get("/api/credential-types")
async def get_credential_types():
    """모든 credential 타입 스키마 반환"""
    try:
        from programgarden_core.registry import get_credential_type_registry
        
        registry = get_credential_type_registry()
        schemas = registry.list_types()
        
        return JSONResponse({
            "credential_types": [
                schema.model_dump(mode='json')
                for schema in schemas
            ]
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "credential_types": []
        }, status_code=500)


@app.get("/api/credential-types/{type_id}")
async def get_credential_type(type_id: str):
    """특정 credential 타입 스키마 반환"""
    try:
        from programgarden_core.registry import get_credential_type_registry
        
        registry = get_credential_type_registry()
        schema = registry.get(type_id)
        
        if not schema:
            return JSONResponse({"error": f"Unknown credential type: {type_id}"}, status_code=404)
        
        return JSONResponse(schema.model_dump(mode='json'))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/credentials")
async def list_credentials(user_id: str = "default", credential_type: Optional[str] = None):
    """Credential 목록 반환 (데이터는 마스킹)"""
    try:
        from programgarden_core.registry import get_credential_store
        
        store = get_credential_store()
        credentials = store.list(user_id=user_id, credential_type=credential_type)
        
        # Mask sensitive data
        result = []
        for cred in credentials:
            masked_data = {}
            for key, value in cred.data.items():
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                elif isinstance(value, bool):
                    masked_data[key] = value
                else:
                    masked_data[key] = "***"
            
            result.append({
                "id": cred.id,
                "name": cred.name,
                "credential_type": cred.credential_type,
                "user_id": cred.user_id,
                "data": masked_data,
                "created_at": cred.created_at.isoformat() if cred.created_at else None,
                "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
            })
        
        return JSONResponse({"credentials": result})
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "credentials": []
        }, status_code=500)


@app.get("/api/credentials/{credential_id}")
async def get_credential(credential_id: str):
    """특정 credential 조회 (데이터는 마스킹)"""
    try:
        from programgarden_core.registry import get_credential_store
        
        store = get_credential_store()
        cred = store.get(credential_id)
        
        if not cred:
            return JSONResponse({"error": f"Credential not found: {credential_id}"}, status_code=404)
        
        # Mask sensitive data
        masked_data = {}
        for key, value in cred.data.items():
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
            elif isinstance(value, bool):
                masked_data[key] = value
            else:
                masked_data[key] = "***"
        
        return JSONResponse({
            "id": cred.id,
            "name": cred.name,
            "credential_type": cred.credential_type,
            "user_id": cred.user_id,
            "data": masked_data,
            "created_at": cred.created_at.isoformat() if cred.created_at else None,
            "updated_at": cred.updated_at.isoformat() if cred.updated_at else None,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/credentials")
async def create_credential(request: CredentialCreateRequest):
    """새 credential 생성"""
    try:
        from programgarden_core.registry import get_credential_store, get_credential_type_registry
        from programgarden_core.models import Credential
        import uuid
        
        # Validate credential type
        type_registry = get_credential_type_registry()
        if not type_registry.get(request.credential_type):
            return JSONResponse({
                "error": f"Unknown credential type: {request.credential_type}"
            }, status_code=400)
        
        # Create credential
        cred = Credential(
            id=str(uuid.uuid4()),
            name=request.name,
            credential_type=request.credential_type,
            user_id=request.user_id,
            data=request.data,
        )
        
        store = get_credential_store()
        created = store.create(cred)
        
        return JSONResponse({
            "id": created.id,
            "name": created.name,
            "credential_type": created.credential_type,
            "message": "Credential created successfully",
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status_code=500)


@app.put("/api/credentials/{credential_id}")
async def update_credential(credential_id: str, request: CredentialUpdateRequest):
    """Credential 업데이트"""
    try:
        from programgarden_core.registry import get_credential_store
        
        store = get_credential_store()
        
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.data is not None:
            updates["data"] = request.data
        
        if not updates:
            return JSONResponse({"error": "No updates provided"}, status_code=400)
        
        updated = store.update(credential_id, updates)
        
        if not updated:
            return JSONResponse({"error": f"Credential not found: {credential_id}"}, status_code=404)
        
        return JSONResponse({
            "id": updated.id,
            "name": updated.name,
            "message": "Credential updated successfully",
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/credentials/{credential_id}")
async def delete_credential(credential_id: str):
    """Credential 삭제"""
    try:
        from programgarden_core.registry import get_credential_store
        
        store = get_credential_store()
        deleted = store.delete(credential_id)
        
        if not deleted:
            return JSONResponse({"error": f"Credential not found: {credential_id}"}, status_code=404)
        
        return JSONResponse({"message": "Credential deleted successfully"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ========================================
# Workflow Execution API
# ========================================

@app.post("/api/workflow/run-inline")
async def run_workflow_inline(request: WorkflowRunRequest):
    """JSON 워크플로우 직접 실행 (저장 없이)"""
    global current_job
    
    # Check if already running
    if current_job and current_job.status == "running":
        return JSONResponse(
            {"error": "Job already running", "jobId": current_job.job_id},
            status_code=400
        )
    
    try:
        from programgarden import ProgramGarden
        
        print(f"\n🚀 Starting inline workflow: {request.name}")
        
        # Convert React Flow format to ProgramGarden format
        workflow = {
            "id": request.id,
            "name": request.name,
            "description": request.description,
            "nodes": request.nodes,
            "edges": [
                {
                    "from": edge.get("from") or edge.get("source"),
                    "to": edge.get("to") or edge.get("target"),
                    **({"from_port": edge["from_port"]} if "from_port" in edge else {}),
                    **({"to_port": edge["to_port"]} if "to_port" in edge else {}),
                }
                for edge in request.edges
            ],
        }
        
        print(f"📋 Nodes: {len(workflow['nodes'])}")
        print(f"📋 Edges: {len(workflow['edges'])}")
        
        pg = ProgramGarden()
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


@app.post("/api/workflow/validate")
async def validate_workflow(request: WorkflowRunRequest):
    """워크플로우 유효성 검증"""
    errors = []
    warnings = []
    
    # Basic validation
    if not request.nodes:
        errors.append("Workflow must have at least one node")
    
    # Check for StartNode
    start_nodes = [n for n in request.nodes if n.get("type") == "StartNode"]
    if not start_nodes:
        warnings.append("Workflow has no StartNode")
    elif len(start_nodes) > 1:
        warnings.append("Workflow has multiple StartNodes")
    
    # Check for orphan nodes
    connected_nodes = set()
    for edge in request.edges:
        connected_nodes.add(edge.get("from") or edge.get("source"))
        connected_nodes.add(edge.get("to") or edge.get("target"))
    
    node_ids = {n.get("id") for n in request.nodes}
    orphans = node_ids - connected_nodes - {"start"}  # StartNode is OK to be unconnected
    if orphans:
        warnings.append(f"Unconnected nodes: {', '.join(orphans)}")
    
    return JSONResponse({
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    })


def main(host: str = "0.0.0.0", port: int = 8765):
    """Run the server."""
    print("\n" + "=" * 50)
    print("🌱 ProgramGarden Workflow Editor")
    print("=" * 50)
    print(f"\n📍 Open http://localhost:{port} in your browser")
    print("   Press Ctrl+C to stop")
    print("\n📁 Frontend: " + str(static_dir))
    if not (static_dir / "index.html").exists():
        print("   ⚠️  Frontend not built. Run:")
        print("      cd frontend && npm install && npm run build")
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
