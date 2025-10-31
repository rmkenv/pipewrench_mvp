"""
Job Roles Configuration for PipeWrench AI
Defines role-specific contexts for municipal DPW positions
Version: 2024-10-31-v2 - Reorganized function order for Vercel serverless compatibility
"""

JOB_ROLES = {
    "director": {
        "title": "Director/Superintendent",
        "context": """You are assisting a Director or Superintendent of Public Works who oversees:
- Strategic planning and budget management
- Policy development and regulatory compliance
- Interdepartmental coordination
- Public relations and community engagement
- Long-term infrastructure planning
Focus on high-level strategic guidance, compliance requirements, and best practices for municipal leadership."""
    },
    
    "engineer": {
        "title": "Civil/Public Works Engineer",
        "context": """You are assisting a Civil or Public Works Engineer who handles:
- Design and specifications for infrastructure projects
- Technical review and plan approval
- Construction oversight and quality control
- Engineering standards and code compliance
- Project cost estimation and feasibility studies
Provide technical engineering guidance with proper citations to relevant codes and standards."""
    },
    
    "foreman": {
        "title": "Field Supervisor/Foreman",
        "context": """You are assisting a Field Supervisor or Foreman who manages:
- Daily crew operations and work assignments
- Equipment deployment and maintenance scheduling
- Safety compliance and incident reporting
- Quality control of field work
- Coordination with other departments
Focus on practical field operations, safety procedures, and crew management best practices."""
    },
    
    "maintenance_worker": {
        "title": "Maintenance Worker/Technician",
        "context": """You are assisting a Maintenance Worker or Technician who performs:
- Routine maintenance and repairs
- Equipment operation
- Safety protocol compliance
- Work order completion
- Basic troubleshooting
Provide clear, practical guidance on procedures, safety requirements, and proper techniques."""
    },
    
    "water_operator": {
        "title": "Water/Wastewater Operator",
        "context": """You are assisting a Water or Wastewater Treatment Operator who handles:
- Treatment plant operations
- Water quality monitoring and testing
- Regulatory compliance and reporting
- Equipment maintenance and troubleshooting
- Emergency response procedures
Focus on operational procedures, regulatory requirements, and technical specifications for water/wastewater systems."""
    },
    
    "fleet_manager": {
        "title": "Fleet/Equipment Manager",
        "context": """You are assisting a Fleet or Equipment Manager responsible for:
- Vehicle and equipment maintenance programs
- Fleet replacement planning
- Procurement and specifications
- Maintenance records and cost tracking
- Vendor management
Provide guidance on fleet management best practices, maintenance standards, and procurement procedures."""
    },
    
    "safety_officer": {
        "title": "Safety Officer/Coordinator",
        "context": """You are assisting a Safety Officer or Coordinator who oversees:
- Safety program development and implementation
- OSHA compliance and training
- Incident investigation and reporting
- Safety equipment and PPE management
- Risk assessment and mitigation
Focus on safety regulations, compliance requirements, and best practices for workplace safety."""
    },
    
    "admin": {
        "title": "Administrative Staff",
        "context": """You are assisting Administrative Staff who handle:
- Records management and documentation
- Public inquiries and customer service
- Permit processing and tracking
- Budget tracking and reporting
- Interdepartmental communication
Provide guidance on administrative procedures, record-keeping requirements, and customer service best practices."""
    }
}

# Primary functions - defined early for Vercel serverless import compatibility
def get_all_roles():
    """Get list of all role keys"""
    return list(JOB_ROLES.keys())


def get_role_info(role_key: str):
    """Get complete information for a specific role"""
    if not role_key or role_key not in JOB_ROLES:
        return None
    
    role = JOB_ROLES[role_key]
    return {
        "title": role["title"],
        "context": role["context"],
        "focus_areas": [
            line.strip("- ").strip() 
            for line in role["context"].split("\n") 
            if line.strip().startswith("-")
        ]
    }


# Helper functions
def get_role_list():
    """Return list of all roles for dropdown selection"""
    return [
        {"value": key, "title": role["title"]}
        for key, role in JOB_ROLES.items()
    ]


def get_role_context(role_key: str) -> str:
    """Get the context prompt for a specific role"""
    if not role_key or role_key not in JOB_ROLES:
        return ""
    return JOB_ROLES[role_key]["context"]


def get_role_title(role_key: str) -> str:
    """Get the display title for a specific role"""
    if not role_key or role_key not in JOB_ROLES:
        return "General"
    return JOB_ROLES[role_key]["title"]


def get_role_focus_areas(role_key: str):
    """Get focus areas for a specific role"""
    role_info = get_role_info(role_key)
    if role_info:
        return role_info.get("focus_areas", [])
    return []
