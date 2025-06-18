# vendors/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from geopy.distance import geodesic

from .models import (
    VendorProfile, VendorInventory, VendorHours, 
    VendorBankAccount, VendorPromotion
)
from .serializers import (
    VendorProfileSerializer, VendorInventorySerializer, VendorHoursSerializer,
    VendorBankAccountSerializer, VendorPromotionSerializer, VendorListSerializer,
    VendorDashboardSerializer
)

class VendorProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor profiles"""
    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return VendorProfile.objects.all()
        elif user.is_vendor:
            return VendorProfile.objects.filter(user=user)
        else:
            # Customers and riders can see active vendors only
            return VendorProfile.objects.filter(status='active')
    
    def perform_create(self, serializer):
        """Only vendors can create vendor profiles"""
        if not self.request.user.is_vendor:
            raise permissions.PermissionDenied("Only vendor users can create vendor profiles")
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify vendor (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = self.get_object()
        vendor.status = 'active'
        vendor.verified_at = timezone.now()
        vendor.verified_by = request.user
        vendor.save()
        
        return Response({'message': 'Vendor verified successfully'})
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend vendor (admin only)"""
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = self.get_object()
        vendor.status = 'suspended'
        vendor.save()
        
        return Response({'message': 'Vendor suspended successfully'})


class VendorInventoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor inventory"""
    serializer_class = VendorInventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Vendors can only manage their own inventory"""
        user = self.request.user
        if user.is_admin_user:
            return VendorInventory.objects.all()
        elif user.is_vendor:
            try:
                vendor_profile = user.vendor_profile
                return VendorInventory.objects.filter(vendor=vendor_profile)
            except VendorProfile.DoesNotExist:
                return VendorInventory.objects.none()
        else:
            # Customers can see available inventory
            return VendorInventory.objects.filter(
                is_available=True,
                current_stock__gt=0,
                vendor__status='active'
            )
    
    def perform_create(self, serializer):
        """Set vendor from user profile"""
        if not self.request.user.is_vendor:
            raise permissions.PermissionDenied("Only vendors can manage inventory")
        
        try:
            vendor_profile = self.request.user.vendor_profile
            serializer.save(vendor=vendor_profile)
        except VendorProfile.DoesNotExist:
            raise permissions.PermissionDenied("Vendor profile not found")
    
    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        """Restock inventory item"""
        inventory_item = self.get_object()
        quantity = request.data.get('quantity', 0)
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than 0'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inventory_item.current_stock += quantity
        inventory_item.last_restocked = timezone.now()
        inventory_item.save()
        
        return Response({
            'message': f'Restocked {quantity} units',
            'new_stock': inventory_item.current_stock
        })
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock items"""
        if not request.user.is_vendor:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            vendor_profile = request.user.vendor_profile
            low_stock_items = VendorInventory.objects.filter(
                vendor=vendor_profile,
                current_stock__lte=models.F('minimum_stock')
            )
            serializer = self.get_serializer(low_stock_items, many=True)
            return Response(serializer.data)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=404)


class VendorHoursViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor operating hours"""
    serializer_class = VendorHoursSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return VendorHours.objects.all()
        elif user.is_vendor:
            try:
                vendor_profile = user.vendor_profile
                return VendorHours.objects.filter(vendor=vendor_profile)
            except VendorProfile.DoesNotExist:
                return VendorHours.objects.none()
        else:
            # Customers can see operating hours of active vendors
            vendor_id = self.request.query_params.get('vendor_id')
            if vendor_id:
                return VendorHours.objects.filter(
                    vendor_id=vendor_id,
                    vendor__status='active'
                )
            return VendorHours.objects.none()
    
    def perform_create(self, serializer):
        """Set vendor from user profile"""
        if not self.request.user.is_vendor:
            raise permissions.PermissionDenied("Only vendors can manage operating hours")
        
        try:
            vendor_profile = self.request.user.vendor_profile
            serializer.save(vendor=vendor_profile)
        except VendorProfile.DoesNotExist:
            raise permissions.PermissionDenied("Vendor profile not found")


class VendorBankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor bank accounts"""
    serializer_class = VendorBankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Vendors can only see their own bank accounts"""
        user = self.request.user
        if user.is_admin_user:
            return VendorBankAccount.objects.all()
        elif user.is_vendor:
            try:
                vendor_profile = user.vendor_profile
                return VendorBankAccount.objects.filter(vendor=vendor_profile)
            except VendorProfile.DoesNotExist:
                return VendorBankAccount.objects.none()
        return VendorBankAccount.objects.none()
    
    def perform_create(self, serializer):
        """Set vendor from user profile"""
        if not self.request.user.is_vendor:
            raise permissions.PermissionDenied("Only vendors can manage bank accounts")
        
        try:
            vendor_profile = self.request.user.vendor_profile
            serializer.save(vendor=vendor_profile)
        except VendorProfile.DoesNotExist:
            raise permissions.PermissionDenied("Vendor profile not found")
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set bank account as primary"""
        bank_account = self.get_object()
        
        # Remove primary from other accounts
        VendorBankAccount.objects.filter(
            vendor=bank_account.vendor,
            is_primary=True
        ).update(is_primary=False)
        
        # Set this as primary
        bank_account.is_primary = True
        bank_account.save()
        
        return Response({'message': 'Bank account set as primary'})


class VendorPromotionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor promotions"""
    serializer_class = VendorPromotionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return VendorPromotion.objects.all()
        elif user.is_vendor:
            try:
                vendor_profile = user.vendor_profile
                return VendorPromotion.objects.filter(vendor=vendor_profile)
            except VendorProfile.DoesNotExist:
                return VendorPromotion.objects.none()
        else:
            # Customers can see active promotions
            vendor_id = self.request.query_params.get('vendor_id')
            if vendor_id:
                return VendorPromotion.objects.filter(
                    vendor_id=vendor_id,
                    is_active=True,
                    start_date__lte=timezone.now(),
                    end_date__gte=timezone.now()
                )
            return VendorPromotion.objects.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
    
    def perform_create(self, serializer):
        """Set vendor from user profile"""
        if not self.request.user.is_vendor:
            raise permissions.PermissionDenied("Only vendors can create promotions")
        
        try:
            vendor_profile = self.request.user.vendor_profile
            serializer.save(vendor=vendor_profile)
        except VendorProfile.DoesNotExist:
            raise permissions.PermissionDenied("Vendor profile not found")


class VendorDashboardView(APIView):
    """Vendor dashboard with key metrics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_vendor:
            return Response(
                {'error': 'Only vendors can access dashboard'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            vendor_profile = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=404)
        
        from orders.models import Order
        
        # Date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Order statistics
        all_orders = Order.objects.filter(vendor=vendor_profile)
        pending_orders = all_orders.filter(status__in=['pending', 'confirmed', 'preparing'])
        completed_orders = all_orders.filter(status='delivered')
        
        # Revenue statistics
        total_revenue = completed_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Inventory statistics
        inventory_items = VendorInventory.objects.filter(vendor=vendor_profile)
        low_stock_items = inventory_items.filter(
            current_stock__lte=models.F('minimum_stock')
        ).count()
        
        # Active promotions
        active_promotions = VendorPromotion.objects.filter(
            vendor=vendor_profile,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).count()
        
        dashboard_data = {
            'total_orders': all_orders.count(),
            'pending_orders': pending_orders.count(),
            'completed_orders': completed_orders.count(),
            'total_revenue': total_revenue,
            'average_rating': vendor_profile.average_rating,
            'low_stock_items': low_stock_items,
            'active_promotions': active_promotions
        }
        
        serializer = VendorDashboardSerializer(dashboard_data)
        return Response(serializer.data)


class VendorAnalyticsView(APIView):
    """Detailed vendor analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_vendor:
            return Response(
                {'error': 'Only vendors can access analytics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            vendor_profile = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=404)
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        from orders.models import Order
        
        orders = Order.objects.filter(
            vendor=vendor_profile,
            created_at__date__gte=start_date
        )
        
        # Daily sales data
        daily_sales = orders.values('created_at__date').annotate(
            orders_count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('created_at__date')
        
        # Top selling products
        from orders.models import OrderItem
        top_products = OrderItem.objects.filter(
            order__vendor=vendor_profile,
            order__created_at__date__gte=start_date
        ).values('product_name', 'cylinder_size').annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum('total_price')
        ).order_by('-quantity_sold')[:10]
        
        analytics = {
            'period_days': days,
            'daily_sales': list(daily_sales),
            'top_products': list(top_products),
            'total_orders': orders.count(),
            'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        }
        
        return Response(analytics)


class VendorOrdersView(APIView):
    """Vendor orders management"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_vendor:
            return Response(
                {'error': 'Only vendors can view orders'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            vendor_profile = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=404)
        
        from orders.models import Order
        from orders.serializers import OrderListSerializer
        
        # Filter parameters
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        orders = Order.objects.filter(vendor=vendor_profile)
        
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


class VendorSearchView(APIView):
    """Search for vendors based on location and other criteria"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get search parameters
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius = float(request.query_params.get('radius', 10))  # Default 10km
        business_type = request.query_params.get('business_type')
        min_rating = request.query_params.get('min_rating')
        
        vendors = VendorProfile.objects.filter(status='active')
        
        # Filter by business type
        if business_type:
            vendors = vendors.filter(business_type=business_type)
        
        # Filter by rating
        if min_rating:
            vendors = vendors.filter(average_rating__gte=float(min_rating))
        
        # Calculate distance if coordinates provided
        if latitude and longitude:
            user_location = (float(latitude), float(longitude))
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
        else:
            # Return all active vendors without distance calculation
            serializer = VendorListSerializer(vendors, many=True)
            return Response(serializer.data)