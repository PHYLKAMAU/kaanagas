# customers/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    CustomerProfile, CustomerAddress, CustomerCylinder,
    CustomerPaymentMethod, CustomerFavorite, CustomerComplaint
)
from .serializers import (
    CustomerProfileSerializer, CustomerAddressSerializer, CustomerCylinderSerializer,
    CustomerPaymentMethodSerializer, CustomerFavoriteSerializer, CustomerComplaintSerializer,
    CustomerDashboardSerializer, CustomerAddressListSerializer
)

class CustomerProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer profiles"""
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerProfile.objects.all()
        elif user.is_customer:
            return CustomerProfile.objects.filter(user=user)
        return CustomerProfile.objects.none()
    
    def perform_create(self, serializer):
        """Only customers can create customer profiles"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customer users can create customer profiles")
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify customer (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = self.get_object()
        customer.is_verified = True
        customer.verification_date = timezone.now()
        customer.save()
        
        return Response({'message': 'Customer verified successfully'})
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block customer (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        customer.is_blocked = True
        customer.blocked_reason = reason
        customer.save()
        
        return Response({'message': 'Customer blocked successfully'})


class CustomerAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer addresses"""
    serializer_class = CustomerAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Customers can only see their own addresses"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerAddress.objects.all()
        elif user.is_customer:
            try:
                customer_profile = user.customer_profile
                return CustomerAddress.objects.filter(customer=customer_profile)
            except CustomerProfile.DoesNotExist:
                return CustomerAddress.objects.none()
        return CustomerAddress.objects.none()
    
    def perform_create(self, serializer):
        """Set customer from user profile"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can manage addresses")
        
        try:
            customer_profile = self.request.user.customer_profile
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise permissions.PermissionDenied("Customer profile not found")
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set address as default"""
        address = self.get_object()
        
        # Remove default from other addresses
        CustomerAddress.objects.filter(
            customer=address.customer,
            is_default=True
        ).update(is_default=False)
        
        # Set this as default
        address.is_default = True
        address.save()
        
        return Response({'message': 'Address set as default'})


class CustomerCylinderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer cylinders"""
    serializer_class = CustomerCylinderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Customers can only see their own cylinders"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerCylinder.objects.all()
        elif user.is_customer:
            try:
                customer_profile = user.customer_profile
                return CustomerCylinder.objects.filter(customer=customer_profile)
            except CustomerProfile.DoesNotExist:
                return CustomerCylinder.objects.none()
        return CustomerCylinder.objects.none()
    
    def perform_create(self, serializer):
        """Set customer from user profile"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can manage cylinders")
        
        try:
            customer_profile = self.request.user.customer_profile
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise permissions.PermissionDenied("Customer profile not found")
    
    @action(detail=False, methods=['get'])
    def needing_refill(self, request):
        """Get cylinders needing refill"""
        try:
            customer_profile = request.user.customer_profile
            cylinders = CustomerCylinder.objects.filter(
                customer=customer_profile,
                current_fill_level__lte=10,
                status='active'
            )
            serializer = self.get_serializer(cylinders, many=True)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)
    
    @action(detail=False, methods=['get'])
    def needing_inspection(self, request):
        """Get cylinders needing inspection"""
        try:
            customer_profile = request.user.customer_profile
            today = timezone.now().date()
            cylinders = CustomerCylinder.objects.filter(
                customer=customer_profile,
                next_inspection_due__lte=today,
                status='active'
            )
            serializer = self.get_serializer(cylinders, many=True)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)


class CustomerPaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer payment methods"""
    serializer_class = CustomerPaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Customers can only see their own payment methods"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerPaymentMethod.objects.all()
        elif user.is_customer:
            try:
                customer_profile = user.customer_profile
                return CustomerPaymentMethod.objects.filter(customer=customer_profile)
            except CustomerProfile.DoesNotExist:
                return CustomerPaymentMethod.objects.none()
        return CustomerPaymentMethod.objects.none()
    
    def perform_create(self, serializer):
        """Set customer from user profile"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can manage payment methods")
        
        try:
            customer_profile = self.request.user.customer_profile
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise permissions.PermissionDenied("Customer profile not found")
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default"""
        payment_method = self.get_object()
        
        # Remove default from other payment methods
        CustomerPaymentMethod.objects.filter(
            customer=payment_method.customer,
            is_default=True
        ).update(is_default=False)
        
        # Set this as default
        payment_method.is_default = True
        payment_method.save()
        
        return Response({'message': 'Payment method set as default'})


class CustomerFavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer favorites"""
    serializer_class = CustomerFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Customers can only see their own favorites"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerFavorite.objects.all()
        elif user.is_customer:
            try:
                customer_profile = user.customer_profile
                return CustomerFavorite.objects.filter(customer=customer_profile)
            except CustomerProfile.DoesNotExist:
                return CustomerFavorite.objects.none()
        return CustomerFavorite.objects.none()
    
    def perform_create(self, serializer):
        """Set customer from user profile"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can manage favorites")
        
        try:
            customer_profile = self.request.user.customer_profile
            serializer.save(customer=customer_profile)
        except CustomerProfile.DoesNotExist:
            raise permissions.PermissionDenied("Customer profile not found")
    
    @action(detail=False, methods=['get'])
    def vendors(self, request):
        """Get favorite vendors"""
        try:
            customer_profile = request.user.customer_profile
            favorites = CustomerFavorite.objects.filter(
                customer=customer_profile,
                favorite_type='vendor'
            )
            serializer = self.get_serializer(favorites, many=True)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """Get favorite products"""
        try:
            customer_profile = request.user.customer_profile
            favorites = CustomerFavorite.objects.filter(
                customer=customer_profile,
                favorite_type='product'
            )
            serializer = self.get_serializer(favorites, many=True)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)


class CustomerComplaintViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer complaints"""
    serializer_class = CustomerComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return CustomerComplaint.objects.all()
        elif user.is_customer:
            try:
                customer_profile = user.customer_profile
                return CustomerComplaint.objects.filter(customer=customer_profile)
            except CustomerProfile.DoesNotExist:
                return CustomerComplaint.objects.none()
        return CustomerComplaint.objects.none()
    
    def perform_create(self, serializer):
        """Set customer from user profile"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can create complaints")
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve complaint (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        complaint = self.get_object()
        resolution = request.data.get('resolution', '')
        
        complaint.status = 'resolved'
        complaint.resolved_at = timezone.now()
        complaint.resolution = resolution
        complaint.save()
        
        return Response({'message': 'Complaint resolved successfully'})
    
    @action(detail=True, methods=['post'])
    def rate_resolution(self, request, pk=None):
        """Rate complaint resolution"""
        complaint = self.get_object()
        
        if complaint.customer.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        rating = request.data.get('satisfaction_rating')
        feedback = request.data.get('satisfaction_feedback', '')
        
        if rating and 1 <= rating <= 5:
            complaint.satisfaction_rating = rating
            complaint.satisfaction_feedback = feedback
            complaint.save()
            return Response({'message': 'Resolution rated successfully'})
        
        return Response(
            {'error': 'Rating must be between 1 and 5'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class CustomerDashboardView(APIView):
    """Customer dashboard with key metrics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can access dashboard'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            customer_profile = request.user.customer_profile
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=404)
        
        from orders.models import Order
        
        # Order statistics
        all_orders = Order.objects.filter(customer=request.user)
        pending_orders = all_orders.filter(status__in=['pending', 'confirmed', 'preparing', 'out_for_delivery'])
        completed_orders = all_orders.filter(status='delivered')
        
        # Favorite vendors count
        favorite_vendors_count = CustomerFavorite.objects.filter(
            customer=customer_profile,
            favorite_type='vendor'
        ).count()
        
        # Active complaints
        active_complaints = CustomerComplaint.objects.filter(
            customer=customer_profile,
            status__in=['open', 'in_progress']
        ).count()
        
        dashboard_data = {
            'total_orders': all_orders.count(),
            'pending_orders': pending_orders.count(),
            'completed_orders': completed_orders.count(),
            'total_spent': customer_profile.total_spent,
            'loyalty_points': customer_profile.loyalty_points,
            'membership_tier': customer_profile.membership_tier,
            'favorite_vendors_count': favorite_vendors_count,
            'active_complaints': active_complaints
        }
        
        serializer = CustomerDashboardSerializer(dashboard_data)
        return Response(serializer.data)


class OrderHistoryView(APIView):
    """Customer order history"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can view order history'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from orders.models import Order
        from orders.serializers import OrderListSerializer
        
        # Filter parameters
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        orders = Order.objects.filter(customer=request.user)
        
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        
        orders = orders.order_by('-created_at')
        
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        result_page = paginator.paginate_queryset(orders, request)
        
        serializer = OrderListSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class NearbyVendorsView(APIView):
    """Find nearby vendors for customers"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_customer:
            return Response(
                {'error': 'Only customers can search for vendors'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get customer's location
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = float(request.query_params.get('radius', 10))  # Default 10km
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Location coordinates required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from vendors.models import VendorProfile
        from vendors.serializers import VendorListSerializer
        from geopy.distance import geodesic
        
        user_location = (float(latitude), float(longitude))
        vendors = VendorProfile.objects.filter(status='active')
        
        vendor_list = []
        for vendor in vendors:
            if vendor.latitude and vendor.longitude:
                vendor_location = (float(vendor.latitude), float(vendor.longitude))
                distance = geodesic(user_location, vendor_location).kilometers
                
                if distance <= radius:
                    vendor_data = VendorListSerializer(vendor).data
                    vendor_data['distance'] = round(distance, 2)
                    vendor_list.append(vendor_data)
        
        # Sort by distance
        vendor_list.sort(key=lambda x: x['distance'])
        return Response(vendor_list)