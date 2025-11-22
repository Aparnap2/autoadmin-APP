"""
Unit tests for Virtual File System.

Tests the persistent file storage system for agents.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from agents.memory.virtual_filesystem import VirtualFileSystem, VirtualFileSystemTools, VirtualFile


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = Mock()
    client.table = Mock()
    return client


@pytest.fixture
def virtual_filesystem(mock_supabase_client):
    """Create a VirtualFileSystem instance with mocked Supabase."""
    with patch('agents.memory.virtual_filesystem.create_client', return_value=mock_supabase_client):
        return VirtualFileSystem(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )


@pytest.mark.asyncio
async def test_write_file(virtual_filesystem, mock_supabase_client):
    """Test writing a file to the virtual file system."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value.data = [
        {
            'path': 'test/file.txt',
            'content': 'Test file content',
            'last_modified': '2024-01-01T00:00:00Z'
        }
    ]

    # Test writing a file
    await virtual_filesystem.write_file(
        path='test/file.txt',
        content='Test file content',
        content_type='text/plain'
    )

    # Verify Supabase was called correctly
    mock_supabase_client.table.assert_called_with('agent_files')
    mock_supabase_client.table.return_value.upsert.assert_called_once()

    # Verify file is cached
    assert 'test/file.txt' in virtual_filesystem._cache
    cached_file = virtual_filesystem._cache['test/file.txt']
    assert cached_file.content == 'Test file content'
    assert cached_file.content_type == 'text/plain'


@pytest.mark.asyncio
async def test_read_file_from_cache(virtual_filesystem):
    """Test reading a file from cache."""
    # Add file to cache
    test_file = VirtualFile(
        path='test/cached.txt',
        content='Cached content',
        content_type='text/plain'
    )
    virtual_filesystem._cache['test/cached.txt'] = test_file

    # Test reading from cache
    content = await virtual_filesystem.read_file('test/cached.txt')

    # Verify content
    assert content == 'Cached content'


@pytest.mark.asyncio
async def test_read_file_from_database(virtual_filesystem, mock_supabase_client):
    """Test reading a file from database."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        'path': 'test/db_file.txt',
        'content': 'Database content',
        'last_modified': '2024-01-01T00:00:00Z'
    }

    # Test reading from database
    content = await virtual_filesystem.read_file('test/db_file.txt')

    # Verify content
    assert content == 'Database content'

    # Verify file is cached after reading
    assert 'test/db_file.txt' in virtual_filesystem._cache
    cached_file = virtual_filesystem._cache['test/db_file.txt']
    assert cached_file.content == 'Database content'


@pytest.mark.asyncio
async def test_read_file_not_found(virtual_filesystem, mock_supabase_client):
    """Test reading a file that doesn't exist."""
    # Mock Supabase response for not found
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No rows found")

    # Test reading non-existent file
    with pytest.raises(FileNotFoundError):
        await virtual_filesystem.read_file('non-existent.txt')


@pytest.mark.asyncio
async def test_file_exists(virtual_filesystem, mock_supabase_client):
    """Test checking if a file exists."""
    # Add file to cache
    virtual_filesystem._cache['existing.txt'] = VirtualFile(
        path='existing.txt',
        content='content'
    )

    # Test cached file exists
    assert await virtual_filesystem.exists('existing.txt') is True

    # Test non-cached file
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'path': 'db_existing.txt'}
    ]
    assert await virtual_filesystem.exists('db_existing.txt') is True

    # Test non-existent file
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    assert await virtual_filesystem.exists('non_existent.txt') is False


@pytest.mark.asyncio
async def test_list_directory(virtual_filesystem, mock_supabase_client):
    """Test listing files in a directory."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = [
        {'path': 'test/file1.txt', 'last_modified': '2024-01-01T00:00:00Z'},
        {'path': 'test/file2.txt', 'last_modified': '2024-01-01T00:00:00Z'},
        {'path': 'test/subdir/file3.txt', 'last_modified': '2024-01-01T00:00:00Z'}
    ]

    # Test listing directory
    entries = await virtual_filesystem.list_directory('test/')

    # Verify results
    assert len(entries) == 3

    # Check file entries
    file_entries = [e for e in entries if e.type == 'file']
    subdir_entries = [e for e in entries if e.type == 'directory']

    assert len(file_entries) == 1  # file1.txt
    assert len(subdir_entries) == 1  # subdir
    assert file_entries[0].path == 'test/file1.txt'
    assert subdir_entries[0].path == 'test/subdir'


@pytest.mark.asyncio
async def test_delete_file(virtual_filesystem, mock_supabase_client):
    """Test deleting a file."""
    # Add file to cache
    virtual_filesystem._cache['test/delete.txt'] = VirtualFile(
        path='test/delete.txt',
        content='to be deleted'
    )

    # Mock Supabase response
    mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [
        {'path': 'test/delete.txt'}
    ]

    # Test deleting file
    result = await virtual_filesystem.delete_file('test/delete.txt')

    # Verify deletion
    assert result is True
    assert 'test/delete.txt' not in virtual_filesystem._cache


@pytest.mark.asyncio
async def test_delete_file_not_found(virtual_filesystem, mock_supabase_client):
    """Test deleting a file that doesn't exist."""
    # Mock Supabase response for not found
    mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

    # Test deleting non-existent file
    result = await virtual_filesystem.delete_file('non_existent.txt')

    # Verify result
    assert result is False


@pytest.mark.asyncio
async def test_get_file_info(virtual_filesystem, mock_supabase_client):
    """Test getting file information."""
    # Add file to cache
    virtual_filesystem._cache['test/info.txt'] = VirtualFile(
        path='test/info.txt',
        content='test content',
        content_type='text/plain'
    )

    # Test getting cached file info
    info = await virtual_filesystem.get_file_info('test/info.txt')

    # Verify info
    assert info is not None
    assert info.path == 'test/info.txt'
    assert info.type == 'file'
    assert info.size == len('test content')


@pytest.mark.asyncio
async def test_get_stats(virtual_filesystem, mock_supabase_client):
    """Test getting file system statistics."""
    # Add files to cache
    virtual_filesystem._cache['file1.txt'] = VirtualFile(
        path='file1.txt',
        content='content1'
    )
    virtual_filesystem._cache['file2.txt'] = VirtualFile(
        path='file2.txt',
        content='longer content 2'
    )

    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = [
        {'path': 'file1.txt', 'last_modified': '2024-01-01T00:00:00Z'},
        {'path': 'file2.txt', 'last_modified': '2024-01-01T00:00:00Z'},
        {'path': 'file3.txt', 'last_modified': '2024-01-01T00:00:00Z'}
    ]

    # Mock read_file for size calculation
    virtual_filesystem.read_file = AsyncMock(side_effect=['file1 content', 'file2 content', 'file3 content'])

    # Test getting stats
    stats = await virtual_filesystem.get_stats()

    # Verify stats
    assert stats['total_files'] == 3
    assert stats['total_size'] == len('file1 content') + len('file2 content') + len('file3 content')
    assert stats['cached_files'] == 2


@pytest.mark.asyncio
async def test_export(virtual_filesystem, mock_supabase_client):
    """Test exporting the file system."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.execute.return_value.data = [
        {'path': 'file1.txt'},
        {'path': 'file2.txt'},
        {'path': 'subdir/.directory_marker'}
    ]

    # Mock read_file
    virtual_filesystem.read_file = AsyncMock(side_effect=['content1', 'content2', ''])

    # Test export
    export_data = await virtual_filesystem.export()

    # Verify export
    assert len(export_data) == 2  # Should skip directory marker
    assert 'file1.txt' in export_data
    assert 'file2.txt' in export_data
    assert export_data['file1.txt'] == 'content1'
    assert export_data['file2.txt'] == 'content2'


@pytest.mark.asyncio
async def test_clear_cache(virtual_filesystem):
    """Test clearing the file system cache."""
    # Add files to cache
    virtual_filesystem._cache['file1.txt'] = VirtualFile(path='file1.txt', content='content1')
    virtual_filesystem._cache['file2.txt'] = VirtualFile(path='file2.txt', content='content2')

    # Verify cache has files
    assert len(virtual_filesystem._cache) == 2

    # Clear cache
    virtual_filesystem.clear_cache()

    # Verify cache is empty
    assert len(virtual_filesystem._cache) == 0


@pytest.mark.asyncio
async def test_virtual_filesystem_tools_save_document(virtual_filesystem):
    """Test VirtualFileSystemTools save_document functionality."""
    tools = VirtualFileSystemTools(virtual_filesystem)

    # Mock write_file
    virtual_filesystem.write_file = AsyncMock()

    # Test saving document
    result = await tools.save_document(
        path='test/doc.md',
        content='# Test Document\n\nThis is a test.',
        document_type='markdown'
    )

    # Verify the result
    assert "Document saved to test/doc.md" in result
    virtual_filesystem.write_file.assert_called_once_with('test/doc.md', '# Test Document\n\nThis is a test.', 'text/plain')


@pytest.mark.asyncio
async def test_virtual_filesystem_tools_load_document(virtual_filesystem):
    """Test VirtualFileSystemTools load_document functionality."""
    tools = VirtualFileSystemTools(virtual_filesystem)

    # Test loading existing document
    virtual_filesystem.read_file = AsyncMock(return_value='# Test Document\n\nContent here.')

    result = await tools.load_document('test/doc.md')
    assert result == '# Test Document\n\nContent here.'

    # Test loading non-existent document
    virtual_filesystem.read_file = AsyncMock(side_effect=FileNotFoundError("File not found"))

    result = await tools.load_document('nonexistent.md')
    assert "Document not found: nonexistent.md" in result


@pytest.mark.asyncio
async def test_virtual_filesystem_tools_list_workspace(virtual_filesystem):
    """Test VirtualFileSystemTools list_workspace functionality."""
    tools = VirtualFileSystemTools(virtual_filesystem)

    # Mock list_directory
    virtual_filesystem.list_directory = AsyncMock(return_value=[
        Mock(path='file1.txt'),
        Mock(path='file2.txt'),
        Mock(path='subdir/')
    ])

    result = await tools.list_workspace('/')
    assert len(result) == 3
    assert 'file1.txt' in result
    assert 'file2.txt' in result
    assert 'subdir/' in result

    # Test error case
    virtual_filesystem.list_directory = AsyncMock(side_effect=Exception("Error"))

    result = await tools.list_workspace('/')
    assert len(result) == 1
    assert "Error listing workspace" in result[0]


@pytest.mark.asyncio
async def test_virtual_filesystem_tools_workspace_stats(virtual_filesystem):
    """Test VirtualFileSystemTools workspace_stats functionality."""
    tools = VirtualFileSystemTools(virtual_filesystem)

    # Mock get_stats
    expected_stats = {
        'total_files': 5,
        'total_size': 1024,
        'last_modified': '2024-01-01T00:00:00Z'
    }
    virtual_filesystem.get_stats = AsyncMock(return_value=expected_stats)

    result = await tools.workspace_stats()
    assert result == expected_stats


class TestVirtualFile:
    """Test the VirtualFile dataclass."""

    def test_virtual_file_creation(self):
        """Test creating a VirtualFile."""
        file = VirtualFile(
            path='test.txt',
            content='Test content'
        )

        assert file.path == 'test.txt'
        assert file.content == 'Test content'
        assert file.content_type == 'text/plain'  # Default value
        assert file.last_modified is not None  # Should be set automatically
        assert file.size == len('Test content')  # Should be calculated automatically

    def test_virtual_file_with_content_type(self):
        """Test creating a VirtualFile with specific content type."""
        file = VirtualFile(
            path='test.json',
            content='{"key": "value"}',
            content_type='application/json'
        )

        assert file.content_type == 'application/json'

    def test_virtual_file_to_dict(self):
        """Test converting VirtualFile to dictionary."""
        file = VirtualFile(
            path='test.txt',
            content='Test content',
            content_type='text/plain',
            last_modified='2024-01-01T00:00:00Z'
        )

        file_dict = file.to_dict()

        expected = {
            'path': 'test.txt',
            'content': 'Test content',
            'content_type': 'text/plain',
            'last_modified': '2024-01-01T00:00:00Z',
            'size': len('Test content')
        }

        assert file_dict == expected