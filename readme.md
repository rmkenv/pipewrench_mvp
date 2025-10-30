# 🔧 PipeWrench AI - Municipal DPW Knowledge Capture System

**Preserving Institutional Knowledge in Public Works**

PipeWrench AI is an AI-powered knowledge capture and retrieval system designed specifically for municipal Department of Public Works (DPW) professionals. Built with Claude 3.5 Sonnet, it helps preserve critical institutional knowledge through document analysis and intelligent Q&A with strict source verification.

---

## 🎯 Key Features

### Document-First Workflow

* **Upload institutional documents** (TXT, PDF, DOCX) containing procedures, standards, and knowledge

* **AI-powered analysis** extracts key information and procedures

* **Session-based storage** keeps your documents available for queries

* **Multi-document support** - upload multiple documents per session

### Intelligent Q&A

* **Document-based answers** - AI responds only using your uploaded content

* **Precise citations** - Every answer includes specific document and section references

* **Department-specific prompts** - Tailored responses for 10+ DPW departments

* **Role-based context** - Additional context for specific job roles (Director, Supervisor, Technician, etc.)

### Compliance & Safety

* **126 whitelisted sources** including:

  * 24 federal sources (OSHA, EPA, FHWA, FAR, etc.)

  * All 50 state DOT standards

  * All 50 state professional engineering licensing boards

* **Anti-hallucination protocols** - Strict source verification

* **Federal compliance** - References FAR, OSHA 1926, EPA regulations, and more

### Report Generation

* **Comprehensive session reports** with all Q&A and document analyses

* **Exportable HTML format** for archiving and sharing

* **Timestamped records** for audit trails

---

## 🏗️ Architecture

### Tech Stack

* **Backend**: FastAPI (Python)

* **AI Model**: Anthropic Claude 3.5 Sonnet

* **Deployment**: Vercel (serverless)

* **Frontend**: Vanilla JavaScript (embedded in FastAPI)

* **File Processing**: PyPDF2, python-docx

### Project Structure

```
pipewrench-ai/
├── api/
│   ├── main.py                          # Main FastAPI application
│   ├── department_prompts_config.py     # Department-specific AI prompts
│   ├── job_roles_config.py              # Job role configurations
│   └── url_whitelist_config.py          # 126 whitelisted compliance sources
├── vercel.json                          # Vercel deployment configuration
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

---

## 🚀 Quick Start

### Prerequisites

* Python 3.9+

* Anthropic API key ([get one here](https://console.anthropic.com/))

* Vercel account (for deployment)

### Local Development

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/pipewrench-ai.git
cd pipewrench-ai
```

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

1. **Set environment variable**

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

1. **Run locally**

```bash
uvicorn api.main:app --reload
```

1. **Open browser**

```
http://localhost:8000
```

### Deploy to Vercel

1. **Install Vercel CLI**

```bash
npm install -g vercel
```

1. **Login to Vercel**

```bash
vercel login
```

1. **Set environment variable in Vercel**

```bash
vercel env add ANTHROPIC_API_KEY
```

Enter your Anthropic API key when prompted.

1. **Deploy**

```bash
vercel --prod
```

Your app will be live at `https://your-project.vercel.app`

---

## 📖 Usage Guide

### Step 1: Upload Documents

1. Navigate to the **"Upload Documents"** tab

2. Select your department/role (optional)

3. Choose a document file (TXT, PDF, or DOCX, max 10MB)

4. Click **"Upload & Analyze"**

5. Review the AI's analysis of the document

6. Repeat for additional documents

### Step 2: Ask Questions

1. Navigate to the **"Ask Questions"** tab

2. Verify your documents are loaded (shown in status box)

3. Select your department/role (optional)

4. Type your question

5. Click **"Ask Question"**

6. Review the answer with document citations

### Step 3: Generate Report

1. Navigate to the **"Generate Report"** tab

2. Click **"Generate Report"**

3. A new window opens with a comprehensive HTML report

4. Save or print for your records

---

## 🏛️ Supported Departments

PipeWrench AI includes specialized prompts for:

* **General Public Works** (default)

* **Water & Wastewater Treatment**

* **Streets & Roads Maintenance**

* **Fleet Management**

* **Facilities Management**

* **Stormwater Management**

* **Solid Waste & Recycling**

* **Parks & Grounds Maintenance**

* **Traffic & Signals**

* **Engineering & Capital Projects**

Each department has tailored AI prompts that understand domain-specific terminology, regulations, and best practices.

---

## 👷 Job Roles

Additional context available for:

* **Department Director**

* **Operations Manager**

* **Maintenance Supervisor**

* **Field Technician**

* **Equipment Operator**

* **Safety Officer**

* **Project Manager**

* **Administrative Staff**

---

## 📋 Whitelisted Federal Sources

PipeWrench AI references **24 federal sources** across 13 categories:

### Federal Acquisition & Construction

* [Federal Acquisition Regulation (FAR) - Part 36](https://www.acquisition.gov/far/part-36)

### OSHA Safety

* [29 CFR Part 1926](https://www.osha.gov/laws-regs/regulations/standardnumber/1926) - Safety and Health Regulations for Construction

* [OSHA Construction Industry Portal](https://www.osha.gov/construction)

### EPA Environmental

* [40 CFR Part 450](https://www.epa.gov/eg/construction-and-development-effluent-guidelines) - Construction and Development Effluent Guidelines

* [EPA Laws & Regulations](https://www.epa.gov/laws-regulations)

* [EPA Managing Environmental Responsibilities Guide](https://www.epa.gov/sites/default/files/2015-10/documents/myerguide.pdf)

* [Federal Environmental Requirements for Construction](https://www.cem.va.gov/pdf/fedreqs.pdf)

### Federal DOT

* [US DOT Roads and Bridges](https://www.transportation.gov/roadways-and-bridges)

* [FHWA Geometric Design Requirements](https://highways.dot.gov/fed-aid-essentials/videos/project-development/design-project-geometric-design-requirements)

* [FHWA Standard Specifications FP-24](https://highways.dot.gov/federal-lands/specs)

### Building Codes

* [International Code Council (ICC)](https://global.iccsafe.org/international-codes-and-standards/) - I-Codes adopted by all 50 states

### Engineering Standards

* [ASCE Standards](https://www.asce.org/publications-and-news/codes-and-standards) - American Society of Civil Engineers

* [ASME Codes & Standards](https://www.asme.org/codes-standards)

### Professional Services

* [Brooks Act (P.L. 92-582)](https://www.fhwa.dot.gov/programadmin/121205.cfm)

* [FAR Subpart 36.6](https://www.acquisition.gov/far/subpart-36.6)

### Standards Organizations

* [American National Standards Institute (ANSI)](https://www.ansi.org)

* [ASTM International](https://www.astm.org)

* [ASTM Construction Standards](https://store.astm.org/products-services/standards-and-publications/standards/construction-standards.html)

### Fire Safety Standards

* [National Fire Protection Association (NFPA)](https://www.nfpa.org/codes-and-standards)

* [NFPA Codes Online (NFCSS)](https://codesonline.nfpa.org)

### Professional Associations

* [American Public Works Association (APWA)](https://www.apwa.org/resources/about-public-works/)

* [National Institute of Standards and Technology (NIST)](https://www.nist.gov)

### Federal Building Standards

* [GSA Facilities Standards](https://www.gsa.gov/real-estate/design-and-construction/facilities-standards-for-the-public-buildings-service)

### Reference

* [Congressional Research on Infrastructure Codes](https://www.congress.gov/crs-product/R47666)

**Plus:** All 50 state DOT standards and professional engineering licensing boards.

**Total: 126 whitelisted sources**

---

## 🔒 Privacy & Security

### Data Handling

* **Session-based storage** - Data stored temporarily in memory

* **No persistent database** - Sessions automatically expire after 24 hours

* **Local API keys** - User-provided API keys stored only in browser localStorage

* **No training data** - Anthropic does not train on API submissions

### Compliance

* **California Generative AI Training Data Transparency Act** - Full disclosure provided

* **GDPR-friendly** - No personal data collection

* **Audit trails** - All Q&A timestamped and exportable

---

## 🛠️ Configuration

### Adding New Departments

Edit `api/department_prompts_config.py`:

```python
DEPARTMENT_PROMPTS = {
    "your_new_department": {
        "name": "Your New Department",
        "prompt": """Your department-specific system prompt here..."""
    }
}
```

### Adding New Job Roles

Edit `api/job_roles_config.py`:

```python
JOB_ROLES = {
    "your_new_role": {
        "title": "Your New Role",
        "context": """Additional context for this role..."""
    }
}
```

### Adding Whitelisted URLs

Edit `api/url_whitelist_config.py`:

```python
WHITELISTED_URLS = {
    "https://example.gov/standards": {
        "include_children": True,
        "description": "Example standards"
    }
}
```

---

## 📊 API Endpoints

### Session Management

* `POST /api/session/create` - Create new session

* `GET /api/session/{session_id}` - Get session data

* `GET /api/session/{session_id}/status` - Get document count and status

* `DELETE /api/session/{session_id}` - Delete session

### Document Operations

* `POST /api/document/upload` - Upload and analyze document

### Query Operations

* `POST /api/query` - Ask question about uploaded documents

### Report Generation

* `POST /api/report/generate` - Generate HTML report

### Configuration

* `GET /api/departments` - List all departments

* `GET /api/roles` - List all job roles

* `GET /api/system` - Get system info (whitelist count, model)

---

## 🧪 Testing

### Manual Testing

1. Upload a sample DPW procedure document

2. Ask questions like:

* "What are the safety requirements for confined space entry?"

* "What is the procedure for emergency water main repairs?"

* "What PPE is required for wastewater operations?"

1. Verify citations reference your uploaded document

### API Testing

```bash
# Create session
curl -X POST http://localhost:8000/api/session/create

# Upload document
curl -X POST http://localhost:8000/api/document/upload \
  -F "file=@sample.pdf" \
  -F "session_id=your-session-id" \
  -F "department=water_wastewater"

# Query
curl -X POST http://localhost:8000/api/query \
  -F "question=What are the safety procedures?" \
  -F "session_id=your-session-id" \
  -F "department=water_wastewater"
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository

2. Create a feature branch (`git checkout -b feature/amazing-feature`)

3. Commit your changes (`git commit -m 'Add amazing feature'`)

4. Push to the branch (`git push origin feature/amazing-feature`)

5. Open a Pull Request

### Areas for Contribution

* Additional department prompts

* More whitelisted compliance sources

* Enhanced document parsing (e.g., Excel, images)

* Multi-language support

* Advanced search features

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

* **Anthropic** - Claude 3.5 Sonnet AI model

* **American Public Works Association (APWA)** - Industry standards and best practices

* **Federal agencies** - OSHA, EPA, FHWA, GSA for public domain compliance resources

* **Municipal DPW professionals** - For feedback and real-world use cases

---

## 📞 Support

* **Issues**: [GitHub Issues](https://github.com/yourusername/pipewrench-ai/issues)

* **Email**: [support@pipewrench.ai](mailto:support@pipewrench.ai)

* **Documentation**: [Full docs](https://pipewrench.ai/docs)

---

## 🗺️ Roadmap

### Version 2.0 (Planned)

* \[ \] Multi-user authentication

* \[ \] Persistent database (PostgreSQL)

* \[ \] Advanced search across all documents

* \[ \] Document versioning

* \[ \] Team collaboration features

* \[ \] Mobile app (iOS/Android)

* \[ \] Integration with municipal document management systems

* \[ \] Automated compliance checking

* \[ \] Training mode for new employees

### Version 1.1 (In Progress)

* \[x\] Document-first workflow

* \[x\] Session-based document storage

* \[x\] 126 whitelisted compliance sources

* \[x\] Role-based context

* \[ \] Excel/CSV support

* \[ \] Image OCR for scanned documents

* \[ \] Bulk document upload

---

## 📈 Use Cases

### Knowledge Transfer

* Retiring employees document their expertise

* New hires learn procedures quickly

* Cross-training between departments

### Compliance & Safety

* Quick reference for OSHA regulations

* EPA compliance verification

* State DOT standard lookups

### Emergency Response

* Rapid access to emergency procedures

* After-hours troubleshooting guidance

* Equipment operation instructions

### Training & Onboarding

* Interactive learning for new employees

* Procedure verification for existing staff

* Continuous professional development

---

## ⚠️ Limitations

* **Document size**: 10MB max per file

* **Session duration**: 24 hours (in-memory storage)

* **File formats**: TXT, PDF, DOCX only (no .doc, Excel, images)

* **Token limits**: \~100KB text per document (Claude API limits)

* **No real-time collaboration**: Single-user sessions only

* **No persistent storage**: Sessions expire after 24 hours

---

## 🔮 Future Enhancements

* **Vector database** for semantic search across all documents

* **RAG (Retrieval Augmented Generation)** for improved accuracy

* **Fine-tuned models** for specific DPW domains

* **Integration with GIS systems** for location-based queries

* **Voice interface** for hands-free operation in the field

* **Offline mode** for areas with limited connectivity

---

**Built with ❤️ for municipal public works professionals**

© 2024 PipeWrench AI. All rights reserved.
