from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    # Patient management
    path('', views.patient_list, name='patient_list'),
    path('create/', views.patient_create, name='patient_create'),
    path('<int:pk>/', views.patient_detail, name='patient_detail'),
    path('<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('<int:pk>/history/', views.patient_history, name='patient_history'),
    
    # Visits
    path('visits/', views.visit_list, name='visit_list'),
    path('visits/create/', views.visit_create, name='visit_create'),
    path('visits/create/<int:patient_id>/', views.visit_create, name='visit_create_for_patient'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/complete/', views.complete_visit, name='complete_visit'),
    
    # Consultations
    path('consultation/create/<int:visit_id>/', views.consultation_create, name='consultation_create'),
    path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultation/<int:pk>/edit/', views.consultation_edit, name='consultation_edit'),
    path('consultation/<int:consultation_id>/complete/', views.complete_consultation, name='complete_consultation'),
    
    # Prescriptions
    path('prescription/add/<int:consultation_id>/', views.prescription_add, name='prescription_add'),
    path('consultation/<int:consultation_id>/add-prescriptions/', views.add_prescriptions_bulk, name='add_prescriptions_bulk'),
    
    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/status/<str:status>/', views.appointment_status, name='appointment_status'),
    path('appointments/calendar/', views.calendar_view, name='calendar_view'),
    path('appointments/calendar/events/', views.calendar_events, name='calendar_events'),
    
    # Reception Dashboard
    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    path('reception/search/', views.patient_search_api, name='patient_search_api'),
    path('reception/check-in/<int:patient_id>/', views.patient_check_in, name='patient_check_in'),
    path('reception/walk-in/', views.walk_in_registration, name='walk_in_registration'),
    
    # Nurse Dashboard
    path('nurse/', views.nurse_dashboard, name='nurse_dashboard'),
    path('nurse/triage/<int:visit_id>/', views.start_triage, name='start_triage'),
    path('nurse/triage/<int:visit_id>/edit/', views.edit_triage, name='edit_triage'),
    
    # Doctor Dashboard
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/start/<int:visit_id>/', views.start_consultation, name='start_consultation'),
    
    # Pharmacy Dashboard
    path('pharmacy/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('pharmacy/dispense/<int:visit_id>/', views.dispense_prescriptions, name='dispense_prescriptions'),
    
    # Queue Display
    path('queue/', views.queue_display, name='queue_display'),
]
