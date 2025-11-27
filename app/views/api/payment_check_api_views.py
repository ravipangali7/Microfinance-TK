from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime
from calendar import monthrange
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, 
    MembershipUser, Loan, MySetting, PaymentStatus, LoanStatus
)
from decimal import Decimal


def should_include_current_month(today, payment_due_date):
    """
    Determine if current month should be included based on day logic.
    If today.day < 5 and payment_due_date >= 10, skip current month.
    If today.day >= 5, include current month.
    """
    if today.day < 5 and payment_due_date >= 10:
        return False
    return True


def get_months_between(start_date, end_date):
    """
    Generate all months between start_date and end_date (inclusive).
    Returns list of (year, month) tuples.
    """
    months = []
    current = datetime(start_date.year, start_date.month, 1).date()
    end = datetime(end_date.year, end_date.month, 1).date()
    
    while current <= end:
        months.append((current.year, current.month))
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1).date()
        else:
            current = datetime(current.year, current.month + 1, 1).date()
    
    return months


def get_months_back_3_at_a_time(today, start_date):
    """
    Get all months going back 3 months at a time from today until reaching start_date.
    Returns list of (year, month) tuples in reverse chronological order.
    This checks all months but processes them in batches of 3.
    """
    months = []
    start = datetime(start_date.year, start_date.month, 1).date()
    
    # Start from current month and go back month by month
    check_year = today.year
    check_month = today.month
    
    while True:
        check_date = datetime(check_year, check_month, 1).date()
        
        # Stop if we've gone before the start date
        if check_date < start:
            break
        
        months.append((check_year, check_month))
        
        # Move to previous month
        if check_month == 1:
            check_month = 12
            check_year -= 1
        else:
            check_month -= 1
    
    return months


def is_deposit_unpaid(user, membership, check_year, check_month):
    """
    Check if deposit is unpaid for given month/year.
    Returns True if:
    - There's a pending deposit for that month/year, OR
    - No paid deposit exists for that month/year
    """
    # Check for pending deposits
    pending_deposits = MonthlyMembershipDeposit.objects.filter(
        user=user,
        membership=membership,
        date__year=check_year,
        date__month=check_month,
        payment_status=PaymentStatus.PENDING
    )
    
    if pending_deposits.exists():
        return True
    
    # Check if no paid deposit exists
    paid_deposits = MonthlyMembershipDeposit.objects.filter(
        user=user,
        membership=membership,
        date__year=check_year,
        date__month=check_month,
        payment_status=PaymentStatus.PAID
    )
    
    return not paid_deposits.exists()


def is_interest_payment_unpaid(loan, check_year, check_month):
    """
    Check if interest payment is unpaid for given month/year.
    Returns True if:
    - There's a pending payment for that month/year (with paid_date matching), OR
    - No paid payment exists for that month/year
    """
    # Check for pending payments with paid_date matching the month/year
    # (pending payments might have paid_date set even if not paid yet)
    pending_payments = LoanInterestPayment.objects.filter(
        loan=loan,
        paid_date__year=check_year,
        paid_date__month=check_month,
        payment_status=PaymentStatus.PENDING
    )
    
    if pending_payments.exists():
        return True
    
    # Check if no paid payment exists for this month/year
    paid_payments = LoanInterestPayment.objects.filter(
        loan=loan,
        paid_date__year=check_year,
        paid_date__month=check_month,
        payment_status=PaymentStatus.PAID
    )
    
    return not paid_payments.exists()


def calculate_payment_date(year, month, due_day):
    """
    Calculate payment date for given year/month with due_day.
    Handles edge cases like February 30th.
    """
    try:
        last_day = monthrange(year, month)[1]
        payment_date = datetime(year, month, min(due_day, last_day)).date()
    except ValueError:
        # If day doesn't exist, use last day of month
        last_day = monthrange(year, month)[1]
        payment_date = datetime(year, month, last_day).date()
    return payment_date


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_check_api(request):
    """
    Check for missing deposit and interest payments for the authenticated user.
    - Deposits: Start from MembershipUser.created_at, search back 3 months at a time if range > 3 months
    - Loan Interest: Start from Loan.created_at
    - Checks for both pending records and missing paid records
    - Current month logic: skip if today.day < 5 and payment_date >= 10
    """
    user = request.user
    today = timezone.now().date()
    settings = MySetting.get_settings()
    
    # Get configured dates
    deposit_date = settings.membership_deposit_date
    interest_date = settings.loan_interest_payment_date
    
    missing_deposits = []
    missing_interest_payments = []
    
    # Get user's memberships
    user_memberships = MembershipUser.objects.filter(user=user).select_related('membership')
    
    # Check deposits - start from MembershipUser.created_at
    for membership_user in user_memberships:
        membership = membership_user.membership
        created_at = membership_user.created_at.date() if membership_user.created_at else today
        
        # Calculate months from created_at to today
        months_from_start = (today.year - created_at.year) * 12 + (today.month - created_at.month)
        
        if months_from_start < 0:
            # Future date, skip
            continue
        
        # Determine months to check
        if months_from_start > 3:
            # Range > 3 months: search back 3 months at a time
            months_to_check = get_months_back_3_at_a_time(today, created_at)
        else:
            # Range <= 3 months: check all months from created_at to today
            months_to_check = get_months_between(created_at, today)
            # Reverse to go from most recent to oldest
            months_to_check = list(reversed(months_to_check))
        
        # Check each month
        for check_year, check_month in months_to_check:
            # Check if this is current month and should be skipped
            if check_year == today.year and check_month == today.month:
                if not should_include_current_month(today, deposit_date):
                    continue
            
            # Check if deposit is unpaid
            if is_deposit_unpaid(user, membership, check_year, check_month):
                payment_date = calculate_payment_date(check_year, check_month, deposit_date)
                
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
    
    # Check loan interest payments - start from Loan.created_at
    for loan in user_loans:
        # Use created_at as start date
        loan_start_date = loan.created_at.date() if loan.created_at else today
        
        if not loan_start_date:
            continue
        
        # Get all months from loan created_at to today
        months_to_check = get_months_between(loan_start_date, today)
        # Reverse to go from most recent to oldest
        months_to_check = list(reversed(months_to_check))
        
        # Check each month
        for check_year, check_month in months_to_check:
            # Check if this is current month and should be skipped
            if check_year == today.year and check_month == today.month:
                if not should_include_current_month(today, interest_date):
                    continue
            
            # Check if interest payment is unpaid
            if is_interest_payment_unpaid(loan, check_year, check_month):
                # Calculate interest amount (monthly interest based on principal and rate)
                monthly_interest = (loan.principal_amount * loan.interest_rate / 100) / 12
                payment_date = calculate_payment_date(check_year, check_month, interest_date)
                
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

