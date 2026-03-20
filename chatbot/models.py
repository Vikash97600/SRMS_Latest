from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class ChatMessage(models.Model):
    """
    Model to store chat messages between user and AI chatbot
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField(help_text="User's message/query")
    response = models.TextField(help_text="AI's response", blank=True, null=True)
    sql_query = models.TextField(help_text="Generated SQL query", blank=True, null=True)
    query_result = models.JSONField(help_text="Query execution result", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_ai_response = models.BooleanField(default=True, help_text="Whether this is an AI response")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."
