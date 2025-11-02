"""
Unit tests for utility functions.
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add api directory to path
api_path = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_path))

from utils import SessionManager, sanitize_html, validate_file_extension, format_file_size


class TestSessionManager:
    """Tests for SessionManager class."""
    
    def test_create_session(self):
        """Test session creation."""
        manager = SessionManager()
        session_id = manager.create_session()
        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in manager.sessions
    
    def test_get_session(self):
        """Test getting a session."""
        manager = SessionManager()
        session_id = manager.create_session()
        session = manager.get_session(session_id)
        assert session is not None
        assert "created_at" in session
        assert "questions" in session
        assert "documents" in session
    
    def test_get_nonexistent_session(self):
        """Test getting a non-existent session."""
        manager = SessionManager()
        session = manager.get_session("nonexistent-id")
        assert session is None
    
    def test_delete_session(self):
        """Test deleting a session."""
        manager = SessionManager()
        session_id = manager.create_session()
        assert manager.delete_session(session_id) is True
        assert session_id not in manager.sessions
    
    def test_delete_nonexistent_session(self):
        """Test deleting a non-existent session."""
        manager = SessionManager()
        assert manager.delete_session("nonexistent-id") is False
    
    def test_session_cleanup(self):
        """Test session cleanup."""
        manager = SessionManager()
        session_id = manager.create_session()
        
        # Make session old
        manager.sessions[session_id]["last_accessed"] = datetime.now() - timedelta(hours=25)
        
        # Cleanup
        count = manager.cleanup_expired_sessions()
        assert count == 1
        assert session_id not in manager.sessions
    
    def test_get_session_count(self):
        """Test getting session count."""
        manager = SessionManager()
        assert manager.get_session_count() == 0
        
        manager.create_session()
        assert manager.get_session_count() == 1
        
        manager.create_session()
        assert manager.get_session_count() == 2
    
    def test_get_session_status(self):
        """Test getting session status."""
        manager = SessionManager()
        session_id = manager.create_session()
        status = manager.get_session_status(session_id)
        
        assert status is not None
        assert status["session_id"] == session_id
        assert "created_at" in status
        assert "document_count" in status
        assert status["document_count"] == 0


class TestSanitizeHTML:
    """Tests for HTML sanitization."""
    
    def test_sanitize_basic(self):
        """Test basic HTML sanitization."""
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_sanitize_quotes(self):
        """Test quote sanitization."""
        result = sanitize_html('Test "quote" and \'single\'')
        assert '&quot;' in result
        assert '&#39;' in result
    
    def test_sanitize_empty(self):
        """Test empty string sanitization."""
        result = sanitize_html("")
        assert result == ""
    
    def test_sanitize_none(self):
        """Test None sanitization."""
        result = sanitize_html(None)
        assert result == ""


class TestValidateFileExtension:
    """Tests for file extension validation."""
    
    def test_valid_extensions(self):
        """Test valid file extensions."""
        assert validate_file_extension("document.txt") is True
        assert validate_file_extension("document.pdf") is True
        assert validate_file_extension("document.docx") is True
    
    def test_case_insensitive(self):
        """Test case insensitive validation."""
        assert validate_file_extension("document.TXT") is True
        assert validate_file_extension("document.PDF") is True
        assert validate_file_extension("document.DOCX") is True
    
    def test_invalid_extensions(self):
        """Test invalid file extensions."""
        assert validate_file_extension("document.doc") is False
        assert validate_file_extension("document.xlsx") is False
        assert validate_file_extension("document.jpg") is False
    
    def test_no_extension(self):
        """Test file with no extension."""
        assert validate_file_extension("document") is False


class TestFormatFileSize:
    """Tests for file size formatting."""
    
    def test_bytes(self):
        """Test bytes formatting."""
        result = format_file_size(512)
        assert "B" in result
    
    def test_kilobytes(self):
        """Test kilobytes formatting."""
        result = format_file_size(1024)
        assert "KB" in result
    
    def test_megabytes(self):
        """Test megabytes formatting."""
        result = format_file_size(1024 * 1024)
        assert "MB" in result
    
    def test_gigabytes(self):
        """Test gigabytes formatting."""
        result = format_file_size(1024 * 1024 * 1024)
        assert "GB" in result
