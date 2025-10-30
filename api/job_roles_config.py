"""
Job Role Definitions for Municipal DPW Personnel
Used to tailor AI responses to specific user roles and experience levels
"""

JOB_ROLES = {
    "operator_trainee": {
        "title": "Operator Trainee / New Hire",
        "experience_level": "entry",
        "focus_areas": [
            "Basic safety procedures",
            "Fundamental operational concepts",
            "Standard operating procedures (SOPs)",
            "Equipment familiarization",
            "Regulatory basics",
            "Mentorship and training resources"
        ]
    },
    
    "operator_1": {
        "title": "Operator I / Technician I",
        "experience_level": "junior",
        "focus_areas": [
            "Routine operations and maintenance",
            "Basic troubleshooting",
            "Safety compliance",
            "Documentation and record-keeping",
            "Equipment operation",
            "Standard procedures"
        ]
    },
    
    "operator_2": {
        "title": "Operator II / Technician II",
        "experience_level": "intermediate",
        "focus_areas": [
            "Advanced operations",
            "Process optimization",
            "Intermediate troubleshooting",
            "Preventive maintenance",
            "Training junior staff",
            "Regulatory compliance"
        ]
    },
    
    "operator_3": {
        "title": "Operator III / Senior Technician",
        "experience_level": "senior",
        "focus_areas": [
            "Complex troubleshooting",
            "Process control and optimization",
            "Emergency response",
            "Mentoring and training",
            "Regulatory reporting",
            "System improvements"
        ]
    },
    
    "lead_operator": {
        "title": "Lead Operator / Crew Leader",
        "experience_level": "lead",
        "focus_areas": [
            "Crew supervision",
            "Work planning and scheduling",
            "Quality control",
            "Safety oversight",
            "Performance management",
            "Resource allocation"
        ]
    },
    
    "supervisor": {
        "title": "Supervisor / Foreman",
        "experience_level": "supervisory",
        "focus_areas": [
            "Team management",
            "Budget oversight",
            "Project coordination",
            "Performance evaluation",
            "Policy implementation",
            "Interdepartmental coordination"
        ]
    },
    
    "manager": {
        "title": "Manager / Superintendent",
        "experience_level": "management",
        "focus_areas": [
            "Strategic planning",
            "Budget development",
            "Policy development",
            "Regulatory compliance oversight",
            "Stakeholder communication",
            "Long-term asset management"
        ]
    },
    
    "director": {
        "title": "Director / Department Head",
        "experience_level": "executive",
        "focus_areas": [
            "Strategic vision",
            "Political liaison",
            "Budget and finance",
            "Policy and governance",
            "Public relations",
            "Organizational development"
        ]
    },
    
    "engineer": {
        "title": "Engineer",
        "experience_level": "professional",
        "focus_areas": [
            "Design and specifications",
            "Technical analysis",
            "Regulatory compliance",
            "Project management",
            "Quality assurance",
            "Innovation and improvement"
        ]
    },
    
    "safety_officer": {
        "title": "Safety Officer / Compliance Coordinator",
        "experience_level": "professional",
        "focus_areas": [
            "Safety program development",
            "Incident investigation",
            "Training coordination",
            "Regulatory compliance",
            "Risk assessment",
            "Emergency preparedness"
        ]
    },
    
    "maintenance_tech": {
        "title": "Maintenance Technician",
        "experience_level": "intermediate",
        "focus_areas": [
            "Equipment repair",
            "Preventive maintenance",
            "Troubleshooting",
            "Parts management",
            "Documentation",
            "Safety procedures"
        ]
    },
    
    "electrician": {
        "title": "Electrician / Instrumentation Tech",
        "experience_level": "professional",
        "focus_areas": [
            "Electrical systems",
            "Motor controls",
            "SCADA and instrumentation",
            "PLC programming",
            "Troubleshooting",
            "NEC compliance"
        ]
    },
    
    "mechanic": {
        "title": "Mechanic / Fleet Technician",
        "experience_level": "professional",
        "focus_areas": [
            "Vehicle and equipment repair",
            "Diagnostics",
            "Preventive maintenance",
            "Hydraulic systems",
            "Diesel engines",
            "Welding and fabrication"
        ]
    },
    
    "lab_tech": {
        "title": "Laboratory Technician",
        "experience_level": "professional",
        "focus_areas": [
            "Sample collection and analysis",
            "QA/QC procedures",
            "Laboratory equipment",
            "Data management",
            "Regulatory reporting",
            "Safety protocols"
        ]
    },
    
    "admin_staff": {
        "title": "Administrative Staff",
        "experience_level": "support",
        "focus_areas": [
            "Customer service",
            "Billing and accounts",
            "Record management",
            "Communication",
            "Scheduling",
            "Regulatory reporting support"
        ]
    }
}

def get_all_roles() -> list:
    """
    Get list of all role keys
    
    Returns:
        List of role key strings
    """
    return list(JOB_ROLES.keys())

def get_role_info(role_key: str) -> dict:
    """
    Get complete information for a specific role
    
    Args:
        role_key: Key from JOB_ROLES
        
    Returns:
        Role dictionary or empty dict if not found
    """
    return JOB_ROLES.get(role_key, {})

def get_role_focus_areas(role_key: str) -> list:
    """
    Get focus areas for a specific role
    
    Args:
        role_key: Key from JOB_ROLES
        
    Returns:
        List of focus area strings
    """
    role = JOB_ROLES.get(role_key, {})
    return role.get("focus_areas", [])
