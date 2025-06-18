# orders/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import TimeStampedModel, GasProduct
from vendors.models import VendorProfile
import uuid

class Order(TimeStampedModel):
    """Main order model"""
    
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    ORDER_TYPES = [
        ('delivery', 'Home Delivery'),
        ('pickup', 'Customer Pickup'),
        ('refill', 'Cylinder Refill'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order Identification
    order_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_number = models.CharField(max_length=20, unique=True)
    
    # Parties Involved
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        limit_choices_to={'role': 'customer'}
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries',
        limit_choices_to={'role': 'rider'}
    )
    
    # Order Details
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES, default='delivery')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    
    # Delivery Information
    delivery_address = models.TextField()
    delivery_instructions = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Timing
    requested_delivery_time = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Additional Information
    special_instructions = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    is_emergency = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['rider', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        from datetime import datetime
        date_str = datetime.now().strftime('%Y%m%d')
        last_order = Order.objects.filter(order_number__startswith=f'KAA{date_str}').order_by('-order_number').first()
        
        if last_order:
            last_sequence = int(last_order.order_number[-4:])
            sequence = f"{last_sequence + 1:04d}"
        else:
            sequence = "0001"
        
        return f"KAA{date_str}{sequence}"
    
    @property
    def is_deliverable(self):
        """Check if order can be delivered"""
        return self.status in ['confirmed', 'preparing', 'ready_for_pickup']
    
    @property
    def estimated_total_time(self):
        """Estimate total delivery time in minutes"""
        if self.order_type == 'pickup':
            return 30  # Standard preparation time
        return 60  # Preparation + delivery time


class OrderItem(TimeStampedModel):
    """Individual items in an order"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    gas_product = models.ForeignKey(GasProduct, on_delete=models.CASCADE)
    
    # Quantity and Pricing
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Product details at time of order (for historical accuracy)
    product_name = models.CharField(max_length=100)
    cylinder_size = models.CharField(max_length=10)
    brand = models.CharField(max_length=50, blank=True)
    
    # Service Type
    is_refill = models.BooleanField(default=False)
    customer_cylinder_serial = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'orders_order_item'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['gas_product']),
        ]
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} - {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class OrderTracking(TimeStampedModel):
    """Track order status changes"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking')
    status = models.CharField(max_length=20, choices=Order.ORDER_STATUS)
    notes = models.TextField(blank=True)
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Who updated the status
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    class Meta:
        db_table = 'orders_tracking'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.created_at}"


class Payment(TimeStampedModel):
    """Payment records for orders"""
    
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash on Delivery'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # External Payment Information
    external_reference = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=17, blank=True)  # For M-Pesa
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Response Data
    gateway_response = models.JSONField(blank=True, null=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'orders_payment'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.order.order_number} ({self.status})"


class OrderPromotion(TimeStampedModel):
    """Track promotion usage in orders"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='applied_promotions')
    promotion = models.ForeignKey(
        'vendors.VendorPromotion',
        on_delete=models.CASCADE,
        related_name='used_in_orders'
    )
    
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        db_table = 'orders_promotion'
        unique_together = ['order', 'promotion']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.promotion.title}"