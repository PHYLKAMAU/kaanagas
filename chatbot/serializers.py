# chatbot/serializers.py

from rest_framework import serializers
from .models import (
    ChatSession, ChatMessage, ChatbotKnowledgeBase, ChatbotIntent,
    ChatbotAnalytics, ChatbotFeedback
)

class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    human_agent_name = serializers.CharField(source='human_agent.get_full_name', read_only=True)
    duration = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'session_id', 'user', 'user_name', 'channel', 'status',
            'anonymous_id', 'phone_number', 'user_intent', 'current_flow',
            'context_data', 'started_at', 'ended_at', 'last_activity',
            'transferred_to_human', 'transfer_reason', 'human_agent',
            'human_agent_name', 'user_satisfaction', 'feedback_text',
            'duration', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'session_id', 'user_name', 'human_agent_name',
            'started_at', 'duration', 'created_at', 'updated_at'
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'message_type', 'message_format', 'content',
            'structured_content', 'intent', 'confidence_score', 'entities',
            'response_time', 'ai_model_used', 'is_read', 'user_reaction',
            'sequence_number', 'external_message_id', 'created_at'
        ]
        read_only_fields = [
            'id', 'sequence_number', 'intent', 'confidence_score',
            'entities', 'response_time', 'ai_model_used', 'created_at'
        ]


class ChatbotKnowledgeBaseSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotKnowledgeBase model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    last_updated_by_name = serializers.CharField(source='last_updated_by.get_full_name', read_only=True)
    satisfaction_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = ChatbotKnowledgeBase
        fields = [
            'id', 'title', 'content_type', 'question', 'answer',
            'alternative_questions', 'keywords', 'category', 'subcategory',
            'has_rich_content', 'rich_content', 'usage_count',
            'positive_feedback', 'negative_feedback', 'is_active',
            'priority', 'created_by', 'created_by_name', 'last_updated_by',
            'last_updated_by_name', 'satisfaction_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'last_updated_by_name', 'usage_count',
            'positive_feedback', 'negative_feedback', 'satisfaction_rate',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Set created_by from request context"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Set last_updated_by from request context"""
        validated_data['last_updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)


class ChatbotIntentSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotIntent model"""
    
    class Meta:
        model = ChatbotIntent
        fields = [
            'id', 'intent_name', 'intent_type', 'description',
            'training_phrases', 'response_templates', 'requires_authentication',
            'next_intent', 'requires_human_handoff', 'required_context',
            'context_to_collect', 'usage_count', 'success_rate',
            'is_active', 'confidence_threshold', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usage_count', 'success_rate', 'created_at', 'updated_at'
        ]


class ChatbotAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotAnalytics model"""
    
    class Meta:
        model = ChatbotAnalytics
        fields = [
            'id', 'metric_type', 'date', 'total_sessions', 'active_sessions',
            'completed_sessions', 'abandoned_sessions', 'transferred_sessions',
            'total_messages', 'user_messages', 'bot_messages',
            'average_session_duration', 'average_response_time',
            'intent_recognition_accuracy', 'total_ratings', 'average_rating',
            'positive_feedback', 'negative_feedback', 'top_intents',
            'unhandled_queries', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatbotFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotFeedback model"""
    session_id = serializers.CharField(source='session.session_id', read_only=True)
    responded_by_name = serializers.CharField(source='responded_by.get_full_name', read_only=True)
    
    class Meta:
        model = ChatbotFeedback
        fields = [
            'id', 'session', 'session_id', 'message', 'feedback_type',
            'rating', 'comment', 'issue_category', 'is_resolved',
            'admin_response', 'responded_by', 'responded_by_name',
            'responded_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'session_id', 'responded_by_name', 'responded_at',
            'created_at', 'updated_at'
        ]


class ChatSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat sessions"""
    
    class Meta:
        model = ChatSession
        fields = ['channel', 'phone_number', 'user_intent']
    
    def create(self, validated_data):
        """Create chat session with user context"""
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['user'] = user
        return super().create(validated_data)


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = [
            'session', 'message_type', 'message_format', 'content',
            'structured_content'
        ]


class ChatBotResponseSerializer(serializers.Serializer):
    """Serializer for chatbot response"""
    message = serializers.CharField()
    message_type = serializers.CharField()
    intent = serializers.CharField(required=False)
    confidence = serializers.FloatField(required=False)
    quick_replies = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    requires_human = serializers.BooleanField(default=False)
    session_ended = serializers.BooleanField(default=False)


class WhatsAppMessageSerializer(serializers.Serializer):
    """Serializer for WhatsApp webhook messages"""
    from_number = serializers.CharField()
    message_text = serializers.CharField()
    message_id = serializers.CharField()
    timestamp = serializers.CharField()


class ChatAnalyticsSerializer(serializers.Serializer):
    """Serializer for chat analytics dashboard"""
    total_sessions_today = serializers.IntegerField()
    total_sessions_week = serializers.IntegerField()
    total_sessions_month = serializers.IntegerField()
    average_session_duration = serializers.FloatField()
    resolution_rate = serializers.FloatField()
    user_satisfaction = serializers.FloatField()
    top_intents = serializers.ListField()
    busiest_hours = serializers.ListField()
    transfer_rate = serializers.FloatField()