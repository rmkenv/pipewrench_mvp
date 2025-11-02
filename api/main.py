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
from urllib.parse import urlparse
import requests
import dotenv
import os
import anthropic

dotenv.load_dotenv()

app = FastAPI()

# ============================================================================
# CONFIGURATION: ENVIRONMENT VARIABLES AND CLIENTS
# ============================================================================
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")

anthropic_client = anthropic.Anthropic()

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

def get_role_list():
    """Return list of available roles"""
    return [{"id": role_id, "name": role_data["name"]} for role_id, role_data in JOB_ROLES.items()]

def get_role_context(role_id: str) -> str:
    """Get context for a specific role"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])["context"]


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


Always reference EPA regulations (40 CFR), state environmental rules, and environmental best practices."""
    },
    "safety": {
        "name": "Safety & Training",
        "prompt": """You are a specialized AI assistant for Safety & Training.

**Your Expertise:**
- OSHA regulations (29 CFR 1926, 1910)
- Workplace safety programs
- Confined space entry
- Trenching and excavation safety
- Personal protective equipment
- Safety training requirements
- Accident investigation

**Key Responsibilities:**
- Guide OSHA compliance
- Recommend safety procedures
- Assist with training program development
- Explain PPE requirements
- Support incident prevention

Always reference OSHA standards (29 CFR), ANSI standards, and safety best practices."""
    },
    "administration": {
        "name": "Administration & Planning",
        "prompt": """You are a specialized AI assistant for DPW Administration & Planning.

**Your Expertise:**
- Capital improvement planning
- Budget development
- Asset management
- Performance metrics
- Grant administration
- Public communication
- Strategic planning

**Key Responsibilities:**
- Guide planning processes
- Assist with budget preparation
- Explain grant requirements
- Support asset management programs
- Address administrative procedures

Always reference applicable federal grant requirements, municipal finance best practices, and planning standards."""
    }
}

def get_department_prompt(department_id: str) -> str:
    """Get specialized prompt for department"""
    return DEPARTMENT_PROMPTS.get(department_id, {}).get("prompt", "")

def get_all_departments():
    """Return list of all departments"""
    return [{"id": dept_id, "name": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

# ============================================================================
# SESSION STORAGE
# ============================================================================

# In-memory session storage (use Redis/database in production)
sessions: Dict[str, Dict] = {}

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

def extract_text_from_asbuilt_pdf(file: UploadFile) -> str:
    """Extract text from as-built drawing PDF (specialized processing)"""
    file.file.seek(0)
    response = requests.post(
        DRAWING_PROCESSING_API_URL,
        files={
            "file": (file.filename, file.file, file.content_type)
        },
        data={
            "ocr_method": "textract"
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Error processing as-built PDF")
    data = response.text
    return data

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "assistant", "content": "Use user query and document context to generate response."},
                {"role": "user", "content": f"User query: {query}\nDocument context: {context}"}
            ]
        )

        if message.content and len(message.content) > 0:
            # Get the first text block
            return message.content[0].text
        else:
            raise HTTPException(status_code=500, detail="Empty response from LLM")
            
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM response: {str(e)}")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...), is_asbuilt: bool = False):
    """Upload and process PDF document"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate inputs
    if not question or len(question.strip()) == 0:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Extract text
    if is_asbuilt:
        # Specialized processing for as-built drawings can be added here
        file.file.seek(0)
        text = extract_text_from_asbuilt_pdf(file)
    else:
        # Read file
        text = extract_text_from_pdf(content)
    
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
    
    # Store in session
    sessions[session_id] = {
        "filename": file.filename,
        "text": text,
        "uploaded_at": "timestamp_here",
        "is_asbuilt": is_asbuilt
    }
    
    # Build system prompt
    system_prompt = build_system_prompt(department, role)
    
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
    
    # Generate response (replace with actual LLM call)
    if has_document:
        # response = generate_llm_response(request.query, document_text, system_prompt, has_document)
        response = generate_llm_response(request.query, document_text, system_prompt, has_document)
    else:
        response = generate_mock_response(request.query, document_text, system_prompt, has_document)

    sources = ["whitelisted_urls"]
    if has_document:
        sources.insert(0, "uploaded_document")
    
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
        <div class="header">
            <h1>🏗️ Municipal DPW Knowledge Capture System</h1>
            <p>AI-Powered Infrastructure Knowledge Base with Source Verification</p>
        </div>

        <div id="alertBox" class="alert"></div>

        <!-- Upload Section (Optional) -->
        <div class="card">
            <h2>📄 Upload Document (Optional)</h2>
            <p style="color: #666; margin-bottom: 15px;">Upload a PDF to query your own documents, or skip to query whitelisted sources directly.</p>
            <div class="upload-zone" id="uploadZone">
                <div class="upload-icon">📁</div>
                <div>Drag & drop your PDF here or click to browse</div>
                <div style="color: #999; font-size: 0.9em; margin-top: 10px;">PDF files only</div>
                <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelect(event)">
            </div>

            <!-- As-Built Checkbox -->
            <div style="margin-top: 15px; padding: 15px; background: #f0f8ff; border-radius: 8px;">
                <label style="display: flex; align-items: center; cursor: pointer; font-weight: 500; color: #333;">
                    <input type="checkbox" id="asBuiltCheckbox" style="width: auto; margin-right: 10px; cursor: pointer;">
                    <span>📐 This is an As-Built/Record Drawing</span>
                </label>
                <p style="margin: 8px 0 0 32px; color: #666; font-size: 0.9em;">
                    Check this if uploading construction as-built drawings or record documents
                </p>
            </div>
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

    <script>
        let sessionId = null;

        // Load configuration
        async function loadConfiguration() {
            try {
                const rolesResponse = await fetch('/roles');
                const roles = await rolesResponse.json();
                const roleSelect = document.getElementById('roleSelect');
                roleSelect.innerHTML = roles.map(role => 
                    `<option value="${role.id}">${role.name}</option>`
                ).join('');

                const deptsResponse = await fetch('/departments');
                const depts = await deptsResponse.json();
                const deptSelect = document.getElementById('departmentSelect');
                deptSelect.innerHTML = '<option value="">Select Department</option>' +
                    depts.map(dept => 
                        `<option value="${dept.id}">${dept.name}</option>`
                    ).join('');
            } catch (error) {
                console.error('Error loading configuration:', error);
            }
        }

        // Drag and drop
        const uploadZone = document.getElementById('uploadZone');

        uploadZone.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                handleFile(file);
            }
        }

        async function handleFile(file) {
            if (!file.name.endsWith('.pdf')) {
                showAlert('Please upload a PDF file', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Get checkbox value
            const isAsBuilt = document.getElementById('asBuiltCheckbox').checked;

            showAlert('Uploading and processing document...', 'info');

            try {
                // Send is_asbuilt as query parameter
                const url = `/upload?is_asbuilt=${isAsBuilt}`;
                const response = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    sessionId = data.session_id;
                    showAlert(`✅ ${data.message}`, 'success');
                    document.getElementById('responseSection').style.display = 'block';
                    
                    // Generate temporary session ID for custom URLs
                    if (!sessionId) {
                        sessionId = 'temp_' + Date.now();
                    }
                    loadCustomUrls();
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error uploading file: ${error.message}`, 'error');
            }
        }

        async function submitQuery() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) {
                showAlert('Please enter a question', 'error');
                return;
            }

            const role = document.getElementById('roleSelect').value;
            const department = document.getElementById('departmentSelect').value;

            // Generate temporary session ID if none exists
            if (!sessionId) {
                sessionId = 'temp_' + Date.now();
            }

            showAlert('Processing your question...', 'info');

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        query: query,
                        role: role,
                        department: department || null
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    document.getElementById('responseBox').textContent = data.answer;
                    document.getElementById('responseSection').style.display = 'block';
                    showAlert('✅ Response generated', 'success');
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        function handleQueryKeyPress(event) {
            if (event.key === 'Enter') {
                submitQuery();
            }
        }

        async function addCustomUrl() {
            const urlInput = document.getElementById('customUrlInput');
            const url = urlInput.value.trim();

            if (!url) {
                showAlert('Please enter a URL', 'error');
                return;
            }

            // Generate temporary session ID if none exists
            if (!sessionId) {
                sessionId = 'temp_' + Date.now();
            }

            try {
                const response = await fetch('/custom-url/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        url: url
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert('✅ URL added successfully', 'success');
                    urlInput.value = '';
                    loadCustomUrls();
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        async function loadCustomUrls() {
            if (!sessionId) return;

            try {
                const response = await fetch(`/custom-url/list/${sessionId}`);
                const data = await response.json();

                const listDiv = document.getElementById('customUrlList');
                if (data.custom_urls.length === 0) {
                    listDiv.innerHTML = '<p style="color: #666; font-size: 0.9em; margin-top: 10px;">No custom URLs added yet</p>';
                } else {
                    listDiv.innerHTML = data.custom_urls.map(url => `
                        <div class="url-item">
                            <span>${url}</span>
                            <button class="btn-remove" onclick="removeCustomUrl('${url}')">Remove</button>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Error loading custom URLs:', error);
            }
        }

        async function removeCustomUrl(url) {
            try {
                const response = await fetch('/custom-url/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        url: url
                    })
                });

                if (response.ok) {
                    showAlert('✅ URL removed', 'success');
                    loadCustomUrls();
                } else {
                    showAlert('Error removing URL', 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        function showAlert(message, type) {
            const alertBox = document.getElementById('alertBox');
            alertBox.textContent = message;
            alertBox.className = `alert alert-${type} show`;

            if (type === 'success') {
                setTimeout(() => {
                    alertBox.classList.remove('show');
                }, 5000);
            }
        }

        function toggleFooter() {
            const content = document.getElementById('footerContent');
            const arrow = document.getElementById('footerArrow');
            content.classList.toggle('show');
            arrow.classList.toggle('expanded');
        }

        // Initialize
        loadConfiguration();
    </script>
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
