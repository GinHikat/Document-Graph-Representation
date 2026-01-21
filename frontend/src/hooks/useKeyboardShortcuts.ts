import { useEffect, useCallback } from 'react';

type KeyboardShortcut = {
  key: string;
  modifiers?: {
    ctrl?: boolean;
    alt?: boolean;
    shift?: boolean;
    meta?: boolean;
  };
  action: () => void;
  description?: string;
};

type UseKeyboardShortcutsOptions = {
  enabled?: boolean;
  preventDefault?: boolean;
};

export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true, preventDefault = true } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts when typing in inputs
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Exception: allow Cmd+Enter in textareas for submit
        if (!(event.key === 'Enter' && (event.metaKey || event.ctrlKey))) {
          return;
        }
      }

      for (const shortcut of shortcuts) {
        const keyMatches = event.key === shortcut.key || event.key === shortcut.key.toLowerCase();
        const modifiers = shortcut.modifiers || {};

        const modifiersMatch =
          (modifiers.ctrl ?? false) === event.ctrlKey &&
          (modifiers.alt ?? false) === event.altKey &&
          (modifiers.shift ?? false) === event.shiftKey &&
          (modifiers.meta ?? false) === event.metaKey;

        if (keyMatches && modifiersMatch) {
          if (preventDefault) {
            event.preventDefault();
          }
          shortcut.action();
          return;
        }
      }
    },
    [shortcuts, enabled, preventDefault]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);
}

// Utility to format shortcut for display
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = [];
  const modifiers = shortcut.modifiers || {};

  if (modifiers.meta) parts.push('⌘');
  if (modifiers.ctrl) parts.push('Ctrl');
  if (modifiers.alt) parts.push('Alt');
  if (modifiers.shift) parts.push('⇧');

  parts.push(shortcut.key.toUpperCase());

  return parts.join('+');
}
