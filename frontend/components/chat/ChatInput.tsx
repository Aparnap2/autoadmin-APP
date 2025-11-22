import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Keyboard,
} from 'react-native';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { IconSymbol } from '@/components/ui/icon-symbol';

interface ChatInputProps {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onClearConversation?: () => void;
  isDisabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  showClearButton?: boolean;
  style?: any;
}

export function ChatInput({
  value,
  onChangeText,
  onSend,
  onClearConversation,
  isDisabled = false,
  placeholder = 'Type your message...',
  maxLength = 2000,
  showClearButton = true,
  style,
}: ChatInputProps) {
  const colorScheme = useColorScheme();
  const [isFocused, setIsFocused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const inputRef = useRef<TextInput>(null);

  const handleSend = () => {
    if (value.trim() && !isDisabled) {
      onSend();
      inputRef.current?.blur();
    }
  };

  const handleKeyPress = (e: any) => {
    if (e.nativeEvent.key === 'Enter' && !e.nativeEvent.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceRecord = () => {
    setIsRecording(!isRecording);
    // Voice recording implementation would go here
    Alert.alert('Voice Input', 'Voice recording feature coming soon!');
  };

  const handleClearChat = () => {
    Alert.alert(
      'Clear Conversation',
      'Are you sure you want to clear all messages?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: onClearConversation,
        },
      ]
    );
  };

  const handleAttachFile = () => {
    Alert.alert('File Attachment', 'File attachment feature coming soon!');
  };

  useEffect(() => {
    const keyboardDidHideListener = Keyboard.addListener('keyboardDidHide', () => {
      setIsFocused(false);
    });

    return () => {
      keyboardDidHideListener.remove();
    };
  }, []);

  const inputStyle = [
    styles.input,
    {
      borderColor: isFocused
        ? '#66FCF1'
        : '#333',
      backgroundColor: '#1F2833',
      color: '#C5C6C7',
    },
  ];

  const containerStyle = [
    styles.container,
    {
      backgroundColor: '#0B0C10',
      borderTopColor: '#333',
    },
    style,
  ];

  const buttonStyle = [
    styles.button,
    {
      backgroundColor: isDisabled
        ? '#333'
        : '#66FCF1',
    },
  ];

  const secondaryButtonStyle = [
    styles.secondaryButton,
    {
      backgroundColor: colorScheme === 'dark' ? '#333' : '#f0f0f0',
    },
  ];

  return (
    <ThemedView style={containerStyle}>
      {/* Character Count */}
      {value.length > maxLength * 0.8 && (
        <View style={styles.characterCountContainer}>
          <ThemedText style={[
            styles.characterCount,
            {
              color: value.length >= maxLength ? '#e91e63' : '#666'
            }
          ]}>
            {value.length}/{maxLength}
          </ThemedText>
        </View>
      )}

      <View style={styles.inputContainer}>
        {/* Attach File Button */}
        <TouchableOpacity
          style={secondaryButtonStyle}
          onPress={handleAttachFile}
          disabled={isDisabled}
        >
          <IconSymbol
            name="paperclip"
            size={20}
            color={colorScheme === 'dark' ? '#fff' : '#333'}
          />
        </TouchableOpacity>

        {/* Text Input */}
        <TextInput
          ref={inputRef}
          style={inputStyle}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colorScheme === 'dark' ? '#888' : '#999'}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          multiline
          maxLength={maxLength}
          editable={!isDisabled}
          onSubmitEditing={handleSend}
          blurOnSubmit={false}
          returnKeyType="send"
          textAlignVertical="center"
          selectionColor="#66FCF1"
        />

        {/* Voice Record Button */}
        <TouchableOpacity
          style={[
            secondaryButtonStyle,
            isRecording && styles.recordingButton
          ]}
          onPress={handleVoiceRecord}
          disabled={isDisabled}
        >
          <IconSymbol
            name={isRecording ? "stop.circle.fill" : "mic.fill"}
            size={20}
            color={isRecording ? '#e91e63' : (colorScheme === 'dark' ? '#fff' : '#333')}
          />
        </TouchableOpacity>

        {/* Send Button */}
        <TouchableOpacity
          style={[
            buttonStyle,
            (!value.trim() || isDisabled) && styles.disabledButton
          ]}
          onPress={handleSend}
          disabled={!value.trim() || isDisabled}
        >
          <IconSymbol
            name="arrow.up.circle.fill"
            size={24}
            color="#fff"
          />
        </TouchableOpacity>
      </View>

      {/* Clear Conversation Button */}
      {showClearButton && (
        <View style={styles.clearContainer}>
          <TouchableOpacity onPress={handleClearChat} disabled={isDisabled}>
            <ThemedText style={[
              styles.clearButton,
              {
                color: isDisabled
                  ? (colorScheme === 'dark' ? '#555' : '#ccc')
                  : '#e91e63',
              }
            ]}>
              Clear Conversation
            </ThemedText>
          </TouchableOpacity>
        </View>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderTopWidth: 1,
  },
  characterCountContainer: {
    alignItems: 'flex-end',
    marginBottom: 4,
  },
  characterCount: {
    fontSize: 12,
    fontWeight: '500',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 16,
    lineHeight: 20,
    maxHeight: 100,
    minHeight: 44,
  },
  button: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  secondaryButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordingButton: {
    backgroundColor: '#ffebee',
    borderWidth: 2,
    borderColor: '#e91e63',
  },
  disabledButton: {
    opacity: 0.5,
    shadowOpacity: 0,
    elevation: 0,
  },
  clearContainer: {
    alignItems: 'center',
    marginTop: 8,
  },
  clearButton: {
    fontSize: 14,
    fontWeight: '500',
  },
});

export default ChatInput;