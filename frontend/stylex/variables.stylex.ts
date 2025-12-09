import stylex from '@stylexjs/stylex';

export const tokens = stylex.defineVars({
  // Color variables
  colors: {
    text: null, // Will be set by theme
    background: null, // Will be set by theme
    tint: null, // Will be set by theme
    icon: null, // Will be set by theme
    tabIconDefault: null, // Will be set by theme
    tabIconSelected: null, // Will be set by theme
    border: null, // Will be set by theme
  },
  // Spacing variables
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px',
  },
  // Typography
  fontSize: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '32px',
  },
  // Border radius
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px',
  },
  // Shadows
  shadow: {
    sm: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 1,
    },
    md: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    lg: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.15,
      shadowRadius: 8,
      elevation: 6,
    },
  },
});

// Light theme
export const lightTheme = stylex.createTheme(tokens.colors, {
  text: '#11181C',
  background: '#fff',
  tint: '#0a7ea4',
  icon: '#687076',
  tabIconDefault: '#687076',
  tabIconSelected: '#0a7ea4',
  border: '#e5e5e5',
});

// Dark theme
export const darkTheme = stylex.createTheme(tokens.colors, {
  text: '#C5C6C7',
  background: '#0B0C10',
  tint: '#66FCF1',
  icon: '#45A29E',
  tabIconDefault: '#45A29E',
  tabIconSelected: '#66FCF1',
  border: '#45A29E',
});

// Export theme types for TypeScript
export type ThemeType = typeof lightTheme | typeof darkTheme;