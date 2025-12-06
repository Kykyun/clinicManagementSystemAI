from django.urls import path
from . import views

app_name = 'setup_app'

urlpatterns = [
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/create/', views.medicine_create, name='medicine_create'),
    path('medicines/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    
    path('lab-tests/', views.lab_test_list, name='lab_test_list'),
    path('lab-tests/create/', views.lab_test_create, name='lab_test_create'),
    path('lab-tests/<int:pk>/edit/', views.lab_test_edit, name='lab_test_edit'),
    
    path('allergies/', views.allergy_list, name='allergy_list'),
    path('allergies/create/', views.allergy_create, name='allergy_create'),
    
    path('disposables/', views.disposable_list, name='disposable_list'),
    path('disposables/create/', views.disposable_create, name='disposable_create'),
    path('disposables/<int:pk>/edit/', views.disposable_edit, name='disposable_edit'),
    
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.room_create, name='room_create'),
    
    path('fees/', views.fee_list, name='fee_list'),
    path('fees/create/', views.fee_create, name='fee_create'),
    path('fees/<int:pk>/edit/', views.fee_edit, name='fee_edit'),
    
    path('panels/', views.panel_list, name='panel_list'),
    path('panels/create/', views.panel_create, name='panel_create'),
    path('panels/<int:pk>/edit/', views.panel_edit, name='panel_edit'),
    
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
]
