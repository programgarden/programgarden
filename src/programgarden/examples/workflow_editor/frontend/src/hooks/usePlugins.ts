import { useState, useEffect, useCallback, useRef } from 'react';
import { ConfigField } from '@/types/workflow';

// 플러그인 필드 스키마 (서버에서 오는 형태)
export interface PluginFieldSchema {
  type: string;           // 'int', 'float', 'string', 'boolean'
  required?: boolean;
  default?: unknown;
  title?: string;         // 필드 제목
  description?: string;   // 필드 설명
  enum?: string[];        // enum 타입일 때 선택지
  ge?: number;            // 최소값 (greater or equal)
  le?: number;            // 최대값 (less or equal)
  gt?: number;            // 초과 (greater than)
  lt?: number;            // 미만 (less than)
}

export interface PluginSchema {
  id: string;
  name?: string;
  category: string;
  version: string;
  description?: string;
  products: string[];
  fields_schema: Record<string, PluginFieldSchema>;
  tags?: string[];
  locales?: Record<string, Record<string, string>>;  // 다국어 지원
  required_data?: string[];  // 필요한 데이터 타입 (예: ['data'], ['positions'])
}

// 플러그인 목록에서 간략 정보
export interface PluginSummary {
  id: string;
  name: string;
  description: string;
}

export interface PluginsByCategory {
  [category: string]: PluginSummary[];
}

// 노드 타입과 플러그인 카테고리 매핑
const NODE_TYPE_TO_PLUGIN_CATEGORY: Record<string, string> = {
  ConditionNode: 'strategy_condition',
  NewOrderNode: 'new_order',
  ModifyOrderNode: 'modify_order',
  CancelOrderNode: 'cancel_order',
};

/**
 * 플러그인 fields_schema를 프론트엔드 ConfigField로 변환
 * 다국어 지원: locale이 있으면 해당 언어의 설명 사용
 */
export function convertFieldsSchemaToConfigFields(
  fieldsSchema: Record<string, PluginFieldSchema>,
  locales?: Record<string, Record<string, string>>,
  locale: string = 'en'
): Record<string, ConfigField & { 
  ge?: number; 
  le?: number;
  gt?: number;
  lt?: number;
  title?: string;
}> {
  const result: Record<string, ConfigField & { 
    ge?: number; 
    le?: number;
    gt?: number;
    lt?: number;
    title?: string;
  }> = {};
  
  // 해당 locale의 번역 가져오기
  const translations = locales?.[locale] || {};
  
  for (const [key, field] of Object.entries(fieldsSchema)) {
    // 타입 매핑
    let configType: string;
    let enumValues: string[] | undefined;
    
    if (field.enum && field.enum.length > 0) {
      configType = 'enum';
      enumValues = field.enum;
    } else if (field.type === 'int' || field.type === 'integer') {
      configType = 'integer';
    } else if (field.type === 'float' || field.type === 'number') {
      configType = 'number';
    } else if (field.type === 'boolean' || field.type === 'bool') {
      configType = 'boolean';
    } else {
      configType = 'string';
    }
    
    // 다국어 설명 가져오기 (fields.{key} 형식)
    const localizedDescription = translations[`fields.${key}`] 
      || field.description 
      || field.title 
      || key;
    
    result[key] = {
      type: configType,
      required: field.required ?? false,
      default: field.default,
      description: localizedDescription,
      title: field.title || key,
      category: 'parameters',
      enum_values: enumValues,
      bindable: true,
      // 유효성 검사용 제약조건
      ge: field.ge,
      le: field.le,
      gt: field.gt,
      lt: field.lt,
    };
  }
  
  return result;
}

/**
 * 플러그인 스키마에서 기본값 객체 생성
 */
export function getDefaultFieldsFromSchema(
  fieldsSchema: Record<string, PluginFieldSchema>
): Record<string, unknown> {
  const defaults: Record<string, unknown> = {};
  for (const [key, field] of Object.entries(fieldsSchema)) {
    if (field.default !== undefined) {
      defaults[key] = field.default;
    }
  }
  return defaults;
}

// 브라우저 언어 감지 (ko, en 중 선택)
function detectLocale(): string {
  const browserLang = navigator.language || 'en';
  return browserLang.startsWith('ko') ? 'ko' : 'en';
}

export function usePlugins() {
  const [plugins, setPlugins] = useState<PluginsByCategory>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 플러그인 스키마 캐시 (중복 fetch 방지)
  const schemaCache = useRef<Map<string, PluginSchema>>(new Map());
  
  // 현재 locale
  const locale = detectLocale();

  // 전체 플러그인 목록 로드
  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        const res = await fetch(`/api/plugins?locale=${locale}`);
        if (!res.ok) throw new Error('Failed to fetch plugins');
        const data = await res.json();
        setPlugins(data.plugins || {});
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchPlugins();
  }, [locale]);

  // 노드 타입에 맞는 플러그인 목록 반환 (id, name, description 포함)
  const getPluginsForNodeType = useCallback((nodeType: string): PluginSummary[] => {
    const category = NODE_TYPE_TO_PLUGIN_CATEGORY[nodeType];
    if (!category) return [];
    return plugins[category] || [];
  }, [plugins]);

  // 특정 플러그인 스키마 가져오기 (캐싱 적용)
  const getPluginSchema = useCallback(async (pluginId: string): Promise<PluginSchema | null> => {
    // 캐시 확인
    if (schemaCache.current.has(pluginId)) {
      return schemaCache.current.get(pluginId)!;
    }
    
    try {
      const res = await fetch(`/api/plugins/${pluginId}`);
      if (!res.ok) return null;
      const data = await res.json();
      const schema = data.plugin || null;
      
      // 캐시에 저장
      if (schema) {
        schemaCache.current.set(pluginId, schema);
      }
      
      return schema;
    } catch {
      return null;
    }
  }, []);
  
  // 캐시에서 동기적으로 스키마 가져오기 (이미 로드된 경우)
  const getCachedPluginSchema = useCallback((pluginId: string): PluginSchema | null => {
    return schemaCache.current.get(pluginId) || null;
  }, []);
  
  // 캐시 초기화
  const clearSchemaCache = useCallback(() => {
    schemaCache.current.clear();
  }, []);

  return {
    plugins,
    loading,
    error,
    getPluginsForNodeType,
    getPluginSchema,
    getCachedPluginSchema,
    clearSchemaCache,
  };
}
