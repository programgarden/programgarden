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
