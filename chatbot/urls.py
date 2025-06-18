# chatbot/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.ChatSessionViewSet, basename='chatsession')
router.register(r'messages', views.ChatMessageViewSet, basename='chatmessage')
router.register(r'knowledge-base', views.ChatbotKnowledgeBaseViewSet, basename='chatbotknowledgebase')
router.register(r'intents', views.ChatbotIntentViewSet, basename='chatbotintent')
router.register(r'feedback', views.ChatbotFeedbackViewSet, basename='chatbotfeedback')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('whatsapp-webhook/', views.WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    path('analytics/', views.ChatbotAnalyticsView.as_view(), name='chatbot_analytics'),
]