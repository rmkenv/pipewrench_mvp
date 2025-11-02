"""
Utility functions for PipeWrench AI application.
Includes logging setup, session management, and helper functions.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

from config import settings


# Configure logging
def setup_logging() -> logging.Logger:
    """Setup application logging with appropriate level and format."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger("pipewrench")
    logger.setLevel(log_level)
    
    return logger


# Initialize logger
logger = setup_logging()


class SessionManager:
    """Manage application sessions with automatic cleanup."""
    
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self._last_cleanup = datetime.now()
    
    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
            "questions": [],
            "documents": []
        }
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data and update last accessed time."""
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        session = self.sessions[session_id]
        session["last_accessed"] = datetime.now()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove sessions older than SESSION_TIMEOUT_HOURS."""
        now = datetime.now()
        timeout_delta = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
        
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session["last_accessed"] > timeout_delta
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        self._last_cleanup = now
        return len(expired)
    
    def maybe_cleanup(self) -> None:
        """Cleanup sessions if it's been long enough since last cleanup."""
        if datetime.now() - self._last_cleanup > timedelta(
            seconds=settings.SESSION_CLEANUP_INTERVAL_SECONDS
        ):
            self.cleanup_expired_sessions()
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)
    
    def get_session_status(self, session_id: str) -> Optional[dict]:
        """Get session status information."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "created_at": session["created_at"].isoformat(),
            "last_accessed": session["last_accessed"].isoformat(),
            "document_count": len(session["documents"]),
            "question_count": len(session["questions"]),
        }


def sanitize_html(text: str) -> str:
    """Basic HTML sanitization to prevent injection in reports."""
    if not text:
        return ""
    
    # Replace & first to avoid double-encoding
    # Then replace other special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    
    return text


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension from filename."""
    return Path(filename).suffix.lower()


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in settings.ALLOWED_FILE_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
