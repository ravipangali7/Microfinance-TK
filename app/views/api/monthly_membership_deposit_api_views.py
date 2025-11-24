from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import MonthlyMembershipDeposit
from app.serializers import MonthlyMembershipDepositSerializer
from app.views.admin.helpers import is_admin_board_or_staff, is_member


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_membership_deposit_list_api(request):
    """List monthly membership deposits with role-based filtering"""
    if is_member(request.user):
        # Members can only see their own deposits
        deposits = MonthlyMembershipDeposit.objects.filter(user=request.user).select_related('user', 'membership').order_by('-date', '-created_at')
    else:
        # Admin/Board/Staff can see all deposits
        deposits = MonthlyMembershipDeposit.objects.all().select_related('user', 'membership').order_by('-date', '-created_at')
    
    serializer = MonthlyMembershipDepositSerializer(deposits, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monthly_membership_deposit_create_api(request):
    """Create a new monthly membership deposit"""
    # Members can create their own deposits, Admin/Board/Staff can create any
    data = request.data.copy()
    
    if is_member(request.user):
        # Members can only create deposits for themselves
        data['user_id'] = request.user.id
        # Ensure they have the membership
        membership_id = data.get('membership_id')
        if membership_id:
            from app.models import MembershipUser
            if not MembershipUser.objects.filter(user=request.user, membership_id=membership_id).exists():
                return Response(
                    {'error': 'You do not have this membership.'},
                    status=status.HTTP_403_FORBIDDEN
                )
    
    serializer = MonthlyMembershipDepositSerializer(data=data)
    if serializer.is_valid():
        deposit = serializer.save()
        return Response(MonthlyMembershipDepositSerializer(deposit).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_membership_deposit_detail_api(request, pk):
    """Get monthly membership deposit details"""
    deposit = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    
    # Members can only see their own deposits
    if is_member(request.user) and deposit.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own deposits.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MonthlyMembershipDepositSerializer(deposit)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def monthly_membership_deposit_update_api(request, pk):
    """Update monthly membership deposit"""
    # Only Admin/Board/Staff can update deposits
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update deposits.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    deposit = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    serializer = MonthlyMembershipDepositSerializer(deposit, data=request.data, partial=True)
    if serializer.is_valid():
        deposit = serializer.save()
        return Response(MonthlyMembershipDepositSerializer(deposit).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def monthly_membership_deposit_delete_api(request, pk):
    """Delete monthly membership deposit"""
    # Only Admin/Board/Staff can delete deposits
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can delete deposits.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    deposit = get_object_or_404(MonthlyMembershipDeposit, pk=pk)
    deposit.delete()
    return Response({'message': 'Monthly membership deposit deleted successfully'}, status=status.HTTP_200_OK)

