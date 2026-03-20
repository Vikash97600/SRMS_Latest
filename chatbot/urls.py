from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat_view'),
    path('api/', views.chat_api, name='chat_api'),
    path('history/', views.get_chat_history, name='chat_history'),
    path('clear/', views.clear_chat, name='clear_chat'),
    path('test/', views.test_chatbot, name='test_chatbot'),
]
