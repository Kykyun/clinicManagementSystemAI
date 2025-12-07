from django.contrib import admin
from .models import AILog, AIConfig


@admin.register(AILog)
class AILogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'status', 'tokens_used', 'response_time_ms', 'created_at']
    list_filter = ['action', 'status', 'created_at']
    search_fields = ['user__username', 'input_summary', 'output_summary']
    readonly_fields = ['user', 'action', 'status', 'input_summary', 'output_summary', 
                       'tokens_used', 'response_time_ms', 'error_message', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = ['is_enabled', 'model_name', 'max_tokens', 'temperature', 'updated_at']
    fieldsets = (
        ('General Settings', {
            'fields': ('is_enabled', 'model_name', 'max_tokens', 'temperature')
        }),
        ('Feature Toggles', {
            'fields': (
                'triage_enabled', 
                'consultation_notes_enabled', 
                'medical_summary_enabled',
                'referral_letter_enabled', 
                'stock_suggestion_enabled',
                'dashboard_insights_enabled',
                'revenue_forecast_enabled',
                'anomaly_detection_enabled',
                'assistant_enabled',
            )
        }),
        ('Audit', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['updated_at', 'updated_by']
    
    def has_add_permission(self, request):
        return not AIConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
