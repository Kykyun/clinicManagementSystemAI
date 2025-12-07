from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('billing/', views.billing_dashboard, name='billing_dashboard'),
    path('billing/quick-invoice/<int:visit_id>/', views.quick_invoice_create, name='quick_invoice_create'),
    path('billing/complete/<int:visit_id>/', views.complete_billing, name='complete_billing'),
    
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/create/<int:visit_id>/', views.invoice_create, name='invoice_create_for_visit'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/items/', views.invoice_items, name='invoice_items'),
    path('invoices/<int:pk>/finalize/', views.invoice_finalize, name='invoice_finalize'),
    
    path('payments/create/<int:invoice_id>/', views.payment_create, name='payment_create'),
    path('credit-payments/', views.credit_payment_list, name='credit_payment_list'),
    
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    
    path('stock-orders/', views.stock_order_list, name='stock_order_list'),
    path('stock-orders/create/', views.stock_order_create, name='stock_order_create'),
    path('stock-orders/<int:pk>/items/', views.stock_order_items, name='stock_order_items'),
    path('stock-orders/<int:pk>/status/<str:status>/', views.stock_order_status, name='stock_order_status'),
    
    path('panel-claims/', views.panel_claim_list, name='panel_claim_list'),
    path('panel-claims/create/', views.panel_claim_create, name='panel_claim_create'),
    
    path('eod/', views.eod_report, name='eod_report'),
    path('eod/generate/', views.eod_generate, name='eod_generate'),
]
