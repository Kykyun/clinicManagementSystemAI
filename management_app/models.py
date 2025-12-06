from django.db import models
from django.conf import settings


class ClinicSettings(models.Model):
    clinic_name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='clinic/', blank=True, null=True)
    tax_registration = models.CharField(max_length=50, blank=True)
    operating_hours = models.TextField(blank=True)
    invoice_prefix = models.CharField(max_length=10, default='INV')
    invoice_terms = models.TextField(blank=True)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='USD')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Clinic Settings'
        verbose_name_plural = 'Clinic Settings'

    def __str__(self):
        return self.clinic_name


class Attendance(models.Model):
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'On Leave'),
    ], default='present')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['staff', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.staff.username} - {self.date}"

    @property
    def hours_worked(self):
        if self.check_in and self.check_out:
            from datetime import datetime, timedelta
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            return (check_out_dt - check_in_dt).seconds / 3600
        return 0


class QueueTicket(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('in_service', 'In Service'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
    
    ticket_number = models.IntegerField()
    patient_name = models.CharField(max_length=200)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    room = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['date', 'ticket_number']
        unique_together = ['ticket_number', 'date']

    def __str__(self):
        return f"#{self.ticket_number} - {self.patient_name}"


class PromotionalProduct(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    promotional_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='promotions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        from datetime import date
        return self.start_date <= date.today() <= self.end_date


class MembershipReward(models.Model):
    patient = models.OneToOneField('patients.Patient', on_delete=models.CASCADE, related_name='membership')
    points_balance = models.IntegerField(default=0)
    membership_tier = models.CharField(max_length=20, choices=[
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], default='bronze')
    joined_date = models.DateField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.full_name} - {self.points_balance} points"


class RewardTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('earn', 'Earned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
        ('adjust', 'Adjustment'),
    ]
    
    membership = models.ForeignKey(MembershipReward, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    points = models.IntegerField()
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.membership.patient.full_name} - {self.transaction_type} {self.points}"
