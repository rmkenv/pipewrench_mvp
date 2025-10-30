from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import json
from typing import List, Dict
import PyPDF2
import io

# Import configuration modules
from job_roles_config import get_role_list, get_role_context
from url_whitelist_config import (
    is_url_whitelisted, 
    get_whitelisted_sources,
    add_custom_url,
    remove_custom_url,
    get_custom_urls,
    get_all_whitelisted_urls
)
from department_prompts_config import get_department_prompt, get_all_departments

app = FastAPI(title="PipeWrench AI")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions = {}

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PipeWrench AI - Municipal DPW Knowledge Capture</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
        
        .section h3 {
            color: #1e293b;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #475569;
            font-weight: 500;
        }
        
        select, input[type="text"], input[type="url"], textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        select:focus, input:focus, textarea:focus {
            outline: none;
            border-color: #3b82f6;
        }
        
        textarea {
            min-height: 120px;
            resize: vertical;
            font-family: inherit;
        }
        
        .button {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
        }
        
        .button:active {
            transform: translateY(0);
        }
        
        .button:disabled {
            background: #94a3b8;
            cursor: not-allowed;
            transform: none;
        }
        
        .file-upload {
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .file-upload:hover {
            border-color: #3b82f6;
            background: #f1f5f9;
        }
        
        .file-upload.dragover {
            border-color: #3b82f6;
            background: #dbeafe;
        }
        
        #fileList {
            margin-top: 15px;
        }
        
        .file-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #e2e8f0;
        }
        
        .response-box {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            min-height: 200px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .loading {
            text-align: center;
            color: #64748b;
            padding: 40px;
        }
        
        .spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        .alert-info {
            background: #dbeafe;
            color: #1e40af;
            border: 1px solid #93c5fd;
        }
        
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #6ee7b7;
        }
        
        .alert-warning {
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fcd34d;
        }
        
        .footer {
            background: #f8fafc;
            padding: 20px 30px;
            border-top: 1px solid #e2e8f0;
        }
        
        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .sources-toggle {
            cursor: pointer;
            color: #3b82f6;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .sources-toggle:hover {
            color: #2563eb;
        }
        
        .sources-list {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .sources-list.show {
            display: block;
        }
        
        .source-item {
            padding: 8px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .source-item:last-child {
            border-bottom: none;
        }
        
        .source-item a {
            color: #3b82f6;
            text-decoration: none;
            word-break: break-all;
        }
        
        .source-item a:hover {
            text-decoration: underline;
        }
        
        .custom-url-item {
            background: white;
            padding: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .custom-url-info {
            flex: 1;
        }
        
        .custom-url-url {
            font-weight: 500;
            color: #2563eb;
            word-break: break-all;
            margin-bottom: 4px;
        }
        
        .custom-url-desc {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 4px;
        }
        
        .custom-url-meta {
            font-size: 0.75em;
            color: #999;
        }
        
        .remove-btn {
            background: #dc2626;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            margin-left: 10px;
        }
        
        .remove-btn:hover {
            background: #b91c1c;
        }
        
        .checkbox-label {
            display: flex;
            align-items: center;
            cursor: pointer;
            margin-bottom: 10px;
        }
        
        .checkbox-label input[type="checkbox"] {
            width: auto;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 PipeWrench AI</h1>
            <p>Municipal DPW Knowledge Capture System</p>
        </div>
        
        <div class="content">
            <!-- Role Selection -->
            <div class="section">
                <h3>👤 Select Your Role</h3>
                <div class="form-group">
                    <select id="roleSelect" onchange="updateRoleContext()">
                        <option value="">-- Select Your Role --</option>
                    </select>
                </div>
                <div id="roleContext" style="display: none; margin-top: 10px; padding: 12px; background: #dbeafe; border-radius: 6px; color: #1e40af;">
                </div>
            </div>
            
            <!-- Custom URL Whitelist -->
            <div class="section">
                <h3>🔗 Custom URL Whitelist</h3>
                <p style="font-size: 0.9em; color: #666; margin-bottom: 15px;">
                    Add your organization's internal documentation or additional trusted sources
                </p>
                
                <!-- Add URL Form -->
                <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #e2e8f0;">
                    <div class="form-group">
                        <input type="url" id="customUrl" placeholder="https://example.com/docs" 
                               style="margin-bottom: 10px;">
                    </div>
                    <div class="form-group">
                        <input type="text" id="customUrlDesc" placeholder="Description (optional)">
                    </div>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="includeChildren" checked>
                            <span>Include child pages (e.g., /docs/page1, /docs/page2)</span>
                        </label>
                    </div>
                    <button onclick="addCustomUrl()" class="button" style="width: 100%;">
                        ➕ Add Custom URL
                    </button>
                </div>
                
                <!-- Custom URLs List -->
                <div id="customUrlsList" style="max-height: 250px; overflow-y: auto;">
                    <p style="color: #999; text-align: center; padding: 20px;">Loading custom URLs...</p>
                </div>
            </div>
            
            <!-- Document Upload -->
            <div class="section">
                <h3>📄 Upload Documents</h3>
                <div class="alert alert-info">
                    <strong>📌 Required:</strong> Upload your documents first before asking questions
                </div>
                <div class="file-upload" id="dropZone">
                    <div style="font-size: 3em; margin-bottom: 10px;">📁</div>
                    <p style="font-size: 1.1em; margin-bottom: 8px;">Drag & drop files here or click to browse</p>
                    <p style="font-size: 0.9em; color: #64748b;">Supports PDF, TXT, and other document formats</p>
                    <input type="file" id="fileInput" multiple style="display: none;">
                </div>
                <div id="fileList"></div>
                <button onclick="uploadDocuments()" class="button" style="width: 100%; margin-top: 15px;" id="uploadBtn" disabled>
                    📤 Upload Documents
                </button>
            </div>
            
            <!-- Query Section -->
            <div class="section">
                <h3>💬 Ask a Question</h3>
                <div class="alert alert-warning" id="uploadWarning">
                    ⚠️ Please upload documents before asking questions
                </div>
                <div class="form-group">
                    <label for="queryInput">Your Question:</label>
                    <textarea id="queryInput" placeholder="Ask about compliance, regulations, standards, or best practices..." disabled></textarea>
                </div>
                <button onclick="submitQuery()" class="button" style="width: 100%;" id="queryBtn" disabled>
                    🔍 Get Answer
                </button>
                
                <div id="responseBox" class="response-box" style="display: none;">
                    <div id="responseContent"></div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <div style="margin-bottom: 10px;">
                    <strong>🔒 Verified Sources Only:</strong> All responses reference approved federal, state, and custom sources
                </div>
                <div class="sources-toggle" onclick="toggleSources()">
                    <span id="sourcesToggleText">📚 View Federal Sources (24 sources)</span>
                    <span id="sourcesToggleIcon">▼</span>
                </div>
                <div class="sources-list" id="sourcesList">
                    <div style="font-weight: 600; margin-bottom: 10px; color: #1e293b;">Federal Compliance Sources:</div>
                    <div class="source-item"><a href="https://www.acquisition.gov/far/part-36" target="_blank">Federal Acquisition Regulation (FAR) - Part 36</a></div>
                    <div class="source-item"><a href="https://highways.dot.gov/federal-lands/specs" target="_blank">FHWA Standard Specifications FP-24</a></div>
                    <div class="source-item"><a href="https://www.osha.gov/laws-regs/regulations/standardnumber/1926" target="_blank">OSHA 29 CFR Part 1926</a></div>
                    <div class="source-item"><a href="https://www.osha.gov/construction" target="_blank">OSHA Construction Industry Portal</a></div>
                    <div class="source-item"><a href="https://www.epa.gov/eg/construction-and-development-effluent-guidelines" target="_blank">EPA 40 CFR Part 450</a></div>
                    <div class="source-item"><a href="https://www.epa.gov/laws-regulations" target="_blank">EPA Laws & Regulations</a></div>
                    <div class="source-item"><a href="https://www.transportation.gov/roadways-and-bridges" target="_blank">USDOT Roadways and Bridges</a></div>
                    <div class="source-item"><a href="https://global.iccsafe.org/international-codes-and-standards/" target="_blank">International Code Council (ICC)</a></div>
                    <div class="source-item"><a href="https://www.asce.org/publications-and-news/codes-and-standards" target="_blank">ASCE Codes and Standards</a></div>
                    <div class="source-item"><a href="https://www.asme.org/codes-standards" target="_blank">ASME Codes & Standards</a></div>
                    <div class="source-item"><a href="https://www.fhwa.dot.gov/programadmin/121205.cfm" target="_blank">FHWA Program Administration</a></div>
                    <div class="source-item"><a href="https://www.gsa.gov/real-estate/design-and-construction/facilities-standards-for-the-public-buildings-service" target="_blank">GSA Facilities Standards</a></div>
                    <div class="source-item"><a href="https://www.congress.gov/crs-product/R47666" target="_blank">Congressional Research Service</a></div>
                    <div class="source-item"><a href="https://www.ansi.org" target="_blank">ANSI Standards</a></div>
                    <div class="source-item"><a href="https://www.astm.org" target="_blank">ASTM International</a></div>
                    <div class="source-item"><a href="https://store.astm.org/products-services/standards-and-publications/standards/construction-standards.html" target="_blank">ASTM Construction Standards</a></div>
                    <div class="source-item"><a href="https://www.nfpa.org/codes-and-standards" target="_blank">NFPA Codes and Standards</a></div>
                    <div class="source-item"><a href="https://codesonline.nfpa.org" target="_blank">NFPA Codes Online</a></div>
                    <div class="source-item"><a href="https://www.apwa.org/resources/about-public-works/" target="_blank">APWA Resources</a></div>
                    <div class="source-item"><a href="https://www.nist.gov" target="_blank">NIST Standards</a></div>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e2e8f0; font-size: 0.9em; color: #64748b;">
                        Plus 102 state-specific DOT and licensing board sources
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let sessionId = 'session_' + Date.now();
        let uploadedFiles = [];
        let documentsUploaded = false;
        
        // Load roles on page load
        async function loadRoles() {
            try {
                const response = await fetch('/api/roles');
                const data = await response.json();
                const select = document.getElementById('roleSelect');
                
                data.roles.forEach(role => {
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading roles:', error);
            }
        }
        
        function updateRoleContext() {
            const select = document.getElementById('roleSelect');
            const contextDiv = document.getElementById('roleContext');
            
            if (select.value) {
                const selectedOption = select.options[select.selectedIndex];
                contextDiv.textContent = '✓ Role selected: ' + selectedOption.textContent;
                contextDiv.style.display = 'block';
            } else {
                contextDiv.style.display = 'none';
            }
        }
        
        // Load custom URLs
        async function loadCustomUrls() {
            try {
                const response = await fetch('/api/custom-urls');
                const data = await response.json();
                displayCustomUrls(data.custom_urls || []);
            } catch (error) {
                console.error('Error loading custom URLs:', error);
                document.getElementById('customUrlsList').innerHTML = 
                    '<p style="color: #999; text-align: center; padding: 20px;">No custom URLs added yet</p>';
            }
        }
        
        function displayCustomUrls(urls) {
            const container = document.getElementById('customUrlsList');
            
            if (urls.length === 0) {
                container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No custom URLs added yet</p>';
                return;
            }
            
            container.innerHTML = urls.map(entry => `
                <div class="custom-url-item">
                    <div class="custom-url-info">
                        <div class="custom-url-url">${entry.url}</div>
                        ${entry.description ? `<div class="custom-url-desc">${entry.description}</div>` : ''}
                        <div class="custom-url-meta">
                            ${entry.include_children ? '✓ Includes child pages' : '○ Exact URL only'}
                        </div>
                    </div>
                    <button onclick="removeCustomUrl('${entry.url.replace(/'/g, "\\'")}\')" class="remove-btn">
                        Remove
                    </button>
                </div>
            `).join('');
        }
        
        async function addCustomUrl() {
            const url = document.getElementById('customUrl').value.trim();
            const description = document.getElementById('customUrlDesc').value.trim();
            const includeChildren = document.getElementById('includeChildren').checked;
            
            if (!url) {
                alert('Please enter a URL');
                return;
            }
            
            try {
                const response = await fetch('/api/custom-urls/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        url: url,
                        description: description,
                        include_children: includeChildren
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('customUrl').value = '';
                    document.getElementById('customUrlDesc').value = '';
                    document.getElementById('includeChildren').checked = true;
                    
                    await loadCustomUrls();
                    alert('✅ URL added successfully!');
                } else {
                    alert('❌ ' + result.message);
                }
            } catch (error) {
                console.error('Error adding URL:', error);
                alert('❌ Failed to add URL');
            }
        }
        
        async function removeCustomUrl(url) {
            if (!confirm(`Remove this URL from whitelist?\\n\\n${url}`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/custom-urls/remove', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    await loadCustomUrls();
                    alert('✅ URL removed successfully!');
                } else {
                    alert('❌ ' + result.message);
                }
            } catch (error) {
                console.error('Error removing URL:', error);
                alert('❌ Failed to remove URL');
            }
        }
        
        function toggleSources() {
            const list = document.getElementById('sourcesList');
            const icon = document.getElementById('sourcesToggleIcon');
            
            if (list.classList.contains('show')) {
                list.classList.remove('show');
                icon.textContent = '▼';
            } else {
                list.classList.add('show');
                icon.textContent = '▲';
            }
        }
        
        // File upload handling
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        function handleFiles(files) {
            uploadedFiles = Array.from(files);
            displayFiles();
            document.getElementById('uploadBtn').disabled = uploadedFiles.length === 0;
        }
        
        function displayFiles() {
            const fileList = document.getElementById('fileList');
            if (uploadedFiles.length === 0) {
                fileList.innerHTML = '';
                return;
            }
            
            fileList.innerHTML = '<div style="margin-top: 15px;"><strong>Selected Files:</strong></div>' +
                uploadedFiles.map((file, index) => `
                    <div class="file-item">
                        <span>📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                        <button onclick="removeFile(${index})" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;">Remove</button>
                    </div>
                `).join('');
        }
        
        function removeFile(index) {
            uploadedFiles.splice(index, 1);
            displayFiles();
            document.getElementById('uploadBtn').disabled = uploadedFiles.length === 0;
        }
        
        async function uploadDocuments() {
            if (uploadedFiles.length === 0) {
                alert('Please select files to upload');
                return;
            }
            
            const formData = new FormData();
            formData.append('session_id', sessionId);
            uploadedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            document.getElementById('uploadBtn').disabled = true;
            document.getElementById('uploadBtn').textContent = '⏳ Uploading...';
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    documentsUploaded = true;
                    document.getElementById('uploadWarning').style.display = 'none';
                    document.getElementById('queryInput').disabled = false;
                    document.getElementById('queryBtn').disabled = false;
                    alert('✅ Documents uploaded successfully!');
                } else {
                    alert('❌ Upload failed: ' + result.message);
                }
            } catch (error) {
                console.error('Upload error:', error);
                alert('❌ Upload failed');
            } finally {
                document.getElementById('uploadBtn').disabled = false;
                document.getElementById('uploadBtn').textContent = '📤 Upload Documents';
            }
        }
        
        async function submitQuery() {
            const query = document.getElementById('queryInput').value.trim();
            const role = document.getElementById('roleSelect').value;
            
            if (!documentsUploaded) {
                alert('Please upload documents first');
                return;
            }
            
            if (!query) {
                alert('Please enter a question');
                return;
            }
            
            if (!role) {
                alert('Please select your role');
                return;
            }
            
            const responseBox = document.getElementById('responseBox');
            const responseContent = document.getElementById('responseContent');
            
            responseBox.style.display = 'block';
            responseContent.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Processing your query...</p>
                </div>
            `;
            
            document.getElementById('queryBtn').disabled = true;
            
            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: sessionId,
                        query: query,
                        role: role
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    responseContent.innerHTML = `
                        <div style="line-height: 1.6;">
                            <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px; margin-bottom: 15px; border-radius: 4px;">
                                <strong>✓ Response generated from verified sources</strong>
                            </div>
                            <div style="white-space: pre-wrap;">${result.answer}</div>
                            ${result.sources && result.sources.length > 0 ? `
                                <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #e2e8f0;">
                                    <strong>📚 Sources Referenced:</strong>
                                    <ul style="margin-top: 10px;">
                                        ${result.sources.map(src => `<li><a href="${src}" target="_blank" style="color: #3b82f6;">${src}</a></li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    `;
                } else {
                    responseContent.innerHTML = `
                        <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; color: #991b1b;">
                            <strong>❌ Error:</strong> ${result.message}
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Query error:', error);
                responseContent.innerHTML = `
                    <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; color: #991b1b;">
                        <strong>❌ Error:</strong> Failed to process query
                    </div>
                `;
            } finally {
                document.getElementById('queryBtn').disabled = false;
            }
        }
        
        // Initialize on page load
        window.addEventListener('DOMContentLoaded', () => {
            loadRoles();
            loadCustomUrls();
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main HTML interface"""
    return HTML_TEMPLATE

@app.get("/api/roles")
async def get_roles():
    """Get list of available job roles"""
    roles = get_role_list()
    return {"roles": roles}

@app.get("/api/custom-urls")
async def get_custom_urls_endpoint():
    """Get list of custom whitelisted URLs"""
    custom_urls = get_custom_urls()
    return {"custom_urls": custom_urls}

@app.post("/api/custom-urls/add")
async def add_custom_url_endpoint(request: Request):
    """Add a new custom URL to whitelist"""
    data = await request.json()
    url = data.get("url", "").strip()
    include_children = data.get("include_children", True)
    description = data.get("description", "")
    
    if not url:
        return {"success": False, "message": "URL is required"}
    
    result = add_custom_url(url, include_children, description)
    return result

@app.post("/api/custom-urls/remove")
async def remove_custom_url_endpoint(request: Request):
    """Remove a custom URL from whitelist"""
    data = await request.json()
    url = data.get("url", "").strip()
    
    if not url:
        return {"success": False, "message": "URL is required"}
    
    result = remove_custom_url(url)
    return result

@app.post("/api/upload")
async def upload_documents(request: Request):
    """Handle document uploads"""
    form = await request.form()
    session_id = form.get("session_id")
    files = form.getlist("files")
    
    if not session_id:
        return JSONResponse({"success": False, "message": "Session ID required"}, status_code=400)
    
    if not files:
        return JSONResponse({"success": False, "message": "No files uploaded"}, status_code=400)
    
    # Initialize session storage
    if session_id not in sessions:
        sessions[session_id] = {
            "documents": [],
            "document_texts": []
        }
    
    # Process uploaded files
    for file in files:
        try:
            content = await file.read()
            
            # Extract text based on file type
            if file.filename.endswith('.pdf'):
                text = extract_text_from_pdf(content)
            elif file.filename.endswith('.txt'):
                text = content.decode('utf-8')
            else:
                text = content.decode('utf-8', errors='ignore')
            
            sessions[session_id]["documents"].append({
                "filename": file.filename,
                "size": len(content),
                "uploaded_at": datetime.now().isoformat()
            })
            
            sessions[session_id]["document_texts"].append({
                "filename": file.filename,
                "text": text
            })
            
        except Exception as e:
            return JSONResponse({
                "success": False,
                "message": f"Error processing {file.filename}: {str(e)}"
            }, status_code=500)
    
    return {
        "success": True,
        "message": f"Uploaded {len(files)} file(s)",
        "files": [f.filename for f in files]
    }

@app.post("/api/query")
async def process_query(request: Request):
    """Process user query against uploaded documents"""
    data = await request.json()
    session_id = data.get("session_id")
    query = data.get("query")
    role = data.get("role")
    
    if not session_id or session_id not in sessions:
        return {"success": False, "message": "No documents uploaded. Please upload documents first."}
    
    if not query:
        return {"success": False, "message": "Query is required"}
    
    if not role:
        return {"success": False, "message": "Role selection is required"}
    
    session_data = sessions[session_id]
    
    if not session_data.get("document_texts"):
        return {"success": False, "message": "No documents found. Please upload documents first."}
    
    try:
        # Get role context
        role_context = get_role_context(role)
        
        # Simulate AI processing (replace with actual AI integration)
        answer = generate_answer(query, session_data["document_texts"], role_context)
        
        # Extract and validate sources
        sources = extract_sources(answer)
        validated_sources = [src for src in sources if is_url_whitelisted(src)]
        
        return {
            "success": True,
            "answer": answer,
            "sources": validated_sources,
            "role": role
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error processing query: {str(e)}"}

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\\n"
        return text
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {str(e)}")

def generate_answer(query: str, documents: List[Dict], role_context: str) -> str:
    """
    Generate answer based on query and documents
    This is a placeholder - integrate with your AI model here
    """
    # Combine document texts
    combined_text = "\\n\\n".join([doc["text"] for doc in documents])
    
    # Placeholder response
    answer = f"""Based on the uploaded documents and your role as {role_context}:

{query}

[This is a placeholder response. Integrate with your AI model (OpenAI, Anthropic, etc.) to generate actual responses based on:
1. The user's query
2. The uploaded document content
3. The user's role context
4. References to whitelisted sources only]

The system will ensure all citations reference only approved federal, state, and custom whitelisted sources.

Example sources that might be referenced:
- https://www.osha.gov/construction
- https://www.epa.gov/laws-regulations
- https://www.fhwa.dot.gov/programadmin/121205.cfm
"""
    
    return answer

def extract_sources(text: str) -> List[str]:
    """Extract URLs from text"""
    import re
    url_pattern = r'https?://[^\\s<>"{}|\\\\^`\\[\\]]+'
    urls = re.findall(url_pattern, text)
    return list(set(urls))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
