from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('management_app:dashboard')),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('finance/', include('finance.urls')),
    path('management/', include('management_app.urls')),
    path('setup/', include('setup_app.urls')),
    path('einvoice/', include('einvoice.urls')),
    path('ai/', include('ai.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
