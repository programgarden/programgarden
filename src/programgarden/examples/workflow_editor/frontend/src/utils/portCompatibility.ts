/**
 * Port type compatibility checker
 * 
 * Determines if a source port type can connect to a target port type.
 */

// Port types that are compatible with each other
const COMPATIBLE_TYPES: Record<string, string[]> = {
  // any accepts everything
  'any': ['*'],
  
  // Specific type compatibility
  'broker_connection': ['broker_connection', 'any'],
  'account_data': ['account_data', 'dict', 'any'],
  'symbol_list': ['symbol_list', 'any'],
  'market_data': ['market_data', 'dict', 'any'],
  'balance_data': ['balance_data', 'dict', 'any'],
  'order_result': ['order_result', 'dict', 'any'],
  
  // Primitive types
  'signal': ['signal'],
  'float': ['float', 'number', 'any'],
  'int': ['int', 'integer', 'number', 'float', 'any'],
  'integer': ['int', 'integer', 'number', 'float', 'any'],
  'number': ['number', 'float', 'int', 'any'],
  'bool': ['bool', 'boolean', 'any'],
  'boolean': ['bool', 'boolean', 'any'],
  'string': ['string', 'any'],
  'str': ['str', 'string', 'any'],
  
  // Collection types
  'dict': ['dict', 'object', 'any'],
  'object': ['dict', 'object', 'any'],
  'list': ['list', 'array', 'any'],
  'array': ['list', 'array', 'any'],
  'dataframe': ['dataframe', 'dict', 'any'],
};

/**
 * Check if source port type is compatible with target port type
 */
export function isPortCompatible(sourceType: string | undefined, targetType: string | undefined): boolean {
  // If either type is undefined, allow connection (legacy behavior)
  if (!sourceType || !targetType) {
    return true;
  }
  
  // Normalize to lowercase
  const src = sourceType.toLowerCase();
  const tgt = targetType.toLowerCase();
  
  // Same type is always compatible
  if (src === tgt) {
    return true;
  }
  
  // Target 'any' accepts everything
  if (tgt === 'any') {
    return true;
  }
  
  // Source 'any' can go to anything (though this is unusual)
  if (src === 'any') {
    return true;
  }
  
  // Check compatibility matrix
  const compatibleTargets = COMPATIBLE_TYPES[src];
  if (compatibleTargets) {
    if (compatibleTargets.includes('*')) {
      return true;
    }
    return compatibleTargets.includes(tgt);
  }
  
  // Default: not compatible
  return false;
}

/**
 * Get human-readable description of why types are incompatible
 */
export function getIncompatibilityReason(sourceType: string, targetType: string): string {
  return `Type mismatch: ${sourceType} → ${targetType}`;
}

/**
 * Get color for edge based on compatibility
 */
export function getEdgeColor(isValid: boolean): string {
  return isValid ? '#4b5563' : '#ef4444';  // gray-600 or red-500
}
