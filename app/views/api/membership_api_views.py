from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import Membership
from app.serializers import MembershipSerializer
from app.views.admin.helpers import is_admin
from app.views.admin.filter_helpers import apply_text_search


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def membership_list_api(request):
    """List all memberships"""
    memberships = Membership.objects.all()
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        memberships = apply_text_search(memberships, search, ['name', 'description'])
    
    memberships = memberships.order_by('name')
    serializer = MembershipSerializer(memberships, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def membership_create_api(request):
    """Create a new membership"""
    # Only Admin can create memberships
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can create memberships.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MembershipSerializer(data=request.data)
    if serializer.is_valid():
        membership = serializer.save()
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def membership_detail_api(request, pk):
    """Get membership details"""
    membership = get_object_or_404(Membership, pk=pk)
    serializer = MembershipSerializer(membership)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def membership_update_api(request, pk):
    """Update membership"""
    # Only Admin can update memberships
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can update memberships.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    membership = get_object_or_404(Membership, pk=pk)
    serializer = MembershipSerializer(membership, data=request.data, partial=True)
    if serializer.is_valid():
        membership = serializer.save()
        return Response(MembershipSerializer(membership).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def membership_delete_api(request, pk):
    """Delete membership"""
    # Only Admin can delete memberships
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete memberships.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    membership = get_object_or_404(Membership, pk=pk)
    membership.delete()
    return Response({'message': 'Membership deleted successfully'}, status=status.HTTP_200_OK)

