"""
PipeWrench AI - Municipal DPW Knowledge Capture System
FastAPI application with integrated frontend UI
Optimized for Render.com deployment with SSL/connection diagnostics
Updated to use **Gemini API (Google GenAI SDK)**
"""

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
# New Gemini Imports
from google import genai
from google.genai.errors import APIError, ResourceExhaustedError, InternalServerError
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
from contextlib import asynccontextmanager
import random
import time
import httpx
import certifi
import ssl
import socket

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ====
# URL WHITELIST CONFIGURATION (Unchanged)
# ====

WHITELIST_URL = "https://raw.githubusercontent.com/rmkenv/pipewrench_mvp/main/custom_whitelist.json"
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

EMBEDDED_WHITELIST = [
    {"url": "https://www.epa.gov", "description": "EPA Regulations"},
    {"url": "https://www.osha.gov", "description": "OSHA Standards"},
    {"url": "https://www.fhwa.dot.gov", "description": "FHWA Standards"},
    {"url": "https://www.awwa.org", "description": "Water Standards"},
    {"url": "https://www.apwa.net", "description": "APWA Resources"},
    {"url": "https://www.asce.org", "description": "ASCE Standards"},
]

whitelist_urls = []

def fetch_whitelist():
    """Fetch whitelist from external URL or use embedded fallback"""
    global whitelist_urls
    try:
        logger.info(f"Fetching whitelist from {WHITELIST_URL}...")
        response = requests.get(WHITELIST_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        whitelist_urls = [entry["url"] for entry in data if "url" in entry]
        logger.info(f"✅ Loaded {len(whitelist_urls)} URLs from external whitelist")
    except Exception as e:
        logger.warning(f"⚠️  Failed to fetch external whitelist: {e}")
        whitelist_urls = [entry["url"] for entry in EMBEDDED_WHITELIST]
        logger.info(f"✅ Using embedded whitelist with {len(whitelist_urls)} URLs")

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
# CONFIGURATION: ENVIRONMENT VARIABLES
# ====
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Render-specific configuration
IS_RENDER = bool(os.getenv("RENDER"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "production" if IS_RENDER else "development")

# Gemini model configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ====
# APPLICATION STATE CLASS
# ====
class AppState:
    """Application state container"""
    def __init__(self):
        self.gemini_client: Optional[genai.Client] = None 
        self.session_manager: Optional['SessionManager'] = None
        self.http_client: Optional[httpx.Client] = None
        
app_state = AppState()

# ====
# LIFESPAN CONTEXT MANAGER (Render-Optimized)
# ====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager - Render.com optimized with SSL diagnostics"""
    # STARTUP
    logger.info("=" * 70)
    logger.info("PipeWrench AI - Municipal DPW Knowledge Capture System")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Running on Render: {IS_RENDER}")
    logger.info(f"Debug Mode: {DEBUG_MODE}")
    logger.info("=" * 70)
    
    # Initialize session manager
    app_state.session_manager = SessionManager()
    logger.info("✅ Session manager initialized")
    
    # Check PDF extraction
    if not PDF_EXTRACTION_AVAILABLE:
        logger.warning("⚠️  PDF extraction library not available")
    else:
        logger.info("✅ PDF extraction library available")
    
    # Fetch whitelist
    fetch_whitelist()
    logger.info(f"✅ Whitelisted URLs: {get_total_whitelisted_urls()}")
    
    # Configuration info
    logger.info(f"✅ Departments: {len(DEPARTMENT_PROMPTS)}")
    logger.info(f"✅ Job Roles: {len(JOB_ROLES)}")
    logger.info(f"✅ Session Expiry: {SESSION_EXPIRY_HOURS} hours")
    
    # Test DNS resolution (Gemini)
    try:
        ip = socket.gethostbyname("api.gemini.google.com") 
        logger.info(f"✅ DNS Resolution: api.gemini.google.com -> {ip}")
    except Exception as e:
        logger.error(f"❌ DNS Resolution failed: {e}")
    
    # Initialize HTTP client and Gemini client
    if GEMINI_API_KEY:
        try:
            timeout_config = httpx.Timeout(
                connect=90.0, read=240.0, write=90.0, pool=60.0
            )
            limits_config = httpx.Limits(
                max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0
            )
            
            # Initialize httpx client (used for explicit network checks and could be passed)
            try:
                app_state.http_client = httpx.Client(
                    timeout=timeout_config, limits=limits_config, verify=certifi.where(), 
                    http2=False, follow_redirects=True,
                    transport=httpx.HTTPTransport(retries=5, verify=certifi.where())
                )
            except Exception as ssl_error:
                logger.warning(f"⚠️  SSL verification failed for httpx: {ssl_error}")
                app_state.http_client = httpx.Client(
                    timeout=timeout_config, limits=limits_config, verify=False, 
                    http2=False, follow_redirects=True
                )
                logger.warning("⚠️  HTTP client (httpx) running WITHOUT SSL verification")
            
            # Initialize Gemini client
            app_state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            
            logger.info("✅ Gemini client initialized")
            logger.info(f"    Model: {GEMINI_MODEL}")
            
            if not IS_RENDER or DEBUG_MODE:
                try:
                    logger.info("Testing Gemini API connection...")
                    test_response = app_state.gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[{"role": "user", "parts": [{"text": "test"}]}],
                        config={"max_output_tokens": 5, "timeout": 30.0}
                    )
                    if test_response.candidates:
                         logger.info("✅ Gemini API connection verified!")
                    else:
                         raise Exception("Empty response from Gemini API test")
                except Exception as test_error:
                    logger.warning(f"⚠️  Startup API test failed: {type(test_error).__name__}")
                
        except Exception as e:
            logger.error(f"❌ Gemini client initialization failed: {e}", exc_info=True)
            app_state.gemini_client = None
    else:
        logger.warning("⚠️  GEMINI_API_KEY not found - running in DEMO MODE")
        app_state.gemini_client = None
    
    logger.info("=" * 70)
    logger.info("🚀 Application startup complete")
    logger.info("=" * 70)
    
    yield  # Application runs here
    
    # SHUTDOWN
    logger.info("Application shutting down...")
    if app_state.http_client:
        app_state.http_client.close()
        logger.info("✅ HTTP client closed")

# ====
# CREATE FASTAPI APP WITH LIFESPAN
# ====
app = FastAPI(
    title="PipeWrench AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG_MODE else None,
    redoc_url="/redoc" if DEBUG_MODE else None
)

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

if templates_dir.exists():
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

# ====
# CONFIGURATION: JOB ROLES (Unchanged)
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
# CONFIGURATION: DEPARTMENTS (Unchanged)
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
# DEPENDENCY: GET CLIENTS (Updated for Gemini)
# ====
def get_gemini_client() -> Optional[genai.Client]:
    """Dependency to get Gemini client"""
    return app_state.gemini_client

def get_session_manager() -> 'SessionManager':
    """Dependency to get session manager"""
    if app_state.session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    return app_state.session_manager

# ====
# HELPER FUNCTIONS
# ====
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
    base = DEPARTMENT_PROMPTS.get(department_key, DEPARTMENT_PROMPTS["general_public_works"]).get("prompt", "")
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
        return "[ERROR: PDF extraction library not installed. Install pypdf or PyPDF2.]"
    
    try:
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from PDF using pypdf")
                return text
            else:
                return "[PDF appears to be empty or contains only images]"
        except (ImportError, AttributeError, Exception):
            from PyPDF2 import PdfReader as PyPDF2Reader
            pdf_reader = PyPDF2Reader(io.BytesIO(content))
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            if text.strip():
                logger.info(f"Extracted {len(text)} characters from PDF using PyPDF2")
                return text
            else:
                return "[PDF appears to be empty or contains only images]"
    
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}", exc_info=True)
        return f"[Error extracting PDF text: {str(e)}]"

# UPDATED: generate_llm_response to use Gemini API
def generate_llm_response(
    query: str, 
    context: str, 
    system_prompt: str, 
    has_document: bool,
    gemini_client: Optional[genai.Client]
) -> str:
    """
    Generate LLM response using Gemini - Render.com optimized with enhanced error handling
    """
    if not gemini_client:
        return generate_mock_response(query, context, system_prompt, has_document)
    
    max_retries = 5
    base_delay = 5  
    
    # Construct contents for the Gemini API
    user_message_parts = [
        {"text": f"User query: {query}"}
    ]
    if context:
        user_message_parts.append({"text": f"\n\nDOCUMENT CONTEXT (for RAG/citation only): {context[:8000]}"})
    else:
        user_message_parts.append({"text": "\n\nNo document uploaded"})

    
    contents = [
        # System instruction and a model response to set the tone/persona
        {"role": "user", "parts": [{"text": system_prompt}]},
        {"role": "model", "parts": [{"text": "Understood. I will follow the instructions and use the whitelisted sources for citation. I am ready for your query."}]},
        # The actual user query + RAG context
        {"role": "user", "parts": user_message_parts}
    ]

    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Gemini API call attempt {attempt + 1}/{max_retries}")
            
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config={
                    "max_output_tokens": 8192, 
                    "temperature": 0.7,
                    "timeout": 240.0, # 4 minutes for Render
                }
            )
            
            if response.candidates and response.candidates[0].content.parts:
                logger.info(f"✅ Gemini API call successful on attempt {attempt + 1}")
                return response.text
            elif response.candidates and response.candidates[0].finish_reason.name != "STOP":
                 return f"[LLM Response Blocked] The model finished generation with reason: {response.candidates[0].finish_reason.name}. This may be due to safety settings or content policy."
            else:
                raise HTTPException(status_code=500, detail="Empty response from LLM or failed to generate content.")
        
        except APIError as e:
            error_str = str(e).lower()
            error_type = type(e).__name__
            logger.error(f"❌ Gemini API Error on attempt {attempt + 1}/{max_retries}: {error_type}")
            
            is_timeout = "timeout" in error_str
            is_connection = is_timeout or "connection" in error_str or "network" in error_str
            is_rate_limit = isinstance(e, ResourceExhaustedError) or "rate" in error_str or "429" in error_str
            is_server_error = isinstance(e, InternalServerError) or any(code in error_str for code in ["500", "502", "503", "504"])
            
            should_retry = (is_timeout or is_connection or is_rate_limit or is_server_error)
            
            if not should_retry or attempt >= max_retries - 1:
                detail = "API error. Check connection or rate limits."
                if is_connection: detail = "Cannot connect to Gemini API. Check network/SSL."
                elif is_timeout: detail = "API request timed out (Render issue)."
                elif is_rate_limit: detail = "Rate limit exceeded."
                raise HTTPException(status_code=503, detail=detail)
            
            delay = base_delay * (2 ** attempt)
            if is_rate_limit: delay *= 3
            elif is_timeout or is_connection: delay *= 2
            
            total_delay = delay + random.uniform(delay * 0.1, delay * 0.3)
            logger.info(f"    ⏳ Retrying in {total_delay:.1f} seconds... (Reason: {error_type})")
            time.sleep(total_delay)
            continue
        
        except Exception as e:
            logger.error(f"❌ Unexpected error on attempt {attempt + 1}/{max_retries}: {e}", exc_info=True)
            if attempt == 0:
                logger.info("    🔄 Retrying once for unexpected error...")
                time.sleep(5)
                continue
            raise HTTPException(status_code=500, detail=f"Unexpected error: {type(e).__name__}.")
    
    logger.error(f"❌ Max retries ({max_retries}) exhausted")
    raise HTTPException(
        status_code=503,
        detail="Service temporarily unavailable after multiple attempts."
    )

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate mock response for testing"""
    return f"""[DEMO MODE - Gemini API key not configured]

Your question: {query}

This is a demonstration response. To get real AI-powered answers:
1. Set the GEMINI_API_KEY environment variable.
2. Redeploy the application

Configuration:
- Department: {re.search(r'You are a specialized AI assistant for (\w+)', system_prompt).group(1) if re.search(r'You are a specialized AI assistant for (\w+)', system_prompt) else 'N/A'}
- Document uploaded: {'Yes' if has_document else 'No'} (Preview: {context[:50]}...)

*All functionality is ready; needs API key.*"""

def enforce_whitelist_on_text(text: str) -> str:
    """Enforce URL whitelist compliance on text."""
    if not text: return text
    
    bad_urls = []
    for url in set(URL_REGEX.findall(text)):
        url_clean = url.rstrip('.,);]')
        if not is_url_whitelisted(url_clean):
            bad_urls.append(url_clean)
    
    if not bad_urls: return text
    
    note = "\n\n[COMPLIANCE NOTICE]\n" \
           "The following URLs are not in the approved whitelist and must not be cited:\n" + \
           "\n".join(f"- {u}" for u in sorted(bad_urls)) + \
           "\n\nPlease revise citations to use only approved sources."
    
    return text + note

def sanitize_html(text: str) -> str:
    """HTML sanitization to prevent XSS"""
    if not text: return ""
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
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session if it exists and is not expired"""
        self.cleanup_expired_sessions()
        return self.sessions.get(session_id)
    
    def create_session(self, session_id: str, data: Dict) -> None:
        """Create a new session"""
        self.sessions[session_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "document_context": "", # Stores the text from the uploaded document
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
# DIAGNOSTIC ENDPOINT (Unchanged from previous update)
# ====
@app.get("/api/test-connection")
async def test_connection():
    """Diagnostic endpoint to test various connections"""
    # ... (Implementation is as in the previous output) ...
    results = {}
    
    # Test 1: Basic DNS resolution (Updated for Gemini)
    try:
        ip = socket.gethostbyname("api.gemini.google.com")
        results["dns_resolution"] = f"✅ Success: {ip}"
    except Exception as e:
        results["dns_resolution"] = f"❌ Failed: {str(e)}"
    
    # Test 2: Basic HTTP connection with requests (Updated for Gemini)
    try:
        resp = requests.get("https://api.gemini.google.com", timeout=10)
        results["http_connection_requests"] = f"✅ Status: {resp.status_code}"
    except Exception as e:
        results["http_connection_requests"] = f"❌ Failed: {str(e)}"
    
    # Test 3: HTTPX with SSL verification (Updated for Gemini URL)
    try:
        with httpx.Client(timeout=10.0, verify=True) as client:
            resp = client.get("https://api.gemini.google.com")
            results["httpx_verified"] = f"✅ Status: {resp.status_code}"
    except Exception as e:
        results["httpx_verified"] = f"❌ Failed: {str(e)[:200]}"
    
    # Test 6: Gemini client initialization (Updated)
    try:
        if GEMINI_API_KEY:
            test_client = genai.Client(api_key=GEMINI_API_KEY)
            results["gemini_init"] = "✅ Client created"
            
            # Try a simple API call (Updated for Gemini)
            try:
                response = test_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[{"role": "user", "parts": [{"text": "hi"}]}],
                    config={"max_output_tokens": 5, "timeout": 30.0}
                )
                if response.candidates:
                    results["gemini_api_call"] = "✅ API call successful"
                else:
                    results["gemini_api_call"] = "❌ API call failed: Empty response"

            except Exception as api_e:
                results["gemini_api_call"] = f"❌ API call failed: {str(api_e)[:200]}"
        else:
            results["gemini_init"] = "❌ No API key"
    except Exception as e:
        results["gemini_init"] = f"❌ Failed: {str(e)[:200]}"
    
    # Test 8: Check current Gemini client (Updated)
    if app_state.gemini_client:
        results["app_gemini_client"] = "✅ Initialized"
    else:
        results["app_gemini_client"] = "❌ Not initialized"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "environment": ENVIRONMENT,
        "is_render": IS_RENDER,
        "debug_mode": DEBUG_MODE,
        "diagnostics": results
    }

# ====
# CORE API ENDPOINT: Query (Implemented and uses Gemini)
# ====
@app.post("/api/query", response_model=Dict)
async def query_endpoint(
    request_data: QueryRequest,
    session_manager: 'SessionManager' = Depends(get_session_manager),
    gemini_client: Optional[genai.Client] = Depends(get_gemini_client)
):
    """Handles user queries, retrieving context from the session and generating a Gemini response."""
    session_id = request_data.session_id
    query = request_data.query
    role = request_data.role or "general"
    department = request_data.department or "general_public_works"

    if not session_id:
        # Create a temporary session if none is provided
        session_id = f"temp-{random.randint(1000, 9999)}"
        session_manager.create_session(session_id, {"role": role, "department": department})
        logger.info(f"No session ID provided, created temporary session: {session_id}")

    session = session_manager.get_session(session_id)
    if not session:
        # Recreate session if expired/not found (but we keep the ID for the frontend)
        session_manager.create_session(session_id, {"role": role, "department": department})
        session = session_manager.get_session(session_id)

    # Use department and role from the request for prompt generation
    document_context = session.get("document_context", "") 
    has_document = bool(document_context)

    system_prompt = build_system_prompt(department, role)
    
    try:
        llm_response = generate_llm_response(
            query=query,
            context=document_context,
            system_prompt=system_prompt,
            has_document=has_document,
            gemini_client=gemini_client
        )
    except HTTPException as e:
        logger.error(f"Error during LLM generation: {e.detail}")
        raise e # Re-raise HTTPExceptions (timeouts, rate limits)

    # Enforce compliance on the raw LLM output
    final_response = enforce_whitelist_on_text(llm_response)

    # Update session history
    session.get("questions", []).append(query)
    session_manager.update_session(session_id, {"questions": session.get("questions")})
    
    return {"response": final_response, "session_id": session_id, "model_used": GEMINI_MODEL}

# ====
# CORE API ENDPOINT: File Upload (Implemented and uses Gemini RAG pattern)
# ====
@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    session_id: str = Form(...),
    department: str = Form(...),
    role: str = Form(...),
    file: UploadFile = File(...),
    session_manager: 'SessionManager' = Depends(get_session_manager)
):
    """
    Handles PDF file upload, extracts text, and stores it as RAG context in the session.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Only PDF files are supported for document-based RAG."
        )

    # Check session
    session = session_manager.get_session(session_id)
    if not session:
        # Create new session if ID is new or expired
        session_manager.create_session(session_id, {"role": role, "department": department})
        session = session_manager.get_session(session_id)

    # Read file content
    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file.")
    
    # Extract text from PDF
    extracted_text = extract_text_from_pdf(contents)
    
    if "[Error" in extracted_text or "[ERROR" in extracted_text:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {extracted_text}")

    page_count = 0
    if extracted_text.startswith("--- Page 1 ---"):
        page_count = extracted_text.count("--- Page")

    # Store extracted text in session (used as RAG context in query_endpoint)
    session_manager.update_session(
        session_id, 
        {
            "document_context": extracted_text,
            "documents": [file.filename] # Update document history
        }
    )
    
    logger.info(f"Stored {len(extracted_text)} chars of text from '{file.filename}' in session {session_id}")
    
    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        pages=page_count,
        message=f"Successfully extracted {page_count} pages and stored context for RAG.",
        is_asbuilt=False # Placeholder for future logic
    )

# ====
# Root Endpoint (For frontend interaction)
# ====
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint serving the HTML frontend"""
    if templates is None:
        raise HTTPException(status_code=500, detail="Jinja2Templates directory 'templates' not found.")
    
    departments = [{"value": k, "name": v["name"]} for k, v in DEPARTMENT_PROMPTS.items()]
    roles = [{"value": k, "name": v["name"]} for k, v in JOB_ROLES.items()]
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "departments": departments,
            "roles": roles,
            "is_demo_mode": GEMINI_API_KEY is None,
            "model_name": GEMINI_MODEL,
            "is_render": IS_RENDER,
        }
    )
