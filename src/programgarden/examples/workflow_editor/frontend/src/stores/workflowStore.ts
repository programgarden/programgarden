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
import { NodeState, EdgeState, LogEntry, NodeTypeSchema, PortDefinition } from '@/types/workflow';
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

  // Node registry
  nodeTypes: NodeTypeSchema[];
  nodeTypesLoaded: boolean;

  // Execution state
  isRunning: boolean;
  nodeStates: Record<string, NodeState>;
  edgeStates: Record<string, EdgeState>;
  logs: LogEntry[];

  // Actions - React Flow
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;

  // Actions - Node management
  addNode: (nodeType: string, category: string, position: { x: number; y: number }, schema?: NodeTypeSchema) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Record<string, unknown>) => void;
  selectNode: (nodeId: string | null) => void;

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
  nodeTypes: [],
  nodeTypesLoaded: false,
  isRunning: false,
  nodeStates: {},
  edgeStates: {},
  logs: [],

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
    
    // Get source and target nodes
    const sourceNode = get().nodes.find((n) => n.id === connection.source);
    const targetNode = get().nodes.find((n) => n.id === connection.target);
    
    // Get port types from node type schemas
    const sourceNodeType = sourceNode?.data.nodeType as string;
    const targetNodeType = targetNode?.data.nodeType as string;
    const sourceSchema = get().nodeTypes.find((t) => t.node_type === sourceNodeType);
    const targetSchema = get().nodeTypes.find((t) => t.node_type === targetNodeType);
    
    const sourcePort = sourceSchema?.outputs?.find((o: PortDefinition) => o.name === connection.sourceHandle);
    const targetPort = targetSchema?.inputs?.find((i: PortDefinition) => i.name === connection.targetHandle);
    
    const sourceType = sourcePort?.type;
    const targetType = targetPort?.type;
    
    // Check port type compatibility
    const isValid = isPortCompatible(sourceType, targetType);
    
    const newEdge: Edge = {
      id: `e_${connection.source}_${connection.target}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      type: 'smoothstep',
      animated: false,
      // Style based on compatibility
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
    
    // Log warning if types are incompatible
    if (!isValid) {
      get().addLog({
        level: 'warning',
        message: `⚠️ Type mismatch: ${sourceType || 'unknown'} → ${targetType || 'unknown'}`,
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
    set({ selectedNodeId: nodeId });
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
}));
