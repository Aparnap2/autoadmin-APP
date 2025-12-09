"""
Virtual File System for AutoAdmin agents.

This module provides a virtual file system that persists to Firebase,
allowing agents to maintain state across GitHub Actions runs.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import mimetypes

from ..services.firebase_service import FirebaseService


@dataclass
class VirtualFile:
    """Represents a file in the virtual file system."""
    path: str
    content: str
    content_type: str = "text/plain"
    last_modified: Optional[str] = None
    size: int = 0

    def __post_init__(self):
        """Initialize derived fields."""
        if self.last_modified is None:
            self.last_modified = datetime.utcnow().isoformat()
        if self.size == 0:
            self.size = len(self.content) if self.content else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


@dataclass
class DirectoryEntry:
    """Represents a directory entry in the virtual file system."""
    path: str
    type: str  # 'file' or 'directory'
    size: int = 0
    last_modified: Optional[str] = None


logger = logging.getLogger(__name__)


class VirtualFileSystem:
    """
    Virtual File System that persists to Firebase.

    Provides a familiar file system interface that agents can use
    to store files, maintain state, and coordinate between runs.
    """

    def __init__(self):
        """Initialize the virtual file system with Firebase service."""
        self.firebase_service = FirebaseService()
        self._cache: Dict[str, VirtualFile] = {}

    async def read_file(self, path: str) -> str:
        """
        Read the contents of a file.

        Args:
            path: File path

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            # Check cache first
            if path in self._cache:
                logger.debug(f"Reading {path} from cache")
                return self._cache[path].content

            # Load from Firebase
            file_data = await self.firebase_service.get_agent_file(path)

            if not file_data:
                raise FileNotFoundError(f"File not found: {path}")

            virtual_file = VirtualFile(
                path=file_data.path,
                content=file_data.content,
                content_type="text/plain",
                last_modified=file_data.last_modified,
                size=len(file_data.content) if file_data.content else 0
            )

            # Cache the file
            self._cache[path] = virtual_file

            logger.debug(f"Read {len(virtual_file.content)} bytes from {path}")
            return virtual_file.content

        except Exception as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            raise

    async def write_file(self, path: str, content: str, content_type: str = "text/plain") -> None:
        """
        Write content to a file.

        Args:
            path: File path
            content: Content to write
            content_type: MIME type of the content
        """
        try:
            virtual_file = VirtualFile(
                path=path,
                content=content,
                content_type=content_type
            )

            # Store in Firebase
            await self.firebase_service.store_agent_file(path, content)

            # Update cache
            self._cache[path] = virtual_file
            logger.debug(f"Wrote {len(content)} bytes to {path}")

        except Exception as e:
            logger.error(f"Error writing file {path}: {str(e)}")
            raise

    async def exists(self, path: str) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Path to check

        Returns:
            True if exists, False otherwise
        """
        try:
            # Check cache first
            if path in self._cache:
                return True

            # Check database
            result = self.supabase.table('agent_files').select('path').eq('path', path).execute()
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error checking existence of {path}: {str(e)}")
            return False

    async def list_directory(self, path: str = "/") -> List[DirectoryEntry]:
        """
        List files and directories in a given path.

        Args:
            path: Directory path to list

        Returns:
            List of directory entries
        """
        try:
            # Normalize path
            if not path.endswith('/'):
                path += '/'

            # Query files that start with the path
            result = self.supabase.table('agent_files').select('path, last_modified').execute()

            if not result.data:
                return []

            # Group files by directory
            entries = {}
            for file_data in result.data:
                file_path = file_data['path']
                if file_path.startswith(path):
                    # Get the relative path from the directory
                    relative_path = file_path[len(path):]
                    parts = relative_path.split('/')

                    if len(parts) == 1:
                        # It's a file in this directory
                        entries[relative_path] = DirectoryEntry(
                            path=file_path,
                            type='file',
                            size=0,  # Size will be updated when we read the file
                            last_modified=file_data.get('last_modified')
                        )
                    elif len(parts) > 1:
                        # It's a subdirectory
                        subdir = parts[0]
                        if subdir not in entries:
                            entries[subdir] = DirectoryEntry(
                                path=f"{path}{subdir}",
                                type='directory',
                                size=0,
                                last_modified=None
                            )

            return list(entries.values())

        except Exception as e:
            logger.error(f"Error listing directory {path}: {str(e)}")
            return []

    async def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: File path to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.supabase.table('agent_files').delete().eq('path', path).execute()

            if result.data and len(result.data) > 0:
                # Remove from cache
                self._cache.pop(path, None)
                logger.debug(f"Deleted file {path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting file {path}: {str(e)}")
            return False

    async def get_file_info(self, path: str) -> Optional[DirectoryEntry]:
        """
        Get information about a file.

        Args:
            path: File path

        Returns:
            Directory entry with file info or None if not found
        """
        try:
            # Check cache first
            if path in self._cache:
                file_data = self._cache[path]
                return DirectoryEntry(
                    path=path,
                    type='file',
                    size=file_data.size,
                    last_modified=file_data.last_modified
                )

            # Check database
            result = self.supabase.table('agent_files').select('path, last_modified').eq('path', path).single().execute()

            if not result.data:
                return None

            # Get file content to determine size
            content = await self.read_file(path)

            return DirectoryEntry(
                path=path,
                type='file',
                size=len(content),
                last_modified=result.data.get('last_modified')
            )

        except Exception as e:
            logger.error(f"Error getting file info for {path}: {str(e)}")
            return None

    async def create_directory(self, path: str) -> None:
        """
        Create a directory.

        Note: This is a virtual file system, so directories are implicit
        based on file paths. This method is for compatibility.

        Args:
            path: Directory path to create
        """
        # Ensure path ends with '/'
        if not path.endswith('/'):
            path += '/'

        # Create a hidden directory marker file
        await self.write_file(f"{path}.directory_marker", "", "text/plain")
        logger.debug(f"Created directory {path}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get file system statistics.

        Returns:
            Dictionary with file system stats
        """
        try:
            result = self.supabase.table('agent_files').select('path, last_modified').execute()

            if not result.data:
                return {
                    'total_files': 0,
                    'total_size': 0,
                    'last_modified': None
                }

            total_size = 0
            for file_data in result.data:
                content = await self.read_file(file_data['path'])
                total_size += len(content)

            # Find most recent modification
            last_modified = max(
                (file_data.get('last_modified') for file_data in result.data),
                default=None
            )

            return {
                'total_files': len(result.data),
                'total_size': total_size,
                'last_modified': last_modified,
                'cached_files': len(self._cache)
            }

        except Exception as e:
            logger.error(f"Error getting file system stats: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'last_modified': None,
                'error': str(e)
            }

    async def export(self) -> Dict[str, str]:
        """
        Export all files in the virtual file system.

        Returns:
            Dictionary mapping file paths to contents
        """
        try:
            result = self.supabase.table('agent_files').select('path').execute()

            if not result.data:
                return {}

            export_data = {}
            for file_data in result.data:
                path = file_data['path']
                # Skip directory marker files
                if not path.endswith('/.directory_marker'):
                    content = await self.read_file(path)
                    export_data[path] = content

            return export_data

        except Exception as e:
            logger.error(f"Error exporting file system: {str(e)}")
            return {}

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.debug("Cleared file system cache")


class VirtualFileSystemTools:
    """
    Tools for agents to interact with the Virtual File System.

    Provides a clean interface for agents to perform file operations.
    """

    def __init__(self, virtual_fs: VirtualFileSystem):
        self.virtual_fs = virtual_fs

    async def save_document(self, path: str, content: str, document_type: str = "document") -> str:
        """
        Save a document to the virtual file system.

        Args:
            path: File path for the document
            content: Document content
            document_type: Type of document

        Returns:
            Confirmation message
        """
        try:
            await self.virtual_fs.write_file(path, content, "text/plain")
            return f"Document saved to {path}"
        except Exception as e:
            return f"Error saving document: {str(e)}"

    async def load_document(self, path: str) -> str:
        """
        Load a document from the virtual file system.

        Args:
            path: File path of the document

        Returns:
            Document content or error message
        """
        try:
            content = await self.virtual_fs.read_file(path)
            return content
        except FileNotFoundError:
            return f"Document not found: {path}"
        except Exception as e:
            return f"Error loading document: {str(e)}"

    async def list_workspace(self, path: str = "/") -> List[str]:
        """
        List files in the workspace.

        Args:
            path: Directory path to list

        Returns:
            List of file paths
        """
        try:
            entries = await self.virtual_fs.list_directory(path)
            return [entry.path for entry in entries]
        except Exception as e:
            return [f"Error listing workspace: {str(e)}"]

    async def workspace_stats(self) -> Dict[str, Any]:
        """
        Get workspace statistics.

        Returns:
            Dictionary with workspace stats
        """
        return await self.virtual_fs.get_stats()