# riders/serializers.py

from rest_framework import serializers
from .models import (
    RiderProfile, RiderAvailability, RiderBankAccount, Delivery,
    RiderEarnings, RiderLocation, RiderIncentive, RiderPerformance
)

class RiderProfileSerializer(serializers.ModelSerializer):
    """Serializer for RiderProfile model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RiderProfile
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'id_number', 'driving_license_number', 'date_of_birth',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'vehicle_type',
            'vehicle_registration', 'vehicle_make', 'vehicle_model',
            'vehicle_year', 'vehicle_color', 'insurance_policy_number',
            'insurance_expiry', 'license_expiry', 'service_areas',
            'max_delivery_distance', 'status', 'is_available',
            'current_latitude', 'current_longitude', 'last_location_update',
            'total_deliveries', 'successful_deliveries', 'average_rating',
            'total_ratings', 'average_delivery_time', 'commission_rate',
            'verification_documents', 'verified_at', 'verified_by',
            'completion_rate', 'is_online', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'user_email', 'user_phone', 'total_deliveries',
            'successful_deliveries', 'average_rating', 'total_ratings',
            'average_delivery_time', 'verified_at', 'verified_by',
            'completion_rate', 'is_online', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Set user from request context"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, attrs):
        """Validate rider data"""
        insurance_expiry = attrs.get('insurance_expiry')
        license_expiry = attrs.get('license_expiry')
        
        from django.utils import timezone
        today = timezone.now().date()
        
        if insurance_expiry and insurance_expiry <= today:
            raise serializers.ValidationError("Insurance must not be expired")
        
        if license_expiry and license_expiry <= today:
            raise serializers.ValidationError("Driving license must not be expired")
        
        return attrs


class RiderAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for RiderAvailability model"""
    
    class Meta:
        model = RiderAvailability
        fields = [
            'id', 'rider', 'day', 'start_time', 'end_time', 'is_available',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate availability hours"""
        if attrs.get('is_available'):
            start_time = attrs.get('start_time')
            end_time = attrs.get('end_time')
            
            if not start_time or not end_time:
                raise serializers.ValidationError(
                    "Start time and end time are required when available"
                )
            
            if start_time >= end_time:
                raise serializers.ValidationError(
                    "End time must be after start time"
                )
        
        return attrs


class RiderBankAccountSerializer(serializers.ModelSerializer):
    """Serializer for RiderBankAccount model"""
    
    class Meta:
        model = RiderBankAccount
        fields = [
            'id', 'rider', 'bank_name', 'account_name', 'account_number',
            'branch', 'mpesa_number', 'mpesa_name', 'is_primary',
            'is_verified', 'verification_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verification_date', 'created_at', 'updated_at'
        ]


class DeliverySerializer(serializers.ModelSerializer):
    """Serializer for Delivery model"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.customer.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='order.customer.phone_number', read_only=True)
    vendor_name = serializers.CharField(source='order.vendor.business_name', read_only=True)
    rider_name = serializers.CharField(source='rider.user.get_full_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Delivery
        fields = [
            'id', 'order', 'order_number', 'customer_name', 'customer_phone',
            'vendor_name', 'rider', 'rider_name', 'status', 'assigned_at',
            'accepted_at', 'picked_up_at', 'delivered_at', 'pickup_latitude',
            'pickup_longitude', 'delivery_latitude', 'delivery_longitude',
            'estimated_distance', 'actual_distance', 'estimated_duration',
            'actual_duration', 'base_fee', 'distance_fee', 'time_bonus',
            'total_earnings', 'pickup_verification_code', 'delivery_verification_code',
            'customer_signature', 'pickup_notes', 'delivery_notes',
            'failure_reason', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer_name', 'customer_phone',
            'vendor_name', 'rider_name', 'assigned_at', 'total_earnings',
            'is_active', 'created_at', 'updated_at'
        ]


class RiderEarningsSerializer(serializers.ModelSerializer):
    """Serializer for RiderEarnings model"""
    rider_name = serializers.CharField(source='rider.user.get_full_name', read_only=True)
    delivery_info = serializers.CharField(source='delivery.order.order_number', read_only=True)
    
    class Meta:
        model = RiderEarnings
        fields = [
            'id', 'rider', 'rider_name', 'delivery', 'delivery_info',
            'earning_type', 'amount', 'description', 'payment_status',
            'payment_date', 'payment_reference', 'earning_date',
            'payment_period', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'rider_name', 'delivery_info', 'payment_date',
            'payment_reference', 'created_at', 'updated_at'
        ]


class RiderLocationSerializer(serializers.ModelSerializer):
    """Serializer for RiderLocation model"""
    
    class Meta:
        model = RiderLocation
        fields = [
            'id', 'rider', 'latitude', 'longitude', 'accuracy', 'speed',
            'delivery', 'is_during_delivery', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RiderIncentiveSerializer(serializers.ModelSerializer):
    """Serializer for RiderIncentive model"""
    
    class Meta:
        model = RiderIncentive
        fields = [
            'id', 'title', 'description', 'incentive_type', 'period_type',
            'minimum_deliveries', 'minimum_rating', 'minimum_distance',
            'target_areas', 'reward_amount', 'is_percentage', 'start_date',
            'end_date', 'is_active', 'applicable_to_all', 'specific_riders',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RiderPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for RiderPerformance model"""
    rider_name = serializers.CharField(source='rider.user.get_full_name', read_only=True)
    acceptance_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = RiderPerformance
        fields = [
            'id', 'rider', 'rider_name', 'period_type', 'period_start',
            'period_end', 'total_orders_assigned', 'total_orders_accepted',
            'total_orders_completed', 'total_orders_failed', 'total_online_hours',
            'total_delivery_time', 'average_delivery_time', 'total_distance',
            'total_earnings', 'total_ratings_received', 'average_rating',
            'acceptance_rate', 'completion_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'rider_name', 'acceptance_rate', 'completion_rate',
            'created_at', 'updated_at'
        ]


class RiderDashboardSerializer(serializers.Serializer):
    """Serializer for rider dashboard data"""
    total_deliveries = serializers.IntegerField()
    pending_deliveries = serializers.IntegerField()
    completed_today = serializers.IntegerField()
    earnings_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    earnings_week = serializers.DecimalField(max_digits=10, decimal_places=2)
    earnings_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    online_hours_today = serializers.DecimalField(max_digits=5, decimal_places=2)


class RiderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for rider listings"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    distance = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = RiderProfile
        fields = [
            'id', 'user_name', 'vehicle_type', 'vehicle_registration',
            'current_latitude', 'current_longitude', 'status',
            'is_available', 'average_rating', 'total_deliveries',
            'distance'
        ]