from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from anthropic import Anthropic
import os
from datetime import datetime
from typing import Optional
import uuid
import io
import re

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
    SYSTEM_INSTRUCTION,
)
from url_whitelist_config import (
    is_url_whitelisted,
    get_whitelisted_domains,
    get_total_whitelisted_urls,
    WHITELISTED_URLS,
)
from job_roles_config import (
    JOB_ROLES,
    get_all_roles,
    get_role_info,
    get_role_focus_areas,
)

app = FastAPI()

# Initialize Anthropic client with server env var key fallback
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Session storage (in production, use Redis or database)
sessions = {}

# URL regex for citation enforcement
URL_REGEX = re.compile(r'https?://[^\s)>\]]+')

# Embedded HTML (your full styled frontend with tabs, forms, etc.)
HTML_TEMPLATE = """<your full HTML here as in your example>"""

def build_system_prompt(department_key: str, role_key: Optional[str]) -> str:
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
    if filename.endswith('.txt'):
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content.decode('latin-1', errors='ignore')
    elif filename.endswith('.pdf'):
        if PdfReader is None:
            raise HTTPException(status_code=400, detail="PDF support not available. Please install PyPDF2.")
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    elif filename.endswith('.docx'):
        if docx is None:
            raise HTTPException(status_code=400, detail="Word document support not available. Please install python-docx.")
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse Word document: {str(e)}")
    elif filename.endswith('.doc'):
        raise HTTPException(status_code=400, detail="Old Word format (.doc) not supported. Please convert to .docx or .txt")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please use TXT, PDF, or DOCX.")

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_TEMPLATE

@app.get("/api/departments")
async def get_departments():
    return {"departments": get_department_list()}

@app.get("/api/roles")
async def list_roles():
    roles = []
    for key in get_all_roles():
        info = get_role_info(key)
        roles.append({"value": key, "title": info["title"]})
    return {"roles": roles}

@app.get("/api/system")
async def system_info():
    return {
        "total_whitelisted_urls": get_total_whitelisted_urls(),
        "whitelisted_domains": sorted(list(get_whitelisted_domains())),
        "roles": get_all_roles(),
        "departments": [d["value"] for d in get_department_list()],
    }

@app.get("/api/whitelist")
async def whitelist_overview():
    return {
        "count": get_total_whitelisted_urls(),
        "domains": sorted(list(get_whitelisted_domains())),
        "sample": sorted(list(WHITELISTED_URLS.keys()))[:50],
    }

@app.post("/api/session/create")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.now(),
        "questions": [],
        "documents": []
    }
    return {"session_id": session_id}

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.post("/api/query")
async def query_ai(
    question: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    system_prompt = build_system_prompt(department, role)
    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        answer = response.content[0].text
        answer = enforce_whitelist_on_text(answer)
        if session_id and session_id in sessions:
            sessions[session_id]["questions"].append({
                "question": question,
                "answer": answer,
                "department": get_department_name(department),
                "role": get_role_info(role)["title"] if role and get_role_info(role) else None,
                "timestamp": datetime.now().isoformat()
            })
        return {
            "answer": answer,
            "department": get_department_name(department)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/document/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
        text_content = extract_text_from_file(content, file.filename)
        max_chars = 100000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n\n[Content truncated due to size...]"
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content found in document.")
        anthropic_client = Anthropic(api_key=api_key) if api_key else client
        system_prompt = build_system_prompt(department, role)
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt + "\n\nAnalyze this document and extract key institutional knowledge, procedures, and important information. Provide APA-style citations from whitelisted sources only.",
            messages=[{
                "role": "user",
                "content": f"Document: {file.filename}\n\nContent:\n{text_content}"
            }]
        )
        analysis = response.content[0].text
        analysis = enforce_whitelist_on_text(analysis)
        sessions[session_id]["documents"].append({
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department),
            "role": get_role_info(role)["title"] if role and get_role_info(role) else None,
            "uploaded_at": datetime.now().isoformat()
        })
        return {
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session_data = sessions[session_id]
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PipeWrench AI - Knowledge Capture Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            h1 {{ color: #1e40af; }}
            h2 {{ color: #3b82f6; margin-top: 30px; }}
            .question {{ background: #eff6ff; padding: 15px; margin: 20px 0; border-left: 4px solid #3b82f6; }}
            .answer {{ margin: 10px 0; white-space: pre-wrap; }}
            .document {{ background: #fef3c7; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .metadata {{ color: #6b7280; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>PipeWrench AI - Knowledge Capture Report</h1>
        <p class="metadata">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <h2>Questions & Answers ({len(session_data['questions'])})</h2>
    """
    for i, qa in enumerate(session_data['questions'], 1):
        role_display = f" • {qa['role']}" if qa.get('role') else ""
        html_report += f"""
        <div class="question">
            <strong>Q{i} ({qa['department']}{role_display}):</strong> {qa['question']}
            <div class="answer">
                <strong>Answer:</strong><br>
                {qa['answer']}
            </div>
            <p class="metadata">Asked: {qa['timestamp']}</p>
        </div>
        """
    html_report += f"""
        <h2>Documents Analyzed ({len(session_data['documents'])})</h2>
    """
    for doc in session_data['documents']:
        role_display = f" • {doc['role']}" if doc.get('role') else ""
        html_report += f"""
        <div class="document">
            <strong>Document:</strong> {doc['filename']} ({doc['department']}{role_display})<br>
            <div class="answer">
                <strong>Analysis:</strong><br>
                {doc['analysis']}
            </div>
            <p class="metadata">Uploaded: {doc['uploaded_at']}</p>
        </div>
        """
    html_report += """
    </body>
    </html>
    """
    return HTMLResponse(content=html_report)

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")
