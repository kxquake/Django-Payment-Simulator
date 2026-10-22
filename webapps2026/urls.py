from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect


urlpatterns = [
    path('admin/', admin.site.urls),
    path('webapps2026/', include('register.urls')),
    path('webapps2026/', include('payapp.urls')),
    path('', lambda request: redirect('dashboard')),
]