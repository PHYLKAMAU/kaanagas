# customers/serializers.py

from rest_framework import serializers
from .models import (
    CustomerProfile, CustomerAddress, CustomerCylinder,
    CustomerPaymentMethod, CustomerFavorite, CustomerComplaint
)

class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for CustomerProfile model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    order_completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'customer_type', 'date_of_birth', 'business_name',
            'business_registration', 'tax_pin', 'preferred_gas_size',
            'preferred_brand', 'preferred_delivery_time',
            'default_delivery_instructions', 'total_orders', 'completed_orders',
            'cancelled_orders', 'total_spent', 'loyalty_points',
            'membership_tier', 'sms_notifications', 'email_notifications',
            'push_notifications', 'promotional_messages', 'is_verified',
            'verification_date', 'is_blocked', 'blocked_reason',
            'order_completion_rate', 'average_order_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'user_email', 'user_phone', 'total_orders',
            'completed_orders', 'cancelled_orders', 'total_spent',
            'loyalty_points', 'membership_tier', 'is_verified',
            'verification_date', 'is_blocked', 'blocked_reason',
            'order_completion_rate', 'average_order_value',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Set user from request context"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CustomerAddressSerializer(serializers.ModelSerializer):
    """Serializer for CustomerAddress model"""
    
    class Meta:
        model = CustomerAddress
        fields = [
            'id', 'customer', 'address_type', 'label', 'address_line_1',
            'address_line_2', 'city', 'county', 'postal_code',
            'latitude', 'longitude', 'landmark', 'delivery_instructions',
            'gate_code', 'is_default', 'is_active', 'times_used',
            'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'times_used', 'last_used', 'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate coordinates"""
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        if latitude and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        
        if longitude and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        
        return attrs


class CustomerCylinderSerializer(serializers.ModelSerializer):
    """Serializer for CustomerCylinder model"""
    needs_refill = serializers.BooleanField(read_only=True)
    needs_inspection = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomerCylinder
        fields = [
            'id', 'customer', 'serial_number', 'brand', 'size',
            'purchase_date', 'status', 'current_fill_level',
            'last_refill_date', 'current_location', 'is_with_customer',
            'last_inspection_date', 'next_inspection_due',
            'safety_certificate', 'total_refills', 'total_cost_spent',
            'needs_refill', 'needs_inspection', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_refills', 'total_cost_spent', 'needs_refill',
            'needs_inspection', 'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate cylinder data"""
        current_fill_level = attrs.get('current_fill_level', 100)
        
        if current_fill_level < 0 or current_fill_level > 100:
            raise serializers.ValidationError("Fill level must be between 0 and 100")
        
        return attrs


class CustomerPaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for CustomerPaymentMethod model"""
    
    class Meta:
        model = CustomerPaymentMethod
        fields = [
            'id', 'customer', 'payment_type', 'label', 'mpesa_number',
            'card_last_four', 'card_type', 'bank_name', 'account_number_masked',
            'is_default', 'is_verified', 'is_active', 'times_used',
            'total_amount_spent', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'card_token', 'is_verified', 'times_used',
            'total_amount_spent', 'last_used', 'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate payment method based on type"""
        payment_type = attrs.get('payment_type')
        
        if payment_type == 'mpesa' and not attrs.get('mpesa_number'):
            raise serializers.ValidationError("M-Pesa number is required for M-Pesa payment method")
        
        if payment_type == 'card' and not attrs.get('card_last_four'):
            raise serializers.ValidationError("Card information is required for card payment method")
        
        if payment_type == 'bank_account' and not attrs.get('bank_name'):
            raise serializers.ValidationError("Bank information is required for bank account payment method")
        
        return attrs


class CustomerFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for CustomerFavorite model"""
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = CustomerFavorite
        fields = [
            'id', 'customer', 'favorite_type', 'vendor', 'vendor_name',
            'product', 'product_name', 'times_ordered', 'last_ordered',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'vendor_name', 'product_name', 'times_ordered',
            'last_ordered', 'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate favorite type matches entity"""
        favorite_type = attrs.get('favorite_type')
        vendor = attrs.get('vendor')
        product = attrs.get('product')
        
        if favorite_type == 'vendor' and not vendor:
            raise serializers.ValidationError("Vendor is required for vendor favorites")
        elif favorite_type == 'product' and not product:
            raise serializers.ValidationError("Product is required for product favorites")
        
        return attrs


class CustomerComplaintSerializer(serializers.ModelSerializer):
    """Serializer for CustomerComplaint model"""
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    rider_name = serializers.CharField(source='rider.user.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = CustomerComplaint
        fields = [
            'id', 'customer', 'customer_name', 'complaint_id', 'complaint_type',
            'subject', 'description', 'priority', 'order', 'order_number',
            'vendor', 'vendor_name', 'rider', 'rider_name', 'status',
            'assigned_to', 'assigned_to_name', 'resolved_at', 'resolution',
            'satisfaction_rating', 'satisfaction_feedback',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'customer_name', 'complaint_id', 'order_number',
            'vendor_name', 'rider_name', 'assigned_to', 'assigned_to_name',
            'resolved_at', 'resolution', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Set customer from request context"""
        validated_data['customer'] = self.context['request'].user.customer_profile
        return super().create(validated_data)


class CustomerDashboardSerializer(serializers.Serializer):
    """Serializer for customer dashboard data"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    loyalty_points = serializers.IntegerField()
    membership_tier = serializers.CharField()
    favorite_vendors_count = serializers.IntegerField()
    active_complaints = serializers.IntegerField()


class CustomerAddressListSerializer(serializers.ModelSerializer):
    """Simplified serializer for address listings"""
    
    class Meta:
        model = CustomerAddress
        fields = [
            'id', 'label', 'address_line_1', 'city', 'latitude',
            'longitude', 'is_default', 'times_used'
        ]