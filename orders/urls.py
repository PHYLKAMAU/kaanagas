# orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='orderitem')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'tracking', views.OrderTrackingViewSet, basename='ordertracking')

urlpatterns = [
    path('', include(router.urls)),
    path('create/', views.CreateOrderView.as_view(), name='create_order'),
    path('estimate/', views.OrderEstimateView.as_view(), name='order_estimate'),
    path('track/<str:order_number>/', views.TrackOrderView.as_view(), name='track_order'),
    path('cancel/', views.CancelOrderView.as_view(), name='cancel_order'),
    path('rate/', views.RateOrderView.as_view(), name='rate_order'),
    path('mpesa-callback/', views.MpesaCallbackView.as_view(), name='mpesa_callback'),
]