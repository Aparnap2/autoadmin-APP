/**
 * DailyCycleComponent
 * Implements the daily routine: morning planning, focus blocks, breaks, evening review
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface FocusBlock {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
  completed: boolean;
  task?: string;
}

interface DailyCycleProps {
  date: string;
  onCycleUpdate?: (cycle: any) => void;
}

const DailyCycleComponent: React.FC<DailyCycleProps> = ({ date, onCycleUpdate }) => {
  const [currentPhase, setCurrentPhase] = useState<'morning' | 'focus' | 'break' | 'evening' | null>(null);
  const [focusBlocks, setFocusBlocks] = useState<FocusBlock[]>([]);
  const [morningNotes, setMorningNotes] = useState('');
  const [eveningNotes, setEveningNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedFocusBlock, setSelectedFocusBlock] = useState<string | null>(null);

  // Initialize daily cycle
  useEffect(() => {
    initializeDailyCycle();
  }, [date]);

  const initializeDailyCycle = async () => {
    try {
      setLoading(true);
      
      // In a real app, this would fetch from the API
      // For now, create mock focus blocks
      const mockBlocks: FocusBlock[] = [
        {
          id: 'block_1',
          title: 'Morning Focus Block',
          startTime: '09:00',
          endTime: '10:30',
          completed: false,
        },
        {
          id: 'block_2',
          title: 'Afternoon Focus Block',
          startTime: '14:00',
          endTime: '15:30',
          completed: false,
        },
      ];

      setFocusBlocks(mockBlocks);
    } catch (error) {
      console.error('Error initializing daily cycle:', error);
    } finally {
      setLoading(false);
    }
  };

  const startMorningPlanning = () => {
    setCurrentPhase('morning');
    Alert.alert(
      'Morning Planning',
      'Review your tasks for today and set priorities',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Start',
          onPress: () => {
            // In a real app, this would start the morning planning process
            Alert.alert('Morning Planning Started');
          }
        }
      ]
    );
  };

  const startFocusBlock = (blockId: string) => {
    const block = focusBlocks.find(b => b.id === blockId);
    if (block && !block.completed) {
      setSelectedFocusBlock(blockId);
      Alert.alert(
        'Start Focus Block',
        `Starting: ${block.title} (${block.startTime} - ${block.endTime})`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Start',
            onPress: () => {
              // In a real app, would start a timer and track focus
              // Here we'll just mark it as completed
              setFocusBlocks(prev => 
                prev.map(b => 
                  b.id === blockId ? { ...b, completed: true } : b
                )
              );
              setSelectedFocusBlock(null);
              Alert.alert('Focus Block Completed!');
            }
          }
        ]
      );
    }
  };

  const startBreak = () => {
    setCurrentPhase('break');
    Alert.alert(
      'Take a Break',
      'Step away from your work. Come back refreshed!',
      [
        { text: 'OK', style: 'default' }
      ]
    );
  };

  const startEveningReview = () => {
    setCurrentPhase('evening');
    Alert.alert(
      'Evening Review',
      'Reflect on your day and plan for tomorrow',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Start',
          onPress: () => {
            // In a real app, this would start the evening review process
            Alert.alert('Evening Review Started');
          }
        }
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Initializing daily cycle...</Text>
      </View>
    );
  }

  const completedBlocks = focusBlocks.filter(b => b.completed).length;
  const totalBlocks = focusBlocks.length;
  const progressPercentage = totalBlocks > 0 ? Math.round((completedBlocks / totalBlocks) * 100) : 0;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>⏰ Daily Cycle</Text>
      
      {/* Progress Overview */}
      <View style={styles.progressContainer}>
        <Text style={styles.progressText}>
          Focus Blocks: {completedBlocks}/{totalBlocks} completed
        </Text>
        <View style={styles.progressBar}>
          <View 
            style={[
              styles.progressFill, 
              { width: `${progressPercentage}%` }
            ]} 
          />
        </View>
        <Text style={styles.progressPercentage}>{progressPercentage}% Complete</Text>
      </View>

      <ScrollView style={styles.content}>
        {/* Morning Planning */}
        <View style={styles.phaseContainer}>
          <View style={styles.phaseHeader}>
            <View style={styles.phaseIconContainer}>
              <Ionicons name="sunny" size={24} color="#FF9800" />
            </View>
            <View style={styles.phaseTitleContainer}>
              <Text style={styles.phaseTitle}>Morning Planning</Text>
              <Text style={styles.phaseTime}>7:00 - 8:00 AM</Text>
            </View>
          </View>
          <TouchableOpacity 
            style={styles.phaseButton} 
            onPress={startMorningPlanning}
          >
            <Text style={styles.phaseButtonText}>Start Planning</Text>
          </TouchableOpacity>
        </View>

        {/* Focus Blocks */}
        <View style={styles.focusBlocksContainer}>
          <Text style={styles.sectionTitle}>Focus Blocks</Text>
          {focusBlocks.map((block) => (
            <TouchableOpacity
              key={block.id}
              style={[
                styles.focusBlockItem,
                {
                  backgroundColor: block.completed ? '#E8F5E9' : '#FFF3E0',
                  borderColor: block.completed ? '#4CAF50' : '#FF9800',
                }
              ]}
              onPress={() => startFocusBlock(block.id)}
              disabled={block.completed || selectedFocusBlock === block.id}
            >
              <View style={styles.focusBlockContent}>
                <View style={styles.focusBlockHeader}>
                  <Text style={styles.focusBlockTitle}>{block.title}</Text>
                  <Ionicons 
                    name={block.completed ? "checkmark-circle" : "time"} 
                    size={20} 
                    color={block.completed ? "#4CAF50" : "#FF9800"} 
                  />
                </View>
                <Text style={styles.focusBlockTime}>
                  {block.startTime} - {block.endTime}
                </Text>
                {block.completed && (
                  <Text style={styles.completedText}>✅ Completed</Text>
                )}
                {selectedFocusBlock === block.id && (
                  <Text style={styles.activeText}>⏱️ Currently Active</Text>
                )}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Break Reminder */}
        <View style={styles.phaseContainer}>
          <View style={styles.phaseHeader}>
            <View style={styles.phaseIconContainer}>
              <Ionicons name="cafe" size={24} color="#2196F3" />
            </View>
            <View style={styles.phaseTitleContainer}>
              <Text style={styles.phaseTitle}>Break Time</Text>
              <Text style={styles.phaseTime}>Between focus blocks</Text>
            </View>
          </View>
          <TouchableOpacity 
            style={styles.phaseButton} 
            onPress={startBreak}
          >
            <Text style={styles.phaseButtonText}>Take Break</Text>
          </TouchableOpacity>
        </View>

        {/* Evening Review */}
        <View style={styles.phaseContainer}>
          <View style={styles.phaseHeader}>
            <View style={styles.phaseIconContainer}>
              <Ionicons name="moon" size={24} color="#795548" />
            </View>
            <View style={styles.phaseTitleContainer}>
              <Text style={styles.phaseTitle}>Evening Review</Text>
              <Text style={styles.phaseTime}>6:00 - 7:00 PM</Text>
            </View>
          </View>
          <TouchableOpacity 
            style={styles.phaseButton} 
            onPress={startEveningReview}
          >
            <Text style={styles.phaseButtonText}>Start Review</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    margin: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
    textAlign: 'center',
  },
  progressContainer: {
    marginBottom: 16,
  },
  progressText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 8,
  },
  progressBar: {
    height: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
    marginBottom: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 4,
  },
  progressPercentage: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  content: {
    maxHeight: 400,
  },
  phaseContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  phaseHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  phaseIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#e3f2fd',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  phaseTitleContainer: {
    flex: 1,
  },
  phaseTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  phaseTime: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  phaseButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  phaseButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  focusBlocksContainer: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  focusBlockItem: {
    borderWidth: 1,
    borderRadius: 8,
    marginBottom: 8,
    overflow: 'hidden',
  },
  focusBlockContent: {
    padding: 12,
  },
  focusBlockHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  focusBlockTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  focusBlockTime: {
    fontSize: 12,
    color: '#666',
  },
  completedText: {
    color: '#4CAF50',
    fontWeight: 'bold',
    marginTop: 4,
  },
  activeText: {
    color: '#FF9800',
    fontWeight: 'bold',
    marginTop: 4,
  },
  loadingContainer: {
    padding: 20,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
});

export default DailyCycleComponent;