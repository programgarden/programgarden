export interface Position {
  x: number;
  y: number;
}

export interface PortDefinition {
  name: string;
  type: string;
  description?: string;
  required?: boolean;
}

export interface ConfigField {
  type: string;
  required: boolean;
  default?: unknown;
  description?: string;
}

export interface NodeTypeSchema {
  node_type: string;
  category: string;
  description: string;
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  config_schema: Record<string, ConfigField>;
}

export interface WorkflowNodeData {
  label?: string;
  nodeType: string;
  category: string;
  inputs?: PortDefinition[];
  outputs?: PortDefinition[];
  state?: NodeState;
  [key: string]: unknown;
}

export interface WorkflowNode {
  id: string;
  type: string;
  category: string;
  position: Position;
  data: WorkflowNodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  version?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export type NodeState = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type EdgeState = 'idle' | 'transmitting' | 'transmitted';

export interface LogEntry {
  timestamp: Date;
  level: 'info' | 'success' | 'warning' | 'error' | 'node';
  message: string;
  nodeId?: string;
}

export interface CategoryInfo {
  category: string;
  count: number;
  description: string;
}


// ========================================
// Credential Types (n8n style)
// ========================================

export type CredentialFieldType = 'string' | 'password' | 'boolean' | 'number' | 'select';

export interface CredentialField {
  key: string;
  label: string;
  field_type: CredentialFieldType;
  required: boolean;
  default?: unknown;
  description?: string;
  options?: string[];
}

export interface CredentialTypeSchema {
  type_id: string;
  name: string;
  description?: string;
  icon?: string;
  fields: CredentialField[];
  plugin_id?: string;
}

export interface Credential {
  id: string;
  name: string;
  credential_type: string;
  user_id: string;
  data: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}
