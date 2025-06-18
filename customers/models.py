# customers/models.py

from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

class CustomerProfile(TimeStampedModel):
    """Extended profile for customers"""
    
    CUSTOMER_TYPES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('restaurant', 'Restaurant'),
        ('institution', 'Institution'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        limit_choices_to={'role': 'customer'}
    )
    
    # Customer Information
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='individual')
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Business Information (if applicable)
    business_name = models.CharField(max_length=200, blank=True)
    business_registration = models.CharField(max_length=50, blank=True)
    tax_pin = models.CharField(max_length=20, blank=True)
    
    # Preferences
    preferred_gas_size = models.CharField(max_length=10, blank=True)
    preferred_brand = models.CharField(max_length=50, blank=True)
    preferred_delivery_time = models.CharField(max_length=50, blank=True)
    
    # Default Delivery Information
    default_delivery_instructions = models.TextField(blank=True)
    
    # Usage Statistics
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Customer Loyalty
    loyalty_points = models.IntegerField(default=0)
    membership_tier = models.CharField(
        max_length=20,
        choices=[
            ('bronze', 'Bronze'),
            ('silver', 'Silver'),
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
        ],
        default='bronze'
    )
    
    # Communication Preferences
    sms_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    promotional_messages = models.BooleanField(default=True)
    
    # Account Status
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'customers_profile'
        indexes = [
            models.Index(fields=['customer_type']),
            models.Index(fields=['membership_tier']),
            models.Index(fields=['total_orders']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.customer_type})"
    
    @property
    def order_completion_rate(self):
        if self.total_orders == 0:
            return 0
        return (self.completed_orders / self.total_orders) * 100
    
    @property
    def average_order_value(self):
        if self.completed_orders == 0:
            return 0
        return self.total_spent / self.completed_orders


class CustomerAddress(TimeStampedModel):
    """Customer delivery addresses"""
    
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('business', 'Business'),
        ('other', 'Other'),
    ]
    
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    
    # Address Details
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home')
    label = models.CharField(max_length=100, help_text="e.g., Home, Office, John's Place")
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
    delivery_instructions = models.TextField(blank=True)
    gate_code = models.CharField(max_length=50, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Usage Statistics
    times_used = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customers_address'
        indexes = [
            models.Index(fields=['customer', 'is_default']),
            models.Index(fields=['address_type']),
        ]
    
    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.label}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per customer
        if self.is_default:
            CustomerAddress.objects.filter(customer=self.customer, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class CustomerCylinder(TimeStampedModel):
    """Track customer-owned gas cylinders"""
    
    CYLINDER_STATUS = [
        ('active', 'Active'),
        ('empty', 'Empty'),
        ('refilling', 'Being Refilled'),
        ('damaged', 'Damaged'),
        ('lost', 'Lost'),
        ('returned', 'Returned'),
    ]
    
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='cylinders'
    )
    
    # Cylinder Information
    serial_number = models.CharField(max_length=50, unique=True)
    brand = models.CharField(max_length=50)
    size = models.CharField(max_length=10)  # e.g., 13kg, 6kg
    purchase_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=CYLINDER_STATUS, default='active')
    current_fill_level = models.IntegerField(
        default=100,
        help_text="Fill level percentage (0-100)"
    )
    last_refill_date = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    current_location = models.CharField(max_length=200, blank=True, help_text="Where the cylinder currently is")
    is_with_customer = models.BooleanField(default=True)
    
    # Maintenance
    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_due = models.DateField(null=True, blank=True)
    safety_certificate = models.FileField(upload_to='cylinder_certs/', blank=True, null=True)
    
    # Usage Statistics
    total_refills = models.IntegerField(default=0)
    total_cost_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        db_table = 'customers_cylinder'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.brand} {self.size} ({self.serial_number})"
    
    @property
    def needs_refill(self):
        return self.current_fill_level <= 10
    
    @property
    def needs_inspection(self):
        from django.utils import timezone
        if not self.next_inspection_due:
            return False
        return timezone.now().date() >= self.next_inspection_due


class CustomerPaymentMethod(TimeStampedModel):
    """Customer payment methods"""
    
    PAYMENT_TYPES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
    ]
    
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Payment Method Details
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    label = models.CharField(max_length=100, help_text="e.g., Personal M-Pesa, Work Card")
    
    # M-Pesa Information
    mpesa_number = models.CharField(max_length=17, blank=True)
    
    # Card Information (stored securely/tokenized)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_type = models.CharField(max_length=20, blank=True)  # Visa, Mastercard, etc.
    card_token = models.CharField(max_length=200, blank=True)  # Payment gateway token
    
    # Bank Account Information
    bank_name = models.CharField(max_length=100, blank=True)
    account_number_masked = models.CharField(max_length=50, blank=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Usage Statistics
    times_used = models.IntegerField(default=0)
    total_amount_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customers_payment_method'
        indexes = [
            models.Index(fields=['customer', 'is_default']),
            models.Index(fields=['payment_type']),
        ]
    
    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.label}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per customer
        if self.is_default:
            CustomerPaymentMethod.objects.filter(customer=self.customer, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class CustomerFavorite(TimeStampedModel):
    """Customer favorite vendors and products"""
    
    FAVORITE_TYPES = [
        ('vendor', 'Vendor'),
        ('product', 'Product'),
    ]
    
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    
    favorite_type = models.CharField(max_length=10, choices=FAVORITE_TYPES)
    
    # Related Objects
    vendor = models.ForeignKey(
        'vendors.VendorProfile',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='favorited_by'
    )
    product = models.ForeignKey(
        'core.GasProduct',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='favorited_by'
    )
    
    # Usage
    times_ordered = models.IntegerField(default=0)
    last_ordered = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customers_favorite'
        unique_together = [
            ('customer', 'vendor'),
            ('customer', 'product'),
        ]
        indexes = [
            models.Index(fields=['customer', 'favorite_type']),
        ]
    
    def __str__(self):
        if self.vendor:
            return f"{self.customer.user.get_full_name()} ❤️ {self.vendor.business_name}"
        elif self.product:
            return f"{self.customer.user.get_full_name()} ❤️ {self.product.name}"
        return f"{self.customer.user.get_full_name()}'s favorite"


class CustomerComplaint(TimeStampedModel):
    """Customer complaints and support tickets"""
    
    COMPLAINT_TYPES = [
        ('delivery', 'Delivery Issue'),
        ('product', 'Product Quality'),
        ('payment', 'Payment Issue'),
        ('vendor', 'Vendor Service'),
        ('rider', 'Rider Behavior'),
        ('app', 'App/Technical Issue'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='complaints'
    )
    
    # Complaint Details
    complaint_id = models.CharField(max_length=20, unique=True)
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Related Objects
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints'
    )
    vendor = models.ForeignKey(
        'vendors.VendorProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints'
    )
    rider = models.ForeignKey(
        'riders.RiderProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints'
    )
    
    # Status and Resolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_complaints',
        limit_choices_to={'role': 'admin'}
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    
    # Customer Satisfaction
    satisfaction_rating = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)]  # 1-5 stars
    )
    satisfaction_feedback = models.TextField(blank=True)
    
    class Meta:
        db_table = 'customers_complaint'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['complaint_type', 'status']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"{self.complaint_id} - {self.customer.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.complaint_id:
            self.complaint_id = self.generate_complaint_id()
        super().save(*args, **kwargs)
    
    def generate_complaint_id(self):
        """Generate unique complaint ID"""
        from datetime import datetime
        date_str = datetime.now().strftime('%y%m%d')
        last_complaint = CustomerComplaint.objects.filter(
            complaint_id__startswith=f'CMP{date_str}'
        ).order_by('-complaint_id').first()
        
        if last_complaint:
            last_sequence = int(last_complaint.complaint_id[-3:])
            sequence = f"{last_sequence + 1:03d}"
        else:
            sequence = "001"
        
        return f"CMP{date_str}{sequence}"