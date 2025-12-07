from django.db import models
from django.conf import settings
from patients.models import Patient, Visit
from setup_app.models import Panel, Medicine, Disposable


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True)
    panel = models.ForeignKey(Panel, on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    invoice_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-invoice_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.patient.full_name}"

    def update_balance(self):
        self.outstanding_balance = self.total_amount - self.amount_paid
        if self.outstanding_balance <= 0:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partial'
        self.save()


class InvoiceItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('lab', 'Laboratory'),
        ('procedure', 'Procedure'),
        ('disposable', 'Disposable'),
        ('other', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    description = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        subtotal = self.unit_price * self.quantity
        tax = subtotal * (self.tax_rate / 100)
        self.total = subtotal + tax - self.discount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('ewallet', 'E-Wallet'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
        ('insurance', 'Insurance'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment ${self.amount} for {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.amount_paid = sum(p.amount for p in self.invoice.payments.all())
        self.invoice.update_balance()


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    bank_details = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StockOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    actual_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"


class StockOrderItem(models.Model):
    order = models.ForeignKey(StockOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True)
    disposable = models.ForeignKey(Disposable, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class PanelClaim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    claim_number = models.CharField(max_length=20, unique=True)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name='claims')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='panel_claims')
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submission_date = models.DateField(null=True, blank=True)
    response_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.claim_number} - {self.panel.company_name}"


class EODReport(models.Model):
    report_date = models.DateField(unique=True)
    total_patients = models.IntegerField(default=0)
    total_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_card = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ewallet = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-report_date']

    def __str__(self):
        return f"EOD Report - {self.report_date}"
