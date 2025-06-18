# kaanagas_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints - TEMPORARILY COMMENTED OUT FOR MIGRATIONS
    # Uncomment these after migrations are successful
    path('api/accounts/', include('accounts.urls')),
    path('api/customers/', include('customers.urls')),
    path('api/vendors/', include('vendors.urls')),
    # path('api/riders/', include('riders.urls')),
    # path('api/orders/', include('orders.urls')),
    # path('api/core/', include('core.urls')),
    # path('api/chatbot/', include('chatbot.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    