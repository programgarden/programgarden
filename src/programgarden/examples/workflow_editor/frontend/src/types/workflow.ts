export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
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
  category?: 'parameters' | 'settings' | 'advanced';  // Field category for UI grouping
  enum_values?: string[];
  enum_labels?: Record<string, string>;  // enum 값에 대한 라벨 (예: {"overseas_stock": "해외주식"})
  bindable?: boolean;
  expression_enabled?: boolean;
  ui_component?: string;  // Custom UI component (e.g., 'symbol_editor')
  ui_hint?: string;       // UI hint for special behavior (e.g., 'port_binding:price_data')
  placeholder?: string;   // Input placeholder text
  
  // === 바인딩 가이드 필드 (신규) ===
  example?: unknown;              // 예시 값 (JSON 직접 입력 시 참고)
  example_binding?: string;       // 바인딩 표현식 예시 ({{ nodes.xxx.yyy }})
  bindable_sources?: string[];    // 바인딩 가능한 소스 노드/포트 목록
  expected_type?: string;         // 기대하는 데이터 타입 (예: dict[str, float])
  
  // === 조건부 표시 필드 ===
  visible_when?: Record<string, unknown>;  // 조건부 표시 조건 (예: {"product": "overseas_stock"})
  depends_on?: Record<string, string[]>;   // chart_type별 필드 표시 조건 (예: {"chart_type": ["line", "bar"]})
  
  // === 고급 옵션 필드 ===
  collapsed?: boolean;    // 기본적으로 접혀있는 필드
  help_text?: string;     // 추가 도움말 텍스트
  group?: string;         // 필드 그룹 (예: 'field_mapping')
}

export interface NodeTypeSchema {
  node_type: string;
  category: string;
  description: string;
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  config_schema: Record<string, ConfigField>;
}

export interface CategoryInfo {
  id: string;
  name: string;
  description: string;
  count: number;
}

export interface WorkflowNodeData {
  label?: string;
  nodeType: string;
  category: string;
  inputs?: PortDefinition[];
  outputs?: PortDefinition[];
  state?: NodeState;
  lastOutput?: unknown; // 마지막 실행 출력값 (프리뷰용)
  // DisplayNode specific
  width?: number;
  height?: number;
  chart_type?: string;
  title?: string;
  [key: string]: unknown;
}

export interface WorkflowNode {
  id: string;
  type: string;
  category: string;
  position: Position;
  size?: Size;  // For DisplayNode sizing
  data: WorkflowNodeData;
}

// DSL Edge format (execution order only)
export interface DslEdge {
  from: string;  // source node ID
  to: string;    // target node ID
  description?: string;
}

// React Flow Edge format (source/target) - internal use
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
