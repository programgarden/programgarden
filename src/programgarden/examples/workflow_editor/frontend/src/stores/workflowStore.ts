import { create } from 'zustand';
import {
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  applyNodeChanges,
  applyEdgeChanges,
  Connection,
} from '@xyflow/react';
import { NodeState, EdgeState, LogEntry, NodeTypeSchema } from '@/types/workflow';
import { isPortCompatible, getEdgeColor } from '@/utils/portCompatibility';

interface WorkflowState {
  // Workflow metadata
  workflowId: string;
  workflowName: string;
  workflowDescription: string;

  // React Flow state
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;

  // Node registry
  nodeTypes: NodeTypeSchema[];
  nodeTypesLoaded: boolean;

  // Execution state
  isRunning: boolean;
  nodeStates: Record<string, NodeState>;
  edgeStates: Record<string, EdgeState>;
  logs: LogEntry[];
  
  // Node outputs (last execution results)
  nodeOutputs: Record<string, unknown>;

  // Actions - React Flow
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;

  // Actions - Node management
  addNode: (nodeType: string, category: string, position: { x: number; y: number }, schema?: NodeTypeSchema) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Record<string, unknown>) => void;
  selectNode: (nodeId: string | null) => void;

  // Actions - Edge management
  selectEdge: (edgeId: string | null) => void;
  removeEdge: (edgeId: string) => void;

  // Actions - Workflow
  setWorkflow: (workflow: { id: string; name: string; description?: string; nodes: Node[]; edges: Edge[] }) => void;
  clearWorkflow: () => void;
  getWorkflowJson: () => object;

  // Actions - Node registry
  setNodeTypes: (types: NodeTypeSchema[]) => void;

  // Actions - Execution
  setRunning: (running: boolean) => void;
  setNodeState: (nodeId: string, state: NodeState) => void;
  resetNodeStates: () => void;
  setEdgeState: (fromNode: string, fromPort: string, toNode: string, toPort: string, state: EdgeState) => void;
  resetEdgeStates: () => void;
  addLog: (log: Omit<LogEntry, 'timestamp'>) => void;
  clearLogs: () => void;
  
  // Actions - Node outputs
  setNodeOutput: (nodeId: string, output: unknown) => void;
  clearNodeOutputs: () => void;
}

let nodeIdCounter = 1;

function generateNodeId(nodeType: string): string {
  return `${nodeType.toLowerCase().replace('node', '')}_${nodeIdCounter++}`;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  workflowId: 'new-workflow',
  workflowName: 'New Workflow',
  workflowDescription: '',
  nodes: [],
  edges: [],
  selectedNodeId: null,
  selectedEdgeId: null,
  nodeTypes: [],
  nodeTypesLoaded: false,
  isRunning: false,
  nodeStates: {},
  edgeStates: {},
  logs: [],
  nodeOutputs: {},

  // React Flow handlers
  onNodesChange: (changes) => {
    set((state) => ({
      nodes: applyNodeChanges(changes, state.nodes),
    }));
  },

  onEdgesChange: (changes) => {
    set((state) => ({
      edges: applyEdgeChanges(changes, state.edges),
    }));
  },

  onConnect: (connection: Connection) => {
    if (!connection.source || !connection.target) return;
    
    // n8n 스타일: 단순화된 단일 포트 연결 (output -> input)
    // 포트 타입 체크는 내부적으로 유지하되 연결 차단은 하지 않음
    const sourceNode = get().nodes.find((n) => n.id === connection.source);
    const targetNode = get().nodes.find((n) => n.id === connection.target);
    
    // 포트 타입 호환성 체크 (경고용, 메타데이터에서 첫 번째 포트 사용)
    const sourceNodeType = sourceNode?.data.nodeType as string;
    const targetNodeType = targetNode?.data.nodeType as string;
    const sourceSchema = get().nodeTypes.find((t) => t.node_type === sourceNodeType);
    const targetSchema = get().nodeTypes.find((t) => t.node_type === targetNodeType);
    
    // 단일 포트이므로 첫 번째 output/input 포트 타입 사용
    const sourceType = sourceSchema?.outputs?.[0]?.type;
    const targetType = targetSchema?.inputs?.[0]?.type;
    
    // Check port type compatibility (for warning only, not blocking)
    const isValid = isPortCompatible(sourceType, targetType);
    
    const newEdge: Edge = {
      id: `e_${connection.source}_${connection.target}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: 'output',  // 항상 'output'
      targetHandle: 'input',   // 항상 'input'
      type: 'smoothstep',
      animated: false,
      style: {
        stroke: getEdgeColor(isValid),
        strokeWidth: isValid ? 1 : 2,
      },
      data: {
        isValid,
        fromType: sourceType,
        toType: targetType,
      },
    };
    
    set((state) => ({
      edges: [...state.edges, newEdge],
    }));
    
    // Log warning if types are incompatible (but don't block connection)
    if (!isValid && sourceType && targetType) {
      get().addLog({
        level: 'warning',
        message: `⚠️ Type mismatch: ${sourceType} → ${targetType}`,
      });
    }
  },

  // Node management
  addNode: (nodeType, category, position, schema) => {
    const id = generateNodeId(nodeType);
    
    // Build config data from schema defaults
    const configData: Record<string, unknown> = {};
    if (schema?.config_schema) {
      for (const [key, field] of Object.entries(schema.config_schema)) {
        if (field.default !== undefined) {
          configData[key] = field.default;
        } else if (field.type === 'string') {
          configData[key] = '';
        } else if (field.type === 'number' || field.type === 'integer') {
          configData[key] = 0;
        } else if (field.type === 'boolean') {
          configData[key] = false;
        } else if (field.type === 'array') {
          configData[key] = [];
        } else if (field.type === 'object') {
          configData[key] = {};
        }
      }
    }
    
    // Use 'displayNode' type for DisplayNode (renders inline chart)
    const reactFlowNodeType = nodeType === 'DisplayNode' ? 'displayNode' : 'customNode';
    
    // Set initial size for DisplayNode (for NodeResizer)
    const nodeStyle = nodeType === 'DisplayNode' 
      ? { width: Number(configData.width) || 300, height: Number(configData.height) || 200 }
      : undefined;
    
    const newNode: Node = {
      id,
      type: reactFlowNodeType,
      position,
      ...(nodeStyle && { style: nodeStyle }),
      data: {
        label: nodeType,
        nodeType,
        category,
        inputs: schema?.inputs || [],
        outputs: schema?.outputs || [],
        configSchema: schema?.config_schema || {},
        ...configData,
      },
    };
    set((state) => ({
      nodes: [...state.nodes, newNode],
    }));
    get().addLog({ level: 'info', message: `Added node: ${nodeType} (${id})` });
  },

  removeNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    }));
    get().addLog({ level: 'info', message: `Removed node: ${nodeId}` });
  },

  updateNodeData: (nodeId, data) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
      ),
    }));
  },

  selectNode: (nodeId) => {
    set({ selectedNodeId: nodeId, selectedEdgeId: null });
  },

  // Edge management
  selectEdge: (edgeId) => {
    set({ selectedEdgeId: edgeId, selectedNodeId: null });
  },

  removeEdge: (edgeId) => {
    const edge = get().edges.find((e) => e.id === edgeId);
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== edgeId),
      selectedEdgeId: state.selectedEdgeId === edgeId ? null : state.selectedEdgeId,
    }));
    if (edge) {
      get().addLog({ level: 'info', message: `Removed edge: ${edge.source} → ${edge.target}` });
    }
  },

  // Workflow management
  setWorkflow: (workflow) => {
    // Update nodeIdCounter based on existing nodes
    const maxId = workflow.nodes.reduce((max, node) => {
      const match = node.id.match(/_(\d+)$/);
      if (match) {
        return Math.max(max, parseInt(match[1], 10));
      }
      return max;
    }, 0);
    nodeIdCounter = maxId + 1;

    set({
      workflowId: workflow.id,
      workflowName: workflow.name,
      workflowDescription: workflow.description || '',
      nodes: workflow.nodes,
      edges: workflow.edges,
      selectedNodeId: null,
      selectedEdgeId: null,
    });
    get().addLog({ level: 'success', message: `Loaded workflow: ${workflow.name}` });
  },

  clearWorkflow: () => {
    nodeIdCounter = 1;
    set({
      workflowId: 'new-workflow',
      workflowName: 'New Workflow',
      workflowDescription: '',
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedEdgeId: null,
      nodeStates: {},
    });
    get().addLog({ level: 'info', message: 'Cleared workflow' });
  },

  getWorkflowJson: () => {
    const state = get();
    return {
      id: state.workflowId,
      name: state.workflowName,
      description: state.workflowDescription,
      nodes: state.nodes.map((node) => {
        const baseNode = {
          id: node.id,
          type: node.data.nodeType,
          category: node.data.category,
          position: node.position,
          ...Object.fromEntries(
            Object.entries(node.data).filter(
              ([key]) => !['label', 'nodeType', 'category', 'inputs', 'outputs', 'state', 'configSchema'].includes(key)
            )
          ),
        };
        
        // Add size for DisplayNode
        if (node.data.nodeType === 'DisplayNode' && (node.data.width || node.data.height)) {
          return {
            ...baseNode,
            size: {
              width: node.data.width || 300,
              height: node.data.height || 200,
            },
          };
        }
        
        return baseNode;
      }),
      // DSL format: from/to with port as "nodeId.port" or just "nodeId"
      edges: state.edges.map((edge) => {
        const from = edge.sourceHandle ? `${edge.source}.${edge.sourceHandle}` : edge.source;
        const to = edge.targetHandle ? `${edge.target}.${edge.targetHandle}` : edge.target;
        return {
          from,
          to,
        };
      }),
    };
  },

  // Node registry
  setNodeTypes: (types) => {
    set({ nodeTypes: types, nodeTypesLoaded: true });
  },

  // Execution
  setRunning: (running) => {
    set({ isRunning: running });
    if (running) {
      get().resetNodeStates();
    }
  },

  setNodeState: (nodeId, state) => {
    set((s) => ({
      nodeStates: { ...s.nodeStates, [nodeId]: state },
      nodes: s.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, state } } : node
      ),
    }));
  },

  resetNodeStates: () => {
    set((state) => ({
      nodeStates: {},
      nodes: state.nodes.map((node) => ({
        ...node,
        data: { ...node.data, state: undefined },
      })),
    }));
  },

  setEdgeState: (fromNode, fromPort, toNode, toPort, state) => {
    // Generate edge key matching the edge ID format
    const edgeKey = `${fromNode}.${fromPort}→${toNode}.${toPort}`;
    set((s) => {
      // Find matching edge and update its animated/style properties
      const updatedEdges = s.edges.map((edge) => {
        // Match by source/target nodes (port matching is optional)
        if (edge.source === fromNode && edge.target === toNode) {
          const isActive = state === 'transmitting';
          const isComplete = state === 'transmitted';
          return {
            ...edge,
            animated: isActive,
            style: {
              ...edge.style,
              stroke: isActive ? '#3b82f6' : isComplete ? '#22c55e' : '#4b5563',
              strokeWidth: isActive ? 3 : isComplete ? 2 : 1,
              filter: isActive ? 'drop-shadow(0 0 6px #3b82f6)' : undefined,
            },
          };
        }
        return edge;
      });
      return {
        edgeStates: { ...s.edgeStates, [edgeKey]: state },
        edges: updatedEdges,
      };
    });
  },

  resetEdgeStates: () => {
    set((state) => ({
      edgeStates: {},
      edges: state.edges.map((edge) => ({
        ...edge,
        animated: false,
        style: {
          ...edge.style,
          stroke: '#4b5563',
          strokeWidth: 1,
        },
      })),
    }));
  },

  addLog: (log) => {
    set((state) => ({
      logs: [
        ...state.logs,
        {
          ...log,
          timestamp: new Date(),
        },
      ],
    }));
  },

  clearLogs: () => {
    set({ logs: [] });
  },

  // Node output management
  setNodeOutput: (nodeId, output) => {
    set((state) => ({
      nodeOutputs: { ...state.nodeOutputs, [nodeId]: output },
      // 노드 데이터에도 lastOutput 추가 (프리뷰용)
      nodes: state.nodes.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, lastOutput: output } }
          : n
      ),
    }));
  },

  clearNodeOutputs: () => {
    set((state) => ({
      nodeOutputs: {},
      nodes: state.nodes.map((n) => ({
        ...n,
        data: { ...n.data, lastOutput: undefined },
      })),
    }));
  },
}));
