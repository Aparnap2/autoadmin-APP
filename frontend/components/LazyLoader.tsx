import React, { Suspense, lazy, ComponentType } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

interface LazyLoaderProps {
  componentLoader: () => Promise<{ default: ComponentType<any> }>;
  fallback?: React.ReactNode;
  props?: any;
}

const defaultFallback = (
  <ThemedView style={styles.loadingContainer}>
    <ActivityIndicator size="large" color="#66FCF1" />
    <ThemedText style={styles.loadingText}>Loading...</ThemedText>
  </ThemedView>
);

export function LazyLoader({
  componentLoader,
  fallback = defaultFallback,
  props = {}
}: LazyLoaderProps) {
  const LazyComponent = lazy(componentLoader);

  return (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

// Pre-configured lazy components
export const LazyAutoAdminDashboard = (props: any) => (
  <LazyLoader
    componentLoader={() => import('@/components/dashboard/AutoAdminDashboard')}
    props={props}
  />
);

export const LazyAgentChatInterface = (props: any) => (
  <LazyLoader
    componentLoader={() => import('@/components/chat/AgentChatInterface')}
    props={props}
  />
);

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    textAlign: 'center',
    opacity: 0.7,
  },
});