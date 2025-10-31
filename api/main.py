"""
PipeWrench AI - Municipal DPW Knowledge Capture System
FastAPI application with improved error handling, logging, and production readiness.
"""
# Force redeploy timestamp: 2025-10-31 13:15:00 UTC - URL whitelist fix

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from anthropic import Anthropic, APIError
import os
from datetime import datetime
from typing import Optional
import io
import re
from pathlib import Path

# Import for file parsing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

# Add path for local imports
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Import configurations
from department_prompts_config import (
    get_department_prompt,
    get_department_list,
    get_department_name,
)
from url_whitelist_config import (
    is_url_whitelisted,
    get_whitelisted_domains,
    get_total_whitelisted_urls,
    WHITELISTED_URLS,
)
from job_roles_config import (
    get_all_roles,
    get_role_info,
)

# Import new modules
from config import settings
from utils import logger, SessionManager, sanitize_html, validate_file_extension, format_file_size
from models import (
    SessionCreateResponse, SessionStatusResponse, QueryResponse,
    DocumentUploadResponse, HealthCheckResponse, SystemInfoResponse,
    ErrorResponse
)

# Validate configuration on startup
try:
    settings.validate()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    # Don't crash on startup, but log the error
    # This allows health checks to work even without API key

# Initialize FastAPI app
app = FastAPI(
    title="PipeWrench AI",
    description="Municipal DPW Knowledge Capture System",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
session_manager = SessionManager()

# Initialize Anthropic client
try:
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {e}")
    client = None

# URL regex for citation enforcement
URL_REGEX = re.compile(r'https?://[^\s)>\]]+')

# Load HTML template
HTML_TEMPLATE = None
html_path = Path(__file__).parent.parent / "index.html"
try:
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            HTML_TEMPLATE = f.read()
        logger.info("HTML template loaded successfully")
    else:
        logger.warning(f"HTML template not found at {html_path}")
except Exception as e:
    logger.error(f"Failed to load HTML template: {e}")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("=" * 50)
    logger.info("PipeWrench AI Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Claude Model: {settings.CLAUDE_MODEL}")
    logger.info(f"API Key Configured: {bool(settings.ANTHROPIC_API_KEY)}")
    logger.info("=" * 50)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("PipeWrench AI shutting down...")
    # Cleanup sessions
    session_count = session_manager.get_session_count()
    logger.info(f"Cleaning up {session_count} active sessions")


# Middleware for automatic session cleanup
@app.middleware("http")
async def cleanup_middleware(request: Request, call_next):
    """Middleware to periodically cleanup expired sessions."""
    session_manager.maybe_cleanup()
    response = await call_next(request)
    return response


# Helper Functions
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


def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract text content from uploaded file."""
    ext = Path(filename).suffix.lower()
    
    if ext == '.txt':
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content.decode('latin-1', errors='ignore')
            except Exception as e:
                logger.error(f"Failed to decode text file: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to decode text file. Please ensure it's a valid UTF-8 or Latin-1 encoded file."
                )
    
    elif ext == '.pdf':
        if PdfReader is None:
            raise HTTPException(
                status_code=400,
                detail="PDF support not available. Please contact administrator."
            )
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text += page.extract_text() + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            if not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="No text could be extracted from PDF. The file may be image-based or corrupted."
                )
            return text
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse PDF. The file may be corrupted or password-protected."
            )
    
    elif ext == '.docx':
        if docx is None:
            raise HTTPException(
                status_code=400,
                detail="Word document support not available. Please contact administrator."
            )
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            if not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="No text could be extracted from Word document."
                )
            return text
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse Word document: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to parse Word document. The file may be corrupted."
            )
    
    elif ext == '.doc':
        raise HTTPException(
            status_code=400,
            detail="Old Word format (.doc) not supported. Please convert to .docx, .txt, or PDF."
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Please use TXT, PDF, or DOCX."
        )


# Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main HTML interface."""
    if HTML_TEMPLATE is None:
        logger.error("HTML template not loaded")
        return HTMLResponse(
            content="<h1>Service Temporarily Unavailable</h1><p>Please contact administrator.</p>",
            status_code=503
        )
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.1.0",
        environment=settings.ENVIRONMENT,
        api_key_configured=bool(settings.ANTHROPIC_API_KEY),
        active_sessions=session_manager.get_session_count()
    )


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


@app.get("/api/system", response_model=SystemInfoResponse)
async def system_info():
    """Get system configuration information."""
    try:
        return SystemInfoResponse(
            total_whitelisted_urls=get_total_whitelisted_urls(),
            whitelisted_domains=sorted(list(get_whitelisted_domains())),
            roles=get_all_roles(),
            departments=[d["value"] for d in get_department_list()],
            config=settings.get_info()
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


@app.post("/api/session/create", response_model=SessionCreateResponse)
async def create_session():
    """Create a new user session."""
    try:
        session_id = session_manager.create_session()
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session data."""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return session


@app.get("/api/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get session status information."""
    status = session_manager.get_session_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return SessionStatusResponse(**status)


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_manager.delete_session(session_id):
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/query")
async def query_ai(
    question: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """Query the AI with a question about uploaded documents."""
    logger.info(f"Query request - Department: {department}, Role: {role}, Session: {session_id}")
    
    # Validate inputs
    if not question or len(question.strip()) == 0:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question too long. Maximum 2000 characters.")
    
    # Get or create Anthropic client
    anthropic_client = None
    if api_key:
        try:
            anthropic_client = Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to create client with provided API key: {e}")
            raise HTTPException(status_code=400, detail="Invalid API key provided")
    else:
        anthropic_client = client
    
    if anthropic_client is None:
        raise HTTPException(
            status_code=503,
            detail="API key not configured. Please provide your Anthropic API key."
        )
    
    # Build system prompt
    system_prompt = build_system_prompt(department, role)
    
    # Make API call
    try:
        logger.info(f"Calling Claude API with model: {settings.CLAUDE_MODEL}")
        response = anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        
        answer = response.content[0].text
        answer = enforce_whitelist_on_text(answer)
        
        # Store in session if provided
        if session_id:
            session = session_manager.get_session(session_id)
            if session:
                session["questions"].append({
                    "question": question,
                    "answer": answer,
                    "department": get_department_name(department),
                    "role": get_role_info(role)["title"] if role and get_role_info(role) else None,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"Stored query in session {session_id}")
            else:
                logger.warning(f"Session {session_id} not found for storing query")
        
        return QueryResponse(
            answer=answer,
            department=get_department_name(department),
            timestamp=datetime.now().isoformat()
        )
    
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
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """Upload and analyze a document."""
    logger.info(f"Document upload - File: {file.filename}, Session: {session_id}")
    
    # Validate session
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Validate file extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Check file size
        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB. "
                       f"Your file is {format_file_size(file_size)}."
            )
        
        logger.info(f"Processing file: {file.filename}, Size: {format_file_size(file_size)}")
        
        # Extract text
        text_content = extract_text_from_file(content, file.filename)
        
        # Truncate if too long
        if len(text_content) > settings.MAX_TEXT_CHARS:
            logger.warning(f"File content truncated from {len(text_content)} to {settings.MAX_TEXT_CHARS} chars")
            text_content = text_content[:settings.MAX_TEXT_CHARS] + "\n\n[Content truncated due to size...]"
        
        if not text_content.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content found in document. Please ensure the file contains readable text."
            )
        
        # Get or create Anthropic client
        anthropic_client = None
        if api_key:
            try:
                anthropic_client = Anthropic(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to create client with provided API key: {e}")
                raise HTTPException(status_code=400, detail="Invalid API key provided")
        else:
            anthropic_client = client
        
        if anthropic_client is None:
            raise HTTPException(
                status_code=503,
                detail="API key not configured. Please provide your Anthropic API key."
            )
        
        # Build system prompt
        system_prompt = build_system_prompt(department, role)
        
        # Analyze document
        logger.info(f"Analyzing document with Claude API")
        response = anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt + "\n\nAnalyze this document and extract key institutional knowledge, procedures, and important information. Provide citations from whitelisted sources only.",
            messages=[{
                "role": "user",
                "content": f"Document: {file.filename}\n\nContent:\n{text_content}"
            }]
        )
        
        analysis = response.content[0].text
        analysis = enforce_whitelist_on_text(analysis)
        
        # Store in session
        session["documents"].append({
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department),
            "role": get_role_info(role)["title"] if role and get_role_info(role) else None,
            "uploaded_at": datetime.now().isoformat(),
            "file_size": format_file_size(file_size)
        })
        
        logger.info(f"Document {file.filename} analyzed and stored successfully")
        
        return DocumentUploadResponse(
            filename=file.filename,
            analysis=analysis,
            department=get_department_name(department),
            file_size=format_file_size(file_size)
        )
    
    except HTTPException:
        raise
    except APIError as e:
        logger.error(f"Anthropic API error during document upload: {e}")
        raise HTTPException(
            status_code=502,
            detail="AI service error. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error during document upload: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your document."
        )


@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report for a session."""
    logger.info(f"Generating report for session: {session_id}")
    
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    try:
        # Build HTML report with sanitization
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
        .stats {{
            background: #f0f9ff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
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
        <p class="metadata">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p class="metadata">Session ID: {sanitize_html(session_id)}</p>
        
        <div class="stats">
            <strong>Session Statistics:</strong><br>
            Documents Analyzed: {len(session["documents"])}<br>
            Questions Answered: {len(session["questions"])}<br>
            Created: {session["created_at"].strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <h2>📄 Documents Analyzed ({len(session["documents"])})</h2>
"""
        
        for i, doc in enumerate(session["documents"], 1):
            role_display = f" • {sanitize_html(doc['role'])}" if doc.get('role') else ""
            file_size_display = f" ({doc['file_size']})" if doc.get('file_size') else ""
            html_report += f"""
        <div class="document">
            <strong>Document {i}:</strong> {sanitize_html(doc['filename'])}{file_size_display}<br>
            <strong>Department:</strong> {sanitize_html(doc['department'])}{role_display}<br>
            <div class="answer">
                <strong>Analysis:</strong><br>
                {sanitize_html(doc['analysis'])}
            </div>
            <p class="metadata">Uploaded: {doc['uploaded_at']}</p>
        </div>
"""
        
        html_report += f"""
        <h2>💬 Questions & Answers ({len(session["questions"])})</h2>
"""
        
        for i, qa in enumerate(session["questions"], 1):
            role_display = f" • {sanitize_html(qa['role'])}" if qa.get('role') else ""
            html_report += f"""
        <div class="question">
            <strong>Q{i} ({sanitize_html(qa['department'])}{role_display}):</strong> {sanitize_html(qa['question'])}
            <div class="answer">
                <strong>Answer:</strong><br>
                {sanitize_html(qa['answer'])}
            </div>
            <p class="metadata">Asked: {qa['timestamp']}</p>
        </div>
"""
        
        html_report += """
        <div class="footer">
            <p><strong>PipeWrench AI</strong> - Municipal DPW Knowledge Capture System</p>
            <p>Built with Claude 3.5 Sonnet by Anthropic</p>
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
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred. Please try again later."
        ).dict()
    )


# For Vercel
app = app
