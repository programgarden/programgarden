import { useState, useEffect, useCallback } from 'react';
import type { Credential, CredentialTypeSchema } from '../types/workflow';

interface UseCredentialsReturn {
  credentials: Credential[];
  credentialTypes: CredentialTypeSchema[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createCredential: (data: CreateCredentialRequest) => Promise<Credential | null>;
  updateCredential: (id: string, data: UpdateCredentialRequest) => Promise<boolean>;
  deleteCredential: (id: string) => Promise<boolean>;
}

interface CreateCredentialRequest {
  name: string;
  credential_type: string;
  data: Record<string, unknown>;
}

interface UpdateCredentialRequest {
  name?: string;
  data?: Record<string, unknown>;
}

export function useCredentials(): UseCredentialsReturn {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [credentialTypes, setCredentialTypes] = useState<CredentialTypeSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCredentialTypes = useCallback(async () => {
    try {
      const response = await fetch('/api/credential-types');
      const data = await response.json();
      if (data.credential_types) {
        setCredentialTypes(data.credential_types);
      }
    } catch (err) {
      console.error('Failed to fetch credential types:', err);
    }
  }, []);

  const fetchCredentials = useCallback(async () => {
    try {
      const response = await fetch('/api/credentials');
      const data = await response.json();
      if (data.credentials) {
        setCredentials(data.credentials);
      }
    } catch (err) {
      console.error('Failed to fetch credentials:', err);
    }
  }, []);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchCredentialTypes(), fetchCredentials()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch credentials');
    } finally {
      setLoading(false);
    }
  }, [fetchCredentialTypes, fetchCredentials]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const createCredential = useCallback(async (data: CreateCredentialRequest): Promise<Credential | null> => {
    try {
      const response = await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create credential');
      }
      
      const result = await response.json();
      await fetchCredentials(); // Refresh list
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create credential');
      return null;
    }
  }, [fetchCredentials]);

  const updateCredential = useCallback(async (id: string, data: UpdateCredentialRequest): Promise<boolean> => {
    try {
      const response = await fetch(`/api/credentials/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update credential');
      }
      
      await fetchCredentials(); // Refresh list
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update credential');
      return false;
    }
  }, [fetchCredentials]);

  const deleteCredential = useCallback(async (id: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/credentials/${id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete credential');
      }
      
      await fetchCredentials(); // Refresh list
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete credential');
      return false;
    }
  }, [fetchCredentials]);

  return {
    credentials,
    credentialTypes,
    loading,
    error,
    refetch,
    createCredential,
    updateCredential,
    deleteCredential,
  };
}

// Helper hook to get credentials filtered by type
export function useCredentialsByType(credentialType: string): Credential[] {
  const { credentials } = useCredentials();
  return credentials.filter(c => c.credential_type === credentialType);
}
