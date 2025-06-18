# vendors/serializers.py

from rest_framework import serializers
from .models import (
    VendorProfile, VendorInventory, VendorHours, 
    VendorBankAccount, VendorPromotion
)
from core.models import GasProduct

class VendorProfileSerializer(serializers.ModelSerializer):
    """Serializer for VendorProfile model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'business_name', 'business_type', 'business_registration_number',
            'tax_pin', 'business_address', 'business_phone', 'business_email',
            'latitude', 'longitude', 'operating_hours_start', 'operating_hours_end',
            'operating_days', 'delivery_radius', 'minimum_order_amount',
            'delivery_fee', 'storage_capacity', 'daily_refill_capacity',
            'status', 'verification_documents', 'verified_at', 'verified_by',
            'total_orders', 'completed_orders', 'average_rating', 'total_ratings',
            'commission_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'user_email', 'user_phone', 'total_orders',
            'completed_orders', 'average_rating', 'total_ratings', 'verified_at',
            'verified_by', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Set user from request context"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class VendorInventorySerializer(serializers.ModelSerializer):
    """Serializer for VendorInventory model"""
    gas_product_name = serializers.CharField(source='gas_product.name', read_only=True)
    gas_product_size = serializers.CharField(source='gas_product.cylinder_size', read_only=True)
    gas_product_brand = serializers.CharField(source='gas_product.brand', read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = VendorInventory
        fields = [
            'id', 'vendor', 'gas_product', 'gas_product_name', 'gas_product_size',
            'gas_product_brand', 'current_stock', 'reserved_stock', 'minimum_stock',
            'maximum_stock', 'selling_price', 'refill_price', 'cost_price',
            'is_available', 'auto_reorder', 'reorder_level', 'last_restocked',
            'total_sold', 'available_stock', 'is_low_stock', 'is_out_of_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'gas_product_name', 'gas_product_size', 'gas_product_brand',
            'available_stock', 'is_low_stock', 'is_out_of_stock', 'total_sold',
            'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        """Validate stock levels"""
        current_stock = attrs.get('current_stock', 0)
        minimum_stock = attrs.get('minimum_stock', 0)
        maximum_stock = attrs.get('maximum_stock', 100)
        
        if current_stock < 0:
            raise serializers.ValidationError("Current stock cannot be negative")
        
        if minimum_stock < 0:
            raise serializers.ValidationError("Minimum stock cannot be negative")
        
        if maximum_stock <= minimum_stock:
            raise serializers.ValidationError("Maximum stock must be greater than minimum stock")
        
        return attrs


class VendorHoursSerializer(serializers.ModelSerializer):
    """Serializer for VendorHours model"""
    
    class Meta:
        model = VendorHours
        fields = [
            'id', 'vendor', 'day', 'open_time', 'close_time', 'is_closed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate operating hours"""
        if not attrs.get('is_closed'):
            open_time = attrs.get('open_time')
            close_time = attrs.get('close_time')
            
            if not open_time or not close_time:
                raise serializers.ValidationError(
                    "Open time and close time are required when not closed"
                )
            
            if open_time >= close_time:
                raise serializers.ValidationError(
                    "Close time must be after open time"
                )
        
        return attrs


class VendorBankAccountSerializer(serializers.ModelSerializer):
    """Serializer for VendorBankAccount model"""
    
    class Meta:
        model = VendorBankAccount
        fields = [
            'id', 'vendor', 'bank_name', 'account_name', 'account_number',
            'branch', 'swift_code', 'mpesa_number', 'mpesa_name',
            'is_primary', 'is_verified', 'verification_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verification_date', 'created_at', 'updated_at'
        ]


class VendorPromotionSerializer(serializers.ModelSerializer):
    """Serializer for VendorPromotion model"""
    applicable_products_details = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = VendorPromotion
        fields = [
            'id', 'vendor', 'title', 'description', 'promotion_type',
            'discount_value', 'minimum_order_amount', 'maximum_discount',
            'usage_limit', 'usage_limit_per_customer', 'start_date',
            'end_date', 'is_active', 'applicable_products',
            'applicable_products_details', 'total_used', 'is_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'applicable_products_details', 'total_used', 'is_valid',
            'created_at', 'updated_at'
        ]
    
    def get_applicable_products_details(self, obj):
        """Get details of applicable products"""
        if obj.applicable_products.exists():
            return [
                {
                    'id': product.id,
                    'name': product.name,
                    'size': product.cylinder_size,
                    'brand': product.brand
                }
                for product in obj.applicable_products.all()
            ]
        return []
    
    def validate(self, attrs):
        """Validate promotion dates and values"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date")
        
        discount_value = attrs.get('discount_value', 0)
        promotion_type = attrs.get('promotion_type')
        
        if promotion_type == 'percentage' and discount_value > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%")
        
        if discount_value < 0:
            raise serializers.ValidationError("Discount value cannot be negative")
        
        return attrs


class VendorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for vendor listings"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    distance = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'user_name', 'business_name', 'business_type',
            'latitude', 'longitude', 'delivery_radius', 'minimum_order_amount',
            'delivery_fee', 'average_rating', 'total_ratings', 'distance'
        ]


class VendorDashboardSerializer(serializers.Serializer):
    """Serializer for vendor dashboard data"""
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    low_stock_items = serializers.IntegerField()
    active_promotions = serializers.IntegerField()