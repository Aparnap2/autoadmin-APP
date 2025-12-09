import React, { createContext, useContext } from 'react';
import * as stylex from '@stylexjs/stylex';
import { lightTheme, darkTheme, type ThemeType, tokens } from '@/stylex/variables.stylex';
import { useColorScheme } from '@/hooks/use-color-scheme';

const ThemeContext = createContext<{
  theme: ThemeType;
  colorScheme: 'light' | 'dark';
} | null>(null);

export function StyleXThemeProvider({ children }: { children: React.ReactNode }) {
  const colorScheme = useColorScheme();
  const theme = colorScheme === 'dark' ? darkTheme : lightTheme;

  return (
    <ThemeContext.Provider value={{ theme, colorScheme }}>
      <div {...stylex.props(theme)}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}

export function useStyleXTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useStyleXTheme must be used within StyleXThemeProvider');
  }
  return context;
}

// Export a hook for backward compatibility with existing theme system
export function useThemeColors() {
  const colorScheme = useColorScheme();
  const theme = colorScheme === 'dark' ? darkTheme : lightTheme;

  // Map the Colors structure to work with existing useThemeColor hook
  return {
    text: colorScheme === 'dark' ? '#C5C6C7' : '#11181C',
    background: colorScheme === 'dark' ? '#0B0C10' : '#fff',
    tint: colorScheme === 'dark' ? '#66FCF1' : '#0a7ea4',
    icon: colorScheme === 'dark' ? '#45A29E' : '#687076',
    tabIconDefault: colorScheme === 'dark' ? '#45A29E' : '#687076',
    tabIconSelected: colorScheme === 'dark' ? '#66FCF1' : '#0a7ea4',
    border: colorScheme === 'dark' ? '#45A29E' : '#e5e5e5',
  };
}