# orders/serializers.py

from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking, Payment, OrderPromotion
from core.models import GasProduct

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model"""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'gas_product', 'quantity', 'unit_price',
            'total_price', 'product_name', 'cylinder_size', 'brand',
            'is_refill', 'customer_cylinder_serial', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at', 'updated_at']


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for OrderTracking model"""
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderTracking
        fields = [
            'id', 'order', 'status', 'notes', 'location_latitude',
            'location_longitude', 'updated_by', 'updated_by_name',
            'created_at'
        ]
        read_only_fields = ['id', 'updated_by_name', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'payment_id', 'amount',
            'payment_method', 'status', 'external_reference',
            'transaction_id', 'phone_number', 'initiated_at',
            'completed_at', 'gateway_response', 'failure_reason'
        ]
        read_only_fields = [
            'id', 'order_number', 'payment_id', 'initiated_at',
            'completed_at', 'gateway_response'
        ]


class OrderPromotionSerializer(serializers.ModelSerializer):
    """Serializer for OrderPromotion model"""
    promotion_title = serializers.CharField(source='promotion.title', read_only=True)
    
    class Meta:
        model = OrderPromotion
        fields = [
            'id', 'order', 'promotion', 'promotion_title',
            'discount_amount', 'created_at'
        ]
        read_only_fields = ['id', 'promotion_title', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.business_phone', read_only=True)
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    rider_phone = serializers.CharField(source='rider.phone_number', read_only=True)
    
    items = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    applied_promotions = OrderPromotionSerializer(many=True, read_only=True)
    
    is_deliverable = serializers.BooleanField(read_only=True)
    estimated_total_time = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'order_number', 'customer', 'customer_name',
            'customer_phone', 'vendor', 'vendor_name', 'vendor_phone',
            'rider', 'rider_name', 'rider_phone', 'order_type', 'status',
            'delivery_address', 'delivery_instructions', 'delivery_latitude',
            'delivery_longitude', 'requested_delivery_time',
            'estimated_delivery_time', 'actual_delivery_time', 'subtotal',
            'delivery_fee', 'discount_amount', 'tax_amount', 'total_amount',
            'payment_status', 'payment_method', 'payment_reference',
            'special_instructions', 'cancellation_reason', 'is_emergency',
            'items', 'tracking', 'payments', 'applied_promotions',
            'is_deliverable', 'estimated_total_time', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_id', 'order_number', 'customer_name', 'customer_phone',
            'vendor_name', 'vendor_phone', 'rider_name', 'rider_phone',
            'items', 'tracking', 'payments', 'applied_promotions',
            'is_deliverable', 'estimated_total_time', 'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    items = OrderItemSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'vendor', 'order_type', 'delivery_address', 'delivery_instructions',
            'delivery_latitude', 'delivery_longitude', 'requested_delivery_time',
            'special_instructions', 'is_emergency', 'items'
        ]
    
    def create(self, validated_data):
        """Create order with items"""
        items_data = validated_data.pop('items')
        validated_data['customer'] = self.context['request'].user
        
        order = Order.objects.create(**validated_data)
        
        # Create order items
        subtotal = 0
        for item_data in items_data:
            gas_product = item_data['gas_product']
            quantity = item_data['quantity']
            
            # Get price from vendor inventory or use base price
            try:
                from vendors.models import VendorInventory
                inventory = VendorInventory.objects.get(
                    vendor=order.vendor,
                    gas_product=gas_product
                )
                unit_price = inventory.refill_price if item_data.get('is_refill') else inventory.selling_price
            except VendorInventory.DoesNotExist:
                unit_price = gas_product.refill_price if item_data.get('is_refill') else gas_product.base_price
            
            total_price = quantity * unit_price
            subtotal += total_price
            
            OrderItem.objects.create(
                order=order,
                gas_product=gas_product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                product_name=gas_product.name,
                cylinder_size=gas_product.cylinder_size,
                brand=gas_product.brand,
                is_refill=item_data.get('is_refill', False),
                customer_cylinder_serial=item_data.get('customer_cylinder_serial', '')
            )
        
        # Calculate order totals
        order.subtotal = subtotal
        order.delivery_fee = order.vendor.delivery_fee
        order.total_amount = subtotal + order.delivery_fee
        order.save()
        
        # Create initial tracking entry
        OrderTracking.objects.create(
            order=order,
            status='pending',
            notes='Order created successfully',
            updated_by=order.customer
        )
        
        return order
    
    def validate_items(self, items):
        """Validate order items"""
        if not items:
            raise serializers.ValidationError("At least one item is required")
        
        for item in items:
            if item['quantity'] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0")
        
        return items


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order listings"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.business_name', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'vendor_name',
            'status', 'order_type', 'total_amount', 'payment_status',
            'items_count', 'created_at', 'estimated_delivery_time'
        ]
    
    def get_items_count(self, obj):
        """Get total number of items in order"""
        return obj.items.count()


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status"""
    
    class Meta:
        model = Order
        fields = ['status', 'rider', 'estimated_delivery_time', 'actual_delivery_time']
    
    def update(self, instance, validated_data):
        """Update order and create tracking entry"""
        old_status = instance.status
        instance = super().update(instance, validated_data)
        
        # Create tracking entry if status changed
        if old_status != instance.status:
            OrderTracking.objects.create(
                order=instance,
                status=instance.status,
                notes=f'Status updated from {old_status} to {instance.status}',
                updated_by=self.context['request'].user
            )
        
        return instance


class OrderEstimateSerializer(serializers.Serializer):
    """Serializer for order estimates"""
    vendor = serializers.IntegerField()
    items = OrderItemSerializer(many=True)
    delivery_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    
    def validate(self, attrs):
        """Validate estimate request"""
        try:
            from vendors.models import VendorProfile
            vendor = VendorProfile.objects.get(id=attrs['vendor'])
            attrs['vendor_obj'] = vendor
        except VendorProfile.DoesNotExist:
            raise serializers.ValidationError("Vendor not found")
        
        return attrs


class OrderRatingSerializer(serializers.Serializer):
    """Serializer for rating orders"""
    order = serializers.IntegerField()
    vendor_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    vendor_review = serializers.CharField(required=False, allow_blank=True)
    rider_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    rider_review = serializers.CharField(required=False, allow_blank=True)