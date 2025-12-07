from django.contrib import admin
from .models import EInvoiceConfig, EInvoiceDocument, EInvoiceLog, EInvoiceToken, TINValidation


@admin.register(EInvoiceConfig)
class EInvoiceConfigAdmin(admin.ModelAdmin):
    list_display = ['environment', 'is_active', 'taxpayer_tin', 'updated_at']


@admin.register(EInvoiceDocument)
class EInvoiceDocumentAdmin(admin.ModelAdmin):
    list_display = ['internal_id', 'document_type', 'status', 'buyer_name', 'total_amount', 'created_at']
    list_filter = ['status', 'document_type', 'environment']
    search_fields = ['internal_id', 'myinvois_uuid', 'buyer_name', 'buyer_tin']
    readonly_fields = ['myinvois_uuid', 'submission_uid', 'payload_json', 'response_json']


@admin.register(EInvoiceLog)
class EInvoiceLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'document', 'is_success', 'status_code', 'created_at']
    list_filter = ['action', 'is_success']


@admin.register(TINValidation)
class TINValidationAdmin(admin.ModelAdmin):
    list_display = ['tin', 'id_type', 'is_valid', 'taxpayer_name', 'validated_at']
    list_filter = ['is_valid', 'id_type']
    search_fields = ['tin', 'taxpayer_name']
