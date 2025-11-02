# app_combined.py
# FastAPI app for Render (ASGI). Start with:
# uvicorn app_combined:app --host 0.0.0.0 --port $PORT

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import datetime
from typing import Optional, Dict, List
import re
from urllib.parse import urlparse
import requests
import logging
import json

# Anthropic is optional at boot time — app should not crash if key is missing
try:
    from anthropic import Anthropic, APIError  # type: ignore
except Exception:
    Anthropic = None  # type: ignore
    APIError = Exception  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PipeWrench AI", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------------------
# Whitelist config
# --------------------------------------------------------------------------------------
CUSTOM_URLS_FILE = os.path.join(os.path.dirname(__file__), "custom_whitelist.json")
BASE_WHITELISTED_URLS = [
    {"url": "https://www.acquisition.gov/far/part-36", "include_children": True},
]
URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

def _load_custom_urls() -> List[Dict[str, object]]:
    try:
        if os.path.exists(CUSTOM_URLS_FILE):
            with open(CUSTOM_URLS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading custom URLs: {e}")
    return []

def _save_custom_urls(custom_urls: List[Dict[str, object]]) -> bool:
    try:
        with open(CUSTOM_URLS_FILE, 'w') as f:
            json.dump(custom_urls, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving custom URLs: {e}")
        return False

def _get_all_whitelisted_urls() -> List[Dict[str, object]]:
    return BASE_WHITELISTED_URLS + _load_custom_urls()

def get_total_whitelisted_urls() -> int:
    return len(_get_all_whitelisted_urls())

def get_whitelisted_sources() -> List[Dict[str, str]]:
    return _get_all_whitelisted_urls()  # type: ignore

def get_whitelisted_domains() -> set:
    all_urls = _get_all_whitelisted_urls()
    domains = set()
    for entry in all_urls:
        parsed = urlparse(str(entry["url"]))
        domains.add(parsed.netloc)
    return domains

def is_url_whitelisted(url: str) -> bool:
    if not url:
        return False
    all_urls = _get_all_whitelisted_urls()
    parsed_url = urlparse(url)
    url_domain_path = f"{parsed_url.netloc}{parsed_url.path}".rstrip('/')
    for whitelist_entry in all_urls:
        parsed_whitelist = urlparse(str(whitelist_entry["url"]))
        whitelist_domain_path = f"{parsed_whitelist.netloc}{parsed_whitelist.path}".rstrip('/')
        if url_domain_path == whitelist_domain_path:
            return True
        if whitelist_entry.get("include_children", False) and url_domain_path.startswith(whitelist_domain_path):
            return True
    return False

# --------------------------------------------------------------------------------------
# Roles and Departments
# --------------------------------------------------------------------------------------
JOB_ROLES = {
    "director": {
        "title": "Department Director",
        "context": "High-level strategic info, compliance, safety standards, best practices."
    }
}

def get_role_context(role_key: Optional[str]) -> str:
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["context"]
    return ""

def get_role_title(role_key: Optional[str]) -> str:
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["title"]
    return ""

def get_all_roles() -> List[str]:
    return list(JOB_ROLES.keys())

SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in municipal DPW operations and institutional knowledge capture.
CRITICAL RULES: only cite from approved whitelist; include specific URLs; when not available, say it cannot be verified; APA 7th; do not hallucinate; distinguish verified facts vs best practices vs SME-needed.
"""

DEPARTMENT_CONTEXTS = {
    "general_public_works": {
        "name": "General Public Works",
        "context": "Assist general public works personnel with broad infrastructure questions."
    }
}

def get_department_prompt(department_key: str) -> str:
    dept = DEPARTMENT_CONTEXTS.get(department_key, DEPARTMENT_CONTEXTS["general_public_works"])
    return SYSTEM_INSTRUCTION + "\n\n" + dept["context"]

def get_department_list() -> list:
    return [{"value": key, "name": dept["name"]} for key, dept in DEPARTMENT_CONTEXTS.items()]

def get_department_name(department_key: str) -> str:
    dept = DEPARTMENT_CONTEXTS.get(department_key, DEPARTMENT_CONTEXTS["general_public_works"])
    return dept["name"]

# --------------------------------------------------------------------------------------
# Env + external clients
# --------------------------------------------------------------------------------------
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

anthropic_client = None
if ANTHROPIC_API_KEY and Anthropic:
    try:
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as e:
        logger.warning(f"Anthropic client init failed: {e}")

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def build_system_prompt(department_key: str, role_key: Optional[str]) -> str:
    base = get_department_prompt(department_key)
    role_part = ""
    if role_key:
        title = get_role_title(role_key)
        ctx = get_role_context(role_key)
        if title or ctx:
            role_part = f"\n\nROLE CONTEXT:\n- Title: {title or role_key}\n- Guidance:\n{ctx}"
    whitelist_notice = (
        f"\n\nURL RESTRICTIONS:\n"
        f"- Only approved whitelist sources\n"
        f"- Include specific URL for each citation\n"
        f"- If info not in whitelist, say so\n"
        f"- Total Whitelisted URLs: {get_total_whitelisted_urls()}\n"
    )
    return base + role_part + whitelist_notice

def extract_text_from_pdf(content: bytes) -> str:
    # Replace with a real extractor (PyPDF/Textract) as needed
    return "Sample extracted text from PDF"

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    if not anthropic_client:
        # Do not crash service — inform caller explicitly
        raise HTTPException(status_code=500, detail="Anthropic client not configured. Set ANTHROPIC_API_KEY.")
    try:
        message = anthropic_client.messages.create(  # type: ignore
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"User query: {query}\nDocument context: {context}"}],
        )
        content = getattr(message, "content", None)
        if content and len(content) > 0 and hasattr(content[0], "text"):
            return content[0].text
        raise HTTPException(status_code=500, detail="Empty response from LLM")
    except Exception as e:
        # Anthropic SDK raises different exception types — surface as 502
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    return f"Mock response for: {query}\n\nContext: {context[:100]}...\nSystem prompt: {system_prompt[:50]}..."

def enforce_whitelist_on_text(text: str) -> str:
    bad_urls = []
    for url in set(URL_REGEX.findall(text or "")):
        url_clean = url.rstrip('.,);]')
        if not is_url_whitelisted(url_clean):
            bad_urls.append(url_clean)
    if not bad_urls:
        return text
    note = (
        "\n\n[COMPLIANCE NOTICE]\n"
        "The following URLs are not approved:\n" + "\n".join(f"- {u}" for u in sorted(bad_urls))
    )
    return text + note

def sanitize_html(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))

# --------------------------------------------------------------------------------------
# In-memory session manager
# --------------------------------------------------------------------------------------
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)
    def create_session(self, session_id: str, data: Dict) -> None:
        self.sessions[session_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "documents": [],
            "questions": [],
        }
    def update_session(self, session_id: str, updates: Dict) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)

session_manager = SessionManager()

# --------------------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------------------
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

# --------------------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "PipeWrench AI API", "status": "running"}

@app.get("/healthz")
async def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}

@app.get("/api/departments")
async def api_get_departments():
    return {"departments": get_department_list()}

@app.get("/api/roles")
async def list_roles():
    roles = [{"value": key, "title": get_role_title(key)} for key in get_all_roles()]
    return {"roles": roles}

@app.get("/api/system")
async def system_info():
    return SystemInfoResponse(
        total_whitelisted_urls=get_total_whitelisted_urls(),
        whitelisted_domains=sorted(list(get_whitelisted_domains())),
        roles=get_all_roles(),
        departments=[d["value"] for d in get_department_list()],
        config={"version": "1.0"},
    )

@app.get("/api/whitelist")
async def whitelist_overview():
    all_urls = get_whitelisted_sources()
    sample_urls = [str(entry["url"]) for entry in all_urls[:50]]
    return {
        "count": get_total_whitelisted_urls(),
        "domains": sorted(list(get_whitelisted_domains())),
        "sample": sample_urls
    }

def extract_text_from_asbuilt_pdf(file: UploadFile) -> str:
    try:
        file.file.seek(0)
        response = requests.post(
            DRAWING_PROCESSING_API_URL,
            files={"file": (file.filename, file.file, file.content_type or "application/pdf")},
            data={"ocr_method": "textract"},
            timeout=30,
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error processing as-built PDF")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error calling drawing processing API: {e}")
        raise HTTPException(status_code=502, detail="Drawing processing service unavailable")

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    is_asbuilt: bool = False,
    session_id: Optional[str] = None,
    department: str = "general_public_works",
    role: Optional[str] = None,
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        if is_asbuilt:
            text = extract_text_from_asbuilt_pdf(file)
        else:
            content = await file.read()
            text = extract_text_from_pdf(content)
    finally:
        try:
            await file.close()
        except Exception:
            pass

    page_count = max(1, len(text) // 2500)
    session_data = {
        "filename": file.filename,
        "text": text,
        "uploaded_at": datetime.now().isoformat(),
        "is_asbuilt": is_asbuilt,
        "department": department,
        "role": role,
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
        is_asbuilt=is_asbuilt,
    )

@app.post("/query")
async def query_documents(request: QueryRequest):
    document_text = ""
    has_document = False
    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session:
            document_text = session.get("text", "")
            has_document = bool(document_text)
    dept_key = request.department or "general_public_works"
    system_prompt = build_system_prompt(dept_key, request.role)
    if has_document:
        response = generate_llm_response(request.query, document_text, system_prompt, has_document)
    else:
        response = generate_mock_response(request.query, document_text, system_prompt, has_document)
    response = enforce_whitelist_on_text(response)
    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session is not None:
            session.setdefault("questions", []).append({
                "question": request.query,
                "answer": response,
                "timestamp": datetime.now().isoformat(),
                "role": request.role,
                "department": dept_key
            })
    return {"answer": response, "sources": ["whitelisted_urls"] + (["uploaded_document"] if has_document else [])}

@app.post("/api/document/upload")
async def api_upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    session = session_manager.get_session(session_id)
    if session is None:
        session_manager.create_session(session_id, {})
    try:
        content = await file.read()
        text = extract_text_from_pdf(content)
    finally:
        try:
            await file.close()
        except Exception:
            pass
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

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    html_report = f"""
<!DOCTYPE html>
<html>
<head><title>PipeWrench AI - Knowledge Capture Report</title><meta charset="UTF-8"></head>
<body>
<h1>Municipal DPW Knowledge Capture System</h1>
<p><strong>Filename:</strong> {sanitize_html(session.get('filename','N/A'))}</p>
<p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
"""
    return HTMLResponse(content=html_report)

# --------------------------------------------------------------------------------------
# Global exception handler
# --------------------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later."}
    )
