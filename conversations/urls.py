"""
URL configuration for conversations app
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('conversation/<str:conversation_id>/', views.conversation_detail, name='conversation_detail'),
]

