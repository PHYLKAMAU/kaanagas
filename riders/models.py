# riders/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TimeStampedModel

class RiderProfile(TimeStampedModel):
    """Extended profile for delivery riders"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ]
    
    VEHICLE_TYPES = [
        ('motorcycle', 'Motorcycle'),
        ('bicycle', 'Bicycle'),
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('van', 'Van'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_profile',
        limit_choices_to={'role': 'rider'}
    )
    
    # Personal Information
    id_number = models.CharField(max_length=20, unique=True)
    driving_license_number = models.CharField(max_length=50, unique=True)
    date_of_birth = models.DateField()
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=17)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Vehicle Information
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    vehicle_registration = models.CharField(max_length=20, unique=True)
    vehicle_make = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=50)
    vehicle_year = models.IntegerField()
    vehicle_color = models.CharField(max_length=30)
    
    # Insurance and Documents
    insurance_policy_number = models.CharField(max_length=50)
    insurance_expiry = models.DateField()
    license_expiry = models.DateField()
    
    # Service Area
    service_areas = models.TextField(help_text="Areas where rider operates (comma separated)")
    max_delivery_distance = models.IntegerField(
        default=10,
        help_text="Maximum delivery distance in kilometers",
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    
    # Availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_available = models.BooleanField(default=False)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    # Performance Metrics
    total_deliveries = models.IntegerField(default=0)
    successful_deliveries = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.IntegerField(default=0)
    average_delivery_time = models.IntegerField(default=0, help_text="Average delivery time in minutes")
    
    # Financial Information
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Commission rate percentage per delivery"
    )
    
    # Verification
    verification_documents = models.FileField(upload_to='rider_docs/', blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_riders',
        limit_choices_to={'role': 'admin'}
    )
    
    class Meta:
        db_table = 'riders_profile'
        indexes = [
            models.Index(fields=['status', 'is_available']),
            models.Index(fields=['current_latitude', 'current_longitude']),
            models.Index(fields=['average_rating']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.vehicle_type} ({self.vehicle_registration})"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def completion_rate(self):
        if self.total_deliveries == 0:
            return 0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    @property
    def is_online(self):
        return self.status == 'active' and self.is_available


class RiderAvailability(TimeStampedModel):
    """Rider availability schedule"""
    
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='availability_schedule'
    )
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'riders_availability'
        unique_together = ['rider', 'day']
    
    def __str__(self):
        if not self.is_available:
            return f"{self.rider.user.get_full_name()} - {self.day.title()}: Unavailable"
        return f"{self.rider.user.get_full_name()} - {self.day.title()}: {self.start_time} - {self.end_time}"


class RiderBankAccount(TimeStampedModel):
    """Bank account information for riders (for payments)"""
    
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    
    # Bank Information
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    branch = models.CharField(max_length=100, blank=True)
    
    # Mobile Money
    mpesa_number = models.CharField(max_length=17, blank=True)
    mpesa_name = models.CharField(max_length=100, blank=True)
    
    # Status
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'riders_bank_account'
        indexes = [
            models.Index(fields=['rider', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.rider.user.get_full_name()} - {self.bank_name} ({self.account_number})"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary account per rider
        if self.is_primary:
            RiderBankAccount.objects.filter(rider=self.rider, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class Delivery(TimeStampedModel):
    """Delivery records for tracking rider assignments"""
    
    DELIVERY_STATUS = [
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('picking_up', 'Picking Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='delivery'
    )
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    
    # Status and Timing
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery Details
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Distance and Time
    estimated_distance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_distance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_duration = models.IntegerField(null=True, blank=True, help_text="Estimated duration in minutes")
    actual_duration = models.IntegerField(null=True, blank=True, help_text="Actual duration in minutes")
    
    # Earnings
    base_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    distance_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    time_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Verification
    pickup_verification_code = models.CharField(max_length=6, blank=True)
    delivery_verification_code = models.CharField(max_length=6, blank=True)
    customer_signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    
    # Notes
    pickup_notes = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'riders_delivery'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['rider', 'status']),
            models.Index(fields=['status', 'assigned_at']),
        ]
    
    def __str__(self):
        return f"Delivery {self.order.order_number} - {self.rider.user.get_full_name()} ({self.status})"
    
    @property
    def is_active(self):
        return self.status in ['assigned', 'accepted', 'picking_up', 'in_transit']


class RiderEarnings(TimeStampedModel):
    """Track rider earnings and payments"""
    
    EARNING_TYPES = [
        ('delivery', 'Delivery Fee'),
        ('bonus', 'Performance Bonus'),
        ('incentive', 'Daily/Weekly Incentive'),
        ('tip', 'Customer Tip'),
        ('adjustment', 'Manual Adjustment'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='earnings',
        null=True, blank=True
    )
    
    # Earning Details
    earning_type = models.CharField(max_length=20, choices=EARNING_TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    
    # Payment Information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Period (for grouping payments)
    earning_date = models.DateField()
    payment_period = models.CharField(max_length=20, blank=True, help_text="e.g., 2024-W01, 2024-01")
    
    class Meta:
        db_table = 'riders_earnings'
        ordering = ['-earning_date', '-created_at']
        indexes = [
            models.Index(fields=['rider', 'payment_status']),
            models.Index(fields=['earning_date']),
            models.Index(fields=['payment_period']),
        ]
    
    def __str__(self):
        return f"{self.rider.user.get_full_name()} - {self.earning_type}: KES {self.amount}"


class RiderLocation(TimeStampedModel):
    """Track rider location history for analytics and safety"""
    
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='location_history'
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    speed = models.FloatField(null=True, blank=True, help_text="Speed in km/h")
    
    # Context
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='location_updates',
        null=True, blank=True
    )
    is_during_delivery = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'riders_location'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rider', 'created_at']),
            models.Index(fields=['delivery', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.rider.user.get_full_name()} - {self.created_at}"


class RiderIncentive(TimeStampedModel):
    """Incentive programs for riders"""
    
    INCENTIVE_TYPES = [
        ('daily_target', 'Daily Delivery Target'),
        ('weekly_target', 'Weekly Delivery Target'),
        ('rating_bonus', 'High Rating Bonus'),
        ('peak_hours', 'Peak Hours Bonus'),
        ('distance_bonus', 'Long Distance Bonus'),
        ('new_rider', 'New Rider Bonus'),
    ]
    
    PERIOD_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('one_time', 'One Time'),
    ]
    
    # Incentive Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    incentive_type = models.CharField(max_length=20, choices=INCENTIVE_TYPES)
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    
    # Conditions
    minimum_deliveries = models.IntegerField(default=0)
    minimum_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    minimum_distance = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    target_areas = models.TextField(blank=True, help_text="Specific areas for incentive")
    
    # Reward
    reward_amount = models.DecimalField(max_digits=8, decimal_places=2)
    is_percentage = models.BooleanField(default=False, help_text="If true, reward_amount is percentage of earnings")
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Applicable Riders
    applicable_to_all = models.BooleanField(default=True)
    specific_riders = models.ManyToManyField(
        RiderProfile,
        blank=True,
        related_name='specific_incentives'
    )
    
    class Meta:
        db_table = 'riders_incentive'
        indexes = [
            models.Index(fields=['incentive_type', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - KES {self.reward_amount}"


class RiderPerformance(TimeStampedModel):
    """Daily/weekly performance tracking for riders"""
    
    PERIOD_TYPES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    rider = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='performance_records'
    )
    
    # Period Information
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Performance Metrics
    total_orders_assigned = models.IntegerField(default=0)
    total_orders_accepted = models.IntegerField(default=0)
    total_orders_completed = models.IntegerField(default=0)
    total_orders_failed = models.IntegerField(default=0)
    
    # Time Metrics
    total_online_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    total_delivery_time = models.IntegerField(default=0, help_text="Total delivery time in minutes")
    average_delivery_time = models.IntegerField(default=0, help_text="Average delivery time in minutes")
    
    # Distance and Earnings
    total_distance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Ratings
    total_ratings_received = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    class Meta:
        db_table = 'riders_performance'
        unique_together = ['rider', 'period_type', 'period_start']
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['rider', 'period_type']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.rider.user.get_full_name()} - {self.period_type} ({self.period_start})"
    
    @property
    def acceptance_rate(self):
        if self.total_orders_assigned == 0:
            return 0
        return (self.total_orders_accepted / self.total_orders_assigned) * 100
    
    @property
    def completion_rate(self):
        if self.total_orders_accepted == 0:
            return 0
        return (self.total_orders_completed / self.total_orders_accepted) * 100