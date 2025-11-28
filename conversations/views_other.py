"""
Views for other sections: Agentes, Clientes, Bots, Workspace
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.models import User
from .models import UserProfile, Team
from .forms import ProfileForm, AgentEditForm, UserCreateForm, TeamCreateForm
from .permissions import get_user_team_members, can_view_alma_uuid


@login_required
def agent_create(request):
    """Create a new user/agent"""
    # Get current user's profile
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check permissions - only admins and directors can create users
    if not (current_profile.is_admin() or current_profile.is_director()):
        raise PermissionDenied("You don't have permission to create users.")
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, current_profile=current_profile)
        if form.is_valid():
            try:
                # Create the user
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data.get('email', ''),
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', ''),
                )
                
                # Create the user profile
                # Inherit alma_internal_organization from creator, or use form value if admin explicitly set it
                if current_profile.is_admin() and form.cleaned_data.get('alma_internal_organization'):
                    # Admin explicitly set a value, use it
                    inherited_org = form.cleaned_data.get('alma_internal_organization', '')
                else:
                    # Inherit from creator
                    inherited_org = current_profile.alma_internal_organization or ''
                
                profile = UserProfile.objects.create(
                    user=user,
                    role=form.cleaned_data['role'],
                    team=form.cleaned_data.get('team'),
                    external_uuid=form.cleaned_data.get('external_uuid', ''),
                    cell_phone=form.cleaned_data.get('cell_phone', ''),
                    alma_internal_uuid=form.cleaned_data.get('alma_internal_uuid', '') if current_profile.is_admin() else '',
                    alma_internal_organization=inherited_org,
                )
                
                # Validate the profile (team requirements, etc.)
                try:
                    profile.full_clean()
                    profile.save()
                    messages.success(request, f'User {user.username} created successfully!')
                    return redirect('agent_detail', user_id=user.id)
                except Exception as e:
                    # If validation fails, delete the user and show error
                    user.delete()
                    messages.error(request, f'Error creating user: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
    else:
        form = UserCreateForm(current_profile=current_profile)
    
    context = {
        'title': 'Create New User',
        'form': form,
        'current_profile': current_profile,
    }
    return render(request, 'conversations/agent_create.html', context)


@login_required
def team_create(request):
    """Create a new team"""
    # Get current user's profile
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check permissions - only admins and directors can create teams
    if not (current_profile.is_admin() or current_profile.is_director()):
        raise PermissionDenied("You don't have permission to create teams.")
    
    if request.method == 'POST':
        form = TeamCreateForm(request.POST, current_profile=current_profile)
        if form.is_valid():
            try:
                team = form.save(commit=False)
                # Inherit alma_internal_organization from creator
                team.alma_internal_organization = current_profile.alma_internal_organization or ''
                team.save()
                # Assign the selected manager to the team
                manager_profile = form.cleaned_data['manager']
                manager_profile.team = team
                manager_profile.save()
                messages.success(request, f'Team "{team.name}" created successfully with manager {manager_profile.get_display_name()}!')
                return redirect('agentes_list')
            except Exception as e:
                messages.error(request, f'Error creating team: {str(e)}')
    else:
        form = TeamCreateForm(current_profile=current_profile)
    
    context = {
        'title': 'Create New Team',
        'form': form,
        'current_profile': current_profile,
    }
    return render(request, 'conversations/team_create.html', context)


@login_required
def agentes_list(request):
    """List all agents/users with filtering"""
    # Get current user's profile for permission checks
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Get all users that the current user can view
    profiles = get_user_team_members(request.user)
    
    # Filter by alma_internal_organization (admins can see all)
    if not current_profile.is_admin() and current_profile.alma_internal_organization:
        profiles = profiles.filter(alma_internal_organization=current_profile.alma_internal_organization)
    
    # Filtering options
    role_filter = request.GET.get('role', '')
    team_filter = request.GET.get('team', '')
    search_query = request.GET.get('search', '')
    
    # Apply filters
    if role_filter:
        profiles = profiles.filter(role=role_filter)
    
    if team_filter:
        profiles = profiles.filter(team_id=team_filter)
    
    if search_query:
        profiles = profiles.filter(
            user__username__icontains=search_query
        ) | profiles.filter(
            user__first_name__icontains=search_query
        ) | profiles.filter(
            user__last_name__icontains=search_query
        ) | profiles.filter(
            user__email__icontains=search_query
        )
    
    # Get filter options
    all_roles = ['User', 'Manager', 'Director', 'Admin']
    # Filter teams by organization (admins can see all)
    if current_profile.is_admin():
        all_teams = Team.objects.all().order_by('name')
    else:
        if current_profile.alma_internal_organization:
            all_teams = Team.objects.filter(alma_internal_organization=current_profile.alma_internal_organization).order_by('name')
        else:
            all_teams = Team.objects.none()
    
    context = {
        'title': 'Agentes',
        'profiles': profiles.select_related('user', 'team'),
        'all_roles': all_roles,
        'all_teams': all_teams,
        'current_role_filter': role_filter,
        'current_team_filter': team_filter,
        'current_search': search_query,
        'current_profile': current_profile,
        'can_view_alma_uuid': can_view_alma_uuid(request.user),
    }
    return render(request, 'conversations/agents_list.html', context)


@login_required
def teams_list(request):
    """List all teams"""
    # Get current user's profile for permission checks
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Filter teams by alma_internal_organization (admins can see all)
    if current_profile.is_admin():
        teams = Team.objects.all().prefetch_related('members__user').order_by('name')
    else:
        if current_profile.alma_internal_organization:
            teams = Team.objects.filter(alma_internal_organization=current_profile.alma_internal_organization).prefetch_related('members__user').order_by('name')
        else:
            teams = Team.objects.none()
    
    # For each team, get the manager(s) and members
    teams_data = []
    for team in teams:
        # Get managers/directors in this team
        managers = team.members.filter(role__in=['Manager', 'Director', 'Admin']).select_related('user')
        # Get all members
        members = team.members.all().select_related('user')
        
        teams_data.append({
            'team': team,
            'managers': managers,
            'members': members,
            'member_count': members.count(),
        })
    
    context = {
        'title': 'Teams',
        'teams_data': teams_data,
        'current_profile': current_profile,
    }
    return render(request, 'conversations/teams_list.html', context)


@login_required
def team_detail(request, team_id):
    """View team details with manager and members"""
    team = get_object_or_404(Team, pk=team_id)
    
    # Get current user's profile for permission checks
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check if user can access this team (same organization or admin)
    if not current_profile.is_admin():
        if not current_profile.alma_internal_organization or team.alma_internal_organization != current_profile.alma_internal_organization:
            raise PermissionDenied("You don't have permission to view this team.")
    
    # Check if user can edit/delete team (admins and directors)
    can_edit_team = current_profile.is_admin() or current_profile.is_director()
    
    # Get managers/directors in this team
    managers = team.members.filter(role__in=['Manager', 'Director', 'Admin']).select_related('user').order_by('user__last_name', 'user__first_name')
    
    # Get all members excluding the managers (those shown in the Managers section)
    # Exclude by getting manager IDs and excluding them from members
    manager_ids = managers.values_list('id', flat=True)
    members = team.members.exclude(id__in=manager_ids).select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
    
    # Handle POST requests for team management
    if request.method == 'POST' and can_edit_team:
        if 'change_manager' in request.POST:
            new_manager_id = request.POST.get('new_manager')
            if new_manager_id:
                try:
                    new_manager = UserProfile.objects.get(pk=new_manager_id)
                    # Verify new manager has appropriate role
                    if new_manager.role in ['Manager', 'Director', 'Admin']:
                        # Add the new manager to the team
                        new_manager.team = team
                        new_manager.save()
                        messages.success(request, f'Manager {new_manager.get_display_name()} added to team')
                        return redirect('team_detail', team_id=team_id)
                    else:
                        messages.error(request, 'Selected user must be a Manager, Director, or Admin')
                except UserProfile.DoesNotExist:
                    messages.error(request, 'Selected manager not found')
        elif 'remove_manager' in request.POST:
            manager_id = request.POST.get('remove_manager')
            if manager_id:
                try:
                    manager_to_remove = UserProfile.objects.get(pk=manager_id, team=team)
                    # Remove the manager from the team
                    manager_to_remove.team = None
                    manager_to_remove.save()
                    messages.success(request, f'Manager {manager_to_remove.get_display_name()} removed from team')
                    # Check if team still has a manager
                    remaining_managers = team.members.filter(role__in=['Manager', 'Director', 'Admin']).exists()
                    if not remaining_managers:
                        messages.warning(request, 'Warning: This team now has no manager. Please assign a Manager, Director, or Admin to this team.')
                    return redirect('team_detail', team_id=team_id)
                except UserProfile.DoesNotExist:
                    messages.error(request, 'Manager not found')
        elif 'remove_member' in request.POST:
            member_id = request.POST.get('remove_member')
            if member_id:
                try:
                    member_to_remove = UserProfile.objects.get(pk=member_id, team=team)
                    # Check if removing this member would leave the team without a manager
                    is_manager = member_to_remove.role in ['Manager', 'Director', 'Admin']
                    if is_manager:
                        # Check if there are other managers
                        other_managers = team.members.filter(role__in=['Manager', 'Director', 'Admin']).exclude(pk=member_id)
                        if not other_managers.exists():
                            messages.warning(request, f'Warning: {member_to_remove.get_display_name()} is the last manager. Removing them will leave the team without a manager.')
                    # Remove the member from the team
                    member_to_remove.team = None
                    member_to_remove.save()
                    messages.success(request, f'Member {member_to_remove.get_display_name()} removed from team')
                    return redirect('team_detail', team_id=team_id)
                except UserProfile.DoesNotExist:
                    messages.error(request, 'Member not found')
        elif 'delete_team' in request.POST:
            # Delete team - move all members to no team
            team_name = team.name
            all_members = team.members.all()
            for member in all_members:
                member.team = None
                member.save()
            team.delete()
            messages.success(request, f'Team "{team_name}" deleted successfully')
            return redirect('teams_list')
    
    # Get available managers for change manager dropdown
    available_managers = UserProfile.objects.filter(
        role__in=['Manager', 'Director', 'Admin']
    ).exclude(
        team=team
    ).select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
    
    context = {
        'title': f'Team: {team.name}',
        'team': team,
        'managers': managers,
        'members': members,
        'current_profile': current_profile,
        'can_edit_team': can_edit_team,
        'available_managers': available_managers,
    }
    return render(request, 'conversations/team_detail.html', context)


@login_required
def clientes_list(request):
    """List all clients"""
    context = {
        'title': 'Clientes',
    }
    return render(request, 'conversations/placeholder.html', context)


@login_required
def bots_list(request):
    """List all bots"""
    context = {
        'title': 'Bots',
    }
    return render(request, 'conversations/placeholder.html', context)


@login_required
def workspace(request):
    """Workspace view"""
    context = {
        'title': 'Workspace',
    }
    return render(request, 'conversations/placeholder.html', context)


@login_required
def analytics(request):
    """Analytics view"""
    context = {
        'title': 'Analytics',
    }
    return render(request, 'conversations/placeholder.html', context)


@login_required
def agent_detail(request, user_id):
    """View and edit agent details"""
    target_user = get_object_or_404(User, pk=user_id)
    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
    
    # Get current user's profile
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Check if user can access this agent (same organization or admin)
    if not current_profile.is_admin():
        if not current_profile.alma_internal_organization or target_profile.alma_internal_organization != current_profile.alma_internal_organization:
            raise PermissionDenied("You don't have permission to view this agent.")
    
    # Check permissions
    can_edit = current_profile.can_manage_user(target_profile)
    can_change_role = current_profile.can_change_role(target_profile)
    can_view_alma = can_view_alma_uuid(request.user)
    
    if request.method == 'POST' and can_edit:
        form = AgentEditForm(
            request.POST,
            instance=target_user,
            profile_instance=target_profile,
            current_profile=current_profile
        )
        if form.is_valid():
            # Update user fields
            target_user.first_name = form.cleaned_data.get('first_name', '')
            target_user.last_name = form.cleaned_data.get('last_name', '')
            target_user.email = form.cleaned_data.get('email', '')
            
            # Update password if provided (admin-only)
            if current_profile.is_admin() and form.cleaned_data.get('new_password'):
                target_user.set_password(form.cleaned_data['new_password'])
            
            target_user.save()
            
            # Update profile fields
            target_profile.external_uuid = form.cleaned_data.get('external_uuid', '')
            target_profile.cell_phone = form.cleaned_data.get('cell_phone', '')
            
            # Role update - admins can change any role, directors have restrictions
            if current_profile.is_admin():
                # Admins can always change role if it's in the form
                if 'role' in form.cleaned_data:
                    target_profile.role = form.cleaned_data['role']
            elif current_profile.is_director():
                # Directors can only change between User and Manager
                if 'role' in form.cleaned_data:
                    new_role = form.cleaned_data['role']
                    if new_role in ['User', 'Manager']:
                        target_profile.role = new_role
            
            # Team update - managers, directors, and admins can change teams
            # Always update team if user has permission
            if (current_profile.is_manager() or current_profile.is_director() or current_profile.is_admin()):
                # Get team value from form (will be None if "No Team" is selected)
                team_value = form.cleaned_data.get('team')
                # Explicitly set team (even if None to clear it)
                target_profile.team = team_value
            
            # ALMA UUID and Organization can only be set by admins
            if can_view_alma and 'alma_internal_uuid' in form.cleaned_data:
                target_profile.alma_internal_uuid = form.cleaned_data['alma_internal_uuid']
            if can_view_alma and 'alma_internal_organization' in form.cleaned_data:
                target_profile.alma_internal_organization = form.cleaned_data['alma_internal_organization']
            
            try:
                # Validate before saving
                target_profile.full_clean()
                # Save the profile
                target_profile.save()
                messages.success(request, f'Agent {target_profile.get_display_name()} updated successfully!')
                return redirect('agent_detail', user_id=user_id)
            except ValidationError as e:
                # Handle validation errors specifically
                error_messages = []
                if hasattr(e, 'error_dict'):
                    for field, errors in e.error_dict.items():
                        for error in errors:
                            error_messages.append(f"{field}: {error.message}")
                else:
                    error_messages.append(str(e))
                messages.error(request, f'Validation error: {"; ".join(error_messages)}')
            except Exception as e:
                messages.error(request, f'Error updating agent: {str(e)}')
    else:
        form = AgentEditForm(
            instance=target_user,
            profile_instance=target_profile,
            current_profile=current_profile
        )
    
    context = {
        'title': f'Agent: {target_profile.get_display_name()}',
        'form': form,
        'profile': target_profile,
        'target_user': target_user,
        'can_edit': can_edit,
        'can_change_role': can_change_role,
        'can_view_alma': can_view_alma,
        'current_profile': current_profile,
    }
    return render(request, 'conversations/agent_detail.html', context)


@login_required
def profile(request):
    """Profile view - display and edit user profile"""
    # Get or create user profile
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user, profile_instance=profile_obj)
        if form.is_valid():
            # Update user fields
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            
            # Update profile fields
            profile_obj.external_uuid = form.cleaned_data.get('external_uuid', '')
            profile_obj.cell_phone = form.cleaned_data.get('cell_phone', '')
            profile_obj.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user, profile_instance=profile_obj)
    
    context = {
        'title': 'Profile',
        'form': form,
        'profile': profile_obj,
        'user': request.user,
    }
    return render(request, 'conversations/profile.html', context)

