from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import PaymentTransaction
from app.serializers import PaymentTransactionSerializer
from app.views.admin.helpers import is_member
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, apply_amount_range_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_transaction_list_api(request):
    """List payment transactions with role-based filtering"""
    if is_member(request.user):
        # Members can only see their own transactions
        transactions = PaymentTransaction.objects.filter(user=request.user).select_related('user')
    else:
        # Admin/Board/Staff can see all transactions
        transactions = PaymentTransaction.objects.all().select_related('user')
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        transactions = apply_text_search(transactions, search, ['transaction_id', 'user__name', 'user__phone'])
    
    # Apply status filter
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            transactions = apply_date_filter(transactions, 'created_at', start_date, end_date)
    
    # Apply amount range filter
    min_amount = request.query_params.get('min_amount', '').strip()
    max_amount = request.query_params.get('max_amount', '').strip()
    if min_amount or max_amount:
        transactions = apply_amount_range_filter(transactions, 'amount', min_amount, max_amount)
    
    transactions = transactions.order_by('-created_at')
    serializer = PaymentTransactionSerializer(transactions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_transaction_detail_api(request, pk):
    """Get payment transaction details"""
    # For members, filter at query level to check access before checking existence
    # This prevents information leakage about transactions that don't belong to them
    if is_member(request.user):
        # Members can only see their own transactions
        try:
            transaction = PaymentTransaction.objects.filter(user=request.user, pk=pk).select_related('user').get()
        except PaymentTransaction.DoesNotExist:
            # Return 404 for members - transaction either doesn't exist or doesn't belong to them
            return Response(
                {'error': 'Payment transaction not found or you do not have access to view it.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Admin/Board/Staff can see all transactions
        transaction = get_object_or_404(PaymentTransaction, pk=pk)
    
    serializer = PaymentTransactionSerializer(transaction)
    return Response(serializer.data, status=status.HTTP_200_OK)

