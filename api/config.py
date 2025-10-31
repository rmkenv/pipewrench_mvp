"""
Configuration module for PipeWrench AI application.
Centralizes all configuration values and environment variable management.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Configuration
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    
    # File Upload Limits
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    MAX_TEXT_CHARS: int = int(os.getenv("MAX_TEXT_CHARS", "100000"))
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SESSION_CLEANUP_INTERVAL_SECONDS: int = 3600  # Clean up every hour
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    
    # Allowed File Extensions
    ALLOWED_FILE_EXTENSIONS: set = {".txt", ".pdf", ".docx"}
    
    # Request Size Limits
    MAX_REQUEST_SIZE_MB: int = 50
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Get your API key from https://console.anthropic.com/"
            )
    
    @classmethod
    def get_info(cls) -> dict:
        """Get sanitized configuration info for health checks."""
        return {
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            "claude_model": cls.CLAUDE_MODEL,
            "max_file_size_mb": cls.MAX_FILE_SIZE_MB,
            "max_text_chars": cls.MAX_TEXT_CHARS,
            "session_timeout_hours": cls.SESSION_TIMEOUT_HOURS,
            "api_key_configured": bool(cls.ANTHROPIC_API_KEY),
        }


# Create singleton settings instance
settings = Settings()
