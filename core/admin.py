# core/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Location, GasProduct, Rating, Notification, SystemSettings

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Location Admin"""
    
    list_display = [
        'name', 'user', 'user_role', 'city', 'county', 
        'is_default', 'is_active', 'created_at'
    ]
    list_filter = ['is_default', 'is_active', 'city', 'county', 'created_at']
    search_fields = [
        'name', 'user__email', 'user__first_name', 'user__last_name',
        'address_line_1', 'city', 'county'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'county', 'postal_code')
        }),
        ('Coordinates', {
            'fields': ('latitude', 'longitude')
        }),
        ('Additional Info', {
            'fields': ('landmark', 'instructions'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def user_role(self, obj):
        """Display user role"""
        return obj.user.role.title()
    user_role.short_description = "User Role"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')


@admin.register(GasProduct)
class GasProductAdmin(admin.ModelAdmin):
    """Gas Product Admin"""
    
    list_display = [
        'name', 'gas_type', 'cylinder_size', 'brand', 
        'base_price', 'refill_price', 'is_active', 'created_at'
    ]
    list_filter = ['gas_type', 'cylinder_size', 'brand', 'is_active', 'created_at']
    search_fields = ['name', 'brand', 'description']
    ordering = ['gas_type', 'cylinder_size', 'brand']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'gas_type', 'cylinder_size', 'brand', 'description')
        }),
        ('Specifications', {
            'fields': ('weight_empty', 'weight_full')
        }),
        ('Pricing', {
            'fields': ('base_price', 'refill_price')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['activate_products', 'deactivate_products']
    
    def activate_products(self, request, queryset):
        """Bulk activate products"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products were activated.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        """Bulk deactivate products"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products were deactivated.')
    deactivate_products.short_description = "Deactivate selected products"


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """Rating Admin"""
    
    list_display = [
        'customer', 'rating_type', 'rating', 'rating_stars',
        'vendor_or_rider', 'is_verified', 'is_published', 'created_at'
    ]
    list_filter = [
        'rating_type', 'rating', 'is_verified', 'is_published', 'created_at'
    ]
    search_fields = [
        'customer__email', 'customer__first_name', 'customer__last_name',
        'vendor__user__email', 'rider__user__email', 'review'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Rating Information', {
            'fields': ('customer', 'rating_type', 'rating')
        }),
        ('Target', {
            'fields': ('vendor', 'rider', 'order')
        }),
        ('Content', {
            'fields': ('review',)
        }),
        ('Status', {
            'fields': ('is_verified', 'is_published')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def rating_stars(self, obj):
        """Display rating as stars"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: gold; font-size: 16px;">{}</span>', stars)
    rating_stars.short_description = "Stars"
    
    def vendor_or_rider(self, obj):
        """Display vendor or rider name"""
        if obj.vendor:
            return f"Vendor: {obj.vendor.business_name}"
        elif obj.rider:
            return f"Rider: {obj.rider.user.get_full_name()}"
        return "N/A"
    vendor_or_rider.short_description = "Target"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'customer', 'vendor__user', 'rider__user', 'order'
        )
    
    actions = ['verify_ratings', 'publish_ratings', 'unpublish_ratings']
    
    def verify_ratings(self, request, queryset):
        """Bulk verify ratings"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} ratings were verified.')
    verify_ratings.short_description = "Verify selected ratings"
    
    def publish_ratings(self, request, queryset):
        """Bulk publish ratings"""
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} ratings were published.')
    publish_ratings.short_description = "Publish selected ratings"
    
    def unpublish_ratings(self, request, queryset):
        """Bulk unpublish ratings"""
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} ratings were unpublished.')
    unpublish_ratings.short_description = "Unpublish selected ratings"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification Admin"""
    
    list_display = [
        'recipient', 'title', 'notification_type', 'is_read', 
        'is_sent', 'sent_at', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_sent', 'send_push', 
        'send_email', 'send_sms', 'created_at'
    ]
    search_fields = [
        'recipient__email', 'recipient__first_name', 'recipient__last_name',
        'title', 'message'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'title', 'message', 'notification_type')
        }),
        ('Related Objects', {
            'fields': ('order',),
            'classes': ('collapse',)
        }),
        ('Delivery Status', {
            'fields': ('is_read', 'is_sent', 'sent_at')
        }),
        ('Delivery Channels', {
            'fields': ('send_push', 'send_email', 'send_sms'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('recipient', 'order')
    
    actions = ['mark_as_read', 'mark_as_sent']
    
    def mark_as_read(self, request, queryset):
        """Bulk mark as read"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications were marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_sent(self, request, queryset):
        """Bulk mark as sent"""
        from django.utils import timezone
        updated = queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(request, f'{updated} notifications were marked as sent.')
    mark_as_sent.short_description = "Mark selected notifications as sent"


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """System Settings Admin"""
    
    list_display = ['key', 'value_preview', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['key', 'value', 'description']
    ordering = ['key']
    
    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def value_preview(self, obj):
        """Show truncated value"""
        if len(obj.value) > 50:
            return f"{obj.value[:50]}..."
        return obj.value
    value_preview.short_description = "Value"
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of system settings"""
        return request.user.is_superuser