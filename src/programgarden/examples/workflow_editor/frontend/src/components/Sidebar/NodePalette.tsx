import { useState, useEffect, DragEvent } from 'react';
import { ChevronDown, ChevronRight, Search, X } from 'lucide-react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { getCategoryColor, getCategoryIcon } from '@/utils/nodeColors';
import { getNodeLabel } from '@/utils/nodeLabels';
import { NodeTypeSchema, CategoryInfo } from '@/types/workflow';

interface GroupedNodeTypes {
  [category: string]: NodeTypeSchema[];
}

interface NodePaletteProps {
  onClose?: () => void;
}

export default function NodePalette({ onClose }: NodePaletteProps) {
  const { nodeTypes, nodeTypesLoaded, setNodeTypes, addNode, locale } = useWorkflowStore();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['infra', 'condition', 'order']));
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categoryInfo, setCategoryInfo] = useState<Record<string, CategoryInfo>>({});
  const [categoriesLoaded, setCategoriesLoaded] = useState(false);

  // Load node types from API
  useEffect(() => {
    if (!nodeTypesLoaded) {
      setLoading(true);
      setError(null);
      
      fetch(`/api/node-types?locale=${locale}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (data.node_types && data.node_types.length > 0) {
            setNodeTypes(data.node_types);
          } else {
            console.warn('API returned empty node types, using mock data');
            setNodeTypes(getMockNodeTypes());
          }
        })
        .catch((err) => {
          console.error('Failed to load node types:', err);
          setError('Using demo nodes');
          setNodeTypes(getMockNodeTypes());
        })
        .finally(() => setLoading(false));
    }
  }, [nodeTypesLoaded, setNodeTypes, locale]);

  // Load categories separately (always load if not loaded)
  useEffect(() => {
    if (!categoriesLoaded) {
      fetch(`/api/categories?locale=${locale}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (data.categories && data.categories.length > 0) {
            const catMap: Record<string, CategoryInfo> = {};
            for (const cat of data.categories) {
              catMap[cat.id] = cat;
            }
            setCategoryInfo(catMap);
            setCategoriesLoaded(true);
          }
        })
        .catch((err) => {
          console.error('Failed to load categories:', err);
        });
    }
  }, [categoriesLoaded, locale]);

  // Group node types by category
  const groupedTypes: GroupedNodeTypes = nodeTypes.reduce((acc, type) => {
    const category = type.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(type);
    return acc;
  }, {} as GroupedNodeTypes);

  // Filter by search term
  const filteredGroups = Object.entries(groupedTypes).reduce((acc, [category, types]) => {
    const filtered = types.filter(
      (t) =>
        t.node_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.description?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false)
    );
    if (filtered.length > 0) {
      acc[category] = filtered;
    }
    return acc;
  }, {} as GroupedNodeTypes);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const onDragStart = (event: DragEvent, nodeType: string, category: string) => {
    console.log('Drag start:', nodeType, category);
    event.dataTransfer.setData('application/nodeType', nodeType);
    event.dataTransfer.setData('application/category', category);
    event.dataTransfer.setData('text/plain', nodeType); // Fallback for compatibility
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDoubleClick = (nodeType: string, category: string) => {
    // Add node at center of canvas when double-clicked
    const schema = nodeTypes.find((t) => t.node_type === nodeType);
    const position = { x: 200 + Math.random() * 200, y: 100 + Math.random() * 200 };
    addNode(nodeType, category, position, schema);
  };

  return (
    <div className="w-72 bg-gray-800 border-r border-gray-700 flex flex-col h-full shadow-xl">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-200">Node Palette</h2>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        {error && (
          <div className="mt-2 text-xs text-yellow-500">{error}</div>
        )}
      </div>

      {/* Node List */}
      <div className="flex-1 overflow-y-auto p-2">
        {Object.entries(filteredGroups).map(([category, types]) => (
          <div key={category} className="mb-2">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex flex-col px-2 py-1.5 rounded hover:bg-gray-700 text-left"
            >
              <div className="flex items-center gap-2 w-full">
                {expandedCategories.has(category) ? (
                  <ChevronDown className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                )}
                <span className="text-base">{getCategoryIcon(category)}</span>
                <span
                  className="text-sm font-medium"
                  style={{ color: getCategoryColor(category) }}
                >
                  {categoryInfo[category]?.name || category}
                </span>
                <span className="text-xs text-gray-500 ml-auto">{types.length}</span>
              </div>
              {categoryInfo[category]?.description && (
                <div className="text-xs text-gray-500 ml-8 mt-0.5 line-clamp-2">
                  {categoryInfo[category].description}
                </div>
              )}
            </button>

            {/* Node Items */}
            {expandedCategories.has(category) && (
              <div className="ml-4 mt-1 space-y-1">
                {types.map((type) => (
                  <div
                    key={type.node_type}
                    className="flex items-center gap-1"
                  >
                    <div
                      draggable
                      onDragStart={(e) => onDragStart(e, type.node_type, category)}
                      onDoubleClick={() => onDoubleClick(type.node_type, category)}
                      className="flex-1 px-2 py-2 rounded bg-gray-750 hover:bg-gray-700 cursor-pointer border border-transparent hover:border-gray-600 transition-colors group"
                      title="더블클릭으로 캔버스에 추가"
                    >
                      <div className="text-xs font-medium text-gray-200">{getNodeLabel(type.node_type, locale)}</div>
                      {type.description && (
                        <div className="text-xs text-gray-400 mt-1 leading-relaxed group-hover:text-gray-300 transition-colors">
                          {type.description}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => onDoubleClick(type.node_type, category)}
                      className="px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded self-start mt-0.5"
                      title="캔버스에 추가"
                    >
                      +
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {Object.keys(filteredGroups).length === 0 && (
          <div className="text-center text-gray-500 text-sm py-4">
            {loading ? 'Loading...' : nodeTypesLoaded ? 'No nodes found' : 'Loading...'}
          </div>
        )}
      </div>

      {/* Help text */}
      <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
        Drag nodes to canvas to add them
      </div>
    </div>
  );
}

// Mock data for development
function getMockNodeTypes(): NodeTypeSchema[] {
  return [
    { node_type: 'StartNode', category: 'infra', description: 'Workflow entry point', inputs: [], outputs: [{ name: 'next', type: 'flow' }], config_schema: {} },
    { node_type: 'BrokerNode', category: 'infra', description: 'Broker connection', inputs: [{ name: 'trigger', type: 'flow' }], outputs: [{ name: 'connected', type: 'flow' }], config_schema: {} },
    { node_type: 'WatchlistNode', category: 'symbol', description: 'Symbol watchlist', inputs: [{ name: 'broker', type: 'broker' }], outputs: [{ name: 'symbols', type: 'list' }], config_schema: {} },
    { node_type: 'HistoricalDataNode', category: 'data', description: 'Historical price data', inputs: [{ name: 'symbols', type: 'list' }], outputs: [{ name: 'data', type: 'dataframe' }], config_schema: {} },
    { node_type: 'ConditionNode', category: 'condition', description: 'Evaluate conditions', inputs: [{ name: 'data', type: 'dataframe' }], outputs: [{ name: 'passed', type: 'list' }, { name: 'failed', type: 'list' }], config_schema: {} },
    { node_type: 'LogicNode', category: 'condition', description: 'Combine conditions', inputs: [{ name: 'conditions', type: 'list' }], outputs: [{ name: 'result', type: 'bool' }], config_schema: {} },
    { node_type: 'NewOrderNode', category: 'order', description: 'Create new order', inputs: [{ name: 'symbols', type: 'list' }], outputs: [{ name: 'orders', type: 'list' }], config_schema: {} },
    { node_type: 'PositionSizingNode', category: 'risk', description: 'Calculate position size', inputs: [{ name: 'signals', type: 'list' }], outputs: [{ name: 'sized', type: 'list' }], config_schema: {} },
    { node_type: 'DisplayNode', category: 'display', description: 'Display results', inputs: [{ name: 'data', type: 'any' }], outputs: [], config_schema: {} },
    { node_type: 'BacktestEngineNode', category: 'backtest', description: 'Run backtest', inputs: [{ name: 'strategy', type: 'flow' }], outputs: [{ name: 'results', type: 'object' }], config_schema: {} },
  ];
}
