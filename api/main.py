"""
Municipal DPW Knowledge Capture System - Main Module
Implements AI-powered knowledge capture with strict source verification
"""

from url_whitelist_config import (
    WHITELISTED_URLS, 
    is_url_whitelisted, 
    get_whitelisted_domains,
    get_total_whitelisted_urls
)
from job_roles_config import (
    JOB_ROLES, 
    get_role_info, 
    get_all_roles,
    get_role_focus_areas
)

class DPWKnowledgeSystem:
    """
    Main class for DPW Knowledge Capture System
    Enforces strict source verification and role-based knowledge filtering
    """

    def __init__(self, user_role=None):
        """
        Initialize the DPW Knowledge System

        Args:
            user_role (str): The role key of the current user (optional)
        """
        self.user_role = user_role
        self.role_info = get_role_info(user_role) if user_role else None
        self.verified_sources = []

    def set_user_role(self, role_key):
        """
        Set or update the user's role

        Args:
            role_key (str): The role identifier key

        Returns:
            bool: True if role was set successfully, False otherwise
        """
        if role_key in JOB_ROLES:
            self.user_role = role_key
            self.role_info = get_role_info(role_key)
            return True
        return False

    def validate_source(self, url):
        """
        Validate if a source URL is whitelisted

        Args:
            url (str): The URL to validate

        Returns:
            dict: Validation result with status and message
        """
        if is_url_whitelisted(url):
            return {
                "valid": True,
                "url": url,
                "message": "Source is whitelisted and verified"
            }
        else:
            return {
                "valid": False,
                "url": url,
                "message": "Source is NOT whitelisted - cannot be used"
            }

    def add_verified_source(self, url, description=""):
        """
        Add a verified source to the current session

        Args:
            url (str): The source URL
            description (str): Optional description of the source

        Returns:
            bool: True if source was added, False if not whitelisted
        """
        validation = self.validate_source(url)
        if validation["valid"]:
            self.verified_sources.append({
                "url": url,
                "description": description,
                "role": self.user_role
            })
            return True
        return False

    def get_role_relevant_sources(self):
        """
        Get sources relevant to the current user's role
        This is a placeholder - in production, you'd filter based on role focus areas

        Returns:
            list: List of relevant source URLs
        """
        if not self.role_info:
            return []

        # This is a simplified example - in production, you'd implement
        # more sophisticated filtering based on role focus areas
        focus_areas = self.role_info.get("focus_areas", [])
        return focus_areas

    def format_citation(self, url, title="", access_date=None):
        """
        Format a citation for a whitelisted source

        Args:
            url (str): The source URL
            title (str): Title of the source document
            access_date (str): Date accessed (YYYY-MM-DD format)

        Returns:
            str: Formatted citation or error message
        """
        if not is_url_whitelisted(url):
            return f"ERROR: Cannot cite non-whitelisted source: {url}"

        citation = f"Source: {title if title else 'Document'}"
        citation += f"\nURL: {url}"
        if access_date:
            citation += f"\nAccessed: {access_date}"
        citation += "\n[Verified Authoritative Source]"

        return citation

    def get_system_info(self):
        """
        Get information about the current system configuration

        Returns:
            dict: System configuration information
        """
        return {
            "total_whitelisted_urls": get_total_whitelisted_urls(),
            "whitelisted_domains": list(get_whitelisted_domains()),
            "available_roles": get_all_roles(),
            "current_role": self.user_role,
            "role_title": self.role_info.get("title") if self.role_info else None,
            "verified_sources_count": len(self.verified_sources)
        }

    def generate_compliance_prompt(self):
        """
        Generate a system prompt for AI that enforces compliance rules

        Returns:
            str: System prompt text
        """
        prompt = f"""You are a Municipal Department of Public Works (DPW) Knowledge Assistant.

STRICT RULES - MUST FOLLOW:
1. ONLY cite and reference sources from the whitelisted URL list
2. NEVER fabricate, hallucinate, or make up information
3. If information is not available from whitelisted sources, explicitly state: "This information is not available in approved sources"
4. Always provide the specific URL when citing information
5. Mark all citations as [Verified Source: URL]

CURRENT USER ROLE: {self.role_info.get('title') if self.role_info else 'Not Set'}

"""

        if self.role_info:
            prompt += f"""ROLE FOCUS AREAS:
{chr(10).join('- ' + area for area in self.role_info.get('focus_areas', []))}

"""

        prompt += f"""WHITELISTED SOURCES: {get_total_whitelisted_urls()} approved URLs
All child pages of these URLs are also approved.

When answering questions:
- Search only within whitelisted sources
- Provide specific citations with URLs
- If uncertain, state limitations clearly
- Prioritize information relevant to the user's role
"""

        return prompt


def main():
    """
    Example usage of the DPW Knowledge System
    """
    print("=" * 70)
    print("Municipal DPW Knowledge Capture System")
    print("=" * 70)
    print()

    # Initialize system
    system = DPWKnowledgeSystem()

    # Display system info
    info = system.get_system_info()
    print(f"System Configuration:")
    print(f"  - Total Whitelisted URLs: {info['total_whitelisted_urls']}")
    print(f"  - Unique Domains: {len(info['whitelisted_domains'])}")
    print(f"  - Available Roles: {len(info['available_roles'])}")
    print()

    # Set user role
    print("Setting user role to 'civil_engineer'...")
    system.set_user_role('civil_engineer')
    print(f"  Role: {system.role_info['title']}")
    print(f"  Focus Areas: {', '.join(system.role_info['focus_areas'][:3])}...")
    print()

    # Validate some sources
    print("Validating Sources:")
    test_urls = [
        "https://www.osha.gov/laws-regs/regulations/standardnumber/1926",
        "https://www.example.com/not-whitelisted",
        "https://www.epa.gov/laws-regulations"
    ]

    for url in test_urls:
        result = system.validate_source(url)
        status = "✓ VALID" if result["valid"] else "✗ INVALID"
        print(f"  {status}: {url}")
    print()

    # Generate compliance prompt
    print("Generating AI Compliance Prompt:")
    print("-" * 70)
    prompt = system.generate_compliance_prompt()
    print(prompt)
    print("-" * 70)
    print()

    # Display available roles
    print("Available Job Roles:")
    for role_key in get_all_roles():
        role = get_role_info(role_key)
        print(f"  - {role['title']} ({role_key})")
    print()

    print("System initialized successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
