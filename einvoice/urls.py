from django.urls import path
from . import views

app_name = 'einvoice'

urlpatterns = [
    path('', views.einvoice_list, name='list'),
    path('config/', views.einvoice_config, name='config'),
    path('document/<int:pk>/', views.einvoice_detail, name='detail'),
    path('document/<int:pk>/submit/', views.submit_einvoice, name='submit'),
    path('document/<int:pk>/status/', views.check_status, name='check_status'),
    path('document/<int:pk>/cancel/', views.cancel_einvoice, name='cancel'),
    path('document/<int:pk>/view-payload/', views.view_payload, name='view_payload'),
    path('create-from-invoice/<int:invoice_id>/', views.create_from_invoice, name='create_from_invoice'),
    path('create-from-claim/<int:claim_id>/', views.create_from_claim, name='create_from_claim'),
    path('validate-tin/', views.validate_tin, name='validate_tin'),
    path('authenticate/', views.test_authentication, name='authenticate'),
    path('logs/', views.einvoice_logs, name='logs'),
    path('batch-submit/', views.batch_submit, name='batch_submit'),
    path('sync-all-status/', views.sync_all_status, name='sync_all_status'),
]
