import { memo } from 'react';

interface NodeDataTreeProps {
  nodeId: string;
  nodeLabel: string;
  data: unknown;
  onFieldClick: (expression: string) => void;
}

// 노드 데이터 트리 (드래그 가능)
function NodeDataTree({ nodeId, nodeLabel, data, onFieldClick }: NodeDataTreeProps) {
  return (
    <div className="bg-gray-700/30 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-gray-300">📦 {nodeLabel}</span>
        <span className="text-xs text-gray-500">({nodeId})</span>
      </div>
      
      <FieldTree
        data={data}
        path={`nodes.${nodeId}`}
        onFieldClick={onFieldClick}
      />
    </div>
  );
}

interface FieldTreeProps {
  data: unknown;
  path: string;
  onFieldClick: (expression: string) => void;
  depth?: number;
}

// 재귀적 필드 트리 렌더링
function FieldTree({ data, path, onFieldClick, depth = 0 }: FieldTreeProps) {
  if (data === null || data === undefined) {
    return <span className="text-gray-500 text-xs">null</span>;
  }
  
  // 최대 깊이 제한
  if (depth > 5) {
    return <span className="text-gray-500 text-xs">...</span>;
  }
  
  // Leaf node (primitive value) - 드래그 가능
  if (typeof data !== 'object') {
    const expression = `{{ ${path} }}`;
    const displayValue = typeof data === 'string' 
      ? `"${data.length > 30 ? data.slice(0, 30) + '...' : data}"`
      : String(data);
    
    return (
      <span
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', expression);
          e.dataTransfer.effectAllowed = 'copy';
        }}
        onClick={() => onFieldClick(expression)}
        className="text-green-400 cursor-pointer hover:bg-gray-600 px-1 rounded text-xs font-mono"
        title={`Click or drag: ${expression}`}
      >
        {displayValue}
      </span>
    );
  }
  
  // Array
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="text-gray-500 text-xs">[]</span>;
    }
    
    return (
      <div className="pl-3 border-l border-gray-600">
        {data.slice(0, 5).map((item, index) => (
          <div key={index} className="py-0.5">
            <span
              draggable
              onDragStart={(e) => {
                const expr = `{{ ${path}[${index}] }}`;
                e.dataTransfer.setData('text/plain', expr);
                e.dataTransfer.effectAllowed = 'copy';
              }}
              onClick={() => onFieldClick(`{{ ${path}[${index}] }}`)}
              className="text-purple-400 cursor-pointer hover:underline text-xs"
            >
              [{index}]
            </span>
            <span className="text-gray-500 text-xs">: </span>
            <FieldTree
              data={item}
              path={`${path}[${index}]`}
              onFieldClick={onFieldClick}
              depth={depth + 1}
            />
          </div>
        ))}
        {data.length > 5 && (
          <div className="text-gray-500 text-xs py-0.5">... {data.length - 5} more items</div>
        )}
      </div>
    );
  }
  
  // Object
  const entries = Object.entries(data as Record<string, unknown>);
  if (entries.length === 0) {
    return <span className="text-gray-500 text-xs">{'{}'}</span>;
  }
  
  return (
    <div className="pl-3 border-l border-gray-600">
      {entries.map(([key, value]) => (
        <div key={key} className="py-0.5">
          <span
            draggable
            onDragStart={(e) => {
              const expr = `{{ ${path}.${key} }}`;
              e.dataTransfer.setData('text/plain', expr);
              e.dataTransfer.effectAllowed = 'copy';
            }}
            onClick={() => onFieldClick(`{{ ${path}.${key} }}`)}
            className="text-blue-400 cursor-pointer hover:underline text-xs"
          >
            {key}
          </span>
          <span className="text-gray-500 text-xs">: </span>
          <FieldTree
            data={value}
            path={`${path}.${key}`}
            onFieldClick={onFieldClick}
            depth={depth + 1}
          />
        </div>
      ))}
    </div>
  );
}

export default memo(NodeDataTree);
