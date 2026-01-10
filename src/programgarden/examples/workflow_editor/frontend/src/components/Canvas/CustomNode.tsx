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
  lastOutput?: unknown; // 마지막 실행 출력값 (프리뷰용)
  [key: string]: unknown;
}

// 노드 아이콘 가져오기
function getNodeIcon(nodeType: string): string {
  const icons: Record<string, string> = {
    StartNode: '▶️',
    BrokerNode: '🔌',
    ConditionNode: '🔀',
    NewOrderNode: '📝',
    AlertNode: '🔔',
    ScheduleNode: '⏰',
    DisplayNode: '📊',
    WatchlistNode: '👀',
    ScreenerNode: '🔍',
    HistoricalDataNode: '📈',
    RealMarketDataNode: '📡',
    PositionSizingNode: '⚖️',
    RiskGuardNode: '🛡️',
    LiquidateNode: '💰',
    LogicNode: '🧠',
    GroupNode: '📦',
    BacktestEngineNode: '🔬',
    EventHandlerNode: '⚡',
    CustomPnLNode: '💹',
    DeployNode: '🚀',
  };
  return icons[nodeType] || '📦';
}

// 출력 프리뷰 생성 (n8n 스타일)
function getOutputPreview(output: unknown): string | null {
  if (!output) return null;
  if (Array.isArray(output)) return `✅ ${output.length} items`;
  if (typeof output === 'object' && output !== null) {
    const keys = Object.keys(output);
    return `✅ ${keys.length} fields`;
  }
  return `✅ ${String(output).slice(0, 20)}`;
}

function getStateStyles(state?: NodeState): string {
  switch (state) {
    case 'running':
      // 펄스 애니메이션 + 빛나는 테두리
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
  const stateStyles = getStateStyles(nodeData.state);
  
  // 출력 프리뷰 생성
  const outputPreview = nodeData.lastOutput 
    ? getOutputPreview(nodeData.lastOutput) 
    : null;

  return (
    <div
      className={`
        bg-gray-800 rounded-lg shadow-lg min-w-[160px] overflow-hidden
        border-2 transition-all duration-200
        ${selected ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900' : ''}
        ${stateStyles}
      `}
      style={{ borderColor: color }}
    >
      {/* 단일 Input Handle (StartNode 제외) */}
      {nodeData.nodeType !== 'StartNode' && (
        <Handle
          type="target"
          position={Position.Left}
          id="input"
          className="!w-3 !h-3 !bg-gray-400 hover:!bg-blue-400 !border-2 !border-gray-700"
          style={{ top: '50%' }}
        />
      )}

      {/* Header */}
      <div
        className="px-3 py-2 text-white text-sm font-medium flex items-center gap-2"
        style={{ backgroundColor: color }}
      >
        <span>{getNodeIcon(nodeData.nodeType)}</span>
        <span>{nodeData.label || nodeData.nodeType}</span>
      </div>

      {/* Body */}
      <div className="px-3 py-2 text-gray-400 text-xs">
        {nodeData.nodeType}
      </div>

      {/* Output Preview (n8n 스타일) */}
      {outputPreview && (
        <div className="px-3 py-1.5 bg-gray-700/50 text-xs text-green-400 border-t border-gray-700">
          {outputPreview}
        </div>
      )}

      {/* 단일 Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!w-3 !h-3 !bg-gray-400 hover:!bg-green-400 !border-2 !border-gray-700"
        style={{ top: '50%' }}
      />
    </div>
  );
}

export default memo(CustomNode);
