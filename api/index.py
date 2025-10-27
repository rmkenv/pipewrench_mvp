from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import anthropic
import PyPDF2
import docx
import io
import uuid
from datetime import datetime
from collections import defaultdict
import json

app = FastAPI(title="PipeWrench Simple API", version="1.0")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory session storage (use Redis or database for production)
sessions: Dict[str, Dict] = defaultdict(lambda: {
    "questions": [],
    "documents": [],
    "created_at": datetime.now().isoformat(),
    "metadata": {}
})

# Comprehensive custom instructions for engineering and public works knowledge capture
CUSTOM_INSTRUCTIONS = """
You are PipeWrench AI, an institutional knowledge preservation expert specialized in engineering and public works departments in local government.

Your task is to assist in capturing and formalizing knowledge from retiring employees by:
- Reviewing their job description and work history
- Asking targeted questions based on best practices, SOPs, regulatory compliance, maintenance, commissioning, and project management
- Extracting and rewriting their answers into clear, structured documentation

Ensure you reference:
- Relevant industry standards (ASCE, AWWA, ASTM)
- Federal and state regulatory requirements (EPA, OSHA, ADA)
- Preventive maintenance and commissioning best practices
- Risk mitigation and quality assurance protocols

Structure your responses as usable training material or SOP drafts, emphasizing clarity, completeness, and adherence to professional norms.

If certain information is missing or unclear, generate questions that will elicit it from the employee.
"""

# Data models
class QueryRequest(BaseModel):
    api_key: str
    question: str
    model: Optional[str] = "claude-3-5-sonnet-20241022"
    session_id: Optional[str] = None

class SessionMetadata(BaseModel):
    employee_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    retirement_date: Optional[str] = None

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from uploaded files (PDF, DOCX, TXT)
    """
    try:
        if filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif filename.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        elif filename.endswith('.txt'):
            return file_content.decode('utf-8')
        else:
            return None
    except Exception as e:
        raise Exception(f"Error extracting text from file: {str(e)}")

def generate_html_report(session_id: str) -> str:
    """
    Generate an HTML report with all Q&A and document appendices
    """
    session = sessions.get(session_id)
    if not session:
        return "<html><body><h1>Session not found</h1></body></html>"
    
    metadata = session.get("metadata", {})
    questions = session.get("questions", [])
    documents = session.get("documents", [])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Knowledge Transfer Report - {metadata.get('employee_name', 'Unknown')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: #1e40af;
                color: white;
                padding: 30px;
                border-radius: 8px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
            }}
            .metadata {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metadata-item {{
                padding: 10px;
                border-left: 3px solid #f97316;
            }}
            .metadata-label {{
                font-weight: bold;
                color: #1e40af;
                font-size: 0.9em;
                text-transform: uppercase;
            }}
            .section {{
                background: white;
                padding: 30px;
                margin-bottom: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #1e40af;
                border-bottom: 3px solid #f97316;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .qa-item {{
                margin-bottom: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #1e40af;
            }}
            .question {{
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 10px;
                font-size: 1.1em;
            }}
            .answer {{
                color: #333;
                white-space: pre-wrap;
                line-height: 1.8;
            }}
            .timestamp {{
                color: #666;
                font-size: 0.85em;
                margin-top: 10px;
                font-style: italic;
            }}
            .document {{
                margin-bottom: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #f97316;
            }}
            .document h3 {{
                color: #f97316;
                margin-bottom: 15px;
            }}
            .document-content {{
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                color: #333;
                max-height: 500px;
                overflow-y: auto;
                background: white;
                padding: 15px;
                border-radius: 4px;
            }}
            .footer {{
                text-align: center;
                color: #666;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 2px solid #ddd;
            }}
            @media print {{
                body {{
                    background: white;
                }}
                .section, .metadata {{
                    box-shadow: none;
                    page-break-inside: avoid;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔧 Knowledge Transfer Report</h1>
            <p>PipeWrench AI - Institutional Knowledge Preservation</p>
        </div>
        
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Employee Name</div>
                <div>{metadata.get('employee_name', 'Not specified')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Department</div>
                <div>{metadata.get('department', 'Not specified')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Position</div>
                <div>{metadata.get('position', 'Not specified')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Retirement Date</div>
                <div>{metadata.get('retirement_date', 'Not specified')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Session ID</div>
                <div>{session_id}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Report Generated</div>
                <div>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Questions & Answers</h2>
            <p><strong>Total Interactions:</strong> {len(questions)}</p>
    """
    
    if questions:
        for idx, qa in enumerate(questions, 1):
            html += f"""
            <div class="qa-item">
                <div class="question">Q{idx}: {qa.get('question', '')}</div>
                <div class="answer">{qa.get('answer', '')}</div>
                <div class="timestamp">Timestamp: {qa.get('timestamp', '')}</div>
            </div>
            """
    else:
        html += "<p><em>No questions recorded in this session.</em></p>"
    
    html += "</div>"
    
    # Appendix - Documents
    if documents:
        html += """
        <div class="section">
            <h2>📎 Appendix - Source Documents</h2>
        """
        for idx, doc in enumerate(documents, 1):
            html += f"""
            <div class="document">
                <h3>Document {idx}: {doc.get('filename', 'Unknown')}</h3>
                <p><strong>Uploaded:</strong> {doc.get('timestamp', '')}</p>
                <p><strong>Analysis Type:</strong> {doc.get('analysis_type', 'N/A')}</p>
                <div class="document-content">{doc.get('content', '')[:5000]}{'...' if len(doc.get('content', '')) > 5000 else ''}</div>
            </div>
            """
        html += "</div>"
    
    html += """
        <div class="footer">
            <p>Generated by PipeWrench AI - Knowledge Preservation Platform</p>
            <p>© 2025 PipeWrench AI. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html

@app.post("/session/create")
async def create_session(metadata: SessionMetadata):
    """
    Create a new session for knowledge capture
    """
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "questions": [],
        "documents": [],
        "created_at": datetime.now().isoformat(),
        "metadata": metadata.dict()
    }
    return {"success": True, "session_id": session_id}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Retrieve session data
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session": sessions[session_id]}

@app.post("/query")
async def query_anthropic(data: QueryRequest):
    """
    Main endpoint — user provides their Anthropic key and prompt.
    Caches Q&A in session if session_id provided.
    """
    try:
        client = anthropic.Anthropic(api_key=data.api_key)
        response = client.messages.create(
            model=data.model,
            max_tokens=600,
            system=CUSTOM_INSTRUCTIONS,
            messages=[
                {"role": "user", "content": data.question},
            ],
        )
        
        answer = response.content[0].text
        
        # Cache in session if session_id provided
        if data.session_id and data.session_id in sessions:
            sessions[data.session_id]["questions"].append({
                "question": data.question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "model": data.model
            })
        
        return {"success": True, "response": answer, "session_id": data.session_id}

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/analyze-document")
async def analyze_document(
    api_key: str = Form(...),
    file: UploadFile = File(...),
    analysis_type: str = Form("generate_questions"),
    model: str = Form("claude-3-5-sonnet-20241022"),
    session_id: Optional[str] = Form(None)
):
    """
    Analyze uploaded documents and cache them in session
    """
    try:
        # Read and extract text from file
        file_content = await file.read()
        extracted_text = extract_text_from_file(file_content, file.filename)
        
        if not extracted_text:
            return {"success": False, "error": "Unsupported file format. Please upload PDF, DOCX, or TXT files."}
        
        # Create prompt based on analysis type
        if analysis_type == "generate_questions":
            prompt = f"""Based on the following document, generate 10-15 targeted questions that would help capture critical institutional knowledge from the employee. Focus on:
- Undocumented procedures and workarounds
- Decision-making criteria and judgment calls
- Common problems and their solutions
- Relationships with vendors, contractors, and other departments
- Regulatory compliance nuances
- Safety considerations

Document content:
{extracted_text}

Generate specific, actionable questions that will elicit detailed responses."""
        
        elif analysis_type == "identify_gaps":
            prompt = f"""Review this document and identify knowledge gaps, missing information, or areas that need more detail for proper knowledge transfer. Focus on:
- Missing procedural steps
- Unclear responsibilities
- Undocumented decision criteria
- Missing regulatory references
- Incomplete maintenance schedules

Document content:
{extracted_text}

Provide a structured analysis of gaps and recommendations."""
        
        elif analysis_type == "create_sop":
            prompt = f"""Based on this document, create a draft Standard Operating Procedure (SOP) that includes:
- Purpose and scope
- Responsibilities
- Required materials/equipment
- Step-by-step procedures
- Safety considerations
- Quality control checkpoints
- Regulatory compliance notes

Document content:
{extracted_text}

Create a comprehensive, well-structured SOP draft."""
        
        else:
            prompt = f"""Analyze this document and provide insights for knowledge capture:\n\n{extracted_text}"""
        
        # Call Anthropic API
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=CUSTOM_INSTRUCTIONS,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        
        answer = response.content[0].text
        
        # Cache document and analysis in session
        if session_id and session_id in sessions:
            sessions[session_id]["documents"].append({
                "filename": file.filename,
                "content": extracted_text,
                "analysis_type": analysis_type,
                "analysis_result": answer,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "success": True,
            "filename": file.filename,
            "analysis_type": analysis_type,
            "response": answer,
            "session_id": session_id
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/report/{session_id}")
async def generate_report(session_id: str):
    """
    Generate and download HTML report for a session
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    html_content = generate_html_report(session_id)
    
    return StreamingResponse(
        io.BytesIO(html_content.encode('utf-8')),
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename=knowledge_transfer_report_{session_id[:8]}.html"
        }
    )

@app.get("/report/{session_id}/json")
async def get_report_json(session_id: str):
    """
    Get session data as JSON
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "session_id": session_id,
        "data": sessions[session_id]
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session
    """
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/ask")
async def ask_from_form(api_key: str = Form(...), question: str = Form(...)):
    """
    Simple web form support (handy for local or browser requests)
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            system=CUSTOM_INSTRUCTIONS,
            messages=[
                {"role": "user", "content": question},
            ],
        )
        return {"answer": resp.content[0].text}
    except Exception as e:
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Serve the main GUI
    """
    return FileResponse("static/index.html")

@app.get("/form", response_class=HTMLResponse)
def simple_form():
    """
    Legacy simple form endpoint
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PipeWrench AI Query</title>
    </head>
    <body>
        <h1>Ask PipeWrench AI (Anthropic Claude)</h1>
        <form action="/ask" method="post">
            <label for="api_key">Your Anthropic API Key:</label><br>
            <input type="text" id="api_key" name="api_key" style="width:300px;" required><br><br>

            <label for="question">Your Question:</label><br>
            <textarea id="question" name="question" rows="4" cols="50" placeholder="Type your question here..." required></textarea><br><br>

            <button type="submit">Ask</button>
        </form>
    </body>
    </html>
    """
