from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderTracking, Payment, OrderPromotion

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order Admin"""
    
    list_display = [
        'order_number', 'customer_name', 'vendor_name', 'status',
        'total_amount', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'order_type', 'created_at']
    search_fields = [
        'order_number', 'customer__email', 'vendor__business_name'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'vendor', 'rider', 'order_type')
        }),
        ('Delivery Details', {
            'fields': (
                'delivery_address', 'delivery_instructions',
                'delivery_latitude', 'delivery_longitude'
            )
        }),
        ('Timing', {
            'fields': (
                'requested_delivery_time', 'estimated_delivery_time',
                'actual_delivery_time'
            )
        }),
        ('Pricing', {
            'fields': (
                'subtotal', 'delivery_fee', 'discount_amount',
                'tax_amount', 'total_amount'
            )
        }),
        ('Status', {
            'fields': ('status', 'payment_status', 'payment_method', 'payment_reference')
        }),
    )
    
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    
    def customer_name(self, obj):
        return obj.customer.get_full_name()
    customer_name.short_description = "Customer"
    
    def vendor_name(self, obj):
        return obj.vendor.business_name
    vendor_name.short_description = "Vendor"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order Item Admin"""
    
    list_display = [
        'order_number', 'product_name', 'quantity', 'unit_price', 'total_price'
    ]
    list_filter = ['is_refill', 'created_at']
    search_fields = ['order__order_number', 'product_name', 'brand']
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = "Order"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment Admin"""
    
    list_display = [
        'order_number', 'amount', 'payment_method', 'status',
        'initiated_at', 'completed_at'
    ]
    list_filter = ['payment_method', 'status', 'initiated_at']
    search_fields = ['order__order_number', 'external_reference', 'transaction_id']
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = "Order"

