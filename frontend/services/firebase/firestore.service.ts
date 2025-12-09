import {
  db,
  collection,
  doc,
  addDoc,
  updateDoc,
  deleteDoc,
  getDoc,
  getDocs,
  query,
  where,
  orderBy,
  limit,
  Timestamp,
  DocumentData,
  QuerySnapshot,
  Query
} from './config';

export interface AgentMessage {
  id?: string;
  sessionId: string;
  agentId: string;
  content: string;
  type: 'user' | 'agent';
  timestamp: Timestamp;
  metadata?: Record<string, any>;
}

export interface AgentState {
  id?: string;
  sessionId: string;
  agentId: string;
  state: Record<string, any>;
  updatedAt: Timestamp;
  createdAt: Timestamp;
}

export class FirestoreService {
  private static instance: FirestoreService;
  private userId: string = 'default_session';

  static getInstance(): FirestoreService {
    if (!FirestoreService.instance) {
      FirestoreService.instance = new FirestoreService();
    }
    return FirestoreService.instance;
  }

  // Set the current session/user ID
  setUserId(sessionId: string): void {
    this.userId = sessionId;
  }

  // Get the current session/user ID
  getUserId(): string {
    return this.userId;
  }

  // Message operations
  async saveMessage(message: Omit<AgentMessage, 'id' | 'timestamp'>): Promise<string> {
    try {
      const messageWithTimestamp = {
        ...message,
        sessionId: this.userId,
        timestamp: Timestamp.now()
      };

      const docRef = await addDoc(collection(db, 'messages'), messageWithTimestamp);
      return docRef.id;
    } catch (error) {
      console.error('Error saving message:', error);
      throw error;
    }
  }

  async getMessages(
    sessionId?: string,
    agentId?: string,
    limitCount: number = 50
  ): Promise<AgentMessage[]> {
    try {
      let q: Query;
      const messagesCollection = collection(db, 'messages');
      const currentSessionId = sessionId || this.userId;

      if (agentId) {
        q = query(
          messagesCollection,
          where('sessionId', '==', currentSessionId),
          where('agentId', '==', agentId),
          orderBy('timestamp', 'desc'),
          limit(limitCount)
        );
      } else {
        q = query(
          messagesCollection,
          where('sessionId', '==', currentSessionId),
          orderBy('timestamp', 'desc'),
          limit(limitCount)
        );
      }

      const querySnapshot: QuerySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as AgentMessage[];
    } catch (error) {
      console.error('Error getting messages:', error);
      throw error;
    }
  }

  // Agent state operations
  async saveAgentState(state: Omit<AgentState, 'id' | 'updatedAt' | 'createdAt'>): Promise<string> {
    try {
      const stateWithTimestamps = {
        ...state,
        sessionId: this.userId,
        updatedAt: Timestamp.now(),
        createdAt: Timestamp.now()
      };

      const docRef = await addDoc(collection(db, 'agentStates'), stateWithTimestamps);
      return docRef.id;
    } catch (error) {
      console.error('Error saving agent state:', error);
      throw error;
    }
  }

  async updateAgentState(id: string, updates: Partial<AgentState>): Promise<void> {
    try {
      const docRef = doc(db, 'agentStates', id);
      await updateDoc(docRef, {
        ...updates,
        updatedAt: Timestamp.now()
      });
    } catch (error) {
      console.error('Error updating agent state:', error);
      throw error;
    }
  }

  async getAgentState(sessionId?: string, agentId?: string): Promise<AgentState | null> {
    try {
      const currentSessionId = sessionId || this.userId;
      const currentAgentId = agentId || 'default_agent';

      const q = query(
        collection(db, 'agentStates'),
        where('sessionId', '==', currentSessionId),
        where('agentId', '==', currentAgentId),
        orderBy('updatedAt', 'desc'),
        limit(1)
      );

      const querySnapshot: QuerySnapshot = await getDocs(q);
      if (querySnapshot.empty) {
        return null;
      }

      const doc = querySnapshot.docs[0];
      return {
        id: doc.id,
        ...doc.data()
      } as AgentState;
    } catch (error) {
      console.error('Error getting agent state:', error);
      throw error;
    }
  }

  // Generic document operations
  async getDocument(collectionName: string, docId: string): Promise<DocumentData | null> {
    try {
      const docRef = doc(db, collectionName, docId);
      const docSnap = await getDoc(docRef);

      if (docSnap.exists()) {
        return docSnap.data();
      }
      return null;
    } catch (error) {
      console.error(`Error getting document ${docId} from ${collectionName}:`, error);
      throw error;
    }
  }

  async updateDocument(collectionName: string, docId: string, updates: DocumentData): Promise<void> {
    try {
      const docRef = doc(db, collectionName, docId);
      await updateDoc(docRef, updates);
    } catch (error) {
      console.error(`Error updating document ${docId} in ${collectionName}:`, error);
      throw error;
    }
  }

  async deleteDocument(collectionName: string, docId: string): Promise<void> {
    try {
      const docRef = doc(db, collectionName, docId);
      await deleteDoc(docRef);
    } catch (error) {
      console.error(`Error deleting document ${docId} from ${collectionName}:`, error);
      throw error;
    }
  }
}

export default FirestoreService;