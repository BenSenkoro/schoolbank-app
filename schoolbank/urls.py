from django.contrib import admin
from django.urls import path, include  # ← include is now imported
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),  # dashboard sends logged-out users to login
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('dashboard.urls')),
    path('', include('banking.urls')),
    path('', include('loans.urls')),
    path('', include('reports.urls')),
    path('', include('backup.urls')),
]
