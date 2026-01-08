"""
URL configuration for conversations app
"""
from django.urls import path
from . import views
from . import views_other
from . import admin_views

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
    path('analytics/cx-volumetrics/', views_other.analytics_cx_volumetrics, name='analytics_cx_volumetrics'),
    path('analytics/friction-heuristics/', views_other.analytics_friction_heuristics, name='analytics_friction_heuristics'),
    path('analytics/temporal-heat/', views_other.analytics_temporal_heat, name='analytics_temporal_heat'),
    path('analytics/churn-risk/', views_other.analytics_churn_risk, name='analytics_churn_risk'),
    path('analytics/critical-cases/', views_other.analytics_critical_cases, name='analytics_critical_cases'),
    path('analytics/sales-velocity/', views_other.analytics_sales_velocity, name='analytics_sales_velocity'),
    path('analytics/segmentation-matrix/', views_other.analytics_segmentation_matrix, name='analytics_segmentation_matrix'),
    path('analytics/team-performance/', views_other.team_performance_detail, name='team_performance_detail'),
    path('profile/', views_other.profile, name='profile'),
    
    # Admin Panel (only for admins)
    path('admin-panel/', admin_views.admin_panel, name='admin_panel'),
    path('admin-panel/create-organization/', admin_views.admin_create_organization, name='admin_create_organization'),
    path('admin-panel/organizations/', admin_views.admin_organizations_list, name='admin_organizations_list'),
    path('admin-panel/organizations/<str:org_uuid>/', admin_views.admin_organization_detail, name='admin_organization_detail'),
]

