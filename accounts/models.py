# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    """Custom User model with role-based access"""
    
    USER_ROLES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('rider', 'Rider'),
        ('admin', 'Admin'),
    ]
    
    VENDOR_TYPES = [
        ('retailer', 'Retailer'),
        ('refill_station', 'Refill Station'),
    ]
    
    # Basic Information
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    
    # Role and Profile
    role = models.CharField(max_length=20, choices=USER_ROLES, default='customer')
    vendor_type = models.CharField(
        max_length=20, 
        choices=VENDOR_TYPES, 
        blank=True, 
        null=True,
        help_text="Only applicable for vendors"
    )
    
    # Location Information
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    
    # Profile Information
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_document = models.FileField(upload_to='verification/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Make email the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone_number', 'role']
    
    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_customer(self):
        return self.role == 'customer'
    
    @property
    def is_vendor(self):
        return self.role == 'vendor'
    
    @property
    def is_rider(self):
        return self.role == 'rider'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'


class UserProfile(models.Model):
    """Extended profile information for all users"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Additional Information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True
    )
    id_number = models.CharField(max_length=20, blank=True, unique=True, null=True)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('sw', 'Swahili')],
        default='en'
    )
    receive_notifications = models.BooleanField(default=True)
    receive_sms = models.BooleanField(default=True)
    receive_email = models.BooleanField(default=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=17, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_user_profile'
    
    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"


class UserActivity(models.Model):
    """Track user activity for analytics"""
    
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('order_placed', 'Order Placed'),
        ('order_completed', 'Order Completed'),
        ('profile_updated', 'Profile Updated'),
        ('password_changed', 'Password Changed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'accounts_user_activity'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.activity_type} at {self.timestamp}"