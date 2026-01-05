"""
Views for other sections: Agentes, Clientes, Bots, Workspace
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
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
                    return redirect('agent_detail', profile_id=profile.id)
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
    
    # Check if user is a manager of this team (can add/remove members but not delete team or manage managers)
    is_team_manager = (current_profile.is_manager() and 
                       current_profile.team == team and 
                       current_profile.role in ['Manager', 'Director', 'Admin'])
    
    # Can manage members (add/remove) - admins, directors, or team managers
    can_manage_members = can_edit_team or is_team_manager
    
    # Get managers/directors in this team
    managers = team.members.filter(role__in=['Manager', 'Director', 'Admin']).select_related('user').order_by('user__last_name', 'user__first_name')
    
    # Get all members excluding the managers (those shown in the Managers section)
    # Exclude by getting manager IDs and excluding them from members
    manager_ids = managers.values_list('id', flat=True)
    members = team.members.exclude(id__in=manager_ids).select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
    
    # Handle POST requests for team management
    if request.method == 'POST':
        if 'add_member' in request.POST:
            # Admins, directors, and team managers can add members
            if not can_manage_members:
                raise PermissionDenied("You don't have permission to add members to this team.")
            member_id = request.POST.get('member_id')
            if member_id:
                try:
                    member_to_add = UserProfile.objects.get(pk=member_id)
                    # Verify member is from same organization
                    if team.alma_internal_organization and member_to_add.alma_internal_organization != team.alma_internal_organization:
                        messages.error(request, 'Selected user must be from the same organization as the team.')
                    else:
                        member_to_add.team = team
                        member_to_add.save()
                        messages.success(request, f'Member {member_to_add.get_display_name()} added to team')
                        return redirect('team_detail', team_id=team_id)
                except UserProfile.DoesNotExist:
                    messages.error(request, 'Selected member not found')
        elif 'change_manager' in request.POST:
            # Only admins and directors can add managers
            if not can_edit_team:
                raise PermissionDenied("You don't have permission to add managers to this team.")
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
            # Only admins and directors can remove managers
            if not can_edit_team:
                raise PermissionDenied("You don't have permission to remove managers from this team.")
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
            # Admins, directors, and team managers can remove members
            if not can_manage_members:
                raise PermissionDenied("You don't have permission to remove members from this team.")
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
            # Only admins and directors can delete teams
            if not can_edit_team:
                raise PermissionDenied("You don't have permission to delete this team.")
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
    # Always filter by team's organization (even for admins)
    available_managers_query = UserProfile.objects.filter(
        role__in=['Manager', 'Director', 'Admin']
    ).exclude(
        team=team
    )
    
    # Filter by team's organization - applies to everyone including admins
    if team.alma_internal_organization:
        available_managers_query = available_managers_query.filter(
            alma_internal_organization=team.alma_internal_organization
        )
    else:
        # If team has no organization, only show managers with no organization
        available_managers_query = available_managers_query.filter(
            alma_internal_organization__isnull=True
        ) | available_managers_query.filter(
            alma_internal_organization=''
        )
    
    available_managers = available_managers_query.select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
    
    # Get available members to add to team (users not already in this team, from same organization)
    available_members_query = UserProfile.objects.exclude(team=team)
    
    # Filter by team's organization
    if team.alma_internal_organization:
        available_members_query = available_members_query.filter(
            alma_internal_organization=team.alma_internal_organization
        )
    else:
        # If team has no organization, only show users with no organization
        available_members_query = available_members_query.filter(
            alma_internal_organization__isnull=True
        ) | available_members_query.filter(
            alma_internal_organization=''
        )
    
    available_members = available_members_query.select_related('user').order_by('user__last_name', 'user__first_name', 'user__username')
    
    # Check if user can view ALMA fields (admin only)
    from .permissions import can_view_alma_uuid
    can_view_alma = can_view_alma_uuid(request.user)
    
    context = {
        'title': f'Team: {team.name}',
        'team': team,
        'managers': managers,
        'members': members,
        'current_profile': current_profile,
        'can_edit_team': can_edit_team,
        'can_manage_members': can_manage_members,
        'available_managers': available_managers,
        'available_members': available_members,
        'can_view_alma': can_view_alma,
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
    from django.conf import settings
    
    bots = [
        {
            'uuid': 'bot_001',
            'name': 'MedCof Assistente Virtual',
            'description': 'Responsável por resolução de dúvidas e encaminhamento de leads para o time de vendas da MedCof.',
            'platform': 'Chatbase',
            'url': 'https://www.chatbase.co/chatbot-iframe/',
            'status': 'active',
            'chatbase_id': settings.CHATBASE_AGENT_ID,
            'corporation': 'MedCof',
            'created_at': '2026-01-05'
        }
    ]

    context = {
        'title': 'Gerenciamento de Bots',
        'bots': bots,
    }
    
    return render(request, 'conversations/bots_list.html', context)


@login_required
def workspace(request):
    """Workspace view"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    is_manager_plus = profile and (profile.is_manager() or profile.is_director() or profile.is_admin())
    
    mode = request.GET.get('mode', 'agent')
    
    if mode == 'supervisor' and not is_manager_plus:
        return redirect('workspace')
        
    if mode == 'supervisor':
        return _workspace_supervisor_view(request, profile)
    else:
        return _workspace_agent_view(request, profile, is_manager_plus)

def _workspace_agent_view(request, user_profile, can_switch_view):
    """Workspace view"""
    import json
    from .followups import (get_followups_for_agent, 
                            get_link_tracking_from_agent,
                            get_conversation_id,
                            create_infobip_conversation_link
                            )
    from .analytics_metrics import ( get_stage_scores, 
                                    get_metrics_for_agent,
                                    get_metrics_for_team_members)
    
    if not user_profile:
        user_profile = getattr(request.user, 'profile', None)

    external_uuid = user_profile.external_uuid if user_profile else None
    team_members = get_user_team_members(request.user)
    team_uuids = [p.external_uuid for p in team_members if p.external_uuid]

    all_followups = get_followups_for_agent(external_uuid)
    all_links = get_link_tracking_from_agent(external_uuid)

    followups_dict = {}

    for link in all_links:
        baseUrl = "https://followupsbot-prod.up.railway.app/r/"
        link_url = link['original_url']
        slug = link['slug']
        if link_url:
            conversation_id = get_conversation_id(link_url, "conversationId=", "&")
            if conversation_id:
                if slug:
                    followups_dict[conversation_id] = baseUrl + slug
                else:
                    followups_dict[conversation_id] = link_url

    now = timezone.now()
    end = (now + timezone.timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

    high_priority_tasks = []
    low_priority_tasks = []
    calendar_events = []

    for task in all_followups:
        conversation_id_str = str(task['conversation_uuid'])
        task['original_url'] = followups_dict.get(conversation_id_str)

        if not task['original_url']:
            task['original_url'] = create_infobip_conversation_link(conversation_id_str)

        task_date = task['follow_up_date']

        if timezone.is_naive(task_date):
            task_date = timezone.make_aware(task_date)
            task['follow_up_date'] = task_date

        is_high_priority = False 

        if task_date <= now and task['score'] >= 700:
            if len(high_priority_tasks) <= 5:
                high_priority_tasks.append(task)
                is_high_priority = True

        if not is_high_priority:
            if task_date <= end:
                low_priority_tasks.append(task)

    all_tasks_for_calendar = high_priority_tasks + low_priority_tasks

    for task in all_tasks_for_calendar:
        event = {
            'title': f"Score: {task['score']}", 
            'start': task['follow_up_date'].isoformat(),
            'url': task.get('original_url') or '#',
            'backgroundColor': '#e53e3e' if task['score'] >= 700 else '#38a169',
            'borderColor': '#e53e3e' if task['score'] >= 700 else '#38a169',
            'allDay': True
        }
        calendar_events.append(event)

    high_priority_tasks.sort(key=lambda x: (-x['score'], x['follow_up_date']))
    high_priority_tasks = high_priority_tasks[:5]

    low_priority_tasks.sort(key=lambda x: (x['follow_up_date'], -x['score']))
    low_priority_tasks = low_priority_tasks[:10]

    metrics_data = get_metrics_for_agent(external_uuid)
    members_data = get_metrics_for_team_members(team_uuids)
    scores_data = get_stage_scores(metrics_data, members_data)

    context = {
        'title': 'Agent Workspace',
        'high_priority_tasks': high_priority_tasks,
        'metrics': scores_data,
        'can_switch_view': can_switch_view,
        'current_view': 'agent',
        'calendar_events_json': json.dumps(calendar_events)
    }
    
    return render(request, 'conversations/workspace_agent.html', context)

def _workspace_supervisor_view(request, profile):
    from .events_db import ( get_sales_stage_metrics )
    from .analytics_utils import ( get_clients_analysis )
    from .analytics_metrics import ( get_team_summary_stats )
    
    team_members = get_user_team_members(request.user)
    team_uuids = [p.external_uuid for p in team_members if p.external_uuid]
    team_summary = get_team_summary_stats(team_members)

    sales_data = get_sales_stage_metrics(team_uuids)

    funnel_raw = sales_data.get('stages', {})
    sorted_items = sorted(funnel_raw.items(), key=lambda x: x[1], reverse=True)

    clients_data, _, global_analyses = get_clients_analysis()
    
    funnel_data = {
        'labels': [item[0] for item in sorted_items],
        'data': [item[1] for item in sorted_items]
    }

    critical_cases = []
    cases = global_analyses.get('critical_cases', []) if global_analyses else []
    
    if clients_data:
        critical_cases = [
            c for c in cases 
            if c.get('risk_level', '').lower() == 'high' 
            or c.get('risk_score', 0) >= 80
        ]
        critical_cases.sort(key=lambda x: x.get('risk_score', 0), reverse=True)

    context = {
        'title': 'Supervisor Workspace',
        'current_view': 'supervisor',
        'can_switch_view': True,
        'funnel_data': funnel_data,
        'critical_count': len(critical_cases),
        'team_summary': team_summary,
        'top_critical_cases': critical_cases[:5],
    }
    
    return render(request, 'conversations/workspace_supervisor.html', context)

@login_required
def team_performance_detail(request):
    from .analytics_metrics import (
                                    get_metrics_for_agent, 
                                    calculate_agent_scores,
                                    get_objections_from_database,
                                    format_objection_data)
    from datetime import timedelta
    
    try:
        days_param = int(request.GET.get('days', 30))
    except ValueError:
        days_param = 30
        
    start_date = timezone.now() - timedelta(days=days_param)

    team_members = get_user_team_members(request.user)
    user, _ = UserProfile.objects.get_or_create(user=request.user)
    team_name = None

    if user and user.team:
        if user.team.name is not None:
            team_name = user.team.name

    team_aggregates = {
        'total_conversations': 0,
        'total_sales': 0,
        'meetings_scheduled': 0,
        'referrals_received': 0,
        'total_follow_ups': 0,
        'sum_performance': 0,
        'count_performance': 0,
        
        'sum_followup_rate': 0,
        'sum_meeting_attempt': 0,
        'sum_meeting_success': 0,
        'sum_referral_req': 0,
        'sum_discount_strat': 0,
        'sum_objection_res': 0,
        'active_agents_count': 0
    }

    sellers_analytics = []

    for member in team_members:
        analysis_list = get_metrics_for_agent(member.external_uuid, start_date=start_date)
        agent_data = calculate_agent_scores(member, analysis_list)
        
        if not agent_data: continue

        sellers_analytics.append(agent_data)

        team_aggregates['total_conversations'] += agent_data.get('total_conversations', 0)
        team_aggregates['total_sales'] += agent_data.get('total_sales', 0)
        team_aggregates['meetings_scheduled'] += agent_data.get('meetings_scheduled', 0)
        team_aggregates['referrals_received'] += agent_data.get('referrals_received', 0)
        team_aggregates['total_follow_ups'] += agent_data.get('total_followups', 0)
        
        team_aggregates['sum_performance'] += agent_data.get('avg_performance', 0)
        team_aggregates['count_performance'] += 1 if agent_data.get('avg_performance', 0) > 0 else 0

        team_aggregates['sum_followup_rate'] += agent_data.get('follow_up_rate', 0)
        team_aggregates['sum_meeting_attempt'] += agent_data.get('meeting_attempt_rate', 0)
        team_aggregates['sum_meeting_success'] += agent_data.get('meeting_success_rate', 0)
        team_aggregates['sum_referral_req'] += agent_data.get('referral_request_rate', 0)
        team_aggregates['sum_discount_strat'] += agent_data.get('discount_strategy_rate', 0)
        team_aggregates['sum_objection_res'] += agent_data.get('objection_resolution_rate', 0)
        
        team_aggregates['active_agents_count'] += 1

    num_agents = team_aggregates['active_agents_count'] if team_aggregates['active_agents_count'] > 0 else 1
    
    team_conversion_rate = 0
    if team_aggregates['total_conversations'] > 0:
        team_conversion_rate = (team_aggregates['total_sales'] / team_aggregates['total_conversations']) * 100

    team_uuids = [p.external_uuid for p in team_members if p.external_uuid]
    objection_list = get_objections_from_database(team_uuids, start_date=start_date)

    team_members_dict = {}
    for member in team_members:
        team_members_dict[member.external_uuid] = member.get_display_name()

    objection_analysis = format_objection_data(objection_list, team_members_dict)

    team_data = {
        'team_name': team_name,
        'seller_analytics': sellers_analytics,
        'objection_analysis': objection_analysis,
        
        'total_conversations': team_aggregates['total_conversations'],
        'meetings_scheduled': team_aggregates['meetings_scheduled'],
        'referrals_received': team_aggregates['referrals_received'],
        'total_follow_ups': team_aggregates['total_follow_ups'],
        
        'conversion_rate': round(team_conversion_rate, 2),
        'avg_performance': round(team_aggregates['sum_performance'] / num_agents, 2),
        
        'follow_up_rate': round(team_aggregates['sum_followup_rate'] / num_agents, 1),
        'meeting_attempt_rate': round(team_aggregates['sum_meeting_attempt'] / num_agents, 1),
        'meeting_success_rate': round(team_aggregates['sum_meeting_success'] / num_agents, 1),
        'referral_request_rate': round(team_aggregates['sum_referral_req'] / num_agents, 1),
        'discount_strategy_rate': round(team_aggregates['sum_discount_strat'] / num_agents, 1),
        'objection_resolution_rate': round(team_aggregates['sum_objection_res'] / num_agents, 1),
        
        'referral_conversion_rate': 0,
        'avg_seller_messages': 0,
    }

    context = {
        'title': 'Team Performance Analysis',
        'team_data': team_data,
        'current_days': days_param,
    }
    
    return render(request, 'conversations/analytics_team_performance_detail.html', context)

@login_required
def analytics(request):
    """Analytics dashboard - main entry point"""
    from .analytics_utils import (
        get_cx_volumetrics, get_friction_heuristics, get_temporal_heat,
        get_churn_risk_monitor, get_sales_velocity, get_segmentation_matrix,
        get_summary_stats, get_clients_analysis
    )
    
    # Get critical cases count
    clients, metadata, global_analyses = get_clients_analysis()
    critical_cases_count = 0
    if global_analyses and 'critical_cases' in global_analyses:
        critical_cases_count = len(global_analyses.get('critical_cases', []))
    
    # Get summary stats for each dataset
    datasets = {
        'critical_cases': {
            'name': 'Critical Cases',
            'description': f'High-risk clients requiring immediate attention ({critical_cases_count} cases)',
            'stats': {'row_count': critical_cases_count, 'column_count': 0, 'columns': []},
            'url': 'analytics_critical_cases'
        },
        'cx_volumetrics': {
            'name': 'CX Volumetrics',
            'description': 'Manager-Client pairs with interaction velocity, neediness ratio, load metrics',
            'stats': get_summary_stats(get_cx_volumetrics()),
            'url': 'analytics_cx_volumetrics'
        },
        'friction_heuristics': {
            'name': 'Friction Heuristics',
            'description': 'Individual interactions flagged with urgency/failure/escalation scores',
            'stats': get_summary_stats(get_friction_heuristics()),
            'url': 'analytics_friction_heuristics'
        },
        'temporal_heat': {
            'name': 'Temporal Heatmap',
            'description': 'Heatmap data (DayOfWeek × Hour) for volume and friction patterns',
            'stats': get_summary_stats(get_temporal_heat()),
            'url': 'analytics_temporal_heat'
        },
        'churn_risk': {
            'name': 'Churn Risk Monitor',
            'description': 'Churn risk scores by client',
            'stats': get_summary_stats(get_churn_risk_monitor()),
            'url': 'analytics_churn_risk'
        },
        'sales_velocity': {
            'name': 'Sales Velocity',
            'description': 'Sales pipeline velocity metrics',
            'stats': get_summary_stats(get_sales_velocity()),
            'url': 'analytics_sales_velocity'
        },
        'segmentation_matrix': {
            'name': 'Segmentation Matrix',
            'description': 'Client segmentation matrix',
            'stats': get_summary_stats(get_segmentation_matrix()),
            'url': 'analytics_segmentation_matrix'
        }
    }
    
    context = {
        'title': 'Analytics Dashboard',
        'datasets': datasets,
    }
    return render(request, 'conversations/analytics_dashboard.html', context)


@login_required
def analytics_cx_volumetrics(request):
    """CX Volumetrics analytics view"""
    from .analytics_utils import get_cx_volumetrics, get_data_slice, get_summary_stats
    
    data = get_cx_volumetrics()
    stats = get_summary_stats(data)
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if data is not None and len(data) > 0:
        paginated_data = data[start_idx:end_idx]
        total_pages = (len(data) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    context = {
        'title': 'CX Volumetrics',
        'data': paginated_data,
        'stats': stats,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
    }
    return render(request, 'conversations/analytics_detail.html', context)


@login_required
def analytics_friction_heuristics(request):
    """Friction Heuristics analytics view"""
    from .analytics_utils import get_friction_heuristics, get_data_slice, get_summary_stats
    
    data = get_friction_heuristics()
    stats = get_summary_stats(data)
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if data is not None and len(data) > 0:
        paginated_data = data[start_idx:end_idx]
        total_pages = (len(data) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    context = {
        'title': 'Friction Heuristics',
        'data': paginated_data,
        'stats': stats,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
    }
    return render(request, 'conversations/analytics_detail.html', context)


@login_required
def analytics_temporal_heat(request):
    """Temporal Heatmap analytics view - displays as visual heatmap"""
    from .analytics_utils import get_temporal_heat, get_summary_stats
    
    data = get_temporal_heat()
    stats = get_summary_stats(data)
    
    # Get available metrics for dropdown (exclude day_of_week, day_name, hour)
    available_metrics = []
    available_metrics_display = []
    if data is not None and len(data) > 0:
        # Get columns from first record
        all_columns = list(data[0].keys()) if data else []
        available_metrics = [col for col in all_columns if col not in ['day_of_week', 'day_name', 'hour']]
        # Format metric names for display (replace underscores with spaces, title case)
        for metric in available_metrics:
            display_name = metric.replace('_', ' ').title()
            available_metrics_display.append({
                'value': metric,
                'display': display_name
            })
    
    # Get metric type from query parameter (default to first available or interaction_count)
    requested_metric = request.GET.get('metric', '')
    if requested_metric and requested_metric in available_metrics:
        metric_type = requested_metric
    elif available_metrics:
        metric_type = available_metrics[0]
    else:
        metric_type = 'interaction_count'
    
    # Prepare heatmap data as a list of lists for easier template access
    heatmap_data = []
    max_value = 0
    min_value = 0
    has_heatmap_data = False
    
    if data is not None and len(data) > 0:
        # Build a dictionary keyed by (day_of_week, hour) for quick lookup
        data_dict = {}
        for record in data:
            day = record.get('day_of_week', 0)
            hour = record.get('hour', 0)
            value = record.get(metric_type, 0) or 0
            key = (day, hour)
            # Sum if multiple records for same day/hour
            if key in data_dict:
                data_dict[key] += float(value)
            else:
                data_dict[key] = float(value)
        
        # Convert to list of lists for template (7 days × 24 hours)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in range(7):  # 0-6 for Monday-Sunday
            day_row = {
                'day_name': day_names[day],
                'day_num': day,
                'hours': []
            }
            for hour in range(24):  # 0-23
                key = (day, hour)
                value = float(data_dict.get(key, 0))
                day_row['hours'].append({
                    'hour': hour,
                    'value': value
                })
                max_value = max(max_value, value)
                min_value = min(min_value, value)
            heatmap_data.append(day_row)
        
        has_heatmap_data = len(heatmap_data) > 0
    
    # Get display name for current metric
    metric_display = metric_type.replace('_', ' ').title()
    
    context = {
        'title': 'Temporal Heatmap',
        'heatmap_data': heatmap_data,
        'has_heatmap_data': has_heatmap_data,
        'stats': stats,
        'metric_type': metric_type,
        'metric_display': metric_display,
        'available_metrics': available_metrics,
        'available_metrics_display': available_metrics_display,
        'max_value': max_value,
        'min_value': min_value,
    }
    return render(request, 'conversations/analytics_temporal_heat.html', context)


@login_required
def analytics_churn_risk(request):
    """Churn Risk Monitor analytics view with sorting and time window filtering - uses clients_analysis_20251211_055217.json"""
    from .analytics_utils import get_clients_analysis, get_data_slice, get_summary_stats, transform_clients_for_time_window
    
    clients, metadata, global_analyses = get_clients_analysis()
    
    # Get time window filter (default to last_6_months)
    time_window = request.GET.get('time_window', 'last_6_months')
    available_time_windows = metadata.get('time_windows_available', ['last_week', 'last_month', 'last_3_months', 'last_6_months', 'last_year'])
    
    # Validate time window
    if time_window not in available_time_windows:
        time_window = 'last_6_months'
    
    # Transform clients data to show metrics from selected time window
    data = transform_clients_for_time_window(clients, time_window) if clients else []
    stats = get_summary_stats(data)
    
    # Get sorting parameters
    sort_column = request.GET.get('sort', '')
    sort_order = request.GET.get('order', 'asc')  # 'asc' or 'desc'
    
    # Sort data if sort column is specified
    if data is not None and len(data) > 0 and sort_column:
        if sort_column in data[0].keys():
            # Helper function to determine if value is numeric
            def is_numeric(value):
                if value is None:
                    return False
                if isinstance(value, list):
                    return False
                try:
                    float(str(value))
                    return True
                except (ValueError, TypeError):
                    return False
            
            # Check if all values in column are numeric
            sample_values = [record.get(sort_column) for record in data[:10] if record.get(sort_column) is not None and not isinstance(record.get(sort_column), list)]
            all_numeric = all(is_numeric(v) for v in sample_values) if sample_values else False
            
            if all_numeric:
                # Sort as numeric
                def numeric_key(x):
                    val = x.get(sort_column)
                    if val is None or isinstance(val, list):
                        return float('-inf') if sort_order == 'desc' else float('inf')
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0
                data = sorted(data, key=numeric_key, reverse=(sort_order == 'desc'))
            else:
                # Sort as string (handle lists by joining them)
                def string_key(x):
                    val = x.get(sort_column)
                    if val is None:
                        return '' if sort_order == 'desc' else 'zzz'
                    if isinstance(val, list):
                        return ', '.join(str(v) for v in val).lower()
                    return str(val).lower()
                data = sorted(data, key=string_key, reverse=(sort_order == 'desc'))
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if data is not None and len(data) > 0:
        paginated_data = data[start_idx:end_idx]
        total_pages = (len(data) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    # Build query string for pagination (preserve sort and time_window parameters)
    query_params = []
    if time_window:
        query_params.append(f'time_window={time_window}')
    if sort_column:
        query_params.append(f'sort={sort_column}')
    if sort_order:
        query_params.append(f'order={sort_order}')
    query_string = '&'.join(query_params)
    if query_string:
        query_string = '&' + query_string
    else:
        query_string = ''
    
    # Build query string for time window filter (preserve sort parameters)
    time_window_query_params = []
    if sort_column:
        time_window_query_params.append(f'sort={sort_column}')
    if sort_order and sort_order != 'asc':
        time_window_query_params.append(f'order={sort_order}')
    time_window_query_string = '&'.join(time_window_query_params)
    if time_window_query_string:
        time_window_query_string = '&' + time_window_query_string
    else:
        time_window_query_string = ''
    
    # Create time window options for dropdown
    time_window_options = []
    window_labels = {
        'last_week': 'Last Week',
        'last_month': 'Last Month',
        'last_3_months': 'Last 3 Months',
        'last_6_months': 'Last 6 Months',
        'last_year': 'Last Year'
    }
    for window in available_time_windows:
        time_window_options.append({
            'value': window,
            'label': window_labels.get(window, window.replace('_', ' ').title()),
            'selected': window == time_window
        })
    
    context = {
        'title': 'Client Analysis & Risk Monitor',
        'data': paginated_data,
        'stats': stats,
        'metadata': metadata,
        'global_analyses': global_analyses,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'sort_column': sort_column,
        'sort_order': sort_order,
        'query_string': query_string,
        'time_window_query_string': time_window_query_string,
        'time_window': time_window,
        'time_window_options': time_window_options,
    }
    return render(request, 'conversations/analytics_detail.html', context)


@login_required
def analytics_sales_velocity(request):
    """Sales Velocity analytics view"""
    from .analytics_utils import get_sales_velocity, get_data_slice, get_summary_stats
    
    data = get_sales_velocity()
    stats = get_summary_stats(data)
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if data is not None and len(data) > 0:
        paginated_data = data[start_idx:end_idx]
        total_pages = (len(data) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    context = {
        'title': 'Sales Velocity',
        'data': paginated_data,
        'stats': stats,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
    }
    return render(request, 'conversations/analytics_detail.html', context)


@login_required
def analytics_segmentation_matrix(request):
    """Segmentation Matrix analytics view"""
    from .analytics_utils import get_segmentation_matrix, get_data_slice, get_summary_stats
    
    data = get_segmentation_matrix()
    stats = get_summary_stats(data)
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if data is not None and len(data) > 0:
        paginated_data = data[start_idx:end_idx]
        total_pages = (len(data) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    context = {
        'title': 'Segmentation Matrix',
        'data': paginated_data,
        'stats': stats,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
    }
    return render(request, 'conversations/analytics_detail.html', context)


@login_required
def analytics_critical_cases(request):
    """Critical Cases analytics view - displays high-risk clients requiring immediate attention"""
    from .analytics_utils import get_clients_analysis, get_summary_stats
    
    clients, metadata, global_analyses = get_clients_analysis()
    critical_cases = global_analyses.get('critical_cases', []) if global_analyses else []
    
    # Get sorting parameters
    sort_column = request.GET.get('sort', '')
    sort_order = request.GET.get('order', 'asc')  # 'asc' or 'desc'
    
    # Sort data if sort column is specified
    if critical_cases and len(critical_cases) > 0 and sort_column:
        if sort_column in critical_cases[0].keys():
            # Helper function to determine if value is numeric
            def is_numeric(value):
                if value is None:
                    return False
                if isinstance(value, list):
                    return False
                if isinstance(value, dict):
                    return False
                try:
                    float(str(value))
                    return True
                except (ValueError, TypeError):
                    return False
            
            # Check if all values in column are numeric
            sample_values = [record.get(sort_column) for record in critical_cases[:10] 
                           if record.get(sort_column) is not None 
                           and not isinstance(record.get(sort_column), (list, dict))]
            all_numeric = all(is_numeric(v) for v in sample_values) if sample_values else False
            
            if all_numeric:
                # Sort as numeric
                def numeric_key(x):
                    val = x.get(sort_column)
                    if val is None or isinstance(val, (list, dict)):
                        return float('-inf') if sort_order == 'desc' else float('inf')
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0
                critical_cases = sorted(critical_cases, key=numeric_key, reverse=(sort_order == 'desc'))
            else:
                # Sort as string (handle lists by joining them)
                def string_key(x):
                    val = x.get(sort_column)
                    if val is None:
                        return '' if sort_order == 'desc' else 'zzz'
                    if isinstance(val, list):
                        return ', '.join(str(v) for v in val).lower()
                    if isinstance(val, dict):
                        return str(val).lower()
                    return str(val).lower()
                critical_cases = sorted(critical_cases, key=string_key, reverse=(sort_order == 'desc'))
    
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 20  # Fewer per page since these are detailed cases
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get data for current page
    if critical_cases and len(critical_cases) > 0:
        paginated_data = critical_cases[start_idx:end_idx]
        total_pages = (len(critical_cases) + per_page - 1) // per_page
    else:
        paginated_data = []
        total_pages = 0
    
    # Build query string for pagination (preserve sort parameters)
    query_params = []
    if sort_column:
        query_params.append(f'sort={sort_column}')
    if sort_order:
        query_params.append(f'order={sort_order}')
    query_string = '&'.join(query_params)
    if query_string:
        query_string = '&' + query_string
    else:
        query_string = ''
    
    # Get summary stats
    stats = {
        'row_count': len(critical_cases) if critical_cases else 0,
        'column_count': len(critical_cases[0].keys()) if critical_cases and len(critical_cases) > 0 else 0,
        'columns': list(critical_cases[0].keys()) if critical_cases and len(critical_cases) > 0 else []
    }
    
    context = {
        'title': 'Critical Cases',
        'data': paginated_data,
        'stats': stats,
        'metadata': metadata,
        'current_page': page,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'previous_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'sort_column': sort_column,
        'sort_order': sort_order,
        'query_string': query_string,
    }
    return render(request, 'conversations/analytics_critical_cases.html', context)


@login_required
def agent_detail(request, profile_id):
    """View and edit agent details"""
    target_profile = get_object_or_404(UserProfile, pk=profile_id)
    target_user = target_profile.user
    
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
                return redirect('agent_detail', profile_id=profile_id)
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
            
            # Update password if provided
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                request.user.set_password(new_password)
                messages.success(request, 'Password changed successfully!')
            
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

