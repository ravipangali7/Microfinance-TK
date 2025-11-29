from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import LoanPrinciplePayment, Loan
from app.serializers import LoanPrinciplePaymentSerializer
from app.views.admin.helpers import is_admin_board_or_staff, is_member


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_principle_payment_list_api(request):
    """List loan principle payments with role-based filtering"""
    loan_id = request.query_params.get('loan_id', None)
    
    if loan_id:
        # Filter by loan
        loan = get_object_or_404(Loan, pk=loan_id)
        # Check access
        if is_member(request.user) and loan.user.id != request.user.id:
            return Response(
                {'error': 'Access denied. You can only view your own loan payments.'},
                status=status.HTTP_403_FORBIDDEN
            )
        payments = LoanPrinciplePayment.objects.filter(loan=loan).select_related('loan').order_by('-paid_date', '-created_at')
    elif is_member(request.user):
        # Members can only see payments for their own loans
        payments = LoanPrinciplePayment.objects.filter(loan__user=request.user).select_related('loan').order_by('-paid_date', '-created_at')
    else:
        # Admin/Board/Staff can see all payments
        payments = LoanPrinciplePayment.objects.all().select_related('loan').order_by('-paid_date', '-created_at')
    
    serializer = LoanPrinciplePaymentSerializer(payments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def loan_principle_payment_create_api(request):
    """Create a new loan principle payment"""
    # Members can create principle payments for their own loans, Admin/Board/Staff can create any
    data = request.data.copy()
    loan_id = data.get('loan_id')
    
    if not loan_id:
        return Response(
            {'error': 'loan_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    loan = get_object_or_404(Loan, pk=loan_id)
    
    if is_member(request.user):
        # Members can only create payments for their own loans
        if loan.user.id != request.user.id:
            return Response(
                {'error': 'You can only create principle payments for your own loans.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Ensure loan is active or approved
        if loan.status not in ['approved', 'active']:
            return Response(
                {'error': 'Principle payments can only be made for approved or active loans.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Validate amount doesn't exceed remaining principle
    amount = data.get('amount')
    if amount:
        from decimal import Decimal
        try:
            amount_decimal = Decimal(str(amount))
            remaining = loan.get_remaining_principle()
            if amount_decimal > remaining:
                return Response(
                    {'error': f'Payment amount cannot exceed remaining principle of {remaining}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = LoanPrinciplePaymentSerializer(data=data)
    if serializer.is_valid():
        payment = serializer.save()
        return Response(LoanPrinciplePaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_principle_payment_detail_api(request, pk):
    """Get loan principle payment details"""
    payment = get_object_or_404(LoanPrinciplePayment, pk=pk)
    
    # Members can only see payments for their own loans
    if is_member(request.user) and payment.loan.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own loan payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = LoanPrinciplePaymentSerializer(payment)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def loan_principle_payment_update_api(request, pk):
    """Update loan principle payment"""
    # Only Admin/Board/Staff can update principle payments
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update principle payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    payment = get_object_or_404(LoanPrinciplePayment, pk=pk)
    
    # Validate amount if being updated
    amount = request.data.get('amount')
    if amount:
        from decimal import Decimal
        try:
            amount_decimal = Decimal(str(amount))
            # Calculate remaining principle excluding this payment
            other_payments_total = sum(
                p.amount for p in payment.loan.principle_payments.filter(payment_status='paid').exclude(pk=payment.pk)
            )
            remaining = payment.loan.principal_amount - other_payments_total
            if amount_decimal > remaining:
                return Response(
                    {'error': f'Payment amount cannot exceed remaining principle of {remaining}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = LoanPrinciplePaymentSerializer(payment, data=request.data, partial=True)
    if serializer.is_valid():
        payment = serializer.save()
        return Response(LoanPrinciplePaymentSerializer(payment).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def loan_principle_payment_delete_api(request, pk):
    """Delete loan principle payment"""
    # Only Admin/Board/Staff can delete principle payments
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can delete principle payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    payment = get_object_or_404(LoanPrinciplePayment, pk=pk)
    payment.delete()
    return Response({'message': 'Loan principle payment deleted successfully'}, status=status.HTTP_200_OK)

