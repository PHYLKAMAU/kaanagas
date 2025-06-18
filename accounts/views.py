# accounts/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import User, UserProfile, UserActivity
from .serializers import (
    UserSerializer, UserProfileSerializer, UserRegistrationSerializer,
    UserActivitySerializer, LoginSerializer, ChangePasswordSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on permissions"""
        user = self.request.user
        if user.is_admin_user:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=True, methods=['post'])
    def verify_account(self, request, pk=None):
        """Verify user account (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_verified = True
        user.save()
        
        return Response({'message': 'Account verified successfully'})


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user profiles"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only access their own profile"""
        return UserProfile.objects.filter(user=self.request.user)


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user activities"""
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own activities"""
        return UserActivity.objects.filter(user=self.request.user)


class RegisterView(APIView):
    """User registration view"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Log registration activity
            UserActivity.objects.create(
                user=user,
                activity_type='registration',
                description='User registered successfully',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Registration successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LoginView(APIView):
    """User login view"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(email=email, password=password)
            
            if user:
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                # Log login activity
                UserActivity.objects.create(
                    user=user,
                    activity_type='login',
                    description='User logged in successfully',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                })
            
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """User logout view"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Log logout activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='logout',
                description='User logged out successfully'
            )
            
            return Response({'message': 'Logout successful'})
        except Exception as e:
            return Response(
                {'error': 'Invalid token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    """Get and update user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user profile"""
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(profile).data
        })
    
    def put(self, request):
        """Update user profile"""
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Update user basic info
        user_data = request.data.get('user', {})
        for field in ['first_name', 'last_name', 'phone_number', 'address', 'city', 'county']:
            if field in user_data:
                setattr(user, field, user_data[field])
        user.save()
        
        # Update profile
        profile_data = request.data.get('profile', {})
        profile_serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
        
        if profile_serializer.is_valid():
            profile_serializer.save()
            
            # Log profile update activity
            UserActivity.objects.create(
                user=user,
                activity_type='profile_updated',
                description='User profile updated'
            )
            
            return Response({
                'message': 'Profile updated successfully',
                'user': UserSerializer(user).data,
                'profile': profile_serializer.data
            })
        
        return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                
                # Log password change activity
                UserActivity.objects.create(
                    user=user,
                    activity_type='password_changed',
                    description='User changed password'
                )
                
                return Response({'message': 'Password changed successfully'})
            
            return Response(
                {'error': 'Invalid old password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyAccountView(APIView):
    """Verify user account with verification code"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        verification_code = request.data.get('verification_code')
        
        # In a real implementation, you would verify the code
        # For now, we'll just mark the account as verified
        user.is_verified = True
        user.save()
        
        # Log verification activity
        UserActivity.objects.create(
            user=user,
            activity_type='account_verified',
            description='User account verified'
        )
        
        return Response({'message': 'Account verified successfully'})