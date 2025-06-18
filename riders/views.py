# riders/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from geopy.distance import geodesic

from .models import (
    RiderProfile, RiderAvailability, RiderBankAccount, Delivery,
    RiderEarnings, RiderLocation, RiderIncentive, RiderPerformance
)
from .serializers import (
    RiderProfileSerializer, RiderAvailabilitySerializer, RiderBankAccountSerializer,
    DeliverySerializer, RiderEarningsSerializer, RiderLocationSerializer,
    RiderIncentiveSerializer, RiderPerformanceSerializer, RiderDashboardSerializer,
    RiderListSerializer
)

class RiderProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing rider profiles"""
    serializer_class = RiderProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return RiderProfile.objects.all()
        elif user.is_rider:
            return RiderProfile.objects.filter(user=user)
        elif user.is_vendor:
            # Vendors can see available riders
            return RiderProfile.objects.filter(status='active', is_available=True)
        return RiderProfile.objects.none()
    
    def perform_create(self, serializer):
        """Only riders can create rider profiles"""
        if not self.request.user.is_rider:
            raise permissions.PermissionDenied("Only rider users can create rider profiles")
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify rider (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rider = self.get_object()
        rider.status = 'active'
        rider.verified_at = timezone.now()
        rider.verified_by = request.user
        rider.save()
        
        return Response({'message': 'Rider verified successfully'})
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend rider (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rider = self.get_object()
        rider.status = 'suspended'
        rider.is_available = False
        rider.save()
        
        return Response({'message': 'Rider suspended successfully'})
    
    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle rider availability"""
        rider = self.get_object()
        
        if rider.user != request.user and not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rider.is_available = not rider.is_available
        rider.save()
        
        status_text = 'available' if rider.is_available else 'unavailable'
        return Response({'message': f'Rider is now {status_text}'})


class RiderAvailabilityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing rider availability schedule"""
    serializer_class = RiderAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Riders can only manage their own availability"""
        user = self.request.user
        if user.is_admin_user:
            return RiderAvailability.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return RiderAvailability.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return RiderAvailability.objects.none()
        return RiderAvailability.objects.none()
    
    def perform_create(self, serializer):
        """Set rider from user profile"""
        if not self.request.user.is_rider:
            raise permissions.PermissionDenied("Only riders can manage availability")
        
        try:
            rider_profile = self.request.user.rider_profile
            serializer.save(rider=rider_profile)
        except RiderProfile.DoesNotExist:
            raise permissions.PermissionDenied("Rider profile not found")


class RiderBankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for managing rider bank accounts"""
    serializer_class = RiderBankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Riders can only see their own bank accounts"""
        user = self.request.user
        if user.is_admin_user:
            return RiderBankAccount.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return RiderBankAccount.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return RiderBankAccount.objects.none()
        return RiderBankAccount.objects.none()
    
    def perform_create(self, serializer):
        """Set rider from user profile"""
        if not self.request.user.is_rider:
            raise permissions.PermissionDenied("Only riders can manage bank accounts")
        
        try:
            rider_profile = self.request.user.rider_profile
            serializer.save(rider=rider_profile)
        except RiderProfile.DoesNotExist:
            raise permissions.PermissionDenied("Rider profile not found")
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set bank account as primary"""
        bank_account = self.get_object()
        
        # Remove primary from other accounts
        RiderBankAccount.objects.filter(
            rider=bank_account.rider,
            is_primary=True
        ).update(is_primary=False)
        
        # Set this as primary
        bank_account.is_primary = True
        bank_account.save()
        
        return Response({'message': 'Bank account set as primary'})


class DeliveryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing deliveries"""
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return Delivery.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return Delivery.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return Delivery.objects.none()
        elif user.is_vendor:
            return Delivery.objects.filter(order__vendor__user=user)
        elif user.is_customer:
            return Delivery.objects.filter(order__customer=user)
        return Delivery.objects.none()
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept delivery"""
        delivery = self.get_object()
        
        if not request.user.is_rider or delivery.rider.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if delivery.status != 'assigned':
            return Response(
                {'error': 'Delivery cannot be accepted'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        delivery.status = 'accepted'
        delivery.accepted_at = timezone.now()
        delivery.save()
        
        # Update order status
        delivery.order.status = 'out_for_delivery'
        delivery.order.save()
        
        return Response({'message': 'Delivery accepted successfully'})
    
    @action(detail=True, methods=['post'])
    def pickup(self, request, pk=None):
        """Mark as picked up"""
        delivery = self.get_object()
        
        if not request.user.is_rider or delivery.rider.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        delivery.status = 'in_transit'
        delivery.picked_up_at = timezone.now()
        delivery.pickup_notes = request.data.get('notes', '')
        delivery.save()
        
        return Response({'message': 'Order picked up successfully'})
    
    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        """Mark as delivered"""
        delivery = self.get_object()
        
        if not request.user.is_rider or delivery.rider.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        verification_code = request.data.get('verification_code')
        
        # In a real implementation, you would verify the code
        # For now, we'll assume it's correct
        
        delivery.status = 'delivered'
        delivery.delivered_at = timezone.now()
        delivery.delivery_notes = request.data.get('notes', '')
        delivery.save()
        
        # Update order status
        delivery.order.status = 'delivered'
        delivery.order.actual_delivery_time = timezone.now()
        delivery.order.save()
        
        # Calculate earnings
        base_fee = 100  # Base delivery fee
        distance_fee = delivery.actual_distance * 10 if delivery.actual_distance else 0
        total_earnings = base_fee + distance_fee
        
        delivery.base_fee = base_fee
        delivery.distance_fee = distance_fee
        delivery.total_earnings = total_earnings
        delivery.save()
        
        # Create earnings record
        RiderEarnings.objects.create(
            rider=delivery.rider,
            delivery=delivery,
            earning_type='delivery',
            amount=total_earnings,
            description=f'Delivery for order {delivery.order.order_number}',
            earning_date=timezone.now().date()
        )
        
        return Response({'message': 'Order delivered successfully'})
    
    @action(detail=True, methods=['post'])
    def report_issue(self, request, pk=None):
        """Report delivery issue"""
        delivery = self.get_object()
        
        if not request.user.is_rider or delivery.rider.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        issue_reason = request.data.get('reason', '')
        
        delivery.status = 'failed'
        delivery.failure_reason = issue_reason
        delivery.save()
        
        # Update order status
        delivery.order.status = 'cancelled'
        delivery.order.cancellation_reason = f'Delivery failed: {issue_reason}'
        delivery.order.save()
        
        return Response({'message': 'Issue reported successfully'})


class RiderEarningsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing rider earnings"""
    serializer_class = RiderEarningsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Riders can only see their own earnings"""
        user = self.request.user
        if user.is_admin_user:
            return RiderEarnings.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return RiderEarnings.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return RiderEarnings.objects.none()
        return RiderEarnings.objects.none()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get earnings summary"""
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can view earnings'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return Response({'error': 'Rider profile not found'}, status=404)
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        earnings = RiderEarnings.objects.filter(rider=rider_profile)
        
        summary = {
            'today': earnings.filter(earning_date=today).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'this_week': earnings.filter(earning_date__gte=week_start).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'this_month': earnings.filter(earning_date__gte=month_start).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'total': earnings.aggregate(total=Sum('amount'))['total'] or 0
        }
        
        return Response(summary)


class RiderLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for tracking rider location"""
    serializer_class = RiderLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return RiderLocation.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return RiderLocation.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return RiderLocation.objects.none()
        return RiderLocation.objects.none()
    
    def perform_create(self, serializer):
        """Set rider from user profile and update current location"""
        if not self.request.user.is_rider:
            raise permissions.PermissionDenied("Only riders can update location")
        
        try:
            rider_profile = self.request.user.rider_profile
            location = serializer.save(rider=rider_profile)
            
            # Update rider's current location
            rider_profile.current_latitude = location.latitude
            rider_profile.current_longitude = location.longitude
            rider_profile.last_location_update = timezone.now()
            rider_profile.save()
            
        except RiderProfile.DoesNotExist:
            raise permissions.PermissionDenied("Rider profile not found")


class RiderIncentiveViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing rider incentives (read-only for riders)"""
    serializer_class = RiderIncentiveSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Show active incentives"""
        if self.request.user.is_admin_user:
            return RiderIncentive.objects.all()
        
        # Show active incentives for all users
        return RiderIncentive.objects.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )


class RiderPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing rider performance"""
    serializer_class = RiderPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Riders can only see their own performance"""
        user = self.request.user
        if user.is_admin_user:
            return RiderPerformance.objects.all()
        elif user.is_rider:
            try:
                rider_profile = user.rider_profile
                return RiderPerformance.objects.filter(rider=rider_profile)
            except RiderProfile.DoesNotExist:
                return RiderPerformance.objects.none()
        return RiderPerformance.objects.none()


class RiderDashboardView(APIView):
    """Rider dashboard with key metrics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can access dashboard'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return Response({'error': 'Rider profile not found'}, status=404)
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Delivery statistics
        all_deliveries = Delivery.objects.filter(rider=rider_profile)
        pending_deliveries = all_deliveries.filter(status__in=['assigned', 'accepted', 'picking_up', 'in_transit'])
        completed_today = all_deliveries.filter(
            status='delivered',
            delivered_at__date=today
        )
        
        # Earnings statistics
        earnings = RiderEarnings.objects.filter(rider=rider_profile)
        
        dashboard_data = {
            'total_deliveries': all_deliveries.count(),
            'pending_deliveries': pending_deliveries.count(),
            'completed_today': completed_today.count(),
            'earnings_today': earnings.filter(earning_date=today).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'earnings_week': earnings.filter(earning_date__gte=week_start).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'earnings_month': earnings.filter(earning_date__gte=month_start).aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'average_rating': rider_profile.average_rating,
            'completion_rate': rider_profile.completion_rate,
            'online_hours_today': 8.0  # This would be calculated from location tracking
        }
        
        serializer = RiderDashboardSerializer(dashboard_data)
        return Response(serializer.data)


class AvailableJobsView(APIView):
    """View available delivery jobs for riders"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can view available jobs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return Response({'error': 'Rider profile not found'}, status=404)
        
        if not rider_profile.is_available:
            return Response({'message': 'Set yourself as available to see jobs'})
        
        # Get rider's current location
        rider_lat = rider_profile.current_latitude
        rider_lng = rider_profile.current_longitude
        
        if not rider_lat or not rider_lng:
            return Response({'error': 'Location not set. Please update your location.'})
        
        from orders.models import Order
        
        # Find orders that need riders
        available_orders = Order.objects.filter(
            status='ready_for_pickup',
            rider__isnull=True
        )
        
        job_list = []
        rider_location = (float(rider_lat), float(rider_lng))
        
        for order in available_orders:
            if order.vendor.latitude and order.vendor.longitude:
                vendor_location = (float(order.vendor.latitude), float(order.vendor.longitude))
                distance = geodesic(rider_location, vendor_location).kilometers
                
                # Only show jobs within rider's max delivery distance
                if distance <= rider_profile.max_delivery_distance:
                    job_data = {
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'vendor_name': order.vendor.business_name,
                        'vendor_address': order.vendor.business_address,
                        'delivery_address': order.delivery_address,
                        'total_amount': order.total_amount,
                        'estimated_fee': 100 + (distance * 10),  # Base + distance fee
                        'distance_km': round(distance, 2),
                        'items_count': order.items.count()
                    }
                    job_list.append(job_data)
        
        # Sort by distance
        job_list.sort(key=lambda x: x['distance_km'])
        return Response(job_list)


class UpdateLocationView(APIView):
    """Update rider location"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can update location'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return Response({'error': 'Rider profile not found'}, status=404)
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        accuracy = request.data.get('accuracy')
        speed = request.data.get('speed')
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create location record
        RiderLocation.objects.create(
            rider=rider_profile,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed
        )
        
        # Update rider's current location
        rider_profile.current_latitude = latitude
        rider_profile.current_longitude = longitude
        rider_profile.last_location_update = timezone.now()
        rider_profile.save()
        
        return Response({'message': 'Location updated successfully'})


class AcceptDeliveryView(APIView):
    """Accept a delivery job"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can accept deliveries'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return Response({'error': 'Rider profile not found'}, status=404)
        
        order_id = request.data.get('order_id')
        if not order_id:
            return Response(
                {'error': 'Order ID required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from orders.models import Order
        
        try:
            order = Order.objects.get(id=order_id, rider__isnull=True)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found or already assigned'}, status=404)
        
        # Assign rider to order
        order.rider = request.user
        order.save()
        
        # Create delivery record
        delivery = Delivery.objects.create(
            order=order,
            rider=rider_profile,
            status='assigned'
        )
        
        return Response({
            'message': 'Delivery accepted successfully',
            'delivery_id': delivery.id,
            'order_number': order.order_number
        })


class UpdateDeliveryStatusView(APIView):
    """Update delivery status"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_rider:
            return Response(
                {'error': 'Only riders can update delivery status'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        delivery_id = request.data.get('delivery_id')
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not delivery_id or not new_status:
            return Response(
                {'error': 'Delivery ID and status required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            delivery = Delivery.objects.get(
                id=delivery_id,
                rider__user=request.user
            )
        except Delivery.DoesNotExist:
            return Response({'error': 'Delivery not found'}, status=404)
        
        # Update delivery status
        delivery.status = new_status
        
        if new_status == 'picking_up':
            delivery.pickup_notes = notes
        elif new_status == 'delivered':
            delivery.delivered_at = timezone.now()
            delivery.delivery_notes = notes
            # Update order status
            delivery.order.status = 'delivered'
            delivery.order.actual_delivery_time = timezone.now()
            delivery.order.save()
        
        delivery.save()
        
        return Response({'message': f'Delivery status updated to {new_status}'})