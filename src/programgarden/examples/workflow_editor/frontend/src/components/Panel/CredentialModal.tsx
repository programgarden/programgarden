import { useState, useEffect } from 'react';
import type { CredentialTypeSchema, CredentialField } from '../../types/workflow';

interface CredentialModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: { name: string; credential_type: string; data: Record<string, unknown> }) => Promise<void>;
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

  const selectedSchema = credentialTypes.find(t => t.type_id === selectedType);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedType(initialType || '');
      setName('');
      setFormData({});
      setError(null);
    }
  }, [isOpen, initialType]);

  // Set defaults when type changes
  useEffect(() => {
    if (selectedSchema) {
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
  }, [selectedSchema]);

  const handleFieldChange = (key: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [key]: value }));
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

    // Validate required fields
    if (selectedSchema) {
      for (const field of selectedSchema.fields) {
        if (field.required) {
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
      await onSave({
        name: name.trim(),
        credential_type: selectedType,
        data: formData,
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
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
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
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
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
              placeholder="e.g., My LS Securities Account"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Type-specific fields */}
          {selectedSchema && (
            <div className="space-y-3 pt-2 border-t border-gray-700">
              <p className="text-sm text-gray-400">{selectedSchema.description}</p>
              {selectedSchema.fields.map((field: CredentialField) => (
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
