"""
Job Roles Configuration for PipeWrench AI
Defines different job roles and their context for DPW professionals
"""

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


def get_role_context(role_key):
    """
    Get the context string for a specific role
    
    Args:
        role_key (str): The key identifying the role (e.g., 'director', 'field_technician')
        
    Returns:
        str: The context string for that role, or empty string if role not found
    """
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["context"]
    return ""


def get_role_title(role_key):
    """
    Get the title for a specific role
    
    Args:
        role_key (str): The key identifying the role
        
    Returns:
        str: The title for that role, or empty string if role not found
    """
    if role_key and role_key in JOB_ROLES:
        return JOB_ROLES[role_key]["title"]
    return ""


def get_all_roles():
    """
    Get a list of all available role keys
    
    Returns:
        list: List of all role keys
    """
    return list(JOB_ROLES.keys())


def get_roles_dict():
    """
    Get the full roles dictionary formatted for API responses
    
    Returns:
        dict: Dictionary with role keys as keys and role info as values
    """
    return {
        key: {
            "key": key,
            "title": value["title"],
            "context": value["context"]
        }
        for key, value in JOB_ROLES.items()
    }
