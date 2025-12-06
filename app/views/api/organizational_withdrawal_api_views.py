from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import OrganizationalWithdrawal
from app.serializers import OrganizationalWithdrawalSerializer
from app.views.admin.helpers import is_admin_or_board, is_admin_board_or_staff
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, apply_amount_range_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizational_withdrawal_list_api(request):
    """List organizational withdrawals"""
    # Only Admin/Board/Staff can view withdrawals
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can view withdrawals.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    withdrawals = OrganizationalWithdrawal.objects.all()
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        withdrawals = apply_text_search(withdrawals, search, ['description', 'purpose'])
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            withdrawals = apply_date_filter(withdrawals, 'date', start_date, end_date)
    
    # Apply amount range filter
    min_amount = request.query_params.get('min_amount', '').strip()
    max_amount = request.query_params.get('max_amount', '').strip()
    if min_amount or max_amount:
        withdrawals = apply_amount_range_filter(withdrawals, 'amount', min_amount, max_amount)
    
    withdrawals = withdrawals.order_by('-date', '-created_at')
    serializer = OrganizationalWithdrawalSerializer(withdrawals, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def organizational_withdrawal_create_api(request):
    """Create a new organizational withdrawal"""
    # Only Admin and Board can create withdrawals
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board can create withdrawals.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = OrganizationalWithdrawalSerializer(data=request.data)
    if serializer.is_valid():
        withdrawal = serializer.save()
        return Response(OrganizationalWithdrawalSerializer(withdrawal).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizational_withdrawal_detail_api(request, pk):
    """Get organizational withdrawal details"""
    # Only Admin/Board/Staff can view withdrawals
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can view withdrawals.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    withdrawal = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    serializer = OrganizationalWithdrawalSerializer(withdrawal)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def organizational_withdrawal_update_api(request, pk):
    """Update organizational withdrawal"""
    # Only Admin/Board/Staff can update withdrawals
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update withdrawals.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    withdrawal = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    serializer = OrganizationalWithdrawalSerializer(withdrawal, data=request.data, partial=True)
    if serializer.is_valid():
        withdrawal = serializer.save()
        return Response(OrganizationalWithdrawalSerializer(withdrawal).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def organizational_withdrawal_delete_api(request, pk):
    """Delete organizational withdrawal"""
    # Only Admin can delete withdrawals
    from app.views.admin.helpers import is_admin
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete withdrawals.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    withdrawal = get_object_or_404(OrganizationalWithdrawal, pk=pk)
    withdrawal.delete()
    return Response({'message': 'Organizational withdrawal deleted successfully'}, status=status.HTTP_200_OK)

