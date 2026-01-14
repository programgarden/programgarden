import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { getCategoryColor } from '@/utils/nodeColors';
import { getNodeLabel } from '@/utils/nodeLabels';
import { PortDefinition, NodeState } from '@/types/workflow';

interface CustomNodeData {
  label: string;
  nodeType: string;
  category: string;
  description?: string; // 노드 설명 (편집 가능)
  inputs?: PortDefinition[];
  outputs?: PortDefinition[];
  state?: NodeState;
  lastOutput?: unknown; // 마지막 실행 출력값 (프리뷰용)
  [key: string]: unknown;
}

// 노드 아이콘 URL 가져오기
function getNodeIconUrl(nodeType: string): string | null {
  const iconUrls: Record<string, string> = {
    // TelegramNode - 사용자 지정 아이콘
    TelegramNode: 'https://i.namu.wiki/i/WB0c5rSBD3_LUdsinRiemDrRTepFImNUJr-K4mWBvITAmyXksxKMsA6Bohk388FJQyjdQw0Vbs_XQ8CXv_mg-w.svg',
    // 샘플 아이콘 (simpleicons.org 등에서 가져온 SVG들)
    StartNode: 'https://cdn.simpleicons.org/playwright/45ba4b',
    BrokerNode: 'https://cdn.simpleicons.org/socket.io/ffffff',
    ConditionNode: 'https://cdn.simpleicons.org/git/f05032',
    NewOrderNode: 'https://cdn.simpleicons.org/googledocs/4285f4',
    AlertNode: 'https://cdn.simpleicons.org/googlemessages/4285f4',
    ScheduleNode: 'https://cdn.simpleicons.org/clockify/03a9f4',
    DisplayNode: 'https://cdn.simpleicons.org/grafana/f46800',
    WatchlistNode: 'https://cdn.simpleicons.org/openlayers/1f6b75',
    ScreenerNode: 'https://cdn.simpleicons.org/elasticsearch/005571',
    HistoricalDataNode: 'https://cdn.simpleicons.org/googleanalytics/e37400',
    RealMarketDataNode: 'https://cdn.simpleicons.org/mqtt/660066',
    PositionSizingNode: 'https://cdn.simpleicons.org/googlefit/4285f4',
    RiskGuardNode: 'https://cdn.simpleicons.org/bitwarden/175ddc',
    LiquidateNode: 'https://cdn.simpleicons.org/cashapp/00c853',
    LogicNode: 'https://cdn.simpleicons.org/probot/00b0d8',
    GroupNode: 'https://cdn.simpleicons.org/diagramsdotnet/f08705',
    BacktestEngineNode: 'https://cdn.simpleicons.org/testcafe/36b6e5',
    EventHandlerNode: 'https://cdn.simpleicons.org/amazonaws/ff9900',
    CustomPnLNode: 'https://cdn.simpleicons.org/googlesheets/34a853',
    DeployNode: 'https://cdn.simpleicons.org/docker/2496ed',
    AccountNode: 'https://cdn.simpleicons.org/stripe/635bff',
  };
  return iconUrls[nodeType] || null;
}

// 폴백용 이모지 아이콘
function getNodeEmojiIcon(nodeType: string): string {
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
    TelegramNode: '📨',
    AccountNode: '👤',
  };
  return icons[nodeType] || '📦';
}

// 노드 아이콘 컴포넌트
function NodeIcon({ nodeType }: { nodeType: string }) {
  const [imgError, setImgError] = useState(false);
  const iconUrl = getNodeIconUrl(nodeType);
  
  if (iconUrl && !imgError) {
    return (
      <img 
        src={iconUrl} 
        alt={nodeType}
        className="w-5 h-5 object-contain"
        onError={() => setImgError(true)}
      />
    );
  }
  
  return <span>{getNodeEmojiIcon(nodeType)}</span>;
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
      // 빛나는 테두리 (반짝임 제거)
      return 'ring-2 ring-blue-500 shadow-lg shadow-blue-500/50';
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

function CustomNode({ data, selected, id }: NodeProps) {
  const nodeData = data as CustomNodeData;
  const color = getCategoryColor(nodeData.category);
  const stateStyles = getStateStyles(nodeData.state);
  
  // 노드 이름 편집 상태
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const defaultLabel = getNodeLabel(nodeData.nodeType, 'ko');
  const [editedLabel, setEditedLabel] = useState<string>((nodeData.customLabel as string) || defaultLabel);
  
  // 설명 편집 상태
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [editedDescription, setEditedDescription] = useState(nodeData.description || '');
  
  // 출력 프리뷰 생성
  const outputPreview = nodeData.lastOutput 
    ? getOutputPreview(nodeData.lastOutput) 
    : null;
  
  // 노드 이름 저장 핸들러
  const handleLabelSave = () => {
    setIsEditingLabel(false);
    const event = new CustomEvent('updateNodeLabel', {
      detail: { nodeId: id, customLabel: editedLabel || defaultLabel }
    });
    window.dispatchEvent(event);
  };
  
  // 설명 저장 핸들러
  const handleDescriptionSave = () => {
    setIsEditingDescription(false);
    // workflowStore의 updateNodeData를 통해 저장
    const event = new CustomEvent('updateNodeDescription', {
      detail: { nodeId: id, description: editedDescription }
    });
    window.dispatchEvent(event);
  };
  
  // 표시할 라벨 (커스텀 라벨 > 기본 한글 라벨)
  const displayLabel = (nodeData.customLabel as string) || defaultLabel;

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

      {/* Header - 노드 이름 (더블클릭으로 편집) */}
      <div
        className="px-3 py-2 text-white text-sm font-medium flex items-center gap-2 cursor-text"
        style={{ backgroundColor: color }}
        onDoubleClick={() => {
          setIsEditingLabel(true);
          setEditedLabel(displayLabel);
        }}
      >
        {/* 실행 중일 때 회전 아이콘, 아니면 노드 아이콘 */}
        {nodeData.state === 'running' ? (
          <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" opacity="0.3"/>
            <path d="M12 4a8 8 0 018 8h4c0-6.627-5.373-12-12-12v4z" fill="currentColor"/>
          </svg>
        ) : (
          <NodeIcon nodeType={nodeData.nodeType} />
        )}
        {isEditingLabel ? (
          <input
            type="text"
            className="flex-1 bg-white/20 text-white text-sm px-1 py-0.5 rounded border border-white/30 focus:border-white focus:outline-none"
            value={editedLabel}
            onChange={(e) => setEditedLabel(e.target.value)}
            onBlur={handleLabelSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleLabelSave();
              if (e.key === 'Escape') {
                setIsEditingLabel(false);
                setEditedLabel(displayLabel);
              }
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span title="더블클릭하여 이름 변경">{displayLabel}</span>
        )}
      </div>

      {/* Node ID 표시 */}
      <div className="px-3 py-1 bg-gray-900/50 border-b border-gray-700">
        <span className="text-[10px] font-mono text-gray-500 select-all" title="Node ID">
          #{id}
        </span>
      </div>

      {/* Body - 설명 (더블클릭으로 편집) */}
      <div 
        className="px-3 py-2 text-gray-300 text-xs min-h-[32px] cursor-text hover:bg-gray-700/50 transition-colors"
        onDoubleClick={() => {
          setIsEditingDescription(true);
          setEditedDescription(nodeData.description || '');
        }}
      >
        {isEditingDescription ? (
          <input
            type="text"
            className="w-full bg-gray-700 text-white text-xs px-1 py-0.5 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            value={editedDescription}
            onChange={(e) => setEditedDescription(e.target.value)}
            onBlur={handleDescriptionSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleDescriptionSave();
              if (e.key === 'Escape') setIsEditingDescription(false);
            }}
            autoFocus
            placeholder="설명을 입력하세요..."
          />
        ) : (
          <span className="text-gray-400">
            {nodeData.description || '더블클릭하여 설명 추가'}
          </span>
        )}
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
