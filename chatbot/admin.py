from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ChatSession, ChatMessage, ChatbotKnowledgeBase, ChatbotIntent,
    ChatbotAnalytics, ChatbotFeedback
)

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Chat Session Admin"""
    
    list_display = [
        'session_id_short', 'user_display', 'channel', 'status',
        'started_at', 'duration_display', 'user_satisfaction'
    ]
    list_filter = ['channel', 'status', 'transferred_to_human', 'started_at']
    search_fields = ['user__email', 'phone_number', 'user_intent']
    ordering = ['-started_at']
    
    def session_id_short(self, obj):
        return str(obj.session_id)[:8] + "..."
    session_id_short.short_description = "Session ID"
    
    def user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return f"Anonymous ({obj.phone_number})"
    user_display.short_description = "User"
    
    def duration_display(self, obj):
        return f"{obj.duration:.1f} min"
    duration_display.short_description = "Duration"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Chat Message Admin"""
    
    list_display = [
        'session_short', 'message_type', 'content_preview', 'intent',
        'confidence_score', 'created_at'
    ]
    list_filter = ['message_type', 'intent', 'created_at']
    search_fields = ['content', 'intent', 'session__user__email']
    ordering = ['-created_at']
    
    def session_short(self, obj):
        return str(obj.session.session_id)[:8] + "..."
    session_short.short_description = "Session"
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(ChatbotKnowledgeBase)
class ChatbotKnowledgeBaseAdmin(admin.ModelAdmin):
    """Chatbot Knowledge Base Admin"""
    
    list_display = [
        'title', 'content_type', 'category', 'usage_count',
        'satisfaction_rate_display', 'is_active', 'priority'
    ]
    list_filter = ['content_type', 'category', 'is_active', 'created_at']
    search_fields = ['title', 'question', 'answer', 'keywords']
    ordering = ['-priority', 'title']
    
    def satisfaction_rate_display(self, obj):
        rate = obj.satisfaction_rate
        color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    satisfaction_rate_display.short_description = "Satisfaction"


@admin.register(ChatbotFeedback)
class ChatbotFeedbackAdmin(admin.ModelAdmin):
    """Chatbot Feedback Admin"""
    
    list_display = [
        'session_short', 'feedback_type', 'rating', 'is_resolved', 'created_at'
    ]
    list_filter = ['feedback_type', 'rating', 'is_resolved', 'created_at']
    search_fields = ['comment', 'session__user__email']
    ordering = ['-created_at']
    
    def session_short(self, obj):
        return str(obj.session.session_id)[:8] + "..."
    session_short.short_description = "Session"