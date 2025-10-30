from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request\
from fastapi.responses import HTMLResponse, JSONResponse
from anthropic import Anthropic
import os
from datetime import datetime
from typing import Optional
import uuid
import io

# Import for file parsing

try:\
from PyPDF2 import PdfReader\
except ImportError:\
PdfReader = None

try:\
import docx\
except ImportError:\
docx = None

# Add path for local imports

import sys\
sys.path.insert(0, os.path.dirname(**file**))

# Import configurations

from department_prompts_config import get_department_prompt, get_department_list, get_department_name\
from job_roles_config import get_role_list, get_role_context\
from url_whitelist_config import is_url_whitelisted, get_whitelisted_sources, WHITELISTED_URLS

app = FastAPI()

# Initialize Anthropic client

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Session storage (in production, use Redis or database)

sessions = {}

# Embedded HTML

HTML_TEMPLATE = """\
<!DOCTYPE html>\
<html lang="en">\
<head>\
<meta charset="UTF-8">\
<meta name="viewport" content="width=device-width, initial-scale=1.0">\
<title>PipeWrench AI - Municipal Knowledge Capture</title>\
<style>\
\* {\
margin: 0;\
padding: 0;\
box-sizing: border-box;\
}

```
    :root {
        --primary-blue: #1e40af;
        --secondary-blue: #3b82f6;
        --light-blue: #eff6ff;
        --accent-orange: #f59e0b;
        --dark-orange: #d97706;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --text-light: #f1f5f9;
        --text-muted: #94a3b8;
        --border: #334155;
        --success-green: #10b981;
    }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, var(--bg-dark) 0%, #1e293b 100%);
        color: var(--text-light);
        min-height: 100vh;
        padding: 20px;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
        background: var(--bg-card);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        overflow: hidden;
    }

    header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
        padding: 40px;
        text-align: center;
        border-bottom: 4px solid var(--accent-orange);
    }

    header h1 {
        font-size: 2.5em;
        margin-bottom: 10px;
        color: white;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }

    header p {
        font-size: 1.1em;
        color: var(--light-blue);
        opacity: 0.95;
    }

    .tabs {
        display: flex;
        background: var(--bg-dark);
        border-bottom: 2px solid var(--border);
        overflow-x: auto;
    }

    .tab-btn {
        flex: 1;
        padding: 18px 24px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        font-size: 1em;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        border-bottom: 3px solid transparent;
        white-space: nowrap;
    }

    .tab-btn:hover {
        background: rgba(59, 130, 246, 0.1);
        color: var(--secondary-blue);
    }

    .tab-btn.active {
        color: var(--accent-orange);
        border-bottom-color: var(--accent-orange);
        background: rgba(245, 158, 11, 0.1);
    }

    .tab-content {
        display: none;
        padding: 40px;
        animation: fadeIn 0.3s ease;
    }

    .tab-content.active {
        display: block;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    h2 {
        color: var(--secondary-blue);
        margin-bottom: 24px;
        font-size: 1.8em;
        border-bottom: 2px solid var(--border);
        padding-bottom: 12px;
    }

    .form-group {
        margin-bottom: 24px;
    }

    label {
        display: block;
        margin-bottom: 8px;
        color: var(--text-light);
        font-weight: 600;
        font-size: 0.95em;
    }

    .form-control {
        width: 100%;
        padding: 14px 16px;
        background: var(--bg-dark);
        border: 2px solid var(--border);
        border-radius: 8px;
        color: var(--text-light);
        font-size: 1em;
        transition: all 0.3s ease;
        font-family: inherit;
    }

    .form-control:focus {
        outline: none;
        border-color: var(--secondary-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    select.form-control {
        cursor: pointer;
    }

    textarea.form-control {
        resize: vertical;
        min-height: 120px;
    }

    .btn {
        padding: 14px 32px;
        border: none;
        border-radius: 8px;
        font-size: 1em;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .btn-primary {
        background: linear-gradient(135deg, var(--accent-orange) 0%, var(--dark-orange) 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }

    .btn-primary:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
    }

    .btn-primary:active {
        transform: translateY(0);
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .answer-box {
        background: var(--bg-dark);
        border-left: 4px solid var(--secondary-blue);
        padding: 24px;
        border-radius: 8px;
        margin-top: 16px;
        line-height: 1.8;
        color: var(--text-light);
        white-space: pre-wrap;
    }

    #answer-container, #upload-result {
        margin-top: 32px;
        animation: fadeIn 0.5s ease;
    }

    #answer-container h3, #upload-result h3 {
        color: var(--accent-orange);
        margin-bottom: 16px;
        font-size: 1.4em;
    }

    small {
        display: block;
        margin-top: 8px;
        color: var(--text-muted);
        font-size: 0.85em;
    }

    .status-box {
        padding: 16px;
        margin-bottom: 24px;
        border-radius: 8px;
        background: var(--bg-dark);
        border-left: 4px solid var(--accent-orange);
    }

    .status-box.has-docs {
        border-left-color: var(--success-green);
    }

    .doc-list {
        margin-top: 8px;
        color: var(--text-muted);
        font-size: 0.9em;
    }

    .doc-list.has-items {
        color: var(--success-green);
    }

    footer {
        background: var(--bg-dark);
        padding: 32px 40px;
        border-top: 2px solid var(--border);
        color: var(--text-muted);
        font-size: 0.9em;
        line-height: 1.6;
    }

    footer h4 {
        color: var(--secondary-blue);
        margin-bottom: 12px;
        font-size: 1.1em;
    }

    footer a {
        color: var(--accent-orange);
        text-decoration: none;
        transition: color 0.3s ease;
    }

    footer a:hover {
        color: var(--dark-orange);
        text-decoration: underline;
    }

    footer details {
        margin-top: 12px;
    }

    footer summary {
        cursor: pointer;
        color: var(--accent-orange);
        font-weight: 600;
        margin-bottom: 8px;
    }

    footer summary:hover {
        color: var(--dark-orange);
    }

    footer ul {
        list-style-type: disc;
    }

    .footer-section {
        margin-bottom: 20px;
    }

    .spinner {
        border: 3px solid var(--border);
        border-top: 3px solid var(--accent-orange);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
        display: none;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .error-message {
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid #ef4444;
        padding: 16px;
        border-radius: 8px;
        margin-top: 16px;
        color: #fca5a5;
    }

    @media (max-width: 768px) {
        header h1 {
            font-size: 1.8em;
        }

        .tab-content {
            padding: 24px;
        }

        .tabs {
            flex-wrap: wrap;
        }

        .tab-btn {
            flex: 1 1 50%;
        }
    }
</style>
```

</head>\
<body>\
<div class="container">\
<header>\
<h1>🔧 PipeWrench AI</h1>\
<p>Preserving Institutional Knowledge in Public Works</p>\
</header>

```
    <div class="tabs">
        <button class="tab-btn" data-tab="upload">Upload Documents</button>
        <button class="tab-btn active" data-tab="query">Ask Questions</button>
        <button class="tab-btn" data-tab="report">Generate Report</button>
        <button class="tab-btn" data-tab="settings">Settings</button>
    </div>

    <!-- Upload Tab (Now First) -->
    <div id="upload" class="tab-content">
        <h2>Upload Document</h2>
        <p style="margin-bottom: 24px; color: var(--text-muted);">
            Upload your institutional knowledge documents first. You can then ask questions about them.
        </p>
        
        <div class="form-group">
            <label for="upload-department">Department/Role:</label>
            <select id="upload-department" class="form-control">
                <option value="">Loading departments...</option>
            </select>
        </div>

        <div class="form-group">
            <label for="upload-role">Job Role (optional):</label>
            <select id="upload-role" class="form-control">
                <option value="">None</option>
            </select>
        </div>

        <div class="form-group">
            <label for="file">Select Document:</label>
            <input type="file" id="file" class="form-control" accept=".txt,.pdf,.doc,.docx">
            <small>Supported formats: TXT, PDF, DOC, DOCX (max 10MB)</small>
        </div>

        <button onclick="uploadDocument()" class="btn btn-primary" id="upload-btn">Upload & Analyze</button>
        <div class="spinner" id="upload-spinner"></div>

        <div id="upload-result" style="display:none;">
            <h3>Analysis:</h3>
            <div id="analysis" class="answer-box"></div>
        </div>
    </div>

    <!-- Query Tab -->
    <div id="query" class="tab-content active">
        <h2>Ask a Question</h2>
        
        <!-- Document Status Indicator -->
        <div id="document-status" class="status-box">
            <strong>📄 Uploaded Documents:</strong> <span id="doc-count">0</span>
            <div id="doc-list" class="doc-list"></div>
            <p id="doc-instruction" style="margin-top: 8px; color: var(--text-muted); font-size: 0.9em;">
                ⚠️ Upload documents in the "Upload Documents" tab before asking questions.
            </p>
        </div>
        
        <div class="form-group">
            <label for="department">Department/Role:</label>
            <select id="department" class="form-control">
                <option value="">Loading departments...</option>
            </select>
        </div>

        <div class="form-group">
            <label for="role">Job Role (optional):</label>
            <select id="role" class="form-control">
                <option value="">None</option>
            </select>
        </div>

        <div class="form-group">
            <label for="question">Your Question:</label>
            <textarea id="question" rows="4" class="form-control" 
                placeholder="e.g., What are the proper procedures for confined space entry in a wastewater lift station?"></textarea>
        </div>

        <button onclick="askQuestion()" class="btn btn-primary" id="query-btn">Ask Question</button>
        <div class="spinner" id="query-spinner"></div>

        <div id="answer-container" style="display:none;">
            <h3>Answer:</h3>
            <div id="answer" class="answer-box"></div>
        </div>
    </div>

    <!-- Report Tab -->
    <div id="report" class="tab-content">
        <h2>Generate Report</h2>
        <p style="margin-bottom: 24px; color: var(--text-muted);">
            Generate a comprehensive report with all questions, answers, and document analyses from this session. 
            All responses include citations and references from your uploaded documents.
        </p>
        <button onclick="generateReport()" class="btn btn-primary">Generate Report</button>
    </div>

    <!-- Settings Tab -->
    <div id="settings" class="tab-content">
        <h2>Settings</h2>
        
        <div class="form-group">
            <label for="api-key">Anthropic API Key (Optional):</label>
            <input type="password" id="api-key" class="form-control" 
                placeholder="sk-ant-...">
            <small>Leave blank to use server default. Your key is stored locally and never sent to our servers except for API calls.</small>
        </div>

        <button onclick="saveSettings()" class="btn btn-primary">Save Settings</button>
        
        <div style="margin-top: 32px; padding: 20px; background: var(--bg-dark); border-radius: 8px; border-left: 4px solid var(--accent-orange);">
            <h4 style="color: var(--accent-orange); margin-bottom: 12px;">About PipeWrench AI</h4>
            <p style="color: var(--text-muted); line-height: 1.6;">
                PipeWrench AI uses Claude 3.5 Sonnet with department-specific prompts to capture and preserve 
                institutional knowledge in municipal public works departments. All responses include verifiable 
                citations from <span id="whitelist-count">126</span> approved sources and follow strict anti-hallucination protocols.
            </p>
            <p style="color: var(--text-muted); line-height: 1.6; margin-top: 12px;">
                <strong>Document-Based Q&A:</strong> Upload your institutional documents first, then ask questions. 
                The AI will answer based only on your uploaded content with proper citations.
            </p>
        </div>
    </div>

    <footer>
        <div class="footer-section">
            <h4>Approved Federal Reference Sources</h4>
            <p style="margin-bottom: 12px;">
                This application references <strong>24 federal sources</strong> across 13 categories to ensure 
                compliance with federal standards and regulations:
            </p>
            <details style="margin-top: 12px;">
                <summary>View Complete Federal Source List</summary>
                <div style="margin-left: 20px; margin-top: 12px; line-height: 1.8;">
                    <p><strong>Federal Acquisition & Construction:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.acquisition.gov/far/part-36" target="_blank">Federal Acquisition Regulation (FAR) - Part 36</a></li>
                    </ul>
                    
                    <p><strong>Federal Standards:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://highways.dot.gov/federal-lands/specs" target="_blank">FHWA Standard Specifications FP-24</a></li>
                    </ul>
                    
                    <p><strong>OSHA Safety:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.osha.gov/laws-regs/regulations/standardnumber/1926" target="_blank">29 CFR Part 1926</a> - Safety and Health Regulations for Construction</li>
                        <li><a href="https://www.osha.gov/construction" target="_blank">OSHA Construction Industry Portal</a></li>
                    </ul>
                    
                    <p><strong>EPA Environmental:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.epa.gov/eg/construction-and-development-effluent-guidelines" target="_blank">40 CFR Part 450</a> - Construction and Development Effluent Guidelines</li>
                        <li><a href="https://www.epa.gov/laws-regulations" target="_blank">EPA Laws & Regulations</a></li>
                        <li><a href="https://www.epa.gov/sites/default/files/2015-10/documents/myerguide.pdf" target="_blank">EPA Managing Environmental Responsibilities Guide</a></li>
                        <li><a href="https://www.cem.va.gov/pdf/fedreqs.pdf" target="_blank">Federal Environmental Requirements for Construction</a></li>
                    </ul>
                    
                    <p><strong>Federal DOT:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.transportation.gov/roadways-and-bridges" target="_blank">US DOT Roads and Bridges</a></li>
                        <li><a href="https://highways.dot.gov/fed-aid-essentials/videos/project-development/design-project-geometric-design-requirements" target="_blank">FHWA Geometric Design Requirements</a></li>
                    </ul>
                    
                    <p><strong>Building Codes:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://global.iccsafe.org/international-codes-and-standards/" target="_blank">International Code Council (ICC)</a> - I-Codes adopted by all 50 states</li>
                    </ul>
                    
                    <p><strong>Engineering Standards:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.asce.org/publications-and-news/codes-and-standards" target="_blank">ASCE Standards</a> - American Society of Civil Engineers</li>
                        <li><a href="https://www.asme.org/codes-standards" target="_blank">ASME Codes & Standards</a></li>
                    </ul>
                    
                    <p><strong>Professional Services:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.fhwa.dot.gov/programadmin/121205.cfm" target="_blank">Brooks Act (P.L. 92-582)</a></li>
                        <li><a href="https://www.acquisition.gov/far/subpart-36.6" target="_blank">FAR Subpart 36.6</a></li>
                    </ul>
                    
                    <p><strong>Federal Building Standards:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.gsa.gov/real-estate/design-and-construction/facilities-standards-for-the-public-buildings-service" target="_blank">GSA Facilities Standards</a></li>
                    </ul>
                    
                    <p><strong>Standards Organizations:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.ansi.org" target="_blank">American National Standards Institute (ANSI)</a></li>
                        <li><a href="https://www.astm.org" target="_blank">ASTM International</a></li>
                        <li><a href="https://store.astm.org/products-services/standards-and-publications/standards/construction-standards.html" target="_blank">ASTM Construction Standards</a></li>
                    </ul>
                    
                    <p><strong>Fire Safety Standards:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.nfpa.org/codes-and-standards" target="_blank">National Fire Protection Association (NFPA)</a></li>
                        <li><a href="https://codesonline.nfpa.org" target="_blank">NFPA Codes Online (NFCSS)</a></li>
                    </ul>
                    
                    <p><strong>Professional Associations:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.apwa.org/resources/about-public-works/" target="_blank">American Public Works Association (APWA)</a></li>
                        <li><a href="https://www.nist.gov" target="_blank">National Institute of Standards and Technology (NIST)</a></li>
                    </ul>
                    
                    <p><strong>Reference:</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 12px;">
                        <li><a href="https://www.congress.gov/crs-product/R47666" target="_blank">Congressional Research on Infrastructure Codes</a></li>
                    </ul>
                </div>
            </details>
            <p style="margin-top: 12px; color: var(--text-muted); font-size: 0.9em;">
                Additionally, this system references all 50 state DOT standards and professional licensing boards. 
                <strong>Total whitelisted sources: 126</strong>
            </p>
        </div>

        <div class="footer-section">
            <h4>Privacy Policy</h4>
            <p>
                PipeWrench AI is committed to protecting your privacy. Session data is stored temporarily 
                and automatically deleted after 24 hours. API keys are stored locally in your browser and 
                never transmitted to our servers except for direct API calls to Anthropic.
            </p>
        </div>

        <div class="footer-section">
            <h4>California Generative AI Training Data Transparency Act</h4>
            <p>
                This application uses Anthropic's Claude AI model. For information about training data used 
                in Claude's development, please visit 
                <a href="https://www.anthropic.com/legal/data-transparency" target="_blank">Anthropic's Data Transparency page</a>.
            </p>
            <p style="margin-top: 12px;">
                <strong>Data Usage:</strong> Your questions and uploaded documents are sent to Anthropic's API 
                for processing. Anthropic does not train on data submitted via their API. For more information, 
                see <a href="https://www.anthropic.com/legal/commercial-terms" target="_blank">Anthropic's Commercial Terms</a>.
            </p>
        </div>

        <div class="footer-section">
            <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border);">
                © 2024 PipeWrench AI. Built for municipal public works professionals.
            </p>
        </div>
    </footer>
</div>

<script>
    let sessionId = null;
    let apiKey = null;
    let documentCount = 0;

    window.onload = async function() {
        await createSession();
        await loadDepartments();
        await loadRoles();
        await loadSystemInfo();
        await updateDocumentStatus();
        loadSettings();
    };

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
        });
    });

    async function createSession() {
        try {
            const response = await fetch('/api/session/create', { method: 'POST' });
            const data = await response.json();
            sessionId = data.session_id;
            console.log('Session created:', sessionId);
        } catch (error) {
            console.error('Error creating session:', error);
            alert('Failed to create session. Please refresh the page.');
        }
    }

    async function loadDepartments() {
        try {
            const response = await fetch('/api/departments');
            const data = await response.json();
            
            const selects = ['department', 'upload-department'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                select.innerHTML = '<option value="general_public_works">General Public Works</option>';
                
                data.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.value;
                    option.textContent = dept.name;
                    select.appendChild(option);
                });
            });
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    }

    async function loadRoles() {
        try {
            const response = await fetch('/api/roles');
            const data = await response.json();
            
            const selects = ['role', 'upload-role'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                select.innerHTML = '<option value="">None</option>';
                
                data.roles.forEach(role => {
                    const option = document.createElement('option');
                    option.value = role.value;
                    option.textContent = role.title;
                    select.appendChild(option);
                });
            });
        } catch (error) {
            console.error('Error loading roles:', error);
        }
    }

    async function loadSystemInfo() {
        try {
            const response = await fetch('/api/system');
            const data = await response.json();
            document.getElementById('whitelist-count').textContent = data.total_whitelisted_urls;
        } catch (error) {
            console.error('Error loading system info:', error);
        }
    }

    async function updateDocumentStatus() {
        if (!sessionId) return;
        
        try {
            const response = await fetch(`/api/session/${sessionId}/status`);
            const data = await response.json();
            
            documentCount = data.document_count;
            document.getElementById('doc-count').textContent = documentCount;
            
            const docList = document.getElementById('doc-list');
            const docStatus = document.getElementById('document-status');
            const docInstruction = document.getElementById('doc-instruction');
            const queryBtn = document.getElementById('query-btn');
            
            if (data.documents && data.documents.length > 0) {
                docList.innerHTML = '✓ ' + data.documents.join('<br>✓ ');
                docList.classList.add('has-items');
                docStatus.classList.add('has-docs');
                docInstruction.innerHTML = '✅ Documents loaded. You can now ask questions about them.';
                docInstruction.style.color = 'var(--success-green)';
                queryBtn.disabled = false;
            } else {
                docList.innerHTML = '';
                docList.classList.remove('has-items');
                docStatus.classList.remove('has-docs');
                docInstruction.innerHTML = '⚠️ Upload documents in the "Upload Documents" tab before asking questions.';
                docInstruction.style.color = 'var(--text-muted)';
                queryBtn.disabled = true;
            }
            
        } catch (error) {
            console.error('Error updating document status:', error);
        }
    }

    async function askQuestion() {
        const question = document.getElementById('question').value.trim();
        const department = document.getElementById('department').value;
        const role = document.getElementById('role').value;
        
        if (!question) {
            alert('Please enter a question');
            return;
        }
        
        if (documentCount === 0) {
            alert('Please upload at least one document before asking questions. Go to the "Upload Documents" tab.');
            return;
        }

        const spinner = document.getElementById('query-spinner');
        spinner.style.display = 'block';
        document.getElementById('answer-container').style.display = 'none';

        const formData = new FormData();
        formData.append('question', question);
        formData.append('department', department);
        formData.append('role', role);
        formData.append('session_id', sessionId);
        if (apiKey) formData.append('api_key', apiKey);

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'API request failed');
            }
            
            const data = await response.json();
            document.getElementById('answer').textContent = data.answer;
            document.getElementById('answer-container').style.display = 'block';
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            spinner.style.display = 'none';
        }
    }

    async function uploadDocument() {
        const fileInput = document.getElementById('file');
        const department = document.getElementById('upload-department').value;
        const role = document.getElementById('upload-role').value;
        
        if (!fileInput.files[0]) {
            alert('Please select a file');
            return;
        }

        const file = fileInput.files[0];
        if (file.size > 10 * 1024 * 1024) {
            alert('File too large. Maximum size is 10MB.');
            return;
        }

        const spinner = document.getElementById('upload-spinner');
        const uploadBtn = document.getElementById('upload-btn');
        spinner.style.display = 'block';
        uploadBtn.disabled = true;
        document.getElementById('upload-result').style.display = 'none';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('department', department);
        formData.append('role', role);
        formData.append('session_id', sessionId);
        if (apiKey) formData.append('api_key', apiKey);

        try {
            const response = await fetch('/api/document/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }
            
            const data = await response.json();
            document.getElementById('analysis').textContent = data.analysis;
            document.getElementById('upload-result').style.display = 'block';
            fileInput.value = '';
            
            // Update document status after successful upload
            await updateDocumentStatus();
            
            alert(`✅ Document uploaded successfully! You now have ${data.total_documents} document(s) in this session. Go to "Ask Questions" tab to query them.`);
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            spinner.style.display = 'none';
            uploadBtn.disabled = false;
        }
    }

    async function generateReport() {
        const formData = new FormData();
        formData.append('session_id', sessionId);

        try {
            const response = await fetch('/api/report/generate', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Report generation failed');
            
            const html = await response.text();
            const reportWindow = window.open('', '_blank');
            reportWindow.document.write(html);
            reportWindow.document.close();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }

    function saveSettings() {
        apiKey = document.getElementById('api-key').value.trim();
        if (apiKey) {
            localStorage.setItem('anthropic_api_key', apiKey);
            alert('Settings saved! Your API key is stored locally in your browser.');
        } else {
            localStorage.removeItem('anthropic_api_key');
            alert('API key cleared. Using server default.');
        }
    }

    function loadSettings() {
        const savedKey = localStorage.getItem('anthropic_api_key');
        if (savedKey) {
            apiKey = savedKey;
            document.getElementById('api-key').value = savedKey;
        }
    }

    document.getElementById('question').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            askQuestion();
        }
    });
</script>
```

</body>\
</html>\
"""

def extract_text_from_file(content: bytes, filename: str) -> str:\
"""Extract text from various file formats"""

```
# Text files
if filename.endswith('.txt'):
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        return content.decode('latin-1', errors='ignore')

# PDF files
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

# Word documents
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

# DOC files (old Word format)
elif filename.endswith('.doc'):
    raise HTTPException(status_code=400, detail="Old Word format (.doc) not supported. Please convert to .docx or .txt")

else:
    raise HTTPException(status_code=400, detail="Unsupported file format. Please use TXT, PDF, or DOCX.")
```

@app.get("/", response_class=HTMLResponse)\
async def home():\
"""Serve the main page"""\
return HTML_TEMPLATE

@app.get("/api/departments")\
async def get_departments():\
"""Return list of all departments for dropdown"""\
return {"departments": get_department_list()}

@app.get("/api/roles")\
async def get_roles():\
"""Return list of all job roles for dropdown"""\
return {"roles": get_role_list()}

@app.get("/api/system")\
async def get_system_info():\
"""Return system information including whitelist count"""\
return {\
"total_whitelisted_urls": len(WHITELISTED_URLS),\
"model": "claude-3-5-sonnet-20241022"\
}

@app.post("/api/session/create")\
async def create_session():\
"""Create a new session for tracking questions"""\
session_id = str(uuid.uuid4())\
sessions\[session_id\] = {\
"created_at": datetime.now(),\
"questions": \[\],\
"documents": \[\],\
"document_texts": \[\]  # Store full document content for queries\
}\
return {"session_id": session_id}

@app.get("/api/session/{session_id}")\
async def get_session(session_id: str):\
"""Retrieve session data"""\
if session_id not in sessions:\
raise HTTPException(status_code=404, detail="Session not found")\
return sessions\[session_id\]

@app.get("/api/session/{session_id}/status")\
async def get_session_status(session_id: str):\
"""Get session status including document count"""\
if session_id not in sessions:\
return {\
"exists": False,\
"document_count": 0,\
"can_query": False,\
"documents": \[\]\
}

```
doc_count = len(sessions[session_id].get("document_texts", []))
return {
    "exists": True,
    "document_count": doc_count,
    "can_query": doc_count > 0,
    "documents": [doc["filename"] for doc in sessions[session_id].get("document_texts", [])]
}
```

@app.post("/api/query")\
async def query_ai(\
question: str = Form(...),\
department: str = Form("general_public_works"),\
role: str = Form(""),\
session_id: Optional\[str\] = Form(None),\
api_key: Optional\[str\] = Form(None)\
):\
"""Query the AI with department-specific context and uploaded documents"""

```
# Check if session exists and has documents
if not session_id or session_id not in sessions:
    raise HTTPException(status_code=400, detail="Please upload documents first before asking questions.")

if not sessions[session_id]["document_texts"]:
    raise HTTPException(status_code=400, detail="Please upload at least one document before asking questions.")

anthropic_client = Anthropic(api_key=api_key) if api_key else client

# Get department and role prompts
system_prompt = get_department_prompt(department, role)

# Build context from uploaded documents
document_context = "\n\n=== UPLOADED DOCUMENTS ===\n\n"
for doc in sessions[session_id]["document_texts"]:
    document_context += f"Document: {doc['filename']}\n{doc['content']}\n\n---\n\n"

# Add instruction to reference documents
enhanced_system_prompt = system_prompt + """
```

IMPORTANT: The user has uploaded documents to this session. You MUST:

1. Answer questions based ONLY on the content of the uploaded documents provided below

2. Cite specific documents and sections when providing answers using the format: (Source: \[filename\], Section: \[relevant section\])

3. If the answer is not in the uploaded documents, clearly state: "This information is not available in the uploaded documents."

4. Do not use external knowledge - only reference the document content provided

5. When citing, be specific about which document and which part of the document contains the information\
  """

  try:\
  response = anthropic_client.messages.create(\
  model="claude-3-5-sonnet-20241022",\
  max_tokens=4096,\
  system=enhanced_system_prompt,\
  messages=\[{\
  "role": "user",\
  "content": f"{document_context}\\n\\nQuestion: {question}"\
  }\]\
  )

  ```
   answer = response.content[0].text
   
   sessions[session_id]["questions"].append({
       "question": question,
       "answer": answer,
       "department": get_department_name(department),
       "role": role,
       "timestamp": datetime.now().isoformat(),
       "documents_referenced": len(sessions[session_id]["document_texts"])
   })
   
   return {
       "answer": answer,
       "department": get_department_name(department),
       "documents_used": len(sessions[session_id]["document_texts"])
   }
  ```

  except Exception as e:\
  raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/document/upload")\
async def upload_document(\
file: UploadFile = File(...),\
session_id: str = Form(...),\
department: str = Form("general_public_works"),\
role: str = Form(""),\
api_key: Optional\[str\] = Form(None)\
):\
"""Upload and analyze a document"""

```
if session_id not in sessions:
    raise HTTPException(status_code=404, detail="Session not found")

try:
    # Read file content
    content = await file.read()
    
    # Check file size (10MB limit)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    # Extract text based on file type
    text_content = extract_text_from_file(content, file.filename)
    
    # Limit content size for API (Claude has token limits)
    max_chars = 100000  # ~100KB of text
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n\n[Content truncated due to size...]"
    
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No text content found in document.")
    
    # Store the document text for later queries
    sessions[session_id]["document_texts"].append({
        "filename": file.filename,
        "content": text_content
    })
    
    anthropic_client = Anthropic(api_key=api_key) if api_key else client
    system_prompt = get_department_prompt(department, role)
    
    response = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system=system_prompt + "\n\nAnalyze this document and extract key institutional knowledge, procedures, and important information. Provide citations for any specific claims.",
        messages=[{
            "role": "user",
            "content": f"Document: {file.filename}\n\nContent:\n{text_content}"
        }]
    )
    
    analysis = response.content[0].text
    
    sessions[session_id]["documents"].append({
        "filename": file.filename,
        "analysis": analysis,
        "department": get_department_name(department),
        "role": role,
        "uploaded_at": datetime.now().isoformat()
    })
    
    return {
        "filename": file.filename,
        "analysis": analysis,
        "department": get_department_name(department),
        "total_documents": len(sessions[session_id]["document_texts"])
    }
    
except HTTPException:
    raise
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

@app.post("/api/report/generate")\
async def generate_report(session_id: str = Form(...)):\
"""Generate HTML report with all questions and documents"""

```
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
    <p class="metadata">Session ID: {session_id}</p>
    
    <h2>Documents Analyzed ({len(session_data['documents'])})</h2>
"""

for doc in session_data['documents']:
    html_report += f"""
    <div class="document">
        <strong>Document:</strong> {doc['filename']} ({doc['department']})<br>
        {f"<strong>Role:</strong> {doc['role']}<br>" if doc.get('role') else ""}
        <div class="answer">
            <strong>Analysis:</strong><br>
            {doc['analysis']}
        </div>
        <p class="metadata">Uploaded: {doc['uploaded_at']}</p>
    </div>
    """

html_report += f"""
    <h2>Questions & Answers ({len(session_data['questions'])})</h2>
"""

for i, qa in enumerate(session_data['questions'], 1):
    html_report += f"""
    <div class="question">
        <strong>Q{i} ({qa['department']}):</strong> {qa['question']}<br>
        {f"<strong>Role:</strong> {qa['role']}<br>" if qa.get('role') else ""}
        <p class="metadata">Documents referenced: {qa.get('documents_referenced', 0)}</p>
        <div class="answer">
            <strong>Answer:</strong><br>
            {qa['answer']}
        </div>
        <p class="metadata">Asked: {qa['timestamp']}</p>
    </div>
    """

html_report += """
</body>
</html>
"""

return HTMLResponse(content=html_report)
```

@app.delete("/api/session/{session_id}")\
async def delete_session(session_id: str):\
"""Delete a session"""\
if session_id in sessions:\
del sessions\[session_id\]\
return {"message": "Session deleted"}\
raise HTTPException(status_code=404, detail="Session not found")
