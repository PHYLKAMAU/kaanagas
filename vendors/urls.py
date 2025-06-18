# vendors/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.VendorProfileViewSet, basename='vendorprofile')
router.register(r'inventory', views.VendorInventoryViewSet, basename='vendorinventory')
router.register(r'hours', views.VendorHoursViewSet, basename='vendorhours')
router.register(r'bank-accounts', views.VendorBankAccountViewSet, basename='vendorbankaccount')
router.register(r'promotions', views.VendorPromotionViewSet, basename='vendorpromotion')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('analytics/', views.VendorAnalyticsView.as_view(), name='vendor_analytics'),
    path('orders/', views.VendorOrdersView.as_view(), name='vendor_orders'),
    path('search/', views.VendorSearchView.as_view(), name='vendor_search'),
]