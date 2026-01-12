import { useState, useMemo, useCallback, useRef } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { getCategoryColor } from '@/utils/nodeColors';
import { getNodeLabel } from '@/utils/nodeLabels';
import { findUpstreamNodes } from '@/utils/graphUtils';
import { Trash2, Info } from 'lucide-react';
import { ConfigField } from '@/types/workflow';
import { useCredentials } from '@/hooks/useCredentials';
import { usePlugins, getDefaultFieldsFromSchema } from '@/hooks/usePlugins';
import { CredentialModal } from './CredentialModal';
import InputTab from './InputTab';
import OutputTab from './OutputTab';
import BindableField from './BindableField';
import PluginFieldsGroup from './PluginFieldsGroup';

// Map node types to their required credential types
const NODE_CREDENTIAL_TYPES: Record<string, string> = {
  'BrokerNode': 'broker_ls',
  'AlertNode': 'telegram',
  'TelegramNode': 'telegram',
  'PostgresNode': 'postgres',
};

// Tab button component
function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
        active
          ? 'text-white border-b-2 border-blue-500'
          : 'text-gray-400 hover:text-gray-200'
      }`}
    >
      {children}
    </button>
  );
}

export default function PropertiesPanel() {
  const [activeTab, setActiveTab] = useState<'input' | 'parameters' | 'settings' | 'output'>('parameters');
  const { nodes, edges, selectedNodeId, updateNodeData, removeNode, nodeOutputs, addCredential } = useWorkflowStore();
  const { credentials, credentialTypes, createCredential, loading: credLoading } = useCredentials();
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const [credentialTypeForModal, setCredentialTypeForModal] = useState<string | undefined>();
  const { getPluginsForNodeType, getPluginSchema } = usePlugins();
  
  // useRef로 마지막 포커스된 필드 기억 (탭 전환해도 유지)
  const lastFocusedFieldRef = useRef<string | null>(null);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  // 이전 노드들 찾기
  const upstreamNodes = useMemo(() => {
    if (!selectedNodeId) return [];
    return findUpstreamNodes(selectedNodeId, nodes, edges);
  }, [selectedNodeId, nodes, edges]);

  // 이전 노드들의 출력값
  const inputData = useMemo(() => {
    return upstreamNodes.reduce((acc, node) => {
      if (nodeOutputs[node.id]) {
        acc[node.id] = nodeOutputs[node.id];
      }
      return acc;
    }, {} as Record<string, unknown>);
  }, [upstreamNodes, nodeOutputs]);

  // configSchema를 selectedNode에서 가져오기
  const configSchema = useMemo(() => {
    if (!selectedNode) return {} as Record<string, ConfigField>;
    return ((selectedNode.data as Record<string, unknown>).configSchema || {}) as Record<string, ConfigField>;
  }, [selectedNode]);

  // 필드 클릭 핸들러 (Input 탭에서 필드 클릭 시)
  const handleFieldClick = useCallback((expression: string) => {
    // lastFocusedFieldRef가 있으면 해당 필드에 삽입
    if (lastFocusedFieldRef.current && selectedNode) {
      updateNodeData(selectedNode.id, { [lastFocusedFieldRef.current]: expression });
    } else {
      // 클립보드에 복사
      navigator.clipboard.writeText(expression);
    }
  }, [selectedNode, updateNodeData]);
  
  // 필드 포커스 핸들러
  const handleFieldFocus = useCallback((fieldKey: string) => {
    lastFocusedFieldRef.current = fieldKey;
  }, []);

  if (!selectedNode) {
    return (
      <div className="h-full p-4">
        <h2 className="text-sm font-semibold text-gray-200 mb-4">Properties</h2>
        <div className="flex flex-col items-center justify-center h-32 text-gray-500">
          <Info className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-sm text-center">Select a node to edit its properties</p>
        </div>
      </div>
    );
  }

  const nodeData = selectedNode.data as Record<string, unknown>;
  const color = getCategoryColor(nodeData.category as string);
  
  // 삭제 시 표시할 이름
  const nodeName = (nodeData.customLabel as string) || getNodeLabel(nodeData.nodeType as string, 'ko');

  const handleDelete = () => {
    if (confirm(`"${nodeName}" 노드를 삭제하시겠습니까?`)) {
      removeNode(selectedNode.id);
    }
  };

  // Get the credential type required by this node
  const nodeType = nodeData.nodeType as string;
  const requiredCredentialType = NODE_CREDENTIAL_TYPES[nodeType];

  const handleOpenCredentialModal = useCallback((initialType?: string) => {
    setCredentialTypeForModal(initialType || requiredCredentialType);
    setShowCredentialModal(true);
  }, [requiredCredentialType]);

  const handleSaveCredential = async (data: { name: string; credential_type: string; data: unknown }) => {
    const result = await createCredential(data as { name: string; credential_type: string; data: Record<string, unknown> });
    if (result) {
      // Store credential info in workflow store for JSON export
      addCredential(result.id, {
        type: data.credential_type,
        name: data.name,
        data: data.data,
      });
      // Auto-select the newly created credential
      updateNodeData(selectedNode.id, { credential_id: result.id });
    }
  };
  
  // credential_id 필드 변경 시 store에 credential 정보 등록
  const handleFieldChange = useCallback((fieldKey: string, value: unknown) => {
    updateNodeData(selectedNode.id, { [fieldKey]: value });
    
    // credential_id 필드인 경우 store에 credential 정보 등록
    if (fieldKey === 'credential_id' && typeof value === 'string' && value) {
      const cred = credentials.find(c => c.id === value);
      if (cred) {
        addCredential(cred.id, {
          type: cred.credential_type,
          name: cred.name,
          data: cred.data,
        });
      }
    }
  }, [selectedNode?.id, updateNodeData, credentials, addCredential]);

  // Get config fields from schema
  const hasConfigSchema = Object.keys(configSchema).length > 0;
  
  // 표시할 라벨 (커스텀 라벨 > 기본 한글 라벨)
  const displayLabel = (nodeData.customLabel as string) || getNodeLabel(nodeData.nodeType as string, 'ko');

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-200">
            {displayLabel}
          </h2>
          <button
            onClick={handleDelete}
            className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors"
            title="Delete node"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        <div
          className="text-xs px-2 py-1 rounded inline-block text-white"
          style={{ backgroundColor: color }}
        >
          {nodeData.category as string}
        </div>
        {/* Node Description */}
        {typeof nodeData.description === 'string' && nodeData.description && (
          <div className="mt-3 p-2 bg-gray-750 rounded border border-gray-600">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-gray-300 leading-relaxed">
                {nodeData.description}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs (4개: Input | Parameters | Settings | Output) */}
      <div className="flex border-b border-gray-700">
        <TabButton active={activeTab === 'input'} onClick={() => setActiveTab('input')}>
          Input
        </TabButton>
        <TabButton active={activeTab === 'parameters'} onClick={() => setActiveTab('parameters')}>
          Parameters
        </TabButton>
        <TabButton active={activeTab === 'settings'} onClick={() => setActiveTab('settings')}>
          Settings
        </TabButton>
        <TabButton active={activeTab === 'output'} onClick={() => setActiveTab('output')}>
          Output
        </TabButton>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'input' && (
          <InputTab 
            inputData={inputData} 
            upstreamNodes={upstreamNodes}
            onFieldClick={handleFieldClick}
            targetField={lastFocusedFieldRef.current}
          />
        )}

        {/* Parameters Tab - 핵심 설정 */}
        {activeTab === 'parameters' && (
          <div className="space-y-4">
            {/* HTTPRequestNode URL Preview */}
            {nodeType === 'HTTPRequestNode' && nodeData.url ? (
              <div className="p-3 bg-gray-900 rounded border border-gray-700">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400">🔗 Request URL</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                    nodeData.method === 'GET' ? 'bg-green-900 text-green-300' :
                    nodeData.method === 'POST' ? 'bg-blue-900 text-blue-300' :
                    nodeData.method === 'PUT' ? 'bg-yellow-900 text-yellow-300' :
                    nodeData.method === 'DELETE' ? 'bg-red-900 text-red-300' :
                    'bg-gray-700 text-gray-300'
                  }`}>
                    {String(nodeData.method || 'GET')}
                  </span>
                </div>
                <code className="text-xs text-cyan-400 break-all">
                  {(() => {
                    const baseUrl = String(nodeData.url || '');
                    const params = nodeData.query_params as Record<string, string> | undefined;
                    if (!params || Object.keys(params).length === 0) return baseUrl;
                    const queryString = Object.entries(params)
                      .filter(([k, v]) => k && v)
                      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
                      .join('&');
                    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
                  })()}
                </code>
              </div>
            ) : null}
            
            {hasConfigSchema && (() => {
              const paramFields = Object.entries(configSchema).filter(
                ([, schema]) => schema.category === 'parameters' || !schema.category
              );
              
              if (paramFields.length === 0) {
                return (
                  <div className="text-center text-gray-500 py-8">
                    <p className="text-sm">No parameters for this node</p>
                  </div>
                );
              }
              
              // 현재 노드 타입에 맞는 플러그인 목록
              const availablePlugins = getPluginsForNodeType(nodeType);
              // 플러그인 사용 노드인지 확인
              const isPluginNode = ['ConditionNode', 'NewOrderNode', 'ModifyOrderNode', 'CancelOrderNode'].includes(nodeType);
              const currentPluginId = nodeData.plugin as string | undefined;
              
              // fields 필드는 PluginFieldsGroup에서 처리하므로 제외
              const filteredParamFields = isPluginNode 
                ? paramFields.filter(([key]) => key !== 'fields')
                : paramFields;
              
              return (
                <>
                  {filteredParamFields.map(([key, schema]) => (
                    <div key={key}>
                      <BindableField
                        label={key.replace(/_/g, ' ')}
                        fieldKey={key}
                        value={nodeData[key]}
                        onChange={(value) => handleFieldChange(key, value)}
                        onFocus={() => handleFieldFocus(key)}
                        schema={schema}
                        // Credential props (credential_id 필드용)
                        credentials={credentials}
                        credentialTypes={credentialTypes}
                        onOpenCredentialModal={handleOpenCredentialModal}
                        credentialLoading={credLoading}
                        requiredCredentialType={requiredCredentialType}
                        // WatchlistNode용 (symbol_editor)
                        nodeData={nodeData}
                        onNodeDataChange={handleFieldChange}
                        // Plugin 관련 props (plugin 필드용)
                        availablePlugins={availablePlugins}
                        onPluginChange={async (pluginId) => {
                          // 플러그인 변경 시 fields 완전 초기화 후 새 기본값 설정
                          handleFieldChange('plugin', pluginId);
                          // 플러그인 스키마 가져와서 기본값 설정
                          const pluginSchema = await getPluginSchema(pluginId);
                          if (pluginSchema?.fields_schema) {
                            const defaultFields = getDefaultFieldsFromSchema(pluginSchema.fields_schema);
                            // 기존 fields를 완전히 교체 (새 플러그인 기본값으로)
                            handleFieldChange('fields', defaultFields);
                          } else {
                            handleFieldChange('fields', {});
                          }
                        }}
                      />
                    </div>
                  ))}
                  
                  {/* 플러그인 필드 그룹 - 플러그인이 선택되었을 때만 표시 */}
                  {isPluginNode && currentPluginId && (
                    <PluginFieldsGroup
                      pluginId={currentPluginId}
                      fields={(nodeData.fields as Record<string, unknown>) || {}}
                      onChange={(newFields) => handleFieldChange('fields', newFields)}
                      locale="en"  // 기본 영어, 향후 사용자 설정으로 변경 가능
                    />
                  )}
                  
                  {/* 플러그인 미선택 안내 */}
                  {isPluginNode && !currentPluginId && (
                    <div className="mt-4 p-3 bg-amber-900/20 border border-amber-700/50 rounded text-amber-400 text-sm">
                      <p className="flex items-center gap-2">
                        <span>💡</span>
                        <span>Select a plugin above to configure its parameters</span>
                      </p>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* Settings Tab - 부가 설정 */}
        {activeTab === 'settings' && (
          <div className="space-y-4">
            {hasConfigSchema && (() => {
              const settingsFields = Object.entries(configSchema).filter(
                ([, schema]) => schema.category === 'settings'
              );
              
              if (settingsFields.length === 0) {
                return (
                  <div className="text-center text-gray-500 py-8">
                    <p className="text-sm">No settings for this node</p>
                  </div>
                );
              }
              
              return settingsFields.map(([key, schema]) => (
                <div key={key}>
                  <BindableField
                    label={key.replace(/_/g, ' ')}
                    fieldKey={key}
                    value={nodeData[key]}
                    onChange={(value) => handleFieldChange(key, value)}
                    onFocus={() => handleFieldFocus(key)}
                    schema={schema}
                    // Credential props (credential_id 필드용)
                    credentials={credentials}
                    credentialTypes={credentialTypes}
                    onOpenCredentialModal={handleOpenCredentialModal}
                    credentialLoading={credLoading}
                    requiredCredentialType={requiredCredentialType}
                  />
                </div>
              ));
            })()}

            {/* Inputs/Outputs Info */}
            <div className="border-t border-gray-700 pt-4 mt-4">
              <h3 className="text-xs font-semibold text-gray-400 mb-2">Ports</h3>
              <div className="space-y-2">
                {(nodeData.inputs as { name: string; type: string }[] | undefined)?.map(
                  (input) => (
                    <div key={input.name} className="flex items-center gap-2 text-xs">
                      <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                      <span className="text-gray-300">{input.name}</span>
                      <span className="text-gray-500">({input.type})</span>
                    </div>
                  )
                )}
                {(nodeData.outputs as { name: string; type: string }[] | undefined)?.map(
                  (output) => (
                    <div key={output.name} className="flex items-center gap-2 text-xs">
                      <span className="w-2 h-2 rounded-full bg-green-500"></span>
                      <span className="text-gray-300">{output.name}</span>
                      <span className="text-gray-500">({output.type})</span>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'output' && <OutputTab output={nodeOutputs[selectedNodeId!]} />}
      </div>

      {/* Credential Modal */}
      <CredentialModal
        isOpen={showCredentialModal}
        onClose={() => setShowCredentialModal(false)}
        onSave={handleSaveCredential}
        credentialTypes={credentialTypes}
        initialType={credentialTypeForModal}
      />
    </div>
  );
}
