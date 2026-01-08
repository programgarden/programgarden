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
import { NodeState, LogEntry, NodeTypeSchema } from '@/types/workflow';

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
    
    const newEdge: Edge = {
      id: `e_${connection.source}_${connection.target}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      type: 'smoothstep',
      animated: false,
    };
    set((state) => ({
      edges: [...state.edges, newEdge],
    }));
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
    
    const newNode: Node = {
      id,
      type: 'customNode',
      position,
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
      nodes: state.nodes.map((node) => ({
        id: node.id,
        type: node.data.nodeType,
        category: node.data.category,
        position: node.position,
        ...Object.fromEntries(
          Object.entries(node.data).filter(
            ([key]) => !['label', 'nodeType', 'category', 'inputs', 'outputs', 'state'].includes(key)
          )
        ),
      })),
      edges: state.edges.map((edge) => ({
        from: edge.source,
        to: edge.target,
        ...(edge.sourceHandle && { from_port: edge.sourceHandle }),
        ...(edge.targetHandle && { to_port: edge.targetHandle }),
      })),
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
