import { useState, useRef } from 'react';
import { Node } from '@xyflow/react';
import { ConfigField, Credential, CredentialTypeSchema } from '@/types/workflow';
import { Plus, X, Lock, Key } from 'lucide-react';
import SymbolEditor from './SymbolEditor';
import { findAutoBindingSource, getRequiredNodeTypesForPort, AutoBindingResult } from '@/utils/graphUtils';

// 민감한 헤더 키 목록 (대소문자 무시)
const SENSITIVE_HEADER_KEYS = [
  'authorization',
  'x-api-key',
  'api-key',
  'apikey',
  'x-auth-token',
  'x-access-token',
  'bearer',
  'token',
  'secret',
  'password',
  'credential',
  'private-key',
  'x-secret',
];

const isSensitiveKey = (key: string): boolean => {
  const lowerKey = key.toLowerCase();
  return SENSITIVE_HEADER_KEYS.some(sensitive => 
    lowerKey.includes(sensitive)
  );
};

interface BindableFieldProps {
  label: string;
  fieldKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
  onFocus?: () => void;
  schema?: ConfigField;
  // Credential 관련 props (credential_id 필드용)
  credentials?: Credential[];
  credentialTypes?: CredentialTypeSchema[];
  onOpenCredentialModal?: (initialType?: string) => void;
  credentialLoading?: boolean;
  requiredCredentialType?: string;
  // WatchlistNode 관련 (symbol_editor용)
  nodeData?: Record<string, unknown>;
  onNodeDataChange?: (key: string, value: unknown) => void;
  // Plugin 관련 props (plugin 필드용)
  availablePlugins?: string[];
  onPluginChange?: (pluginId: string) => void;
  // Port Binding 자동 연결 확인용
  upstreamNodes?: Node[];
}

export default function BindableField({ 
  label, 
  fieldKey,
  value, 
  onChange, 
  onFocus,
  schema,
  credentials,
  credentialTypes,
  onOpenCredentialModal,
  credentialLoading,
  requiredCredentialType,
  nodeData,
  onNodeDataChange,
  availablePlugins,
  onPluginChange,
  upstreamNodes,
}: BindableFieldProps) {
  const [isExpression, setIsExpression] = useState(() => {
    return typeof value === 'string' && value.startsWith('{{');
  });
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  
  // Credential field인지 확인 (fieldKey가 credential_id이거나 schema.type이 credential)
  const isCredentialField = fieldKey === 'credential_id' || schema?.type === 'credential';
  
  // Plugin field인지 확인 (fieldKey가 plugin)
  const isPluginField = fieldKey === 'plugin';
  
  // Port binding field인지 확인 (ui_hint가 port_binding:*로 시작)
  const isPortBindingField = schema?.ui_hint?.startsWith('port_binding:');
  const portBindingType = isPortBindingField ? schema?.ui_hint?.split(':')[1] : null;
  
  // 드롭 핸들러
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const expression = e.dataTransfer.getData('text/plain');
    if (expression && expression.startsWith('{{')) {
      onChange(expression);
      setIsExpression(true);
    }
  };
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };
  
  // Expression 모드 토글
  const toggleExpression = () => {
    setIsExpression(!isExpression);
    if (!isExpression) {
      // 일반 → Expression: 기존 값을 그대로 유지
    } else {
      // Expression → 일반: {{ }} 문법이면 빈 값으로
      if (typeof value === 'string' && value.startsWith('{{')) {
        onChange('');
      }
    }
  };

  // 드롭 영역 스타일
  const dropZoneClass = isDragOver 
    ? 'ring-2 ring-orange-500 ring-offset-1 ring-offset-gray-800' 
    : '';
  
  // Credential 타입 (credential_id 필드)
  if (isCredentialField) {
    // 필터링된 credentials (특정 타입만 필터링 가능)
    const filteredCredentials = requiredCredentialType && credentials
      ? credentials.filter((c) => c.credential_type === requiredCredentialType)
      : credentials || [];
    
    // 모든 credential 타입 또는 특정 타입만
    const availableTypes = requiredCredentialType && credentialTypes
      ? credentialTypes.filter(t => t.type_id === requiredCredentialType)
      : credentialTypes || [];

    return (
      <div>
        <label className="block text-xs text-gray-400 mb-1 capitalize">
          <span className="flex items-center gap-1">
            <Key className="w-3 h-3" />
            {label}
          </span>
          {schema?.required && <span className="text-red-400 ml-1">*</span>}
        </label>
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <div className="flex gap-2">
          <select
            value={String(value || '')}
            onChange={(e) => onChange(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            disabled={credentialLoading}
          >
            <option value="">Select credential...</option>
            {filteredCredentials.map(cred => {
              // credential 타입에 맞는 아이콘/이름 찾기
              const typeInfo = credentialTypes?.find(t => t.type_id === cred.credential_type);
              return (
                <option key={cred.id} value={cred.id}>
                  {typeInfo?.icon || '🔑'} {cred.name}
                </option>
              );
            })}
          </select>
          {onOpenCredentialModal && (
            <button
              onClick={() => onOpenCredentialModal(requiredCredentialType)}
              className="px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1 transition-colors"
              title="Add new credential"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>
        {filteredCredentials.length === 0 && !credentialLoading && (
          <p className="text-xs text-amber-500/70 mt-1.5 flex items-center gap-1">
            <span>⚠️</span>
            No credentials found. 
            {onOpenCredentialModal && (
              <button 
                onClick={() => onOpenCredentialModal(requiredCredentialType)}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                Add one
              </button>
            )}
          </p>
        )}
        {availableTypes.length > 0 && !requiredCredentialType && (
          <p className="text-xs text-gray-500 mt-1">
            Supported: {availableTypes.map(t => t.name).join(', ')}
          </p>
        )}
      </div>
    );
  }
  
  // Plugin 타입 (드롭다운)
  if (isPluginField && availablePlugins && availablePlugins.length > 0) {
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">
            <span className="flex items-center gap-1">
              🔌 {label}
            </span>
          </label>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </div>
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <select
          value={String(value || '')}
          onChange={(e) => {
            if (onPluginChange) {
              onPluginChange(e.target.value);
            } else {
              onChange(e.target.value);
            }
          }}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
        >
          <option value="">Select plugin...</option>
          {availablePlugins.map(pluginId => (
            <option key={pluginId} value={pluginId}>
              {pluginId}
            </option>
          ))}
        </select>
        {!value && (
          <p className="text-xs text-amber-500/70 mt-1.5">
            💡 Select a plugin to configure its parameters
          </p>
        )}
      </div>
    );
  }
  
  // Port Binding 필드 (ui_hint가 port_binding:* 인 경우)
  // 자동 바인딩이 백엔드에서 처리되므로, 비어있으면 자동으로 연결됨
  if (isPortBindingField) {
    // 포트 타입별 설정 (아이콘, 색상, 예시 필드명, JSON 직접 입력 예시)
    const portTypeConfig: Record<string, { 
      icon: string; 
      color: string; 
      exampleField: string;
      jsonExample: string;
      jsonDescription: string;
    }> = {
      'market_data': { 
        icon: '📈', 
        color: 'emerald', 
        exampleField: 'ohlcv',
        jsonExample: '[{"open":100,"high":105,"low":99,"close":102,"volume":1000}]',
        jsonDescription: 'OHLCV 배열',
      },
      'price_data': { 
        icon: '📈', 
        color: 'emerald', 
        exampleField: 'price',
        jsonExample: '[{"symbol":"AAPL","price":185.5},{"symbol":"NVDA","price":450.2}]',
        jsonDescription: '종목별 가격 배열',
      },
      'volume_data': { 
        icon: '📊', 
        color: 'emerald', 
        exampleField: 'volume',
        jsonExample: '[{"symbol":"AAPL","volume":15000000}]',
        jsonDescription: '종목별 거래량 배열',
      },
      'symbol_list': { 
        icon: '🎯', 
        color: 'cyan', 
        exampleField: 'symbols',
        jsonExample: '["AAPL","NVDA","TSLA"]',
        jsonDescription: '종목코드 문자열 배열',
      },
      'symbols': { 
        icon: '🎯', 
        color: 'cyan', 
        exampleField: 'symbols',
        jsonExample: '["AAPL","NVDA","TSLA"]',
        jsonDescription: '종목코드 문자열 배열',
      },
      'position_data': { 
        icon: '📋', 
        color: 'purple', 
        exampleField: 'positions',
        jsonExample: '[{"symbol":"AAPL","qty":10,"avg_price":150.5,"pnl_rate":5.2}]',
        jsonDescription: '포지션 객체 배열',
      },
      'held_symbols': { 
        icon: '🎯', 
        color: 'purple', 
        exampleField: 'held_symbols',
        jsonExample: '["AAPL","GOOGL"]',
        jsonDescription: '보유 종목코드 배열',
      },
      'order_list': { 
        icon: '📝', 
        color: 'orange', 
        exampleField: 'active_orders',
        jsonExample: '[{"order_id":"123","symbol":"AAPL","side":"buy","qty":10}]',
        jsonDescription: '주문 객체 배열',
      },
      'quantity': { 
        icon: '🔢', 
        color: 'indigo', 
        exampleField: 'quantity',
        jsonExample: '100',
        jsonDescription: '정수 또는 소수',
      },
      'balance': { 
        icon: '💰', 
        color: 'yellow', 
        exampleField: 'balance',
        jsonExample: '1000000',
        jsonDescription: '잔고 금액 (숫자)',
      },
    };
    
    const typeKey = portBindingType || 'default';
    const config = portTypeConfig[typeKey] || { 
      icon: '🔗', 
      color: 'gray', 
      exampleField: label.toLowerCase().replace(/ /g, '_'),
      jsonExample: '{"key": "value"}',
      jsonDescription: 'JSON 데이터',
    };
    
    const colorClasses: Record<string, string> = {
      emerald: 'border-emerald-600 bg-emerald-900/20 text-emerald-300 focus:ring-emerald-500',
      blue: 'border-blue-600 bg-blue-900/20 text-blue-300 focus:ring-blue-500',
      cyan: 'border-cyan-600 bg-cyan-900/20 text-cyan-300 focus:ring-cyan-500',
      violet: 'border-violet-600 bg-violet-900/20 text-violet-300 focus:ring-violet-500',
      purple: 'border-purple-600 bg-purple-900/20 text-purple-300 focus:ring-purple-500',
      orange: 'border-orange-600 bg-orange-900/20 text-orange-300 focus:ring-orange-500',
      indigo: 'border-indigo-600 bg-indigo-900/20 text-indigo-300 focus:ring-indigo-500',
      yellow: 'border-yellow-600 bg-yellow-900/20 text-yellow-300 focus:ring-yellow-500',
      gray: 'border-gray-600 bg-gray-900/20 text-gray-300 focus:ring-gray-500',
    };
    
    // 값이 비어있으면 자동 바인딩 상태
    const isEmpty = !value || (typeof value === 'string' && value.trim() === '');
    
    // upstream 노드에서 자동 바인딩 소스 찾기
    const autoBindingResult: AutoBindingResult = upstreamNodes && portBindingType
      ? findAutoBindingSource(portBindingType, upstreamNodes)
      : { available: false };
    
    // 상태 결정: 값 있음 / 자동 바인딩 가능 / 연결 필요
    const bindingStatus = !isEmpty 
      ? 'bound'  // 사용자가 직접 값을 입력함
      : autoBindingResult.available 
        ? 'auto'  // 자동 바인딩 가능
        : 'missing';  // 연결 필요
    
    // 연결 필요 시 필요한 노드 타입 안내
    const requiredNodeTypes = portBindingType 
      ? getRequiredNodeTypesForPort(portBindingType) 
      : '';
    
    // placeholder: 실제 사용 가능한 표현식 예시
    const placeholderExpression = autoBindingResult.available && autoBindingResult.expression
      ? autoBindingResult.expression
      : `{{ nodes.노드ID.${config.exampleField} }}`;

    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">
            <span className="flex items-center gap-1">
              {config.icon} {label}
            </span>
          </label>
          <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${
            bindingStatus === 'auto'
              ? 'bg-green-900/50 text-green-400 border border-green-700'
              : bindingStatus === 'missing'
                ? 'bg-amber-900/50 text-amber-400 border border-amber-700'
                : 'bg-blue-900/50 text-blue-400 border border-blue-700'
          }`}>
            {bindingStatus === 'auto' 
              ? '✨ auto' 
              : bindingStatus === 'missing' 
                ? '⚠️ 연결 필요' 
                : '✏️ 직접 입력'}
          </span>
        </div>
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="text"
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          placeholder={placeholderExpression}
          className={`w-full px-3 py-1.5 rounded text-sm font-mono focus:outline-none focus:ring-1 transition-colors ${
            bindingStatus === 'auto'
              ? 'border border-green-700/50 bg-green-900/10 text-green-400 placeholder:text-green-600/70' 
              : bindingStatus === 'missing'
                ? 'border border-amber-700/50 bg-amber-900/10 text-amber-400 placeholder:text-amber-600/70'
                : colorClasses[config.color]
          }`}
        />
        
        {/* 상태별 안내 메시지 */}
        <div className="mt-2 text-xs space-y-1.5">
          {bindingStatus === 'auto' && autoBindingResult.sourceNode && (
            <>
              <p className="text-green-400 flex items-center gap-1">
                <span>✅</span>
                <span>
                  자동 연결: <code className="bg-gray-700 px-1 rounded">{autoBindingResult.sourceNode.id}</code> → 
                  <code className="bg-gray-700 px-1 ml-1 rounded">{autoBindingResult.sourceField}</code>
                </span>
              </p>
              <div className="p-2 bg-gray-800/50 rounded border border-gray-700">
                <p className="text-gray-400 mb-1">💡 직접 입력 옵션:</p>
                <p className="text-gray-500 ml-3">• 표현식: <code className="bg-gray-700 px-1 rounded text-cyan-400">{placeholderExpression}</code></p>
                <p className="text-gray-500 ml-3">• JSON ({config.jsonDescription}): <code className="bg-gray-700 px-1 rounded text-yellow-400 break-all">{config.jsonExample}</code></p>
              </div>
            </>
          )}
          
          {bindingStatus === 'missing' && (
            <>
              <p className="text-amber-400 flex items-center gap-1">
                <span>⚠️</span>
                <span>자동 바인딩 가능 노드: <strong>{requiredNodeTypes}</strong></span>
              </p>
              <div className="p-2 bg-gray-800/50 rounded border border-gray-700">
                <p className="text-gray-400 mb-1">💡 입력 방법:</p>
                <p className="text-gray-500 ml-3">1. 위 노드 연결 → 자동 바인딩</p>
                <p className="text-gray-500 ml-3">2. 표현식: <code className="bg-gray-700 px-1 rounded text-cyan-400">{`{{ nodes.노드ID.${config.exampleField} }}`}</code></p>
                <p className="text-gray-500 ml-3">3. JSON 직접 입력 ({config.jsonDescription}):</p>
                <p className="text-gray-500 ml-6"><code className="bg-gray-700 px-1 rounded text-yellow-400 break-all">{config.jsonExample}</code></p>
              </div>
            </>
          )}
          
          {bindingStatus === 'bound' && (
            <>
              <p className="text-blue-400 flex items-center gap-1">
                <span>✏️</span>
                <span>직접 입력됨. 비우면 자동 바인딩으로 전환됩니다.</span>
              </p>
              <p className="text-gray-500">
                기대 형식 ({config.jsonDescription}): <code className="bg-gray-700 px-1 rounded text-yellow-400">{config.jsonExample}</code>
              </p>
            </>
          )}
        </div>
      </div>
    );
  }
  
  // Boolean 타입
  if (schema?.type === 'boolean') {
    return (
      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <span className="text-sm text-gray-300">{label}</span>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </label>
        {/* Field Description */}
        {schema?.description && (
          <p className="text-xs text-gray-500 mt-1 ml-6">{schema.description}</p>
        )}
      </div>
    );
  }
  
  // ENUM 타입 (드롭다운)
  if (schema?.type === 'enum' && schema?.enum_values && schema.enum_values.length > 0) {
    // 한글 라벨 매핑
    const enumLabels: Record<string, string> = {
      'overseas_stock': '해외주식',
      'overseas_futures': '해외선물',
      'domestic_stock': '국내주식',
      'domestic_futures': '국내선물',
    };
    
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </div>
        {/* Field Description */}
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <select
          value={String(value ?? schema.default ?? '')}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
        >
          {schema.enum_values.map((enumValue) => (
            <option key={enumValue} value={enumValue}>
              {enumLabels[enumValue] || enumValue}
            </option>
          ))}
        </select>
      </div>
    );
  }
  
  // Number 타입
  if (schema?.type === 'number' || schema?.type === 'integer') {
    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          <div className="flex items-center gap-1">
            {schema?.required && <span className="text-red-400 text-xs">*</span>}
            <button
              onClick={toggleExpression}
              className={`px-1.5 py-0.5 text-xs rounded font-mono transition-colors ${
                isExpression 
                  ? 'bg-orange-600 text-white' 
                  : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
              }`}
              title="Toggle expression mode"
            >
              fx
            </button>
          </div>
        </div>
        
        {/* Field Description */}
        {schema?.description && !isExpression && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        
        {isExpression ? (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value)}
            onFocus={onFocus}
            className="w-full px-3 py-1.5 rounded text-sm focus:outline-none focus:ring-1 bg-orange-900/30 border border-orange-600 text-orange-300 font-mono focus:ring-orange-500"
            placeholder="{{ nodes.nodeId.field }}"
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="number"
            value={typeof value === 'number' ? value : 0}
            step={schema?.type === 'integer' ? 1 : 0.01}
            onChange={(e) => {
              const num = schema?.type === 'integer' 
                ? parseInt(e.target.value) || 0 
                : parseFloat(e.target.value) || 0;
              onChange(num);
            }}
            onFocus={onFocus}
            className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
        )}
        
        {isExpression && (
          <p className="text-xs text-orange-400/70 mt-1">
            💡 Drag from Input tab or type expression
          </p>
        )}
      </div>
    );
  }
  
  // Symbol Editor (WatchlistNode용)
  if (schema?.ui_component === 'symbol_editor') {
    // nodeData에서 product 정보 추출 (BrokerNode 연동 시)
    const product = nodeData?.product as string | undefined;
    
    return (
      <div>
        <label className="block text-xs text-gray-400 mb-2 capitalize">{label}</label>
        <SymbolEditor
          value={(value as Array<{exchange: string; symbol: string}>) || []}
          onChange={(newValue) => onChange(newValue)}
          product={product}
          onProductChange={onNodeDataChange ? (p) => onNodeDataChange('product', p) : undefined}
        />
      </div>
    );
  }
  
  // Array/Object 타입 - JSON 에디터 또는 표현식
  if (schema?.type === 'array' || schema?.type === 'object') {
    // 표현식인지 확인
    const isExpr = typeof value === 'string' && value.startsWith('{{');
    const displayValue = isExpr 
      ? value 
      : (typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value || '[]'));
    
    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </div>
        {/* Field Description */}
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          defaultValue={displayValue}
          rows={3}
          onBlur={(e) => {
            const val = e.target.value.trim();
            // 표현식이면 그대로 저장
            if (val.startsWith('{{')) {
              onChange(val);
              return;
            }
            // JSON 파싱 시도
            try {
              const parsed = JSON.parse(val);
              onChange(parsed);
            } catch {
              // 파싱 실패시 문자열로 저장
              onChange(val);
            }
          }}
          onClick={onFocus}
          onFocus={onFocus}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500 font-mono"
        />
      </div>
    );
  }

  // Key-Value Pairs 타입 (headers 등)
  if (schema?.type === 'key_value_pairs') {
    const pairs = (value as Record<string, string>) || {};
    const entries = Object.entries(pairs);
    const [showCredentialPicker, setShowCredentialPicker] = useState<number | null>(null);
    
    const addPair = () => {
      onChange({ ...pairs, '': '' });
    };
    
    // Credential에서 값을 가져와서 삽입
    const insertCredentialValue = (index: number, credentialId: string, fieldKey: string) => {
      const entriesArr = Object.entries(pairs);
      if (entriesArr[index]) {
        const [key] = entriesArr[index];
        // {{ credential.credentialId.fieldKey }} 형식으로 삽입
        const expression = `{{ credential.${credentialId}.${fieldKey} }}`;
        onChange({ ...pairs, [key]: expression });
      }
      setShowCredentialPicker(null);
    };
    
    const updateKey = (oldKey: string, newKey: string) => {
      const newPairs: Record<string, string> = {};
      for (const [k, v] of Object.entries(pairs)) {
        if (k === oldKey) {
          newPairs[newKey] = v;
        } else {
          newPairs[k] = v;
        }
      }
      onChange(newPairs);
    };
    
    const updateValue = (key: string, newValue: string) => {
      onChange({ ...pairs, [key]: newValue });
    };
    
    const removePair = (key: string) => {
      const newPairs = { ...pairs };
      delete newPairs[key];
      onChange(newPairs);
    };
    
    // Credential picker 팝업
    const CredentialPicker = ({ index }: { index: number }) => {
      if (!credentials || credentials.length === 0) {
        return (
          <div className="absolute right-0 top-full mt-1 z-20 bg-gray-800 border border-gray-600 rounded-lg shadow-xl p-3 min-w-[200px]">
            <p className="text-xs text-gray-400 mb-2">No credentials available</p>
            {onOpenCredentialModal && (
              <button
                onClick={() => {
                  setShowCredentialPicker(null);
                  onOpenCredentialModal();
                }}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
              >
                <Plus className="w-3 h-3" />
                Add Credential
              </button>
            )}
          </div>
        );
      }
      
      return (
        <div className="absolute right-0 top-full mt-1 z-20 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-[300px] overflow-y-auto min-w-[250px]">
          <div className="p-2 border-b border-gray-700">
            <p className="text-xs text-gray-400">Select credential value to insert</p>
          </div>
          <div className="py-1">
            {credentials.map((cred) => {
              const typeInfo = credentialTypes?.find(t => t.type_id === cred.credential_type);
              // credential의 데이터 키 목록 가져오기
              const dataKeys = typeInfo?.fields.map(f => f.key) || Object.keys(cred.data || {});
              
              return (
                <div key={cred.id} className="px-2 py-1">
                  <div className="flex items-center gap-2 text-xs text-gray-300 mb-1">
                    <span>{typeInfo?.icon || '🔑'}</span>
                    <span className="font-medium">{cred.name}</span>
                    <span className="text-gray-500">({typeInfo?.name || cred.credential_type})</span>
                  </div>
                  <div className="ml-4 space-y-0.5">
                    {dataKeys.map((key) => (
                      <button
                        key={key}
                        onClick={() => insertCredentialValue(index, cred.id, key)}
                        className="block w-full text-left px-2 py-1 text-xs text-gray-400 hover:bg-gray-700 hover:text-white rounded transition-colors"
                      >
                        <code className="text-amber-400">{key}</code>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          {onOpenCredentialModal && (
            <div className="border-t border-gray-700 p-2">
              <button
                onClick={() => {
                  setShowCredentialPicker(null);
                  onOpenCredentialModal();
                }}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
              >
                <Plus className="w-3 h-3" />
                Add New Credential
              </button>
            </div>
          )}
        </div>
      );
    };
    
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          <button
            onClick={addPair}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            <Plus className="w-3 h-3" />
            Add
          </button>
        </div>
        {schema?.description && (
          <p className="text-xs text-gray-500">{schema.description}</p>
        )}
        
        {entries.length === 0 ? (
          <p className="text-xs text-gray-500 italic">No headers. Click "Add" to add one.</p>
        ) : (
          <div className="space-y-2">
            {entries.map(([key, val], index) => {
              const isSensitive = isSensitiveKey(key);
              const isCredentialExpression = typeof val === 'string' && val.includes('{{ credential.');
              return (
                <div key={index} className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={key}
                      onChange={(e) => updateKey(key, e.target.value)}
                      placeholder="Header name"
                      className={`w-full px-2 py-1 bg-gray-700 border rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500 ${
                        isSensitive ? 'border-amber-600 pr-7' : 'border-gray-600'
                      }`}
                    />
                    {isSensitive && (
                      <Lock className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-500" />
                    )}
                  </div>
                  <div className="relative flex-1">
                    <input
                      type={isSensitive && !isCredentialExpression ? 'password' : 'text'}
                      value={val}
                      onChange={(e) => updateValue(key, e.target.value)}
                      placeholder={isSensitive ? '●●●●●● or use 🔑' : 'Value'}
                      className={`w-full px-2 py-1 pr-8 bg-gray-700 border rounded text-sm focus:outline-none focus:border-blue-500 ${
                        isCredentialExpression
                          ? 'border-amber-600 text-amber-300 font-mono text-xs'
                          : isSensitive 
                            ? 'border-amber-600 text-amber-300' 
                            : 'border-gray-600 text-gray-200'
                      }`}
                    />
                    {/* Credential 삽입 버튼 */}
                    <button
                      onClick={() => setShowCredentialPicker(showCredentialPicker === index ? null : index)}
                      className={`absolute right-1 top-1/2 -translate-y-1/2 p-0.5 rounded transition-colors ${
                        showCredentialPicker === index
                          ? 'bg-amber-600 text-white'
                          : 'text-gray-400 hover:text-amber-400 hover:bg-gray-600'
                      }`}
                      title="Insert credential value"
                    >
                      <Key className="w-4 h-4" />
                    </button>
                    {/* Credential Picker Popup */}
                    {showCredentialPicker === index && <CredentialPicker index={index} />}
                  </div>
                  <button
                    onClick={() => removePair(key)}
                    className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                    title="Remove"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
  
  // 객체/배열이 잘못 들어온 경우 (스키마 없이) - JSON 에디터로 폴백
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    const displayValue = JSON.stringify(value, null, 2);
    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          <div className="flex items-center gap-1">
            {schema?.required && <span className="text-red-400 text-xs">*</span>}
            <button
              onClick={toggleExpression}
              className={`px-1.5 py-0.5 text-xs rounded font-mono transition-colors ${
                isExpression 
                  ? 'bg-orange-600 text-white' 
                  : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
              }`}
              title="Toggle expression mode"
            >
              fx
            </button>
          </div>
        </div>
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          defaultValue={displayValue}
          rows={Math.min(Object.keys(value).length + 2, 8)}
          onBlur={(e) => {
            const val = e.target.value.trim();
            if (val.startsWith('{{')) {
              onChange(val);
              return;
            }
            try {
              onChange(JSON.parse(val));
            } catch {
              onChange(val);
            }
          }}
          onFocus={onFocus}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500 font-mono"
        />
      </div>
    );
  }
  
  // String 타입 (기본)
  // 값을 문자열로 변환 (배열인 경우 JSON으로)
  const stringValue = Array.isArray(value) 
    ? JSON.stringify(value) 
    : String(value ?? '');
  
  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`rounded transition-all ${dropZoneClass}`}
    >
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs text-gray-400 capitalize">{label}</label>
        <div className="flex items-center gap-1">
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
          <button
            onClick={toggleExpression}
            className={`px-1.5 py-0.5 text-xs rounded font-mono transition-colors ${
              isExpression 
                ? 'bg-orange-600 text-white' 
                : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
            }`}
            title="Toggle expression mode"
          >
            fx
          </button>
        </div>
      </div>
      
      {/* Field Description */}
      {schema?.description && !isExpression && (
        <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
      )}
      
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="text"
        value={stringValue}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        placeholder={isExpression ? '{{ nodes.nodeId.field }}' : undefined}
        className={`w-full px-3 py-1.5 rounded text-sm focus:outline-none focus:ring-1 transition-colors ${
          isExpression 
            ? 'bg-orange-900/30 border border-orange-600 text-orange-300 font-mono focus:ring-orange-500'
            : 'bg-gray-700 border border-gray-600 text-gray-200 focus:border-blue-500'
        }`}
      />
      
      {isExpression && (
        <p className="text-xs text-orange-400/70 mt-1">
          💡 Drag from Input tab or type expression
        </p>
      )}
    </div>
  );
}
