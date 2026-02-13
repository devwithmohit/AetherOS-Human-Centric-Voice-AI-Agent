import { useState, useEffect } from 'react';
import { useAppStore } from '@store/appStore';
import { apiClient } from '@services/api';

export interface MemoryItem {
  id: string;
  type: 'fact' | 'preference' | 'context';
  content: string;
  timestamp: Date;
  source?: string;
}

export const useMemory = (userId?: string) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const memories = useAppStore((state) => state.memories);
  const addMemory = useAppStore((state) => state.addMemory);
  const removeMemory = useAppStore((state) => state.removeMemory);

  // Fetch memories from backend
  const fetchMemories = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient.getMemories(userId);

      // Clear and reload memories
      data.forEach((memory: any) => {
        addMemory({
          type: memory.type,
          content: memory.content,
          source: memory.source,
        });
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch memories');
      console.error('Failed to fetch memories:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Delete memory
  const deleteMemory = async (memoryId: string) => {
    setError(null);

    try {
      await apiClient.deleteMemory(memoryId);
      removeMemory(memoryId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete memory');
      console.error('Failed to delete memory:', err);
      throw err;
    }
  };

  // Edit preference
  const editPreference = async (memoryId: string, newContent: string) => {
    setError(null);

    try {
      await apiClient.updateMemory(memoryId, newContent);

      // Refresh memories after edit
      await fetchMemories();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to edit preference');
      console.error('Failed to edit preference:', err);
      throw err;
    }
  };

  // Clear all memories
  const clearAllMemories = async () => {
    setError(null);

    try {
      await apiClient.clearMemories(userId);

      // Remove all from local store
      memories.forEach((memory) => {
        removeMemory(memory.id);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear memories');
      console.error('Failed to clear memories:', err);
      throw err;
    }
  };

  // Auto-fetch on mount
  useEffect(() => {
    fetchMemories();
  }, [userId]);

  return {
    memories,
    isLoading,
    error,
    fetchMemories,
    deleteMemory,
    editPreference,
    clearAllMemories,
  };
};
