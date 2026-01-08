import { useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';

interface WorkflowJson {
  id: string;
  name: string;
  description?: string;
  nodes?: unknown[];
  edges?: unknown[];
}

export default function JsonViewer() {
  const { getWorkflowJson } = useWorkflowStore();
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const workflowJson = getWorkflowJson() as WorkflowJson;
  const jsonString = JSON.stringify(workflowJson, null, 2);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-800 border-t border-gray-700">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-200">📝 JSON</span>
          <span className="text-xs text-gray-500">
            ({workflowJson.nodes?.length || 0} nodes, {workflowJson.edges?.length || 0} edges)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
            className="p-1 text-gray-400 hover:text-white rounded hover:bg-gray-700"
            title="Copy JSON"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* JSON Content */}
      {expanded && (
        <div className="max-h-[500px] overflow-auto border-t border-gray-700">
          <pre className="p-4 text-xs text-gray-300 font-mono whitespace-pre-wrap">
            {jsonString}
          </pre>
        </div>
      )}
    </div>
  );
}
