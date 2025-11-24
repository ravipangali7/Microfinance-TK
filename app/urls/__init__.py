from django.urls import path, include

urlpatterns = [
    path('', include('app.urls.admin_urls')),
    path('api/', include('app.urls.api_urls')),
]
