from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

def root_view(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'curl' in user_agent or 'health' in user_agent or 'replit' in user_agent:
        return HttpResponse('OK', status=200, content_type='text/plain')
    accept = request.META.get('HTTP_ACCEPT', '')
    if 'text/html' not in accept and 'application/json' not in accept:
        return HttpResponse('OK', status=200, content_type='text/plain')
    return redirect('management_app:dashboard')

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('healthz', health_check, name='health_check_z'),
    path('admin/', admin.site.urls),
    path('', root_view, name='root'),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('finance/', include('finance.urls')),
    path('management/', include('management_app.urls')),
    path('setup/', include('setup_app.urls')),
    path('einvoice/', include('einvoice.urls')),
    path('ai/', include('ai.urls')),
    path('xray/', include('xray.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
