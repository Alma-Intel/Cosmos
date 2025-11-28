"""
Permission helpers for role-based access control
"""
from django.core.exceptions import PermissionDenied
from .models import UserProfile


def require_role(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            if profile.role not in allowed_roles:
                raise PermissionDenied("You don't have permission to access this page.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def can_view_alma_uuid(user):
    """Check if user can view ALMA internal UUID"""
    if not user.is_authenticated:
        return False
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.is_admin()


def get_user_team_members(user):
    """Get all team members that a user can manage"""
    if not user.is_authenticated:
        return UserProfile.objects.none()
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if profile.is_admin():
        # Admins can see everyone
        return UserProfile.objects.all().select_related('user', 'team')
    
    if profile.is_director():
        # Directors can see everyone
        return UserProfile.objects.all().select_related('user', 'team')
    
    if profile.is_manager() and profile.team:
        # Managers can see their team members
        return UserProfile.objects.filter(team=profile.team).select_related('user', 'team')
    
    # Regular users can only see themselves
    return UserProfile.objects.filter(user=user).select_related('user', 'team')

