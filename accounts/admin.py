# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, UserActivity

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = [
        'email', 'username', 'first_name', 'last_name', 
        'role', 'vendor_type', 'is_verified', 'is_active', 
        'created_at', 'profile_picture_preview'
    ]
    list_filter = [
        'role', 'vendor_type', 'is_verified', 'is_active', 
        'created_at', 'city', 'county'
    ]
    search_fields = [
        'email', 'username', 'first_name', 'last_name', 
        'phone_number', 'address'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')
        }),
        ('Role & Type', {
            'fields': ('role', 'vendor_type')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'address', 'city', 'county'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_document'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'phone_number'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_active']
    
    def profile_picture_preview(self, obj):
        """Show profile picture preview"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return "No Image"
    profile_picture_preview.short_description = "Picture"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related()
    
    actions = ['verify_users', 'deactivate_users', 'activate_users']
    
    def verify_users(self, request, queryset):
        """Bulk verify users"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users were verified.')
    verify_users.short_description = "Verify selected users"
    
    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users were deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def activate_users(self, request, queryset):
        """Bulk activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users were activated.')
    activate_users.short_description = "Activate selected users"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User Profile Admin"""
    
    list_display = [
        'user', 'user_role', 'date_of_birth', 'gender', 
        'preferred_language', 'receive_notifications', 'created_at'
    ]
    list_filter = [
        'gender', 'preferred_language', 'receive_notifications', 
        'receive_sms', 'receive_email', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name', 
        'id_number', 'emergency_contact_name'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'gender', 'id_number')
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'receive_notifications', 'receive_sms', 'receive_email')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def user_role(self, obj):
        """Display user role"""
        return obj.user.role.title()
    user_role.short_description = "Role"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User Activity Admin"""
    
    list_display = [
        'user', 'activity_type', 'description', 'ip_address', 'timestamp'
    ]
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['user__email', 'user__username', 'description', 'ip_address']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'description')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        """Prevent manual addition of activities"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of activities"""
        return False
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user')