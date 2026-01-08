import { useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { getCategoryColor } from '@/utils/nodeColors';
import { Trash2, Info, Plus } from 'lucide-react';
import { ConfigField } from '@/types/workflow';
import { useCredentials } from '@/hooks/useCredentials';
import { CredentialModal } from './CredentialModal';

// Map node types to their required credential types
const NODE_CREDENTIAL_TYPES: Record<string, string> = {
  'BrokerNode': 'broker_ls',
  'AlertNode': 'telegram',
  // Add more mappings as needed
};

export default function PropertiesPanel() {
  const { nodes, selectedNodeId, updateNodeData, removeNode } = useWorkflowStore();
  const { credentials, credentialTypes, createCredential, loading: credLoading } = useCredentials();
  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const [credentialTypeForModal, setCredentialTypeForModal] = useState<string | undefined>();

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

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
  const configSchema = (nodeData.configSchema || {}) as Record<string, ConfigField>;

  const handleLabelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateNodeData(selectedNode.id, { label: e.target.value });
  };

  const handleDelete = () => {
    if (confirm(`Delete node "${nodeData.label || nodeData.nodeType}"?`)) {
      removeNode(selectedNode.id);
    }
  };

  // Get the credential type required by this node
  const nodeType = nodeData.nodeType as string;
  const requiredCredentialType = NODE_CREDENTIAL_TYPES[nodeType];
  const filteredCredentials = requiredCredentialType 
    ? credentials.filter(c => c.credential_type === requiredCredentialType)
    : [];

  const handleOpenCredentialModal = () => {
    setCredentialTypeForModal(requiredCredentialType);
    setShowCredentialModal(true);
  };

  const handleSaveCredential = async (data: { name: string; credential_type: string; data: Record<string, unknown> }) => {
    const result = await createCredential(data);
    if (result) {
      // Auto-select the newly created credential
      updateNodeData(selectedNode.id, { credential_id: result.id });
    }
  };

  // Render credential dropdown for credential_id field
  const renderCredentialField = (key: string, schema: ConfigField, value: unknown) => {
    if (!requiredCredentialType) {
      // No credential type mapping, fall back to text input
      return renderTextField(key, schema, value);
    }

    return (
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Credential
          {schema.required && <span className="text-red-400 ml-1">*</span>}
        </label>
        <div className="flex gap-2">
          <select
            value={String(value || '')}
            onChange={(e) => updateNodeData(selectedNode.id, { [key]: e.target.value })}
            className="flex-1 px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            disabled={credLoading}
          >
            <option value="">Select credential...</option>
            {filteredCredentials.map(cred => (
              <option key={cred.id} value={cred.id}>
                {cred.name}
              </option>
            ))}
          </select>
          <button
            onClick={handleOpenCredentialModal}
            className="px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1"
            title="Add new credential"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
        {filteredCredentials.length === 0 && !credLoading && (
          <p className="text-xs text-gray-500 mt-1">
            No credentials found. Click + to add one.
          </p>
        )}
      </div>
    );
  };

  // Render text field (extracted for reuse)
  const renderTextField = (key: string, schema: ConfigField, value: unknown) => (
    <div>
      <label className="block text-xs text-gray-400 mb-1 capitalize">
        {key.replace(/_/g, ' ')}
        {schema.required && <span className="text-red-400 ml-1">*</span>}
        {schema.description && (
          <span className="text-gray-500 ml-1" title={schema.description}>ⓘ</span>
        )}
      </label>
      <input
        type="text"
        value={String(value ?? '')}
        onChange={(e) => updateNodeData(selectedNode.id, { [key]: e.target.value })}
        placeholder={schema.description}
        className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
      />
    </div>
  );

  // Render form field based on schema type
  const renderField = (key: string, schema: ConfigField, value: unknown) => {
    const fieldType = schema.type;
    const isRequired = schema.required;
    
    // Special handling for credential_id field
    if (key === 'credential_id') {
      return renderCredentialField(key, schema, value);
    }
    
    // Boolean: checkbox
    if (fieldType === 'boolean') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => updateNodeData(selectedNode.id, { [key]: e.target.checked })}
            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <span className="text-sm text-gray-300">{key.replace(/_/g, ' ')}</span>
          {isRequired && <span className="text-red-400 text-xs">*</span>}
        </label>
      );
    }
    
    // Number
    if (fieldType === 'number' || fieldType === 'integer') {
      return (
        <div>
          <label className="block text-xs text-gray-400 mb-1 capitalize">
            {key.replace(/_/g, ' ')}
            {isRequired && <span className="text-red-400 ml-1">*</span>}
            {schema.description && (
              <span className="text-gray-500 ml-1" title={schema.description}>ⓘ</span>
            )}
          </label>
          <input
            type="number"
            value={typeof value === 'number' ? value : 0}
            step={fieldType === 'integer' ? 1 : 0.01}
            onChange={(e) => {
              const num = fieldType === 'integer' 
                ? parseInt(e.target.value) || 0 
                : parseFloat(e.target.value) || 0;
              updateNodeData(selectedNode.id, { [key]: num });
            }}
            className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
        </div>
      );
    }
    
    // Array or Object: textarea for JSON
    if (fieldType === 'array' || fieldType === 'object') {
      const jsonValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : '[]';
      return (
        <div>
          <label className="block text-xs text-gray-400 mb-1 capitalize">
            {key.replace(/_/g, ' ')}
            {isRequired && <span className="text-red-400 ml-1">*</span>}
            {schema.description && (
              <span className="text-gray-500 ml-1" title={schema.description}>ⓘ</span>
            )}
          </label>
          <textarea
            value={jsonValue}
            rows={3}
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value);
                updateNodeData(selectedNode.id, { [key]: parsed });
              } catch {
                // Invalid JSON, don't update
              }
            }}
            className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>
      );
    }
    
    // Default: text input
    return (
      <div>
        <label className="block text-xs text-gray-400 mb-1 capitalize">
          {key.replace(/_/g, ' ')}
          {isRequired && <span className="text-red-400 ml-1">*</span>}
          {schema.description && (
            <span className="text-gray-500 ml-1" title={schema.description}>ⓘ</span>
          )}
        </label>
        <input
          type="text"
          value={String(value ?? '')}
          onChange={(e) => updateNodeData(selectedNode.id, { [key]: e.target.value })}
          placeholder={schema.description}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
        />
      </div>
    );
  };

  // Get config fields from schema
  const hasConfigSchema = Object.keys(configSchema).length > 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-200">Properties</h2>
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
          {nodeData.nodeType as string}
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Label */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Label</label>
          <input
            type="text"
            value={(nodeData.label as string) || ''}
            onChange={handleLabelChange}
            placeholder={nodeData.nodeType as string}
            className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Config Fields from Schema */}
        {hasConfigSchema && (
          <>
            <div className="border-t border-gray-700 pt-4">
              <h3 className="text-xs font-semibold text-gray-400 mb-3">Configuration</h3>
            </div>
            {Object.entries(configSchema).map(([key, schema]) => (
              <div key={key}>
                {renderField(key, schema, nodeData[key])}
              </div>
            ))}
          </>
        )}

        {/* Inputs/Outputs Info */}
        <div className="border-t border-gray-700 pt-4">
          <h3 className="text-xs font-semibold text-gray-400 mb-2">Ports</h3>
          <div className="space-y-2">
            {(nodeData.inputs as { name: string; type: string }[] | undefined)?.map((input) => (
              <div key={input.name} className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span className="text-gray-300">{input.name}</span>
                <span className="text-gray-500">({input.type})</span>
              </div>
            ))}
            {(nodeData.outputs as { name: string; type: string }[] | undefined)?.map((output) => (
              <div key={output.name} className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                <span className="text-gray-300">{output.name}</span>
                <span className="text-gray-500">({output.type})</span>
              </div>
            ))}
          </div>
        </div>
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
