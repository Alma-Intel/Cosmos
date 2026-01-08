"""
Admin panel views - exclusive to admins
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.db import transaction
from .models import UserProfile, Team
from .organizations_db import (
    create_organization,
    get_all_organizations,
    get_organization_by_uuid,
    get_authorization_by_organization
)


def require_admin(view_func):
    """Decorator to require admin role"""
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.profile
            if not profile.is_admin():
                raise PermissionDenied("This page is only accessible to administrators.")
        except:
            raise PermissionDenied("This page is only accessible to administrators.")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_admin
def admin_panel(request):
    """Main admin panel dashboard"""
    current_profile = request.user.profile
    
    # Get all organizations
    organizations = get_all_organizations()
    
    context = {
        'title': 'Admin Panel',
        'current_profile': current_profile,
        'organizations': organizations,
    }
    return render(request, 'conversations/admin_panel.html', context)


@login_required
@require_admin
def admin_create_organization(request):
    """Create a new organization and director user"""
    current_profile = request.user.profile
    
    if request.method == 'POST':
        # Get form data
        org_name = request.POST.get('org_name', '').strip()
        director_username = request.POST.get('director_username', '').strip()
        director_email = request.POST.get('director_email', '').strip()
        director_password = request.POST.get('director_password', '').strip()
        director_first_name = request.POST.get('director_first_name', '').strip()
        director_last_name = request.POST.get('director_last_name', '').strip()
        director_phone = request.POST.get('director_phone', '').strip()
        
        # Validate required fields
        if not org_name:
            messages.error(request, 'Organization name is required.')
        elif not director_username:
            messages.error(request, 'Director username is required.')
        elif not director_password:
            messages.error(request, 'Director password is required.')
        elif User.objects.filter(username=director_username).exists():
            messages.error(request, f'Username {director_username} already exists.')
        else:
            try:
                with transaction.atomic():
                    # Create organization in organizations database
                    org_uuid = create_organization(
                        name=org_name,
                        active='true',
                        meta_data={'created_by_admin': request.user.username}
                    )
                    
                    # Create a team for this organization
                    team = Team.objects.create(
                        name=f"{org_name} - Main Team",
                        description=f"Main team for {org_name}",
                        alma_internal_organization=org_uuid
                    )
                    
                    # Create director user
                    director_user = User.objects.create_user(
                        username=director_username,
                        email=director_email,
                        password=director_password,
                        first_name=director_first_name,
                        last_name=director_last_name,
                    )
                    
                    # Create director profile
                    director_profile = UserProfile.objects.create(
                        user=director_user,
                        role='Director',
                        team=team,
                        alma_internal_organization=org_uuid,
                        cell_phone=director_phone,
                    )
                    
                    messages.success(
                        request,
                        f'Organization "{org_name}" created successfully with UUID: {org_uuid}. '
                        f'Director user "{director_username}" has been created.'
                    )
                    return redirect('admin_organization_detail', org_uuid=org_uuid)
                    
            except Exception as e:
                messages.error(request, f'Error creating organization: {str(e)}')
    
    context = {
        'title': 'Create New Organization',
        'current_profile': current_profile,
    }
    return render(request, 'conversations/admin_create_organization.html', context)


@login_required
@require_admin
def admin_organization_detail(request, org_uuid):
    """View organization details"""
    current_profile = request.user.profile
    
    # Get organization from organizations database
    organization = get_organization_by_uuid(org_uuid)
    
    if not organization:
        messages.error(request, 'Organization not found.')
        return redirect('admin_panel')
    
    # Get authorization for this organization
    authorization = get_authorization_by_organization(org_uuid)
    
    # Get all teams for this organization
    teams = Team.objects.filter(alma_internal_organization=org_uuid)
    
    # Get all users for this organization
    users = UserProfile.objects.filter(alma_internal_organization=org_uuid).select_related('user', 'team')
    
    context = {
        'title': f'Organization: {organization["name"]}',
        'current_profile': current_profile,
        'organization': organization,
        'authorization': authorization,
        'teams': teams,
        'users': users,
    }
    return render(request, 'conversations/admin_organization_detail.html', context)


@login_required
@require_admin
def admin_organizations_list(request):
    """List all organizations"""
    current_profile = request.user.profile
    
    # Get all organizations
    organizations = get_all_organizations()
    
    # For each organization, get user count
    for org in organizations:
        org['user_count'] = UserProfile.objects.filter(
            alma_internal_organization=org['uuid']
        ).count()
        org['team_count'] = Team.objects.filter(
            alma_internal_organization=org['uuid']
        ).count()
    
    context = {
        'title': 'All Organizations',
        'current_profile': current_profile,
        'organizations': organizations,
    }
    return render(request, 'conversations/admin_organizations_list.html', context)

