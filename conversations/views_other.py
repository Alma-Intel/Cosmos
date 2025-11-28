"""
Views for other sections: Agentes, Clientes, Bots, Workspace
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .forms import ProfileForm


@login_required
def agentes_list(request):
    """List all agents"""
    context = {
        'title': 'Agentes',
    }
    return render(request, 'conversations/placeholder.html', context)


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

