"""
Views for other sections: Agentes, Clientes, Bots, Workspace
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from .models import UserProfile, Team
from .forms import ProfileForm, AgentEditForm, UserCreateForm
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
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', ''),
                )
                
                # Create the user profile
                profile = UserProfile.objects.create(
                    user=user,
                    role=form.cleaned_data['role'],
                    team=form.cleaned_data.get('team'),
                    external_uuid=form.cleaned_data.get('external_uuid', ''),
                    cell_phone=form.cleaned_data.get('cell_phone', ''),
                    alma_internal_uuid=form.cleaned_data.get('alma_internal_uuid', '') if current_profile.is_admin() else '',
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
def agentes_list(request):
    """List all agents/users with filtering"""
    # Get all users that the current user can view
    profiles = get_user_team_members(request.user)
    
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
    all_teams = Team.objects.all().order_by('name')
    
    # Get current user's profile for permission checks
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
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
            target_user.first_name = form.cleaned_data['first_name']
            target_user.last_name = form.cleaned_data['last_name']
            target_user.email = form.cleaned_data['email']
            target_user.save()
            
            # Update profile fields
            target_profile.external_uuid = form.cleaned_data.get('external_uuid', '')
            target_profile.cell_phone = form.cleaned_data.get('cell_phone', '')
            
            # Role and team can only be changed by authorized users
            if can_change_role and 'role' in form.cleaned_data:
                new_role = form.cleaned_data['role']
                # Validate role change
                if current_profile.is_admin():
                    # Admins can change to any role
                    target_profile.role = new_role
                elif current_profile.is_director() and new_role in ['User', 'Manager']:
                    # Directors can only change between User and Manager
                    target_profile.role = new_role
            
            # Team can be changed by managers, directors, and admins
            if (current_profile.is_manager() or current_profile.is_director() or current_profile.is_admin()):
                if 'team' in form.cleaned_data:
                    if form.cleaned_data['team']:
                        target_profile.team = form.cleaned_data['team']
                    else:
                        target_profile.team = None
            
            # ALMA UUID can only be set by admins
            if can_view_alma and 'alma_internal_uuid' in form.cleaned_data:
                target_profile.alma_internal_uuid = form.cleaned_data['alma_internal_uuid']
            
            try:
                target_profile.full_clean()
                target_profile.save()
                messages.success(request, f'Agent {target_profile.get_display_name()} updated successfully!')
                return redirect('agent_detail', user_id=user_id)
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
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            
            # Update profile fields
            profile_obj.external_uuid = form.cleaned_data['external_uuid']
            profile_obj.cell_phone = form.cleaned_data['cell_phone']
            profile_obj.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user, profile_instance=profile_obj)
    
    context = {
        'title': 'Profile',
        'form': form,
        'profile': profile_obj,
    }
    return render(request, 'conversations/profile.html', context)

