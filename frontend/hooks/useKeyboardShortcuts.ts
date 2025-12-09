import React, { useEffect, useCallback, useRef, useState } from 'react';
import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useNavigation } from '@react-navigation/native';

interface KeyboardShortcut {
  key: string;
  modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta' | 'cmd')[];
  action: () => void;
  description: string;
  enabled?: boolean;
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  onShortcutTriggered?: (shortcut: KeyboardShortcut) => void;
}

export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true, onShortcutTriggered } = options;
  const shortcutsRef = useRef(shortcuts);

  // Update ref when shortcuts change
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  // Check if event matches shortcut
  const matchesShortcut = useCallback((event: KeyboardEvent, shortcut: KeyboardShortcut): boolean => {
    // Check key match
    if (event.key.toLowerCase() !== shortcut.key.toLowerCase()) {
      return false;
    }

    // Check modifiers
    if (shortcut.modifiers) {
      const hasCtrl = shortcut.modifiers.includes('ctrl') || shortcut.modifiers.includes('cmd');
      const hasAlt = shortcut.modifiers.includes('alt');
      const hasShift = shortcut.modifiers.includes('shift');
      const hasMeta = shortcut.modifiers.includes('meta');

      // For cross-platform compatibility, treat 'cmd' as 'meta' on Mac and 'ctrl' on Windows/Linux
      const cmdPressed = event.metaKey || event.ctrlKey;
      
      if (hasCtrl && !cmdPressed) return false;
      if (hasAlt && !event.altKey) return false;
      if (hasShift && !event.shiftKey) return false;
      if (hasMeta && !event.metaKey) return false;
    }

    return true;
  }, []);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Don't trigger shortcuts when typing in input fields
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.contentEditable === 'true'
      ) {
        // Allow some shortcuts even in inputs (like Escape)
        if (event.key !== 'Escape') {
          return;
        }
      }

      // Find matching shortcut
      const matchingShortcut = shortcutsRef.current.find(
        (shortcut) => 
          (shortcut.enabled !== false) && 
          matchesShortcut(event, shortcut)
      );

      if (matchingShortcut) {
        event.preventDefault();
        event.stopPropagation();

        // Trigger haptic feedback
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

        // Execute action
        matchingShortcut.action();

        // Notify callback
        if (onShortcutTriggered) {
          onShortcutTriggered(matchingShortcut);
        }
      }
    },
    [enabled, matchesShortcut, onShortcutTriggered]
  );

  // Set up event listeners
  useEffect(() => {
    if (Platform.OS === 'web' && enabled) {
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [handleKeyDown, enabled]);

  // Helper function to create standard shortcuts
  const createShortcut = useCallback((
    key: string,
    action: () => void,
    description: string,
    modifiers?: KeyboardShortcut['modifiers']
  ): KeyboardShortcut => ({
    key,
    action,
    description,
    modifiers,
  }), []);

  // Common shortcuts
  const commonShortcuts = {
    cmdK: (action: () => void, description: string) =>
      createShortcut('k', action, description, ['cmd']),
    escape: (action: () => void, description: string) =>
      createShortcut('escape', action, description),
    ctrlSlash: (action: () => void, description: string) =>
      createShortcut('/', action, description, ['ctrl']),
    cmdD: (action: () => void, description: string) =>
      createShortcut('d', action, description, ['cmd']),
    cmdC: (action: () => void, description: string) =>
      createShortcut('c', action, description, ['cmd']),
    cmdR: (action: () => void, description: string) =>
      createShortcut('r', action, description, ['cmd']),
  };

  return {
    createShortcut,
    commonShortcuts,
  };
}

// Hook for managing global shortcuts across the app
export function useGlobalShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isLogStreamOpen, setIsLogStreamOpen] = useState(false);
  const navigation = useNavigation();

  const shortcuts: KeyboardShortcut[] = [
    // Command Palette
    {
      key: 'k',
      modifiers: ['cmd'],
      action: () => setIsCommandPaletteOpen(true),
      description: 'Open Command Palette',
    },
    {
      key: 'escape',
      action: () => {
        setIsCommandPaletteOpen(false);
        setIsLogStreamOpen(false);
      },
      description: 'Close modals',
    },

    // Navigation
    {
      key: 'd',
      modifiers: ['cmd'],
      action: () => navigation.navigate('index'),
      description: 'Go to Dashboard',
    },
    {
      key: 'c',
      modifiers: ['cmd'],
      action: () => navigation.navigate('chat'),
      description: 'Go to Chat',
    },
    {
      key: 'e',
      modifiers: ['cmd'],
      action: () => navigation.navigate('explore'),
      description: 'Go to Explore',
    },

    // System
    {
      key: 'l',
      modifiers: ['cmd'],
      action: () => setIsLogStreamOpen(!isLogStreamOpen),
      description: 'Toggle Log Stream',
    },
    {
      key: 'r',
      modifiers: ['cmd'],
      action: () => {
        // Refresh current screen
        navigation.reset({
          index: 0,
          routes: [{ name: navigation.getCurrentRoute()?.name || 'index' }],
        });
      },
      description: 'Refresh current screen',
    },
  ];

  const { createShortcut } = useKeyboardShortcuts(shortcuts, options);

  return {
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    isLogStreamOpen,
    setIsLogStreamOpen,
    createShortcut,
  };
}
