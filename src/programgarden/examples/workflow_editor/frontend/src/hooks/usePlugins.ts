import { useState, useEffect, useCallback } from 'react';

export interface PluginSchema {
  id: string;
  name?: string;
  category: string;
  version: string;
  description?: string;
  products: string[];
  fields_schema: Record<string, {
    type: string;
    required?: boolean;
    default?: unknown;
    description?: string;
    enum_values?: string[];
  }>;
}

export interface PluginsByCategory {
  [category: string]: string[];
}

// 노드 타입과 플러그인 카테고리 매핑
const NODE_TYPE_TO_PLUGIN_CATEGORY: Record<string, string> = {
  ConditionNode: 'strategy_condition',
  NewOrderNode: 'new_order',
  ModifyOrderNode: 'modify_order',
  CancelOrderNode: 'cancel_order',
};

export function usePlugins() {
  const [plugins, setPlugins] = useState<PluginsByCategory>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 전체 플러그인 목록 로드
  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        const res = await fetch('/api/plugins');
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
  }, []);

  // 노드 타입에 맞는 플러그인 목록 반환
  const getPluginsForNodeType = useCallback((nodeType: string): string[] => {
    const category = NODE_TYPE_TO_PLUGIN_CATEGORY[nodeType];
    if (!category) return [];
    return plugins[category] || [];
  }, [plugins]);

  // 특정 플러그인 스키마 가져오기
  const getPluginSchema = useCallback(async (pluginId: string): Promise<PluginSchema | null> => {
    try {
      const res = await fetch(`/api/plugins/${pluginId}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.plugin || null;
    } catch {
      return null;
    }
  }, []);

  return {
    plugins,
    loading,
    error,
    getPluginsForNodeType,
    getPluginSchema,
  };
}
