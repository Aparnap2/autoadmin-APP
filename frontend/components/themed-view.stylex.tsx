import { View, type ViewProps } from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { useThemeColors } from '@/components/StyleXThemeProvider';

const styles = stylex.create({
  default: {
    backgroundColor: tokens.colors.background,
  },
});

export type ThemedViewProps = ViewProps & {
  lightColor?: string;
  darkColor?: string;
  style?: stylex.StyleXStyles;
};

export function ThemedView({
  style,
  lightColor,
  darkColor,
  ...otherProps
}: ThemedViewProps) {
  // For backward compatibility, we still use useThemeColors hook
  const colors = useThemeColors();

  return (
    <View
      {...stylex.props(
        styles.default,
        // Override background color if specified
        (lightColor || darkColor) ? { backgroundColor: lightColor || colors.background } : null,
        style
      )}
      {...otherProps}
    />
  );
}