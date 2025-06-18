# core/models.py

from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    """Abstract base model with timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Location(TimeStampedModel):
    """Location model for storing addresses and coordinates"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='locations'
    )
    
    # Address Information
    name = models.CharField(max_length=100, help_text="e.g., Home, Office, Shop")
    address_line_1 = models.CharField(max_length=200)
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, blank=True)
    
    # Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Additional Information
    landmark = models.CharField(max_length=200, blank=True)
    instructions = models.TextField(blank=True, help_text="Delivery instructions")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'core_location'
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default location per user
        if self.is_default:
            Location.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class GasProduct(TimeStampedModel):
    """Gas product types and specifications"""
    
    CYLINDER_SIZES = [
        ('3kg', '3 KG'),
        ('6kg', '6 KG'),
        ('13kg', '13 KG'),
        ('50kg', '50 KG'),
    ]
    
    GAS_TYPES = [
        ('lpg', 'LPG (Liquefied Petroleum Gas)'),
        ('industrial', 'Industrial Gas'),
        ('cooking', 'Cooking Gas'),
    ]
    
    name = models.CharField(max_length=100)
    gas_type = models.CharField(max_length=20, choices=GAS_TYPES, default='lpg')
    cylinder_size = models.CharField(max_length=10, choices=CYLINDER_SIZES)
    brand = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    
    # Specifications
    weight_empty = models.DecimalField(max_digits=5, decimal_places=2, help_text="Empty cylinder weight in KG")
    weight_full = models.DecimalField(max_digits=5, decimal_places=2, help_text="Full cylinder weight in KG")
    
    # Pricing (base prices, vendors can adjust)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    refill_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'core_gas_product'
        unique_together = ['gas_type', 'cylinder_size', 'brand']
        indexes = [
            models.Index(fields=['gas_type', 'cylinder_size']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.cylinder_size}"


class Rating(TimeStampedModel):
    """Rating system for vendors, riders, and orders"""
    
    RATING_TYPES = [
        ('vendor', 'Vendor Rating'),
        ('rider', 'Rider Rating'),
        ('order', 'Order Rating'),
    ]
    
    # Who is rating
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_given',
        limit_choices_to={'role': 'customer'}
    )
    
    # What is being rated
    rating_type = models.CharField(max_length=10, choices=RATING_TYPES)
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_ratings',
        null=True, blank=True,
        limit_choices_to={'role': 'vendor'}
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_ratings',
        null=True, blank=True,
        limit_choices_to={'role': 'rider'}
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='ratings',
        null=True, blank=True
    )
    
    # Rating Details
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    review = models.TextField(blank=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'core_rating'
        unique_together = [
            ('customer', 'vendor', 'order'),
            ('customer', 'rider', 'order'),
        ]
        indexes = [
            models.Index(fields=['rating_type', 'rating']),
            models.Index(fields=['vendor', 'rating']),
            models.Index(fields=['rider', 'rating']),
        ]
    
    def __str__(self):
        if self.vendor:
            return f"{self.rating}★ for {self.vendor.get_full_name()}"
        elif self.rider:
            return f"{self.rating}★ for {self.rider.get_full_name()}"
        return f"{self.rating}★ rating"


class Notification(TimeStampedModel):
    """Notification system for all users"""
    
    NOTIFICATION_TYPES = [
        ('order_update', 'Order Update'),
        ('payment_update', 'Payment Update'),
        ('delivery_update', 'Delivery Update'),
        ('system_update', 'System Update'),
        ('promotion', 'Promotion'),
        ('reminder', 'Reminder'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Related Objects
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery Channels
    send_push = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'core_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"


class SystemSettings(models.Model):
    """System-wide settings and configurations"""
    
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"