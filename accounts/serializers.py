# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile, UserActivity

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'phone_number', 'role', 'vendor_type', 'latitude', 'longitude',
            'address', 'city', 'county', 'profile_picture', 'is_verified',
            'created_at', 'updated_at', 'last_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_active']
    
    def to_representation(self, instance):
        """Customize representation based on user role"""
        data = super().to_representation(instance)
        
        # Don't show vendor_type for non-vendors
        if instance.role != 'vendor':
            data.pop('vendor_type', None)
            
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'date_of_birth', 'gender', 'id_number', 'preferred_language',
            'receive_notifications', 'receive_sms', 'receive_email',
            'emergency_contact_name', 'emergency_contact_phone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone_number',
            'role', 'vendor_type', 'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        """Validate password confirmation and role-specific fields"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate vendor type for vendors
        if attrs['role'] == 'vendor' and not attrs.get('vendor_type'):
            raise serializers.ValidationError("Vendor type is required for vendors")
        
        # Remove vendor_type for non-vendors
        if attrs['role'] != 'vendor':
            attrs.pop('vendor_type', None)
        
        return attrs
    
    def create(self, validated_data):
        """Create user with encrypted password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for UserActivity model"""
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'description', 'ip_address', 
            'user_agent', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']