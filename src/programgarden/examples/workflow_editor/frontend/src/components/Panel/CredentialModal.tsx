import { useState, useEffect } from 'react';
import { Plus, X } from 'lucide-react';
import type { CredentialTypeSchema, CredentialField } from '../../types/workflow';

// Custom credential의 단일 항목 타입
interface CustomCredentialItem {
  type: 'headers' | 'query_params' | 'body';
  key: string;
  value: string;
  label: string;
}

// 타입별 아이콘 및 색상
const TYPE_CONFIG = {
  headers: { icon: '📋', color: 'bg-blue-600', label: 'Header' },
  query_params: { icon: '❓', color: 'bg-green-600', label: 'Query Param' },
  body: { icon: '📦', color: 'bg-purple-600', label: 'Body' },
};

interface CredentialModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: { name: string; credential_type: string; data: unknown }) => Promise<void>;
  credentialTypes: CredentialTypeSchema[];
  initialType?: string;
}

export function CredentialModal({
  isOpen,
  onClose,
  onSave,
  credentialTypes,
  initialType,
}: CredentialModalProps) {
  const [selectedType, setSelectedType] = useState<string>(initialType || '');
  const [name, setName] = useState('');
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // http_custom용 배열 기반 데이터
  const [customItems, setCustomItems] = useState<CustomCredentialItem[]>([]);

  const selectedSchema = credentialTypes.find(t => t.type_id === selectedType);
  const isCustomType = selectedType === 'http_custom';

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedType(initialType || '');
      setName('');
      setFormData({});
      setCustomItems([]);
      setError(null);
    }
  }, [isOpen, initialType]);

  // Set defaults when type changes
  useEffect(() => {
    if (selectedSchema && !isCustomType) {
      const defaults: Record<string, unknown> = {};
      for (const field of selectedSchema.fields) {
        if (field.default !== undefined) {
          defaults[field.key] = field.default;
        } else if (field.field_type === 'boolean') {
          defaults[field.key] = false;
        } else {
          defaults[field.key] = '';
        }
      }
      setFormData(defaults);
    }
  }, [selectedSchema, isCustomType]);

  const handleFieldChange = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  // Custom item 추가
  const addCustomItem = (type: CustomCredentialItem['type']) => {
    setCustomItems(prev => [...prev, { type, key: '', value: '', label: '' }]);
  };

  // Custom item 업데이트
  const updateCustomItem = (index: number, field: keyof CustomCredentialItem, value: string) => {
    setCustomItems(prev => prev.map((item, i) => 
      i === index ? { ...item, [field]: value } : item
    ));
  };

  // Custom item 삭제
  const removeCustomItem = (index: number) => {
    setCustomItems(prev => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!selectedType) {
      setError('Please select a credential type');
      return;
    }
    if (!name.trim()) {
      setError('Please enter a name');
      return;
    }

    // http_custom 타입 검증
    if (isCustomType) {
      const validItems = customItems.filter(item => item.key.trim());
      if (validItems.length === 0) {
        setError('Please add at least one credential field');
        return;
      }
    }

    // Validate required fields for non-custom types
    if (selectedSchema && !isCustomType) {
      for (const field of selectedSchema.fields) {
        if (field.required && !field.key.startsWith('_')) {
          const value = formData[field.key];
          if (value === undefined || value === null || value === '') {
            setError(`Please fill in ${field.label}`);
            return;
          }
        }
      }
    }

    setSaving(true);
    setError(null);
    try {
      let dataToSave: unknown;
      
      if (isCustomType) {
        // http_custom: 배열 기반 데이터 저장 (빈 키 필터링)
        dataToSave = customItems
          .filter(item => item.key.trim())
          .map(item => ({
            type: item.type,
            key: item.key.trim(),
            value: item.value,
            label: item.label.trim() || item.key.trim(), // label이 없으면 key 사용
          }));
      } else {
        dataToSave = formData;
      }

      await onSave({
        name: name.trim(),
        credential_type: selectedType,
        data: dataToSave,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save credential');
    } finally {
      setSaving(false);
    }
  };

  const renderField = (field: CredentialField) => {
    const value = formData[field.key];
    const baseInputClass = "w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500";

    switch (field.field_type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(value)}
              onChange={(e) => handleFieldChange(field.key, e.target.checked)}
              className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-500 focus:ring-blue-500"
            />
            <span className="text-gray-300">{field.label}</span>
          </label>
        );

      case 'password':
        return (
          <input
            type="password"
            value={String(value || '')}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.description || `Enter ${field.label}`}
            className={baseInputClass}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            value={Number(value) || 0}
            onChange={(e) => handleFieldChange(field.key, Number(e.target.value))}
            className={baseInputClass}
          />
        );

      case 'select':
        return (
          <select
            value={String(value || '')}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            className={baseInputClass}
          >
            <option value="">Select...</option>
            {field.options?.map((opt: string) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        );

      default:
        return (
          <input
            type="text"
            value={String(value || '')}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.description || `Enter ${field.label}`}
            className={baseInputClass}
          />
        );
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Add Credential</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Error message */}
          {error && (
            <div className="bg-red-900/30 text-red-400 px-3 py-2 rounded text-sm">
              {error}
            </div>
          )}

          {/* Credential Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Credential Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              disabled={!!initialType}
            >
              <option value="">Select a type...</option>
              {credentialTypes.map(type => (
                <option key={type.type_id} value={type.type_id}>
                  {type.icon} {type.name}
                </option>
              ))}
            </select>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My API Credential"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Type-specific fields (non-custom types) */}
          {selectedSchema && !isCustomType && (
            <div className="space-y-3 pt-2 border-t border-gray-700">
              <p className="text-sm text-gray-400">{selectedSchema.description}</p>
              {selectedSchema.fields
                .filter(f => !f.key.startsWith('_'))
                .map((field: CredentialField) => (
                <div key={field.key}>
                  {field.field_type !== 'boolean' && (
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      {field.label}
                      {field.required && <span className="text-red-400 ml-1">*</span>}
                    </label>
                  )}
                  {renderField(field)}
                  {field.description && field.field_type !== 'boolean' && (
                    <p className="text-xs text-gray-500 mt-1">{field.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Custom HTTP Credential - Array-based UI */}
          {isCustomType && (
            <div className="space-y-3 pt-2 border-t border-gray-700">
              <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-3">
                <p className="text-sm text-blue-300">
                  💡 <strong>Custom Credential</strong>: 아래 버튼으로 Headers, Query Params, Body 필드를 추가하세요. 
                  워크플로우 JSON에는 credential ID만 저장됩니다.
                </p>
              </div>

              {/* Add buttons */}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => addCustomItem('headers')}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  📋 Header
                </button>
                <button
                  onClick={() => addCustomItem('query_params')}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  ❓ Query Param
                </button>
                <button
                  onClick={() => addCustomItem('body')}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  📦 Body
                </button>
              </div>

              {/* Items list */}
              {customItems.length === 0 ? (
                <p className="text-xs text-gray-500 italic text-center py-4">
                  No fields added. Click buttons above to add credential fields.
                </p>
              ) : (
                <div className="space-y-3">
                  {customItems.map((item, index) => {
                    const config = TYPE_CONFIG[item.type];
                    return (
                      <div 
                        key={index} 
                        className="bg-gray-750 border border-gray-600 rounded-lg p-3 space-y-2"
                      >
                        {/* Item header */}
                        <div className="flex items-center justify-between">
                          <span className={`px-2 py-0.5 text-xs text-white rounded ${config.color}`}>
                            {config.icon} {config.label}
                          </span>
                          <button
                            onClick={() => removeCustomItem(index)}
                            className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                            title="Remove"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>

                        {/* Item fields */}
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-xs text-gray-400 mb-1">Label (표시명)</label>
                            <input
                              type="text"
                              value={item.label}
                              onChange={(e) => updateCustomItem(index, 'label', e.target.value)}
                              placeholder="예: API 인증 토큰"
                              className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-400 mb-1">Key (필드명) *</label>
                            <input
                              type="text"
                              value={item.key}
                              onChange={(e) => updateCustomItem(index, 'key', e.target.value)}
                              placeholder="예: Authorization"
                              className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Value (값) *</label>
                          <input
                            type="password"
                            value={item.value}
                            onChange={(e) => updateCustomItem(index, 'value', e.target.value)}
                            placeholder="민감한 값 입력"
                            className="w-full px-2 py-1.5 bg-gray-700 border border-amber-600/50 rounded text-sm text-amber-300 focus:outline-none focus:border-amber-500"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Summary */}
              {customItems.length > 0 && (
                <div className="flex gap-4 text-xs text-gray-500 pt-2 border-t border-gray-700">
                  <span>📋 Headers: {customItems.filter(i => i.type === 'headers').length}</span>
                  <span>❓ Params: {customItems.filter(i => i.type === 'query_params').length}</span>
                  <span>📦 Body: {customItems.filter(i => i.type === 'body').length}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !selectedType || !name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
