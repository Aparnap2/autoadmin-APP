import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';

interface StreamingIndicatorProps {
  agent: 'ceo' | 'strategy' | 'devops';
  content: string;
  isTyping?: boolean;
  style?: any;
}

const { width: screenWidth } = Dimensions.get('window');

const agentConfig = {
  ceo: {
    name: 'CEO Agent',
    color: '#66FCF1',
    icon: 'person.crop.circle',
  },
  strategy: {
    name: 'Strategy Agent',
    color: '#E91E63',
    icon: 'chart.bar',
  },
  devops: {
    name: 'DevOps Agent',
    color: '#45A29E',
    icon: 'gear',
  },
};

export function StreamingIndicator({
  agent,
  content,
  isTyping = false,
  style,
}: StreamingIndicatorProps) {
  const colorScheme = useColorScheme();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const dot1Anim = useRef(new Animated.Value(0)).current;
  const dot2Anim = useRef(new Animated.Value(0)).current;
  const dot3Anim = useRef(new Animated.Value(0)).current;

  const config = agentConfig[agent];

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

    if (isTyping) {
      animateDots();
    }

    return () => {
      fadeAnim.setValue(0);
      dot1Anim.setValue(0);
      dot2Anim.setValue(0);
      dot3Anim.setValue(0);
    };
  }, [fadeAnim, dot1Anim, dot2Anim, dot3Anim, isTyping]);

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
    <Animated.View style={[styles.container, animatedStyle, style]}>
      <ThemedView style={[
        styles.bubble,
        {
          backgroundColor: '#1F2833',
          borderLeftColor: config.color,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.1,
          shadowRadius: 2,
          elevation: 2,
        },
      ]}>
        {/* Agent Header */}
        <View style={styles.agentHeader}>
          <View style={[styles.agentIcon, { backgroundColor: config.color }]}>
            <IconSymbol
              name={config.icon as any}
              size={16}
              color="#fff"
            />
          </View>
          <ThemedText style={[
            styles.agentName,
            { color: config.color }
          ]}>
            {config.name}
          </ThemedText>
          <View style={styles.statusContainer}>
            <View style={[styles.statusDot, { backgroundColor: config.color }]} />
            <ThemedText style={styles.statusText}>
              {isTyping ? 'Typing' : 'Responding'}
            </ThemedText>
          </View>
        </View>

        {/* Content */}
        {isTyping ? (
          <View style={styles.typingContainer}>
            <ThemedText style={styles.typingText}>Thinking</ThemedText>
            <View style={styles.dotsContainer}>
              <Animated.View style={[styles.dot, dotStyle(dot1Anim)]} />
              <Animated.View style={[styles.dot, dotStyle(dot2Anim)]} />
              <Animated.View style={[styles.dot, dotStyle(dot3Anim)]} />
            </View>
          </View>
        ) : (
          <ThemedText style={styles.contentText}>
            {content}
            <Text style={styles.cursor}>|</Text>
          </ThemedText>
        )}
      </ThemedView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 4,
  },
  bubble: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderBottomLeftRadius: 4,
    borderLeftWidth: 3,
    maxWidth: screenWidth * 0.8,
    alignSelf: 'flex-start',
  },
  agentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  agentIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  agentName: {
    fontSize: 14,
    fontWeight: '600',
    marginRight: 8,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  statusText: {
    fontSize: 12,
    opacity: 0.7,
  },
  typingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  typingText: {
    fontSize: 16,
    color: '#C5C6C7',
    marginRight: 8,
  },
  dotsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#66FCF1',
  },
  contentText: {
    fontSize: 16,
    lineHeight: 22,
    color: '#C5C6C7',
  },
  cursor: {
    color: '#66FCF1',
  },
});

export default StreamingIndicator;