from django.contrib import admin
from .models import XrayStudy, XrayImage, XrayDocument, XrayAIAnalysis, XrayReport


class XrayImageInline(admin.TabularInline):
    model = XrayImage
    extra = 1


class XrayDocumentInline(admin.TabularInline):
    model = XrayDocument
    extra = 1


@admin.register(XrayStudy)
class XrayStudyAdmin(admin.ModelAdmin):
    list_display = ['patient', 'body_region', 'view_type', 'status', 'priority', 'study_date']
    list_filter = ['status', 'priority', 'body_region', 'study_date']
    search_fields = ['patient__name', 'clinical_indication']
    inlines = [XrayImageInline, XrayDocumentInline]


@admin.register(XrayAIAnalysis)
class XrayAIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['study', 'confidence_level', 'analyzed_at']
    list_filter = ['confidence_level', 'analyzed_at']


@admin.register(XrayReport)
class XrayReportAdmin(admin.ModelAdmin):
    list_display = ['study', 'reported_by', 'verified_by', 'reported_at']
    list_filter = ['reported_at', 'verified_at']
