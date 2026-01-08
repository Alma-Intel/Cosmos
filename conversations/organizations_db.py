"""
Utility functions for interacting with the organizations database
"""
import uuid
import json
from django.db import connections
from django.utils import timezone
from datetime import datetime


def get_organizations_connection():
    """Get connection to organizations database"""
    return connections['organizations']


def create_organization(name, active='true', meta_data=None):
    """
    Create a new organization in the organizations database
    
    Args:
        name (str): Name of the organization
        active (str): Active status ('true' or 'false')
        meta_data (dict): Optional metadata as JSON
        
    Returns:
        str: UUID of the created organization
    """
    org_uuid = uuid.uuid4()
    now = timezone.now()
    
    # Convert meta_data dict to JSON string if provided
    meta_data_json = json.dumps(meta_data) if meta_data else None
    
    with get_organizations_connection().cursor() as cursor:
        cursor.execute("""
            INSERT INTO organizations (uuid, name, created_at, updated_at, active, meta_data)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING uuid
        """, [str(org_uuid), name, now, now, active, meta_data_json])
        
        result = cursor.fetchone()
        return str(result[0]) if result else str(org_uuid)


def get_organization_by_uuid(org_uuid):
    """
    Get organization by UUID
    
    Args:
        org_uuid (str): UUID of the organization
        
    Returns:
        dict: Organization data or None if not found
    """
    with get_organizations_connection().cursor() as cursor:
        cursor.execute("""
            SELECT uuid, name, created_at, updated_at, active, meta_data
            FROM organizations
            WHERE uuid = %s
        """, [str(org_uuid)])
        
        row = cursor.fetchone()
        if row:
            return {
                'uuid': str(row[0]),
                'name': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'active': row[4],
                'meta_data': row[5],
            }
        return None


def get_all_organizations():
    """
    Get all organizations
    
    Returns:
        list: List of organization dictionaries
    """
    with get_organizations_connection().cursor() as cursor:
        cursor.execute("""
            SELECT uuid, name, created_at, updated_at, active, meta_data
            FROM organizations
            ORDER BY created_at DESC
        """)
        
        organizations = []
        for row in cursor.fetchall():
            organizations.append({
                'uuid': str(row[0]),
                'name': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'active': row[4],
                'meta_data': row[5],
            })
        return organizations


def update_organization(org_uuid, name=None, active=None, meta_data=None):
    """
    Update an organization
    
    Args:
        org_uuid (str): UUID of the organization
        name (str): Optional new name
        active (str): Optional new active status
        meta_data (dict): Optional new metadata
        
    Returns:
        bool: True if updated successfully
    """
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    
    if active is not None:
        updates.append("active = %s")
        params.append(active)
    
    if meta_data is not None:
        updates.append("meta_data = %s")
        params.append(json.dumps(meta_data))
    
    if not updates:
        return False
    
    # Always update updated_at
    updates.append("updated_at = %s")
    params.append(timezone.now())
    
    params.append(str(org_uuid))
    
    with get_organizations_connection().cursor() as cursor:
        cursor.execute(f"""
            UPDATE organizations
            SET {', '.join(updates)}
            WHERE uuid = %s
        """, params)
        
        return cursor.rowcount > 0



