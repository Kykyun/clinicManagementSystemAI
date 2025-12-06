from django.urls import path
from . import views

app_name = 'management_app'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    
    path('settings/', views.clinic_settings, name='clinic_settings'),
    
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/checkin/', views.attendance_checkin, name='attendance_checkin'),
    path('attendance/checkout/', views.attendance_checkout, name='attendance_checkout'),
    
    path('queue/', views.queue_display, name='queue_display'),
    path('queue/ticket/create/', views.queue_ticket_create, name='queue_ticket_create'),
    path('queue/call-next/', views.queue_call_next, name='queue_call_next'),
    
    path('reports/', views.reporting, name='reporting'),
    path('reports/export/csv/', views.export_report_csv, name='export_report_csv'),
    path('reports/export/pdf/', views.export_report_pdf, name='export_report_pdf'),
    
    path('promotions/', views.promotional_list, name='promotional_list'),
    path('promotions/create/', views.promotional_create, name='promotional_create'),
]
