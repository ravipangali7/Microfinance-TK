from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from decimal import Decimal
from app.models import LoanInterestPayment, Loan, PaymentStatus
from app.serializers import LoanInterestPaymentSerializer
from app.views.admin.helpers import is_admin_board_or_staff, is_member
from app.views.admin.filter_helpers import (
    apply_text_search, apply_date_filter, apply_amount_range_filter, parse_date_range
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_interest_payment_list_api(request):
    """List loan interest payments with role-based filtering"""
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
        payments = LoanInterestPayment.objects.filter(loan=loan).select_related('loan')
    elif is_member(request.user):
        # Members can only see payments for their own loans
        payments = LoanInterestPayment.objects.filter(loan__user=request.user).select_related('loan')
    else:
        # Admin/Board/Staff can see all payments
        payments = LoanInterestPayment.objects.all().select_related('loan')
    
    # Apply search filter
    search = request.query_params.get('search', '').strip()
    if search:
        payments = apply_text_search(payments, search, ['loan__user__name', 'loan_id'])
    
    # Apply status filter
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
    
    # Apply date range filter
    date_range_str = request.query_params.get('date_range', '').strip()
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
            payments = apply_date_filter(payments, 'paid_date', start_date, end_date)
    
    # Apply amount range filter
    min_amount = request.query_params.get('min_amount', '').strip()
    max_amount = request.query_params.get('max_amount', '').strip()
    if min_amount or max_amount:
        payments = apply_amount_range_filter(payments, 'amount', min_amount, max_amount)
    
    payments = payments.order_by('-paid_date', '-created_at')
    serializer = LoanInterestPaymentSerializer(payments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def loan_interest_payment_create_api(request):
    """Create a new loan interest payment or update existing pending one"""
    # Members can create interest payments for their own loans, Admin/Board/Staff can create any
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
                {'error': 'You can only create interest payments for your own loans.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Ensure loan is active or approved
        if loan.status not in ['approved', 'active']:
            return Response(
                {'error': 'Interest payments can only be made for approved or active loans.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Check for existing pending payment with strict matching
    paid_date_str = data.get('paid_date')
    amount = data.get('amount')
    
    if loan_id and paid_date_str and amount:
        try:
            # Parse date
            if isinstance(paid_date_str, str):
                paid_date = parse_date(paid_date_str)
                if paid_date is None:
                    # Date parsing failed, continue with normal creation
                    pass
                else:
                    # Convert amount to Decimal for comparison
                    amount_decimal = Decimal(str(amount))
                    
                    # Check for existing pending payment with exact match
                    existing_pending = LoanInterestPayment.objects.filter(
                        loan_id=loan_id,
                        paid_date=paid_date,
                        amount=amount_decimal,
                        payment_status=PaymentStatus.PENDING
                    ).first()
                    
                    if existing_pending:
                        # Update existing pending payment
                        serializer = LoanInterestPaymentSerializer(existing_pending, data=data, partial=True)
                        if serializer.is_valid():
                            payment = serializer.save()
                            return Response(LoanInterestPaymentSerializer(payment).data, status=status.HTTP_200_OK)
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Date is already a date object
                paid_date = paid_date_str
                # Convert amount to Decimal for comparison
                amount_decimal = Decimal(str(amount))
                
                # Check for existing pending payment with exact match
                existing_pending = LoanInterestPayment.objects.filter(
                    loan_id=loan_id,
                    paid_date=paid_date,
                    amount=amount_decimal,
                    payment_status=PaymentStatus.PENDING
                ).first()
                
                if existing_pending:
                    # Update existing pending payment
                    serializer = LoanInterestPaymentSerializer(existing_pending, data=data, partial=True)
                    if serializer.is_valid():
                        payment = serializer.save()
                        return Response(LoanInterestPaymentSerializer(payment).data, status=status.HTTP_200_OK)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError) as e:
            # If parsing fails, continue with normal creation
            pass
    
    # No existing pending payment found, create new one
    serializer = LoanInterestPaymentSerializer(data=data)
    if serializer.is_valid():
        payment = serializer.save()
        return Response(LoanInterestPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_interest_payment_detail_api(request, pk):
    """Get loan interest payment details"""
    payment = get_object_or_404(LoanInterestPayment, pk=pk)
    
    # Members can only see payments for their own loans
    if is_member(request.user) and payment.loan.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own loan payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = LoanInterestPaymentSerializer(payment)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def loan_interest_payment_update_api(request, pk):
    """Update loan interest payment"""
    # Only Admin/Board/Staff can update interest payments
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update interest payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    payment = get_object_or_404(LoanInterestPayment, pk=pk)
    serializer = LoanInterestPaymentSerializer(payment, data=request.data, partial=True)
    if serializer.is_valid():
        payment = serializer.save()
        return Response(LoanInterestPaymentSerializer(payment).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def loan_interest_payment_delete_api(request, pk):
    """Delete loan interest payment"""
    # Only Admin/Board/Staff can delete interest payments
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can delete interest payments.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    payment = get_object_or_404(LoanInterestPayment, pk=pk)
    payment.delete()
    return Response({'message': 'Loan interest payment deleted successfully'}, status=status.HTTP_200_OK)

