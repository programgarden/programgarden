import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { getCategoryColor } from '@/utils/nodeColors';
import { PortDefinition, NodeState } from '@/types/workflow';

interface CustomNodeData {
  label: string;
  nodeType: string;
  category: string;
  inputs?: PortDefinition[];
  outputs?: PortDefinition[];
  state?: NodeState;
  [key: string]: unknown;
}

function getStateStyles(state?: NodeState): string {
  switch (state) {
    case 'running':
      // 펌스 애니메이션 + 빛나는 테두리
      return 'animate-pulse ring-2 ring-blue-500 shadow-lg shadow-blue-500/50';
    case 'completed':
      return 'ring-2 ring-green-500 bg-green-900/20';
    case 'failed':
      return 'ring-2 ring-red-500 bg-red-900/20';
    case 'skipped':
      return 'opacity-50 grayscale';
    case 'pending':
    default:
      return '';
  }
}

function CustomNode({ data, selected }: NodeProps) {
  const nodeData = data as CustomNodeData;
  const color = getCategoryColor(nodeData.category);
  const inputs = nodeData.inputs || [];
  const outputs = nodeData.outputs || [];
  const stateStyles = getStateStyles(nodeData.state);

  // Calculate handle positions - ensure at least one input and output handle
  const hasInputs = inputs.length > 0;
  const hasOutputs = outputs.length > 0;

  return (
    <div
      className={`
        bg-gray-800 rounded-lg shadow-lg min-w-[140px] overflow-hidden
        border-2 transition-all duration-200
        ${selected ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900' : ''}
        ${stateStyles}
      `}
      style={{ borderColor: color }}
    >
      {/* Default Input Handle (if no inputs defined) */}
      {!hasInputs && (
        <Handle
          type="target"
          position={Position.Left}
          id="input"
          className="!w-3 !h-3 !bg-blue-400 hover:!bg-blue-300 !border-2 !border-gray-600"
          style={{ top: '50%' }}
          title="Input"
        />
      )}

      {/* Input Handles */}
      {inputs.map((input, i) => (
        <Handle
          key={input.name}
          type="target"
          position={Position.Left}
          id={input.name}
          className="!w-3 !h-3 !bg-blue-400 hover:!bg-blue-300 !border-2 !border-gray-600"
          style={{ top: `${20 + i * 20}px` }}
          title={`${input.name} (${input.type})`}
        />
      ))}

      {/* Header */}
      <div
        className="px-3 py-1.5 text-white text-xs font-semibold"
        style={{ backgroundColor: color }}
      >
        {nodeData.label || nodeData.nodeType}
      </div>

      {/* Body */}
      <div className="px-3 py-2 text-gray-300 text-xs">
        <div className="text-gray-500">{nodeData.nodeType}</div>
        {nodeData.state && (
          <div className="mt-1 text-xs capitalize">
            {nodeData.state === 'running' && '🔄 '}
            {nodeData.state === 'completed' && '✅ '}
            {nodeData.state === 'failed' && '❌ '}
            {nodeData.state === 'skipped' && '⏭️ '}
            {nodeData.state}
          </div>
        )}
      </div>

      {/* Default Output Handle (if no outputs defined) */}
      {!hasOutputs && (
        <Handle
          type="source"
          position={Position.Right}
          id="output"
          className="!w-3 !h-3 !bg-green-400 hover:!bg-green-300 !border-2 !border-gray-600"
          style={{ top: '50%' }}
          title="Output"
        />
      )}

      {/* Output Handles */}
      {outputs.map((output, i) => (
        <Handle
          key={output.name}
          type="source"
          position={Position.Right}
          id={output.name}
          className="!w-3 !h-3 !bg-green-400 hover:!bg-green-300 !border-2 !border-gray-600"
          style={{ top: `${20 + i * 20}px` }}
          title={`${output.name} (${output.type})`}
        />
      ))}
    </div>
  );
}

export default memo(CustomNode);
