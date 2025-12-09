import { Text, type TextProps } from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens } from '@/stylex/variables.stylex';
import { useThemeColors } from '@/components/StyleXThemeProvider';

const styles = stylex.create({
  default: {
    fontSize: 16,
    lineHeight: 24,
    color: tokens.colors.text,
  },
  defaultSemiBold: {
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '600',
    color: tokens.colors.text,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    lineHeight: 32,
    color: tokens.colors.text,
  },
  subtitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: tokens.colors.text,
  },
  link: {
    lineHeight: 30,
    fontSize: 16,
    color: tokens.colors.tint,
  },
});

export type ThemedTextProps = TextProps & {
  lightColor?: string;
  darkColor?: string;
  type?: 'default' | 'title' | 'defaultSemiBold' | 'subtitle' | 'link';
  style?: stylex.StyleXStyles;
};

export function ThemedText({
  style,
  lightColor,
  darkColor,
  type = 'default',
  ...rest
}: ThemedTextProps) {
  // For backward compatibility, we still use useThemeColors hook
  // but this can be simplified in future iterations
  const colors = useThemeColors();

  return (
    <Text
      {...stylex.props(
        styles[type],
        // Override color if specified
        (lightColor || darkColor) ? { color: lightColor || colors.text } : null,
        style
      )}
      {...rest}
    />
  );
}