"""
Custom template filters for user-related display
"""
from django import template

register = template.Library()


@register.filter
def display_name(user_or_profile):
    """
    Returns the user's display name: first_name + last_name if available,
    otherwise username.
    Accepts both User and UserProfile objects.
    """
    if not user_or_profile:
        return ""
    
    # Handle UserProfile objects
    if hasattr(user_or_profile, 'user'):
        user = user_or_profile.user
    else:
        # It's already a User object
        user = user_or_profile
    
    if user.first_name or user.last_name:
        # Join first and last name, strip extra whitespace
        name_parts = [part for part in [user.first_name, user.last_name] if part]
        return " ".join(name_parts).strip()
    
    return user.username

