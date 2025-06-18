from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    RiderProfile, RiderAvailability, RiderBankAccount, Delivery,
    RiderEarnings, RiderLocation, RiderIncentive, RiderPerformance
)

@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    """Rider Profile Admin"""
    
    list_display = [
        'user_name', 'user_email', 'vehicle_info', 'status',
        'is_available', 'average_rating', 'total_deliveries',
        'completion_rate_display', 'is_verified', 'created_at'
    ]
    list_filter = [
        'status', 'is_available', 'vehicle_type', 'verified_at', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'id_number', 'driving_license_number', 'vehicle_registration'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('id_number', 'driving_license_number', 'date_of_birth')
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship'
            ),
            'classes': ('collapse',)
        }),
        ('Vehicle Information', {
            'fields': (
                'vehicle_type', 'vehicle_registration', 'vehicle_make',
                'vehicle_model', 'vehicle_year', 'vehicle_color'
            )
        }),
        ('Documents', {
            'fields': (
                'insurance_policy_number', 'insurance_expiry', 'license_expiry',
                'verification_documents'
            ),
            'classes': ('collapse',)
        }),
        ('Service Area', {
            'fields': ('service_areas', 'max_delivery_distance')
        }),
        ('Availability', {
            'fields': ('status', 'is_available', 'current_latitude', 'current_longitude')
        }),
        ('Performance', {
            'fields': (
                'total_deliveries', 'successful_deliveries', 'average_rating',
                'total_ratings', 'average_delivery_time'
            ),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verified_at', 'verified_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'total_deliveries', 'successful_deliveries', 'average_rating',
        'total_ratings', 'average_delivery_time', 'verified_at',
        'created_at', 'updated_at'
    ]
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = "Name"
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"
    
    def vehicle_info(self, obj):
        return f"{obj.vehicle_type} - {obj.vehicle_registration}"
    vehicle_info.short_description = "Vehicle"
    
    def completion_rate_display(self, obj):
        rate = obj.completion_rate
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    completion_rate_display.short_description = "Completion Rate"
    
    def is_verified(self, obj):
        if obj.verified_at:
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: red;">✗ Not Verified</span>')
    is_verified.short_description = "Verified"


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Delivery Admin"""
    
    list_display = [
        'order_number', 'rider_name', 'customer_name', 'status',
        'assigned_at', 'delivered_at', 'total_earnings', 'duration_display'
    ]
    list_filter = ['status', 'assigned_at', 'delivered_at']
    search_fields = [
        'order__order_number', 'rider__user__email', 'order__customer__email'
    ]
    ordering = ['-assigned_at']
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = "Order"
    
    def rider_name(self, obj):
        return obj.rider.user.get_full_name()
    rider_name.short_description = "Rider"
    
    def customer_name(self, obj):
        return obj.order.customer.get_full_name()
    customer_name.short_description = "Customer"
    
    def duration_display(self, obj):
        if obj.delivered_at and obj.assigned_at:
            duration = obj.delivered_at - obj.assigned_at
            return f"{duration.total_seconds() / 60:.0f} min"
        return "N/A"
    duration_display.short_description = "Duration"
