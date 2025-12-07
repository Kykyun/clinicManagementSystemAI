from django.db import models
from django.conf import settings


class AILog(models.Model):
    ACTION_CHOICES = [
        ('triage', 'Triage Classification'),
        ('consultation_notes', 'Consultation Notes'),
        ('medical_summary', 'Medical History Summary'),
        ('referral_letter', 'Referral Letter'),
        ('quarantine_slip', 'Quarantine Slip'),
        ('stock_suggestion', 'Stock Order Suggestion'),
        ('dashboard_insight', 'Dashboard Insight'),
        ('revenue_forecast', 'Revenue Forecast'),
        ('anomaly_detection', 'Anomaly Detection'),
        ('assistant', 'AI Assistant'),
        ('nl_query', 'Natural Language Query'),
        ('lab_extraction', 'Lab Result Extraction'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('rate_limited', 'Rate Limited'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    input_summary = models.TextField(help_text='Truncated/anonymized input for traceability')
    output_summary = models.TextField(blank=True, help_text='Truncated output for traceability')
    tokens_used = models.IntegerField(default=0)
    response_time_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI Log'
        verbose_name_plural = 'AI Logs'
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AIConfig(models.Model):
    is_enabled = models.BooleanField(default=True, help_text='Master switch for AI features')
    model_name = models.CharField(max_length=50, default='gpt-4o-mini', help_text='OpenAI model to use')
    max_tokens = models.IntegerField(default=2000)
    temperature = models.DecimalField(max_digits=2, decimal_places=1, default=0.7)
    
    triage_enabled = models.BooleanField(default=True)
    consultation_notes_enabled = models.BooleanField(default=True)
    medical_summary_enabled = models.BooleanField(default=True)
    referral_letter_enabled = models.BooleanField(default=True)
    stock_suggestion_enabled = models.BooleanField(default=True)
    dashboard_insights_enabled = models.BooleanField(default=True)
    revenue_forecast_enabled = models.BooleanField(default=True)
    anomaly_detection_enabled = models.BooleanField(default=True)
    assistant_enabled = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'AI Configuration'
        verbose_name_plural = 'AI Configuration'
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        config, created = cls.objects.get_or_create(pk=1)
        return config
