/**
 * useChatThreads - Chat Thread Management Hook
 *
 * Sprint 74: S74-2 - useChatThreads Hook
 * Sprint 74: S74-BF-1 - Add message persistence for thread switching
 * Phase 19: UI Enhancement
 *
 * Manages chat threads with localStorage persistence.
 * Provides CRUD operations for thread management.
 * Now includes message persistence per thread.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ChatMessage } from '@/types/ag-ui';

/**
 * Chat thread data structure
 */
export interface ChatThread {
  id: string;
  title: string;
  lastMessage?: string;
  updatedAt: string;
  messageCount: number;
}

/**
 * Hook return type
 */
export interface UseChatThreadsReturn {
  /** List of all threads */
  threads: ChatThread[];
  /** Create a new thread */
  createThread: (title?: string) => string;
  /** Update an existing thread */
  updateThread: (id: string, updates: Partial<Omit<ChatThread, 'id'>>) => void;
  /** Delete a thread */
  deleteThread: (id: string) => void;
  /** Get a thread by ID */
  getThread: (id: string) => ChatThread | undefined;
  /** Generate a title from message content */
  generateTitle: (message: string) => string;
  /** Get messages for a thread (S74-BF-1) */
  getMessages: (threadId: string) => ChatMessage[];
  /** Save messages for a thread (S74-BF-1) */
  saveMessages: (threadId: string, messages: ChatMessage[]) => void;
  /** Clear messages for a thread (S74-BF-1) */
  clearThreadMessages: (threadId: string) => void;
}

// localStorage keys
const STORAGE_KEY = 'ipa_chat_threads';
const MESSAGES_KEY_PREFIX = 'ipa_thread_messages_';
// Maximum number of threads to keep
const MAX_THREADS = 50;
// Maximum messages per thread to store
const MAX_MESSAGES_PER_THREAD = 100;

/**
 * useChatThreads Hook
 *
 * Manages chat threads with localStorage persistence.
 *
 * @example
 * ```tsx
 * const { threads, createThread, updateThread, deleteThread } = useChatThreads();
 *
 * // Create new thread
 * const threadId = createThread('New Conversation');
 *
 * // Update thread
 * updateThread(threadId, { title: 'Updated Title' });
 *
 * // Delete thread
 * deleteThread(threadId);
 * ```
 */
export function useChatThreads(): UseChatThreadsReturn {
  // Load initial state from localStorage
  const [threads, setThreads] = useState<ChatThread[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Validate the data structure
        if (Array.isArray(parsed)) {
          return parsed.filter(
            (t): t is ChatThread =>
              typeof t === 'object' &&
              typeof t.id === 'string' &&
              typeof t.title === 'string'
          );
        }
      }
    } catch (e) {
      console.warn('[useChatThreads] Failed to load from localStorage:', e);
    }
    return [];
  });

  // Persist to localStorage whenever threads change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(threads));
    } catch (e) {
      console.warn('[useChatThreads] Failed to save to localStorage:', e);
      // If quota exceeded, try to save fewer threads
      if (e instanceof DOMException && e.name === 'QuotaExceededError') {
        try {
          // Keep only the most recent threads
          const reduced = threads.slice(0, Math.floor(MAX_THREADS / 2));
          localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced));
        } catch {
          // Give up
        }
      }
    }
  }, [threads]);

  /**
   * Create a new thread
   * @param title - Optional title (defaults to '新對話')
   * @returns The new thread's ID
   */
  const createThread = useCallback((title: string = '新對話'): string => {
    const newThread: ChatThread = {
      id: crypto.randomUUID(),
      title,
      updatedAt: new Date().toISOString(),
      messageCount: 0,
    };

    setThreads((prev) => {
      // Add new thread at the beginning and limit total count
      const updated = [newThread, ...prev].slice(0, MAX_THREADS);
      return updated;
    });

    return newThread.id;
  }, []);

  /**
   * Update an existing thread
   * @param id - Thread ID
   * @param updates - Partial updates to apply
   */
  const updateThread = useCallback(
    (id: string, updates: Partial<Omit<ChatThread, 'id'>>) => {
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id === id) {
            return {
              ...t,
              ...updates,
              // Always update the timestamp
              updatedAt: new Date().toISOString(),
            };
          }
          return t;
        })
      );
    },
    []
  );

  /**
   * Get a thread by ID
   * @param id - Thread ID
   * @returns The thread or undefined
   */
  const getThread = useCallback(
    (id: string): ChatThread | undefined => {
      return threads.find((t) => t.id === id);
    },
    [threads]
  );

  /**
   * Generate a title from message content
   * Takes the first 30 characters and truncates at word boundary
   * @param message - Message content
   * @returns Generated title
   */
  const generateTitle = useCallback((message: string): string => {
    // Remove leading/trailing whitespace
    const trimmed = message.trim();

    // If empty, return default
    if (!trimmed) return '新對話';

    // Max length for title
    const maxLength = 30;

    // If short enough, return as-is
    if (trimmed.length <= maxLength) return trimmed;

    // Find a good truncation point (word boundary)
    const truncated = trimmed.slice(0, maxLength);
    const lastSpace = truncated.lastIndexOf(' ');

    // If we found a space after position 20, truncate there
    if (lastSpace > 20) {
      return truncated.slice(0, lastSpace) + '...';
    }

    // Otherwise just truncate with ellipsis
    return truncated + '...';
  }, []);

  // ==========================================================================
  // Message Persistence (S74-BF-1)
  // ==========================================================================

  /**
   * Get messages for a specific thread
   * @param threadId - Thread ID
   * @returns Array of messages or empty array
   */
  const getMessages = useCallback((threadId: string): ChatMessage[] => {
    try {
      const key = `${MESSAGES_KEY_PREFIX}${threadId}`;
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('[useChatThreads] Failed to load messages:', e);
    }
    return [];
  }, []);

  /**
   * Save messages for a specific thread
   * @param threadId - Thread ID
   * @param messages - Messages to save
   */
  const saveMessages = useCallback((threadId: string, messages: ChatMessage[]) => {
    try {
      const key = `${MESSAGES_KEY_PREFIX}${threadId}`;
      // Limit messages to prevent localStorage overflow
      const toSave = messages.slice(-MAX_MESSAGES_PER_THREAD);
      localStorage.setItem(key, JSON.stringify(toSave));
    } catch (e) {
      console.warn('[useChatThreads] Failed to save messages:', e);
      // If quota exceeded, try saving fewer messages
      if (e instanceof DOMException && e.name === 'QuotaExceededError') {
        try {
          const key = `${MESSAGES_KEY_PREFIX}${threadId}`;
          const reduced = messages.slice(-Math.floor(MAX_MESSAGES_PER_THREAD / 2));
          localStorage.setItem(key, JSON.stringify(reduced));
        } catch {
          // Give up
        }
      }
    }
  }, []);

  /**
   * Clear messages for a specific thread
   * @param threadId - Thread ID
   */
  const clearThreadMessages = useCallback((threadId: string) => {
    try {
      const key = `${MESSAGES_KEY_PREFIX}${threadId}`;
      localStorage.removeItem(key);
    } catch (e) {
      console.warn('[useChatThreads] Failed to clear messages:', e);
    }
  }, []);

  // Clean up messages when thread is deleted
  const deleteThreadWithMessages = useCallback((id: string) => {
    clearThreadMessages(id);
    setThreads((prev) => prev.filter((t) => t.id !== id));
  }, [clearThreadMessages]);

  return {
    threads,
    createThread,
    updateThread,
    deleteThread: deleteThreadWithMessages,
    getThread,
    generateTitle,
    getMessages,
    saveMessages,
    clearThreadMessages,
  };
}

export default useChatThreads;
