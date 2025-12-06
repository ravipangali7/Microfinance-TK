from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, 
    PaymentStatus, LoanStatus, Penalty, PenaltyType
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_check_api(request):
    """
    Get pending deposit, interest payments, and penalties for the authenticated user.
    Only returns payments with payment_status='pending' from the database.
    """
    user = request.user
    
    missing_deposits = []
    missing_interest_payments = []
    penalties = []
    
    # Get all pending deposits for the user
    pending_deposits = MonthlyMembershipDeposit.objects.filter(
        user=user,
        payment_status=PaymentStatus.PENDING
    ).select_related('membership').order_by('-date')
    
    for deposit in pending_deposits:
        missing_deposits.append({
            'membership_id': deposit.membership.id,
            'membership_name': deposit.membership.name,
            'amount': float(deposit.amount),
            'month': deposit.date.month,
            'year': deposit.date.year,
            'payment_date': deposit.date.isoformat(),
        })
    
    # Get all pending interest payments for user's loans
    # Only check active loans
    pending_interest_payments = LoanInterestPayment.objects.filter(
        loan__user=user,
        loan__status=LoanStatus.ACTIVE,
        payment_status=PaymentStatus.PENDING
    ).select_related('loan').order_by('-paid_date')
    
    for payment in pending_interest_payments:
        # Use paid_date if available, otherwise use a default
        if payment.paid_date:
            payment_date = payment.paid_date.isoformat()
            month = payment.paid_date.month
            year = payment.paid_date.year
        else:
            # Fallback if paid_date is not set
            payment_date = ''
            month = 1
            year = 2024
        
        missing_interest_payments.append({
            'loan_id': payment.loan.id,
            'loan_principal': float(payment.loan.principal_amount),
            'interest_rate': float(payment.loan.interest_rate),
            'amount': float(payment.amount),
            'month': month,
            'year': year,
            'payment_date': payment_date,
        })
    
    # Get all pending penalties for the user
    pending_penalties = Penalty.objects.filter(
        user=user,
        payment_status=PaymentStatus.PENDING
    ).order_by('-due_date')
    
    for penalty in pending_penalties:
        penalties.append({
            'penalty_id': penalty.id,
            'penalty_type': penalty.penalty_type,
            'amount': float(penalty.penalty_amount),
            'due_date': penalty.due_date.isoformat(),
            'month': penalty.due_date.month,
            'year': penalty.due_date.year,
            'month_number': penalty.month_number,
            'related_object_id': penalty.related_object_id,
            'related_object_type': penalty.related_object_type,
        })
    
    return Response({
        'missing_deposits': missing_deposits,
        'missing_interest_payments': missing_interest_payments,
        'penalties': penalties,
    }, status=status.HTTP_200_OK)
