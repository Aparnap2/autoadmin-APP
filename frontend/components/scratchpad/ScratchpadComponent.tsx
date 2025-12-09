/**
 * Scratchpad Component
 * Markdown-enabled notes linked to tasks
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface ScratchpadNote {
  id: string;
  title: string;
  content: string;
  taskId?: string;
  createdAt: string;
  updatedAt: string;
}

interface ScratchpadComponentProps {
  taskId?: string;
  onNoteSaved?: (note: ScratchpadNote) => void;
}

const ScratchpadComponent: React.FC<ScratchpadComponentProps> = ({ taskId, onNoteSaved }) => {
  const [notes, setNotes] = useState<ScratchpadNote[]>([]);
  const [currentNote, setCurrentNote] = useState<ScratchpadNote | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Load notes - in a real app, this would fetch from API
  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    // Mock data loading
    const mockNotes: ScratchpadNote[] = [
      {
        id: 'note_1',
        title: 'Project Ideas',
        content: '# E-commerce Platform\n\n## Features:\n- Product catalog\n- Shopping cart\n- Payment processing\n\n## Considerations:\n- Security requirements\n- Performance optimization',
        taskId: taskId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: 'note_2',
        title: 'Meeting Notes',
        content: '## Team Meeting - 2024-01-15\n\n- Discussed API integration\n- Planned next sprint\n- Assigned tasks to team members',
        taskId: taskId,
        createdAt: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
        updatedAt: new Date(Date.now() - 86400000).toISOString(),
      },
    ];
    
    setNotes(mockNotes);
    if (mockNotes.length > 0) {
      loadNote(mockNotes[0]);
    }
  };

  const loadNote = (note: ScratchpadNote) => {
    setCurrentNote(note);
    setTitle(note.title);
    setContent(note.content);
    setIsEditing(false);
  };

  const createNewNote = () => {
    const newNote: ScratchpadNote = {
      id: `note_${Date.now()}`,
      title: 'Untitled Note',
      content: '# New Note\n\nStart writing here...',
      taskId: taskId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    setCurrentNote(newNote);
    setTitle(newNote.title);
    setContent(newNote.content);
    setIsEditing(true);
    setNotes(prev => [newNote, ...prev]);
  };

  const saveNote = () => {
    if (!currentNote) return;

    const updatedNote: ScratchpadNote = {
      ...currentNote,
      title,
      content,
      updatedAt: new Date().toISOString(),
    };

    // Update the notes list
    setNotes(prev => 
      prev.map(note => 
        note.id === updatedNote.id ? updatedNote : note
      )
    );

    setCurrentNote(updatedNote);
    setIsEditing(false);
    onNoteSaved?.(updatedNote);
  };

  const deleteNote = (noteId: string) => {
    Alert.alert(
      'Delete Note',
      'Are you sure you want to delete this note?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            setNotes(prev => prev.filter(note => note.id !== noteId));
            if (currentNote?.id === noteId) {
              setCurrentNote(null);
              setTitle('');
              setContent('');
              setIsEditing(false);
            }
          }
        }
      ]
    );
  };

  const formatContent = (text: string) => {
    // Simple markdown formatting for demonstration
    // In a real app, use a proper markdown library
    return text;
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.header}>
        <Text style={styles.title}>📝 Scratchpad</Text>
        <TouchableOpacity style={styles.newNoteButton} onPress={createNewNote}>
          <Ionicons name="add" size={20} color="white" />
          <Text style={styles.newNoteButtonText}>New Note</Text>
        </TouchableOpacity>
      </View>

      {notes.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="document" size={48} color="#9E9E9E" />
          <Text style={styles.emptyTitle}>No Notes Yet</Text>
          <Text style={styles.emptySubtitle}>Create your first note to get started</Text>
          <TouchableOpacity style={styles.createButton} onPress={createNewNote}>
            <Text style={styles.createButtonText}>Create Note</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.contentContainer}>
          {/* Notes List */}
          <View style={styles.notesList}>
            {notes.map(note => (
              <TouchableOpacity
                key={note.id}
                style={[
                  styles.noteItem,
                  currentNote?.id === note.id && styles.selectedNoteItem
                ]}
                onPress={() => loadNote(note)}
              >
                <Text style={styles.noteTitle} numberOfLines={1}>
                  {note.title}
                </Text>
                <Text style={styles.notePreview} numberOfLines={2}>
                  {note.content.substring(0, 50)}...
                </Text>
                <Text style={styles.noteDate}>
                  {new Date(note.updatedAt).toLocaleDateString()}
                </Text>
                <TouchableOpacity 
                  style={styles.deleteButton} 
                  onPress={(e) => {
                    e.stopPropagation();
                    deleteNote(note.id);
                  }}
                >
                  <Ionicons name="trash" size={16} color="#F44336" />
                </TouchableOpacity>
              </TouchableOpacity>
            ))}
          </View>

          {/* Note Editor/Viewer */}
          {currentNote ? (
            <View style={styles.noteEditor}>
              {isEditing ? (
                <>
                  <TextInput
                    style={styles.titleInput}
                    value={title}
                    onChangeText={setTitle}
                    placeholder="Note title..."
                  />
                  <TextInput
                    style={styles.contentInput}
                    value={content}
                    onChangeText={setContent}
                    placeholder="Start writing your note..."
                    multiline
                    textAlignVertical="top"
                  />
                  <View style={styles.editorActions}>
                    <TouchableOpacity style={styles.cancelButton} onPress={() => {
                      if (currentNote) loadNote(currentNote);
                      else setIsEditing(false);
                    }}>
                      <Text style={styles.cancelButtonText}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.saveButton} onPress={saveNote}>
                      <Text style={styles.saveButtonText}>Save</Text>
                    </TouchableOpacity>
                  </View>
                </>
              ) : (
                <>
                  <View style={styles.viewHeader}>
                    <Text style={styles.viewTitle}>{title}</Text>
                    <TouchableOpacity onPress={() => setIsEditing(true)}>
                      <Ionicons name="create" size={24} color="#007AFF" />
                    </TouchableOpacity>
                  </View>
                  <ScrollView style={styles.noteContent}>
                    <Text style={styles.formattedContent}>
                      {formatContent(content)}
                    </Text>
                  </ScrollView>
                </>
              )}
            </View>
          ) : (
            <View style={styles.noNoteSelected}>
              <Ionicons name="document-text" size={48} color="#9E9E9E" />
              <Text style={styles.noNoteText}>Select a note to view</Text>
              <Text style={styles.noNoteSubtext}>or create a new note</Text>
            </View>
          )}
        </View>
      )}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  newNoteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  newNoteButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  contentContainer: {
    flex: 1,
    flexDirection: 'row',
  },
  notesList: {
    width: '40%',
    backgroundColor: 'white',
    borderRightWidth: 1,
    borderRightColor: '#e0e0e0',
  },
  noteItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  selectedNoteItem: {
    backgroundColor: '#e3f2fd',
    borderLeftWidth: 4,
    borderLeftColor: '#2196F3',
  },
  noteTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  notePreview: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  noteDate: {
    fontSize: 12,
    color: '#999',
  },
  deleteButton: {
    position: 'absolute',
    top: 8,
    right: 8,
  },
  noteEditor: {
    flex: 1,
    backgroundColor: 'white',
  },
  titleInput: {
    padding: 16,
    fontSize: 18,
    fontWeight: 'bold',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  contentInput: {
    flex: 1,
    padding: 16,
    fontSize: 16,
    textAlignVertical: 'top',
  },
  editorActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  cancelButtonText: {
    color: '#666',
    fontWeight: 'bold',
  },
  saveButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
  },
  saveButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  viewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  viewTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  noteContent: {
    flex: 1,
    padding: 16,
  },
  formattedContent: {
    fontSize: 16,
    lineHeight: 24,
  },
  noNoteSelected: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  noNoteText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#666',
    marginTop: 16,
  },
  noNoteSubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#666',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
  },
  createButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 6,
    marginTop: 16,
  },
  createButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
});

export default ScratchpadComponent;