from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('config/', views.ai_config, name='config'),
    path('logs/', views.ai_logs, name='logs'),
    
    path('api/triage/', views.api_triage, name='api_triage'),
    path('api/structure-notes/', views.api_structure_notes, name='api_structure_notes'),
    path('api/medical-summary/<int:patient_id>/', views.api_medical_summary, name='api_medical_summary'),
    path('api/referral-letter/', views.api_referral_letter, name='api_referral_letter'),
    path('api/stock-suggestions/', views.api_stock_suggestions, name='api_stock_suggestions'),
    path('api/dashboard-insights/', views.api_dashboard_insights, name='api_dashboard_insights'),
    path('api/assistant/', views.api_assistant, name='api_assistant'),
    path('api/revenue-forecast/', views.api_revenue_forecast, name='api_revenue_forecast'),
    path('api/anomaly-detection/', views.api_anomaly_detection, name='api_anomaly_detection'),
]
