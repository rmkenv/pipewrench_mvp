from fastapi import FastAPI, Form
from pydantic import BaseModel
from typing import Optional
import anthropic

app = FastAPI(title="PipeWrench Simple API", version="1.0")

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

from fastapi.responses import HTMLResponse

@app.get("/")
async def root():
    """
    Simple UI instructions when visiting the root path
    """
    return {
        "message": "PipeWrench AI Wrapper is running!",
        "instructions": {
            "POST /query": "Send JSON with api_key and question",
            "POST /ask": "Send form data if testing in browser",
            "GET /form": "Fill out a simple form and submit your question"
        },
    }

@app.get("/form", response_class=HTMLResponse)
def simple_form():
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
