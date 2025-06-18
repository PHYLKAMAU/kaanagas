# customers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.CustomerProfileViewSet, basename='customerprofile')
router.register(r'addresses', views.CustomerAddressViewSet, basename='customeraddress')
router.register(r'cylinders', views.CustomerCylinderViewSet, basename='customercylinder')
router.register(r'payment-methods', views.CustomerPaymentMethodViewSet, basename='customerpaymentmethod')
router.register(r'favorites', views.CustomerFavoriteViewSet, basename='customerfavorite')
router.register(r'complaints', views.CustomerComplaintViewSet, basename='customercomplaint')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.CustomerDashboardView.as_view(), name='customer_dashboard'),
    path('order-history/', views.OrderHistoryView.as_view(), name='order_history'),
    path('nearby-vendors/', views.NearbyVendorsView.as_view(), name='nearby_vendors'),
]