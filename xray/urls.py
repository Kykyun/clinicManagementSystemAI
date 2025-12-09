from django.urls import path
from . import views

app_name = 'xray'

urlpatterns = [
    path('', views.xray_dashboard, name='dashboard'),
    path('new/', views.xray_new, name='new'),
    path('study/<int:pk>/', views.xray_detail, name='detail'),
    path('study/<int:pk>/upload-image/', views.upload_image, name='upload_image'),
    path('study/<int:pk>/upload-document/', views.upload_document, name='upload_document'),
    path('study/<int:pk>/analyze/', views.ai_analyze, name='ai_analyze'),
    path('study/<int:pk>/report/', views.create_report, name='create_report'),
    path('study/<int:pk>/verify/', views.verify_report, name='verify_report'),
]
