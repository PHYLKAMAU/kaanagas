# orders/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.conf import settings
import requests
import json

from .models import Order, OrderItem, OrderTracking, Payment, OrderPromotion
from .serializers import (
    OrderSerializer, OrderItemSerializer, OrderTrackingSerializer,
    PaymentSerializer, OrderPromotionSerializer, OrderCreateSerializer,
    OrderListSerializer, OrderUpdateSerializer, OrderEstimateSerializer,
    OrderRatingSerializer
)

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing orders"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return Order.objects.all()
        elif user.is_customer:
            return Order.objects.filter(customer=user)
        elif user.is_vendor:
            return Order.objects.filter(vendor__user=user)
        elif user.is_rider:
            return Order.objects.filter(rider=user)
        return Order.objects.none()
    
    def perform_create(self, serializer):
        """Create order with customer and initial tracking"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can create orders")
        order = serializer.save()
        
        # Create initial tracking entry
        OrderTracking.objects.create(
            order=order,
            status='pending',
            notes='Order created successfully',
            updated_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm order (vendor only)"""
        order = self.get_object()
        
        if not request.user.is_vendor or order.vendor.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'pending':
            return Response(
                {'error': 'Order cannot be confirmed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        estimated_time = request.data.get('estimated_time', 30)  # minutes
        
        order.status = 'confirmed'
        order.estimated_delivery_time = timezone.now() + timezone.timedelta(minutes=estimated_time)
        order.save()
        
        # Create tracking entry
        OrderTracking.objects.create(
            order=order,
            status='confirmed',
            notes=f'Order confirmed. Estimated delivery time: {estimated_time} minutes',
            updated_by=request.user
        )
        
        return Response({'message': 'Order confirmed successfully'})
    
    @action(detail=True, methods=['post'])
    def prepare(self, request, pk=None):
        """Mark order as preparing (vendor only)"""
        order = self.get_object()
        
        if not request.user.is_vendor or order.vendor.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        order.status = 'preparing'
        order.save()
        
        OrderTracking.objects.create(
            order=order,
            status='preparing',
            notes='Order is being prepared',
            updated_by=request.user
        )
        
        return Response({'message': 'Order marked as preparing'})
    
    @action(detail=True, methods=['post'])
    def ready_for_pickup(self, request, pk=None):
        """Mark order as ready for pickup (vendor only)"""
        order = self.get_object()
        
        if not request.user.is_vendor or order.vendor.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        order.status = 'ready_for_pickup'
        order.save()
        
        OrderTracking.objects.create(
            order=order,
            status='ready_for_pickup',
            notes='Order is ready for pickup',
            updated_by=request.user
        )
        
        return Response({'message': 'Order marked as ready for pickup'})
    
    @action(detail=True, methods=['post'])
    def assign_rider(self, request, pk=None):
        """Assign rider to order (vendor only)"""
        order = self.get_object()
        
        if not request.user.is_vendor or order.vendor.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rider_id = request.data.get('rider_id')
        if not rider_id:
            return Response(
                {'error': 'Rider ID required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            rider = User.objects.get(id=rider_id, role='rider')
            order.rider = rider
            order.status = 'out_for_delivery'
            order.save()
            
            # Create delivery record
            from riders.models import Delivery
            Delivery.objects.create(
                order=order,
                rider=rider.rider_profile,
                status='assigned'
            )
            
            OrderTracking.objects.create(
                order=order,
                status='out_for_delivery',
                notes=f'Order assigned to rider {rider.get_full_name()}',
                updated_by=request.user
            )
            
            return Response({'message': 'Rider assigned successfully'})
            
        except User.DoesNotExist:
            return Response({'error': 'Rider not found'}, status=404)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order"""
        order = self.get_object()
        
        # Check permissions
        if not (order.customer == request.user or 
                (request.user.is_vendor and order.vendor.user == request.user) or
                request.user.is_admin_user):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status in ['delivered', 'cancelled']:
            return Response(
                {'error': 'Order cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'No reason provided')
        
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.save()
        
        OrderTracking.objects.create(
            order=order,
            status='cancelled',
            notes=f'Order cancelled. Reason: {reason}',
            updated_by=request.user
        )
        
        return Response({'message': 'Order cancelled successfully'})


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing order items"""
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user permissions"""
        user = self.request.user
        if user.is_admin_user:
            return OrderItem.objects.all()
        elif user.is_customer:
            return OrderItem.objects.filter(order__customer=user)
        elif user.is_vendor:
            return OrderItem.objects.filter(order__vendor__user=user)
        elif user.is_rider:
            return OrderItem.objects.filter(order__rider=user)
        return OrderItem.objects.none()


class OrderTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing order tracking"""
    serializer_class = OrderTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user permissions"""
        user = self.request.user
        if user.is_admin_user:
            return OrderTracking.objects.all()
        elif user.is_customer:
            return OrderTracking.objects.filter(order__customer=user)
        elif user.is_vendor:
            return OrderTracking.objects.filter(order__vendor__user=user)
        elif user.is_rider:
            return OrderTracking.objects.filter(order__rider=user)
        return OrderTracking.objects.none()


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing payments"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user permissions"""
        user = self.request.user
        if user.is_admin_user:
            return Payment.objects.all()
        elif user.is_customer:
            return Payment.objects.filter(order__customer=user)
        elif user.is_vendor:
            return Payment.objects.filter(order__vendor__user=user)
        return Payment.objects.none()


class CreateOrderView(APIView):
    """Create a new order"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can create orders'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            
            # Return full order details
            response_serializer = OrderSerializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderEstimateView(APIView):
    """Get order estimate"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = OrderEstimateSerializer(data=request.data)
        if serializer.is_valid():
            vendor = serializer.validated_data['vendor_obj']
            items = serializer.validated_data['items']
            delivery_lat = serializer.validated_data['delivery_latitude']
            delivery_lng = serializer.validated_data['delivery_longitude']
            
            # Calculate subtotal
            subtotal = 0
            estimated_items = []
            
            for item_data in items:
                gas_product = item_data['gas_product']
                quantity = item_data['quantity']
                
                # Get price from vendor inventory
                try:
                    from vendors.models import VendorInventory
                    inventory = VendorInventory.objects.get(
                        vendor=vendor,
                        gas_product=gas_product
                    )
                    unit_price = inventory.refill_price if item_data.get('is_refill') else inventory.selling_price
                    in_stock = inventory.available_stock >= quantity
                except VendorInventory.DoesNotExist:
                    unit_price = gas_product.refill_price if item_data.get('is_refill') else gas_product.base_price
                    in_stock = False
                
                total_price = quantity * unit_price
                subtotal += total_price
                
                estimated_items.append({
                    'product_name': gas_product.name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price,
                    'in_stock': in_stock
                })
            
            # Calculate delivery fee and distance
            from geopy.distance import geodesic
            
            if vendor.latitude and vendor.longitude:
                vendor_location = (float(vendor.latitude), float(vendor.longitude))
                delivery_location = (float(delivery_lat), float(delivery_lng))
                distance = geodesic(vendor_location, delivery_location).kilometers
                
                if distance <= vendor.delivery_radius:
                    delivery_fee = vendor.delivery_fee
                    can_deliver = True
                else:
                    delivery_fee = vendor.delivery_fee
                    can_deliver = False
            else:
                distance = 0
                delivery_fee = vendor.delivery_fee
                can_deliver = True
            
            total_amount = subtotal + delivery_fee
            
            estimate = {
                'vendor': {
                    'id': vendor.id,
                    'name': vendor.business_name,
                    'delivery_radius': vendor.delivery_radius,
                    'minimum_order_amount': vendor.minimum_order_amount
                },
                'items': estimated_items,
                'subtotal': subtotal,
                'delivery_fee': delivery_fee,
                'total_amount': total_amount,
                'distance_km': round(distance, 2),
                'can_deliver': can_deliver,
                'meets_minimum': subtotal >= vendor.minimum_order_amount,
                'estimated_delivery_time': 60  # minutes
            }
            
            return Response(estimate)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TrackOrderView(APIView):
    """Track order by order number"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
            
            # Check if user has permission to view this order
            if not (order.customer == request.user or 
                   (request.user.is_vendor and order.vendor.user == request.user) or
                   (request.user.is_rider and order.rider == request.user) or
                   request.user.is_admin_user):
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
            
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)


class CancelOrderView(APIView):
    """Cancel an order"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        order_id = request.data.get('order_id')
        reason = request.data.get('reason', 'Customer requested cancellation')
        
        if not order_id:
            return Response(
                {'error': 'Order ID required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=order_id)
            
            # Check permissions
            if not (order.customer == request.user or 
                   (request.user.is_vendor and order.vendor.user == request.user) or
                   request.user.is_admin_user):
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if order.status in ['delivered', 'cancelled']:
                return Response(
                    {'error': 'Order cannot be cancelled'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            order.status = 'cancelled'
            order.cancellation_reason = reason
            order.save()
            
            # Create tracking entry
            OrderTracking.objects.create(
                order=order,
                status='cancelled',
                notes=f'Order cancelled. Reason: {reason}',
                updated_by=request.user
            )
            
            return Response({'message': 'Order cancelled successfully'})
            
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)


class RateOrderView(APIView):
    """Rate an order (vendor and rider)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can rate orders'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = OrderRatingSerializer(data=request.data)
        if serializer.is_valid():
            order_id = serializer.validated_data['order']
            
            try:
                order = Order.objects.get(id=order_id, customer=request.user)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=404)
            
            if order.status != 'delivered':
                return Response(
                    {'error': 'Can only rate delivered orders'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from core.models import Rating
            
            # Rate vendor if provided
            vendor_rating = serializer.validated_data.get('vendor_rating')
            vendor_review = serializer.validated_data.get('vendor_review', '')
            
            if vendor_rating:
                Rating.objects.update_or_create(
                    customer=request.user,
                    vendor=order.vendor.user,
                    order=order,
                    defaults={
                        'rating_type': 'vendor',
                        'rating': vendor_rating,
                        'review': vendor_review
                    }
                )
            
            # Rate rider if provided and order has rider
            rider_rating = serializer.validated_data.get('rider_rating')
            rider_review = serializer.validated_data.get('rider_review', '')
            
            if rider_rating and order.rider:
                Rating.objects.update_or_create(
                    customer=request.user,
                    rider=order.rider,
                    order=order,
                    defaults={
                        'rating_type': 'rider',
                        'rating': rider_rating,
                        'review': rider_review
                    }
                )
            
            return Response({'message': 'Order rated successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MpesaCallbackView(APIView):
    """M-Pesa payment callback"""
    permission_classes = []  # Allow unauthenticated access for callbacks
    
    def post(self, request):
        """Handle M-Pesa payment callback"""
        try:
            callback_data = request.data
            
            # Extract relevant information from callback
            checkout_request_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
            result_code = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            result_desc = callback_data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
            
            if not checkout_request_id:
                return Response({'error': 'Invalid callback data'}, status=400)
            
            # Find the payment record
            try:
                payment = Payment.objects.get(external_reference=checkout_request_id)
            except Payment.DoesNotExist:
                return Response({'error': 'Payment not found'}, status=404)
            
            # Update payment status based on result
            if result_code == 0:  # Success
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                
                # Update order payment status
                payment.order.payment_status = 'paid'
                payment.order.save()
                
                # Create tracking entry
                OrderTracking.objects.create(
                    order=payment.order,
                    status=payment.order.status,
                    notes='Payment completed successfully via M-Pesa',
                    updated_by=payment.order.customer
                )
                
            else:  # Failed
                payment.status = 'failed'
                payment.failure_reason = result_desc
                
                # Update order payment status
                payment.order.payment_status = 'failed'
                payment.order.save()
            
            # Store the full callback response
            payment.gateway_response = callback_data
            payment.save()
            
            return Response({'message': 'Callback processed successfully'})
            
        except Exception as e:
            # Log the error in production
            return Response({'error': 'Callback processing failed'}, status=500)


class InitiatePaymentView(APIView):
    """Initiate M-Pesa payment"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can initiate payments'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_id = request.data.get('order_id')
        phone_number = request.data.get('phone_number')
        
        if not order_id or not phone_number:
            return Response(
                {'error': 'Order ID and phone number required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)
        
        if order.payment_status == 'paid':
            return Response({'error': 'Order already paid'}, status=400)
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method='mpesa',
            phone_number=phone_number,
            status='pending'
        )
        
        # In a real implementation, you would integrate with M-Pesa STK Push API
        # For now, we'll simulate the process
        
        # Simulate M-Pesa API call
        mpesa_response = {
            'CheckoutRequestID': f'ws_CO_{payment.payment_id}',
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': 'Success. Request accepted for processing'
        }
        
        if mpesa_response.get('ResponseCode') == '0':
            payment.external_reference = mpesa_response['CheckoutRequestID']
            payment.status = 'processing'
            payment.gateway_response = mpesa_response
            payment.save()
            
            return Response({
                'message': 'Payment initiated successfully',
                'checkout_request_id': mpesa_response['CheckoutRequestID'],
                'customer_message': mpesa_response['CustomerMessage']
            })
        else:
            payment.status = 'failed'
            payment.failure_reason = mpesa_response.get('ResponseDescription', 'Unknown error')
            payment.gateway_response = mpesa_response
            payment.save()
            
            return Response({
                'error': 'Payment initiation failed',
                'reason': payment.failure_reason
            }, status=400)


class OrderStatsView(APIView):
    """Order statistics (admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Date range
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        
        orders = Order.objects.filter(created_at__date__gte=start_date)
        
        stats = {
            'total_orders': orders.count(),
            'completed_orders': orders.filter(status='delivered').count(),
            'pending_orders': orders.filter(
                status__in=['pending', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery']
            ).count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
            'total_revenue': orders.filter(
                status='delivered', 
                payment_status='paid'
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
            'average_order_value': orders.aggregate(
                avg=Avg('total_amount')
            )['avg'] or 0,
            'orders_by_status': list(orders.values('status').annotate(
                count=Count('id')
            )),
            'daily_orders': list(orders.values('created_at__date').annotate(
                count=Count('id'),
                revenue=Sum('total_amount')
            ).order_by('created_at__date'))
        }
        
        return Response(stats)