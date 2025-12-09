/**
 * Font utilities for cross-platform font handling
 */

import { Platform } from 'react-native';
import { Fonts } from '@/constants/theme';

/**
 * Safely gets the appropriate font family for the current platform
 * @param fontType - The type of font (sans, serif, rounded, mono)
 * @returns The font family string for the current platform
 */
export function getFontFamily(fontType: keyof Omit<typeof Fonts.ios, 'ios' | 'default' | 'web'> = 'sans'): string {
  if (Platform.OS === 'ios') {
    return Fonts.ios?.[fontType] || 'system-ui';
  } else if (Platform.OS === 'web') {
    return Fonts.web?.[fontType] || 'system-ui, -apple-system, BlinkMacSystemFont, sans-serif';
  } else {
    // For Android and other platforms
    return (Fonts as any)?.[fontType] || 'normal';
  }
}

/**
 * Gets the monospace font family for the current platform
 * @returns The monospace font family string
 */
export function getMonoFontFamily(): string {
  return getFontFamily('mono');
}

/**
 * Gets the sans-serif font family for the current platform
 * @returns The sans-serif font family string
 */
export function getSansFontFamily(): string {
  return getFontFamily('sans');
}

/**
 * Gets the serif font family for the current platform
 * @returns The serif font family string
 */
export function getSerifFontFamily(): string {
  return getFontFamily('serif');
}

/**
 * Gets the rounded font family for the current platform
 * @returns The rounded font family string
 */
export function getRoundedFontFamily(): string {
  return getFontFamily('rounded');
}