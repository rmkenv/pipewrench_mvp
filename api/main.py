"""
DPW Knowledge Capture System - Standalone Version
All configurations embedded for Vercel deployment
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import PyPDF2
import io
import re
from urllib.parse import urlparse

app = FastAPI()

# ============================================================================
# CONFIGURATION: JOB ROLES
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

def get_role_list():
    """Return list of available roles"""
    return [{"id": role_id, "name": role_data["name"]} for role_id, role_data in JOB_ROLES.items()]

def get_role_context(role_id: str) -> str:
    """Get context for a specific role"""
    return JOB_ROLES.get(role_id, JOB_ROLES["general"])["context"]

# ============================================================================
# CONFIGURATION: URL WHITELIST
# ============================================================================

URL_WHITELIST = [
    {"url": "https://www.acquisition.gov/far/part-36", "include_children": True},
    {"url": "https://highways.dot.gov/federal-lands/specs", "include_children": True},
    {"url": "https://www.osha.gov/laws-regs/regulations/standardnumber/1926", "include_children": True},
    {"url": "https://www.osha.gov/construction", "include_children": True},
    {"url": "https://www.epa.gov/eg/construction-and-development-effluent-guidelines", "include_children": True},
    {"url": "https://www.epa.gov/laws-regulations", "include_children": True},
    {"url": "https://www.epa.gov/sites/default/files/2015-10/documents/myerguide.pdf", "include_children": True},
    {"url": "https://www.cem.va.gov/pdf/fedreqs.pdf", "include_children": True},
    {"url": "https://www.transportation.gov/roadways-and-bridges", "include_children": True},
    {"url": "https://highways.dot.gov/fed-aid-essentials/videos/project-development/design-project-geometric-design-requirements", "include_children": True},
    {"url": "https://global.iccsafe.org/international-codes-and-standards/", "include_children": True},
    {"url": "https://www.asce.org/publications-and-news/codes-and-standards", "include_children": True},
    {"url": "https://www.asme.org/codes-standards", "include_children": True},
    {"url": "https://www.fhwa.dot.gov/programadmin/121205.cfm", "include_children": True},
    {"url": "https://www.acquisition.gov/far/subpart-36.6", "include_children": True},
    {"url": "https://www.gsa.gov/real-estate/design-and-construction/facilities-standards-for-the-public-buildings-service", "include_children": True},
    {"url": "https://www.congress.gov/crs-product/R47666", "include_children": True},
    {"url": "https://www.ansi.org", "include_children": True},
    {"url": "https://www.astm.org", "include_children": True},
    {"url": "https://store.astm.org/products-services/standards-and-publications/standards/construction-standards.html", "include_children": True},
    {"url": "https://www.nfpa.org/codes-and-standards", "include_children": True},
    {"url": "https://codesonline.nfpa.org", "include_children": True},
    {"url": "https://www.apwa.org/resources/about-public-works/", "include_children": True},
    {"url": "https://www.nist.gov", "include_children": True},
    {"url": "https://www.dot.state.al.us/publications/Maintenance/pdf/Permits/PermitManual.pdf", "include_children": True},
    {"url": "https://bels.alabama.gov", "include_children": True},
    {"url": "https://dot.alaska.gov/stwddes/dcsstandards.shtml", "include_children": True},
    {"url": "https://www.commerce.alaska.gov/web/cbpl/ProfessionalLicensing/BoardofArchitectsEngineersandLandSurveyors.aspx", "include_children": True},
    {"url": "https://azdot.gov/business/engineering-standards", "include_children": True},
    {"url": "https://btr.az.gov/licensing/professional-engineering", "include_children": True},
    {"url": "https://www.arkansashighways.com/standard_specifications.aspx", "include_children": True},
    {"url": "https://www.arkansas.gov/pels/", "include_children": True},
    {"url": "https://www.dir.ca.gov/public-works/publicworks.html", "include_children": True},
    {"url": "https://www.bpelsg.ca.gov/", "include_children": True},
    {"url": "https://www.codot.gov/business/designsupport/cdot-construction-specifications", "include_children": True},
    {"url": "https://dpo.colorado.gov/Engineers", "include_children": True},
    {"url": "https://portal.ct.gov/DOT/Engineering", "include_children": True},
    {"url": "https://portal.ct.gov/DCP/License-Services-Division/PE-Home-Page/Professional-Engineer-PE", "include_children": True},
    {"url": "https://deldot.gov/Programs/DRC/", "include_children": True},
    {"url": "https://dpr.delaware.gov/boards/professionalengineers/", "include_children": True},
    {"url": "https://dpw.dc.gov/", "include_children": True},
    {"url": "https://dcra.dc.gov/service/professional-engineers", "include_children": True},
    {"url": "https://www.fdot.gov/programmanagement/implemented/specbooks/default.shtm", "include_children": True},
    {"url": "https://fbpe.org/", "include_children": True},
    {"url": "https://www.dot.ga.gov/PartnerSmart/DesignManuals/Specifications", "include_children": True},
    {"url": "https://sos.ga.gov/page/engineers-land-surveyors", "include_children": True},
    {"url": "https://hidot.hawaii.gov/highways/home/standards-and-specifications/", "include_children": True},
    {"url": "https://cca.hawaii.gov/pvl/boards/engineer/", "include_children": True},
    {"url": "https://itd.idaho.gov/highway-construction-standards/", "include_children": True},
    {"url": "https://ipels.idaho.gov/", "include_children": True},
    {"url": "https://idot.illinois.gov/doing-business/procurements/engineering-architectural-professional-services/index.html", "include_children": True},
    {"url": "https://www.idfpr.com/profs/ProfEng.asp", "include_children": True},
    {"url": "https://www.in.gov/indot/construction/design-standards/", "include_children": True},
    {"url": "https://www.in.gov/pla/professions/professional-engineers/", "include_children": True},
    {"url": "https://iowadot.gov/design/dmanual", "include_children": True},
    {"url": "https://plb.iowa.gov/board/engineering-and-land-surveying", "include_children": True},
    {"url": "https://www.ksdot.org/bureaus/burConsMain/SpecProv/specprov.asp", "include_children": True},
    {"url": "https://www.kansas.gov/engineers/", "include_children": True},
    {"url": "https://transportation.ky.gov/Highway-Design/Pages/Design-Guidance.aspx", "include_children": True},
    {"url": "https://kyboels.ky.gov/", "include_children": True},
    {"url": "https://www.dotd.la.gov/engineering/standards/", "include_children": True},
    {"url": "https://lapels.com/", "include_children": True},
    {"url": "https://www.maine.gov/mdot/engineering/", "include_children": True},
    {"url": "https://www.maine.gov/professionalengineers/", "include_children": True},
    {"url": "https://www.roads.maryland.gov/ohd2/", "include_children": True},
    {"url": "https://dllr.maryland.gov/license/pe/", "include_children": True},
    {"url": "https://www.mass.gov/orgs/highway-division", "include_children": True},
    {"url": "https://www.mass.gov/orgs/board-of-registration-of-professional-engineers-and-land-surveyors", "include_children": True},
    {"url": "https://www.michigan.gov/mdot/design/standards", "include_children": True},
    {"url": "https://www.michigan.gov/lara/bureau-list/bpl/occ/prof/engineers", "include_children": True},
    {"url": "https://www.dot.state.mn.us/bridge/manuals.html", "include_children": True},
    {"url": "https://mn.gov/boards/engineering/", "include_children": True},
    {"url": "https://www.mdot.ms.gov/portal/home/engineering", "include_children": True},
    {"url": "https://www.pepls.ms.gov/", "include_children": True},
    {"url": "https://www.modot.org/engineering-policy-guide", "include_children": True},
    {"url": "https://pr.mo.gov/engineers-architects-land-surveyors.asp", "include_children": True},
    {"url": "https://www.mdt.mt.gov/publications/manuals.shtml", "include_children": True},
    {"url": "https://boards.bsd.dli.mt.gov/pel", "include_children": True},
    {"url": "https://dot.nebraska.gov/business-center/design-consultant/design-manuals/", "include_children": True},
    {"url": "https://engineers.nebraska.gov/", "include_children": True},
    {"url": "https://www.dot.nv.gov/doing-business/design-engineering", "include_children": True},
    {"url": "https://nv.gov/BOE/", "include_children": True},
    {"url": "https://www.nh.gov/dot/programs/projectdevelopment/", "include_children": True},
    {"url": "https://www.oplc.nh.gov/board-professional-engineers", "include_children": True},
    {"url": "https://www.nj.gov/transportation/eng/", "include_children": True},
    {"url": "https://www.njconsumeraffairs.gov/pels/", "include_children": True},
    {"url": "https://www.dot.nm.gov/engineering/", "include_children": True},
    {"url": "https://www.rld.nm.gov/boards-and-commissions/individual-boards-and-commissions/professional-engineers-and-professional-surveyors/", "include_children": True},
    {"url": "https://www.dot.ny.gov/divisions/engineering", "include_children": True},
    {"url": "https://www.op.nysed.gov/professions/engineering", "include_children": True},
    {"url": "https://www.ncdot.gov/engineering/", "include_children": True},
    {"url": "https://www.ncbels.org/", "include_children": True},
    {"url": "https://www.dot.nd.gov/divisions/design/", "include_children": True},
    {"url": "https://www.ndpelsboard.org/", "include_children": True},
    {"url": "https://www.transportation.ohio.gov/working/engineering", "include_children": True},
    {"url": "https://peps.ohio.gov/", "include_children": True},
    {"url": "https://www.odot.org/roadway/", "include_children": True},
    {"url": "https://www.ok.gov/pels/", "include_children": True},
    {"url": "https://www.oregon.gov/odot/Engineering/Pages/Standards.aspx", "include_children": True},
    {"url": "https://www.oregon.gov/osbeels/", "include_children": True},
    {"url": "https://www.penndot.pa.gov/ProjectAndPrograms/Design/Pages/default.aspx", "include_children": True},
    {"url": "https://www.dos.pa.gov/ProfessionalLicensing/BoardsCommissions/Engineers/Pages/default.aspx", "include_children": True},
    {"url": "https://www.dot.ri.gov/engineering/", "include_children": True},
    {"url": "https://health.ri.gov/licenses/detail.php?id=250", "include_children": True},
    {"url": "https://www.scdot.org/business/engineering.aspx", "include_children": True},
    {"url": "https://llr.sc.gov/pel/", "include_children": True},
    {"url": "https://dot.sd.gov/doing-business/engineering", "include_children": True},
    {"url": "https://dlr.sd.gov/bdotm/engineeringsurveying/", "include_children": True},
    {"url": "https://www.tn.gov/tdot/roadway-design.html", "include_children": True},
    {"url": "https://www.tn.gov/commerce/regboards/aeel.html", "include_children": True},
    {"url": "https://www.txdot.gov/inside-txdot/division/design.html", "include_children": True},
    {"url": "https://pels.texas.gov/", "include_children": True},
    {"url": "https://www.udot.utah.gov/main/f?p=100:pg:0:::1:T,V:1435", "include_children": True},
    {"url": "https://dopl.utah.gov/eng/", "include_children": True},
    {"url": "https://vtrans.vermont.gov/highway-construction", "include_children": True},
    {"url": "https://sos.vermont.gov/engineers-land-surveyors/", "include_children": True},
    {"url": "https://www.virginiadot.org/business/design-manual.asp", "include_children": True},
    {"url": "https://www.dpor.virginia.gov/boards/professional-engineers", "include_children": True},
    {"url": "https://wsdot.wa.gov/engineering-standards/design-topics-manuals", "include_children": True},
    {"url": "https://fortress.wa.gov/dol/dolprod/bpdlicensing/", "include_children": True},
    {"url": "https://transportation.wv.gov/highways/engineering/Pages/default.aspx", "include_children": True},
    {"url": "https://peboards.wv.gov/", "include_children": True},
    {"url": "https://wisconsindot.gov/Pages/doing-bus/eng-consultants/cnslt-rsrces/design/default.aspx", "include_children": True},
    {"url": "https://dsps.wi.gov/Pages/Professions/Engineer/Default.aspx", "include_children": True},
    {"url": "https://www.dot.state.wy.us/home/engineering_technical_programs/engineering_programs.html", "include_children": True},
    {"url": "https://engineer-lsla.wyoming.gov/", "include_children": True},
]

# Session storage for custom URLs
session_custom_urls: Dict[str, List[str]] = {}

def is_url_whitelisted(url: str, session_id: str = None) -> bool:
    """Check if URL is in whitelist or custom session URLs"""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    
    # Check default whitelist
    for entry in URL_WHITELIST:
        whitelisted_url = entry["url"]
        if entry["include_children"]:
            if base_url.startswith(whitelisted_url.rstrip('/')):
                return True
        else:
            if base_url == whitelisted_url:
                return True
    
    # Check session custom URLs
    if session_id and session_id in session_custom_urls:
        for custom_url in session_custom_urls[session_id]:
            if base_url.startswith(custom_url.rstrip('/')):
                return True
    
    return False

def get_whitelisted_sources() -> List[Dict[str, str]]:
    """Return formatted list of whitelisted sources"""
    sources = []
    for entry in URL_WHITELIST:
        sources.append({
            "url": entry["url"],
            "include_children": entry["include_children"]
        })
    return sources

def get_federal_sources() -> List[str]:
    """Return list of federal source URLs"""
    federal_keywords = ['acquisition.gov', 'dot.gov', 'osha.gov', 'epa.gov', 'fhwa.dot', 
                       'transportation.gov', 'gsa.gov', 'congress.gov', 'nist.gov']
    federal_sources = []
    for entry in URL_WHITELIST:
        if any(keyword in entry["url"] for keyword in federal_keywords):
            federal_sources.append(entry["url"])
    return federal_sources

# ============================================================================
# CONFIGURATION: DEPARTMENT PROMPTS
# ============================================================================

DEPARTMENT_PROMPTS = {
    "streets_roads": {
        "name": "Streets & Roads",
        "prompt": """You are a specialized AI assistant for municipal Streets & Roads operations.

**Your Expertise:**
- Pavement management and maintenance
- Street design standards and specifications
- Traffic control devices and signage
- Roadway safety improvements
- Winter maintenance operations
- Street lighting and signals
- ADA compliance for pedestrian facilities

**Key Responsibilities:**
- Provide guidance on MUTCD standards
- Assist with pavement condition assessments
- Recommend maintenance strategies
- Explain traffic calming measures
- Guide winter operations planning

Always reference applicable federal (FHWA, MUTCD) and state DOT standards."""
    },
    "water_sewer": {
        "name": "Water & Sewer",
        "prompt": """You are a specialized AI assistant for municipal Water & Sewer utilities.

**Your Expertise:**
- Water distribution system design and maintenance
- Wastewater collection systems
- Stormwater management
- EPA Clean Water Act compliance
- AWWA and WEF standards
- Pump station operations
- Water quality monitoring

**Key Responsibilities:**
- Guide compliance with Safe Drinking Water Act
- Assist with capacity planning
- Explain treatment processes
- Recommend infrastructure improvements
- Address regulatory requirements

Always reference EPA regulations, state environmental standards, and industry best practices (AWWA, WEF)."""
    },
    "solid_waste": {
        "name": "Solid Waste & Recycling",
        "prompt": """You are a specialized AI assistant for Solid Waste & Recycling operations.

**Your Expertise:**
- Collection route optimization
- Recycling program management
- Landfill operations and regulations
- Hazardous waste handling
- EPA RCRA compliance
- Waste reduction strategies
- Equipment specifications

**Key Responsibilities:**
- Guide EPA waste regulations compliance
- Recommend collection best practices
- Assist with recycling program development
- Explain proper disposal procedures
- Address environmental concerns

Always reference EPA RCRA regulations, state solid waste rules, and industry standards."""
    },
    "fleet_equipment": {
        "name": "Fleet & Equipment",
        "prompt": """You are a specialized AI assistant for Fleet & Equipment management.

**Your Expertise:**
- Fleet maintenance programs
- Equipment specifications and procurement
- Preventive maintenance scheduling
- Fuel management
- Vehicle replacement planning
- Shop safety (OSHA compliance)
- Telematics and fleet tracking

**Key Responsibilities:**
- Recommend maintenance best practices
- Guide equipment selection
- Assist with lifecycle cost analysis
- Explain OSHA shop safety requirements
- Support fleet optimization

Always reference OSHA standards, manufacturer specifications, and fleet management best practices."""
    },
    "parks_facilities": {
        "name": "Parks & Facilities",
        "prompt": """You are a specialized AI assistant for Parks & Facilities management.

**Your Expertise:**
- Park maintenance operations
- Playground safety standards (CPSC, ASTM)
- Building maintenance
- Grounds management
- ADA accessibility requirements
- Athletic field maintenance
- Facility energy management

**Key Responsibilities:**
- Guide CPSC Playground safety compliance
- Recommend maintenance schedules
- Assist with accessibility improvements
- Explain building code requirements
- Support sustainability initiatives

Always reference CPSC guidelines, ASTM standards, ADA requirements, and building codes."""
    },
    "engineering": {
        "name": "Engineering & Design",
        "prompt": """You are a specialized AI assistant for municipal Engineering & Design.

**Your Expertise:**
- Civil engineering design standards
- Construction specifications
- Plan review and permitting
- Surveying and GIS
- Professional engineering requirements
- Project management
- Value engineering

**Key Responsibilities:**
- Guide engineering design standards
- Assist with specification development
- Explain permitting requirements
- Support project delivery methods
- Address professional licensing requirements

Always reference ASCE standards, state engineering requirements, and applicable building codes."""
    },
    "construction": {
        "name": "Construction Management",
        "prompt": """You are a specialized AI assistant for Construction Management.

**Your Expertise:**
- Construction inspection procedures
- Quality control and assurance
- Contract administration
- Change order management
- Progress monitoring
- Safety compliance (OSHA)
- Materials testing

**Key Responsibilities:**
- Guide inspection best practices
- Assist with contract interpretation
- Explain quality control procedures
- Support safety compliance
- Address construction documentation

Always reference OSHA construction standards, contract specifications, and industry best practices."""
    },
    "environmental": {
        "name": "Environmental Compliance",
        "prompt": """You are a specialized AI assistant for Environmental Compliance.

**Your Expertise:**
- EPA regulations (Clean Water Act, Clean Air Act)
- NPDES stormwater permits
- Environmental impact assessments
- Wetlands protection
- Erosion and sediment control
- Hazardous materials management
- Environmental monitoring

**Key Responsibilities:**
- Guide EPA compliance requirements
- Assist with permit applications
- Explain environmental regulations
- Support pollution prevention
- Address remediation procedures

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

class CustomURLRequest(BaseModel):
    session_id: str
    url: str

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_text_from_pdf(pdf_file: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")

def create_system_prompt(role: str, department: Optional[str] = None) -> str:
    """Create system prompt based on role and department"""
    
    base_prompt = f"""You are an AI assistant for municipal Department of Public Works (DPW) operations.

{get_role_context(role)}

**STRICT SYSTEM INSTRUCTIONS - CRITICAL:**

1. **SOURCE VERIFICATION (MANDATORY):**
   - You may ONLY reference information from:
     a) The user's uploaded documents (if provided)
     b) The pre-approved whitelisted sources
   - NEVER use your general training knowledge
   - NEVER make assumptions or provide information not explicitly found in these sources
   - If information is not in the uploaded documents or whitelisted sources, you MUST say: "I cannot find this information in the provided documents or approved sources."

2. **CITATION REQUIREMENTS:**
   - ALWAYS cite your sources with [Source: filename/URL]
   - For uploaded documents: [Source: document_name.pdf, page X]
   - For whitelisted sources: [Source: URL]
   - Every factual claim must have a citation

3. **PROHIBITED ACTIONS:**
   - Do NOT fabricate or "hallucinate" information
   - Do NOT use general knowledge not verified in provided sources
   - Do NOT make assumptions about local regulations unless explicitly stated in documents
   - Do NOT provide legal advice (suggest consulting legal counsel)

4. **RESPONSE FORMAT:**
   - Start with a direct answer if found in sources
   - Provide relevant citations
   - If information is incomplete, state what is missing
   - Suggest which whitelisted sources might contain the information

5. **UNCERTAINTY HANDLING:**
   - If unsure, say "I'm not certain based on the provided documents"
   - Offer to search specific whitelisted sources
   - Never guess or approximate when precision is required

"""

    if department:
        dept_prompt = get_department_prompt(department)
        if dept_prompt:
            base_prompt += f"\n**DEPARTMENT-SPECIFIC CONTEXT:**\n{dept_prompt}\n"
    
    return base_prompt

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    """Generate mock AI response (replace with actual LLM call)"""
    
    doc_note = "uploaded document and " if has_document else ""
    
    # This is a placeholder - integrate your actual LLM here
    response = f"""Based on the {doc_note}whitelisted sources:

**Answer:** I can help you with "{query}".

"""
    
    if has_document:
        response += f"""**Context from Uploaded Document:**
{context[:500]}...

"""
    
    response += f"""**Sources Referenced:**
"""
    
    if has_document:
        response += "- [Source: Uploaded Document]\n"
    
    response += """- [Source: Relevant whitelisted URL]

**Note:** This is a demonstration response. In production, this would be generated by your LLM with strict adherence to the system prompt requiring source verification.

---
*Remember: All responses must cite sources from uploaded documents or whitelisted URLs only.*
"""
    
    return response

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process PDF document"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Read file
    content = await file.read()
    
    # Extract text
    text = extract_text_from_pdf(content)
    
    # Create session
    import uuid
    session_id = str(uuid.uuid4())
    
    # Store in session
    sessions[session_id] = {
        "filename": file.filename,
        "text": text,
        "uploaded_at": "timestamp_here"
    }
    
    # Count pages
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
    page_count = len(pdf_reader.pages)
    
    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        pages=page_count,
        message=f"Successfully uploaded {file.filename} ({page_count} pages)"
    )

@app.post("/query")
async def query_documents(request: QueryRequest):
    """Query with or without uploaded documents"""
    
    # Get document context if session exists
    document_text = ""
    has_document = False
    
    if request.session_id and request.session_id in sessions:
        session_data = sessions[request.session_id]
        document_text = session_data["text"]
        has_document = True
    
    # Create system prompt
    system_prompt = create_system_prompt(request.role, request.department)
    
    # Generate response (replace with actual LLM call)
    response = generate_mock_response(request.query, document_text, system_prompt, has_document)
    
    sources = ["whitelisted_urls"]
    if has_document:
        sources.insert(0, "uploaded_document")
    
    return JSONResponse({
        "answer": response,
        "session_id": request.session_id,
        "sources_used": sources
    })

@app.get("/roles")
async def get_roles():
    """Get list of available job roles"""
    return JSONResponse(get_role_list())

@app.get("/departments")
async def get_departments():
    """Get list of available departments"""
    return JSONResponse(get_all_departments())

@app.get("/whitelisted-sources")
async def get_sources():
    """Get list of whitelisted sources"""
    return JSONResponse(get_whitelisted_sources())

@app.post("/custom-url/add")
async def add_custom_url(request: CustomURLRequest):
    """Add custom URL to session whitelist"""
    if request.session_id not in session_custom_urls:
        session_custom_urls[request.session_id] = []
    
    # Validate URL format
    parsed = urlparse(request.url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # Add to session
    if request.url not in session_custom_urls[request.session_id]:
        session_custom_urls[request.session_id].append(request.url)
    
    return JSONResponse({
        "message": "URL added successfully",
        "url": request.url,
        "session_id": request.session_id
    })

@app.get("/custom-url/list/{session_id}")
async def list_custom_urls(session_id: str):
    """List custom URLs for session"""
    urls = session_custom_urls.get(session_id, [])
    return JSONResponse({"session_id": session_id, "custom_urls": urls})

@app.post("/custom-url/remove")
async def remove_custom_url(request: CustomURLRequest):
    """Remove custom URL from session whitelist"""
    if request.session_id in session_custom_urls:
        if request.url in session_custom_urls[request.session_id]:
            session_custom_urls[request.session_id].remove(request.url)
            return JSONResponse({"message": "URL removed successfully"})
    
    raise HTTPException(status_code=404, detail="URL not found in session")

# ============================================================================
# HTML FRONTEND
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Municipal DPW Knowledge Capture System</title>
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
            max-width: 900px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }

        .header h1 {
            color: #333;
            font-size: 2em;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 1.1em;
        }

        .card {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }

        .upload-zone {
            border: 3px dashed #ddd;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #fafafa;
        }

        .upload-zone:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }

        .upload-zone.dragover {
            border-color: #667eea;
            background: #e8edff;
        }

        .upload-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }

        select, input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }

        select:focus, input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 500;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .btn-small {
            padding: 8px 20px;
            font-size: 0.9em;
        }

        .query-container {
            display: flex;
            gap: 10px;
        }

        .query-input {
            flex: 1;
        }

        .response-box {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            min-height: 150px;
            white-space: pre-wrap;
            line-height: 1.6;
            color: #333;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }

        .alert.show {
            display: block;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .custom-url-box {
            background: #fff9e6;
            border: 2px solid #ffd700;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }

        .custom-url-box h4 {
            color: #856404;
            margin-bottom: 10px;
        }

        .custom-url-box p {
            color: #856404;
            font-size: 0.9em;
            margin-bottom: 15px;
        }

        .url-input-group {
            display: flex;
            gap: 10px;
        }

        .url-list {
            margin-top: 15px;
            max-height: 200px;
            overflow-y: auto;
        }

        .url-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 8px;
            font-size: 0.9em;
        }

        .btn-remove {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.85em;
        }

        .btn-remove:hover {
            background: #c82333;
        }

        .footer {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-top: 20px;
        }

        .footer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }

        .footer-title {
            font-weight: 600;
            color: #667eea;
        }

        .footer-arrow {
            transition: transform 0.3s;
        }

        .footer-arrow.expanded {
            transform: rotate(180deg);
        }

        .footer-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }

        .footer-content.show {
            max-height: 600px;
            overflow-y: auto;
            margin-top: 15px;
        }

        .source-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }

        .source-link {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }

        .source-link:hover {
            text-decoration: underline;
        }

        input[type="file"] {
            display: none;
        }

        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
            
            .source-grid {
                grid-template-columns: 1fr;
            }
            
            .query-container {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ Municipal DPW Knowledge Capture System</h1>
            <p>AI-Powered Infrastructure Knowledge Base with Source Verification</p>
        </div>

        <div id="alertBox" class="alert"></div>

        <!-- Upload Section (Optional) -->
        <div class="card">
            <h2>📄 Upload Document (Optional)</h2>
            <p style="color: #666; margin-bottom: 15px;">Upload a PDF to query your own documents, or skip to query whitelisted sources directly.</p>
            <div class="upload-zone" id="uploadZone">
                <div class="upload-icon">📁</div>
                <div>Drag & drop your PDF here or click to browse</div>
                <div style="color: #999; font-size: 0.9em; margin-top: 10px;">PDF files only</div>
                <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelect(event)">
            </div>
        </div>

        <!-- Query Section -->
        <div class="card">
            <h2>⚙️ Configure Your Query</h2>
            
            <div class="grid-2">
                <div class="form-group">
                    <label>Your Role</label>
                    <select id="roleSelect"></select>
                </div>
                <div class="form-group">
                    <label>Department (Optional)</label>
                    <select id="departmentSelect">
                        <option value="">Select Department</option>
                    </select>
                </div>
            </div>

            <!-- Custom URLs -->
            <div class="custom-url-box">
                <h4>🔗 Add Your Organization's URLs</h4>
                <p>Add additional trusted sources specific to your organization</p>
                <div class="url-input-group">
                    <input type="text" id="customUrlInput" placeholder="https://your-organization.com/resource">
                    <button class="btn btn-small" onclick="addCustomUrl()">Add URL</button>
                </div>
                <div id="customUrlList" class="url-list"></div>
            </div>

            <div class="form-group" style="margin-top: 20px;">
                <label>Your Question</label>
                <div class="query-container">
                    <input type="text" id="queryInput" class="query-input" 
                           placeholder="Ask a question..." 
                           onkeypress="handleQueryKeyPress(event)">
                    <button class="btn" onclick="submitQuery()">Ask Question</button>
                </div>
            </div>
        </div>

        <!-- Response Section -->
        <div class="card" id="responseSection" style="display: none;">
            <h2>💡 Response</h2>
            <div id="responseBox" class="response-box">
                Your answer will appear here...
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <div class="footer-header" onclick="toggleFooter()">
                <span class="footer-title">📚 Federal Whitelisted Sources (24 sources)</span>
                <span id="footerArrow" class="footer-arrow">▼</span>
            </div>
            <div id="footerContent" class="footer-content">
                <div class="source-grid">
                    <a href="https://www.acquisition.gov/far/part-36" target="_blank" class="source-link">• FAR Part 36</a>
                    <a href="https://highways.dot.gov/federal-lands/specs" target="_blank" class="source-link">• FHWA Standards</a>
                    <a href="https://www.osha.gov/laws-regs/regulations/standardnumber/1926" target="_blank" class="source-link">• OSHA 29 CFR 1926</a>
                    <a href="https://www.osha.gov/construction" target="_blank" class="source-link">• OSHA Construction</a>
                    <a href="https://www.epa.gov/eg/construction-and-development-effluent-guidelines" target="_blank" class="source-link">• EPA 40 CFR 450</a>
                    <a href="https://www.epa.gov/laws-regulations" target="_blank" class="source-link">• EPA Laws & Regulations</a>
                    <a href="https://www.transportation.gov/roadways-and-bridges" target="_blank" class="source-link">• US DOT Roads & Bridges</a>
                    <a href="https://highways.dot.gov/fed-aid-essentials/videos/project-development/design-project-geometric-design-requirements" target="_blank" class="source-link">• FHWA Geometric Design</a>
                    <a href="https://global.iccsafe.org/international-codes-and-standards/" target="_blank" class="source-link">• ICC I-Codes</a>
                    <a href="https://www.asce.org/publications-and-news/codes-and-standards" target="_blank" class="source-link">• ASCE Standards</a>
                    <a href="https://www.asme.org/codes-standards" target="_blank" class="source-link">• ASME Codes</a>
                    <a href="https://www.fhwa.dot.gov/programadmin/121205.cfm" target="_blank" class="source-link">• Brooks Act</a>
                    <a href="https://www.acquisition.gov/far/subpart-36.6" target="_blank" class="source-link">• FAR Subpart 36.6</a>
                    <a href="https://www.gsa.gov/real-estate/design-and-construction/facilities-standards-for-the-public-buildings-service" target="_blank" class="source-link">• GSA Facilities Standards</a>
                    <a href="https://www.congress.gov/crs-product/R47666" target="_blank" class="source-link">• Congressional Research</a>
                    <a href="https://www.ansi.org" target="_blank" class="source-link">• ANSI</a>
                    <a href="https://www.astm.org" target="_blank" class="source-link">• ASTM International</a>
                    <a href="https://store.astm.org/products-services/standards-and-publications/standards/construction-standards.html" target="_blank" class="source-link">• ASTM Construction</a>
                    <a href="https://www.nfpa.org/codes-and-standards" target="_blank" class="source-link">• NFPA Codes</a>
                    <a href="https://codesonline.nfpa.org" target="_blank" class="source-link">• NFPA Online</a>
                    <a href="https://www.apwa.org/resources/about-public-works/" target="_blank" class="source-link">• APWA</a>
                    <a href="https://www.nist.gov" target="_blank" class="source-link">• NIST</a>
                    <a href="https://www.epa.gov/sites/default/files/2015-10/documents/myerguide.pdf" target="_blank" class="source-link">• EPA MYER Guide</a>
                    <a href="https://www.cem.va.gov/pdf/fedreqs.pdf" target="_blank" class="source-link">• Federal Environmental Reqs</a>
                </div>
                <p style="margin-top: 15px; color: #666; font-size: 0.9em;">
                    Plus 102 state-specific DOT and professional licensing sources
                </p>
            </div>
        </div>
    </div>

    <script>
        let sessionId = null;

        // Load configuration
        async function loadConfiguration() {
            try {
                const rolesResponse = await fetch('/roles');
                const roles = await rolesResponse.json();
                const roleSelect = document.getElementById('roleSelect');
                roleSelect.innerHTML = roles.map(role => 
                    `<option value="${role.id}">${role.name}</option>`
                ).join('');

                const deptsResponse = await fetch('/departments');
                const depts = await deptsResponse.json();
                const deptSelect = document.getElementById('departmentSelect');
                deptSelect.innerHTML = '<option value="">Select Department</option>' +
                    depts.map(dept => 
                        `<option value="${dept.id}">${dept.name}</option>`
                    ).join('');
            } catch (error) {
                console.error('Error loading configuration:', error);
            }
        }

        // Drag and drop
        const uploadZone = document.getElementById('uploadZone');

        uploadZone.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                handleFile(file);
            }
        }

        async function handleFile(file) {
            if (!file.name.endsWith('.pdf')) {
                showAlert('Please upload a PDF file', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            showAlert('Uploading and processing document...', 'info');

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    sessionId = data.session_id;
                    showAlert(`✅ ${data.message}`, 'success');
                    document.getElementById('responseSection').style.display = 'block';
                    
                    // Generate temporary session ID for custom URLs
                    if (!sessionId) {
                        sessionId = 'temp_' + Date.now();
                    }
                    loadCustomUrls();
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error uploading file: ${error.message}`, 'error');
            }
        }

        async function submitQuery() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) {
                showAlert('Please enter a question', 'error');
                return;
            }

            const role = document.getElementById('roleSelect').value;
            const department = document.getElementById('departmentSelect').value;

            // Generate temporary session ID if none exists
            if (!sessionId) {
                sessionId = 'temp_' + Date.now();
            }

            showAlert('Processing your question...', 'info');

            try {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        query: query,
                        role: role,
                        department: department || null
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    document.getElementById('responseBox').textContent = data.answer;
                    document.getElementById('responseSection').style.display = 'block';
                    showAlert('✅ Response generated', 'success');
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        function handleQueryKeyPress(event) {
            if (event.key === 'Enter') {
                submitQuery();
            }
        }

        async function addCustomUrl() {
            const urlInput = document.getElementById('customUrlInput');
            const url = urlInput.value.trim();

            if (!url) {
                showAlert('Please enter a URL', 'error');
                return;
            }

            // Generate temporary session ID if none exists
            if (!sessionId) {
                sessionId = 'temp_' + Date.now();
            }

            try {
                const response = await fetch('/custom-url/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        url: url
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert('✅ URL added successfully', 'success');
                    urlInput.value = '';
                    loadCustomUrls();
                } else {
                    showAlert(`Error: ${data.detail}`, 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        async function loadCustomUrls() {
            if (!sessionId) return;

            try {
                const response = await fetch(`/custom-url/list/${sessionId}`);
                const data = await response.json();

                const listDiv = document.getElementById('customUrlList');
                if (data.custom_urls.length === 0) {
                    listDiv.innerHTML = '<p style="color: #666; font-size: 0.9em; margin-top: 10px;">No custom URLs added yet</p>';
                } else {
                    listDiv.innerHTML = data.custom_urls.map(url => `
                        <div class="url-item">
                            <span>${url}</span>
                            <button class="btn-remove" onclick="removeCustomUrl('${url}')">Remove</button>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Error loading custom URLs:', error);
            }
        }

        async function removeCustomUrl(url) {
            try {
                const response = await fetch('/custom-url/remove', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        url: url
                    })
                });

                if (response.ok) {
                    showAlert('✅ URL removed', 'success');
                    loadCustomUrls();
                } else {
                    showAlert('Error removing URL', 'error');
                }
            } catch (error) {
                showAlert(`Error: ${error.message}`, 'error');
            }
        }

        function showAlert(message, type) {
            const alertBox = document.getElementById('alertBox');
            alertBox.textContent = message;
            alertBox.className = `alert alert-${type} show`;

            if (type === 'success') {
                setTimeout(() => {
                    alertBox.classList.remove('show');
                }, 5000);
            }
        }

        function toggleFooter() {
            const content = document.getElementById('footerContent');
            const arrow = document.getElementById('footerArrow');
            content.classList.toggle('show');
            arrow.classList.toggle('expanded');
        }

        // Initialize
        loadConfiguration();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    return HTML_TEMPLATE

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
