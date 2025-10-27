from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from anthropic import Anthropic
import os
from datetime import datetime
from typing import Optional, List
import uuid

# Import department prompts
from department_prompts import get_department_prompt, get_department_list, get_department_name

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Session storage (in production, use Redis or database)
sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/departments")
async def get_departments():
    """Return list of all departments for dropdown"""
    return {"departments": get_department_list()}

@app.post("/api/session/create")
async def create_session():
    """Create a new session for tracking questions"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": datetime.now(),
        "questions": [],
        "documents": []
    }
    return {"session_id": session_id}

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve session data"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.post("/api/query")
async def query_ai(
    question: str = Form(...),
    department: str = Form("general_public_works"),
    session_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """Query the AI with department-specific context"""
    
    # Use provided API key or environment variable
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    
    # Get department-specific prompt (includes anti-hallucination rules + APA citations)
    system_prompt = get_department_prompt(department)
    
    try:
        # Call Claude with the system prompt
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        
        answer = response.content[0].text
        
        # Store in session if session_id provided
        if session_id and session_id in sessions:
            sessions[session_id]["questions"].append({
                "question": question,
                "answer": answer,
                "department": get_department_name(department),
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
    api_key: Optional[str] = Form(None)
):
    """Upload and analyze a document"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read file content
    content = await file.read()
    
    # Use provided API key or environment variable
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    
    # Get department-specific prompt
    system_prompt = get_department_prompt(department)
    
    try:
        # Analyze document with Claude
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt + "\n\nAnalyze this document and extract key institutional knowledge, procedures, and important information.",
            messages=[{
                "role": "user",
                "content": f"Document: {file.filename}\n\nContent:\n{content.decode('utf-8', errors='ignore')}"
            }]
        )
        
        analysis = response.content[0].text
        
        # Store document in session
        sessions[session_id]["documents"].append({
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department),
            "uploaded_at": datetime.now().isoformat()
        })
        
        return {
            "filename": file.filename,
            "analysis": analysis,
            "department": get_department_name(department)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    """Generate HTML report with all questions and documents"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    # Generate HTML report
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
            .answer {{ margin: 10px 0; }}
            .document {{ background: #fef3c7; padding: 15px; margin: 20px 0; border-left: 4px solid #f59e0b; }}
            .metadata {{ color: #6b7280; font-size: 0.9em; }}
            .references {{ background: #f3f4f6; padding: 10px; margin-top: 10px; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>PipeWrench AI - Knowledge Capture Report</h1>
        <p class="metadata">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Questions & Answers ({len(session_data['questions'])})</h2>
    """
    
    for i, qa in enumerate(session_data['questions'], 1):
        html_report += f"""
        <div class="question">
            <strong>Q{i} ({qa['department']}):</strong> {qa['question']}
            <div class="answer">
                <strong>Answer:</strong><br>
                {qa['answer'].replace(chr(10), '<br>')}
            </div>
            <p class="metadata">Asked: {qa['timestamp']}</p>
        </div>
        """
    
    html_report += f"""
        <h2>Documents Analyzed ({len(session_data['documents'])})</h2>
    """
    
    for doc in session_data['documents']:
        html_report += f"""
        <div class="document">
            <strong>Document:</strong> {doc['filename']} ({doc['department']})<br>
            <div class="answer">
                <strong>Analysis:</strong><br>
                {doc['analysis'].replace(chr(10), '<br>')}
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
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
