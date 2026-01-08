import { useState, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import WorkflowCanvas from './components/Canvas/WorkflowCanvas';
import NodePalette from './components/Sidebar/NodePalette';
import PropertiesPanel from './components/Panel/PropertiesPanel';
import JsonViewer from './components/Panel/JsonViewer';
import EditorToolbar from './components/Toolbar/EditorToolbar';
import ExecutionLog from './components/Log/ExecutionLog';
import { useWorkflowStore } from './stores/workflowStore';
import { PanelLeftClose, PanelLeft, Code } from 'lucide-react';

export default function App() {
  const [showPalette, setShowPalette] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const setNodeTypes = useWorkflowStore((state) => state.setNodeTypes);
  const nodeTypesLoaded = useWorkflowStore((state) => state.nodeTypesLoaded);

  // Preload node types on app start
  useEffect(() => {
    if (nodeTypesLoaded) return;
    
    fetch('/api/node-types')
      .then((res) => res.json())
      .then((data) => {
        if (data.node_types) {
          setNodeTypes(data.node_types);
        }
      })
      .catch((err) => console.error('Failed to load node types:', err));
  }, [nodeTypesLoaded, setNodeTypes]);

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-gray-900 text-gray-100">
        {/* Toolbar */}
        <EditorToolbar />

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Toggle Palette Button */}
          <button
            onClick={() => setShowPalette(!showPalette)}
            className="absolute top-2 left-2 z-50 p-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
            title={showPalette ? 'Hide Node Palette' : 'Show Node Palette'}
          >
            {showPalette ? (
              <PanelLeftClose className="w-5 h-5 text-gray-300" />
            ) : (
              <PanelLeft className="w-5 h-5 text-gray-300" />
            )}
          </button>

          {/* Toggle JSON Button */}
          <button
            onClick={() => setShowJson(!showJson)}
            className={`absolute top-2 right-2 z-50 p-2 rounded-lg border transition-colors ${
              showJson 
                ? 'bg-blue-600 hover:bg-blue-700 border-blue-500' 
                : 'bg-gray-800 hover:bg-gray-700 border-gray-600'
            }`}
            title={showJson ? 'Hide JSON' : 'Show JSON'}
          >
            <Code className="w-5 h-5 text-gray-300" />
          </button>

          {/* Left Sidebar - Node Palette (toggleable) */}
          {showPalette && (
            <div className="absolute top-0 left-0 z-40 h-full">
              <NodePalette onClose={() => setShowPalette(false)} />
            </div>
          )}

          {/* Center - Canvas & Logs */}
          <div className="flex-1 flex flex-col">
            {/* Canvas */}
            <div className="flex-1">
              <WorkflowCanvas />
            </div>

            {/* Execution Log */}
            <ExecutionLog />
          </div>

          {/* Right Panel - Properties (only when node selected) */}
          {selectedNodeId && (
            <div className="w-80 flex flex-col border-l border-gray-700 bg-gray-800">
              <div className="flex-1 overflow-y-auto">
                <PropertiesPanel />
              </div>
            </div>
          )}

          {/* JSON Viewer Panel (toggleable) */}
          {showJson && (
            <div className="w-96 border-l border-gray-700 bg-gray-800">
              <JsonViewer />
            </div>
          )}
        </div>
      </div>
    </ReactFlowProvider>
  );
}
