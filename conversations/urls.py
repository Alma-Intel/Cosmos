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
    path('clientes/', views_other.clientes_list, name='clientes_list'),
    path('bots/', views_other.bots_list, name='bots_list'),
]

