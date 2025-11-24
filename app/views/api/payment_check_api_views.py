from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, 
    MembershipUser, Loan, MySetting, PaymentStatus, LoanStatus
)
from decimal import Decimal


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_check_api(request):
    """
    Check for missing deposit and interest payments for the authenticated user.
    Returns missing payments for the last 3 months.
    """
    user = request.user
    today = timezone.now().date()
    settings = MySetting.get_settings()
    
    # Get configured dates
    deposit_date = settings.membership_deposit_date
    interest_date = settings.loan_interest_payment_date
    
    # Calculate check start date (3 days before configured date)
    deposit_check_start = max(1, deposit_date - 3)
    interest_check_start = max(1, interest_date - 3)
    
    missing_deposits = []
    missing_interest_payments = []
    
    # Get user's memberships
    user_memberships = MembershipUser.objects.filter(user=user).select_related('membership')
    
    # Check deposits for last 3 months
    for i in range(3):
        # Calculate date for i months ago
        if i == 0:
            check_date = today
            check_month = today.month
            check_year = today.year
            # For current month, only check if we're past the check start date
            if today.day < deposit_check_start:
                continue
        else:
            # Subtract months manually
            check_year = today.year
            check_month = today.month - i
            while check_month <= 0:
                check_month += 12
                check_year -= 1
            check_date = datetime(check_year, check_month, 1).date()
        
        # For each membership, check if deposit exists for this month
        for membership_user in user_memberships:
            membership = membership_user.membership
            
            # Check if paid deposit exists for this month/year
            deposits = MonthlyMembershipDeposit.objects.filter(
                user=user,
                membership=membership,
                date__year=check_year,
                date__month=check_month,
                payment_status=PaymentStatus.PAID  # Only consider paid deposits
            )
            
            if not deposits.exists():
                # No deposit found for this month
                # Calculate the date for this payment (configured day of that month)
                try:
                    last_day = monthrange(check_year, check_month)[1]
                    payment_date = datetime(check_year, check_month, min(deposit_date, last_day)).date()
                except ValueError:
                    # If day doesn't exist, use last day of month
                    last_day = monthrange(check_year, check_month)[1]
                    payment_date = datetime(check_year, check_month, last_day).date()
                
                missing_deposits.append({
                    'membership_id': membership.id,
                    'membership_name': membership.name,
                    'amount': float(membership.amount),
                    'month': check_month,
                    'year': check_year,
                    'payment_date': payment_date.isoformat(),
                })
    
    # Get user's active loans (only ACTIVE loans, not APPROVED)
    user_loans = Loan.objects.filter(
        user=user,
        status=LoanStatus.ACTIVE
    )
    
    # For each active loan, determine start date and check interest payments
    for loan in user_loans:
        # Determine loan start date: use disbursed_date if available, otherwise applied_date
        loan_start_date = loan.disbursed_date if loan.disbursed_date else loan.applied_date
        if not loan_start_date:
            # Skip if no start date
            continue
        
        loan_start_month = loan_start_date.month
        loan_start_year = loan_start_date.year
        
        # Calculate how many months to check
        # If loan started 3+ months ago: check last 3 months
        # If loan started < 3 months ago: check from start date to today
        months_since_start = (today.year - loan_start_year) * 12 + (today.month - loan_start_month)
        
        if months_since_start < 0:
            # Loan hasn't started yet (future date)
            continue
        
        # Determine how many months to check back
        if months_since_start >= 3:
            # Loan started 3+ months ago: check last 3 months
            months_to_check = 3
        else:
            # Loan started < 3 months ago: check from start to today
            months_to_check = months_since_start + 1  # +1 to include current month
        
        # Check interest payments for the determined months
        for i in range(months_to_check):
            # Calculate date for i months ago
            if i == 0:
                check_month = today.month
                check_year = today.year
                # For current month, only check if we're past the check start date
                if today.day < interest_check_start:
                    continue
            else:
                # Subtract months manually
                check_year = today.year
                check_month = today.month - i
                while check_month <= 0:
                    check_month += 12
                    check_year -= 1
            
            # Only check months that are >= loan start month
            check_date_obj = datetime(check_year, check_month, 1).date()
            if check_date_obj < datetime(loan_start_year, loan_start_month, 1).date():
                # This month is before loan started, skip
                continue
            
            # Check if interest payment exists for this month/year
            payments = LoanInterestPayment.objects.filter(
                loan=loan,
                paid_date__year=check_year,
                paid_date__month=check_month,
                payment_status=PaymentStatus.PAID  # Only consider paid payments
            )
            
            if not payments.exists():
                # No paid payment found for this month
                # Calculate interest amount (monthly interest based on principal and rate)
                monthly_interest = (loan.principal_amount * loan.interest_rate / 100) / 12
                
                # Calculate the date for this payment (configured day of that month)
                try:
                    last_day = monthrange(check_year, check_month)[1]
                    payment_date = datetime(check_year, check_month, min(interest_date, last_day)).date()
                except ValueError:
                    # If day doesn't exist, use last day of month
                    last_day = monthrange(check_year, check_month)[1]
                    payment_date = datetime(check_year, check_month, last_day).date()
                
                missing_interest_payments.append({
                    'loan_id': loan.id,
                    'loan_principal': float(loan.principal_amount),
                    'interest_rate': float(loan.interest_rate),
                    'amount': float(monthly_interest),
                    'month': check_month,
                    'year': check_year,
                    'payment_date': payment_date.isoformat(),
                })
    
    return Response({
        'missing_deposits': missing_deposits,
        'missing_interest_payments': missing_interest_payments,
    }, status=status.HTTP_200_OK)

