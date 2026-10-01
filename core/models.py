from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('organiser', 'Organiser'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    department = models.CharField(max_length=100, blank=True, null=True)
    faculty = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    password_reset_otp = models.CharField(max_length=64, blank=True, null=True)
    password_reset_otp_expires = models.DateTimeField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
    )

class Interest(models.Model):
    CATEGORY_CHOICES = (
        ('academic', 'Academic'),
        ('cultural', 'Cultural'),
        ('sports', 'Sports'),
        ('social', 'Social'),
        ('technology', 'Technology'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interests')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('academic',   'Academic'),
        ('cultural',   'Cultural'),
        ('sports',     'Sports'),
        ('social',     'Social'),
        ('technology', 'Technology'),
    ]
    EVENT_TYPE_CHOICES = [
        ('free', 'Free'),
        ('paid', 'Paid'),
    ]
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    ]
    organiser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_organised')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date_time = models.DateTimeField()
    venue = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField()
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES, default='free')
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    target_faculty = models.CharField(max_length=100, blank=True, null=True)
    target_department = models.CharField(max_length=100, blank=True, null=True)

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    qr_code_hash = models.CharField(max_length=100, unique=True)
    ticket_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    issued_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True, blank=True)

class Payment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    paystack_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)

class Notification(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('24h', '24-Hour Reminder'),
        ('2h', '2-Hour Reminder'),
        ('30m', '30-Minute Reminder'),
        ('announcement', 'Announcement'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications'
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    type = models.CharField(
        max_length=20,
        choices=[
            ('push', 'Push'),
            ('email', 'Email'),
            ('both', 'Both'),
        ]
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES,
        default='general',
    )
    message = models.TextField()
    scheduled_time = models.DateTimeField(
        null=True, blank=True
    )
    sent_at = models.DateTimeField(
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        default='sent',
    )

    class Meta:
        unique_together = [
            ['user', 'event', 'reminder_type']
        ]

    def __str__(self):
        return (
            f"{self.reminder_type} reminder "
            f"for {self.user.email} — "
            f"{self.event.title if self.event else 'N/A'}"
        )

class AdminLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_logs')
    action_type = models.CharField(max_length=100)
    target_id = models.IntegerField()
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
