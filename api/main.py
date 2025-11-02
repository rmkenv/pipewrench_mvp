"""
PipeWrench AI - Municipal DPW Knowledge Capture System
FastAPI application with improved error handling, logging, and production readiness.
"""
# Force redeploy timestamp: 2025-10-31 13:15:00 UTC - URL whitelist fix

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic, APIError
import os
from datetime import datetime
from typing import Optional, Dict, List
import io
import re
from urllib.parse import urlparse
import requests
import dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# URL WHITELIST CONFIGURATION - Import from actual config file
# ============================================================================

try:
    from url_whitelist_config import (
        WHITELISTED_URLS,
        get_whitelisted_domains,
        get_total_whitelisted_urls,
        is_url_whitelisted,
        URL_REGEX
    )
    logger.info("Successfully imported URL whitelist configuration")
except ImportError as e:
    logger.error(f"Failed to import url_whitelist_config: {e}")
    # Fallback to minimal whitelist to keep the app running
    WHITELISTED_URLS = [
        {"url": "https://www.epa.gov", "description": "EPA Regulations"},
        {"url": "https://www.osha.gov", "description": "OSHA Standards"},
        {"url": "https://www.fhwa.dot.gov", "description": "FHWA Standards"},
        {"url": "https://www.awwa.org", "description": "Water Standards"},
    ]
    
    URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    
    def get_whitelisted_domains():
        domains = set()
        for entry in WHITELISTED_URLS:
            parsed = urlparse(entry["url"])
            domains.add(parsed.netloc)
        return domains
    
    def get_total_whitelisted_urls():
        return len(WHITELISTED_URLS)
    
    def is_url_whitelisted(url: str) -> bool:
        try:
            parsed = urlparse(url)
            for whitelisted in WHITELISTED_URLS:
                whitelisted_parsed = urlparse(whitelisted["url"])
                if (parsed.netloc == whitelisted_parsed.netloc and 
                    parsed.path.startswith(whitelisted_parsed.path)):
                    return True
        except Exception:
            return False
        return False

# ============================================================================
# CONFIGURATION: ENVIRONMENT VARIABLES AND CLIENTS
# ============================================================================
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ============================================================================
# CONFIGURATION: JOB ROLES
# ============================================================================

JOB_ROLES = {
    "general": {
        "name": "General DPW Staff",
        "context": "You are assisting general Department of Public Works staff with municipal infrastructure questions."
    },
    "director": {
        "name": "DPW Director",
        "context": "You are assisting a DPW Director with strategic planning, policy decisions, and departmental oversight."
    },
    "engineer": {
        "name": "Civil Engineer",
        "context": "You are assisting a licensed civil engineer with technical engineering standards, design specifications, and compliance requirements."
    },
    "project_manager": {
        "name": "Project Manager",
        "context": "You are assisting a project manager with construction management, scheduling, budgeting, and contractor coordination."
    },
    "inspector": {
        "name": "Construction Inspector",
        "context": "You are assisting a construction inspector with field inspection procedures, quality control, and compliance verification."
    },
    "maintenance": {
        "name": "Maintenance Supervisor",
        "context": "You are assisting a maintenance supervisor with asset management, preventive maintenance, and repair operations."
    },
    "environmental": {
        "name": "Environmental Compliance Officer",
        "context": "You are assisting an environmental compliance officer with EPA regulations, stormwater management, and environmental permits."
    },
    "safety": {
        "name": "Safety Officer",
        "context": "You are assisting a safety officer with OSHA compliance, workplace safety, and accident prevention."
    }
}

# ============================================================================
# CONFIGURATION: DEPARTMENTS
# ============================================================================

DEPARTMENT_PROMPTS = {
    "general_public_works": {
        "name": "General Public Works",
        "prompt": """You are a specialized AI assistant for Municipal Public Works departments."""
    },
    "water_sewer": {
        "name": "Water & Sewer",
        "prompt": """You are a specialized AI assistant for Water & Sewer departments."""
    },
    "streets_highways": {
        "name": "Streets & Highways", 
        "prompt": """You are a specialized AI assistant for Streets & Highways departments."""
    },
    "environmental": {
        "name": "Environmental Compliance",
        "prompt": """You are a specialized AI assistant for Environmental Compliance."""
    },
    "safety": {
        "name": "Safety & Training",
        "prompt": """You are a specialized AI assistant for Safety & Training."""
    },
    "administration": {
        "name": "Administration & Planning",
        "prompt": """You are a specialized AI assistant for DPW Administration & Planning."""
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_role_list():
    """Return list of available roles"""
    return [{"id": role_id, "name": role_data["name"]} for role_id, role_data in JOB_ROLES.items()]

def get_role_context(role_id: str) -> str:
    """Get context for a specific role"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])["context"]

def get_department_prompt(department_id: str) -> str:
    """Get specialized prompt for department"""
    return DEPARTMENT_PROMPTS.get(department_id, {}).get("prompt", "")

def get_all_departments():
    """Return list of all departments"""
    return [{"id": dept_id, "name": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

def get_department_list():
    """Get department list for API"""
    return [{"value": dept_id, "title": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

def get_all_roles():
    """Get all role keys"""
    return list(JOB_ROLES.keys())

def get_role_info(role_key: str):
    """Get role information"""
    role = JOB_ROLES.get(role_key)
    if role:
        return {
            "title": role["name"],
            "focus_areas": ["General DPW operations"]  # Default focus areas
        }
    return None

def build_system_prompt(department_key: str, role_key: Optional[str]) -> str:
    """Build system prompt with department and role context."""
    base = get_department_prompt(department_key)
    role_txt = ""
    if role_key:
        role = get_role_info(role_key)
        if role:
            areas = role.get("focus_areas", [])
            role_txt = f"\n\nROLE CONTEXT:\n- Title: {role.get('title', role_key)}\n- Focus Areas:\n" + \
                      "\n".join(f"  - {a}" for a in areas)
    
    whitelist_notice = f"\n\nURL RESTRICTIONS:\n" \
                      f"- Only cite and reference sources from approved whitelist\n" \
                      f"- Include the specific URL for each citation\n" \
                      f"- If info is not in whitelist, clearly state that it cannot be verified from approved sources\n" \
                      f"- All child pages of whitelisted URLs are permitted\n" \
                      f"- Total Whitelisted URLs: {get_total_whitelisted_urls()}\n" \
                      f"- Approved Domains: {', '.join(sorted(list(get_whitelisted_domains()))[:25])}" + \
                      ("..." if len(get_whitelisted_domains()) > 25 else "")
    
    return base + role_txt + whitelist_notice

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content - basic implementation"""
    # This is a simplified implementation
    # In production, you'd use PyPDF2, pdfplumber, or similar
    return "Sample extracted text from PDF"

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate LLM response using Anthropic"""
    if not anthropic_client:
        raise HTTPException(status_code=500, detail="Anthropic client not configured")
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",  # Using a valid model name
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user", 
                    "content": f"User query: {query}\nDocument context: {context}"
                }
            ]
        )

        if message.content and len(message.content) > 0:
            # Get the first text block
            return message.content[0].text
        else:
            raise HTTPException(status_code=500, detail="Empty response from LLM")
            
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM response: {str(e)}")

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate mock response for testing"""
    return f"Mock response for: {query}\n\nContext: {context[:100]}...\nSystem prompt: {system_prompt[:50]}..."

def enforce_whitelist_on_text(text: str) -> str:
    """Enforce URL whitelist compliance on text."""
    bad_urls = []
    for url in set(URL_REGEX.findall(text or "")):
        url_clean = url.rstrip('.,);]')
        if not is_url_whitelisted(url_clean):
            bad_urls.append(url_clean)
    
    if not bad_urls:
        return text
    
    note = "\n\n[COMPLIANCE NOTICE]\n" \
           "The following URLs are not in the approved whitelist and must not be cited:\n" + \
           "\n".join(f"- {u}" for u in sorted(bad_urls)) + \
           "\n\nPlease revise citations to use only approved sources."
    
    return text + note

def sanitize_html(text: str) -> str:
    """Basic HTML sanitization"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

class SessionManager:
    """Simple session manager"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)
    
    def create_session(self, session_id: str, data: Dict) -> None:
        self.sessions[session_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "documents": [],
            "questions": []
        }
    
    def update_session(self, session_id: str, updates: Dict) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)

session_manager = SessionManager()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    role: Optional[str] = "general"
    department: Optional[str] = None

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    pages: int
    message: str
    is_asbuilt: bool = False

class CustomURLRequest(BaseModel):
    session_id: str
    url: str

class ErrorResponse(BaseModel):
    error: str
    detail: str

class SystemInfoResponse(BaseModel):
    total_whitelisted_urls: int
    whitelisted_domains: List[str]
    roles: List[str]
    departments: List[str]
    config: Dict

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {"message": "PipeWrench AI API", "status": "running"}

@app.get("/api/departments")
async def get_departments():
    """Get list of all available departments."""
    try:
        return {"departments": get_department_list()}
    except Exception as e:
        logger.error(f"Failed to get departments: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve departments")

@app.get("/api/roles")
async def list_roles():
    """Get list of all available job roles."""
    try:
        roles = []
        for key in get_all_roles():
            info = get_role_info(key)
            roles.append({"value": key, "title": info["title"]})
        return {"roles": roles}
    except Exception as e:
        logger.error(f"Failed to get roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve roles")

@app.get("/api/system")
async def system_info():
    """Get system configuration information."""
    try:
        return SystemInfoResponse(
            total_whitelisted_urls=get_total_whitelisted_urls(),
            whitelisted_domains=sorted(list(get_whitelisted_domains())),
            roles=get_all_roles(),
            departments=[d["value"] for d in get_department_list()],
            config={"version": "1.0"}
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")

@app.get("/api/whitelist")
async def whitelist_overview():
    """Get overview of whitelisted URLs."""
    try:
        all_urls = WHITELISTED_URLS
        sample_urls = [entry["url"] for entry in all_urls[:50]]
        
        return {
            "count": get_total_whitelisted_urls(),
            "domains": sorted(list(get_whitelisted_domains())),
            "sample": sample_urls,
        }
    except Exception as e:
        logger.error(f"Failed to get whitelist: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve whitelist")

def extract_text_from_asbuilt_pdf(file: UploadFile) -> str:
    """Extract text from as-built drawing PDF (specialized processing)"""
    try:
        file.file.seek(0)
        response = requests.post(
            DRAWING_PROCESSING_API_URL,
            files={"file": (file.filename, file.file, file.content_type)},
            data={"ocr_method": "textract"},
            timeout=30
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error processing as-built PDF")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error calling drawing processing API: {e}")
        raise HTTPException(status_code=500, detail="Drawing processing service unavailable")

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    is_asbuilt: bool = False,
    session_id: Optional[str] = None,
    department: str = "general_public_works",
    role: Optional[str] = None
):
    """Upload and process PDF document"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate session ID if not provided
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Extract text
    try:
        if is_asbuilt:
            text = extract_text_from_asbuilt_pdf(file)
        else:
            content = await file.read()
            text = extract_text_from_pdf(content)
        
        # Estimate page count (simplified)
        page_count = max(1, len(text) // 2500)  # Rough estimate
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    # Store in session
    session_data = {
        "filename": file.filename,
        "text": text,
        "uploaded_at": datetime.now().isoformat(),
        "is_asbuilt": is_asbuilt,
        "department": department,
        "role": role
    }
    
    if session_manager.get_session(session_id):
        session_manager.update_session(session_id, session_data)
    else:
        session_manager.create_session(session_id, session_data)
    
    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        pages=page_count,
        message=f"Successfully uploaded {file.filename} ({page_count} pages)",
        is_asbuilt=is_asbuilt
    )

@app.post("/query")
async def query_documents(request: QueryRequest):
    """Query with or without uploaded documents"""
    
    # Get document context if session exists
    document_text = ""
    has_document = False
    
    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session:
            document_text = session.get("text", "")
            has_document = bool(document_text)
    
    # Build system prompt
    system_prompt = build_system_prompt(request.department or "general_public_works", request.role)
    
    try:
        # Generate response
        if has_document:
            response = generate_llm_response(request.query, document_text, system_prompt, has_document)
        else:
            response = generate_mock_response(request.query, document_text, system_prompt, has_document)
        
        # Enforce whitelist compliance
        response = enforce_whitelist_on_text(response)
        
        # Update session with question
        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if session:
                session["questions"].append({
                    "question": request.query,
                    "answer": response,
                    "timestamp": datetime.now().isoformat(),
                    "role": request.role,
                    "department": request.department
                })
        
        return {
            "answer": response,
            "sources": ["whitelisted_urls"] + (["uploaded_document"] if has_document else [])
        }
        
    except HTTPException:
        raise
    except APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(
            status_code=502,
            detail="AI service error. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )

@app.post("/api/document/upload")
async def api_upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """API endpoint for document upload"""
    logger.info(f"Document upload - File: {file.filename}, Session: {session_id}")
    
    # Validate session exists or create
    session = session_manager.get_session(session_id)
    if session is None:
        session_manager.create_session(session_id, {})
    
    try:
        # Process upload (simplified - using regular upload logic)
        content = await file.read()
        text = extract_text_from_pdf(content)
        
        # Update session
        session_manager.update_session(session_id, {
            "filename": file.filename,
            "text": text,
            "uploaded_at": datetime.now().isoformat(),
            "department": department,
            "role": role
        })
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": "Document uploaded successfully",
            "pages": max(1, len(text) // 2500)
        }
        
    except Exception as e:
        logger.error(f"Error in API document upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report for a session."""
    logger.info(f"Generating report for session: {session_id}")
    
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    try:
        # Build simplified HTML report
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PipeWrench AI - Knowledge Capture Report</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            line-height: 1.6; 
            background: #f5f5f5;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #1e40af; 
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 10px;
        }}
        h2 {{ 
            color: #3b82f6; 
            margin-top: 30px; 
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 5px;
        }}
        .question {{ 
            background: #eff6ff; 
            padding: 15px; 
            margin: 20px 0; 
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
        }}
        .answer {{ 
            margin: 10px 0; 
            white-space: pre-wrap;
            padding: 10px;
            background: white;
        }}
        .document {{ 
            background: #fef3c7; 
            padding: 15px; 
            margin: 20px 0; 
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
        }}
        .metadata {{ 
            color: #6b7280; 
            font-size: 0.9em;
            font-style: italic;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Municipal DPW Knowledge Capture System</h1>
        <p>AI-Powered Infrastructure Knowledge Base with Source Verification</p>
        
        <h2>📄 Uploaded Document</h2>
"""
        
        if session.get("filename"):
            html_report += f"""
        <div class="document">
            <strong>Filename:</strong> {sanitize_html(session['filename'])}<br>
            <strong>Department:</strong> {sanitize_html(session.get('department', 'N/A'))}<br>
            <strong>Role:</strong> {sanitize_html(session.get('role', 'N/A'))}<br>
            <div class="metadata">Uploaded: {session.get('uploaded_at', 'Unknown')}</div>
        </div>
"""
        
        html_report += f"""
        <h2>💬 Questions & Answers</h2>
"""
        
        for i, qa in enumerate(session.get("questions", []), 1):
            role_display = f" • {sanitize_html(qa.get('role', ''))}" if qa.get('role') else ""
            html_report += f"""
        <div class="question">
            <strong>Q{i} ({sanitize_html(qa.get('department', 'General'))}{role_display}):</strong> {sanitize_html(qa.get('question', ''))}
            <div class="answer">
                <strong>Answer:</strong><br>
                {sanitize_html(qa.get('answer', ''))}
            </div>
            <p class="metadata">Asked: {qa.get('timestamp', 'Unknown')}</p>
        </div>
"""
        
        html_report += """
        <div class="footer">
            <p><strong>PipeWrench AI</strong> - Municipal DPW Knowledge Capture System</p>
            <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </div>
</body>
</html>
"""
        
        logger.info(f"Report generated successfully for session {session_id}")
        return HTMLResponse(content=html_report)
    
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again."
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later."}
    )

# For Vercel
handler = app
