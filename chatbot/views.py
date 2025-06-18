# chatbot/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
import random

from .models import (
    ChatSession, ChatMessage, ChatbotKnowledgeBase, ChatbotIntent,
    ChatbotAnalytics, ChatbotFeedback
)
from .serializers import (
    ChatSessionSerializer, ChatMessageSerializer, ChatbotKnowledgeBaseSerializer,
    ChatbotIntentSerializer, ChatbotAnalyticsSerializer, ChatbotFeedbackSerializer,
    ChatSessionCreateSerializer, ChatMessageCreateSerializer, ChatBotResponseSerializer,
    WhatsAppMessageSerializer, ChatAnalyticsSerializer
)

class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat sessions"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChatSessionCreateSerializer
        return ChatSessionSerializer
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return ChatSession.objects.all()
        else:
            return ChatSession.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End chat session"""
        session = self.get_object()
        
        if session.user != request.user and not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save()
        
        return Response({'message': 'Chat session ended'})
    
    @action(detail=True, methods=['post'])
    def transfer_to_human(self, request, pk=None):
        """Transfer session to human agent"""
        session = self.get_object()
        reason = request.data.get('reason', 'Customer requested human agent')
        
        session.transferred_to_human = True
        session.transfer_reason = reason
        session.status = 'transferred'
        session.save()
        
        # Create system message
        ChatMessage.objects.create(
            session=session,
            message_type='system',
            content='Chat has been transferred to a human agent. Please wait...',
            intent='transfer_to_human'
        )
        
        return Response({'message': 'Session transferred to human agent'})
    
    @action(detail=True, methods=['post'])
    def rate_session(self, request, pk=None):
        """Rate chat session"""
        session = self.get_object()
        
        if session.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rating = request.data.get('rating')
        feedback = request.data.get('feedback', '')
        
        if rating and 1 <= rating <= 5:
            session.user_satisfaction = rating
            session.feedback_text = feedback
            session.save()
            
            return Response({'message': 'Session rated successfully'})
        
        return Response(
            {'error': 'Rating must be between 1 and 5'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class ChatMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat messages"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer
    
    def get_queryset(self):
        """Filter based on user role and session access"""
        user = self.request.user
        if user.is_admin_user:
            return ChatMessage.objects.all()
        else:
            return ChatMessage.objects.filter(session__user=user)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """React to a message (helpful/not helpful)"""
        message = self.get_object()
        reaction = request.data.get('reaction')  # helpful, not_helpful, unclear
        
        if reaction in ['helpful', 'not_helpful', 'unclear']:
            message.user_reaction = reaction
            message.save()
            
            # Update knowledge base feedback if applicable
            if message.intent:
                try:
                    kb_article = ChatbotKnowledgeBase.objects.get(
                        Q(keywords__icontains=message.intent) |
                        Q(question__icontains=message.content)
                    )
                    
                    if reaction == 'helpful':
                        kb_article.positive_feedback += 1
                    else:
                        kb_article.negative_feedback += 1
                    
                    kb_article.save()
                except ChatbotKnowledgeBase.DoesNotExist:
                    pass
            
            return Response({'message': 'Reaction recorded'})
        
        return Response(
            {'error': 'Invalid reaction'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class ChatbotKnowledgeBaseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chatbot knowledge base"""
    serializer_class = ChatbotKnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return ChatbotKnowledgeBase.objects.all()
        else:
            # Non-admins can only view active articles
            return ChatbotKnowledgeBase.objects.filter(is_active=True)
    
    def get_permissions(self):
        """Only admins can create/update/delete"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated]
            # Add admin check in perform_create
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Only admins can create knowledge base articles"""
        if not self.request.user.is_admin_user:
            raise permissions.PermissionDenied("Only admins can create knowledge base articles")
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search knowledge base"""
        query = request.query_params.get('q', '')
        category = request.query_params.get('category')
        
        articles = self.get_queryset().filter(is_active=True)
        
        if query:
            articles = articles.filter(
                Q(title__icontains=query) |
                Q(question__icontains=query) |
                Q(keywords__icontains=query) |
                Q(answer__icontains=query)
            )
        
        if category:
            articles = articles.filter(category=category)
        
        articles = articles.order_by('-priority', '-usage_count')[:10]
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)


class ChatbotIntentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chatbot intents (admin only)"""
    serializer_class = ChatbotIntentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only admins can manage intents"""
        if self.request.user.is_admin_user:
            return ChatbotIntent.objects.all()
        return ChatbotIntent.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Only admins can create intents"""
        if not self.request.user.is_admin_user:
            raise permissions.PermissionDenied("Only admins can create intents")
        serializer.save()


class ChatbotFeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chatbot feedback"""
    serializer_class = ChatbotFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return ChatbotFeedback.objects.all()
        else:
            return ChatbotFeedback.objects.filter(session__user=user)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to feedback (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback = self.get_object()
        response_text = request.data.get('response', '')
        
        feedback.admin_response = response_text
        feedback.responded_by = request.user
        feedback.responded_at = timezone.now()
        feedback.is_resolved = True
        feedback.save()
        
        return Response({'message': 'Response sent successfully'})


class ChatView(APIView):
    """Main chat interface"""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def post(self, request):
        """Process chat message and generate response"""
        message_text = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')
        
        if not message_text:
            return Response(
                {'error': 'Message cannot be empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(session_id=session_id)
            except ChatSession.DoesNotExist:
                session = self.create_session(request)
        else:
            session = self.create_session(request)
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message_text
        )
        
        # Process message and generate response
        bot_response = self.process_message(message_text, session, request.user)
        
        # Save bot response
        bot_message = ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=bot_response['message'],
            intent=bot_response.get('intent'),
            confidence_score=bot_response.get('confidence'),
            structured_content=bot_response.get('structured_content')
        )
        
        response_data = {
            'session_id': str(session.session_id),
            'message_id': bot_message.id,
            'response': bot_response
        }
        
        return Response(response_data)
    
    def create_session(self, request):
        """Create new chat session"""
        session_data = {
            'channel': 'web',
            'user_intent': 'general_inquiry'
        }
        
        if request.user.is_authenticated:
            session_data['user'] = request.user
        
        return ChatSession.objects.create(**session_data)
    
    def process_message(self, message, session, user):
        """Process message and generate appropriate response"""
        # Simple intent detection based on keywords
        message_lower = message.lower()
        
        # Check for greetings
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return {
                'message': 'Hello! Welcome to Kaanagas. How can I help you today?',
                'intent': 'greeting',
                'confidence': 0.9,
                'quick_replies': ['Find vendors', 'Track order', 'Help with account']
            }
        
        # Check for order-related queries
        if any(word in message_lower for word in ['order', 'delivery', 'track', 'status']):
            if user.is_authenticated:
                return self.handle_order_query(message, user)
            else:
                return {
                    'message': 'To help you with orders, please log in to your account first.',
                    'intent': 'order_status',
                    'confidence': 0.8,
                    'requires_human': False
                }
        
        # Check for vendor search
        if any(word in message_lower for word in ['vendor', 'shop', 'store', 'gas', 'cylinder']):
            return {
                'message': 'I can help you find nearby gas vendors. Would you like me to show vendors near your location?',
                'intent': 'find_vendor',
                'confidence': 0.8,
                'quick_replies': ['Yes, find vendors', 'Search by area', 'Cancel']
            }
        
        # Check for pricing queries
        if any(word in message_lower for word in ['price', 'cost', 'how much', 'rate']):
            return {
                'message': 'Gas prices vary by vendor and cylinder size. Would you like me to show current prices from nearby vendors?',
                'intent': 'pricing',
                'confidence': 0.7,
                'quick_replies': ['Show prices', 'Find cheapest', 'Compare vendors']
            }
        
        # Check for complaints
        if any(word in message_lower for word in ['complain', 'issue', 'problem', 'wrong', 'bad']):
            return {
                'message': 'I\'m sorry to hear you\'re having an issue. Would you like me to help you file a complaint or connect you with our support team?',
                'intent': 'complaint',
                'confidence': 0.8,
                'quick_replies': ['File complaint', 'Talk to human', 'Get help']
            }
        
        # Check for goodbye
        if any(word in message_lower for word in ['bye', 'goodbye', 'thanks', 'thank you']):
            return {
                'message': 'Thank you for using Kaanagas! Have a great day!',
                'intent': 'goodbye',
                'confidence': 0.9,
                'session_ended': True
            }
        
        # Default response - search knowledge base
        return self.search_knowledge_base(message)
    
    def handle_order_query(self, message, user):
        """Handle order-related queries for authenticated users"""
        from orders.models import Order
        
        # Get user's recent orders
        recent_orders = Order.objects.filter(customer=user).order_by('-created_at')[:3]
        
        if recent_orders:
            order_info = []
            for order in recent_orders:
                order_info.append(f"Order #{order.order_number}: {order.status.title()}")
            
            orders_text = "\n".join(order_info)
            
            return {
                'message': f'Here are your recent orders:\n\n{orders_text}\n\nWould you like details about any specific order?',
                'intent': 'order_status',
                'confidence': 0.9,
                'structured_content': {
                    'type': 'order_list',
                    'orders': [
                        {
                            'id': order.id,
                            'number': order.order_number,
                            'status': order.status,
                            'total': float(order.total_amount)
                        } for order in recent_orders
                    ]
                }
            }
        else:
            return {
                'message': 'You don\'t have any orders yet. Would you like me to help you find vendors to place your first order?',
                'intent': 'order_status',
                'confidence': 0.8,
                'quick_replies': ['Find vendors', 'How to order', 'Learn more']
            }
    
    def search_knowledge_base(self, message):
        """Search knowledge base for relevant answers"""
        # Simple keyword matching
        articles = ChatbotKnowledgeBase.objects.filter(
            Q(keywords__icontains=message) |
            Q(question__icontains=message) |
            Q(alternative_questions__icontains=message),
            is_active=True
        ).order_by('-priority')[:1]
        
        if articles:
            article = articles[0]
            article.usage_count += 1
            article.save()
            
            return {
                'message': article.answer,
                'intent': 'knowledge_base',
                'confidence': 0.6,
                'structured_content': article.rich_content if article.has_rich_content else None
            }
        else:
            return {
                'message': 'I\'m not sure how to help with that. Would you like me to connect you with a human agent?',
                'intent': 'unknown',
                'confidence': 0.1,
                'requires_human': True,
                'quick_replies': ['Talk to human', 'Try again', 'Main menu']
            }


class WhatsAppWebhookView(APIView):
    """WhatsApp webhook for message handling"""
    permission_classes = []  # Allow unauthenticated access
    
    def post(self, request):
        """Handle incoming WhatsApp messages"""
        try:
            # Parse WhatsApp webhook data
            webhook_data = request.data
            
            # Extract message information
            messages = webhook_data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [])
            
            for message_data in messages:
                phone_number = message_data.get('from')
                message_text = message_data.get('text', {}).get('body', '')
                message_id = message_data.get('id')
                
                if phone_number and message_text:
                    # Process WhatsApp message
                    self.process_whatsapp_message(phone_number, message_text, message_id)
            
            return Response({'status': 'success'})
            
        except Exception as e:
            return Response({'error': 'Webhook processing failed'}, status=500)
    
    def get(self, request):
        """Verify WhatsApp webhook"""
        verify_token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')
        
        # In production, verify the token
        if verify_token == 'your_verify_token':
            return Response(challenge)
        
        return Response('Verification failed', status=403)
    
    def process_whatsapp_message(self, phone_number, message_text, message_id):
        """Process WhatsApp message and send response"""
        # Get or create session
        session, created = ChatSession.objects.get_or_create(
            phone_number=phone_number,
            channel='whatsapp',
            status='active',
            defaults={'anonymous_id': f'whatsapp_{phone_number}'}
        )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message_text,
            external_message_id=message_id
        )
        
        # Generate response (simplified)
        if 'hello' in message_text.lower():
            response_text = 'Hello! Welcome to Kaanagas. How can I help you today?'
        else:
            response_text = 'Thank you for your message. Our team will get back to you soon.'
        
        # Save bot response
        ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=response_text
        )
        
        # In production, send response back to WhatsApp
        # self.send_whatsapp_message(phone_number, response_text)


class ChatbotAnalyticsView(APIView):
    """Chatbot analytics dashboard"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Session statistics
        all_sessions = ChatSession.objects.all()
        today_sessions = all_sessions.filter(started_at__date=today)
        week_sessions = all_sessions.filter(started_at__date__gte=week_ago)
        month_sessions = all_sessions.filter(started_at__date__gte=month_ago)
        
        # Message statistics
        all_messages = ChatMessage.objects.all()
        
        # Calculate resolution rate (sessions that didn't require human transfer)
        completed_sessions = all_sessions.filter(status='ended', transferred_to_human=False).count()
        total_sessions = all_sessions.count()
        resolution_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # User satisfaction
        rated_sessions = all_sessions.filter(user_satisfaction__isnull=False)
        avg_satisfaction = rated_sessions.aggregate(avg=Avg('user_satisfaction'))['avg'] or 0
        
        # Top intents
        top_intents = list(all_messages.filter(
            intent__isnull=False
        ).values('intent').annotate(
            count=Count('id')
        ).order_by('-count')[:10])
        
        # Busiest hours (simplified)
        busiest_hours = list(range(9, 18))  # Business hours
        
        # Transfer rate
        transferred_sessions = all_sessions.filter(transferred_to_human=True).count()
        transfer_rate = (transferred_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        analytics_data = {
            'total_sessions_today': today_sessions.count(),
            'total_sessions_week': week_sessions.count(),
            'total_sessions_month': month_sessions.count(),
            'average_session_duration': 5.5,  # Would be calculated from actual data
            'resolution_rate': round(resolution_rate, 2),
            'user_satisfaction': round(avg_satisfaction, 2),
            'top_intents': top_intents,
            'busiest_hours': busiest_hours,
            'transfer_rate': round(transfer_rate, 2)
        }
        
        serializer = ChatAnalyticsSerializer(analytics_data)
        return Response(serializer.data)