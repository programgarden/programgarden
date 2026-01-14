import { Node } from '@xyflow/react';
import NodeDataTree from './NodeDataTree';

interface InputTabProps {
  inputData: Record<string, unknown>;
  upstreamNodes: Node[];
  onFieldClick: (expression: string) => void;
  targetField: string | null;  // 현재 포커스된 필드
}

export default function InputTab({ 
  inputData, 
  upstreamNodes, 
  onFieldClick,
  targetField,
}: InputTabProps) {
  if (Object.keys(inputData).length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        <p className="text-lg mb-2">📭 No input data</p>
        <p className="text-xs">Run the workflow to see data from previous nodes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 현재 포커스된 필드 표시 */}
      {targetField ? (
        <div className="bg-blue-900/30 border border-blue-600 rounded-lg p-3">
          <p className="text-xs text-blue-300">
            🎯 Click a value to insert into <span className="font-bold text-blue-200">"{targetField}"</span>
          </p>
        </div>
      ) : (
        <div className="bg-gray-700/30 rounded-lg p-3">
          <p className="text-xs text-gray-400">
            💡 First, click a field in Parameters/Settings tab, then come back here to select a value
          </p>
        </div>
      )}

      {upstreamNodes.map((node) => {
        const nodeData = inputData[node.id];
        if (!nodeData) return null;

        const nodeLabel = (node.data as Record<string, unknown>).label as string 
          || (node.data as Record<string, unknown>).nodeType as string;
        const nodeType = (node.data as Record<string, unknown>).nodeType as string | undefined;

        return (
          <NodeDataTree
            key={node.id}
            nodeId={node.id}
            nodeLabel={nodeLabel}
            nodeType={nodeType}
            data={nodeData}
            onFieldClick={onFieldClick}
          />
        );
      })}
    </div>
  );
}
