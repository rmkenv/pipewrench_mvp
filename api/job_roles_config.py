"""
Job Roles Configuration for Municipal DPW Knowledge Capture System
Defines role-specific focus areas and expertise domains
"""

JOB_ROLES = {
    "project_manager": {
        "title": "Project Manager",
        "focus_areas": [
            "project scheduling",
            "budget management",
            "stakeholder coordination",
            "risk management",
            "contract administration",
            "resource allocation",
            "quality control",
            "project documentation"
        ],
        "key_responsibilities": [
            "Overall project oversight",
            "Timeline and milestone tracking",
            "Budget monitoring and reporting",
            "Team coordination"
        ]
    },

    "civil_engineer": {
        "title": "Civil Engineer",
        "focus_areas": [
            "structural design",
            "technical specifications",
            "engineering calculations",
            "design standards compliance",
            "material specifications",
            "load analysis",
            "drainage design",
            "geotechnical considerations"
        ],
        "key_responsibilities": [
            "Design review and approval",
            "Technical specification development",
            "Engineering analysis",
            "Code compliance verification"
        ]
    },

    "construction_inspector": {
        "title": "Construction Inspector",
        "focus_areas": [
            "field inspection",
            "quality assurance",
            "construction compliance",
            "material testing",
            "workmanship standards",
            "safety compliance",
            "daily reporting",
            "deficiency identification"
        ],
        "key_responsibilities": [
            "On-site inspection activities",
            "Compliance verification",
            "Documentation of work progress",
            "Issue identification and reporting"
        ]
    },

    "safety_officer": {
        "title": "Safety Officer",
        "focus_areas": [
            "OSHA compliance",
            "safety regulations",
            "hazard identification",
            "safety training",
            "incident investigation",
            "PPE requirements",
            "safety protocols",
            "emergency procedures"
        ],
        "key_responsibilities": [
            "Safety program implementation",
            "Site safety inspections",
            "Safety training coordination",
            "Incident response and reporting"
        ]
    },

    "environmental_specialist": {
        "title": "Environmental Specialist",
        "focus_areas": [
            "EPA regulations",
            "environmental permits",
            "stormwater management",
            "erosion control",
            "wetlands protection",
            "environmental impact assessment",
            "pollution prevention",
            "environmental monitoring"
        ],
        "key_responsibilities": [
            "Environmental compliance oversight",
            "Permit acquisition and management",
            "Environmental monitoring",
            "Regulatory reporting"
        ]
    },

    "procurement_specialist": {
        "title": "Procurement Specialist",
        "focus_areas": [
            "FAR compliance",
            "contract procurement",
            "vendor selection",
            "bid evaluation",
            "contract negotiation",
            "procurement regulations",
            "competitive bidding",
            "contract types"
        ],
        "key_responsibilities": [
            "Procurement process management",
            "Contract document preparation",
            "Vendor evaluation",
            "Compliance with procurement regulations"
        ]
    },

    "maintenance_supervisor": {
        "title": "Maintenance Supervisor",
        "focus_areas": [
            "preventive maintenance",
            "equipment management",
            "maintenance scheduling",
            "repair procedures",
            "asset management",
            "maintenance standards",
            "work order management",
            "maintenance documentation"
        ],
        "key_responsibilities": [
            "Maintenance program oversight",
            "Work crew supervision",
            "Equipment and asset tracking",
            "Maintenance planning"
        ]
    },

    "traffic_engineer": {
        "title": "Traffic Engineer",
        "focus_areas": [
            "traffic control",
            "signalization",
            "traffic flow analysis",
            "roadway design",
            "traffic safety",
            "MUTCD compliance",
            "traffic studies",
            "intersection design"
        ],
        "key_responsibilities": [
            "Traffic control plan development",
            "Traffic signal design",
            "Traffic impact analysis",
            "Safety improvement recommendations"
        ]
    },

    "gis_specialist": {
        "title": "GIS Specialist",
        "focus_areas": [
            "spatial analysis",
            "mapping",
            "asset inventory",
            "data management",
            "GPS coordination",
            "infrastructure mapping",
            "data visualization",
            "geospatial databases"
        ],
        "key_responsibilities": [
            "GIS data management",
            "Map production",
            "Spatial analysis",
            "Asset location tracking"
        ]
    },

    "public_works_director": {
        "title": "Public Works Director",
        "focus_areas": [
            "strategic planning",
            "policy development",
            "budget oversight",
            "regulatory compliance",
            "public relations",
            "departmental management",
            "capital improvement planning",
            "interagency coordination"
        ],
        "key_responsibilities": [
            "Department leadership",
            "Strategic decision-making",
            "Budget and resource allocation",
            "Policy implementation"
        ]
    }
}

def get_role_info(role_key):
    """
    Retrieve information for a specific job role

    Args:
        role_key (str): The role identifier key

    Returns:
        dict: Role information or None if not found
    """
    return JOB_ROLES.get(role_key)

def get_all_roles():
    """
    Get list of all available role keys

    Returns:
        list: List of role identifier keys
    """
    return list(JOB_ROLES.keys())

def get_role_focus_areas(role_key):
    """
    Get focus areas for a specific role

    Args:
        role_key (str): The role identifier key

    Returns:
        list: List of focus areas or empty list if role not found
    """
    role = JOB_ROLES.get(role_key)
    return role.get("focus_areas", []) if role else []
