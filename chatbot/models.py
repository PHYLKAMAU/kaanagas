# chatbot/models.py

from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
import uuid

class ChatSession(TimeStampedModel):
    """Chat session between user and AI chatbot"""
    
    SESSION_STATUS = [
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('transferred', 'Transferred to Human'),
    ]
    
    CHANNEL_TYPES = [
        ('web', 'Web Platform'),
        ('whatsapp', 'WhatsApp'),
        ('mobile_app', 'Mobile App'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True, blank=True  # Allow anonymous users
    )
    
    # Session Information
    channel = models.CharField(max_length=20, choices=CHANNEL_TYPES, default='web')
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active')
    
    # User Information (for anonymous users)
    anonymous_id = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=17, blank=True)
    
    # Session Context
    user_intent = models.CharField(max_length=100, blank=True)  # What user wants to do
    current_flow = models.CharField(max_length=50, blank=True)  # Current conversation flow
    context_data = models.JSONField(default=dict, blank=True)  # Store conversation context
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Transfer Information
    transferred_to_human = models.BooleanField(default=False)
    transfer_reason = models.TextField(blank=True)
    human_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='handled_chats',
        limit_choices_to={'role': 'admin'}
    )
    
    # Feedback
    user_satisfaction = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)]  # 1-5 stars
    )
    feedback_text = models.TextField(blank=True)
    
    class Meta:
        db_table = 'chatbot_session'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        user_display = self.user.get_full_name() if self.user else f"Anonymous ({self.phone_number})"
        return f"Chat Session {self.session_id} - {user_display}"
    
    @property
    def duration(self):
        """Get session duration in minutes"""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() / 60
        from django.utils import timezone
        return (timezone.now() - self.started_at).total_seconds() / 60


class ChatMessage(TimeStampedModel):
    """Individual messages in a chat session"""
    
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('bot', 'Bot Message'),
        ('system', 'System Message'),
        ('human', 'Human Agent Message'),
    ]
    
    MESSAGE_FORMATS = [
        ('text', 'Plain Text'),
        ('quick_reply', 'Quick Reply Buttons'),
        ('card', 'Card/Rich Media'),
        ('list', 'List Options'),
        ('location', 'Location Request'),
        ('image', 'Image'),
        ('file', 'File Attachment'),
    ]
    
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message Content
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    message_format = models.CharField(max_length=20, choices=MESSAGE_FORMATS, default='text')
    content = models.TextField()
    
    # Structured Content (for rich messages)
    structured_content = models.JSONField(blank=True, null=True)
    
    # Bot Response Information
    intent = models.CharField(max_length=100, blank=True)  # Detected intent
    confidence_score = models.FloatField(null=True, blank=True)  # Intent confidence
    entities = models.JSONField(blank=True, null=True)  # Extracted entities
    
    # Response Generation
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    ai_model_used = models.CharField(max_length=50, blank=True)
    
    # User Interaction
    is_read = models.BooleanField(default=False)
    user_reaction = models.CharField(
        max_length=20,
        choices=[
            ('helpful', 'Helpful'),
            ('not_helpful', 'Not Helpful'),
            ('unclear', 'Unclear'),
        ],
        blank=True
    )
    
    # Metadata
    sequence_number = models.IntegerField()  # Message order in session
    external_message_id = models.CharField(max_length=100, blank=True)  # WhatsApp message ID
    
    class Meta:
        db_table = 'chatbot_message'
        ordering = ['session', 'sequence_number']
        indexes = [
            models.Index(fields=['session', 'sequence_number']),
            models.Index(fields=['message_type', 'created_at']),
            models.Index(fields=['intent']),
        ]
    
    def __str__(self):
        return f"{self.message_type.title()} - {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        if not self.sequence_number:
            last_message = ChatMessage.objects.filter(session=self.session).order_by('-sequence_number').first()
            self.sequence_number = (last_message.sequence_number + 1) if last_message else 1
        super().save(*args, **kwargs)


class ChatbotKnowledgeBase(TimeStampedModel):
    """Knowledge base for chatbot responses"""
    
    CONTENT_TYPES = [
        ('faq', 'Frequently Asked Question'),
        ('procedure', 'Step-by-step Procedure'),
        ('policy', 'Company Policy'),
        ('product_info', 'Product Information'),
        ('troubleshooting', 'Troubleshooting Guide'),
    ]
    
    # Content Information
    title = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    question = models.TextField(help_text="Question or trigger phrase")
    answer = models.TextField(help_text="Response content")
    
    # Alternative Questions/Phrases
    alternative_questions = models.TextField(
        blank=True,
        help_text="Alternative ways to ask the same question (one per line)"
    )
    
    # Keywords for matching
    keywords = models.TextField(
        blank=True,
        help_text="Keywords for better matching (comma separated)"
    )
    
    # Categorization
    category = models.CharField(max_length=100, blank=True)
    subcategory = models.CharField(max_length=100, blank=True)
    
    # Rich Content
    has_rich_content = models.BooleanField(default=False)
    rich_content = models.JSONField(blank=True, null=True)  # Cards, buttons, etc.
    
    # Usage and Performance
    usage_count = models.IntegerField(default=0)
    positive_feedback = models.IntegerField(default=0)
    negative_feedback = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=50, help_text="Higher numbers = higher priority")
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_kb_articles'
    )
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='updated_kb_articles'
    )
    
    class Meta:
        db_table = 'chatbot_knowledge_base'
        ordering = ['-priority', 'title']
        indexes = [
            models.Index(fields=['content_type', 'is_active']),
            models.Index(fields=['category', 'subcategory']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.content_type})"
    
    @property
    def satisfaction_rate(self):
        total_feedback = self.positive_feedback + self.negative_feedback
        if total_feedback == 0:
            return 0
        return (self.positive_feedback / total_feedback) * 100


class ChatbotIntent(TimeStampedModel):
    """Define chatbot intents and their handling"""
    
    INTENT_TYPES = [
        ('greeting', 'Greeting'),
        ('order_status', 'Order Status Inquiry'),
        ('place_order', 'Place New Order'),
        ('find_vendor', 'Find Vendors'),
        ('pricing', 'Price Inquiry'),
        ('complaint', 'File Complaint'),
        ('support', 'General Support'),
        ('account', 'Account Management'),
        ('payment', 'Payment Issues'),
        ('goodbye', 'Goodbye'),
    ]
    
    # Intent Information
    intent_name = models.CharField(max_length=100, unique=True)
    intent_type = models.CharField(max_length=20, choices=INTENT_TYPES)
    description = models.TextField()
    
    # Training Phrases
    training_phrases = models.TextField(
        help_text="Training phrases for this intent (one per line)"
    )
    
    # Response Templates
    response_templates = models.TextField(
        help_text="Response templates (one per line, bot will randomly select)"
    )
    
    # Flow Control
    requires_authentication = models.BooleanField(default=False)
    next_intent = models.CharField(max_length=100, blank=True)
    requires_human_handoff = models.BooleanField(default=False)
    
    # Context Requirements
    required_context = models.JSONField(
        blank=True, null=True,
        help_text="Required context parameters"
    )
    context_to_collect = models.JSONField(
        blank=True, null=True,
        help_text="Context parameters to collect from user"
    )
    
    # Performance
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)
    
    # Status
    is_active = models.BooleanField(default=True)
    confidence_threshold = models.FloatField(default=0.7)
    
    class Meta:
        db_table = 'chatbot_intent'
        ordering = ['intent_name']
        indexes = [
            models.Index(fields=['intent_type', 'is_active']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.intent_name} ({self.intent_type})"


class ChatbotAnalytics(TimeStampedModel):
    """Analytics data for chatbot performance"""
    
    METRIC_TYPES = [
        ('daily', 'Daily Metrics'),
        ('weekly', 'Weekly Metrics'),
        ('monthly', 'Monthly Metrics'),
    ]
    
    # Time Period
    metric_type = models.CharField(max_length=10, choices=METRIC_TYPES)
    date = models.DateField()
    
    # Session Metrics
    total_sessions = models.IntegerField(default=0)
    active_sessions = models.IntegerField(default=0)
    completed_sessions = models.IntegerField(default=0)
    abandoned_sessions = models.IntegerField(default=0)
    transferred_sessions = models.IntegerField(default=0)
    
    # Message Metrics
    total_messages = models.IntegerField(default=0)
    user_messages = models.IntegerField(default=0)
    bot_messages = models.IntegerField(default=0)
    
    # Performance Metrics
    average_session_duration = models.FloatField(default=0.0)
    average_response_time = models.FloatField(default=0.0)
    intent_recognition_accuracy = models.FloatField(default=0.0)
    
    # User Satisfaction
    total_ratings = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    positive_feedback = models.IntegerField(default=0)
    negative_feedback = models.IntegerField(default=0)
    
    # Popular Intents
    top_intents = models.JSONField(blank=True, null=True)
    unhandled_queries = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'chatbot_analytics'
        unique_together = ['metric_type', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['metric_type', 'date']),
        ]
    
    def __str__(self):
        return f"{self.metric_type.title()} Analytics - {self.date}"


class ChatbotFeedback(TimeStampedModel):
    """User feedback on chatbot interactions"""
    
    FEEDBACK_TYPES = [
        ('message', 'Message Feedback'),
        ('session', 'Session Feedback'),
        ('feature', 'Feature Request'),
        ('bug', 'Bug Report'),
    ]
    
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='feedback',
        null=True, blank=True
    )
    
    # Feedback Details
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_TYPES)
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        null=True, blank=True
    )
    comment = models.TextField(blank=True)
    
    # Categorization
    issue_category = models.CharField(max_length=100, blank=True)
    is_resolved = models.BooleanField(default=False)
    
    # Admin Response
    admin_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chatbot_feedback_responses'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chatbot_feedback'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feedback_type', 'rating']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.feedback_type.title()} Feedback - {self.rating}★" if self.rating else f"{self.feedback_type.title()} Feedback"