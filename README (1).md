# PipeWrench AI — Municipal DPW Knowledge Capture (FastAPI)

PipeWrench AI is a FastAPI application for municipal Department of Public Works (DPW) knowledge capture and retrieval. It enforces strict source verification via a URL whitelist and supports department- and role-specific guidance.

This repository is configured for deployment on Render and local development with Uvicorn.

## Features

- FastAPI backend with CORS enabled
- Department-specific prompts and job-role context
- Strict citation compliance:
  - Only cite from approved whitelisted sources
  - Include specific URLs for each citation
  - Clearly state when info cannot be verified from approved sources
- PDF upload endpoint with stubbed text extraction (swap in your own)
- Optional “as-built” PDF processing via an external service (`DRAWING_PROCESSING_API_URL`)
- Simple in-memory session tracking
- HTML report generation for captured Q&A
- Render blueprint (`render.yaml`) for one-click deployment

## Repository Structure

- `app_combined.py` — Main FastAPI app (single-file combined)
- `render.yaml` — Render blueprint (infra-as-code)
- `.render-build.sh` — Build script for Render (installs dependencies)
- `requirements.txt` — Pinned Python dependencies
- `.env.example` — Example environment variables
- `custom_whitelist.json` — Optional custom URL whitelist entries (default: empty array)
- `scripts/`
  - `dev_run.sh` — Local dev server helper
  - `format_check.sh` — Placeholder for lint/format
- `tests/`
  - `test_api_endpoints.py` — Minimal smoke test

## Environment Variables

- `ANTHROPIC_API_KEY` — Required to call the Anthropic API for LLM answers
- `DRAWING_PROCESSING_API_URL` — Optional; external service to parse “as-built” PDFs (default: `http://localhost:8001/parse`)

For local development, copy `.env.example` to `.env` and fill in values.

## Local Development

1. Python 3.11.x recommended.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scriptsctivate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Set environment variables:
   ```bash
   cp .env.example .env
   # edit .env and add your ANTHROPIC_API_KEY
   ```
4. Run the server:
   ```bash
   # Option A: helper script
   ./scripts/dev_run.sh

   # Option B: directly
   uvicorn app_combined:app --reload --host 0.0.0.0 --port 8000
   ```
5. Open http://localhost:8000 and check the root status response.
6. Interactive API docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Overview

- GET `/` — Health/status
- GET `/api/departments` — List available departments
- GET `/api/roles` — List available job roles
- GET `/api/system` — System metadata (whitelist size, roles, departments)
- GET `/api/whitelist` — Whitelist overview (domains, sample URLs)
- POST `/upload` — Upload a PDF
  - Form fields: `file` (PDF), `is_asbuilt` (bool), `session_id` (optional), `department` (optional), `role` (optional)
- POST `/query` — Ask a question
  - JSON body: `{ "query": "...", "session_id": "optional", "department": "optional", "role": "optional" }`
- POST `/api/document/upload` — Alternate PDF upload (multipart)
  - Form fields: `file`, `session_id`, `department` (optional), `role` (optional)
- POST `/api/report/generate` — HTML summary report
  - Form fields: `session_id`

Note: The PDF extraction is stubbed (`extract_text_from_pdf`). Replace with your real parser as needed.

## Whitelist and Compliance

- Base whitelist is embedded in the app.
- You can extend with `custom_whitelist.json` (array of objects like `{ "url": "...", "include_children": true, "description": "..." }`).
- The app checks outbound citations in generated answers and appends a compliance notice if any URLs are not whitelisted.

If you want `custom_whitelist.json` to be environment-specific, keep it in `.gitignore` (default). If you want shared defaults across deployments, commit it and manage via Git.

## Deploy on Render

This repo includes `render.yaml` for one-click deploys (Render “Blueprint”):

1. Push this repository to GitHub.
2. In Render: New + → Blueprint → Select your repo.
3. Use this render.yaml (headers removed; supported for web services):
   ```yaml
   services:
     - type: web
       name: pipewrench-ai
       env: python
       plan: free
       region: oregon
       buildCommand: ./.render-build.sh
       startCommand: uvicorn app_combined:app --host 0.0.0.0 --port $PORT
       autoDeploy: true
       healthCheckPath: /
       envVars:
         - key: ANTHROPIC_API_KEY
           sync: false
         - key: DRAWING_PROCESSING_API_URL
           value: http://localhost:8001/parse
         - key: PYTHON_VERSION
           value: 3.11.9
   ```
4. Add environment variables (Service → Environment):
   - `ANTHROPIC_API_KEY` (required)
   - Optionally adjust `DRAWING_PROCESSING_API_URL`
5. Deploy. Health check path `/` returns `{ "status": "running" }`.

Alternatively, create a “Web Service” manually with the same build/start commands.

## Testing

Quick smoke test (requires server running locally):
```bash
python -m pytest -q
```

The test suite uses `requests` to verify the root endpoint returns status and 200 OK. You can add more tests for other endpoints.

## Updating/Extending

- Remove Vercel-specific code if present (e.g., `from vercel_fastapi import VercelFastAPI` and `handler = VercelFastAPI(app)`) — not needed on Render.
- Replace the PDF extraction stub with a real parser (Textract, PyPDF, etc.).
- Connect a persistent store if you want sessions to survive restarts (Redis/Postgres).
- Add role/department configs as needed — the app already supports them.

## Troubleshooting

- Startup fails on Render:
  - Ensure `PYTHON_VERSION` is set (render.yaml sets 3.11.9).
  - Verify `ANTHROPIC_API_KEY` is present in Render env vars.
  - Check logs for missing dependencies; confirm `pip install -r requirements.txt` ran in build logs.
- Requests to `/query` fail with “Anthropic client not configured”:
  - Set `ANTHROPIC_API_KEY` in your environment or use the mock path without uploading a document.
- CORS issues in browser:
  - CORS is wide open by default here; adjust in `app.add_middleware(CORSMiddleware, ...)` if you need tighter control.

## License

Proprietary — internal use for municipal DPW knowledge capture unless otherwise specified.
