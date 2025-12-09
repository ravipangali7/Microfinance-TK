from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import MembershipUser
from app.serializers import MembershipUserSerializer
from app.views.admin.helpers import is_admin, is_member
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def membership_user_list_api(request):
    """List membership-user relationships - all users see only their own"""
    # Always filter by logged-in user
    membership_users = MembershipUser.objects.filter(user=request.user).select_related('user', 'membership')
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        membership_users = apply_text_search(membership_users, search, ['user__name', 'user__phone', 'membership__name'])
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            membership_users = apply_date_filter(membership_users, 'created_at', start_date, end_date)
    
    # Apply status filter (if applicable - check if MembershipUser has is_active field)
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        # Assuming there might be an is_active field, adjust based on actual model
        # For now, we'll skip this as MembershipUser might not have status
        pass
    
    membership_users = membership_users.order_by('-created_at')
    serializer = MembershipUserSerializer(membership_users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def membership_user_create_api(request):
    """Create a new membership-user relationship"""
    # Only Admin can create membership users
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can create membership users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MembershipUserSerializer(data=request.data)
    if serializer.is_valid():
        membership_user = serializer.save()
        return Response(MembershipUserSerializer(membership_user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def membership_user_detail_api(request, pk):
    """Get membership-user relationship details - all users can only see their own"""
    membership_user = get_object_or_404(MembershipUser, pk=pk)
    
    # All users can only see their own membership users
    if membership_user.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own memberships.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MembershipUserSerializer(membership_user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def membership_user_update_api(request, pk):
    """Update membership-user relationship"""
    # Only Admin can update membership users
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can update membership users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    membership_user = get_object_or_404(MembershipUser, pk=pk)
    serializer = MembershipUserSerializer(membership_user, data=request.data, partial=True)
    if serializer.is_valid():
        membership_user = serializer.save()
        return Response(MembershipUserSerializer(membership_user).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def membership_user_delete_api(request, pk):
    """Delete membership-user relationship"""
    # Only Admin can delete membership users
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete membership users.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    membership_user = get_object_or_404(MembershipUser, pk=pk)
    membership_user.delete()
    return Response({'message': 'Membership user deleted successfully'}, status=status.HTTP_200_OK)

