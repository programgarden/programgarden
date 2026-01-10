/**
 * DisplayNodeComponent - Inline chart visualization node
 * 
 * Renders charts directly inside the node on the canvas (like Postman)
 */
import { memo } from 'react';
import { Handle, Position, NodeProps, NodeResizer } from '@xyflow/react';
import { useDisplayStore } from '@/stores/displayStore';
import ChartRenderer from './ChartRenderer';
import { getCategoryColor } from '@/utils/nodeColors';
import { NodeState } from '@/types/workflow';

interface DisplayNodeData {
  label?: string;
  nodeType: string;
  category: string;
  state?: NodeState;
  // DisplayNode specific
  chart_type?: string;
  title?: string;
  width?: number;
  height?: number;
  x_label?: string;
  y_label?: string;
  [key: string]: unknown;
}

function getStateStyles(state?: NodeState): string {
  switch (state) {
    case 'running':
      return 'ring-2 ring-blue-500 shadow-lg shadow-blue-500/50';
    case 'completed':
      return 'ring-2 ring-green-500';
    case 'failed':
      return 'ring-2 ring-red-500';
    case 'skipped':
      return 'opacity-50 grayscale';
    default:
      return '';
  }
}

function DisplayNodeComponent({ id, data, selected }: NodeProps) {
  const nodeData = data as DisplayNodeData;
  const displayData = useDisplayStore((s) => s.nodeDisplayData[id]);
  const color = getCategoryColor(nodeData.category);
  const stateStyles = getStateStyles(nodeData.state);
  
  // Default sizes - used for initial node size
  const chartType = nodeData.chart_type || 'line';
  const title = nodeData.title || 'Display';

  return (
    <>
      {/* Resizer for adjusting node size */}
      <NodeResizer
        minWidth={200}
        minHeight={150}
        maxWidth={800}
        maxHeight={600}
        isVisible={selected}
        lineStyle={{ borderColor: color }}
        handleStyle={{ borderColor: color, backgroundColor: '#1f2937' }}
      />
      
      <div
        className={`
          bg-gray-800 rounded-lg shadow-lg overflow-hidden
          border-2 transition-all duration-200
          ${selected ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900' : ''}
          ${stateStyles}
        `}
        style={{ 
          borderColor: color,
          width: '100%',
          height: '100%',
        }}
      >
        {/* Input Handle */}
        <Handle
          type="target"
          position={Position.Left}
          id="data"
          className="!w-3 !h-3 !bg-blue-400 hover:!bg-blue-300 !border-2 !border-gray-600"
          style={{ top: '50%' }}
          title="data (any)"
        />

        {/* Header */}
        <div
          className="px-3 py-1.5 flex items-center justify-between"
          style={{ backgroundColor: color }}
        >
          <span className="text-white text-xs font-semibold truncate">
            📊 {title}
          </span>
          <span className="text-white/70 text-xs">
            {chartType}
          </span>
        </div>

        {/* Chart Area */}
        <div 
          className="p-2 bg-gray-900/50 flex-1"
          style={{ height: 'calc(100% - 32px)' }}
        >
          {displayData?.data ? (
            <ChartRenderer
              type={chartType}
              data={displayData.data}
              xLabel={nodeData.x_label}
              yLabel={nodeData.y_label}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 text-xs gap-2">
              <div className="text-2xl opacity-50">📈</div>
              <div>Run workflow to see chart</div>
            </div>
          )}
        </div>

        {/* Output Handle */}
        <Handle
          type="source"
          position={Position.Right}
          id="rendered"
          className="!w-3 !h-3 !bg-green-400 hover:!bg-green-300 !border-2 !border-gray-600"
          style={{ top: '50%' }}
          title="rendered (signal)"
        />

        {/* State indicator */}
        {nodeData.state && (
          <div className="absolute top-1 right-1 text-xs">
            {nodeData.state === 'running' && '🔄'}
            {nodeData.state === 'completed' && '✅'}
            {nodeData.state === 'failed' && '❌'}
            {nodeData.state === 'skipped' && '⏭️'}
          </div>
        )}
      </div>
    </>
  );
}

export default memo(DisplayNodeComponent);
