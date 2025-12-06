from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import User
from app.serializers import UserSerializer
from app.views.admin.helpers import is_admin, is_admin_or_board, is_member
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_api(request):
    """List users with role-based filtering"""
    # Only Admin and Board can view users list
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board members can view users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    users = User.objects.all()
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        users = apply_text_search(users, search, ['name', 'phone'])
    
    # Apply status filter
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        if status_filter.lower() == 'active':
            users = users.filter(is_active=True)
        elif status_filter.lower() == 'inactive':
            users = users.filter(is_active=False)
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            users = apply_date_filter(users, 'created_at', start_date, end_date)
    
    users = users.order_by('-created_at')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create_api(request):
    """Create a new user"""
    # Only Admin can create users
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can create users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Set password if provided
        if 'password' in request.data:
            user.set_password(request.data['password'])
            user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail_api(request, pk):
    """Get user details"""
    user = get_object_or_404(User, pk=pk)
    
    # Admin and Board can view any user, Members can only view themselves
    if is_member(request.user) and request.user.id != user.id:
        return Response(
            {'error': 'Access denied. You can only view your own profile.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not is_admin_or_board(request.user) and request.user.id != user.id:
        return Response(
            {'error': 'Access denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update_api(request, pk):
    """Update user"""
    user = get_object_or_404(User, pk=pk)
    
    # Only Admin can update users (except members can update themselves)
    if is_member(request.user):
        if request.user.id != user.id:
            return Response(
                {'error': 'Access denied. You can only update your own profile.'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can update users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        updated_user = serializer.save()
        # Set password if provided
        if 'password' in request.data and request.data['password']:
            updated_user.set_password(request.data['password'])
            updated_user.save()
        return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete_api(request, pk):
    """Delete user"""
    # Only Admin can delete users
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)

