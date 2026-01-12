import { useState, useRef } from 'react';
import { ConfigField, Credential, CredentialTypeSchema } from '@/types/workflow';
import { Plus, X, Lock, Key } from 'lucide-react';
import SymbolEditor from './SymbolEditor';

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
