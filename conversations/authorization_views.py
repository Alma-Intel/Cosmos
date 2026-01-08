"""
Authorization management views - for directors and admins
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from .models import UserProfile
from .organizations_db import (
    get_organization_by_uuid,
    get_all_organizations,
    get_api_keys_by_organization,
    create_api_key,
    delete_api_key,
    get_api_key_by_uuid
)


def require_director_or_admin(view_func):
    """Decorator to require director or admin role"""
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.profile
            if not (profile.is_admin() or profile.is_director()):
                raise PermissionDenied("This page is only accessible to directors and administrators.")
        except:
            raise PermissionDenied("This page is only accessible to directors and administrators.")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_director_or_admin
def authorization_management(request):
    """Main authorization management page"""
    current_profile = request.user.profile
    
    # Admins can select an organization, directors use their own
    if current_profile.is_admin():
        # Get all organizations for the selector
        all_organizations = get_all_organizations()
        
        if not all_organizations:
            messages.error(request, 'No organizations found in the system.')
            return redirect('workspace')
        
        # Admin: can choose organization from query param or default to first org
        org_uuid = request.GET.get('org_uuid')
        
        if not org_uuid:
            # Default to admin's own org if they have one, otherwise first org
            if current_profile.alma_internal_organization:
                org_uuid = current_profile.alma_internal_organization
            else:
                # Use first organization as default
                org_uuid = all_organizations[0]['uuid']
    else:
        # Director: can only manage their own organization
        org_uuid = current_profile.alma_internal_organization
        all_organizations = None
        
        if not org_uuid:
            messages.error(request, 'Your profile does not have an organization assigned.')
            return redirect('workspace')
    
    # Get organization details
    organization = get_organization_by_uuid(org_uuid)
    
    if not organization:
        messages.error(request, 'Organization not found.')
        return redirect('workspace')
    
    # Get all API keys for this organization
    api_keys = get_api_keys_by_organization(org_uuid)
    
    context = {
        'title': 'API Key Management',
        'current_profile': current_profile,
        'organization': organization,
        'api_keys': api_keys,
        'all_organizations': all_organizations,  # For admin organization selector
        'selected_org_uuid': org_uuid,
    }
    return render(request, 'conversations/authorization_management.html', context)


@login_required
@require_director_or_admin
def authorization_create(request):
    """Create a new API key"""
    current_profile = request.user.profile
    
    # Admins can select an organization, directors use their own
    if current_profile.is_admin():
        # Get all organizations for the selector
        all_organizations = get_all_organizations()
        
        if not all_organizations:
            messages.error(request, 'No organizations found in the system.')
            return redirect('workspace')
        
        if request.method == 'POST':
            org_uuid = request.POST.get('org_uuid', '').strip()
        else:
            # Default to query param or admin's own org or first org
            org_uuid = request.GET.get('org_uuid')
            if not org_uuid:
                if current_profile.alma_internal_organization:
                    org_uuid = current_profile.alma_internal_organization
                else:
                    org_uuid = all_organizations[0]['uuid']
    else:
        # Director: can only create for their own organization
        org_uuid = current_profile.alma_internal_organization
        all_organizations = None
        
        if not org_uuid:
            messages.error(request, 'Your profile does not have an organization assigned.')
            return redirect('workspace')
    
    if not org_uuid:
        messages.error(request, 'Please select an organization.')
        return redirect('authorization_management')
    
    # Get organization details
    organization = get_organization_by_uuid(org_uuid)
    
    if not organization:
        messages.error(request, 'Organization not found.')
        return redirect('authorization_management')
    
    if request.method == 'POST':
        key_name = request.POST.get('key_name', '').strip()
        
        if not key_name:
            messages.error(request, 'API key name is required.')
        elif not org_uuid:
            messages.error(request, 'Organization is required.')
        else:
            try:
                # Create the API key
                api_key_data = create_api_key(org_uuid, key_name)
                
                if api_key_data:
                    messages.success(
                        request,
                        f'API key "{key_name}" created successfully! '
                        f'Key: {api_key_data["apikey"]} (Copy this now, it won\'t be shown again in full)'
                    )
                    # Redirect back with the organization selected
                    if current_profile.is_admin():
                        return redirect(f'{reverse("authorization_management")}?org_uuid={org_uuid}')
                    else:
                        return redirect('authorization_management')
                else:
                    messages.error(request, 'Failed to create API key.')
            except Exception as e:
                messages.error(request, f'Error creating API key: {str(e)}')
    
    context = {
        'title': 'Create API Key',
        'current_profile': current_profile,
        'organization': organization,
        'all_organizations': all_organizations,  # For admin organization selector
        'selected_org_uuid': org_uuid,
    }
    return render(request, 'conversations/authorization_create.html', context)


@login_required
@require_director_or_admin
def authorization_delete(request, auth_uuid):
    """Delete an API key"""
    current_profile = request.user.profile
    
    # Get the API key
    api_key = get_api_key_by_uuid(auth_uuid)
    
    if not api_key:
        messages.error(request, 'API key not found.')
        return redirect('authorization_management')
    
    # Check permissions
    if not current_profile.is_admin():
        # Director: can only delete keys from their own organization
        if current_profile.alma_internal_organization != api_key['organization_uuid']:
            raise PermissionDenied("You can only delete API keys from your own organization.")
    
    # Get organization for display
    organization = get_organization_by_uuid(api_key['organization_uuid'])
    
    if request.method == 'POST':
        try:
            if delete_api_key(auth_uuid):
                messages.success(request, 'API key deleted successfully.')
                # Redirect back with the organization selected for admins
                if current_profile.is_admin():
                    return redirect(f'{reverse("authorization_management")}?org_uuid={api_key["organization_uuid"]}')
                else:
                    return redirect('authorization_management')
            else:
                messages.error(request, 'Failed to delete API key.')
        except Exception as e:
            messages.error(request, f'Error deleting API key: {str(e)}')
    
    context = {
        'title': 'Delete API Key',
        'current_profile': current_profile,
        'api_key': api_key,
        'organization': organization,
    }
    return render(request, 'conversations/authorization_delete_confirm.html', context)

