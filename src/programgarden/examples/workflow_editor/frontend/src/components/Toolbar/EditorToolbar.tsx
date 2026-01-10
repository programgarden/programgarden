import { useState, useEffect, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useSSE } from '@/hooks/useSSE';
import {
  Play,
  Square,
  Download,
  Upload,
  FileJson,
  Trash2,
  RefreshCw,
} from 'lucide-react';

/**
 * Parse edge endpoint string.
 * Formats:
 *   - "nodeId.portName" -> { nodeId: "nodeId", port: "portName" }
 *   - "nodeId" -> { nodeId: "nodeId", port: undefined }
 */
function parseEdgeEndpoint(endpoint: string): { nodeId: string; port?: string } {
  if (!endpoint) return { nodeId: '' };
  const parts = endpoint.split('.');
  if (parts.length >= 2) {
    return { nodeId: parts[0], port: parts.slice(1).join('.') };
  }
  return { nodeId: endpoint };
}

interface WorkflowInfo {
  id: string;
  name: string;
  description?: string;
}

export default function EditorToolbar() {
  const {
    workflowName,
    isRunning,
    setRunning,
    setWorkflow,
    clearWorkflow,
    getWorkflowJson,
    addLog,
    resetNodeStates,
    nodeTypes: registeredNodeTypes,
    resetEdgeStates,
  } = useWorkflowStore();

  // SSE connection management
  const { connect: connectSSE, disconnect: disconnectSSE } = useSSE();

  const [availableWorkflows, setAvailableWorkflows] = useState<WorkflowInfo[]>([]);
  const [showWorkflowMenu, setShowWorkflowMenu] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load available workflows
  useEffect(() => {
    fetch('/workflows')
      .then((res) => res.json())
      .then((data) => {
        setAvailableWorkflows(data.workflows || []);
      })
      .catch((err) => console.error('Failed to load workflows:', err));
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      disconnectSSE();
    };
  }, [disconnectSSE]);

  const handleRun = async () => {
    try {
      // 1. Reset states first
      resetNodeStates();
      resetEdgeStates();
      addLog({ level: 'info', message: '🔌 Connecting to event stream...' });

      // 2. Connect SSE FIRST (before starting execution)
      await connectSSE();
      addLog({ level: 'info', message: '✅ Event stream connected' });

      // 3. Mark as running
      setRunning(true);
      addLog({ level: 'info', message: '🚀 Starting workflow execution...' });

      // 4. Start execution
      const workflow = getWorkflowJson();
      const response = await fetch('/api/workflow/run-inline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to start workflow');
      }

      const result = await response.json();
      addLog({ level: 'success', message: `📋 Job started: ${result.jobId}` });
    } catch (err) {
      addLog({ level: 'error', message: `❌ Error: ${err}` });
      disconnectSSE();
      setRunning(false);
    }
  };

  const handleStop = async () => {
    try {
      const response = await fetch('/stop', { method: 'POST' });
      if (response.ok) {
        addLog({ level: 'info', message: '🛑 Stop signal sent' });
        // Stop 후 상태 업데이트
        disconnectSSE();
        setRunning(false);
        resetNodeStates();
      }
    } catch (err) {
      addLog({ level: 'error', message: `Error stopping: ${err}` });
    }
  };

  const handleLoadWorkflow = async (workflowId: string) => {
    try {
      const response = await fetch(`/workflow/${workflowId}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `워크플로우 "${workflowId}" 로드 실패 (${response.status})`;
        
        // 특정 에러 메시지 파싱
        if (errorText.includes('APPKEY') || errorText.includes('APPSECRET') || errorText.includes('.env')) {
          errorMessage = `워크플로우 "${workflowId}"에 필요한 환경 변수가 설정되지 않았습니다. .env 파일에 APPKEY, APPSECRET 등을 설정하세요.`;
        } else if (response.status === 500) {
          errorMessage = `서버 에러: 워크플로우 "${workflowId}" 로드 중 문제가 발생했습니다.`;
        }
        
        addLog({ level: 'error', message: errorMessage });
        setShowWorkflowMenu(false);
        return;
      }
      
      const data = await response.json();

      // Build node type schema map for lookup
      const nodeTypeMap = new Map(
        registeredNodeTypes.map((t) => [t.node_type, t])
      );

      // Convert to React Flow format with schema merge
      const nodes = data.nodes.map((node: Record<string, unknown>) => {
        const schema = nodeTypeMap.get(node.type as string);
        const isDisplayNode = node.type === 'DisplayNode';
        
        // Set style for DisplayNode (for NodeResizer)
        const nodeStyle = isDisplayNode 
          ? { width: node.width || 300, height: node.height || 200 }
          : undefined;
        
        return {
          id: node.id,
          type: isDisplayNode ? 'displayNode' : 'customNode',
          position: node.position || { x: 0, y: 0 },
          ...(nodeStyle && { style: nodeStyle }),
          data: {
            label: node.id,
            nodeType: node.type,
            category: schema?.category || node.category || 'group',
            inputs: schema?.inputs || [],
            outputs: schema?.outputs || [],
            configSchema: schema?.config_schema || {},
            ...node, // Merge saved config values
          },
        };
      });

      const edges = (data.edges || []).map((edge: Record<string, unknown>) => {
        const fromStr = String(edge.from || '');
        const toStr = String(edge.to || '');
        const from = parseEdgeEndpoint(fromStr);
        const to = parseEdgeEndpoint(toStr);
        return {
          id: `e_${fromStr}_${toStr}`,
          source: from.nodeId,
          target: to.nodeId,
          sourceHandle: from.port || undefined,
          targetHandle: to.port || undefined,
          type: 'smoothstep',
        };
      });

      setWorkflow({
        id: data.id || workflowId,
        name: data.name || workflowId,
        description: data.description,
        nodes,
        edges,
      });
      setShowWorkflowMenu(false);
      addLog({ level: 'success', message: `워크플로우 "${data.name || workflowId}" 로드 완료` });
    } catch (err) {
      addLog({ level: 'error', message: `워크플로우 로드 실패: ${err}` });
      setShowWorkflowMenu(false);
    }
  };

  const handleExportJson = () => {
    const workflow = getWorkflowJson();
    const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/\s+/g, '_').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    addLog({ level: 'success', message: 'Workflow exported' });
  };

  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);

        // Build node type schema map for lookup
        const nodeTypeMap = new Map(
          registeredNodeTypes.map((t) => [t.node_type, t])
        );

        // Convert to React Flow format with schema merge
        const nodes = (data.nodes || []).map((node: Record<string, unknown>) => {
          const schema = nodeTypeMap.get(node.type as string);
          const isDisplayNode = node.type === 'DisplayNode';
          
          // Set style for DisplayNode (for NodeResizer)
          const nodeStyle = isDisplayNode 
            ? { width: node.width || 300, height: node.height || 200 }
            : undefined;
          
          return {
            id: node.id,
            type: isDisplayNode ? 'displayNode' : 'customNode',
            position: node.position || { x: 0, y: 0 },
            ...(nodeStyle && { style: nodeStyle }),
            data: {
              label: node.id,
              nodeType: node.type,
              category: schema?.category || node.category || 'group',
              inputs: schema?.inputs || [],
              outputs: schema?.outputs || [],
              configSchema: schema?.config_schema || {},
              ...node, // Merge saved config values
            },
          };
        });

        const edges = (data.edges || []).map((edge: Record<string, unknown>) => {
          const fromStr = String(edge.from || '');
          const toStr = String(edge.to || '');
          const from = parseEdgeEndpoint(fromStr);
          const to = parseEdgeEndpoint(toStr);
          return {
            id: `e_${fromStr}_${toStr}`,
            source: from.nodeId,
            target: to.nodeId,
            sourceHandle: from.port || undefined,
            targetHandle: to.port || undefined,
            type: 'smoothstep',
          };
        });

        setWorkflow({
          id: data.id || 'imported',
          name: data.name || file.name.replace('.json', ''),
          description: data.description,
          nodes,
          edges,
        });
        addLog({ level: 'success', message: `Imported: ${file.name}` });
      } catch (err) {
        addLog({ level: 'error', message: `Invalid JSON file: ${err}` });
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
      {/* Left: Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <span>🌱</span>
          <span>ProgramGarden</span>
        </h1>
        <span className="text-gray-400 text-sm">{workflowName}</span>
      </div>

      {/* Center: Actions */}
      <div className="flex items-center gap-2">
        {/* Load Workflow */}
        <div className="relative">
          <button
            onClick={() => setShowWorkflowMenu(!showWorkflowMenu)}
            className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-gray-200 transition-colors"
          >
            <FileJson className="w-4 h-4" />
            Open
          </button>
          {showWorkflowMenu && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-gray-700 rounded-lg shadow-lg z-50 border border-gray-600 max-h-64 overflow-y-auto">
              {availableWorkflows.map((wf) => (
                <button
                  key={wf.id}
                  onClick={() => handleLoadWorkflow(wf.id)}
                  className="w-full px-4 py-2 text-left hover:bg-gray-600 text-sm"
                >
                  <div className="text-gray-200">{wf.name}</div>
                  {wf.description && (
                    <div className="text-gray-400 text-xs truncate">{wf.description}</div>
                  )}
                </button>
              ))}
              {availableWorkflows.length === 0 && (
                <div className="px-4 py-2 text-gray-400 text-sm">No workflows available</div>
              )}
            </div>
          )}
        </div>

        {/* Import */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleImportJson}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-gray-200 transition-colors"
          title="Import JSON"
        >
          <Upload className="w-4 h-4" />
        </button>

        {/* Export */}
        <button
          onClick={handleExportJson}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-gray-200 transition-colors"
          title="Export JSON"
        >
          <Download className="w-4 h-4" />
        </button>

        {/* Clear */}
        <button
          onClick={() => {
            if (confirm('Clear current workflow?')) {
              clearWorkflow();
            }
          }}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-gray-200 transition-colors"
          title="New Workflow"
        >
          <Trash2 className="w-4 h-4" />
        </button>

        <div className="w-px h-6 bg-gray-600 mx-2" />

        {/* Run */}
        <button
          onClick={handleRun}
          disabled={isRunning}
          className={`flex items-center gap-2 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
            isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-500 text-white'
          }`}
        >
          {isRunning ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {isRunning ? 'Running...' : 'Run'}
        </button>

        {/* Stop */}
        <button
          onClick={handleStop}
          disabled={!isRunning}
          className={`flex items-center gap-2 px-4 py-1.5 rounded text-sm font-medium transition-colors ${
            !isRunning
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-red-600 hover:bg-red-500 text-white'
          }`}
        >
          <Square className="w-4 h-4" />
          Stop
        </button>
      </div>

      {/* Right: Status */}
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}
        />
        <span className="text-xs text-gray-400">
          {isRunning ? 'Running' : 'Idle'}
        </span>
      </div>
    </header>
  );
}
