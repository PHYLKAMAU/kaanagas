# riders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.RiderProfileViewSet, basename='riderprofile')
router.register(r'availability', views.RiderAvailabilityViewSet, basename='rideravailability')
router.register(r'bank-accounts', views.RiderBankAccountViewSet, basename='riderbankaccount')
router.register(r'deliveries', views.DeliveryViewSet, basename='delivery')
router.register(r'earnings', views.RiderEarningsViewSet, basename='riderearnings')
router.register(r'performance', views.RiderPerformanceViewSet, basename='riderperformance')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.RiderDashboardView.as_view(), name='rider_dashboard'),
    path('available-jobs/', views.AvailableJobsView.as_view(), name='available_jobs'),
    path('update-location/', views.UpdateLocationView.as_view(), name='update_location'),
    path('accept-delivery/', views.AcceptDeliveryView.as_view(), name='accept_delivery'),
    path('update-delivery-status/', views.UpdateDeliveryStatusView.as_view(), name='update_delivery_status'),
]