import { useState, useRef } from 'react';
import { ConfigField, Credential, CredentialTypeSchema } from '@/types/workflow';
import { Plus, X, Lock, Key } from 'lucide-react';
import SymbolEditor from './SymbolEditor';
import { PluginSummary } from '@/hooks/usePlugins';

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
  availablePlugins?: PluginSummary[];
  onPluginChange?: (pluginId: string) => void;
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
  
  // Port binding field인지 확인 (ui_hint가 port_binding:*로 시작하거나, 바인딩 가이드 정보가 있는 경우)
  // 단, enum/boolean 타입은 제외 (고정된 선택지가 있는 필드)
  const hasBindingGuide = schema?.example !== undefined || (schema?.bindable_sources && schema.bindable_sources.length > 0);
  const isEnumOrBooleanType = schema?.type === 'enum' || schema?.type === 'boolean';
  const isPortBindingField = !isEnumOrBooleanType && (schema?.ui_hint?.startsWith('port_binding:') || hasBindingGuide);
  const portBindingType = schema?.ui_hint?.startsWith('port_binding:') ? schema?.ui_hint?.split(':')[1] : null;
  
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
    // 현재 선택된 플러그인 정보
    const currentPlugin = availablePlugins.find(p => p.id === value);
    
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
          {availablePlugins.map(plugin => (
            <option key={plugin.id} value={plugin.id}>
              {plugin.name || plugin.id}
            </option>
          ))}
        </select>
        {/* 선택된 플러그인의 설명 표시 */}
        {currentPlugin?.description && (
          <p className="text-xs text-gray-400 mt-1.5 p-2 bg-gray-800/50 rounded border border-gray-700">
            📝 {currentPlugin.description}
          </p>
        )}
        {!value && (
          <p className="text-xs text-amber-500/70 mt-1.5">
            💡 Select a plugin to configure its parameters
          </p>
        )}
      </div>
    );
  }
  
  // Port Binding 필드 또는 바인딩 가이드가 있는 필드
  if (isPortBindingField) {
    // 포트 타입별 기본 설정 (아이콘, 색상 등)
    const portTypeDefaults: Record<string, { icon: string; color: string }> = {
      'market_data': { icon: '📈', color: 'emerald' },
      'price_data': { icon: '📈', color: 'emerald' },
      'volume_data': { icon: '📊', color: 'emerald' },
      'symbol_list': { icon: '🎯', color: 'cyan' },
      'symbols': { icon: '🎯', color: 'cyan' },
      'position_data': { icon: '📋', color: 'purple' },
      'held_symbols': { icon: '🎯', color: 'purple' },
      'order_list': { icon: '📝', color: 'orange' },
      'quantity': { icon: '🔢', color: 'indigo' },
      'balance': { icon: '💰', color: 'yellow' },
    };
    
    const typeKey = portBindingType || 'default';
    const defaultConfig = portTypeDefaults[typeKey] || { icon: '🔗', color: 'gray' };
    
    // 스키마에서 바인딩 정보 가져오기 (백엔드에서 전달됨)
    const jsonExample = schema?.example !== undefined 
      ? (typeof schema.example === 'string' ? schema.example : JSON.stringify(schema.example, null, 2))
      : null;
    const bindingExample = schema?.example_binding || `{{ nodes.노드ID.${fieldKey} }}`;
    const bindableSources = schema?.bindable_sources || [];
    const expectedType = schema?.expected_type || 'any';
    
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
    
    // 값이 비어있는지 확인
    const isEmpty = !value || (typeof value === 'string' && value.trim() === '');
    
    // 바인딩 표현식 유효성 검사
    const isBindingExpression = typeof value === 'string' && value.includes('{{');
    const isValidBinding = (() => {
      if (!isBindingExpression) return true; // 바인딩이 아니면 검사 안함
      const strValue = String(value);
      // {{ nodes.xxx.yyy }} 패턴 검사
      const bindingPattern = /^\{\{\s*nodes\.\w+\.\w+(\.\w+)*\s*\}\}$/;
      return bindingPattern.test(strValue.trim());
    })();
    
    // 입력값 상태에 따른 스타일 결정
    const getInputStyle = () => {
      if (isEmpty) {
        return 'border border-gray-600 bg-gray-700 text-gray-200 placeholder:text-gray-500';
      }
      if (isBindingExpression && !isValidBinding) {
        // 바인딩 표현식이지만 형식이 잘못됨 → 빨간색
        return 'border border-red-500 bg-red-900/20 text-red-300 focus:ring-red-500';
      }
      if (isBindingExpression && isValidBinding) {
        // 유효한 바인딩 표현식 → 해당 색상
        return colorClasses[defaultConfig.color];
      }
      // JSON 직접 입력 → 해당 색상
      return colorClasses[defaultConfig.color];
    };

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
              {defaultConfig.icon} {label}
            </span>
          </label>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </div>
        {schema?.description && (
          <p className="text-xs text-gray-500 mb-1.5">{schema.description}</p>
        )}
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          value={
            value === null || value === undefined 
              ? '' 
              : typeof value === 'object' 
                ? JSON.stringify(value, null, 2) 
                : String(value)
          }
          onChange={(e) => {
            const newValue = e.target.value;
            // JSON 파싱 시도 (배열이나 객체일 수 있음)
            if (newValue.trim().startsWith('[') || newValue.trim().startsWith('{')) {
              try {
                const parsed = JSON.parse(newValue);
                onChange(parsed);
                return;
              } catch {
                // 파싱 실패 시 문자열로 유지
              }
            }
            onChange(newValue);
          }}
          onFocus={onFocus}
          placeholder={bindingExample}
          rows={2}
          className={`w-full px-3 py-1.5 rounded text-sm font-mono focus:outline-none focus:ring-1 transition-colors resize-y min-h-[38px] ${getInputStyle()}`}
        />
        
        {/* 바인딩 표현식 검증 에러 메시지 */}
        {isBindingExpression && !isValidBinding && (
          <p className="text-xs text-red-400 mt-1">
            ⚠️ 잘못된 바인딩 형식. 올바른 형식: <code className="bg-gray-700 px-1 rounded">{'{{ nodes.노드ID.필드명 }}'}</code>
          </p>
        )}
        
        {/* 바인딩 가이드 (항상 표시) */}
        {(jsonExample || bindableSources.length > 0) && (
          <div className="mt-2 p-2 bg-gray-800/50 rounded border border-gray-700 text-xs">
            <p className="text-gray-400 mb-2">💡 입력 방법:</p>
            
            {/* 방법 1: 바인딩 표현식 */}
            <p className="text-gray-500 ml-3">1. 바인딩 표현식:</p>
            <p className="text-gray-500 ml-6"><code className="bg-gray-700 px-1 rounded text-cyan-400">{bindingExample}</code></p>
            
            {/* 방법 2: JSON 직접 입력 */}
            {jsonExample && (
              <>
                <p className="text-gray-500 ml-3 mt-2">2. JSON 직접 입력 <span className="text-gray-600">({expectedType})</span>:</p>
                <pre className="ml-6 mt-1 p-2 bg-gray-900 rounded border border-gray-700 text-yellow-400 overflow-x-auto whitespace-pre-wrap break-all">{jsonExample}</pre>
              </>
            )}
            
            {/* 바인딩 가능 소스 목록 */}
            {bindableSources.length > 0 && (
              <>
                <p className="text-gray-500 ml-3 mt-2">📌 바인딩 가능 소스:</p>
                <div className="ml-6 mt-1 flex flex-wrap gap-1">
                  {bindableSources.map((src, i) => (
                    <code key={i} className="bg-gray-700 px-1.5 py-0.5 rounded text-cyan-400 text-xs">{src}</code>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
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
    // 서버에서 제공하는 enum_labels 사용, 없으면 폴백
    const enumLabels: Record<string, string> = schema.enum_labels || {};
    
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
