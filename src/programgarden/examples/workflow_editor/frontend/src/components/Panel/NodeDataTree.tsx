import { memo, useEffect, useState } from 'react';

// 번역 캐시 (전역)
let translationsCache: Record<string, string> | null = null;
let translationsFetching = false;

interface NodeDataTreeProps {
  nodeId: string;
  nodeLabel: string;
  nodeType?: string;  // 노드 타입 (예: RealOrderEventNode)
  data: unknown;
  onFieldClick: (expression: string) => void;
}

// 노드 데이터 트리 (드래그 가능)
function NodeDataTree({ nodeId, nodeLabel, nodeType, data, onFieldClick }: NodeDataTreeProps) {
  const [translations, setTranslations] = useState<Record<string, string>>(translationsCache || {});

  // 번역 데이터 로드 (한 번만)
  useEffect(() => {
    if (translationsCache) {
      setTranslations(translationsCache);
      return;
    }
    if (translationsFetching) return;
    
    translationsFetching = true;
    fetch('/api/translations?prefix=outputs&locale=ko')
      .then(res => res.json())
      .then(data => {
        translationsCache = data.translations || {};
        setTranslations(translationsCache || {});
      })
      .catch(err => {
        console.error('Failed to fetch translations:', err);
        translationsFetching = false;
      });
  }, []);

  return (
    <div className="bg-gray-700/30 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-gray-300">📦 {nodeLabel}</span>
        <span className="text-xs text-gray-500">({nodeId})</span>
      </div>
      
      <FieldTree
        data={data}
        path={`nodes.${nodeId}`}
        nodeType={nodeType}
        translations={translations}
        onFieldClick={onFieldClick}
      />
    </div>
  );
}

interface FieldTreeProps {
  data: unknown;
  path: string;
  nodeType?: string;
  translations: Record<string, string>;
  onFieldClick: (expression: string) => void;
  depth?: number;
  fieldName?: string;  // 현재 필드 이름 (설명 조회용)
}

// 필드 설명 조회 헬퍼
function getFieldDescription(
  translations: Record<string, string>,
  nodeType: string | undefined,
  fieldName: string
): string | null {
  if (!nodeType || !translations) return null;
  
  // 1. 노드 타입별 키 시도: outputs.RealOrderEventNode.status
  const nodeKey = `outputs.${nodeType}.${fieldName}`;
  if (translations[nodeKey]) {
    return translations[nodeKey];
  }
  
  // 2. 공통 키 시도: outputs.common.status
  const commonKey = `outputs.common.${fieldName}`;
  if (translations[commonKey]) {
    return translations[commonKey];
  }
  
  return null;
}

// 재귀적 필드 트리 렌더링
function FieldTree({ data, path, nodeType, translations, onFieldClick, depth = 0 }: FieldTreeProps) {
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
              nodeType={nodeType}
              translations={translations}
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
      {entries.map(([key, value]) => {
        const description = depth === 0 ? getFieldDescription(translations, nodeType, key) : null;
        const isObject = typeof value === 'object' && value !== null && !Array.isArray(value);
        const isArray = Array.isArray(value);
        
        return (
          <div key={key} className="py-0.5">
            {/* 필드명과 값 (primitive) 또는 필드명만 (object/array) */}
            <div>
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
              {/* primitive 값만 같은 줄에 표시 */}
              {!isObject && !isArray && (
                <FieldTree
                  data={value}
                  path={`${path}.${key}`}
                  nodeType={nodeType}
                  translations={translations}
                  onFieldClick={onFieldClick}
                  depth={depth + 1}
                />
              )}
            </div>
            {/* 필드 설명 표시 (최상위 필드, 필드명 바로 아래) */}
            {description && (
              <div className="text-[10px] text-gray-500 pl-2 mt-0.5 leading-tight">
                💬 {description}
              </div>
            )}
            {/* object/array는 설명 아래에 펼침 */}
            {(isObject || isArray) && (
              <FieldTree
                data={value}
                path={`${path}.${key}`}
                nodeType={nodeType}
                translations={translations}
                onFieldClick={onFieldClick}
                depth={depth + 1}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default memo(NodeDataTree);
