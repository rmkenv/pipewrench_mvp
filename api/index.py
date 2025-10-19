from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import anthropic
import PyPDF2
import docx
import io

app = FastAPI(title="PipeWrench Simple API", version="1.0")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# Data model for structured POST requests
class QueryRequest(BaseModel):
    api_key: str
    question: str
    model: Optional[str] = "claude-3-5-sonnet-20241022"

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

@app.post("/query")
async def query_anthropic(data: QueryRequest):
    """
    Main endpoint — user provides their Anthropic key and prompt.
    """
    try:
        client = anthropic.Anthropic(api_key=data.api_key)
        response = client.messages.create(
            model=data.model,
            max_tokens=600,
            messages=[
                {"role": "system", "content": CUSTOM_INSTRUCTIONS},
                {"role": "user", "content": data.question},
            ],
        )
        return {"success": True, "response": response.content[0].text}

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/analyze-document")
async def analyze_document(
    api_key: str = Form(...),
    file: UploadFile = File(...),
    analysis_type: str = Form("generate_questions"),
    model: str = Form("claude-3-5-sonnet-20241022")
):
    """
    Analyze uploaded documents (job descriptions, SOPs, BMPs) and generate questions or insights
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
            messages=[
                {"role": "system", "content": CUSTOM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "analysis_type": analysis_type,
            "response": response.content[0].text
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

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
            messages=[
                {"role": "system", "content": CUSTOM_INSTRUCTIONS},
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
