# customers/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    CustomerProfile, CustomerAddress, CustomerCylinder,
    CustomerPaymentMethod, CustomerFavorite, CustomerComplaint
)

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Customer Profile Admin"""
    
    list_display = [
        'user_name', 'user_email', 'customer_type', 'membership_tier',
        'total_orders', 'total_spent', 'loyalty_points', 'is_verified', 'created_at'
    ]
    list_filter = [
        'customer_type', 'membership_tier', 'is_verified', 'is_blocked', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'business_name', 'business_registration'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Customer Details', {
            'fields': ('customer_type', 'date_of_birth')
        }),
        ('Business Information', {
            'fields': ('business_name', 'business_registration', 'tax_pin'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': (
                'preferred_gas_size', 'preferred_brand', 'preferred_delivery_time',
                'default_delivery_instructions'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_orders', 'completed_orders', 'cancelled_orders',
                'total_spent', 'loyalty_points', 'membership_tier'
            ),
            'classes': ('collapse',)
        }),
        ('Communication Preferences', {
            'fields': (
                'sms_notifications', 'email_notifications', 
                'push_notifications', 'promotional_messages'
            ),
            'classes': ('collapse',)
        }),
        ('Account Status', {
            'fields': ('is_verified', 'verification_date', 'is_blocked', 'blocked_reason')
        }),
    )
    
    readonly_fields = [
        'total_orders', 'completed_orders', 'cancelled_orders', 
        'total_spent', 'loyalty_points', 'membership_tier',
        'verification_date', 'created_at', 'updated_at'
    ]
    
    def user_name(self, obj):
        """Display user full name"""
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = "Name"
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = "Email"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')
    
    actions = ['verify_customers', 'block_customers', 'unblock_customers']
    
    def verify_customers(self, request, queryset):
        """Bulk verify customers"""
        updated = queryset.update(is_verified=True, verification_date=timezone.now())
        self.message_user(request, f'{updated} customers were verified.')
    verify_customers.short_description = "Verify selected customers"
    
    def block_customers(self, request, queryset):
        """Bulk block customers"""
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f'{updated} customers were blocked.')
    block_customers.short_description = "Block selected customers"
    
    def unblock_customers(self, request, queryset):
        """Bulk unblock customers"""
        updated = queryset.update(is_blocked=False, blocked_reason='')
        self.message_user(request, f'{updated} customers were unblocked.')
    unblock_customers.short_description = "Unblock selected customers"


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    """Customer Address Admin"""
    
    list_display = [
        'customer_name', 'label', 'address_type', 'city', 'county',
        'is_default', 'is_active', 'times_used', 'last_used'
    ]
    list_filter = ['address_type', 'is_default', 'is_active', 'city', 'county']
    search_fields = [
        'customer__user__email', 'customer__user__first_name',
        'label', 'address_line_1', 'city'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Address Details', {
            'fields': (
                'address_type', 'label', 'address_line_1', 'address_line_2',
                'city', 'county', 'postal_code'
            )
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Additional Information', {
            'fields': ('landmark', 'delivery_instructions', 'gate_code'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
        ('Usage Statistics', {
            'fields': ('times_used', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['times_used', 'last_used', 'created_at', 'updated_at']
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.user.get_full_name() or obj.customer.user.username
    customer_name.short_description = "Customer"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('customer__user')


@admin.register(CustomerCylinder)
class CustomerCylinderAdmin(admin.ModelAdmin):
    """Customer Cylinder Admin"""
    
    list_display = [
        'customer_name', 'serial_number', 'brand', 'size',
        'status', 'current_fill_level', 'needs_refill_display',
        'last_refill_date', 'total_refills'
    ]
    list_filter = [
        'status', 'brand', 'size', 'is_with_customer', 'last_refill_date'
    ]
    search_fields = [
        'customer__user__email', 'customer__user__first_name',
        'serial_number', 'brand'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Cylinder Details', {
            'fields': ('serial_number', 'brand', 'size', 'purchase_date')
        }),
        ('Status', {
            'fields': ('status', 'current_fill_level', 'last_refill_date')
        }),
        ('Location', {
            'fields': ('current_location', 'is_with_customer')
        }),
        ('Maintenance', {
            'fields': (
                'last_inspection_date', 'next_inspection_due', 'safety_certificate'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_refills', 'total_cost_spent'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_refills', 'total_cost_spent', 'created_at', 'updated_at']
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.user.get_full_name() or obj.customer.user.username
    customer_name.short_description = "Customer"
    
    def needs_refill_display(self, obj):
        """Display refill status"""
        if obj.needs_refill:
            return format_html('<span style="color: red;">⚠ Needs Refill</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    needs_refill_display.short_description = "Refill Status"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('customer__user')


@admin.register(CustomerPaymentMethod)
class CustomerPaymentMethodAdmin(admin.ModelAdmin):
    """Customer Payment Method Admin"""
    
    list_display = [
        'customer_name', 'label', 'payment_type', 'is_default',
        'is_verified', 'times_used', 'last_used'
    ]
    list_filter = ['payment_type', 'is_default', 'is_verified', 'is_active']
    search_fields = [
        'customer__user__email', 'customer__user__first_name',
        'label', 'mpesa_number', 'bank_name'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'label')
        }),
        ('M-Pesa Information', {
            'fields': ('mpesa_number',),
            'classes': ('collapse',)
        }),
        ('Card Information', {
            'fields': ('card_last_four', 'card_type'),
            'classes': ('collapse',)
        }),
        ('Bank Information', {
            'fields': ('bank_name', 'account_number_masked'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_default', 'is_verified', 'is_active')
        }),
        ('Usage Statistics', {
            'fields': ('times_used', 'total_amount_spent', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'times_used', 'total_amount_spent', 'last_used', 'created_at', 'updated_at'
    ]
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.user.get_full_name() or obj.customer.user.username
    customer_name.short_description = "Customer"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('customer__user')


@admin.register(CustomerFavorite)
class CustomerFavoriteAdmin(admin.ModelAdmin):
    """Customer Favorite Admin"""
    
    list_display = [
        'customer_name', 'favorite_type', 'favorite_item',
        'times_ordered', 'last_ordered'
    ]
    list_filter = ['favorite_type', 'last_ordered']
    search_fields = [
        'customer__user__email', 'customer__user__first_name',
        'vendor__business_name', 'product__name'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Favorite Details', {
            'fields': ('favorite_type', 'vendor', 'product')
        }),
        ('Usage Statistics', {
            'fields': ('times_ordered', 'last_ordered'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['times_ordered', 'last_ordered', 'created_at', 'updated_at']
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.user.get_full_name() or obj.customer.user.username
    customer_name.short_description = "Customer"
    
    def favorite_item(self, obj):
        """Display favorite vendor or product"""
        if obj.vendor:
            return f"Vendor: {obj.vendor.business_name}"
        elif obj.product:
            return f"Product: {obj.product.name}"
        return "N/A"
    favorite_item.short_description = "Favorite Item"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'customer__user', 'vendor', 'product'
        )


@admin.register(CustomerComplaint)
class CustomerComplaintAdmin(admin.ModelAdmin):
    """Customer Complaint Admin"""
    
    list_display = [
        'complaint_id', 'customer_name', 'complaint_type', 'subject',
        'priority', 'status', 'satisfaction_rating', 'created_at'
    ]
    list_filter = [
        'complaint_type', 'priority', 'status', 'created_at'  # Removed 'is_resolved'
    ]
    search_fields = [
        'complaint_id', 'customer__user__email', 'customer__user__first_name',
        'subject', 'description'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Complaint Information', {
            'fields': ('customer', 'complaint_id', 'complaint_type', 'subject', 'priority')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Related Objects', {
            'fields': ('order', 'vendor', 'rider'),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('status', 'assigned_to', 'resolved_at', 'resolution')
        }),
        ('Customer Satisfaction', {
            'fields': ('satisfaction_rating', 'satisfaction_feedback'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['complaint_id', 'resolved_at', 'created_at', 'updated_at']
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.user.get_full_name() or obj.customer.user.username
    customer_name.short_description = "Customer"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'customer__user', 'order', 'vendor', 'rider__user', 'assigned_to'
        )
    
    actions = ['assign_to_me', 'mark_resolved', 'mark_in_progress']
    
    def assign_to_me(self, request, queryset):
        """Assign complaints to current user"""
        updated = queryset.update(assigned_to=request.user, status='in_progress')
        self.message_user(request, f'{updated} complaints were assigned to you.')
    assign_to_me.short_description = "Assign selected complaints to me"
    
    def mark_resolved(self, request, queryset):
        """Mark complaints as resolved"""
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'{updated} complaints were marked as resolved.')
    mark_resolved.short_description = "Mark selected complaints as resolved"
    
    def mark_in_progress(self, request, queryset):
        """Mark complaints as in progress"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} complaints were marked as in progress.')
    mark_in_progress.short_description = "Mark selected complaints as in progress"