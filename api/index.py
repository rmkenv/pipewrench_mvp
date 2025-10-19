from fastapi import FastAPI, Form
from pydantic import BaseModel
from typing import Optional
import anthropic

app = FastAPI(title="PipeWrench Simple API", version="1.0")

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
                {"role": "user", "content": data.question}
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
            messages=[{"role": "user", "content": question}],
        )
        return {"answer": resp.content[0].text}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    """
    Simple UI instructions when visiting the root path
    """
    return {
        "message": "PipeWrench AI Wrapper is running!",
        "instructions": {
            "POST /query": "Send JSON with api_key and question",
            "POST /ask": "Send form data if testing in browser"
        },
    }

@app.get("/form")
def web_form():
    return """
    <html>
    <body>
      <form action="/ask" method="post">
        <input type="text" name="api_key" placeholder="Your Anthropic API Key" style="width:300px;"><br>
        <textarea name="question" placeholder="Ask Claude..." rows="4" cols="50"></textarea><br>
        <button type="submit">Send</button>
      </form>
    </body>
    </html>
    """
