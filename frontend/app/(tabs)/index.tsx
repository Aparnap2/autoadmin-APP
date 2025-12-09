import React from 'react';
import { StyleSheet, StatusBar } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';
import { AutoAdminDashboard } from '@/components/dashboard/AutoAdminDashboard';

// Mock user ID - in a real app, this would come from authentication
const MOCK_USER_ID = 'demo-user-123';

export default function HomeScreen() {
  const colorScheme = useColorScheme();

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: Colors[colorScheme ?? 'dark'].background }]}
      edges={['top', 'left', 'right']}
    >
      <StatusBar
        barStyle="light-content"
        backgroundColor={Colors[colorScheme ?? 'dark'].background}
      />
      <AutoAdminDashboard userId={MOCK_USER_ID} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
