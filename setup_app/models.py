from django.db import models
from django.conf import settings


class Medicine(models.Model):
    FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    strength = models.CharField(max_length=50, blank=True)
    form = models.CharField(max_length=20, choices=FORM_CHOICES, default='tablet')
    pack_size = models.CharField(max_length=50, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock_quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.strength})" if self.strength else self.name

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.minimum_stock


class LabTest(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    normal_range = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Allergy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    severity_level = models.CharField(max_length=20, choices=[
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], default='mild')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Allergies'
        ordering = ['name']

    def __str__(self):
        return self.name


class Disposable(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=50, default='piece')
    stock_quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Room(models.Model):
    ROOM_TYPE_CHOICES = [
        ('consultation', 'Consultation Room'),
        ('operation', 'Operation Room'),
        ('lab', 'Laboratory'),
        ('xray', 'X-Ray Room'),
        ('waiting', 'Waiting Area'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.IntegerField(default=1)
    equipment_info = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"


class Fee(models.Model):
    FEE_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('procedure', 'Procedure'),
        ('lab', 'Laboratory'),
        ('xray', 'X-Ray'),
        ('injection', 'Injection'),
        ('dressing', 'Dressing'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.amount}"


class Panel(models.Model):
    company_name = models.CharField(max_length=200)
    panel_code = models.CharField(max_length=50, unique=True)
    tin = models.CharField(max_length=50, blank=True, help_text="Tax Identification Number for e-invoicing")
    brn = models.CharField(max_length=50, blank=True, help_text="Business Registration Number")
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    billing_terms = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} ({self.panel_code})"
