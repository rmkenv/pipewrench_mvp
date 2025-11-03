"""
PipeWrench AI - Municipal DPW Knowledge Capture System
FastAPI application with integrated frontend UI
"""

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from anthropic import Anthropic, APIError
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import io
import re
from urllib.parse import urlparse
import requests
import logging
import json
from pathlib import Path
import time

# PDF extraction imports
try:
    import pypdf
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader as PyPDF2Reader
        PDF_EXTRACTION_AVAILABLE = True
    except ImportError:
        PDF_EXTRACTION_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PipeWrench AI", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
static_dir = Path("static")
templates_dir = Path("templates")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning("Static directory not found - static files will not be served")

if templates_dir.exists():
    templates = Jinja2Templates(directory="templates")
else:
    logger.warning("Templates directory not found - UI will use fallback HTML")
    templates = None

# ====
# URL WHITELIST CONFIGURATION
# ====

WHITELIST_URL = "https://raw.githubusercontent.com/rmkenv/pipewrench_mvp/main/custom_whitelist.json"
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

# Default embedded whitelist as fallback
EMBEDDED_WHITELIST = [
    {"url": "https://www.epa.gov", "description": "EPA Regulations"},
    {"url": "https://www.osha.gov", "description": "OSHA Standards"},
    {"url": "https://www.fhwa.dot.gov", "description": "FHWA Standards"},
    {"url": "https://www.awwa.org", "description": "Water Standards"},
    {"url": "https://www.apwa.net", "description": "APWA Resources"},
    {"url": "https://www.asce.org", "description": "ASCE Standards"},
]

whitelist_urls = []  # Will hold list of URL strings loaded from JSON

def fetch_whitelist():
    """Fetch whitelist from external URL or use embedded fallback"""
    global whitelist_urls
    try:
        logger.info(f"Fetching whitelist from {WHITELIST_URL} ...")
        response = requests.get(WHITELIST_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        whitelist_urls = [entry["url"] for entry in data if "url" in entry]
        logger.info(f"Loaded {len(whitelist_urls)} URLs from external whitelist")
    except Exception as e:
        logger.warning(f"Failed to fetch external whitelist: {e}")
        whitelist_urls = [entry["url"] for entry in EMBEDDED_WHITELIST]
        logger.info(f"Using embedded whitelist with {len(whitelist_urls)} URLs")

def get_whitelisted_domains():
    """Get set of whitelisted domains"""
    domains = set()
    for url in whitelist_urls:
        parsed = urlparse(url)
        if parsed.netloc:
            domains.add(parsed.netloc)
    return domains

def get_total_whitelisted_urls():
    """Get total count of whitelisted URLs"""
    return len(whitelist_urls)

def is_url_whitelisted(url: str) -> bool:
    """Check if a URL is whitelisted"""
    try:
        parsed = urlparse(url)
        for whitelisted_url in whitelist_urls:
            whitelisted_parsed = urlparse(whitelisted_url)
            if (parsed.netloc == whitelisted_parsed.netloc and 
                parsed.path.startswith(whitelisted_parsed.path)):
                return True
    except Exception:
        return False
    return False

# ====
# CONFIGURATION: ENVIRONMENT VARIABLES AND CLIENTS
# ====
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")

# Initialize Anthropic client globally
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Session configuration
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# ====
# CONFIGURATION: JOB ROLES
# ====
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

# ====
# CONFIGURATION: DEPARTMENTS
# ====
DEPARTMENT_PROMPTS = {
    "general_public_works": {
        "name": "General Public Works",
        "prompt": """You are a specialized AI assistant for Municipal Public Works departments. 
You help preserve institutional knowledge and provide accurate, cited information from approved sources."""
    },
    "water_sewer": {
        "name": "Water & Sewer",
        "prompt": """You are a specialized AI assistant for Water & Sewer departments. 
You provide expert guidance on water distribution, wastewater treatment, and utility infrastructure."""
    },
    "streets_highways": {
        "name": "Streets & Highways", 
        "prompt": """You are a specialized AI assistant for Streets & Highways departments.
You provide guidance on road maintenance, traffic management, and transportation infrastructure."""
    },
    "environmental": {
        "name": "Environmental Compliance",
        "prompt": """You are a specialized AI assistant for Environmental Compliance.
You help with EPA regulations, stormwater management, and environmental permitting."""
    },
    "safety": {
        "name": "Safety & Training",
        "prompt": """You are a specialized AI assistant for Safety & Training.
You provide guidance on OSHA compliance, workplace safety, and training programs."""
    },
    "administration": {
        "name": "Administration & Planning",
        "prompt": """You are a specialized AI assistant for DPW Administration & Planning.
You help with budgeting, project planning, and departmental management."""
    }
}

# ====
# HELPER FUNCTIONS
# ====
def get_role_list():
    """Return list of available roles"""
    return [{"id": role_id, "name": role_data["name"]} for role_id, role_data in JOB_ROLES.items()]

def get_role_context(role_id: str) -> str:
    """Get context for a specific role"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])["context"]

def get_department_prompt(department_id: str) -> str:
    """Get specialized prompt for department"""
    return DEPARTMENT_PROMPTS.get(department_id, DEPARTMENT_PROMPTS["general_public_works"]).get("prompt", "")

def get_all_departments():
    """Return list of all departments"""
    return [{"id": dept_id, "name": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

def get_department_list():
    """Get department list for API"""
    return [{"value": dept_id, "name": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

def get_all_roles():
    """Get all role keys"""
    return list(JOB_ROLES.keys())

def get_role_info(role_key: str):
    """Get role information"""
    role = JOB_ROLES.get(role_key)
    if role:
        return {
            "title": role["name"],
            "focus_areas": ["General DPW operations"]
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
    """Extract text from PDF content with multiple fallback methods"""
    if not PDF_EXTRACTION_AVAILABLE:
        logger.error("No PDF extraction library available. Install pypdf or PyPDF2.")
        return "[ERROR: PDF extraction library not installed. Install pypdf or PyPDF2.]"
    
    try:
        # Try pypdf first (recommended)
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                except Exception as page_error:
                    logger.warning(f"Error extracting page {page_num + 1}: {page_error}")
                    text += f"\n--- Page {page_num + 1} ---\n[Error extracting this page]\n"
            
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} characters from PDF using pypdf")
                return text
            else:
                return "[PDF appears to be empty or contains only images]"
        except (ImportError, AttributeError):
            # Fall back to PyPDF2
            from PyPDF2 import PdfReader as PyPDF2Reader
            pdf_reader = PyPDF2Reader(io.BytesIO(content))
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                except Exception as page_error:
                    logger.warning(f"Error extracting page {page_num + 1}: {page_error}")
                    text += f"\n--- Page {page_num + 1} ---\n[Error extracting this page]\n"
            
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} characters from PDF using PyPDF2")
                return text
            else:
                return "[PDF appears to be empty or contains only images]"
    
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}", exc_info=True)
        return f"[Error extracting PDF text: {str(e)}]"

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate LLM response using Anthropic with retry logic"""
    if not anthropic_client:
        return generate_mock_response(query, context, system_prompt, has_document)
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": f"User query: {query}\n\nDocument context: {context[:8000] if context else 'No document uploaded'}"
                    }
                ],
                timeout=60.0
            )

            if message.content and len(message.content) > 0:
                return message.content[0].text
            else:
                raise HTTPException(status_code=500, detail="Empty response from LLM")
        
        except APIError as e:
            logger.error(f"Anthropic API Error details: {type(e).__name__}: {str(e)}")
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise HTTPException(status_code=500, detail=f"Anthropic API Error after {max_retries} attempts: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating LLM response: {str(e)}")

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate mock response for testing"""
    return f"""[DEMO MODE - Anthropic API key not configured]

Your question: {query}

This is a demonstration response. To get real AI-powered answers:
1. Set the ANTHROPIC_API_KEY environment variable
2. Restart the application

The system is configured with {get_total_whitelisted_urls()} whitelisted sources and will only cite approved URLs when operational.

Document uploaded: {'Yes' if has_document else 'No'}
Document preview: {context[:200] if context else 'No document content'}...

Department context configured: Yes
PDF Extraction Available: {PDF_EXTRACTION_AVAILABLE}"""

def enforce_whitelist_on_text(text: str) -> str:
    """Enforce URL whitelist compliance on text."""
    if not text:
        return text
    
    bad_urls = []
    for url in set(URL_REGEX.findall(text)):
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
    """HTML sanitization to prevent XSS"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
            .replace("/", "&#x2F;"))

# ====
# SESSION MANAGEMENT
# ====
class SessionManager:
    """In-memory session manager with expiration"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = []
        for session_id, session_data in self.sessions.items():
            created_at = datetime.fromisoformat(session_data.get("created_at", now.isoformat()))
            if now - created_at > timedelta(hours=SESSION_EXPIRY_HOURS):
                expired.append(session_id)
        
        for session_id in expired:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session if it exists and is not expired"""
        self.cleanup_expired_sessions()
        return self.sessions.get(session_id)
    
    def create_session(self, session_id: str, data: Dict) -> None:
        """Create a new session"""
        self.sessions[session_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "documents": [],
            "questions": []
        }
        logger.info(f"Created session: {session_id}")
    
    def update_session(self, session_id: str, updates: Dict) -> None:
        """Update an existing session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
    
    def get_session_count(self) -> int:
        """Get count of active sessions"""
        self.cleanup_expired_sessions()
        return len(self.sessions)

session_manager = SessionManager()

# ====
# PYDANTIC MODELS
# ====
class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    role: Optional[str] = None
    department: Optional[str] = "general_public_works"

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    pages: int
    message: str
    is_asbuilt: bool = False

class SystemInfoResponse(BaseModel):
    total_whitelisted_urls: int
    whitelisted_domains: List[str]
    roles: List[str]
    departments: List[str]
    config: Dict

# ====
# FRONTEND ROUTES
# ====
@app.get("/", response_class=HTMLResponse)
async def root_redirect():
    """Redirect root to UI"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=/ui">
        <title>Redirecting...</title>
    </head>
    <body>
        <p>Redirecting to <a href="/ui">PipeWrench AI</a>...</p>
    </body>
    </html>
    """)

@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    """Serve the main UI"""
    if templates:
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            logger.error(f"Error serving UI template: {e}")
    
    # Fallback UI if template not found
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PipeWrench AI</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #1e40af; }
            .status { padding: 15px; background: #eff6ff; border-left: 4px solid #3b82f6; margin: 20px 0; }
            .error { background: #fee; border-left-color: #ef4444; }
            a { color: #3b82f6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 PipeWrench AI</h1>
            <p>Municipal DPW Knowledge Capture System</p>
            
            <div class="status error">
                <strong>⚠️ UI Template Not Found</strong>
                <p>The frontend template (templates/index.html) is missing.</p>
                <p>API endpoints are still available:</p>
                <ul>
                    <li><a href="/docs">API Documentation (Swagger UI)</a></li>
                    <li><a href="/redoc">API Documentation (ReDoc)</a></li>
                    <li><a href="/healthz">Health Check</a></li>
                    <li><a href="/api/system">System Information</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/healthz")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "anthropic_configured": anthropic_client is not None,
        "api_key_present": bool(ANTHROPIC_API_KEY),
        "pdf_extraction_available": PDF_EXTRACTION_AVAILABLE,
        "active_sessions": session_manager.get_session_count(),
        "whitelisted_urls": get_total_whitelisted_urls()
    }

# ====
# API ENDPOINTS
# ====
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
            if info:
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
            config={
                "version": "1.0.0",
                "anthropic_configured": anthropic_client is not None,
                "api_key_present": bool(ANTHROPIC_API_KEY),
                "pdf_extraction_available": PDF_EXTRACTION_AVAILABLE,
                "session_expiry_hours": SESSION_EXPIRY_HOURS,
                "active_sessions": session_manager.get_session_count()
            }
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")

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
    system_prompt = build_system_prompt(
        request.department or "general_public_works", 
        request.role
    )
    
    try:
        # Generate response
        response = generate_llm_response(
            request.query, 
            document_text, 
            system_prompt, 
            has_document
        )
        
        # Enforce whitelist compliance
        response = enforce_whitelist_on_text(response)
        
        # Update session with question
        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if session:
                if "questions" not in session:
                    session["questions"] = []
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
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}", exc_info=True)
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
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not PDF_EXTRACTION_AVAILABLE:
        raise HTTPException(
            status_code=500, 
            detail="PDF extraction not available. Install pypdf or PyPDF2."
        )
    
    # Validate session exists or create
    session = session_manager.get_session(session_id)
    if session is None:
        session_manager.create_session(session_id, {})
    
    try:
        # Process upload
        content = await file.read()
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
        
        # Extract text from PDF
        text = extract_text_from_pdf(content)
        
        # Estimate page count from content
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            page_count = len(pdf_reader.pages)
        except:
            try:
                from PyPDF2 import PdfReader as PyPDF2Reader
                pdf_reader = PyPDF2Reader(io.BytesIO(content))
                page_count = len(pdf_reader.pages)
            except:
                page_count = max(1, len(content) // 2500)
        
        # Update session
        session_manager.update_session(session_id, {
            "filename": file.filename,
            "text": text,
            "uploaded_at": datetime.now().isoformat(),
            "department": department,
            "role": role,
            "file_size": len(content),
            "page_count": page_count
        })
        
        logger.info(f"Successfully uploaded {file.filename} ({page_count} pages, {len(text)} chars extracted)")
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": "Document uploaded and processed successfully",
            "pages": page_count,
            "extracted_chars": len(text)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in API document upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report for a session."""
    logger.info(f"Generating report for session: {session_id}")
    
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    try:
        # Build HTML report
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
        <h1>🔧 PipeWrench AI - Knowledge Capture Report</h1>
        <p>Municipal DPW Knowledge Capture System</p>
        
        <h2>📄 Session Information</h2>
        <div class="document">
            <strong>Session ID:</strong> {sanitize_html(session_id)}<br>
            <strong>Created:</strong> {session.get('created_at', 'Unknown')}<br>
"""
        
        if session.get("filename"):
            html_report += f"""
            <strong>Document:</strong> {sanitize_html(session['filename'])}<br>
            <strong>Pages:</strong> {session.get('page_count', 'Unknown')}<br>
            <strong>Department:</strong> {sanitize_html(session.get('department', 'N/A'))}<br>
            <strong>Role:</strong> {sanitize_html(session.get('role', 'N/A'))}<br>
            <strong>Uploaded:</strong> {session.get('uploaded_at', 'Unknown')}<br>
"""
        
        html_report += """
        </div>
        
        <h2>💬 Questions & Answers</h2>
"""
        
        questions = session.get("questions", [])
        if not questions:
            html_report += "<p><em>No questions asked in this session.</em></p>"
        else:
            for i, qa in enumerate(questions, 1):
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
        
        html_report += f"""
        <div class="footer">
            <p><strong>PipeWrench AI</strong> - Municipal DPW Knowledge Capture System</p>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Total Questions: {len(questions)} | Session Duration: {SESSION_EXPIRY_HOURS} hours</p>
        </div>
    </div>
</body>
</html>
"""
        
        logger.info(f"Report generated successfully for session {session_id}")
        return HTMLResponse(content=html_report)
    
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report. Please try again."
        )

# ====
# UTILITY ENDPOINTS
# ====
@app.get("/api/sessions/cleanup")
async def cleanup_sessions():
    """Manually trigger session cleanup (admin endpoint)"""
    try:
        before_count = session_manager.get_session_count()
        session_manager.cleanup_expired_sessions()
        after_count = session_manager.get_session_count()
        
        return {
            "status": "success",
            "sessions_before": before_count,
            "sessions_after": after_count,
            "sessions_removed": before_count - after_count
        }
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup sessions")

@app.get("/api/whitelist")
async def get_whitelist_info():
    """Get whitelist information"""
    try:
        return {
            "total_urls": get_total_whitelisted_urls(),
            "domains": sorted(list(get_whitelisted_domains())),
            "urls": whitelist_urls[:50]  # Return first 50 URLs
        }
    except Exception as e:
        logger.error(f"Error getting whitelist info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve whitelist information")

@app.post("/api/whitelist/refresh")
async def refresh_whitelist():
    """Manually refresh whitelist from external source"""
    try:
        old_count = get_total_whitelisted_urls()
        fetch_whitelist()
        new_count = get_total_whitelisted_urls()
        
        return {
            "status": "success",
            "old_count": old_count,
            "new_count": new_count,
            "message": f"Whitelist refreshed. Now tracking {new_count} URLs."
        }
    except Exception as e:
        logger.error(f"Error refreshing whitelist: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh whitelist")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error", 
            "detail": "An unexpected error occurred. Please try again later.",
            "path": str(request.url)
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("=" * 70)
    logger.info("PipeWrench AI - Municipal DPW Knowledge Capture System")
    logger.info("=" * 70)
    
    # Check PDF extraction
    if not PDF_EXTRACTION_AVAILABLE:
        logger.warning("⚠️  PDF extraction library not available")
        logger.warning("⚠️  Install pypdf or PyPDF2: pip install pypdf")
    else:
        logger.info("✅ PDF extraction library available")
    
    # Fetch whitelist
    fetch_whitelist()
    logger.info(f"✅ Whitelisted URLs: {get_total_whitelisted_urls()}")
    logger.info(f"✅ Whitelisted Domains: {len(get_whitelisted_domains())}")
    
    # Configuration info
    logger.info(f"✅ Departments: {len(DEPARTMENT_PROMPTS)}")
    logger.info(f"✅ Job Roles: {len(JOB_ROLES)}")
    logger.info(f"✅ Session Expiry: {SESSION_EXPIRY_HOURS} hours")
    
    # Check Anthropic client
    if not anthropic_client:
        logger.warning("⚠️  ANTHROPIC_API_KEY not found in environment variables")
        logger.warning("⚠️  Application will run in DEMO MODE")
    else:
        logger.info("✅ Anthropic client initialized successfully")
        
        # Test the connection
        try:
            test_message = anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
                timeout=30.0
            )
            logger.info("✅ Anthropic API connection verified")
            logger.info(f"✅ Using model: claude-sonnet-4-5-20250929")
        except Exception as test_error:
            logger.error(f"⚠️  Anthropic API test failed: {test_error}")
            logger.warning("⚠️  Connection issues detected - will retry during actual use")
    
    logger.info("=" * 70)
    logger.info("🚀 Application startup complete")
    logger.info("=" * 70)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Application shutting down...")
    logger.info(f"Active sessions at shutdown: {session_manager.get_session_count()}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
