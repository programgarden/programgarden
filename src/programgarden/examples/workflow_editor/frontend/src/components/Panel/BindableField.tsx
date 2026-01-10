import { useState, useRef } from 'react';
import { ConfigField } from '@/types/workflow';

interface BindableFieldProps {
  label: string;
  fieldKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
  onFocus?: () => void;
  schema?: ConfigField;
}

export default function BindableField({ 
  label, 
  fieldKey: _fieldKey,
  value, 
  onChange, 
  onFocus,
  schema 
}: BindableFieldProps) {
  const [isExpression, setIsExpression] = useState(() => {
    return typeof value === 'string' && value.startsWith('{{');
  });
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  
  // 드롭 핸들러
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const expression = e.dataTransfer.getData('text/plain');
    if (expression && expression.startsWith('{{')) {
      onChange(expression);
      setIsExpression(true);
    }
  };
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };
  
  // Expression 모드 토글
  const toggleExpression = () => {
    setIsExpression(!isExpression);
    if (!isExpression) {
      // 일반 → Expression: 기존 값을 그대로 유지
    } else {
      // Expression → 일반: {{ }} 문법이면 빈 값으로
      if (typeof value === 'string' && value.startsWith('{{')) {
        onChange('');
      }
    }
  };

  // 드롭 영역 스타일
  const dropZoneClass = isDragOver 
    ? 'ring-2 ring-orange-500 ring-offset-1 ring-offset-gray-800' 
    : '';
  
  // Boolean 타입
  if (schema?.type === 'boolean') {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <span className="text-sm text-gray-300">{label}</span>
        {schema?.required && <span className="text-red-400 text-xs">*</span>}
      </label>
    );
  }
  
  // Number 타입
  if (schema?.type === 'number' || schema?.type === 'integer') {
    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          <div className="flex items-center gap-1">
            {schema?.required && <span className="text-red-400 text-xs">*</span>}
            <button
              onClick={toggleExpression}
              className={`px-1.5 py-0.5 text-xs rounded font-mono transition-colors ${
                isExpression 
                  ? 'bg-orange-600 text-white' 
                  : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
              }`}
              title="Toggle expression mode"
            >
              fx
            </button>
          </div>
        </div>
        
        {isExpression ? (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value)}
            onFocus={onFocus}
            className="w-full px-3 py-1.5 rounded text-sm focus:outline-none focus:ring-1 bg-orange-900/30 border border-orange-600 text-orange-300 font-mono focus:ring-orange-500"
            placeholder="{{ nodeId.field }}"
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="number"
            value={typeof value === 'number' ? value : 0}
            step={schema?.type === 'integer' ? 1 : 0.01}
            onChange={(e) => {
              const num = schema?.type === 'integer' 
                ? parseInt(e.target.value) || 0 
                : parseFloat(e.target.value) || 0;
              onChange(num);
            }}
            onFocus={onFocus}
            className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
        )}
        
        {isExpression && (
          <p className="text-xs text-orange-400/70 mt-1">
            💡 Drag from Input tab or type expression
          </p>
        )}
      </div>
    );
  }
  
  // Array/Object 타입 - JSON 에디터
  if (schema?.type === 'array' || schema?.type === 'object') {
    const jsonValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : '[]';
    return (
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`rounded transition-all ${dropZoneClass}`}
      >
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400 capitalize">{label}</label>
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
        </div>
        <textarea
          ref={inputRef as React.RefObject<HTMLTextAreaElement>}
          value={jsonValue}
          rows={3}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              onChange(parsed);
            } catch {
              // Invalid JSON, keep as string
            }
          }}
          onFocus={onFocus}
          className="w-full px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500 font-mono"
        />
      </div>
    );
  }
  
  // String 타입 (기본)
  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`rounded transition-all ${dropZoneClass}`}
    >
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs text-gray-400 capitalize">{label}</label>
        <div className="flex items-center gap-1">
          {schema?.required && <span className="text-red-400 text-xs">*</span>}
          <button
            onClick={toggleExpression}
            className={`px-1.5 py-0.5 text-xs rounded font-mono transition-colors ${
              isExpression 
                ? 'bg-orange-600 text-white' 
                : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
            }`}
            title="Toggle expression mode"
          >
            fx
          </button>
        </div>
      </div>
      
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="text"
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)}
        onFocus={onFocus}
        placeholder={isExpression ? '{{ nodeId.field }}' : schema?.description}
        className={`w-full px-3 py-1.5 rounded text-sm focus:outline-none focus:ring-1 transition-colors ${
          isExpression 
            ? 'bg-orange-900/30 border border-orange-600 text-orange-300 font-mono focus:ring-orange-500'
            : 'bg-gray-700 border border-gray-600 text-gray-200 focus:border-blue-500'
        }`}
      />
      
      {isExpression && (
        <p className="text-xs text-orange-400/70 mt-1">
          💡 Drag from Input tab or type expression
        </p>
      )}
    </div>
  );
}
