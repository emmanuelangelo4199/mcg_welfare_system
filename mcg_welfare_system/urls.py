from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('attendance/', include('attendance.urls')),
    path('classes/', include('classes.urls')),
    path('communications/', include('communications.urls')),
    path('core/', include('core.urls')),
    path('finance/', include('finance.urls')),
    path('meetings/', include('meetings.urls')),
    path('members/', include('members.urls')),
    path('notifications/', include('notifications.urls')),
    path('organisations/', include('organisations.urls')),
    path('reports/', include('reports.urls')),
    path('services/', include('services.urls')),
    path('welfare-cases/', include('welfare_cases.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)