# Agent Chat Interface

A comprehensive chat interface for interacting with AutoAdmin AI agents (CEO, Strategy, DevOps).

## Features

- **Multi-Agent Support**: Switch between CEO, Strategy, and DevOps agents
- **Real-time Streaming**: See agent responses as they're generated
- **Message History**: Persistent conversation history
- **Quick Actions**: Pre-defined prompts for common tasks
- **Voice Input Support**: Placeholder for voice recording functionality
- **File Attachments**: Placeholder for file upload functionality
- **Message Actions**: Copy, delete, and share messages
- **Agent Status Indicators**: Visual indicators for agent availability
- **Responsive Design**: Optimized for mobile devices
- **Dark Mode Support**: Automatic theme switching

## Components

### AgentChatInterface
Main chat component that orchestrates all other chat components.

**Props:**
- `userId: string` - User identifier for session management
- `initialAgent?: 'ceo' | 'strategy' | 'devops'` - Default agent selection
- `onMessageSent?: (message: string, agentType: string) => void` - Callback for sent messages
- `onAgentSwitch?: (agentType: 'ceo' | 'strategy' | 'devops') => void` - Callback for agent changes
- `style?: any` - Additional styling

### MessageBubble
Individual message component with user/agent differentiation.

**Props:**
- `message: Message` - Message data
- `isStreaming?: boolean` - Show streaming cursor
- `onPress?: () => void` - Tap handler
- `onLongPress?: () => void` - Long press handler
- `showTimestamp?: boolean` - Show message timestamp
- `showAgent?: boolean` - Show agent information

### ChatInput
Input field with send, voice, and attachment buttons.

**Props:**
- `value: string` - Current input value
- `onChangeText: (text: string) => void` - Text change handler
- `onSend: () => void` - Send button handler
- `onClearConversation?: () => void` - Clear conversation handler
- `isDisabled?: boolean` - Disable input state
- `placeholder?: string` - Input placeholder text
- `maxLength?: number` - Maximum character count

### AgentSelector
Agent selection interface with status indicators.

**Props:**
- `selectedAgent: 'ceo' | 'strategy' | 'devops'` - Currently selected agent
- `onAgentChange: (agent: 'ceo' | 'strategy' | 'devops') => void` - Agent change handler
- `isDisabled?: boolean` - Disable selection
- `agentStatus?: any` - Agent status from hook

### QuickActions
Horizontal scrollable quick action buttons.

**Props:**
- `actions: QuickAction[]` - Array of quick action objects
- `onActionPress: (action: QuickAction) => void` - Action press handler
- `isDisabled?: boolean` - Disable actions
- `maxColumns?: number` - Maximum columns in grid

## Usage Example

```tsx
import React, { useState } from 'react';
import { AgentChatInterface } from '@/components/chat';

export function ChatScreen() {
  const [selectedAgent, setSelectedAgent] = useState('ceo');

  return (
    <AgentChatInterface
      userId="user-123"
      initialAgent={selectedAgent}
      onAgentSwitch={setSelectedAgent}
      onMessageSent={(message, agent) => {
        console.log(`Message sent to ${agent}:`, message);
      }}
    />
  );
}
```

## Integration with useAutoAdminAgents

The chat interface is designed to work seamlessly with the `useAutoAdminAgents` hook:

```tsx
import { useAutoAdminAgents } from '@/hooks/useAutoAdminAgents';
import { AgentChatInterface } from '@/components/chat';

export function ChatWrapper() {
  const agents = useAutoAdminAgents({
    userId: 'user-123',
    autoInitialize: true,
    enableStreaming: true,
  });

  return (
    <AgentChatInterface
      userId="user-123"
      onMessageSent={agents.sendMessage}
    />
  );
}
```

## Agent Types

### CEO Agent
- **Color**: Blue (#0a7ea4)
- **Icon**: 👔 person.crop.circle
- **Specializes in**: Strategic oversight, system status, high-level decisions

### Strategy Agent
- **Color**: Pink (#e91e63)
- **Icon**: 📊 chart.bar
- **Specializes in**: Marketing analysis, financial planning, business strategy

### DevOps Agent
- **Color**: Green (#4caf50)
- **Icon**: ⚙️ gear
- **Specializes in**: Technical operations, code review, system performance

## Message Types

### User Messages
- Right-aligned
- Blue background
- Shows timestamp

### Agent Messages
- Left-aligned
- Light background with colored left border
- Shows agent icon and name
- Timestamp on the left
- Support for streaming responses

## Styling

The components use React Native's StyleSheet with support for:
- Dark mode automatic switching
- Color scheme awareness
- Responsive sizing
- Smooth animations
- Accessibility considerations

## Testing

Comprehensive test suite included:
- Component rendering tests
- User interaction tests
- State management tests
- Accessibility tests

Run tests with:
```bash
npm test -- AgentChatInterface
```

## Future Enhancements

- Voice input implementation
- File upload support
- Message search and filtering
- Conversation export
- Multi-language support
- Custom themes
- Message reactions
- Agent collaboration mode