# core/serializers.py

from rest_framework import serializers
from .models import Location, GasProduct, Rating, Notification, SystemSettings

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model"""
    
    class Meta:
        model = Location
        fields = [
            'id', 'user', 'name', 'address_line_1', 'address_line_2',
            'city', 'county', 'postal_code', 'latitude', 'longitude',
            'landmark', 'instructions', 'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Set user from request context"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class GasProductSerializer(serializers.ModelSerializer):
    """Serializer for GasProduct model"""
    
    class Meta:
        model = GasProduct
        fields = [
            'id', 'name', 'gas_type', 'cylinder_size', 'brand', 'description',
            'weight_empty', 'weight_full', 'base_price', 'refill_price',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for Rating model"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'customer', 'customer_name', 'rating_type', 'vendor', 
            'vendor_name', 'rider', 'rider_name', 'order', 'rating', 
            'review', 'is_verified', 'is_published', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'customer_name', 'vendor_name', 'rider_name']
    
    def create(self, validated_data):
        """Set customer from request context"""
        validated_data['customer'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, attrs):
        """Validate that rating type matches the provided entity"""
        rating_type = attrs.get('rating_type')
        vendor = attrs.get('vendor')
        rider = attrs.get('rider')
        
        if rating_type == 'vendor' and not vendor:
            raise serializers.ValidationError("Vendor is required for vendor ratings")
        elif rating_type == 'rider' and not rider:
            raise serializers.ValidationError("Rider is required for rider ratings")
        
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'title', 'message', 'notification_type',
            'order', 'is_read', 'is_sent', 'sent_at', 'send_push',
            'send_email', 'send_sms', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_sent', 'sent_at']


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SystemSettings model"""
    
    class Meta:
        model = SystemSettings
        fields = [
            'id', 'key', 'value', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']