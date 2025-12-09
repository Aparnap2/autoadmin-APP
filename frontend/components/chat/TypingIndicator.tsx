import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
} from 'react-native';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import { useColorScheme } from '@/hooks/use-color-scheme';

interface TypingIndicatorProps {
  agent?: 'ceo' | 'strategy' | 'devops';
  style?: any;
  message?: string;
}

const agentColors = {
  ceo: '#66FCF1',
  strategy: '#E91E63',
  devops: '#45A29E',
};

export function TypingIndicator({
  agent = 'ceo',
  style,
  message = 'Typing',
}: TypingIndicatorProps) {
  const colorScheme = useColorScheme();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const dot1Anim = useRef(new Animated.Value(0)).current;
  const dot2Anim = useRef(new Animated.Value(0)).current;
  const dot3Anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Fade in animation
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();

    // Typing dots animation
    const animateDots = () => {
      const animations = [
        Animated.timing(dot1Anim, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(dot2Anim, {
          toValue: 1,
          duration: 400,
          delay: 200,
          useNativeDriver: true,
        }),
        Animated.timing(dot3Anim, {
          toValue: 1,
          duration: 400,
          delay: 400,
          useNativeDriver: true,
        }),
      ];

      Animated.sequence(animations).start(() => {
        dot1Anim.setValue(0);
        dot2Anim.setValue(0);
        dot3Anim.setValue(0);
        animateDots();
      });
    };

    animateDots();

    return () => {
      fadeAnim.setValue(0);
      dot1Anim.setValue(0);
      dot2Anim.setValue(0);
      dot3Anim.setValue(0);
    };
  }, []);

  const animatedStyle = {
    opacity: fadeAnim,
  };

  const dotStyle = (anim: Animated.Value) => ({
    transform: [
      {
        translateY: anim.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -4],
        }),
      },
    ],
    opacity: anim.interpolate({
      inputRange: [0, 1],
      outputRange: [0.3, 1],
    }),
  });

  return (
    <Animated.View style={[animatedStyle, style]}>
      <ThemedView style={[
        styles.container,
        {
          backgroundColor: '#1F2833',
          borderLeftColor: agentColors[agent],
        },
      ]}>
        <ThemedText style={[
          styles.text,
          { color: colorScheme === 'dark' ? '#aaa' : '#666' }
        ]}>
          {message}
        </ThemedText>
        <View style={styles.dotsContainer}>
          <Animated.View style={[styles.dot, dotStyle(dot1Anim)]} />
          <Animated.View style={[styles.dot, dotStyle(dot2Anim)]} />
          <Animated.View style={[styles.dot, dotStyle(dot3Anim)]} />
        </View>
      </ThemedView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    borderLeftWidth: 2,
    marginHorizontal: 16,
    marginVertical: 4,
    maxWidth: 120,
  },
  text: {
    fontSize: 14,
    marginRight: 8,
  },
  dotsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#999',
  },
});

export default TypingIndicator;