import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

// Polyfill crypto for React Native
import 'react-native-get-random-values';
import { useEffect } from 'react';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { performanceMonitor } from '@/utils/performance';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // Start performance monitoring in development
  useEffect(() => {
    if (__DEV__) {
      performanceMonitor.startMonitoring();
    }

    return () => {
      performanceMonitor.stopMonitoring();
    };
  }, []);

  return (
    <ThemeProvider value={DarkTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
      <StatusBar style="light" />
    </ThemeProvider>
  );
}
