from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import FundManagement, FundManagementType
from app.serializers import FundManagementSerializer
from app.views.admin.helpers import is_admin_or_board, is_admin_board_or_staff
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, apply_amount_range_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fund_management_list_api(request):
    """List fund management records"""
    # Only Admin/Board/Staff can view fund management records
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can view fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = FundManagement.objects.all()
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        fund_management = apply_text_search(fund_management, search, ['purpose'])
    
    # Apply type filter
    fund_type = request.query_params.get('type', '').strip()
    if fund_type:
        fund_management = fund_management.filter(type=fund_type)
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            fund_management = apply_date_filter(fund_management, 'date', start_date, end_date)
    
    # Apply amount range filter
    min_amount = request.query_params.get('min_amount', '').strip()
    max_amount = request.query_params.get('max_amount', '').strip()
    if min_amount or max_amount:
        fund_management = apply_amount_range_filter(fund_management, 'amount', min_amount, max_amount)
    
    fund_management = fund_management.order_by('-date', '-created_at')
    serializer = FundManagementSerializer(fund_management, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fund_management_create_api(request):
    """Create a new fund management record"""
    # Only Admin and Board can create fund management records
    if not is_admin_or_board(request.user):
        return Response(
            {'error': 'Access denied. Only Admin and Board can create fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = FundManagementSerializer(data=request.data)
    if serializer.is_valid():
        fund_management = serializer.save()
        return Response(FundManagementSerializer(fund_management).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fund_management_detail_api(request, pk):
    """Get fund management record details"""
    # Only Admin/Board/Staff can view fund management records
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can view fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = get_object_or_404(FundManagement, pk=pk)
    serializer = FundManagementSerializer(fund_management)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def fund_management_update_api(request, pk):
    """Update fund management record"""
    # Only Admin/Board/Staff can update fund management records
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = get_object_or_404(FundManagement, pk=pk)
    serializer = FundManagementSerializer(fund_management, data=request.data, partial=True)
    if serializer.is_valid():
        fund_management = serializer.save()
        return Response(FundManagementSerializer(fund_management).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def fund_management_delete_api(request, pk):
    """Delete fund management record"""
    # Only Admin can delete fund management records
    from app.views.admin.helpers import is_admin
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete fund management records.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    fund_management = get_object_or_404(FundManagement, pk=pk)
    fund_management.delete()
    return Response({'message': 'Fund management record deleted successfully'}, status=status.HTTP_200_OK)

