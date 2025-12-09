/**
 * Performance Utilities
 * Monitors and optimizes component rendering performance
 */

import { useEffect, useRef, useCallback } from 'react';

interface PerformanceMetrics {
  componentName: string;
  renderCount: number;
  renderTime: number;
  lastRenderTime: number;
  averageRenderTime: number;
}

class PerformanceMonitor {
  private metrics: Map<string, PerformanceMetrics> = new Map();
  private observers: PerformanceObserver[] = [];

  startMonitoring() {
    // React Native doesn't support PerformanceObserver API
    // We'll use console.time for basic performance tracking
    if (__DEV__) {
      console.log('Performance monitoring started (React Native mode)');
    }
  }

  stopMonitoring() {
    // React Native doesn't support PerformanceObserver API
    if (__DEV__) {
      console.log('Performance monitoring stopped');
    }
    this.observers = [];
  }

  recordRender(componentName: string, renderTime: number) {
    const existing = this.metrics.get(componentName) || {
      componentName,
      renderCount: 0,
      renderTime: 0,
      lastRenderTime: 0,
      averageRenderTime: 0,
    };

    const updated: PerformanceMetrics = {
      ...existing,
      renderCount: existing.renderCount + 1,
      lastRenderTime: renderTime,
      renderTime: existing.renderTime + renderTime,
      averageRenderTime: (existing.renderTime + renderTime) / (existing.renderCount + 1),
    };

    this.metrics.set(componentName, updated);

    // Warn on slow renders
    if (renderTime > 16) { // 60fps threshold
      console.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`);
    }
  }

  getMetrics(): PerformanceMetrics[] {
    return Array.from(this.metrics.values()).sort((a, b) => b.averageRenderTime - a.averageRenderTime);
  }

  clearMetrics() {
    this.metrics.clear();
  }
}

export const performanceMonitor = new PerformanceMonitor();

// Hook for performance monitoring
export function usePerformanceMonitor(componentName: string) {
  const renderStartTime = useRef<number>(0);

  useEffect(() => {
    // Use Date.now() for React Native compatibility
    renderStartTime.current = Date.now();

    return () => {
      const renderTime = Date.now() - renderStartTime.current;
      performanceMonitor.recordRender(componentName, renderTime);
    };
  });
}

// Hook for debounce
export function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout>();

  const debouncedCallback = useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  }, [callback, delay]) as T;

  return debouncedCallback;
}

// Hook for throttle
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const lastCallTime = useRef<number>(0);

  const throttledCallback = useCallback((...args: Parameters<T>) => {
    const now = Date.now();

    if (now - lastCallTime.current >= delay) {
      lastCallTime.current = now;
      callback(...args);
    }
  }, [callback, delay]) as T;

  return throttledCallback;
}

// Memory usage monitoring - React Native doesn't support memory API
export function useMemoryMonitor() {
  useEffect(() => {
    if (__DEV__) {
      console.log('Memory monitoring: React Native doesn\'t provide memory API');
    }
  });
}

// FPS monitoring
export function useFPSMonitor() {
  const frameCount = useRef(0);
  const lastTime = useRef(Date.now());

  useEffect(() => {
    let animationFrameId: number;

    const measureFPS = () => {
      frameCount.current++;
      const currentTime = Date.now();

      if (currentTime >= lastTime.current + 1000) {
        const fps = Math.round((frameCount.current * 1000) / (currentTime - lastTime.current));
        if (__DEV__) {
          console.log(`FPS: ${fps}`);
        }

        frameCount.current = 0;
        lastTime.current = currentTime;
      }

      animationFrameId = requestAnimationFrame(measureFPS);
    };

    animationFrameId = requestAnimationFrame(measureFPS);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);
}

// Utility to measure function performance
export function measurePerformance<T extends (...args: any[]) => any>(
  fn: T,
  name: string
): T {
  return ((...args: Parameters<T>) => {
    const start = Date.now();
    const result = fn(...args);
    const end = Date.now();

    console.log(`${name} took ${(end - start).toFixed(2)}ms`);
    return result;
  }) as T;
}