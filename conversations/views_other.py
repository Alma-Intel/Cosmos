"""
Views for other sections: Agentes, Clientes, Bots, Workspace
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


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

