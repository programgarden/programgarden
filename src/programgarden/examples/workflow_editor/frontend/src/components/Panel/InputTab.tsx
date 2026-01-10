import { Node } from '@xyflow/react';
import NodeDataTree from './NodeDataTree';

interface InputTabProps {
  inputData: Record<string, unknown>;
  upstreamNodes: Node[];
  onFieldClick: (expression: string) => void;
}

export default function InputTab({ inputData, upstreamNodes, onFieldClick }: InputTabProps) {
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
      <p className="text-xs text-gray-400">
        💡 Drag fields to Settings tab, or click to copy expression
      </p>

      {upstreamNodes.map((node) => {
        const nodeData = inputData[node.id];
        if (!nodeData) return null;

        const nodeLabel = (node.data as Record<string, unknown>).label as string 
          || (node.data as Record<string, unknown>).nodeType as string;

        return (
          <NodeDataTree
            key={node.id}
            nodeId={node.id}
            nodeLabel={nodeLabel}
            data={nodeData}
            onFieldClick={onFieldClick}
          />
        );
      })}
    </div>
  );
}
