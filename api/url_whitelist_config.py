"""
URL Whitelist Configuration for DPW Knowledge Capture System
Only sources from this whitelist may be cited by the AI
"""

from urllib.parse import urlparse

# Whitelisted URLs with child page inclusion settings
WHITELISTED_URLS = {
    "https://www.acquisition.gov/far/part-36": {"include_children": True},
    "https://highways.dot.gov/federal-lands/specs": {"include_children": True},
    "https://www.osha.gov/laws-regs/regulations/standardnumber/1926": {"include_children": True},
    "https://www.osha.gov/construction": {"include_children": True},
    "https://www.epa.gov/eg/construction-and-development-effluent-guidelines": {"include_children": True},
    "https://www.epa.gov/laws-regulations": {"include_children": True},
    "https://www.epa.gov/sites/default/files/2015-10/documents/myerguide.pdf": {"include_children": True},
    "https://www.cem.va.gov/pdf/fedreqs.pdf": {"include_children": True},
    "https://www.epa.gov/dwreginfo/lead-and-copper-rule": {"include_children": True},
    "https://www.epa.gov/ground-water-and-drinking-water/national-primary-drinking-water-regulations": {"include_children": True},
    "https://www.epa.gov/sdwa": {"include_children": True},
    "https://www.epa.gov/dwreginfo/revised-total-coliform-rule-and-total-coliform-rule": {"include_children": True},
    "https://www.epa.gov/dwreginfo/surface-water-treatment-rules": {"include_children": True},
    "https://www.epa.gov/npdes": {"include_children": True},
    "https://www.epa.gov/npdes/stormwater-discharges-municipal-sources": {"include_children": True},
    "https://www.epa.gov/biosolids": {"include_children": True},
    "https://www.epa.gov/cwa-404": {"include_children": True},
    "https://www.epa.gov/regulatory-information-topic/regulatory-information-topic-water": {"include_children": True},
    "https://www.osha.gov/laws-regs/regulations/standardnumber/1910": {"include_children": True},
    "https://www.osha.gov/confined-spaces": {"include_children": True},
    "https://www.osha.gov/hydrogen-sulfide": {"include_children": True},
    "https://www.osha.gov/chlorine": {"include_children": True},
    "https://www.osha.gov/control-hazardous-energy": {"include_children": True},
    "https://www.osha.gov/heat-exposure": {"include_children": True},
    "https://www.osha.gov/trenching-excavation": {"include_children": True},
    "https://www.osha.gov/fall-protection": {"include_children": True},
    "https://www.osha.gov/respiratory-protection": {"include_children": True},
    "https://www.osha.gov/personal-protective-equipment": {"include_children": True},
    "https://www.osha.gov/hazcom": {"include_children": True},
    "https://mutcd.fhwa.dot.gov/": {"include_children": True},
    "https://mutcd.fhwa.dot.gov/pdfs/2009r1r2/mutcd2009r1r2edition.pdf": {"include_children": True},
    "https://www.fhwa.dot.gov/": {"include_children": True},
    "https://www.fhwa.dot.gov/pavement/": {"include_children": True},
    "https://www.fhwa.dot.gov/bridge/": {"include_children": True},
    "https://www.nhtsa.gov/": {"include_children": True},
    "https://www.fmcsa.dot.gov/": {"include_children": True},
    "https://www.awwa.org/": {"include_children": True},
    "https://www.awwa.org/resources-tools/standards-and-manuals": {"include_children": True},
    "https://www.wef.org/": {"include_children": True},
    "https://www.wef.org/resources/": {"include_children": True},
    "https://www.apwa.net/": {"include_children": True},
    "https://www.apwa.net/Resources": {"include_children": True},
    "https://www.nfpa.org/": {"include_children": True},
    "https://www.nfpa.org/codes-and-standards": {"include_children": True},
    "https://www.astm.org/": {"include_children": True},
    "https://www.astm.org/products-services/standards-and-publications.html": {"include_children": True},
    "https://www.asce.org/": {"include_children": True},
    "https://www.asce.org/publications-and-news/civil-engineering-source/civil-engineering-magazine": {"include_children": True},
    "https://www.iccsafe.org/": {"include_children": True},
    "https://www.iccsafe.org/products-and-services/i-codes/": {"include_children": True},
    "https://www.nfpa.org/codes-and-standards/all-codes-and-standards/list-of-codes-and-standards/detail?code=70": {"include_children": True},
    "https://www.cpsc.gov/": {"include_children": True},
    "https://www.cpsc.gov/safety-education/safety-guides/Playgrounds": {"include_children": True},
    "https://www.ada.gov/": {"include_children": True},
    "https://www.access-board.gov/ada/": {"include_children": True},
    "https://www.access-board.gov/prowag/": {"include_children": True},
    "https://www.fema.gov/": {"include_children": True},
    "https://www.fema.gov/emergency-managers": {"include_children": True},
    "https://www.ready.gov/": {"include_children": True},
    "https://www.nifc.gov/": {"include_children": True},
    "https://www.usgs.gov/": {"include_children": True},
    "https://www.usgs.gov/mission-areas/water-resources": {"include_children": True},
    "https://www.epa.gov/waterutilityresponse": {"include_children": True},
    "https://www.epa.gov/waterresilience": {"include_children": True},
    "https://www.epa.gov/watersecurity": {"include_children": True},
    "https://www.cisa.gov/": {"include_children": True},
    "https://www.cisa.gov/topics/critical-infrastructure-security-and-resilience/critical-infrastructure-sectors/water-and-wastewater-systems-sector": {"include_children": True},
    "https://www.transportation.gov/": {"include_children": True},
    "https://www.transportation.gov/mission/safety": {"include_children": True},
    "https://www.gsa.gov/": {"include_children": True},
    "https://www.gsa.gov/policy-regulations/regulations": {"include_children": True},
    "https://www.sam.gov/": {"include_children": True},
    "https://www.grants.gov/": {"include_children": True},
    "https://www.whitehouse.gov/omb/": {"include_children": True},
    "https://www.ecfr.gov/": {"include_children": True},
    "https://www.govinfo.gov/": {"include_children": True},
    "https://www.regulations.gov/": {"include_children": True},
    "https://www.cdc.gov/": {"include_children": True},
    "https://www.cdc.gov/niosh/": {"include_children": True},
    "https://www.cdc.gov/healthywater/": {"include_children": True},
    "https://www.atsdr.cdc.gov/": {"include_children": True},
    "https://www.epa.gov/indoor-air-quality-iaq": {"include_children": True},
    "https://www.epa.gov/asbestos": {"include_children": True},
    "https://www.epa.gov/lead": {"include_children": True},
    "https://www.epa.gov/mold": {"include_children": True},
    "https://www.epa.gov/radon": {"include_children": True},
    "https://www.epa.gov/pesticides": {"include_children": True},
    "https://www.epa.gov/pesticide-worker-safety": {"include_children": True},
    "https://www.epa.gov/compliance": {"include_children": True},
    "https://www.epa.gov/enforcement": {"include_children": True},
    "https://www.epa.gov/superfund": {"include_children": True},
    "https://www.epa.gov/rcra": {"include_children": True},
    "https://www.epa.gov/hw": {"include_children": True},
    "https://www.epa.gov/hwgenerators": {"include_children": True},
    "https://www.epa.gov/ust": {"include_children": True},
    "https://www.epa.gov/oil-spills-prevention-and-preparedness-regulations": {"include_children": True},
    "https://www.epa.gov/emergency-response": {"include_children": True},
    "https://www.epa.gov/epcra": {"include_children": True},
    "https://www.epa.gov/air-quality": {"include_children": True},
    "https://www.epa.gov/criteria-air-pollutants": {"include_children": True},
    "https://www.epa.gov/haps": {"include_children": True},
    "https://www.epa.gov/clean-air-act-overview": {"include_children": True},
    "https://www.epa.gov/climate-change": {"include_children": True},
    "https://www.epa.gov/ghgreporting": {"include_children": True},
    "https://www.epa.gov/energy": {"include_children": True},
    "https://www.energystar.gov/": {"include_children": True},
    "https://www.epa.gov/greeningepa": {"include_children": True},
    "https://www.epa.gov/smartgrowth": {"include_children": True},
    "https://www.epa.gov/green-infrastructure": {"include_children": True},
    "https://www.epa.gov/wetlands": {"include_children": True},
    "https://www.epa.gov/wqs-tech": {"include_children": True},
    "https://www.epa.gov/tmdl": {"include_children": True},
    "https://www.epa.gov/nps": {"include_children": True},
    "https://www.epa.gov/septics": {"include_children": True},
    "https://www.epa.gov/watersense": {"include_children": True},
    "https://www.epa.gov/waterdata": {"include_children": True},
    "https://www.epa.gov/waterqualitysurveillance": {"include_children": True},
    "https://www.osha.gov/training": {"include_children": True},
    "https://www.osha.gov/publications": {"include_children": True},
    "https://www.osha.gov/safetypays": {"include_children": True},
    "https://www.osha.gov/recordkeeping": {"include_children": True},
    "https://www.osha.gov/whistleblower": {"include_children": True},
}

def is_url_whitelisted(url: str) -> bool:
    """
    Check if a URL is whitelisted (exact match or child page if include_children=True)
    
    Args:
        url: Full URL to check
        
    Returns:
        True if URL is whitelisted, False otherwise
    """
    url = url.rstrip('/')
    
    # Check exact match
    if url in WHITELISTED_URLS:
        return True
    
    # Check if it's a child of a whitelisted parent
    for parent_url, config in WHITELISTED_URLS.items():
        if config.get("include_children", False):
            parent_url = parent_url.rstrip('/')
            if url.startswith(parent_url + '/') or url.startswith(parent_url + '?'):
                return True
    
    return False

def get_whitelisted_domains() -> set:
    """
    Get set of all whitelisted domains
    
    Returns:
        Set of domain names
    """
    domains = set()
    for url in WHITELISTED_URLS.keys():
        parsed = urlparse(url)
        domains.add(parsed.netloc)
    return domains

def get_total_whitelisted_urls() -> int:
    """
    Get total count of whitelisted URLs
    
    Returns:
        Integer count
    """
    return len(WHITELISTED_URLS)
