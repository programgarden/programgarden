import { Node, Edge } from '@xyflow/react';

/**
 * 특정 노드로 연결된 상위(upstream) 노드들 찾기
 */
export function findUpstreamNodes(
  nodeId: string,
  nodes: Node[],
  edges: Edge[]
): Node[] {
  const visited = new Set<string>();
  const result: Node[] = [];

  function traverse(currentId: string) {
    if (visited.has(currentId)) return;
    visited.add(currentId);

    // 현재 노드로 들어오는 엣지들 찾기
    const incomingEdges = edges.filter((e) => e.target === currentId);

    for (const edge of incomingEdges) {
      const sourceNode = nodes.find((n) => n.id === edge.source);
      if (sourceNode && !visited.has(sourceNode.id)) {
        result.push(sourceNode);
        traverse(sourceNode.id);
      }
    }
  }

  traverse(nodeId);
  return result;
}

/**
 * 포트 바인딩 타입별 자동 바인딩 소스 노드 타입 매핑
 * plan-conditionNodeAutoBinding.prompt.md 기반
 */
export const AUTO_BINDING_SOURCES: Record<string, { nodeTypes: string[]; outputFields: string[] }> = {
  // 가격/시장 데이터
  'market_data': {
    nodeTypes: ['RealMarketDataNode', 'MarketDataNode', 'HistoricalDataNode'],
    outputFields: ['price', 'ohlcv'],
  },
  'price_data': {
    nodeTypes: ['RealMarketDataNode', 'MarketDataNode', 'HistoricalDataNode'],
    outputFields: ['price', 'ohlcv'],
  },
  'volume_data': {
    nodeTypes: ['RealMarketDataNode', 'MarketDataNode'],
    outputFields: ['volume'],
  },
  // 종목 리스트
  'symbol_list': {
    nodeTypes: ['WatchlistNode', 'ScreenerNode', 'MarketUniverseNode', 'SymbolFilterNode'],
    outputFields: ['symbols', 'filtered_symbols'],
  },
  'symbols': {
    nodeTypes: ['WatchlistNode', 'ScreenerNode', 'MarketUniverseNode', 'SymbolFilterNode'],
    outputFields: ['symbols', 'filtered_symbols'],
  },
  // 포지션/계좌 데이터
  'position_data': {
    nodeTypes: ['RealAccountNode', 'AccountNode'],
    outputFields: ['positions'],
  },
  'held_symbols': {
    nodeTypes: ['RealAccountNode', 'AccountNode'],
    outputFields: ['held_symbols'],
  },
  // 주문 데이터
  'order_list': {
    nodeTypes: ['NewOrderNode', 'RealAccountNode'],
    outputFields: ['active_orders', 'orders'],
  },
  // 수량
  'quantity': {
    nodeTypes: ['PositionSizingNode'],
    outputFields: ['quantity', 'size'],
  },
  // 잔고
  'balance': {
    nodeTypes: ['RealAccountNode', 'AccountNode'],
    outputFields: ['balance', 'available_balance'],
  },
};

export interface AutoBindingResult {
  available: boolean;
  sourceNode?: Node;
  sourceField?: string;
  expression?: string;
}

/**
 * 특정 포트 타입에 대해 자동 바인딩 가능한 소스를 찾기
 * @param portType - ui_hint의 port_binding: 뒤의 타입 (예: 'market_data', 'symbol_list')
 * @param upstreamNodes - 상위 노드들
 * @returns 자동 바인딩 가능 여부와 소스 정보
 */
export function findAutoBindingSource(
  portType: string,
  upstreamNodes: Node[]
): AutoBindingResult {
  const sourceConfig = AUTO_BINDING_SOURCES[portType];
  
  if (!sourceConfig) {
    return { available: false };
  }
  
  // 우선순위에 따라 소스 노드 탐색 (nodeTypes 배열 순서가 우선순위)
  for (const nodeType of sourceConfig.nodeTypes) {
    const sourceNode = upstreamNodes.find(
      (n) => (n.data as Record<string, unknown>).nodeType === nodeType
    );
    
    if (sourceNode) {
      // 해당 노드의 outputs에서 매칭되는 필드 찾기
      const outputs = (sourceNode.data as Record<string, unknown>).outputs as 
        { name: string; type: string }[] | undefined;
      
      if (outputs) {
        for (const outputField of sourceConfig.outputFields) {
          const matchingOutput = outputs.find(o => o.name === outputField);
          if (matchingOutput) {
            return {
              available: true,
              sourceNode,
              sourceField: outputField,
              expression: `{{ nodes.${sourceNode.id}.${outputField} }}`,
            };
          }
        }
      }
      
      // outputs가 없어도 nodeType이 매칭되면 첫 번째 필드로 바인딩
      const defaultField = sourceConfig.outputFields[0];
      return {
        available: true,
        sourceNode,
        sourceField: defaultField,
        expression: `{{ nodes.${sourceNode.id}.${defaultField} }}`,
      };
    }
  }
  
  return { available: false };
}

/**
 * 포트 타입에 필요한 노드 타입들의 한글 이름 반환
 */
export function getRequiredNodeTypesForPort(portType: string): string {
  const sourceConfig = AUTO_BINDING_SOURCES[portType];
  if (!sourceConfig) return '';
  
  const nodeTypeNames: Record<string, string> = {
    'RealMarketDataNode': '실시간 시세',
    'MarketDataNode': '시장 데이터',
    'HistoricalDataNode': '과거 데이터',
    'WatchlistNode': '관심종목',
    'ScreenerNode': '종목 스크리너',
    'MarketUniverseNode': '시장 유니버스',
    'SymbolFilterNode': '종목 필터',
    'RealAccountNode': '실시간 계좌',
    'AccountNode': '계좌',
    'PositionSizingNode': '포지션 사이징',
    'NewOrderNode': '신규 주문',
  };
  
  return sourceConfig.nodeTypes
    .map(t => nodeTypeNames[t] || t.replace('Node', ''))
    .join(', ');
}
