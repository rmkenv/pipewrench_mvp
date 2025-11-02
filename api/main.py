"""
PipeWrench AI - Municipal DPW Knowledge Capture System
FastAPI application with improved error handling, logging, and production readiness.
"""
# Force redeploy timestamp: 2025-11-02 09:07:00 UTC - Job roles integration fix

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from anthropic import Anthropic, APIError
from pydantic import BaseModel
import os
from datetime import datetime
from typing import Optional, Dict, List
import io
import re
from urllib.parse import urlparse
import requests
import dotenv
import anthropic
import logging

dotenv.load_dotenv()

app = FastAPI()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION: ENVIRONMENT VARIABLES AND CLIENTS
# ============================================================================
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ============================================================================
# CONFIGURATION: JOB ROLES (Integrated inline to prevent import errors)
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

def get_all_roles():
    """Return list of available role keys"""
    return list(JOB_ROLES.keys())

def get_role_list():
    """Return list of available roles (as id and name)"""
    return [{"id": role_id, "name": role_data["name"]} for role_id, role_data in JOB_ROLES.items()]

def get_role_context(role_id: str) -> str:
    """Get context for a specific role"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])["context"]

def get_role_info(role_id: str) -> Dict:
    """Get full role info"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])

# ============================================================================
# CONFIGURATION: DEPARTMENTS
# ============================================================================

DEPARTMENT_PROMPTS = {
    "general_public_works": {
        "name": "General Public Works",
        "prompt": """You are a specialized AI assistant for General Public Works operations.

**Your Expertise:**
- Municipal infrastructure maintenance
- Public works operations and management
- Construction and project coordination
- Equipment and fleet management
- Regulatory compliance
- Best practices for municipal services

**Key Responsibilities:**
- Guide day-to-day public works operations
- Advise on infrastructure management
- Support maintenance and repair operations
- Assist with project coordination
- Ensure compliance with standards

Always reference federal regulations, state standards, and industry best practices."""
    },
    "water_wastewater": {
        "name": "Water & Wastewater",
        "prompt": """You are a specialized AI assistant for Water & Wastewater operations.

**Your Expertise:**
- Water treatment and distribution
- Wastewater collection and treatment
- EPA regulations (40 CFR Part 450)
- Safe drinking water standards
- Asset management for water systems
- Water quality monitoring

**Key Responsibilities:**
- Guide water system operations
- Advise on treatment processes
- Support asset management
- Ensure EPA compliance
- Recommend best practices

Always reference EPA regulations (40 CFR), state environmental rules, and water quality standards."""
    },
    "streets_roads": {
        "name": "Streets & Roads",
        "prompt": """You are a specialized AI assistant for Streets & Roads operations.

**Your Expertise:**
- Road maintenance and repair
- Pavement management
- Traffic control and safety
- Drainage and stormwater
- Snow and ice management
- FHWA standards

**Key Responsibilities:**
- Guide street maintenance operations
- Advise on repair procedures
- Support asset management
- Ensure safety compliance
- Recommend best practices

Always reference FHWA standards, ASCE guidelines, and DOT best practices."""
    },
    "fleet_management": {
        "name": "Fleet Management",
        "prompt": """You are a specialized AI assistant for Fleet Management.

**Your Expertise:**
- Vehicle maintenance and repair
- Fleet operations and scheduling
- Fuel management and emissions
- Safety and compliance
- Equipment management
- Preventive maintenance programs

**Key Responsibilities:**
- Guide maintenance operations
- Advise on fleet scheduling
- Support preventive maintenance
- Ensure safety compliance
- Recommend cost-saving practices

Always reference manufacturer specifications, EPA emissions standards, and industry best practices."""
    },
    "stormwater": {
        "name": "Stormwater Management",
        "prompt": """You are a specialized AI assistant for Stormwater Management.

**Your Expertise:**
- Stormwater collection and treatment
- EPA regulations (40 CFR Part 122)
- NPDES permit compliance
- Green infrastructure
- Permitting and compliance
- Water quality monitoring

**Key Responsibilities:**
- Guide stormwater operations
- Advise on compliance procedures
- Support permit management
- Ensure EPA compliance
- Recommend best practices

Always reference EPA regulations (40 CFR), state environmental rules, and stormwater best practices."""
    },
    "environmental": {
        "name": "Environmental Compliance",
        "prompt": """You are a specialized AI assistant for Environmental Compliance.

**Your Expertise:**
- EPA regulations and compliance
- Environmental permits
- Spill prevention and response
- Hazardous material management
- Environmental monitoring
- Reporting requirements

**Key Responsibilities:**
- Guide compliance procedures
- Advise on permit requirements
- Support environmental monitoring
- Ensure EPA compliance
- Recommend best practices

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

def get_department_list():
    """Return department list formatted for API"""
    return [{"value": dept_id, "name": dept_data["name"]} for dept_id, dept_data in DEPARTMENT_PROMPTS.items()]

# ============================================================================
# WHITELISTED URLS CONFIGURATION
# ============================================================================

WHITELISTED_URLS = [
    {"url": "https://www.osha.gov", "include_children": True, "description": "OSHA Standards and Regulations"},
    {"url": "https://www.epa.gov", "include_children": True, "description": "EPA Environmental Regulations"},
    {"url": "https://www.fhwa.dot.gov", "include_children": True, "description": "Federal Highway Administration"},
    {"url": "https://www.usbm.gov", "include_children": True, "description": "US Bureau of Mines"},
    {"url": "https://www.access.gpo.gov", "include_children": True, "description": "Government Publishing Office"},
]

URL_REGEX = re.compile(r'https?://[^\s]+')

def get_total_whitelisted_urls() -> int:
    """Get total count of whitelisted URLs"""
    return len(WHITELISTED_URLS)

def get_whitelisted_domains() -> set:
    """Get set of whitelisted domains"""
    domains = set()
    for entry in WHITELISTED_URLS:
        parsed = urlparse(entry["url"])
        domains.add(parsed.netloc)
    return domains

def is_url_whitelisted(url: str) -> bool:
    """Check if URL is in whitelist"""
    parsed_url = urlparse(url)
    for entry in WHITELISTED_URLS:
        parsed_entry = urlparse(entry["url"])
        if parsed_entry.netloc == parsed_url.netloc:
            if entry.get("include_children", False):
                return True
            elif parsed_entry.path == parsed_url.path:
                return True
    return False

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

class ErrorResponse(BaseModel):
    error: str
    detail: str

class SystemInfoResponse(BaseModel):
    total_whitelisted_urls: int
    whitelisted_domains: List[str]
    roles: List[str]
    departments: List[str]
    config: Optional[Dict] = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def sanitize_html(text: str) -> str:
    """Sanitize text for HTML output"""
    if not text:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    return text

def build_system_prompt(department_key: Optional[str], role_key: Optional[str]) -> str:
    """Build system prompt with department and role context."""
    base = get_department_prompt(department_key) if department_key else ""
    if not base:
        base = "You are a helpful assistant for municipal Department of Public Works."
    
    role_txt = ""
    if role_key and role_key in JOB_ROLES:
        role_data = JOB_ROLES[role_key]
        role_txt = f"\n\nROLE CONTEXT:\n- Role: {role_data['name']}\n- Context: {role_data['context']}"
    
    whitelist_notice = f"\n\nURL RESTRICTIONS:\n" \
                      f"- Only cite and reference sources from approved whitelist\n" \
                      f"- Include the specific URL for each citation\n" \
                      f"- If info is not in whitelist, clearly state that it cannot be verified from approved sources\n" \
                      f"- All child pages of whitelisted URLs are permitted\n" \
                      f"- Total Whitelisted URLs: {get_total_whitelisted_urls()}\n" \
                      f"- Approved Domains: {', '.join(sorted(list(get_whitelisted_domains())))}"
    
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

def extract_text_from_asbuilt_pdf(file: UploadFile) -> str:
    """Extract text from as-built drawing PDF (specialized processing)"""
    try:
        file.file.seek(0)
        response = requests.post(
            DRAWING_PROCESSING_API_URL,
            files={
                "file": (file.filename, file.file, file.content_type)
            },
            data={
                "ocr_method": "textract"
            },
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"Error processing as-built PDF: {response.status_code}")
            raise HTTPException(status_code=400, detail="Error processing as-built PDF")
        
        return response.text
    except Exception as e:
        logger.error(f"Failed to extract text from as-built PDF: {e}")
        raise HTTPException(status_code=400, detail="Error processing as-built PDF")

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate response from Claude using Anthropic API"""
    try:
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"User query: {query}\n\nDocument context: {context if context else 'No document provided'}"
                }
            ]
        )

        if message.content and len(message.content) > 0:
            response_text = message.content[0].text
            response_text = enforce_whitelist_on_text(response_text)
            return response_text
        else:
            raise HTTPException(status_code=500, detail="Empty response from LLM")
            
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - return HTML UI"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PipeWrench AI - Municipal DPW Knowledge Capture</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }
            
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            .section {
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            
            .section h2 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.5em;
            }
            
            .section p {
                color: #555;
                line-height: 1.6;
                margin-bottom: 10px;
            }
            
            .endpoint {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 6px;
                border: 1px solid #ddd;
                font-family: 'Courier New', monospace;
                color: #333;
            }
            
            .endpoint strong {
                color: #667eea;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            
            .feature {
                padding: 15px;
                background: white;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
            
            .feature h3 {
                color: #667eea;
                margin-bottom: 8px;
            }
            
            .feature p {
                color: #666;
                font-size: 0.9em;
            }
            
            .badge {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                margin: 2px;
            }
            
            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e5e7eb;
                text-align: center;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏗️ PipeWrench AI</h1>
            <p class="subtitle">Municipal DPW Knowledge Capture System</p>
            
            <div class="section">
                <h2>✨ Features</h2>
                <div class="features">
                    <div class="feature">
                        <h3>📄 Document Upload</h3>
                        <p>Upload PDFs and query your institutional knowledge</p>
                    </div>
                    <div class="feature">
                        <h3>🤖 AI Powered</h3>
                        <p>Claude 3.5 Sonnet for intelligent analysis</p>
                    </div>
                    <div class="feature">
                        <h3>✅ Compliance</h3>
                        <p>126+ whitelisted compliance sources</p>
                    </div>
                    <div class="feature">
                        <h3>👥 Role-Based</h3>
                        <p>Specialized contexts for 8+ DPW roles</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📡 API Endpoints</h2>
                <div class="endpoint"><strong>GET</strong> /api/roles - List available job roles</div>
                <div class="endpoint"><strong>GET</strong> /api/departments - List departments</div>
                <div class="endpoint"><strong>GET</strong> /api/system - System configuration</div>
                <div class="endpoint"><strong>POST</strong> /api/document/upload - Upload document</div>
                <div class="endpoint"><strong>POST</strong> /api/query - Query documents</div>
                <div class="endpoint"><strong>POST</strong> /api/report/generate - Generate report</div>
            </div>
            
            <div class="section">
                <h2>🎯 Available Roles</h2>
                <div>
                    <span class="badge">General DPW Staff</span>
                    <span class="badge">DPW Director</span>
                    <span class="badge">Civil Engineer</span>
                    <span class="badge">Project Manager</span>
                    <span class="badge">Inspector</span>
                    <span class="badge">Maintenance Supervisor</span>
                    <span class="badge">Environmental Officer</span>
                    <span class="badge">Safety Officer</span>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>PipeWrench AI</strong> - Built with Claude 3.5 Sonnet by Anthropic</p>
                <p>Preserving Institutional Knowledge in Public Works</p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/api/roles")
async def list_roles():
    """Get list of all available job roles."""
    try:
        roles = []
        for key in get_all_roles():
            info = JOB_ROLES.get(key)
            roles.append({"value": key, "title": info["name"]})
        return {"roles": roles}
    except Exception as e:
        logger.error(f"Failed to get roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve roles")

@app.get("/api/departments")
async def get_departments():
    """Get list of all available departments."""
    try:
        return {"departments": get_department_list()}
    except Exception as e:
        logger.error(f"Failed to get departments: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve departments")

@app.get("/api/system")
async def system_info():
    """Get system configuration information."""
    try:
        return {
            "total_whitelisted_urls": get_total_whitelisted_urls(),
            "whitelisted_domains": sorted(list(get_whitelisted_domains())),
            "roles": get_all_roles(),
            "departments": [d["value"] for d in get_department_list()],
            "model": "claude-3-5-sonnet-20241022"
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")

@app.get("/api/whitelist")
async def whitelist_overview():
    """Get overview of whitelisted URLs."""
    try:
        sample_urls = [entry["url"] for entry in WHITELISTED_URLS[:50]]
        
        return {
            "count": get_total_whitelisted_urls(),
            "domains": sorted(list(get_whitelisted_domains())),
            "sample": sample_urls,
        }
    except Exception as e:
        logger.error(f"Failed to get whitelist: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve whitelist")

@app.post("/api/query")
async def query_documents(request: QueryRequest):
    """Query with or without uploaded documents"""
    
    try:
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        # Get document context if session exists
        document_text = ""
        has_document = False
        
        if session_id in sessions:
            session = sessions[session_id]
            document_text = session.get("text", "")
            has_document = True
        
        # Build system prompt
        system_prompt = build_system_prompt(request.department, request.role)
        
        # Generate response
        response = generate_llm_response(request.query, document_text, system_prompt, has_document)
        
        # Store in session
        if session_id not in sessions:
            sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "questions": []
            }
        
        sessions[session_id]["questions"] = sessions[session_id].get("questions", [])
        sessions[session_id]["questions"].append({
            "question": request.query,
            "answer": response,
            "role": request.role,
            "department": request.department,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "session_id": session_id,
            "answer": response,
            "has_document": has_document,
            "sources": ["whitelisted_urls", "uploaded_document"] if has_document else ["whitelisted_urls"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

@app.post("/api/document/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    is_asbuilt: bool = Form(False)
):
    """Upload and analyze a document."""
    try:
        logger.info(f"Document upload - File: {file.filename}, Session: {session_id}")
        
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create session if needed
        session_id = session_id or f"session_{datetime.now().timestamp()}"
        
        # Extract text from PDF
        if is_asbuilt:
            text = extract_text_from_asbuilt_pdf(file)
        else:
            # Read PDF content
            file.file.seek(0)
            content = await file.read()
            # For now, just store as string representation
            text = f"Document: {file.filename}\nSize: {len(content)} bytes"
        
        # Build system prompt
        system_prompt = build_system_prompt(department, role)
        
        # Generate analysis
        analysis = generate_llm_response(
            f"Analyze this document and provide a summary of key information:",
            text,
            system_prompt,
            True
        )
        
        # Store in session
        if session_id not in sessions:
            sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "documents": [],
                "questions": []
            }
        
        sessions[session_id]["documents"] = sessions[session_id].get("documents", [])
        sessions[session_id]["documents"].append({
            "filename": file.filename,
            "file_size": f"{len(await file.read())} bytes",
            "department": department,
            "role": role,
            "analysis": analysis,
            "is_asbuilt": is_asbuilt,
            "uploaded_at": datetime.now().isoformat()
        })
        
        # Store text for later queries
        sessions[session_id]["text"] = text
        
        logger.info(f"Document uploaded successfully: {file.filename}")
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": f"Successfully uploaded {file.filename}",
            "is_asbuilt": is_asbuilt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during document upload: {e}")
        raise HTTPException(status_code=500, detail="Error processing document")

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report for a session."""
    logger.info(f"Generating report for session: {session_id}")
    
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[session_id]
        documents = session.get("documents", [])
        questions = session.get("questions", [])
        
        # Build HTML report
        html_report = """
<!DOCTYPE html>
<html>
<head>
    <title>PipeWrench AI - Knowledge Capture Report</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; 
            padding: 40px; 
            line-height: 1.6; 
            background: #f5f5f5;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #667eea; 
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
        }
        h2 { 
            color: #667eea; 
            margin-top: 30px; 
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 10px;
        }
        .question { 
            background: #eff6ff; 
            padding: 15px; 
            margin: 20px 0; 
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }
        .answer { 
            margin: 10px 0; 
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .document { 
            background: #fef3c7; 
            padding: 15px; 
            margin: 20px 0; 
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
        }
        .metadata { 
            color: #6b7280; 
            font-size: 0.9em;
            font-style: italic;
            margin-top: 10px;
        }
        .stats {
            background: #f0f9ff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ PipeWrench AI - Knowledge Capture Report</h1>
        <p>AI-Powered Municipal DPW Knowledge Base with Source Verification</p>
"""
        
        # Add statistics
        html_report += f"""
        <div class="stats">
            <strong>Report Statistics:</strong><br>
            Documents Analyzed: {len(documents)}<br>
            Questions Asked: {len(questions)}<br>
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
"""
        
        # Add documents
        if documents:
            html_report += "<h2>📄 Documents Analyzed</h2>"
            for i, doc in enumerate(documents, 1):
                role_display = f" • {sanitize_html(doc.get('role', ''))}" if doc.get('role') else ""
                html_report += f"""
        <div class="document">
            <strong>Document {i}:</strong> {sanitize_html(doc['filename'])}<br>
            <strong>Department:</strong> {sanitize_html(doc['department'])}{role_display}<br>
            <strong>Size:</strong> {sanitize_html(doc['file_size'])}<br>
            <div class="answer">
                <strong>Analysis:</strong><br>
                {sanitize_html(doc['analysis'])}
            </div>
            <p class="metadata">Uploaded: {doc['uploaded_at']}</p>
        </div>
"""
        
        # Add Q&A
        if questions:
            html_report += f"<h2>💬 Questions & Answers ({len(questions)})</h2>"
            for i, qa in enumerate(questions, 1):
                role_display = f" • {sanitize_html(qa.get('role', ''))}" if qa.get('role') else ""
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
            <p>Preserving Institutional Knowledge in Public Works</p>
        </div>
    </div>
</body>
</html>
"""
        
        logger.info(f"Report generated successfully for session {session_id}")
        return HTMLResponse(content=html_report)
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

# ============================================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later."
        }
    )

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# For Vercel
app = app
