/**
 * useTypewriterEffect - Simulated typing effect for synchronous responses
 *
 * Phase 41 Sprint 141: S141-3 - LLM Response Streaming Display
 *
 * Progressively reveals text content character-by-character
 * to simulate real-time LLM token streaming for non-SSE responses.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseTypewriterEffectOptions {
  /** Milliseconds per character (default: 20) */
  speed?: number;
  /** Whether the effect is enabled (default: true) */
  enabled?: boolean;
  /** Callback when typing completes */
  onComplete?: () => void;
}

interface UseTypewriterEffectReturn {
  /** The currently displayed (partially revealed) text */
  displayedText: string;
  /** Whether the typewriter is still animating */
  isTyping: boolean;
  /** Skip to end immediately */
  skipToEnd: () => void;
}

/**
 * Hook that progressively reveals text content with a typewriter effect.
 *
 * @param content - The full text to reveal
 * @param options - Configuration options
 */
export function useTypewriterEffect(
  content: string,
  options: UseTypewriterEffectOptions = {}
): UseTypewriterEffectReturn {
  const { speed = 20, enabled = true, onComplete } = options;
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const rafRef = useRef<number>(0);
  const indexRef = useRef(0);
  const lastTimeRef = useRef(0);
  const contentRef = useRef(content);
  const skippedRef = useRef(false);

  const skipToEnd = useCallback(() => {
    skippedRef.current = true;
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    setDisplayedText(contentRef.current);
    setIsTyping(false);
    onComplete?.();
  }, [onComplete]);

  useEffect(() => {
    contentRef.current = content;

    if (!enabled || !content) {
      setDisplayedText(content || '');
      setIsTyping(false);
      return;
    }

    // Reset for new content
    skippedRef.current = false;
    indexRef.current = 0;
    lastTimeRef.current = 0;
    setDisplayedText('');
    setIsTyping(true);

    const animate = (timestamp: number) => {
      if (skippedRef.current) return;

      if (!lastTimeRef.current) {
        lastTimeRef.current = timestamp;
      }

      const elapsed = timestamp - lastTimeRef.current;

      if (elapsed >= speed) {
        // Calculate how many characters to add based on elapsed time
        const charsToAdd = Math.max(1, Math.floor(elapsed / speed));
        const newIndex = Math.min(indexRef.current + charsToAdd, content.length);
        indexRef.current = newIndex;
        lastTimeRef.current = timestamp;

        setDisplayedText(content.slice(0, newIndex));

        if (newIndex >= content.length) {
          setIsTyping(false);
          onComplete?.();
          return;
        }
      }

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = 0;
      }
    };
  }, [content, speed, enabled, onComplete]);

  return { displayedText, isTyping, skipToEnd };
}

export default useTypewriterEffect;
