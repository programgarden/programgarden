import { useState, useEffect, useCallback } from 'react';
import { usePlugins, PluginSchema, convertFieldsSchemaToConfigFields, getDefaultFieldsFromSchema } from '@/hooks/usePlugins';
import { Loader2, AlertCircle, Info } from 'lucide-react';
import { ConfigField } from '@/types/workflow';

interface ValidationError {
  field: string;
  message: string;
}

interface PluginFieldsGroupProps {
  pluginId: string;
  fields: Record<string, unknown>;
  onChange: (fields: Record<string, unknown>) => void;
  locale?: string;  // 다국어 지원 (기본: en)
}

/**
 * 플러그인 필드 그룹 컴포넌트
 * - 플러그인 선택 시 동적으로 필드를 렌더링
 * - 유효성 검사 지원 (ge, le, required)
 * - 다국어 지원
 */
export default function PluginFieldsGroup({ 
  pluginId, 
  fields, 
  onChange,
  locale = 'en'
}: PluginFieldsGroupProps) {
  const { getPluginSchema, getCachedPluginSchema } = usePlugins();
  const [schema, setSchema] = useState<PluginSchema | null>(() => getCachedPluginSchema(pluginId));
  const [loading, setLoading] = useState(!schema);
  const [errors, setErrors] = useState<ValidationError[]>([]);

  // 플러그인 스키마 로드
  useEffect(() => {
    const cached = getCachedPluginSchema(pluginId);
    if (cached) {
      setSchema(cached);
      setLoading(false);
      return;
    }
    
    setLoading(true);
    getPluginSchema(pluginId)
      .then((s) => {
        setSchema(s);
        // 스키마 로드 후 기본값이 없는 필드는 기본값 설정
        if (s?.fields_schema) {
          const defaults = getDefaultFieldsFromSchema(s.fields_schema);
          const currentFields = fields || {};
          const needsUpdate = Object.keys(defaults).some(
            key => currentFields[key] === undefined
          );
          if (needsUpdate) {
            onChange({ ...defaults, ...currentFields });
          }
        }
      })
      .finally(() => setLoading(false));
  }, [pluginId, getPluginSchema, getCachedPluginSchema]);

  // 유효성 검사
  const validateField = useCallback((
    key: string, 
    value: unknown, 
    fieldSchema: ConfigField & { ge?: number; le?: number; gt?: number; lt?: number; title?: string }
  ): string | null => {
    // required 검사
    if (fieldSchema.required && (value === undefined || value === null || value === '')) {
      return `${fieldSchema.title || key} is required`;
    }
    
    // 숫자 타입 제약조건 검사
    if ((fieldSchema.type === 'integer' || fieldSchema.type === 'number') && value !== undefined && value !== '') {
      const numValue = Number(value);
      if (isNaN(numValue)) {
        return 'Must be a valid number';
      }
      if (fieldSchema.ge !== undefined && numValue < fieldSchema.ge) {
        return `Must be ≥ ${fieldSchema.ge}`;
      }
      if (fieldSchema.le !== undefined && numValue > fieldSchema.le) {
        return `Must be ≤ ${fieldSchema.le}`;
      }
      if (fieldSchema.gt !== undefined && numValue <= fieldSchema.gt) {
        return `Must be > ${fieldSchema.gt}`;
      }
      if (fieldSchema.lt !== undefined && numValue >= fieldSchema.lt) {
        return `Must be < ${fieldSchema.lt}`;
      }
    }
    
    return null;
  }, []);

  // 필드 변경 핸들러 (유효성 검사 포함)
  const handleFieldChange = useCallback((key: string, value: unknown, fieldSchema: ConfigField & { ge?: number; le?: number; gt?: number; lt?: number; title?: string }) => {
    // 값 업데이트
    const newFields = { ...fields, [key]: value };
    onChange(newFields);
    
    // 유효성 검사
    const error = validateField(key, value, fieldSchema);
    setErrors(prev => {
      const filtered = prev.filter(e => e.field !== key);
      if (error) {
        return [...filtered, { field: key, message: error }];
      }
      return filtered;
    });
  }, [fields, onChange, validateField]);

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex items-center justify-center py-6 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-sm">Loading plugin schema...</span>
      </div>
    );
  }

  // 스키마 없음
  if (!schema) {
    return (
      <div className="flex items-center gap-2 py-4 px-3 bg-red-900/20 border border-red-800 rounded text-red-400">
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
        <span className="text-sm">Plugin &quot;{pluginId}&quot; not found</span>
      </div>
    );
  }

  // fields_schema가 없으면 빈 상태
  if (!schema.fields_schema || Object.keys(schema.fields_schema).length === 0) {
    return (
      <div className="py-4 text-center text-gray-500 text-sm">
        No configurable parameters for this plugin
      </div>
    );
  }

  // 필드 스키마를 ConfigField로 변환
  const configFields = convertFieldsSchemaToConfigFields(
    schema.fields_schema,
    schema.locales,
    locale
  );

  // 플러그인 이름 (다국어 지원)
  const pluginDisplayName = schema.locales?.[locale]?.name || schema.name || schema.id;
  const pluginDescription = schema.locales?.[locale]?.description || schema.description;

  return (
    <div className="mt-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
      {/* 헤더 */}
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-700">
        <span className="text-base">📊</span>
        <h4 className="text-sm font-medium text-gray-200">
          {pluginDisplayName}
        </h4>
        {schema.tags && schema.tags.length > 0 && (
          <div className="flex gap-1 ml-auto">
            {schema.tags.slice(0, 2).map(tag => (
              <span key={tag} className="text-xs px-1.5 py-0.5 bg-gray-700 text-gray-400 rounded">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* 플러그인 설명 */}
      {pluginDescription && (
        <div className="flex items-start gap-2 mb-3 p-2 bg-blue-900/20 rounded border border-blue-800/30">
          <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-blue-300/80 leading-relaxed">{pluginDescription}</p>
        </div>
      )}

      {/* 필드 목록 */}
      <div className="space-y-3">
        {Object.entries(configFields).map(([key, fieldSchema]) => {
          const value = fields[key] ?? fieldSchema.default;
          const fieldError = errors.find(e => e.field === key);
          const hasError = !!fieldError;
          
          return (
            <div key={key}>
              {/* 필드 라벨 + 설명 */}
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-gray-300 font-medium">
                  {fieldSchema.title || key}
                  {fieldSchema.required && <span className="text-red-400 ml-1">*</span>}
                </label>
                {/* 제약조건 힌트 */}
                {(fieldSchema.ge !== undefined || fieldSchema.le !== undefined) && (
                  <span className="text-xs text-gray-500">
                    {fieldSchema.ge !== undefined && fieldSchema.le !== undefined 
                      ? `${fieldSchema.ge} ~ ${fieldSchema.le}`
                      : fieldSchema.ge !== undefined 
                        ? `≥ ${fieldSchema.ge}`
                        : `≤ ${fieldSchema.le}`
                    }
                  </span>
                )}
              </div>
              
              {/* 필드 설명 */}
              {fieldSchema.description && fieldSchema.description !== key && (
                <p className="text-xs text-gray-500 mb-1.5">{fieldSchema.description}</p>
              )}
              
              {/* 필드 입력 */}
              {renderField(key, value, fieldSchema, hasError, (v) => handleFieldChange(key, v, fieldSchema))}
              
              {/* 에러 메시지 */}
              {hasError && (
                <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {fieldError.message}
                </p>
              )}
            </div>
          );
        })}
      </div>
      
      {/* 전체 유효성 에러가 있으면 하단에 경고 */}
      {errors.length > 0 && (
        <div className="mt-3 pt-2 border-t border-gray-700">
          <p className="text-xs text-amber-400 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {errors.length} validation error{errors.length > 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  );
}

// 필드 타입별 렌더링
function renderField(
  _key: string,
  value: unknown,
  schema: ConfigField & { ge?: number; le?: number; title?: string },
  hasError: boolean,
  onChange: (value: unknown) => void
) {
  const baseInputClass = `w-full px-3 py-1.5 bg-gray-700 border rounded text-sm text-gray-200 focus:outline-none transition-colors ${
    hasError 
      ? 'border-red-500 focus:border-red-400' 
      : 'border-gray-600 focus:border-blue-500'
  }`;

  // Enum 타입 (드롭다운)
  if (schema.type === 'enum' && schema.enum_values && schema.enum_values.length > 0) {
    return (
      <select
        value={String(value ?? schema.default ?? '')}
        onChange={(e) => onChange(e.target.value)}
        className={baseInputClass}
      >
        {schema.enum_values.map((enumValue) => (
          <option key={enumValue} value={enumValue}>
            {enumValue}
          </option>
        ))}
      </select>
    );
  }
  
  // Boolean 타입
  if (schema.type === 'boolean') {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <span className="text-sm text-gray-300">Enabled</span>
      </label>
    );
  }
  
  // Number/Integer 타입
  if (schema.type === 'number' || schema.type === 'integer') {
    return (
      <input
        type="number"
        value={value !== undefined && value !== null ? String(value) : ''}
        step={schema.type === 'integer' ? 1 : 0.01}
        min={schema.ge}
        max={schema.le}
        onChange={(e) => {
          const val = e.target.value;
          if (val === '') {
            onChange(undefined);
          } else {
            const num = schema.type === 'integer' ? parseInt(val) : parseFloat(val);
            onChange(isNaN(num) ? val : num);
          }
        }}
        className={baseInputClass}
        placeholder={schema.default !== undefined ? `Default: ${schema.default}` : ''}
      />
    );
  }
  
  // 기본 String 타입
  return (
    <input
      type="text"
      value={String(value ?? '')}
      onChange={(e) => onChange(e.target.value)}
      className={baseInputClass}
      placeholder={schema.default !== undefined ? `Default: ${schema.default}` : ''}
    />
  );
}
