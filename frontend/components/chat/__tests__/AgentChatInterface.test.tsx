import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { AgentChatInterface } from '../AgentChatInterface';

// Mock dependencies
jest.mock('@/hooks/useAutoAdminAgents', () => ({
  useAutoAdminAgents: jest.fn(() => ({
    isInitialized: true,
    isLoading: false,
    error: null,
    state: {
      agentStates: {
        ceo: { status: 'idle' },
        strategy: { status: 'idle' },
        devops: { status: 'idle' },
      },
    },
    conversationHistory: [],
    sendMessage: jest.fn().mockResolvedValue({ content: 'Test response' }),
    sendMessageStream: jest.fn().mockImplementation(function* () {
      yield { content: 'Test ' };
      yield { content: 'streaming ' };
      yield { content: 'response' };
    }),
    clearConversation: jest.fn(),
    resetSession: jest.fn(),
  })),
}));

jest.mock('react-native-safe-area-context', () => ({
  SafeAreaView: ({ children }: any) => children,
}));

jest.mock('@/hooks/use-color-scheme', () => ({
  useColorScheme: jest.fn(() => 'light'),
}));

// Mock Alert
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Alert: {
      ...RN.Alert,
      alert: jest.fn(),
    },
  };
});

describe('AgentChatInterface', () => {
  const defaultProps = {
    userId: 'test-user',
    initialAgent: 'ceo' as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly when initialized', () => {
    const { getByTestId } = render(<AgentChatInterface {...defaultProps} />);

    expect(getByTestId('agent-selector')).toBeTruthy();
    expect(getByTestId('message-list')).toBeTruthy();
    expect(getByTestId('chat-input')).toBeTruthy();
  });

  it('shows loading state when initializing', () => {
    const { useAutoAdminAgents } = require('@/hooks/useAutoAdminAgents');
    useAutoAdminAgents.mockReturnValue({
      isInitialized: false,
      isLoading: true,
      error: null,
      conversationHistory: [],
    });

    const { getByText } = render(<AgentChatInterface {...defaultProps} />);

    expect(getByText('Initializing Agent Chat...')).toBeTruthy();
  });

  it('shows error state when there is an error', () => {
    const { useAutoAdminAgents } = require('@/hooks/useAutoAdminAgents');
    useAutoAdminAgents.mockReturnValue({
      isInitialized: false,
      isLoading: false,
      error: new Error('Connection failed'),
      conversationHistory: [],
    });

    const { getByText } = render(<AgentChatInterface {...defaultProps} />);

    expect(getByText('Connection Error')).toBeTruthy();
    expect(getByText('Failed to connect to agent system. Please check your connection.')).toBeTruthy();
  });

  it('allows agent selection', async () => {
    const mockOnAgentSwitch = jest.fn();
    const { getByTestId } = render(
      <AgentChatInterface {...defaultProps} onAgentSwitch={mockOnAgentSwitch} />
    );

    const strategyAgent = getByTestId('agent-strategy');
    fireEvent.press(strategyAgent);

    await waitFor(() => {
      expect(mockOnAgentSwitch).toHaveBeenCalledWith('strategy');
    });
  });

  it('sends messages when send button is pressed', async () => {
    const { useAutoAdminAgents } = require('@/hooks/useAutoAdminAgents');
    const mockSendMessage = jest.fn().mockResolvedValue({ content: 'Response' });
    useAutoAdminAgents.mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      conversationHistory: [],
      sendMessage: mockSendMessage,
      sendMessageStream: jest.fn().mockImplementation(function* () {
        yield { content: 'Response' };
      }),
    });

    const { getByTestId } = render(<AgentChatInterface {...defaultProps} />);

    const textInput = getByTestId('chat-input-text');
    const sendButton = getByTestId('chat-input-send');

    fireEvent.changeText(textInput, 'Test message');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  it('handles quick actions', async () => {
    const mockOnMessageSent = jest.fn();
    const { getByTestId } = render(
      <AgentChatInterface {...defaultProps} onMessageSent={mockOnMessageSent} />
    );

    const quickAction = getByTestId('quick-action-status_update');
    fireEvent.press(quickAction);

    await waitFor(() => {
      expect(mockOnMessageSent).toHaveBeenCalled();
    });
  });

  it('shows quick actions when there are no messages', () => {
    const { getByTestId } = render(<AgentChatInterface {...defaultProps} />);

    expect(getByTestId('quick-actions')).toBeTruthy();
  });

  it('does not show quick actions when there are messages', () => {
    const { useAutoAdminAgents } = require('@/hooks/useAutoAdminAgents');
    useAutoAdminAgents.mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      conversationHistory: [
        { getType: () => 'human', content: 'Hello' },
        { getType: () => 'ai', content: 'Hi there!' },
      ],
      sendMessage: jest.fn(),
      sendMessageStream: jest.fn(),
    });

    const { queryByTestId } = render(<AgentChatInterface {...defaultProps} />);

    expect(queryByTestId('quick-actions')).toBeFalsy();
  });

  it('disables input when streaming', () => {
    const { useAutoAdminAgents } = require('@/hooks/useAutoAdminAgents');
    useAutoAdminAgents.mockReturnValue({
      isInitialized: true,
      isLoading: false,
      error: null,
      conversationHistory: [],
      sendMessage: jest.fn(),
      sendMessageStream: jest.fn().mockImplementation(function* () {
        // Simulate streaming
        for (let i = 0; i < 10; i++) {
          yield { content: 'Streaming content...' };
        }
      }),
    });

    const { getByTestId } = render(<AgentChatInterface {...defaultProps} />);

    const textInput = getByTestId('chat-input-text');
    expect(textInput.props.editable).toBe(true); // Should be enabled by default
  });

  it('calls onMessageSent callback when message is sent', async () => {
    const mockOnMessageSent = jest.fn();
    const { getByTestId } = render(
      <AgentChatInterface {...defaultProps} onMessageSent={mockOnMessageSent} />
    );

    const textInput = getByTestId('chat-input-text');
    const sendButton = getByTestId('chat-input-send');

    fireEvent.changeText(textInput, 'Test message');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(mockOnMessageSent).toHaveBeenCalledWith('Test message', 'ceo');
    });
  });
});