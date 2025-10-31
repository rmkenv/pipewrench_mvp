import os

# Generate updated url_whitelist_config.py with custom URL support

code = '''"""
URL Whitelist Configuration for PipeWrench AI
Contains all approved reference sources for municipal DPW compliance
Plus support for custom organization URLs
"""

from urllib.parse import urlparse
from typing import List, Dict
import json
import os

# Base whitelisted URLs (federal and state sources)
BASE_WHITELISTED_URLS = [
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

# Path to custom URLs file
CUSTOM_URLS_FILE = os.path.join(os.path.dirname(__file__), "custom_whitelist.json")

def load_custom_urls() -> List[Dict[str, any]]:
    """Load custom URLs from JSON file"""
    try:
        if os.path.exists(CUSTOM_URLS_FILE):
            with open(CUSTOM_URLS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading custom URLs: {e}")
    return []

def save_custom_urls(custom_urls: List[Dict[str, any]]) -> bool:
    """Save custom URLs to JSON file"""
    try:
        with open(CUSTOM_URLS_FILE, 'w') as f:
            json.dump(custom_urls, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving custom URLs: {e}")
        return False

def get_all_whitelisted_urls() -> List[Dict[str, any]]:
    """Get combined list of base + custom URLs"""
    custom_urls = load_custom_urls()
    return BASE_WHITELISTED_URLS + custom_urls

# Dynamic WHITELISTED_URLS that includes custom URLs
WHITELISTED_URLS = get_all_whitelisted_urls()

def add_custom_url(url: str, include_children: bool = True, description: str = "") -> Dict[str, any]:
    """
    Add a custom URL to the whitelist
    
    Args:
        url: The URL to add
        include_children: Whether to include child pages
        description: Optional description of the source
        
    Returns:
        Dictionary with success status and message
    """
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"success": False, "message": "Invalid URL format"}
    except Exception as e:
        return {"success": False, "message": f"Invalid URL: {str(e)}"}
    
    # Load existing custom URLs
    custom_urls = load_custom_urls()
    
    # Check if URL already exists
    for entry in custom_urls:
        if entry["url"] == url:
            return {"success": False, "message": "URL already in custom whitelist"}
    
    # Check if URL is in base whitelist
    for entry in BASE_WHITELISTED_URLS:
        if entry["url"] == url:
            return {"success": False, "message": "URL already in base whitelist"}
    
    # Add new URL
    new_entry = {
        "url": url,
        "include_children": include_children,
        "description": description,
        "added_date": None  # Will be set by backend
    }
    
    custom_urls.append(new_entry)
    
    # Save to file
    if save_custom_urls(custom_urls):
        # Refresh the global WHITELISTED_URLS
        global WHITELISTED_URLS
        WHITELISTED_URLS = get_all_whitelisted_urls()
        return {"success": True, "message": "URL added successfully"}
    else:
        return {"success": False, "message": "Failed to save custom URL"}

def remove_custom_url(url: str) -> Dict[str, any]:
    """
    Remove a custom URL from the whitelist
    
    Args:
        url: The URL to remove
        
    Returns:
        Dictionary with success status and message
    """
    custom_urls = load_custom_urls()
    
    # Find and remove the URL
    original_length = len(custom_urls)
    custom_urls = [entry for entry in custom_urls if entry["url"] != url]
    
    if len(custom_urls) == original_length:
        return {"success": False, "message": "URL not found in custom whitelist"}
    
    # Save updated list
    if save_custom_urls(custom_urls):
        # Refresh the global WHITELISTED_URLS
        global WHITELISTED_URLS
        WHITELISTED_URLS = get_all_whitelisted_urls()
        return {"success": True, "message": "URL removed successfully"}
    else:
        return {"success": False, "message": "Failed to save changes"}

def get_custom_urls() -> List[Dict[str, any]]:
    """Get list of custom URLs only"""
    return load_custom_urls()

def is_url_whitelisted(url: str) -> bool:
    """
    Check if a URL is whitelisted
    
    Args:
        url: The URL to check
        
    Returns:
        bool: True if URL is whitelisted, False otherwise
    """
    if not url:
        return False
    
    # Refresh whitelist to include any new custom URLs
    all_urls = get_all_whitelisted_urls()
    
    parsed_url = urlparse(url)
    url_domain_path = f"{parsed_url.netloc}{parsed_url.path}".rstrip('/')
    
    for whitelist_entry in all_urls:
        whitelist_url = whitelist_entry["url"]
        parsed_whitelist = urlparse(whitelist_url)
        whitelist_domain_path = f"{parsed_whitelist.netloc}{parsed_whitelist.path}".rstrip('/')
        
        # Exact match
        if url_domain_path == whitelist_domain_path:
            return True
        
        # Child page match if include_children is True
        if whitelist_entry.get("include_children", False):
            if url_domain_path.startswith(whitelist_domain_path):
                return True
    
    return False

def get_whitelisted_sources() -> List[Dict[str, str]]:
    """
    Get list of all whitelisted sources (base + custom)
    
    Returns:
        List of dictionaries containing URL and metadata
    """
    return get_all_whitelisted_urls()

def get_whitelisted_domains() -> List[str]:
    """
    Get list of unique whitelisted domains
    
    Returns:
        List of domain names
    """
    all_urls = get_all_whitelisted_urls()
    domains = set()
    for entry in all_urls:
        parsed = urlparse(entry["url"])
        domains.add(parsed.netloc)
    return sorted(list(domains))

def validate_citation(citation_url: str) -> Dict[str, any]:
    """
    Validate a citation URL against the whitelist
    
    Args:
        citation_url: The URL to validate
        
    Returns:
        Dictionary with validation results
    """
    is_valid = is_url_whitelisted(citation_url)
    
    return {
        "url": citation_url,
        "is_valid": is_valid,
        "message": "Valid source" if is_valid else "URL not in approved whitelist"
    }
'''

# Save the file in current directory (no outputs folder)
with open('url_whitelist_config.py', 'w') as f:
    f.write(code)

print("✅ Updated url_whitelist_config.py generated!")
print("✅ Now includes custom URL management functions")
print("\n📋 New features:")
print("  - add_custom_url(url, include_children, description)")
print("  - remove_custom_url(url)")
print("  - get_custom_urls()")
print("  - Custom URLs stored in custom_whitelist.json")
print("\n📄 File ready for use!")
