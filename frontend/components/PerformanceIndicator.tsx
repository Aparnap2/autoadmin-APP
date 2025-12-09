import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Colors } from '@/constants/theme';
import { performanceMonitor } from '@/utils/performance';

export function PerformanceIndicator() {
  const [fps, setFps] = useState(60);
  const [metrics, setMetrics] = useState<any[]>([]);
  const colorScheme = useColorScheme();

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();

    const measureFPS = () => {
      frameCount++;
      const currentTime = performance.now();

      if (currentTime >= lastTime + 1000) {
        const currentFps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        setFps(currentFps);
        frameCount = 0;
        lastTime = currentTime;
      }

      requestAnimationFrame(measureFPS);
    };

    const animationFrameId = requestAnimationFrame(measureFPS);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      const topMetrics = performanceMonitor.getMetrics().slice(0, 3);
      setMetrics(topMetrics);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const getFpsColor = () => {
    if (fps >= 55) return '#10B981'; // Green
    if (fps >= 30) return '#F59E0B'; // Yellow
    return '#EF4444'; // Red
  };

  if (__DEV__) {
    return (
      <View style={[
        styles.container,
        { backgroundColor: Colors[colorScheme ?? 'dark'].background }
      ]}>
        <Text style={[
          styles.fpsText,
          { color: getFpsColor() }
        ]}>
          {fps} FPS
        </Text>

        {metrics.length > 0 && (
          <View style={styles.metrics}>
            {metrics.map((metric, index) => (
              <Text key={index} style={[
                styles.metricText,
                { color: Colors[colorScheme ?? 'dark'].text }
              ]}>
                {metric.componentName}: {metric.averageRenderTime.toFixed(1)}ms
              </Text>
            ))}
          </View>
        )}
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 50,
    right: 10,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    zIndex: 9999,
    minWidth: 80,
  },
  fpsText: {
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  metrics: {
    marginTop: 4,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.2)',
    paddingTop: 4,
  },
  metricText: {
    fontSize: 10,
    opacity: 0.8,
  },
});