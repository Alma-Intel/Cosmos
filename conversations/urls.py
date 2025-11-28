"""
URL configuration for conversations app
"""
from django.urls import path
from . import views
from . import views_other

urlpatterns = [
    # Workspace (root)
    path('', views_other.workspace, name='workspace'),
    
    # Conversations routes
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/conversation/<str:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    
    # Other sections
    path('agentes/', views_other.agentes_list, name='agentes_list'),
    path('agentes/create/', views_other.agent_create, name='agent_create'),
    path('agentes/teams/create/', views_other.team_create, name='team_create'),
    path('agentes/<uuid:profile_id>/', views_other.agent_detail, name='agent_detail'),
    path('teams/', views_other.teams_list, name='teams_list'),
    path('teams/<uuid:team_id>/', views_other.team_detail, name='team_detail'),
    path('clientes/', views_other.clientes_list, name='clientes_list'),
    path('bots/', views_other.bots_list, name='bots_list'),
    path('analytics/', views_other.analytics, name='analytics'),
    path('profile/', views_other.profile, name='profile'),
]

