# vendors/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    VendorProfile, VendorInventory, VendorHours, 
    VendorBankAccount, VendorPromotion
)

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """Vendor Profile Admin"""
    
    list_display = [
        'business_name', 'user_email', 'business_type', 'status',
        'average_rating', 'total_orders', 'completion_rate_display', 
        'is_verified', 'created_at'
    ]
    list_filter = [
        'business_type', 'status', 'verified_at', 'created_at'
    ]
    search_fields = [
        'business_name', 'user__email', 'user__first_name', 'user__last_name',
        'business_registration_number', 'business_address'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Business Information', {
            'fields': (
                'business_name', 'business_type', 'business_registration_number', 
                'tax_pin', 'business_address', 'business_phone', 'business_email'
            )
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Operating Details', {
            'fields': (
                'operating_hours_start', 'operating_hours_end', 'operating_days',
                'delivery_radius', 'minimum_order_amount', 'delivery_fee'
            )
        }),
        ('Capacity (Refill Stations)', {
            'fields': ('storage_capacity', 'daily_refill_capacity'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': (
                'status', 'verification_documents', 'verified_at', 
                'verified_by'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'total_orders', 'completed_orders', 'average_rating', 
                'total_ratings'
            ),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('commission_rate',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'total_orders', 'completed_orders', 'average_rating', 
        'total_ratings', 'verified_at', 'created_at', 'updated_at'
    ]
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = "Email"
    
    def completion_rate_display(self, obj):
        """Display completion rate with color"""
        rate = obj.completion_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    completion_rate_display.short_description = "Completion Rate"
    
    def is_verified(self, obj):
        """Display verification status"""
        if obj.verified_at:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Not Verified</span>'
        )
    is_verified.short_description = "Verified"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('user', 'verified_by')
    
    actions = ['verify_vendors', 'suspend_vendors', 'activate_vendors']
    
    def verify_vendors(self, request, queryset):
        """Bulk verify vendors"""
        updated = queryset.update(
            status='active',
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{updated} vendors were verified.')
    verify_vendors.short_description = "Verify selected vendors"
    
    def suspend_vendors(self, request, queryset):
        """Bulk suspend vendors"""
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} vendors were suspended.')
    suspend_vendors.short_description = "Suspend selected vendors"
    
    def activate_vendors(self, request, queryset):
        """Bulk activate vendors"""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} vendors were activated.')
    activate_vendors.short_description = "Activate selected vendors"


@admin.register(VendorInventory)
class VendorInventoryAdmin(admin.ModelAdmin):
    """Vendor Inventory Admin"""
    
    list_display = [
        'vendor_name', 'product_name', 'current_stock', 'available_stock_display',
        'selling_price', 'is_available', 'is_low_stock_display', 'last_restocked'
    ]
    list_filter = [
        'is_available', 'gas_product__gas_type', 'gas_product__cylinder_size',
        'auto_reorder', 'last_restocked'
    ]
    search_fields = [
        'vendor__business_name', 'gas_product__name', 'gas_product__brand'
    ]
    ordering = ['vendor__business_name', 'gas_product__name']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('vendor', 'gas_product')
        }),
        ('Stock Levels', {
            'fields': (
                'current_stock', 'reserved_stock', 'minimum_stock', 
                'maximum_stock'
            )
        }),
        ('Pricing', {
            'fields': ('selling_price', 'refill_price', 'cost_price')
        }),
        ('Settings', {
            'fields': ('is_available', 'auto_reorder', 'reorder_level')
        }),
        ('Tracking', {
            'fields': ('last_restocked', 'total_sold'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_sold', 'created_at', 'updated_at']
    
    def vendor_name(self, obj):
        """Display vendor name"""
        return obj.vendor.business_name
    vendor_name.short_description = "Vendor"
    
    def product_name(self, obj):
        """Display product name with size"""
        return f"{obj.gas_product.name} ({obj.gas_product.cylinder_size})"
    product_name.short_description = "Product"
    
    def available_stock_display(self, obj):
        """Display available stock with color"""
        stock = obj.available_stock
        if stock <= 0:
            color = 'red'
        elif stock <= obj.minimum_stock:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, stock
        )
    available_stock_display.short_description = "Available"
    
    def is_low_stock_display(self, obj):
        """Display low stock warning"""
        if obj.is_low_stock:
            return format_html(
                '<span style="color: red;">⚠ Low Stock</span>'
            )
        return format_html(
            '<span style="color: green;">✓ OK</span>'
        )
    is_low_stock_display.short_description = "Stock Status"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'vendor', 'gas_product'
        )

    actions = ['restock_items', 'mark_unavailable', 'mark_available']
    
    def restock_items(self, request, queryset):
        """Bulk restock items"""
        for item in queryset:
            item.current_stock = item.maximum_stock
            item.last_restocked = timezone.now()
            item.save()
        self.message_user(request, f'{queryset.count()} items were restocked to maximum.')
    restock_items.short_description = "Restock selected items to maximum"
    
    def mark_unavailable(self, request, queryset):
        """Mark items as unavailable"""
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} items were marked as unavailable.')
    mark_unavailable.short_description = "Mark selected items as unavailable"
    
    def mark_available(self, request, queryset):
        """Mark items as available"""
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} items were marked as available.')
    mark_available.short_description = "Mark selected items as available"


@admin.register(VendorHours)
class VendorHoursAdmin(admin.ModelAdmin):
    """Vendor Hours Admin"""
    
    list_display = [
        'vendor_name', 'day', 'hours_display', 'is_closed'
    ]
    list_filter = ['day', 'is_closed']
    search_fields = ['vendor__business_name']
    ordering = ['vendor__business_name', 'day']
    
    fieldsets = (
        ('Vendor Information', {
            'fields': ('vendor', 'day')
        }),
        ('Operating Hours', {
            'fields': ('open_time', 'close_time', 'is_closed')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def vendor_name(self, obj):
        """Display vendor name"""
        return obj.vendor.business_name
    vendor_name.short_description = "Vendor"
    
    def hours_display(self, obj):
        """Display operating hours"""
        if obj.is_closed:
            return format_html('<span style="color: red;">Closed</span>')
        return f"{obj.open_time} - {obj.close_time}"
    hours_display.short_description = "Hours"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('vendor')

    actions = ['close_days', 'open_days']
    
    def close_days(self, request, queryset):
        """Mark selected days as closed"""
        updated = queryset.update(is_closed=True)
        self.message_user(request, f'{updated} operating days were marked as closed.')
    close_days.short_description = "Mark selected days as closed"
    
    def open_days(self, request, queryset):
        """Mark selected days as open"""
        updated = queryset.update(is_closed=False)
        self.message_user(request, f'{updated} operating days were marked as open.')
    open_days.short_description = "Mark selected days as open"


@admin.register(VendorBankAccount)
class VendorBankAccountAdmin(admin.ModelAdmin):
    """Vendor Bank Account Admin"""
    
    list_display = [
        'vendor_name', 'bank_name', 'account_name', 'account_number_masked',
        'is_primary', 'is_verified', 'verification_date'
    ]
    list_filter = ['bank_name', 'is_primary', 'is_verified', 'verification_date']
    search_fields = [
        'vendor__business_name', 'bank_name', 'account_name', 
        'account_number', 'mpesa_number'
    ]
    ordering = ['vendor__business_name']
    
    fieldsets = (
        ('Vendor Information', {
            'fields': ('vendor',)
        }),
        ('Bank Information', {
            'fields': (
                'bank_name', 'account_name', 'account_number', 
                'branch', 'swift_code'
            )
        }),
        ('Mobile Money', {
            'fields': ('mpesa_number', 'mpesa_name'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_primary', 'is_verified', 'verification_date')
        }),
    )
    
    readonly_fields = ['verification_date', 'created_at', 'updated_at']
    
    def vendor_name(self, obj):
        """Display vendor name"""
        return obj.vendor.business_name
    vendor_name.short_description = "Vendor"
    
    def account_number_masked(self, obj):
        """Display masked account number"""
        if len(obj.account_number) > 4:
            return f"****{obj.account_number[-4:]}"
        return obj.account_number
    account_number_masked.short_description = "Account Number"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('vendor')

    actions = ['verify_accounts', 'set_as_primary']
    
    def verify_accounts(self, request, queryset):
        """Verify bank accounts"""
        updated = queryset.update(is_verified=True, verification_date=timezone.now())
        self.message_user(request, f'{updated} bank accounts were verified.')
    verify_accounts.short_description = "Verify selected bank accounts"
    
    def set_as_primary(self, request, queryset):
        """Set accounts as primary (only if single selection)"""
        if queryset.count() == 1:
            account = queryset.first()
            # Remove primary from other accounts of same vendor
            VendorBankAccount.objects.filter(vendor=account.vendor).update(is_primary=False)
            # Set this as primary
            account.is_primary = True
            account.save()
            self.message_user(request, f'Account for {account.vendor.business_name} set as primary.')
        else:
            self.message_user(request, 'Please select only one account to set as primary.', level='WARNING')
    set_as_primary.short_description = "Set as primary account (select only one)"


@admin.register(VendorPromotion)
class VendorPromotionAdmin(admin.ModelAdmin):
    """Vendor Promotion Admin"""
    
    list_display = [
        'title', 'vendor_name', 'promotion_type', 'discount_value',
        'start_date', 'end_date', 'is_active', 'is_valid_display', 'total_used'
    ]
    list_filter = [
        'promotion_type', 'is_active', 'start_date', 'end_date'
    ]
    search_fields = [
        'title', 'vendor__business_name', 'description'
    ]
    ordering = ['-start_date']
    
    fieldsets = (
        ('Promotion Information', {
            'fields': ('vendor', 'title', 'description', 'promotion_type')
        }),
        ('Discount Details', {
            'fields': (
                'discount_value', 'minimum_order_amount', 'maximum_discount'
            )
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_limit_per_customer')
        }),
        ('Validity', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Applicable Products', {
            'fields': ('applicable_products',),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('total_used',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_used', 'created_at', 'updated_at']
    filter_horizontal = ['applicable_products']
    
    def vendor_name(self, obj):
        """Display vendor name"""
        return obj.vendor.business_name
    vendor_name.short_description = "Vendor"
    
    def is_valid_display(self, obj):
        """Display validity status"""
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_display.short_description = "Status"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('vendor').prefetch_related('applicable_products')
    
    actions = ['activate_promotions', 'deactivate_promotions', 'extend_promotions']
    
    def activate_promotions(self, request, queryset):
        """Bulk activate promotions"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotions were activated.')
    activate_promotions.short_description = "Activate selected promotions"
    
    def deactivate_promotions(self, request, queryset):
        """Bulk deactivate promotions"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotions were deactivated.')
    deactivate_promotions.short_description = "Deactivate selected promotions"
    
    def extend_promotions(self, request, queryset):
        """Extend promotion end dates by 7 days"""
        from datetime import timedelta
        for promotion in queryset:
            promotion.end_date = promotion.end_date + timedelta(days=7)
            promotion.save()
        self.message_user(request, f'{queryset.count()} promotions were extended by 7 days.')
    extend_promotions.short_description = "Extend selected promotions by 7 days"

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of promotions that have been used"""
        if obj and obj.total_used > 0:
            return False
        return super().has_delete_permission(request, obj)