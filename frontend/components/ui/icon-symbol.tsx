// Fallback for using MaterialIcons on Android and web.

import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { SymbolWeight, SymbolViewProps } from 'expo-symbols';
import { ComponentProps } from 'react';
import { OpaqueColorValue, type StyleProp, type TextStyle } from 'react-native';
import React from 'react';

type IconMapping = Record<SymbolViewProps['name'], ComponentProps<typeof MaterialIcons>['name']>;
type IconSymbolName = keyof typeof MAPPING;

/**
 * Add your SF Symbols to Material Icons mappings here.
 * - see Material Icons in the [Icons Directory](https://icons.expo.fyi).
 * - see SF Symbols in the [SF Symbols](https://developer.apple.com/sf-symbols/) app.
 */
const MAPPING = {
  'house.fill': 'home',
  'paperplane.fill': 'send',
  'chevron.left.forwardslash.chevron.right': 'code',
  'chevron.right': 'chevron-right',
  'chart.bar.fill': 'bar-chart',
  'message.fill': 'message',
  'person.crop.circle': 'person',
  'chart.bar': 'bar-chart',
  'gear': 'settings',
  'trending.up': 'trending-up',
  'speedometer': 'speed',
  'doc.on.doc': 'content-copy',
  'trash': 'delete',
  'ellipsis': 'more-horiz',
  'chevron.left': 'chevron-left',
  'chevron.down': 'expand-more',
  'plus': 'add',
  'minus': 'remove',
  'checkmark': 'check',
  'xmark': 'close',
  'arrow.up': 'keyboard-arrow-up',
  'arrow.down': 'keyboard-arrow-down',
  'refresh': 'refresh',
  'search': 'search',
  'notifications': 'notifications',
  'settings': 'settings',
  'info.circle': 'info',
  'warning': 'warning',
  'error': 'error',
  'wifi': 'wifi',
  'wifi.off': 'wifi-off',
  'pulse': 'favorite',
  'sync': 'sync',
  'close-circle': 'cancel',
  'checkmark-circle': 'check-circle',
  'list.bullet.clipboard': 'assignment',
  'add': 'add',
  'close-outline': 'close',
} as IconMapping;

/**
 * An icon component that uses native SF Symbols on iOS, and Material Icons on Android and web.
 * This ensures a consistent look across platforms, and optimal resource usage.
 * Icon `name`s are based on SF Symbols and require manual mapping to Material Icons.
 */
export const IconSymbol = React.memo(({
  name,
  size = 24,
  color,
  style,
}: {
  name: IconSymbolName;
  size?: number;
  color: string | OpaqueColorValue;
  style?: StyleProp<TextStyle>;
  weight?: SymbolWeight;
}) => {
  return <MaterialIcons color={color} size={size} name={MAPPING[name]} style={style} />;
});

IconSymbol.displayName = 'IconSymbol';
