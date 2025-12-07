from django.db import models
from django.conf import settings
from finance.models import Invoice, PanelClaim


class EInvoiceConfig(models.Model):
    client_id = models.CharField(max_length=200, blank=True, help_text="MyInvois Client ID")
    client_secret = models.CharField(max_length=200, blank=True, help_text="MyInvois Client Secret (encrypted)")
    taxpayer_tin = models.CharField(max_length=50, blank=True, help_text="Clinic's Tax Identification Number")
    environment = models.CharField(
        max_length=20,
        choices=[('sandbox', 'Sandbox'), ('production', 'Production')],
        default='sandbox'
    )
    is_active = models.BooleanField(default=False, help_text="Enable e-invoicing")
    clinic_name = models.CharField(max_length=200, blank=True)
    clinic_brn = models.CharField(max_length=50, blank=True, help_text="Business Registration Number")
    clinic_address_line1 = models.CharField(max_length=200, blank=True)
    clinic_address_line2 = models.CharField(max_length=200, blank=True)
    clinic_city = models.CharField(max_length=100, blank=True)
    clinic_state = models.CharField(max_length=100, blank=True)
    clinic_postcode = models.CharField(max_length=20, blank=True)
    clinic_country = models.CharField(max_length=5, default='MYS')
    clinic_phone = models.CharField(max_length=20, blank=True)
    clinic_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "E-Invoice Configuration"
        verbose_name_plural = "E-Invoice Configuration"

    def __str__(self):
        return f"E-Invoice Config ({self.environment})"

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class EInvoiceToken(models.Model):
    access_token = models.TextField()
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Token expires at {self.expires_at}"


class EInvoiceDocument(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
        ('debit_note', 'Debit Note'),
        ('refund_note', 'Refund Note'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='einvoice_documents', null=True, blank=True)
    panel_claim = models.ForeignKey(PanelClaim, on_delete=models.CASCADE, related_name='einvoice_documents', null=True, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='invoice')
    myinvois_uuid = models.CharField(max_length=100, blank=True, db_index=True, help_text="UUID returned by MyInvois")
    submission_uid = models.CharField(max_length=100, blank=True, help_text="Submission ID from MyInvois")
    long_id = models.CharField(max_length=200, blank=True, help_text="Long ID for document retrieval")
    internal_id = models.CharField(max_length=50, help_text="Internal document reference")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    environment = models.CharField(max_length=20, default='sandbox')
    payload_json = models.JSONField(null=True, blank=True, help_text="The JSON payload sent to MyInvois")
    response_json = models.JSONField(null=True, blank=True, help_text="Response from MyInvois")
    validation_errors = models.JSONField(null=True, blank=True, help_text="Validation errors if rejected")
    buyer_tin = models.CharField(max_length=50, blank=True, help_text="Buyer's TIN")
    buyer_name = models.CharField(max_length=200, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='MYR')
    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "E-Invoice Document"
        verbose_name_plural = "E-Invoice Documents"

    def __str__(self):
        return f"{self.internal_id} - {self.get_status_display()}"

    @property
    def is_submitted(self):
        return self.status in ['submitted', 'valid', 'invalid']

    @property
    def can_cancel(self):
        return self.status == 'valid'

    @property
    def can_resubmit(self):
        return self.status in ['pending', 'invalid', 'rejected']


class EInvoiceLog(models.Model):
    ACTION_CHOICES = [
        ('submit', 'Submit'),
        ('get_status', 'Get Status'),
        ('cancel', 'Cancel'),
        ('reject', 'Reject'),
        ('validate_tin', 'Validate TIN'),
        ('authenticate', 'Authenticate'),
    ]

    document = models.ForeignKey(EInvoiceDocument, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    is_success = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "E-Invoice Log"
        verbose_name_plural = "E-Invoice Logs"

    def __str__(self):
        return f"{self.action} - {self.created_at}"


class TINValidation(models.Model):
    tin = models.CharField(max_length=50, db_index=True)
    id_type = models.CharField(max_length=20, default='BRN', help_text="ID Type (BRN, NRIC, etc.)")
    id_value = models.CharField(max_length=50, blank=True)
    is_valid = models.BooleanField(default=False)
    taxpayer_name = models.CharField(max_length=200, blank=True)
    validation_response = models.JSONField(null=True, blank=True)
    validated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-validated_at']
        verbose_name = "TIN Validation"
        verbose_name_plural = "TIN Validations"

    def __str__(self):
        status = "Valid" if self.is_valid else "Invalid"
        return f"{self.tin} - {status}"
