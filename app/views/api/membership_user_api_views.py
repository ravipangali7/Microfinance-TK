from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import MembershipUser
from app.serializers import MembershipUserSerializer
from app.views.admin.helpers import is_admin, is_member


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def membership_user_list_api(request):
    """List membership-user relationships with role-based filtering"""
    if is_member(request.user):
        # Members can only see their own membership users
        membership_users = MembershipUser.objects.filter(user=request.user).select_related('user', 'membership').order_by('-created_at')
    else:
        # Admin/Board/Staff can see all membership users
        membership_users = MembershipUser.objects.all().select_related('user', 'membership').order_by('-created_at')
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
    """Get membership-user relationship details"""
    membership_user = get_object_or_404(MembershipUser, pk=pk)
    
    # Members can only see their own membership users
    if is_member(request.user) and membership_user.user.id != request.user.id:
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

