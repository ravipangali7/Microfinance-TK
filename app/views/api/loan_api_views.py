from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from app.models import Loan, PaymentStatus
from app.serializers import LoanSerializer
from app.views.admin.helpers import is_admin_board_or_staff, is_member


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_list_api(request):
    """List loans with role-based filtering"""
    if is_member(request.user):
        # Members can only see their own loans
        loans = Loan.objects.filter(user=request.user).select_related('user', 'action_by').order_by('-applied_date', '-created_at')
    else:
        # Admin/Board/Staff can see all loans
        loans = Loan.objects.all().select_related('user', 'action_by').order_by('-applied_date', '-created_at')
    
    serializer = LoanSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def loan_create_api(request):
    """Create a new loan"""
    # For members, ensure they can only create loans for themselves
    if is_member(request.user):
        user_id = request.data.get('user_id')
        # If user_id is provided, it must match the logged-in user
        if user_id and int(user_id) != request.user.id:
            return Response(
                {'error': 'Access denied. Members can only create loans for themselves.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Force user_id to be the logged-in user for members
        request.data['user_id'] = request.user.id
        # Set status to 'pending' for member applications
        if 'status' not in request.data:
            request.data['status'] = 'pending'
    
    serializer = LoanSerializer(data=request.data)
    if serializer.is_valid():
        loan = serializer.save()
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_detail_api(request, pk):
    """Get loan details"""
    loan = get_object_or_404(Loan, pk=pk)
    
    # Members can only see their own loans
    if is_member(request.user) and loan.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = LoanSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def loan_update_api(request, pk):
    """Update loan"""
    # Only Admin/Board/Staff can update loans
    if not is_admin_board_or_staff(request.user):
        return Response(
            {'error': 'Access denied. Only Admin, Board, and Staff can update loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    loan = get_object_or_404(Loan, pk=pk)
    serializer = LoanSerializer(loan, data=request.data, partial=True)
    if serializer.is_valid():
        loan = serializer.save()
        return Response(LoanSerializer(loan).data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def loan_delete_api(request, pk):
    """Delete loan"""
    # Only Admin can delete loans
    from app.views.admin.helpers import is_admin
    if not is_admin(request.user):
        return Response(
            {'error': 'Access denied. Only Admin can delete loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    loan = get_object_or_404(Loan, pk=pk)
    loan.delete()
    return Response({'message': 'Loan deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_details_api(request, pk):
    """API endpoint to get loan details with interest payment summary"""
    loan = get_object_or_404(Loan, pk=pk)
    
    # Members can only see their own loans
    if is_member(request.user) and loan.user.id != request.user.id:
        return Response(
            {'error': 'Access denied. You can only view your own loans.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get all interest payments for this loan
    interest_payments = loan.interest_payments.all()
    total_payments = interest_payments.count()
    paid_payments = interest_payments.filter(payment_status=PaymentStatus.PAID).count()
    pending_payments = interest_payments.filter(payment_status=PaymentStatus.PENDING).count()
    
    # Calculate totals
    from decimal import Decimal
    total_paid_interest = sum(payment.amount for payment in interest_payments.filter(payment_status=PaymentStatus.PAID))
    total_interest = sum(payment.amount for payment in interest_payments)
    
    # Get first pending payment
    first_pending_payment = interest_payments.filter(payment_status=PaymentStatus.PENDING).order_by('-paid_date').first()
    
    # Get all payments for this loan (for dropdown)
    all_payments = interest_payments.order_by('-paid_date')
    
    from app.serializers import LoanInterestPaymentSerializer
    payments_serializer = LoanInterestPaymentSerializer(all_payments, many=True)
    
    data = {
        'loan': LoanSerializer(loan).data,
        'payments': {
            'total': total_payments,
            'paid': paid_payments,
            'pending': pending_payments,
        },
        'amounts': {
            'total_payable': str(loan.total_payable),
            'total_paid_interest': str(total_paid_interest),
            'total_interest': str(total_interest),
        },
        'first_pending_payment': {
            'id': first_pending_payment.id if first_pending_payment else None,
            'paid_date': str(first_pending_payment.paid_date) if first_pending_payment else None,
            'amount': str(first_pending_payment.amount) if first_pending_payment else None,
        },
        'all_payments': payments_serializer.data,
    }
    
    return Response(data, status=status.HTTP_200_OK)
