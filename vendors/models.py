# vendors/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel, GasProduct

class VendorProfile(TimeStampedModel):
    """Extended profile for vendors (retailers and refill stations)"""
    
    BUSINESS_TYPES = [
        ('retailer', 'Gas Retailer'),
        ('refill_station', 'Refill Station'),
        ('both', 'Retailer & Refill Station'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_profile',
        limit_choices_to={'role': 'vendor'}
    )
    
    # Business Information
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default='retailer')
    business_registration_number = models.CharField(max_length=50, unique=True)
    tax_pin = models.CharField(max_length=20, blank=True)
    
    # Location and Contact
    business_address = models.TextField()
    business_phone = models.CharField(max_length=17)
    business_email = models.EmailField(blank=True)
    
    # Coordinates for mapping
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Operating Information
    operating_hours_start = models.TimeField()
    operating_hours_end = models.TimeField()
    operating_days = models.CharField(
        max_length=20,
        default='monday-sunday',
        help_text="Operating days of the week"
    )
    
    # Service Area
    delivery_radius = models.IntegerField(
        default=5,
        help_text="Delivery radius in kilometers",
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum order amount for delivery"
    )
    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Standard delivery fee"
    )
    
    # Capacity (for refill stations)
    storage_capacity = models.IntegerField(
        null=True, blank=True,
        help_text="Storage capacity in cylinders (for refill stations)"
    )
    daily_refill_capacity = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum refills per day"
    )
    
    # Status and Verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_documents = models.FileField(upload_to='vendor_docs/', blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_vendors',
        limit_choices_to={'role': 'admin'}
    )
    
    # Business Metrics
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.IntegerField(default=0)
    
    # Financial Information
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        help_text="Commission rate percentage"
    )
    
    class Meta:
        db_table = 'vendors_profile'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['business_type']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['average_rating']),
        ]
    
    def __str__(self):
        return f"{self.business_name} ({self.business_type})"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def completion_rate(self):
        if self.total_orders == 0:
            return 0
        return (self.completed_orders / self.total_orders) * 100


class VendorInventory(TimeStampedModel):
    """Inventory management for vendors"""
    
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    gas_product = models.ForeignKey(GasProduct, on_delete=models.CASCADE)
    
    # Stock Information
    current_stock = models.IntegerField(default=0)
    reserved_stock = models.IntegerField(default=0)  # Stock reserved for pending orders
    minimum_stock = models.IntegerField(default=5)
    maximum_stock = models.IntegerField(default=100)
    
    # Pricing
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    refill_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    is_available = models.BooleanField(default=True)
    auto_reorder = models.BooleanField(default=False)
    reorder_level = models.IntegerField(default=10)
    
    # Tracking
    last_restocked = models.DateTimeField(null=True, blank=True)
    total_sold = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'vendors_inventory'
        unique_together = ['vendor', 'gas_product']
        indexes = [
            models.Index(fields=['vendor', 'is_available']),
            models.Index(fields=['current_stock']),
        ]
    
    def __str__(self):
        return f"{self.vendor.business_name} - {self.gas_product.name} ({self.current_stock} in stock)"
    
    @property
    def available_stock(self):
        """Stock available for new orders"""
        return max(0, self.current_stock - self.reserved_stock)
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.current_stock <= self.minimum_stock
    
    @property
    def is_out_of_stock(self):
        """Check if completely out of stock"""
        return self.current_stock <= 0


class VendorHours(TimeStampedModel):
    """Detailed operating hours for vendors"""
    
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='operating_hours'
    )
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'vendors_hours'
        unique_together = ['vendor', 'day']
    
    def __str__(self):
        if self.is_closed:
            return f"{self.vendor.business_name} - {self.day.title()}: Closed"
        return f"{self.vendor.business_name} - {self.day.title()}: {self.open_time} - {self.close_time}"


class VendorBankAccount(TimeStampedModel):
    """Bank account information for vendors (for payments)"""
    
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    
    # Bank Information
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    branch = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Mobile Money
    mpesa_number = models.CharField(max_length=17, blank=True)
    mpesa_name = models.CharField(max_length=100, blank=True)
    
    # Status
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'vendors_bank_account'
        indexes = [
            models.Index(fields=['vendor', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.vendor.business_name} - {self.bank_name} ({self.account_number})"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary account per vendor
        if self.is_primary:
            VendorBankAccount.objects.filter(vendor=self.vendor, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class VendorPromotion(TimeStampedModel):
    """Promotions and discounts offered by vendors"""
    
    PROMOTION_TYPES = [
        ('percentage', 'Percentage Discount'),
        ('fixed_amount', 'Fixed Amount Discount'),
        ('buy_one_get_one', 'Buy One Get One'),
        ('free_delivery', 'Free Delivery'),
    ]
    
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='promotions'
    )
    
    # Promotion Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Conditions
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Maximum number of uses")
    usage_limit_per_customer = models.IntegerField(default=1)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Applicable Products
    applicable_products = models.ManyToManyField(
        GasProduct,
        blank=True,
        help_text="Leave empty for all products"
    )
    
    # Usage Tracking
    total_used = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'vendors_promotion'
        indexes = [
            models.Index(fields=['vendor', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.vendor.business_name} - {self.title}"
    
    @property
    def is_valid(self):
        """Check if promotion is currently valid"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date and
            (self.usage_limit is None or self.total_used < self.usage_limit)
        )