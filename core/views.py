# core/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Avg, Count
from django.conf import settings
import requests
from geopy.distance import geodesic

from .models import Location, GasProduct, Rating, Notification, SystemSettings
from .serializers import (
    LocationSerializer, GasProductSerializer, RatingSerializer,
    NotificationSerializer, SystemSettingsSerializer
)

class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user locations"""
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only access their own locations"""
        return Location.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set location as default"""
        location = self.get_object()
        # Remove default from other locations
        Location.objects.filter(user=request.user, is_default=True).update(is_default=False)
        # Set this as default
        location.is_default = True
        location.save()
        
        return Response({'message': 'Location set as default'})


class GasProductViewSet(viewsets.ModelViewSet):
    """ViewSet for managing gas products"""
    queryset = GasProduct.objects.filter(is_active=True)
    serializer_class = GasProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        """Only admins can create/update/delete"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated]
            # Add admin check here if needed
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def by_size(self, request):
        """Get products grouped by cylinder size"""
        size = request.query_params.get('size')
        if size:
            products = self.queryset.filter(cylinder_size=size)
        else:
            products = self.queryset.all()
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class RatingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing ratings"""
    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.is_admin_user:
            return Rating.objects.all()
        elif user.is_customer:
            return Rating.objects.filter(customer=user)
        elif user.is_vendor:
            return Rating.objects.filter(vendor=user)
        elif user.is_rider:
            return Rating.objects.filter(rider=user)
        return Rating.objects.none()
    
    def perform_create(self, serializer):
        """Ensure only customers can create ratings"""
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can create ratings")
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def vendor_ratings(self, request):
        """Get ratings for a specific vendor"""
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            ratings = Rating.objects.filter(vendor_id=vendor_id, is_published=True)
            serializer = self.get_serializer(ratings, many=True)
            return Response(serializer.data)
        return Response({'error': 'vendor_id parameter required'}, status=400)
    
    @action(detail=False, methods=['get'])
    def rider_ratings(self, request):
        """Get ratings for a specific rider"""
        rider_id = request.query_params.get('rider_id')
        if rider_id:
            ratings = Rating.objects.filter(rider_id=rider_id, is_published=True)
            serializer = self.get_serializer(ratings, many=True)
            return Response(serializer.data)
        return Response({'error': 'rider_id parameter required'}, status=400)


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own notifications"""
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        return Response({'unread_count': count})


class SystemSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing system settings (admin only)"""
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only admins can access system settings"""
        if not self.request.user.is_admin_user:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()


class SearchView(APIView):
    """Global search functionality"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'all')  # all, vendors, products, riders
        
        results = {}
        
        if search_type in ['all', 'vendors']:
            from vendors.models import VendorProfile
            from vendors.serializers import VendorListSerializer
            
            vendors = VendorProfile.objects.filter(
                Q(business_name__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query),
                status='active'
            )[:10]
            results['vendors'] = VendorListSerializer(vendors, many=True).data
        
        if search_type in ['all', 'products']:
            products = GasProduct.objects.filter(
                Q(name__icontains=query) |
                Q(brand__icontains=query),
                is_active=True
            )[:10]
            results['products'] = GasProductSerializer(products, many=True).data
        
        if search_type in ['all', 'riders'] and request.user.is_vendor:
            from riders.models import RiderProfile
            from riders.serializers import RiderListSerializer
            
            riders = RiderProfile.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query),
                status='active'
            )[:10]
            results['riders'] = RiderListSerializer(riders, many=True).data
        
        return Response(results)


class AnalyticsView(APIView):
    """System analytics (admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.contrib.auth import get_user_model
        from orders.models import Order
        from vendors.models import VendorProfile
        from riders.models import RiderProfile
        from customers.models import CustomerProfile
        
        User = get_user_model()
        
        analytics = {
            'users': {
                'total': User.objects.count(),
                'customers': User.objects.filter(role='customer').count(),
                'vendors': User.objects.filter(role='vendor').count(),
                'riders': User.objects.filter(role='rider').count(),
                'verified': User.objects.filter(is_verified=True).count(),
            },
            'orders': {
                'total': Order.objects.count(),
                'pending': Order.objects.filter(status='pending').count(),
                'completed': Order.objects.filter(status='delivered').count(),
                'cancelled': Order.objects.filter(status='cancelled').count(),
            },
            'vendors': {
                'total': VendorProfile.objects.count(),
                'active': VendorProfile.objects.filter(status='active').count(),
                'pending': VendorProfile.objects.filter(status='pending').count(),
            },
            'riders': {
                'total': RiderProfile.objects.count(),
                'active': RiderProfile.objects.filter(status='active').count(),
                'online': RiderProfile.objects.filter(status='active', is_available=True).count(),
            }
        }
        
        return Response(analytics)


class GeocodeView(APIView):
    """Geocoding service using Google Maps API"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        address = request.data.get('address')
        if not address:
            return Response(
                {'error': 'Address is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            return Response(
                {'error': 'Google Maps API not configured'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                
                return Response({
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'formatted_address': result['formatted_address'],
                    'place_id': result.get('place_id'),
                    'address_components': result.get('address_components', [])
                })
            else:
                return Response(
                    {'error': 'Address not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return Response(
                {'error': 'Geocoding service error'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class DirectionsView(APIView):
    """Get directions between two points"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        origin_lat = request.data.get('origin_lat')
        origin_lng = request.data.get('origin_lng')
        dest_lat = request.data.get('dest_lat')
        dest_lng = request.data.get('dest_lng')
        
        if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
            return Response(
                {'error': 'Origin and destination coordinates required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate straight-line distance
        origin = (float(origin_lat), float(origin_lng))
        destination = (float(dest_lat), float(dest_lng))
        distance = geodesic(origin, destination).kilometers
        
        # Estimate travel time (assuming average speed of 30 km/h in city)
        estimated_time = (distance / 30) * 60  # in minutes
        
        api_key = settings.GOOGLE_MAPS_API_KEY
        if api_key:
            try:
                url = f"https://maps.googleapis.com/maps/api/directions/json"
                params = {
                    'origin': f"{origin_lat},{origin_lng}",
                    'destination': f"{dest_lat},{dest_lng}",
                    'key': api_key,
                    'mode': 'driving'
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if data['status'] == 'OK' and data['routes']:
                    route = data['routes'][0]
                    leg = route['legs'][0]
                    
                    return Response({
                        'distance_km': distance,
                        'estimated_time_minutes': estimated_time,
                        'google_data': {
                            'distance': leg['distance'],
                            'duration': leg['duration'],
                            'start_address': leg['start_address'],
                            'end_address': leg['end_address'],
                            'steps': leg.get('steps', [])
                        }
                    })
            except Exception:
                pass  # Fall back to basic calculation
        
        return Response({
            'distance_km': round(distance, 2),
            'estimated_time_minutes': round(estimated_time, 2),
            'note': 'Calculated using straight-line distance'
        })