# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'gas-products', views.GasProductViewSet, basename='gasproduct')
router.register(r'ratings', views.RatingViewSet, basename='rating')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'system-settings', views.SystemSettingsViewSet, basename='systemsettings')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', views.SearchView.as_view(), name='search'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('maps/geocode/', views.GeocodeView.as_view(), name='geocode'),
    path('maps/directions/', views.DirectionsView.as_view(), name='directions'),
]