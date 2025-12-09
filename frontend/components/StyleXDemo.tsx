/**
 * StyleX Demo Component
 * Simple demo to test StyleX integration
 */

import React from 'react';
import { View, ScrollView, Text } from 'react-native';
import stylex from '@stylexjs/stylex';
import { tokens, lightTheme, darkTheme } from '@/stylex/variables.stylex';
import { baseStyles } from '@/stylex/base.stylex';
import { ThemedText } from '@/components/themed-text.stylex';
import { ThemedView } from '@/components/themed-view.stylex';
import { StyleXThemeProvider } from '@/components/StyleXThemeProvider';

const demoStyles = stylex.create({
  container: {
    flex: 1,
  },
  section: {
    padding: tokens.spacing.lg,
    marginBottom: tokens.spacing.md,
  },
  card: {
    backgroundColor: tokens.colors.background,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.borderRadius.lg,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.md,
    ...tokens.shadow.md,
  },
  colorGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: tokens.spacing.sm,
  },
  colorBox: {
    width: '48%',
    aspectRatio: 1,
    borderRadius: tokens.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: tokens.spacing.sm,
  },
  spacingDemo: {
    flexDirection: 'column',
    gap: tokens.spacing.md,
  },
  typographyDemo: {
    flexDirection: 'column',
    gap: tokens.spacing.sm,
  },
  buttonDemo: {
    flexDirection: 'row',
    gap: tokens.spacing.md,
    flexWrap: 'wrap',
  },
  button: {
    paddingVertical: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.lg,
    borderRadius: tokens.borderRadius.md,
    ...tokens.shadow.sm,
  },
});

export function StyleXDemo() {
  return (
    <StyleXThemeProvider>
      <ScrollView
        {...stylex.props(demoStyles.container)}
        contentContainerStyle={{ padding: tokens.spacing.md }}
      >
        {/* Header */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="title">StyleX Integration Demo</ThemedText>
          <ThemedText style={{ marginTop: 8 }}>
            This demo shows the new StyleX styling system with theme variables and consistent spacing.
          </ThemedText>
        </View>

        {/* Color Theme Demo */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">Theme Colors</ThemedText>
          <View {...stylex.props(demoStyles.colorGrid)}>
            <View
              {...stylex.props(demoStyles.colorBox)}
              style={{ backgroundColor: tokens.colors.text }}
            >
              <Text style={{ color: tokens.colors.background, fontWeight: 'bold' }}>
                Text Color
              </Text>
            </View>
            <View
              {...stylex.props(demoStyles.colorBox)}
              style={{ backgroundColor: tokens.colors.background, borderWidth: 1, borderColor: tokens.colors.border }}
            >
              <Text style={{ color: tokens.colors.text }}>Background</Text>
            </View>
            <View
              {...stylex.props(demoStyles.colorBox)}
              style={{ backgroundColor: tokens.colors.tint }}
            >
              <Text style={{ color: tokens.colors.background, fontWeight: 'bold' }}>
                Tint Color
              </Text>
            </View>
            <View
              {...stylex.props(demoStyles.colorBox)}
              style={{ backgroundColor: tokens.colors.border }}
            >
              <Text style={{ color: tokens.colors.text }}>Border</Text>
            </View>
          </View>
        </View>

        {/* Typography Demo */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">Typography Scale</ThemedText>
          <View {...stylex.props(demoStyles.typographyDemo)}>
            <ThemedText {...stylex.props(baseStyles.heading)}>Heading Text</ThemedText>
            <ThemedText {...stylex.props(baseStyles.subheading)}>Subheading Text</ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>Body Text</ThemedText>
            <ThemedText {...stylex.props(baseStyles.caption)}>Caption Text</ThemedText>
          </View>
        </View>

        {/* Spacing Demo */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">Spacing System</ThemedText>
          <View {...stylex.props(demoStyles.spacingDemo)}>
            <ThemedText>Spacing Small (8px)</ThemedText>
            <ThemedText {...stylex.props(baseStyles.p_md)}>
              Padding Medium (16px)
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.p_lg)}>
              Padding Large (24px)
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.p_xl)}>
              Padding Extra Large (32px)
            </ThemedText>
          </View>
        </View>

        {/* Card Components Demo */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">Card Components</ThemedText>
          <View {...stylex.props(baseStyles.card)}>
            <ThemedText {...stylex.props(baseStyles.heading)}>
              Card Title
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>
              This card uses the baseStyles.card style with consistent padding, border radius, and shadows.
            </ThemedText>
          </View>
        </View>

        {/* Button Demo */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">Button Styles</ThemedText>
          <View {...stylex.props(demoStyles.buttonDemo)}>
            <View
              {...stylex.props([demoStyles.button, baseStyles.button])}
              style={{ backgroundColor: tokens.colors.tint }}
            >
              <ThemedText {...stylex.props(baseStyles.buttonText)}>
                Primary Button
              </ThemedText>
            </View>
            <View
              {...stylex.props(demoStyles.button)}
              style={{
                backgroundColor: tokens.colors.background,
                borderWidth: 1,
                borderColor: tokens.colors.border,
              }}
            >
              <ThemedText>Secondary Button</ThemedText>
            </View>
          </View>
        </View>

        {/* StyleX Benefits */}
        <View {...stylex.props(demoStyles.section)}>
          <ThemedText type="subtitle">StyleX Benefits</ThemedText>
          <View {...stylex.props(baseStyles.card)}>
            <ThemedText {...stylex.props(baseStyles.body)}>
              ✓ Atomic CSS for better performance
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>
              ✓ Type-safe styling with TypeScript
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>
              ✓ Consistent theming and variables
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>
              ✓ Better code organization and maintainability
            </ThemedText>
            <ThemedText {...stylex.props(baseStyles.body)}>
              ✓ Zero runtime CSS injection
            </ThemedText>
          </View>
        </View>
      </ScrollView>
    </StyleXThemeProvider>
  );
}