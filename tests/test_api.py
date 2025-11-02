"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import os

# Add api directory to path
api_path = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_path))

# Set test environment variables
os.environ["ANTHROPIC_API_KEY"] = "test-key-12345"

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestSessionEndpoints:
    """Tests for session management endpoints."""
    
    def test_create_session(self):
        """Test creating a new session."""
        response = client.post("/api/session/create")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0
    
    def test_get_session(self):
        """Test getting session data."""
        # Create session first
        create_response = client.post("/api/session/create")
        session_id = create_response.json()["session_id"]
        
        # Get session
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert "questions" in data
        assert "documents" in data
    
    def test_get_nonexistent_session(self):
        """Test getting a non-existent session."""
        response = client.get("/api/session/nonexistent-id")
        assert response.status_code == 404
    
    def test_get_session_status(self):
        """Test getting session status."""
        # Create session first
        create_response = client.post("/api/session/create")
        session_id = create_response.json()["session_id"]
        
        # Get status
        response = client.get(f"/api/session/{session_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["document_count"] == 0
        assert data["question_count"] == 0
    
    def test_delete_session(self):
        """Test deleting a session."""
        # Create session first
        create_response = client.post("/api/session/create")
        session_id = create_response.json()["session_id"]
        
        # Delete session
        response = client.delete(f"/api/session/{session_id}")
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f"/api/session/{session_id}")
        assert get_response.status_code == 404


class TestConfigEndpoints:
    """Tests for configuration endpoints."""
    
    def test_get_departments(self):
        """Test getting departments list."""
        response = client.get("/api/departments")
        assert response.status_code == 200
        data = response.json()
        assert "departments" in data
        assert len(data["departments"]) > 0
    
    def test_get_roles(self):
        """Test getting roles list."""
        response = client.get("/api/roles")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert len(data["roles"]) > 0
    
    def test_get_system_info(self):
        """Test getting system information."""
        response = client.get("/api/system")
        assert response.status_code == 200
        data = response.json()
        assert "total_whitelisted_urls" in data
        assert "whitelisted_domains" in data
        assert "roles" in data
        assert "departments" in data
        assert "config" in data
    
    def test_get_whitelist(self):
        """Test getting whitelist information."""
        response = client.get("/api/whitelist")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "domains" in data
        assert data["count"] > 0


class TestHomeEndpoint:
    """Tests for home endpoint."""
    
    def test_home_page(self):
        """Test home page loads."""
        response = client.get("/")
        assert response.status_code in [200, 503]  # 503 if HTML not loaded
        assert "text/html" in response.headers["content-type"]


class TestQueryEndpoint:
    """Tests for query endpoint."""
    
    def test_query_missing_question(self):
        """Test query with missing question."""
        response = client.post("/api/query", data={
            "question": "",
            "department": "general_public_works"
        })
        assert response.status_code == 400
    
    def test_query_too_long(self):
        """Test query with too long question."""
        long_question = "A" * 2001
        response = client.post("/api/query", data={
            "question": long_question,
            "department": "general_public_works"
        })
        assert response.status_code == 400


class TestDocumentUpload:
    """Tests for document upload endpoint."""
    
    def test_upload_without_session(self):
        """Test upload without valid session."""
        response = client.post(
            "/api/document/upload",
            data={"session_id": "nonexistent"},
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 404
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type."""
        # Create session first
        create_response = client.post("/api/session/create")
        session_id = create_response.json()["session_id"]
        
        # Try to upload invalid file
        response = client.post(
            "/api/document/upload",
            data={"session_id": session_id},
            files={"file": ("test.exe", b"test content", "application/octet-stream")}
        )
        assert response.status_code == 400


class TestReportGeneration:
    """Tests for report generation endpoint."""
    
    def test_generate_report_nonexistent_session(self):
        """Test generating report for non-existent session."""
        response = client.post(
            "/api/report/generate",
            data={"session_id": "nonexistent"}
        )
        assert response.status_code == 404
    
    def test_generate_report_empty_session(self):
        """Test generating report for empty session."""
        # Create session
        create_response = client.post("/api/session/create")
        session_id = create_response.json()["session_id"]
        
        # Generate report
        response = client.post(
            "/api/report/generate",
            data={"session_id": session_id}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
