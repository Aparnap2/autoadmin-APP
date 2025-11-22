/**
 * Virtual File System for AutoAdmin Agents
 * Provides a sandboxed file system environment for agents to work with
 * Integrates with Firebase for persistence and real-time sync
 */

import {
  VirtualFileSystem,
  VirtualFile,
  VirtualDirectory,
  SyncEvent,
  RealtimeConfig
} from './types';
import GraphMemoryService from '../../utils/firebase/graph-memory';
import FirestoreService from '../firebase/firestore.service';

export interface FileSystemEvent {
  type: 'file_created' | 'file_updated' | 'file_deleted' | 'directory_created' | 'directory_deleted';
  path: string;
  timestamp: Date;
  userId: string;
  agentId?: string;
  data?: any;
}

export interface FileSystemWatchers {
  [path: string]: Array<(event: FileSystemEvent) => void>;
}

export interface FileSystemStats {
  totalFiles: number;
  totalDirectories: number;
  totalSize: number;
  largestFile: string;
  mostRecentActivity: Date;
  fileTypes: Record<string, number>;
}

export interface FileOperation {
  id: string;
  type: 'read' | 'write' | 'delete' | 'create' | 'move' | 'copy';
  path: string;
  data?: any;
  timestamp: Date;
  userId: string;
  agentId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
}

export class VirtualFileSystemManager {
  private static instance: VirtualFileSystemManager;
  private fileSystem: VirtualFileSystem;
  private graphMemory: GraphMemoryService;
  private firestoreService: FirestoreService;
  private userId: string;
  private watchers: FileSystemWatchers = {};
  private operationQueue: FileOperation[] = [];
  private realtimeConfig: RealtimeConfig;
  private isProcessing = false;

  constructor(userId: string) {
    this.userId = userId;
    this.graphMemory = new GraphMemoryService();
    this.firestoreService = FirestoreService.getInstance();
    this.firestoreService.setUserId(userId);

    this.fileSystem = {
      files: new Map(),
      directories: new Map(),
      currentPath: '/',
    };

    this.realtimeConfig = {
      enabled: true,
      channels: ['filesystem'],
      syncStrategy: 'optimistic',
      conflictResolution: 'last_write_wins'
    };

    this.initializeFileSystem();
  }

  static getInstance(userId: string): VirtualFileSystemManager {
    if (!VirtualFileSystemManager.instance) {
      VirtualFileSystemManager.instance = new VirtualFileSystemManager(userId);
    }
    return VirtualFileSystemManager.instance;
  }

  /**
   * Initialize the virtual file system
   */
  private async initializeFileSystem(): Promise<void> {
    try {
      // Load existing file system state from Supabase
      await this.loadFileSystemState();

      // Set up basic directory structure
      await this.createDefaultDirectories();

      // Set up real-time synchronization
      this.setupRealtimeSync();

      console.log('Virtual File System initialized successfully');
    } catch (error) {
      console.error('Error initializing Virtual File System:', error);
    }
  }

  /**
   * Load file system state from Firebase
   */
  private async loadFileSystemState(): Promise<void> {
    try {
      const fileNodes = await this.graphMemory.getNodesByType('file');

      for (const fileNode of fileNodes) {
        if (fileNode.metadata?.filePath) {
          const file: VirtualFile = {
            path: fileNode.metadata.filePath,
            content: fileNode.content,
            type: fileNode.metadata?.type || 'document',
            lastModified: fileNode.timestamp,
            size: fileNode.content.length,
            metadata: fileNode.metadata,
          };

          this.fileSystem.files.set(fileNode.metadata.filePath, file);
        }
      }

      // Load directory structure from metadata
      await this.rebuildDirectoryStructure();

    } catch (error) {
      console.warn('Could not load file system state, starting with empty system:', error);
    }
  }

  /**
   * Create default directory structure
   */
  private async createDefaultDirectories(): Promise<void> {
    const defaultDirectories = [
      '/workspace',
      '/workspace/code',
      '/workspace/data',
      '/workspace/config',
      '/workspace/docs',
      '/workspace/temp',
      '/workspace/exports',
      '/workspace/backups'
    ];

    for (const dirPath of defaultDirectories) {
      if (!this.fileSystem.directories.has(dirPath)) {
        await this.createDirectory(dirPath, false);
      }
    }
  }

  /**
   * Set up real-time synchronization with Firebase
   */
  private setupRealtimeSync(): Promise<void> {
    // In a real implementation, would set up Firebase real-time listeners
    // For now, this is a placeholder
    return Promise.resolve();
  }

  /**
   * Rebuild directory structure from file paths
   */
  private async rebuildDirectoryStructure(): Promise<void> {
    const directories = new Set<string>();

    // Extract directories from file paths
    for (const filePath of this.fileSystem.files.keys()) {
      const parts = filePath.split('/');
      let currentPath = '';

      for (let i = 0; i < parts.length - 1; i++) {
        currentPath += '/' + parts[i];
        directories.add(currentPath);
      }
    }

    // Create directory entries
    for (const dirPath of directories) {
      if (!this.fileSystem.directories.has(dirPath)) {
        this.fileSystem.directories.set(dirPath, {
          path: dirPath,
          files: [],
          subdirectories: [],
          createdAt: new Date(),
          lastModified: new Date(),
        });
      }
    }
  }

  /**
   * File operations
   */
  async readFile(path: string): Promise<string> {
    const operation = this.createOperation('read', path);

    try {
      const file = this.fileSystem.files.get(path);
      if (!file) {
        throw new Error(`File not found: ${path}`);
      }

      operation.status = 'completed';
      await this.completeOperation(operation);

      return file.content;
    } catch (error) {
      operation.status = 'failed';
      operation.error = error as string;
      await this.completeOperation(operation);
      throw error;
    }
  }

  async writeFile(path: string, content: string, type: VirtualFile['type'] = 'document'): Promise<void> {
    const operation = this.createOperation('write', path, { content, type });

    try {
      const file: VirtualFile = {
        path,
        content,
        type,
        lastModified: new Date(),
        size: content.length,
        metadata: {},
      };

      this.fileSystem.files.set(path, file);

      // Update directory
      await this.updateDirectoryForFile(path);

      // Persist to Supabase
      await this.persistFile(file);

      // Emit event
      this.emitEvent({
        type: 'file_updated',
        path,
        timestamp: new Date(),
        userId: this.userId,
        data: { size: content.length, type }
      });

      operation.status = 'completed';
      await this.completeOperation(operation);

    } catch (error) {
      operation.status = 'failed';
      operation.error = error as string;
      await this.completeOperation(operation);
      throw error;
    }
  }

  async createFile(path: string, content: string = '', type: VirtualFile['type'] = 'document'): Promise<void> {
    if (this.fileSystem.files.has(path)) {
      throw new Error(`File already exists: ${path}`);
    }

    const operation = this.createOperation('create', path, { content, type });

    try {
      const file: VirtualFile = {
        path,
        content,
        type,
        lastModified: new Date(),
        size: content.length,
        metadata: {},
      };

      this.fileSystem.files.set(path, file);

      // Update directory
      await this.updateDirectoryForFile(path);

      // Persist to Supabase
      await this.persistFile(file);

      // Emit event
      this.emitEvent({
        type: 'file_created',
        path,
        timestamp: new Date(),
        userId: this.userId,
        data: { size: content.length, type }
      });

      operation.status = 'completed';
      await this.completeOperation(operation);

    } catch (error) {
      operation.status = 'failed';
      operation.error = error as string;
      await this.completeOperation(operation);
      throw error;
    }
  }

  async deleteFile(path: string): Promise<void> {
    const operation = this.createOperation('delete', path);

    try {
      const file = this.fileSystem.files.get(path);
      if (!file) {
        throw new Error(`File not found: ${path}`);
      }

      this.fileSystem.files.delete(path);

      // Update directory
      await this.removeFileFromDirectory(path);

      // Remove from Supabase
      await this.removeFileFromStorage(path);

      // Emit event
      this.emitEvent({
        type: 'file_deleted',
        path,
        timestamp: new Date(),
        userId: this.userId,
        data: { size: file.size }
      });

      operation.status = 'completed';
      await this.completeOperation(operation);

    } catch (error) {
      operation.status = 'failed';
      operation.error = error as string;
      await this.completeOperation(operation);
      throw error;
    }
  }

  async moveFile(oldPath: string, newPath: string): Promise<void> {
    const operation = this.createOperation('move', oldPath, { newPath });

    try {
      const file = this.fileSystem.files.get(oldPath);
      if (!file) {
        throw new Error(`File not found: ${oldPath}`);
      }

      if (this.fileSystem.files.has(newPath)) {
        throw new Error(`File already exists: ${newPath}`);
      }

      // Update file path
      const updatedFile: VirtualFile = {
        ...file,
        path: newPath,
        lastModified: new Date(),
      };

      this.fileSystem.files.delete(oldPath);
      this.fileSystem.files.set(newPath, updatedFile);

      // Update directories
      await this.removeFileFromDirectory(oldPath);
      await this.updateDirectoryForFile(newPath);

      // Persist changes
      await this.persistFile(updatedFile);
      await this.removeFileFromStorage(oldPath);

      // Emit events
      this.emitEvent({
        type: 'file_deleted',
        path: oldPath,
        timestamp: new Date(),
        userId: this.userId,
        data: { movedTo: newPath }
      });

      this.emitEvent({
        type: 'file_created',
        path: newPath,
        timestamp: new Date(),
        userId: this.userId,
        data: { movedFrom: oldPath }
      });

      operation.status = 'completed';
      await this.completeOperation(operation);

    } catch (error) {
      operation.status = 'failed';
      operation.error = error as string;
      await this.completeOperation(operation);
      throw error;
    }
  }

  /**
   * Directory operations
   */
  async createDirectory(path: string, persist: boolean = true): Promise<void> {
    if (this.fileSystem.directories.has(path)) {
      return; // Directory already exists
    }

    const directory: VirtualDirectory = {
      path,
      files: [],
      subdirectories: [],
      createdAt: new Date(),
      lastModified: new Date(),
    };

    this.fileSystem.directories.set(path, directory);

    if (persist) {
      // Persist to Supabase
      await this.graphMemory.addMemory(
        `Directory: ${path}`,
        'file',
        [],
        { path, type: 'directory', createdAt: directory.createdAt }
      );

      // Emit event
      this.emitEvent({
        type: 'directory_created',
        path,
        timestamp: new Date(),
        userId: this.userId
      });
    }
  }

  async deleteDirectory(path: string, recursive: boolean = false): Promise<void> {
    const directory = this.fileSystem.directories.get(path);
    if (!directory) {
      throw new Error(`Directory not found: ${path}`);
    }

    if (!recursive && (directory.files.length > 0 || directory.subdirectories.length > 0)) {
      throw new Error(`Directory not empty: ${path}`);
    }

    if (recursive) {
      // Delete all files and subdirectories
      for (const filePath of directory.files) {
        await this.deleteFile(filePath);
      }

      for (const subDirPath of directory.subdirectories) {
        await this.deleteDirectory(subDirPath, true);
      }
    }

    this.fileSystem.directories.delete(path);

    // Emit event
    this.emitEvent({
      type: 'directory_deleted',
      path,
      timestamp: new Date(),
      userId: this.userId
    });
  }

  /**
   * List operations
   */
  async listFiles(path: string = '/'): Promise<VirtualFile[]> {
    const files: VirtualFile[] = [];

    for (const [filePath, file] of this.fileSystem.files.entries()) {
      if (filePath.startsWith(path) && filePath !== path) {
        const relativePath = filePath.substring(path.length);
        if (!relativePath.includes('/')) {
          files.push(file);
        }
      }
    }

    return files.sort((a, b) => a.path.localeCompare(b.path));
  }

  async listDirectories(path: string = '/'): Promise<VirtualDirectory[]> {
    const directories: VirtualDirectory[] = [];

    for (const [dirPath, directory] of this.fileSystem.directories.entries()) {
      if (dirPath.startsWith(path) && dirPath !== path) {
        const relativePath = dirPath.substring(path.length);
        if (!relativePath.includes('/')) {
          directories.push(directory);
        }
      }
    }

    return directories.sort((a, b) => a.path.localeCompare(b.path));
  }

  async listAll(path: string = '/'): Promise<{ files: VirtualFile[]; directories: VirtualDirectory[] }> {
    return {
      files: await this.listFiles(path),
      directories: await this.listDirectories(path)
    };
  }

  /**
   * Search operations
   */
  async searchFiles(query: string, searchContent: boolean = false): Promise<VirtualFile[]> {
    const results: VirtualFile[] = [];
    const queryLower = query.toLowerCase();

    for (const [path, file] of this.fileSystem.files.entries()) {
      const pathMatch = path.toLowerCase().includes(queryLower);
      let contentMatch = false;

      if (searchContent) {
        contentMatch = file.content.toLowerCase().includes(queryLower);
      }

      if (pathMatch || contentMatch) {
        results.push(file);
      }
    }

    return results;
  }

  /**
   * File system statistics
   */
  async getStats(): Promise<FileSystemStats> {
    const files = Array.from(this.fileSystem.files.values());
    const directories = Array.from(this.fileSystem.directories.values());

    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    const largestFile = files.reduce((largest, file) =>
      file.size > (largest?.size || 0) ? file : largest, files[0]);

    const fileTypes: Record<string, number> = {};
    files.forEach(file => {
      fileTypes[file.type] = (fileTypes[file.type] || 0) + 1;
    });

    return {
      totalFiles: files.length,
      totalDirectories: directories.length,
      totalSize,
      largestFile: largestFile?.path || '',
      mostRecentActivity: new Date(), // Would track actual activity
      fileTypes
    };
  }

  /**
   * Event handling
   */
  watch(path: string, callback: (event: FileSystemEvent) => void): () => void {
    if (!this.watchers[path]) {
      this.watchers[path] = [];
    }

    this.watchers[path].push(callback);

    // Return unwatch function
    return () => {
      const callbacks = this.watchers[path];
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  private emitEvent(event: FileSystemEvent): void {
    // Notify specific path watchers
    const callbacks = this.watchers[event.path];
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error('Error in file system watcher callback:', error);
        }
      });
    }

    // Notify parent directory watchers
    const parts = event.path.split('/');
    for (let i = parts.length - 1; i > 0; i--) {
      const parentPath = parts.slice(0, i).join('/');
      const parentCallbacks = this.watchers[parentPath];
      if (parentCallbacks) {
        parentCallbacks.forEach(callback => {
          try {
            callback(event);
          } catch (error) {
            console.error('Error in parent directory watcher callback:', error);
          }
        });
      }
    }
  }

  /**
   * Persistence operations
   */
  private async persistFile(file: VirtualFile): Promise<void> {
    try {
      await this.graphMemory.addFileReference(
        file.path,
        `File: ${file.path}`,
        undefined,
        []
      );
    } catch (error) {
      console.error('Error persisting file:', error);
    }
  }

  private async removeFileFromStorage(path: string): Promise<void> {
    try {
      // In a real implementation, would remove from Supabase
      console.log('Removing file from storage:', path);
    } catch (error) {
      console.error('Error removing file from storage:', error);
    }
  }

  /**
   * Directory management helpers
   */
  private async updateDirectoryForFile(filePath: string): Promise<void> {
    const parts = filePath.split('/');
    const directoryPath = parts.slice(0, -1).join('/') || '/';

    await this.createDirectory(directoryPath, false);

    const directory = this.fileSystem.directories.get(directoryPath);
    if (directory && !directory.files.includes(filePath)) {
      directory.files.push(filePath);
      directory.lastModified = new Date();
    }
  }

  private async removeFileFromDirectory(filePath: string): Promise<void> {
    const parts = filePath.split('/');
    const directoryPath = parts.slice(0, -1).join('/') || '/';

    const directory = this.fileSystem.directories.get(directoryPath);
    if (directory) {
      const index = directory.files.indexOf(filePath);
      if (index > -1) {
        directory.files.splice(index, 1);
        directory.lastModified = new Date();
      }
    }
  }

  /**
   * Operation queue management
   */
  private createOperation(type: FileOperation['type'], path: string, data?: any): FileOperation {
    const operation: FileOperation = {
      id: `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      path,
      data,
      timestamp: new Date(),
      userId: this.userId,
      agentId: 'virtual_filesystem',
      status: 'pending'
    };

    this.operationQueue.push(operation);
    return operation;
  }

  private async completeOperation(operation: FileOperation): Promise<void> {
    // In a real implementation, would persist operation to Firestore
    // For now, just update in-memory state
    const index = this.operationQueue.indexOf(operation);
    if (index > -1) {
      this.operationQueue[index] = operation;
    }
  }

  /**
   * Get current file system state
   */
  getFileSystem(): VirtualFileSystem {
    return { ...this.fileSystem };
  }

  /**
   * Set current directory
   */
  setCurrentPath(path: string): void {
    this.fileSystem.currentPath = path;
  }

  /**
   * Get current directory
   */
  getCurrentPath(): string {
    return this.fileSystem.currentPath;
  }

  /**
   * Check if file exists
   */
  fileExists(path: string): boolean {
    return this.fileSystem.files.has(path);
  }

  /**
   * Check if directory exists
   */
  directoryExists(path: string): boolean {
    return this.fileSystem.directories.has(path);
  }

  /**
   * Get file info
   */
  getFileInfo(path: string): VirtualFile | null {
    return this.fileSystem.files.get(path) || null;
  }

  /**
   * Get directory info
   */
  getDirectoryInfo(path: string): VirtualDirectory | null {
    return this.fileSystem.directories.get(path) || null;
  }

  /**
   * Clear entire file system (for testing/reset)
   */
  async clear(): Promise<void> {
    this.fileSystem.files.clear();
    this.fileSystem.directories.clear();
    this.fileSystem.currentPath = '/';
    await this.createDefaultDirectories();
  }

  /**
   * Export file system state
   */
  async export(): Promise<any> {
    return {
      files: Array.from(this.fileSystem.files.entries()),
      directories: Array.from(this.fileSystem.directories.entries()),
      currentPath: this.fileSystem.currentPath,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Import file system state
   */
  async import(exportedState: any): Promise<void> {
    this.fileSystem.files.clear();
    this.fileSystem.directories.clear();

    // Import files
    for (const [path, file] of exportedState.files) {
      this.fileSystem.files.set(path, file);
    }

    // Import directories
    for (const [path, directory] of exportedState.directories) {
      this.fileSystem.directories.set(path, directory);
    }

    this.fileSystem.currentPath = exportedState.currentPath || '/';
  }
}

export default VirtualFileSystemManager;