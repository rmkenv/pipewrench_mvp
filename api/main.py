# app_combined.py

"""
PipeWrench AI - Municipal DPW Knowledge Capture System (Single-file build)
FastAPI application with Vercel compatibility.

"""

from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic, APIError
import os
from datetime import datetime
from typing import Optional, Dict, List
import re
from urllib.parse import urlparse
import requests
import logging
from vercel_fastapi import VercelFastAPI  # For Vercel compatibility
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# URL WHITELIST CONFIGURATION (from url_whitelist_config.py)
# ============================================================================
CUSTOM_URLS_FILE = os.path.join(os.path.dirname(__file__), "custom_whitelist.json")

# Base whitelisted URLs (federal and state sources)
BASE_WHITELISTED_URLS = [
    {"url": "https://www.acquisition.gov/far/part-36", "include_children": True},
    {"url": "https://highways.dot.gov/federal-lands/specs", "include_children": True},
    {"url": "https://www.osha.gov/laws-regs/regulations/standardnumber/1926", "include_children": True},
    {"url": "https://www.osha.gov/construction", "include_children": True},
    {"url": "https://www.epa.gov/eg/construction-and-development-effluent-guidelines", "include_children": True},
    {"url": "https://www.epa.gov/laws-regments", "include_children": True},
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
    {"url": "https://www.ringpower.com/media/oujnpuga/caterpillarperfhandbook_ed50.pdf", "include_children": False},
]

URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

def _load_custom_urls() -> List[Dict[str, any]]:
    try:
        if os.path.exists(CUSTOM_URLS_FILE):
            with open(CUSTOM_URLS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading custom URLs: {e}")
    return []

def _save_custom_urls(custom_urls: List[Dict[str, any]]) -> bool:
    try:
        with open(CUSTOM_URLS_FILE, 'w') as f:
            json.dump(custom_urls, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving custom URLs: {e}")
        return False

def _get_all_whitelisted_urls() -> List[Dict[str, any]]:
    return BASE_WHITELISTED_URLS + _load_custom_urls()

def get_total_whitelisted_urls() -> int:
    return len(_get_all_whitelisted_urls())

def get_whitelisted_sources() -> List[Dict[str, str]]:
    return _get_all_whitelisted_urls()

def get_whitelisted_domains() -> set:
    all_urls = _get_all_whitelisted_urls()
    domains = set()
    for entry in all_urls:
        parsed = urlparse(entry["url"])
        domains.add(parsed.netloc)
    return domains

def is_url_whitelisted(url: str) -> bool:
    if not url:
        return False
    all_urls = _get_all_whitelisted_urls()
    parsed_url = urlparse(url)
    url_domain_path = f"{parsed_url.netloc}{parsed_url.path}".rstrip('/')
    for whitelist_entry in all_urls:
        parsed_whitelist = urlparse(whitelist_entry["url"])
        whitelist_domain_path = f"{parsed_whitelist.netloc}{parsed_whitelist.path}".rstrip('/')
        if url_domain_path == whitelist_domain_path:
            return True
        if whitelist_entry.get("include_children", False) and url_domain_path.startswith(whitelist_domain_path):
            return True
    return False

def add_custom_url(url: str, include_children: bool = True, description: str = "") -> Dict[str, any]:
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"success": False, "message": "Invalid URL format"}
    except Exception as e:
        return {"success": False, "message": f"Invalid URL: {str(e)}"}

    custom_urls = _load_custom_urls()
    for entry in custom_urls:
        if entry["url"] == url:
            return {"success": False, "message": "URL already in custom whitelist"}
    for entry in BASE_WHITELISTED_URLS:
        if entry["url"] == url:
            return {"success": False, "message": "URL already in base whitelist"}

    new_entry = {
        "url": url,
        "include_children": include_children,
        "description": description,
        "added_date": datetime.now().isoformat()
    }
    custom_urls.append(new_entry)
    if _save_custom_urls(custom_urls):
        return {"success": True, "message": "URL added successfully"}
    else:
        return {"success": False, "message": "Failed to save custom URL"}

def remove_custom_url(url: str) -> Dict[str, any]:
    custom_urls = _load_custom_urls()
    original_length = len(custom_urls)
    custom_urls = [entry for entry in custom_urls if entry["url"] != url]
    if len(custom_urls) == original_length:
        return {"success": False, "message": "URL not found in custom whitelist"}
    if _save_custom_urls(custom_urls):
        return {"success": True, "message": "URL removed successfully"}
    else:
        return {"success": False, "message": "Failed to save changes"}

def get_custom_urls() -> List[Dict[str, any]]:
    return _load_custom_urls()

logger.info("✅ Whitelist configuration loaded")

# ============================================================================
# JOB ROLES CONFIGURATION (from job_roles_config.py)
# ============================================================================
JOB_ROLES = {
    "director": {
        "title": "Department Director",
        "context": """You are answering for a Department Director who needs high-level strategic 
information, budget considerations, policy implications, and leadership guidance. Focus on 
compliance, safety standards, and department-wide best practices."""
    },
    "operations_manager": {
        "title": "Operations Manager",
        "context": """You are answering for an Operations Manager who oversees day-to-day activities. 
Focus on workflow optimization, resource allocation, scheduling, coordination between teams, 
and operational efficiency."""
    },
    "maintenance_supervisor": {
        "title": "Maintenance Supervisor",
        "context": """You are answering for a Maintenance Supervisor who manages field crews and 
maintenance activities. Focus on work orders, crew management, equipment maintenance schedules, 
safety procedures, and quality control."""
    },
    "field_technician": {
        "title": "Field Technician",
        "context": """You are answering for a Field Technician who performs hands-on work. Focus on 
step-by-step procedures, safety protocols, equipment operation, troubleshooting, and 
field-level best practices."""
    },
    "equipment_operator": {
        "title": "Equipment Operator",
        "context": """You are answering for an Equipment Operator who operates heavy machinery and 
vehicles. Focus on equipment operation procedures, pre-operation inspections, safety requirements, 
and equipment-specific guidelines."""
    },
    "safety_officer": {
        "title": "Safety Officer",
        "context": """You are answering for a Safety Officer responsible for workplace safety. Focus on 
OSHA regulations, safety protocols, hazard identification, incident prevention, PPE requirements, 
and safety training."""
    },
    "project_manager": {
        "title": "Project Manager",
        "context": """You are answering for a Project Manager overseeing capital projects. Focus on 
project planning, contractor coordination, specifications, quality assurance, timeline management, 
and documentation."""
    },
    "administrative_staff": {
        "title": "Administrative Staff",
        "context": """You are answering for Administrative Staff who support operations. Focus on 
documentation, record-keeping, permit processes, public inquiries, reporting, and administrative 
procedures."""
    }
}

def get_role_context(role_key: Optional[str]) -> str:
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["context"]
    return ""

def get_role_title(role_key: Optional[str]) -> str:
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["title"]
    return ""

def get_all_roles() -> List[str]:
    return list(JOB_ROLES.keys())

# ============================================================================
# DEPARTMENT PROMPTS CONFIG (from department_prompts_config.py)
# ============================================================================
SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in municipal Department of Public Works (DPW) operations and institutional knowledge capture. Your primary function is to help preserve and transfer critical operational knowledge from experienced personnel.

CRITICAL RULES - NEVER VIOLATE:
1. ONLY cite sources from the approved URL whitelist
2. ALWAYS include the specific URL for each citation
3. If information is not available from whitelisted sources, explicitly state: "This information cannot be verified from approved sources."
4. Use APA 7th edition citation format
5. Never fabricate, guess, or hallucinate information
6. When uncertain, say "I don't know" or "This requires verification"
7. Distinguish clearly between:
   - Verified facts (with citations)
   - General best practices (clearly labeled as such)
   - Information requiring subject matter expert review

CITATION FORMAT:
- In-text: (Source Name, Year)
- Reference list: Author/Organization. (Year). Title. URL

Your responses should be:
- Accurate and verifiable
- Practical and actionable
- Safety-focused
- Compliant with federal, state, and local regulations
"""

DEPARTMENT_CONTEXTS = {
    "general_public_works": {
        "name": "General Public Works",
        "context": """
You are assisting general public works personnel with broad municipal infrastructure questions.

FOCUS AREAS:
- Cross-departmental coordination
- General municipal operations
- Infrastructure planning and maintenance
- Budget and resource allocation
- Public communication and community relations
- Emergency response coordination

KNOWLEDGE DOMAINS:
- Municipal government structure
- Public works administration
- Project management
- Regulatory compliance overview
- Interdepartmental workflows
"""
    },
    "water_distribution": {
        "name": "Water Distribution",
        "context": """
You are assisting water distribution system operators and technicians.

FOCUS AREAS:
- Water main installation, maintenance, and repair
- Valve operation and maintenance
- Hydrant maintenance and flow testing
- Leak detection and repair
- Water quality monitoring in distribution
        - Cross-connection control
- Meter installation and maintenance
- System hydraulics and pressure management

CRITICAL SAFETY TOPICS:
- Confined space entry
- Trench safety and shoring
- Chlorine handling
- Backflow prevention
- Waterborne pathogen protection

REGULATORY FRAMEWORK:
- Safe Drinking Water Act (SDWA)
- State drinking water regulations
- OSHA 1926 (Construction) and 1910 (General Industry)
- AWWA standards
- Local water utility regulations
"""
    },
    "wastewater_collection": {
        "name": "Wastewater Collection",
        "context": """
You are assisting wastewater collection system operators and maintenance personnel.

FOCUS AREAS:
- Sewer main maintenance and repair
- Lift station operation and maintenance
- CCTV inspection and assessment
- Root control and chemical treatment
- Grease trap inspection and enforcement
- Inflow/infiltration (I&I) reduction
- Manhole inspection and rehabilitation
- Emergency response (SSOs)

CRITICAL SAFETY TOPICS:
- Confined space entry (permit-required)
- H2S monitoring and protection
- Electrical safety at lift stations
- Traffic control and excavation safety
- Biological hazards

REGULATORY FRAMEWORK:
- Clean Water Act
- NPDES permits
- SSO reporting requirements
- OSHA 1910.146 (Confined Spaces)
- State wastewater regulations
"""
    },
    "wastewater_treatment": {
        "name": "Wastewater Treatment",
        "context": """
You are assisting wastewater treatment plant operators and laboratory technicians.

FOCUS AREAS:
- Treatment process optimization
- SCADA and process control
- Laboratory testing and QA/QC
- Biosolids management
- Chemical feed systems
- Equipment maintenance (pumps, blowers, clarifiers)
- Permit compliance and reporting
- Energy efficiency

CRITICAL SAFETY TOPICS:
- Chlorine gas handling and safety
- Confined space entry
- Electrical safety and LOTO
- Chemical handling (polymers, caustic, etc.)
- Biological hazards

REGULATORY FRAMEWORK:
- Clean Water Act
- NPDES discharge permits
- 40 CFR Part 503 (Biosolids)
- State operator certification requirements
- OSHA chemical safety standards
"""
    },
    "water_treatment": {
        "name": "Water Treatment",
        "context": """
You are assisting water treatment plant operators and laboratory technicians.

FOCUS AREAS:
- Treatment process optimization (coagulation, filtration, disinfection)
- SCADA and process control
- Laboratory testing and QA/QC
- Chemical feed systems
- Filter operation and backwashing
- Residuals management
- Regulatory compliance and reporting
- Source water protection

CRITICAL SAFETY TOPICS:
- Chlorine gas handling and safety
- Confined space entry
- Electrical safety and LOTO
- Chemical handling (alum, polymers, fluoride, etc.)
- Waterborne pathogen protection

REGULATORY FRAMEWORK:
- Safe Drinking Water Act
- Surface Water Treatment Rule
- Total Coliform Rule / Revised Total Coliform Rule
- Lead and Copper Rule
- State operator certification requirements
- OSHA chemical safety standards
"""
    },
    "streets_roads": {
        "name": "Streets & Roads",
        "context": """
You are assisting street and road maintenance personnel.

FOCUS AREAS:
- Asphalt paving and patching
- Crack sealing and surface treatments
- Pothole repair
- Pavement management systems
- Striping and signage
- Winter maintenance (snow/ice control)
- Drainage maintenance
- Traffic control during operations

CRITICAL SAFETY TOPICS:
- Work zone traffic control (MUTCD)
- Hot asphalt handling
- Equipment operation safety
- Heat stress management
- Chemical handling (deicers, herbicides)

REGULATORY FRAMEWORK:
- MUTCD (Manual on Uniform Traffic Control Devices)
- OSHA construction standards
- State DOT specifications
- ADA accessibility requirements
- Stormwater regulations
"""
    },
    "stormwater": {
        "name": "Stormwater Management",
        "context": """
You are assisting stormwater management and drainage personnel.

FOCUS AREAS:
- Storm drain system maintenance
- Catch basin cleaning
- Culvert inspection and repair
- Detention/retention pond maintenance
- Green infrastructure (bioswales, rain gardens)
- Erosion and sediment control
- Flood response
- MS4 permit compliance

CRITICAL SAFETY TOPICS:
- Confined space entry
- Swift water hazards
- Traffic control
- Vector control (mosquitoes)
- Chemical handling (herbicides)

REGULATORY FRAMEWORK:
- Clean Water Act
- MS4 permits (Municipal Separate Storm Sewer System)
- NPDES stormwater regulations
- State stormwater management requirements
- Local drainage ordinances
"""
    },
    "fleet_maintenance": {
        "name": "Fleet Maintenance",
        "context": """
You are assisting municipal fleet maintenance technicians and managers.

FOCUS AREAS:
- Heavy equipment maintenance (loaders, excavators, dump trucks)
- Light vehicle maintenance
- Preventive maintenance programs
- Diagnostic procedures
- Hydraulic systems
- Diesel engine repair
- Welding and fabrication
- Parts inventory management
- Fleet management software

CRITICAL SAFETY TOPICS:
- LOTO (Lockout/Tagout)
- Hydraulic system safety
- Welding safety
- Battery handling
- Compressed gas safety
- Shop ventilation

REGULATORY FRAMEWORK:
- OSHA general industry standards
- EPA emissions regulations
- DOT vehicle inspection requirements
- Hazardous waste management (used oil, antifreeze)
"""
    },
    "parks_grounds": {
        "name": "Parks & Grounds",
        "context": """
You are assisting parks and grounds maintenance personnel.

FOCUS AREAS:
- Turf management and mowing
- Tree care and removal
- Landscape maintenance
- Irrigation systems
- Playground inspection and maintenance
- Athletic field maintenance
- Pesticide/herbicide application
- Equipment operation

CRITICAL SAFETY TOPICS:
- Chainsaw and chipper safety
- Pesticide safety and licensing
- Heat stress management
- Equipment operation safety
- Playground safety standards

REGULATORY FRAMEWORK:
- OSHA standards
- State pesticide applicator licensing
- CPSC Playground safety guidelines
- ADA accessibility requirements
- Tree protection ordinances
"""
    },
    "facilities_maintenance": {
        "name": "Facilities Maintenance",
        "context": """
You are assisting municipal facilities maintenance personnel.

FOCUS AREAS:
- HVAC systems
- Electrical systems
- Plumbing systems
- Building automation systems
- Preventive maintenance
- Energy management
- ADA compliance
- Emergency systems (generators, fire suppression)

CRITICAL SAFETY TOPICS:
- Electrical safety and LOTO
- Refrigerant handling
- Asbestos awareness
- Lead paint awareness
- Confined space entry
- Fall protection

REGULATORY FRAMEWORK:
- OSHA general industry standards
- Building codes (IBC, NEC, IPC)
- EPA refrigerant regulations
- ADA accessibility requirements
- Fire and life safety codes
"""
    },
    "traffic_signals": {
        "name": "Traffic Signals & ITS",
        "context": """
You are assisting traffic signal technicians and ITS specialists.

FOCUS AREAS:
- Signal timing and coordination
- Controller programming
- Detector installation and maintenance
- LED signal maintenance
- Fiber optic networks
- ITS systems
- Emergency vehicle preemption
- Pedestrian signals and ADA compliance

CRITICAL SAFETY TOPICS:
- Electrical safety and high voltage
- Work zone traffic control
- Aerial lift safety
- Confined space (pull boxes, vaults)

REGULATORY FRAMEWORK:
- MUTCD
- NEMA standards
- NEC (National Electrical Code)
- ADA accessibility requirements
- State traffic engineering standards
"""
    },
    "engineering": {
        "name": "Engineering & Capital Projects",
        "context": """
You are assisting municipal engineers and capital project managers.

FOCUS AREAS:
- Project design and specifications
- Construction management
- Contract administration
- Plan review and permitting
- Asset management
- GIS and mapping
- Grant writing and administration
- Cost estimating

CRITICAL SAFETY TOPICS:
- Construction site safety
- Trench safety
- Traffic control plans
- Utility coordination

REGULATORY FRAMEWORK:
- State engineering licensure requirements
- Federal procurement regulations (if using federal funds)
- ADA accessibility requirements
- Environmental regulations (NEPA, wetlands, etc.)
- State and local building codes
"""
    },
    "utilities_administration": {
        "name": "Utilities Administration",
        "context": """
You are assisting utility billing, customer service, and administrative personnel.

FOCUS AREAS:
- Utility billing systems
- Customer service
- Meter reading (AMR/AMI)
- Rate structures
- Delinquent account management
- Service connections and disconnections
- Regulatory reporting
- Public communication

CRITICAL SAFETY TOPICS:
- Customer interaction protocols
- Data security and privacy
- Field safety for meter readers

REGULATORY FRAMEWORK:
- State utility regulations
- Consumer protection laws
- Data privacy regulations
- Public records laws
"""
    },
    "safety_compliance": {
        "name": "Safety & Compliance",
        "context": """
You are assisting safety officers and compliance coordinators.

FOCUS AREAS:
- Safety program development
- Incident investigation
- Training coordination
- PPE management
- Regulatory compliance
- Safety audits and inspections
- Emergency response planning
- Workers' compensation management

CRITICAL SAFETY TOPICS:
- All OSHA standards applicable to municipal operations
- Hazard communication
- Confined space programs
- LOTO programs
- Respiratory protection
- Fall protection

REGULATORY FRAMEWORK:
- OSHA standards (1910 and 1926)
- EPA environmental regulations
- State safety and health regulations
- DOT regulations (if applicable)
- NFPA standards
"""
    }
}

def get_department_prompt(department_key: str) -> str:
    dept = DEPARTMENT_CONTEXTS.get(department_key, DEPARTMENT_CONTEXTS["general_public_works"])
    return SYSTEM_INSTRUCTION + "\n\n" + dept["context"]

def get_department_list() -> list:
    return [{"value": key, "name": dept["name"]} for key, dept in DEPARTMENT_CONTEXTS.items()]

def get_department_name(department_key: str) -> str:
    dept = DEPARTMENT_CONTEXTS.get(department_key, DEPARTMENT_CONTEXTS["general_public_works"])
    return dept["name"]

# ============================================================================
# ENV VARS, CLIENTS
# ============================================================================
DRAWING_PROCESSING_API_URL = os.getenv("DRAWING_PROCESSING_API_URL", "http://localhost:8001/parse")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ============================================================================
# HELPERS
# ============================================================================
def build_system_prompt(department_key: str, role_key: Optional[str]) -> str:
    base = get_department_prompt(department_key)
    role_part = ""
    if role_key:
        title = get_role_title(role_key)
        ctx = get_role_context(role_key)
        if title or ctx:
            role_part = f"\n\nROLE CONTEXT:\n- Title: {title or role_key}\n- Guidance:\n{ctx}"
    whitelist_notice = (
        f"\n\nURL RESTRICTIONS:\n"
        f"- Only cite and reference sources from approved whitelist\n"
        f"- Include the specific URL for each citation\n"
        f"- If info is not in whitelist, clearly state that it cannot be verified from approved sources\n"
        f"- All child pages of whitelisted URLs are permitted\n"
        f"- Total Whitelisted URLs: {get_total_whitelisted_urls()}\n"
        f"- Approved Domains: {', '.join(sorted(list(get_whitelisted_domains()))[:25])}"
        + ("..." if len(get_whitelisted_domains()) > 25 else "")
    )
    return base + role_part + whitelist_notice

def extract_text_from_pdf(content: bytes) -> str:
    # Placeholder for real PDF text extraction
    return "Sample extracted text from PDF"

def generate_llm_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    if not anthropic_client:
        raise HTTPException(status_code=500, detail="Anthropic client not configured")
    try:
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"User query: {query}\nDocument context: {context}"}],
        )
        if message.content and len(message.content) > 0:
            return message.content[0].text
        raise HTTPException(status_code=500, detail="Empty response from LLM")
    except APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM response: {str(e)}")

def generate_mock_response(query: str, context: str, system_prompt: str, has_document: bool) -> str:
    return f"Mock response for: {query}\n\nContext: {context[:100]}...\nSystem prompt: {system_prompt[:50]}..."

def enforce_whitelist_on_text(text: str) -> str:
    bad_urls = []
    for url in set(URL_REGEX.findall(text or "")):
        url_clean = url.rstrip('.,);]')
        if not is_url_whitelisted(url_clean):
            bad_urls.append(url_clean)
    if not bad_urls:
        return text
    note = (
        "\n\n[COMPLIANCE NOTICE]\n"
        "The following URLs are not in the approved whitelist and must not be cited:\n"
        + "\n".join(f"- {u}" for u in sorted(bad_urls))
        + "\n\nPlease revise citations to use only approved sources."
    )
    return text + note

def sanitize_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def create_session(self, session_id: str, data: Dict) -> None:
        self.sessions[session_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "documents": [],
            "questions": [],
        }

    def update_session(self, session_id: str, updates: Dict) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)

session_manager = SessionManager()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    query: str
    role: Optional[str] = None
    department: Optional[str] = "general_public_works"

class UploadResponse(BaseModel):
    session_id: str
    filename: str
    pages: int
    message: str
    is_asbuilt: bool = False

class CustomURLRequest(BaseModel):
    session_id: str
    url: str

class ErrorResponse(BaseModel):
    error: str
    detail: str

class SystemInfoResponse(BaseModel):
    total_whitelisted_urls: int
    whitelisted_domains: List[str]
    roles: List[str]
    departments: List[str]
    config: Dict

# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.get("/")
async def root():
    return {"message": "PipeWrench AI API", "status": "running"}

@app.get("/api/departments")
async def api_get_departments():
    try:
        return {"departments": get_department_list()}
    except Exception as e:
        logger.error(f"Failed to get departments: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve departments")

@app.get("/api/roles")
async def list_roles():
    try:
        roles = [{"value": key, "title": get_role_title(key)} for key in get_all_roles()]
        return {"roles": roles}
    except Exception as e:
        logger.error(f"Failed to get roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve roles")

@app.get("/api/system")
async def system_info():
    try:
        return SystemInfoResponse(
            total_whitelisted_urls=get_total_whitelisted_urls(),
            whitelisted_domains=sorted(list(get_whitelisted_domains())),
            roles=get_all_roles(),
            departments=[d["value"] for d in get_department_list()],
            config={"version": "1.0"},
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")

@app.get("/api/whitelist")
async def whitelist_overview():
    try:
        all_urls = get_whitelisted_sources()
        sample_urls = [entry["url"] for entry in all_urls[:50]]
        return {
            "count": get_total_whitelisted_urls(),
            "domains": sorted(list(get_whitelisted_domains())),
            "sample": sample_urls,
        }
    except Exception as e:
        logger.error(f"Failed to get whitelist: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve whitelist")

def extract_text_from_asbuilt_pdf(file: UploadFile) -> str:
    try:
        file.file.seek(0)
        response = requests.post(
            DRAWING_PROCESSING_API_URL,
            files={"file": (file.filename, file.file, file.content_type)},
            data={"ocr_method": "textract"},
            timeout=30,
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Error processing as-built PDF")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error calling drawing processing API: {e}")
        raise HTTPException(status_code=500, detail="Drawing processing service unavailable")

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    is_asbuilt: bool = False,
    session_id: Optional[str] = None,
    department: str = "general_public_works",
    role: Optional[str] = None,
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if is_asbuilt:
            text = extract_text_from_asbuilt_pdf(file)
        else:
            content = await file.read()
            text = extract_text_from_pdf(content)
        page_count = max(1, len(text) // 2500)
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

    session_data = {
        "filename": file.filename,
        "text": text,
        "uploaded_at": datetime.now().isoformat(),
        "is_asbuilt": is_asbuilt,
        "department": department,
        "role": role,
    }

    if session_manager.get_session(session_id):
        session_manager.update_session(session_id, session_data)
    else:
        session_manager.create_session(session_id, session_data)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        pages=page_count,
        message=f"Successfully uploaded {file.filename} ({page_count} pages)",
        is_asbuilt=is_asbuilt,
    )

@app.post("/query")
async def query_documents(request: QueryRequest):
    document_text = ""
    has_document = False

    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session:
            document_text = session.get("text", "")
            has_document = bool(document_text)

    dept_key = request.department or "general_public_works"
    system_prompt = build_system_prompt(dept_key, request.role)

    try:
        if has_document:
            response = generate_llm_response(request.query, document_text, system_prompt, has_document)
        else:
            response = generate_mock_response(request.query, document_text, system_prompt, has_document)

        response = enforce_whitelist_on_text(response)

        if request.session_id:
            session = session_manager.get_session(request.session_id)
            if session is not None:
                session.setdefault("questions", []).append(
                    {
                        "question": request.query,
                        "answer": response,
                        "timestamp": datetime.now().isoformat(),
                        "role": request.role,
                        "department": dept_key,
                    }
                )

        return {"answer": response, "sources": ["whitelisted_urls"] + (["uploaded_document"] if has_document else [])}
    except HTTPException:
        raise
    except APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=502, detail="AI service error. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error in query: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

@app.post("/api/document/upload")
async def api_upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    department: str = Form("general_public_works"),
    role: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
):
    logger.info(f"Document upload - File: {file.filename}, Session: {session_id}")
    session = session_manager.get_session(session_id)
    if session is None:
        session_manager.create_session(session_id, {})

    try:
        content = await file.read()
        text = extract_text_from_pdf(content)
        session_manager.update_session(
            session_id,
            {
                "filename": file.filename,
                "text": text,
                "uploaded_at": datetime.now().isoformat(),
                "department": department,
                "role": role,
            },
        )
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": "Document uploaded successfully",
            "pages": max(1, len(text) // 2500),
        }
    except Exception as e:
        logger.error(f"Error in API document upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")

@app.post("/api/report/generate")
async def generate_report(session_id: str = Form(...)):
    logger.info(f"Generating report for session: {session_id}")
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    try:
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PipeWrench AI - Knowledge Capture Report</title>
    <meta charset="UTF-8">
    <style>
    body {{
        font-family: Arial, sans-serif;
        margin: 40px;
        line-height: 1.6;
        background: #f5f5f5;
    }}
    .container {{
        max-width: 900px;
        margin: 0 auto;
        background: white;
        padding: 40px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    h1 {{
        color: #1e40af;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 10px;
    }}
    h2 {{
        color: #3b82f6;
        margin-top: 30px;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 5px;
    }}
    .question {{
        background: #eff6ff;
        padding: 15px;
        margin: 20px 0;
        border-left: 4px solid #3b82f6;
        border-radius: 4px;
    }}
    .answer {{
        margin: 10px 0;
        white-space: pre-wrap;
        padding: 10px;
        background: white;
    }}
    .document {{
        background: #fef3c7;
        padding: 15px;
        margin: 20px 0;
        border-left: 4px solid #f59e0b;
        border-radius: 4px;
    }}
    .metadata {{
        color: #6b7280;
        font-size: 0.9em;
        font-style: italic;
    }}
    .footer {{
        margin-top: 40px;
        padding-top: 20px;
        border-top: 2px solid #e5e7eb;
        text-align: center;
        color: #6b7280;
    }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Municipal DPW Knowledge Capture System</h1>
        <p>AI-Powered Infrastructure Knowledge Base with Source Verification</p>
        <h2>📄 Uploaded Document</h2>
"""
        if session.get("filename"):
            html_report += f"""
        <div class="document">
            <strong>Filename:</strong> {sanitize_html(session['filename'])}<br>
            <strong>Department:</strong> {sanitize_html(session.get('department', 'N/A'))}<br>
            <strong>Role:</strong> {sanitize_html(session.get('role', 'N/A'))}<br>
            <div class="metadata">Uploaded: {session.get('uploaded_at', 'Unknown')}</div>
        </div>
"""
        html_report += f"""
        <h2>💬 Questions & Answers</h2>
"""
        for i, qa in enumerate(session.get("questions", []), 1):
            role_display = f" • {sanitize_html(qa.get('role', ''))}" if qa.get('role') else ""
            html_report += f"""
        <div class="question">
            <strong>Q{i} ({sanitize_html(qa.get('department', 'General'))}{role_display}):</strong> {sanitize_html(qa.get('question', ''))}
            <div class="answer">
                <strong>Answer:</strong><br>
                {sanitize_html(qa.get('answer', ''))}
            </div>
            <p class="metadata">Asked: {qa.get('timestamp', 'Unknown')}</p>
        </div>
"""
        html_report += """
        <div class="footer">
            <p><strong>PipeWrench AI</strong> - Municipal DPW Knowledge Capture System</p>
            <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </div>
</body>
</html>
"""
        return HTMLResponse(content=html_report)
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report. Please try again.")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please try again later."},
    )

# For Vercel
handler = VercelFastAPI(app)
