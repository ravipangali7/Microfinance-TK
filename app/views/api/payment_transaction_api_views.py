from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import PaymentTransaction
from app.serializers import PaymentTransactionSerializer
from app.views.admin.helpers import is_member


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_transaction_list_api(request):
    """List payment transactions with role-based filtering"""
    if is_member(request.user):
        # Members can only see their own transactions
        transactions = PaymentTransaction.objects.filter(user=request.user).select_related('user').order_by('-created_at')
    else:
        # Admin/Board/Staff can see all transactions
        transactions = PaymentTransaction.objects.all().select_related('user').order_by('-created_at')
    
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

