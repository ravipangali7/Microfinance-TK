from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from app.models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, FundManagement, MySetting,
    UserStatus, LoanStatus, PaymentStatus, WithdrawalStatus
)
from app.views.admin.helpers import is_member
from app.serializers import (
    UserSerializer, MonthlyMembershipDepositSerializer,
    LoanSerializer, FundManagementSerializer,
    LoanInterestPaymentSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    """Dashboard API with comprehensive microfinance statistics"""
    
    user = request.user
    is_member_user = is_member(user)
    
    # Date ranges
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Base querysets - filter by user role
    user_queryset = User.objects.all()
    membership_deposit_queryset = MonthlyMembershipDeposit.objects.all()
    loan_queryset = Loan.objects.all()
    fund_management_queryset = FundManagement.objects.all()
    interest_payment_queryset = LoanInterestPayment.objects.all()
    
    # Get total users count (all users including all roles) - needed for My Share calculation
    total_users_all = User.objects.count()
    
    # Filter for Member users (only own data)
    if is_member_user:
        user_queryset = User.objects.filter(id=user.id)
        membership_deposit_queryset = MonthlyMembershipDeposit.objects.filter(user=user)
        loan_queryset = Loan.objects.filter(user=user)
        interest_payment_queryset = LoanInterestPayment.objects.filter(loan__user=user)
    
    # User Statistics
    # For members, return total_users_all so they can calculate their share
    # For admin/board/staff, return filtered count
    total_users = total_users_all if is_member_user else user_queryset.count()
    active_users = user_queryset.filter(status=UserStatus.ACTIVE).count() if not is_member_user else 0
    inactive_users = user_queryset.filter(status=UserStatus.INACTIVE).count() if not is_member_user else 0
    frozen_users = user_queryset.filter(status=UserStatus.FREEZE).count() if not is_member_user else 0
    
    # Get system balance from MySetting
    try:
        settings = MySetting.get_settings()
        total_balance = settings.balance
    except:
        total_balance = Decimal('0.00')
    
    # Membership Deposit Statistics
    total_deposits_amount = membership_deposit_queryset.filter(
        payment_status=PaymentStatus.PAID
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_deposits_count = membership_deposit_queryset.count()
    deposits_last_7_days = membership_deposit_queryset.filter(
        date__gte=last_7_days,
        payment_status=PaymentStatus.PAID
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    deposits_last_30_days = membership_deposit_queryset.filter(
        date__gte=last_30_days,
        payment_status=PaymentStatus.PAID
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    recent_deposits = membership_deposit_queryset.select_related('user', 'membership').order_by('-date', '-created_at')[:10]
    
    # Loan Statistics
    total_loans = loan_queryset.count()
    loans_pending = loan_queryset.filter(status=LoanStatus.PENDING).count()
    loans_approved = loan_queryset.filter(status=LoanStatus.APPROVED).count()
    loans_active = loan_queryset.filter(status=LoanStatus.ACTIVE).count()
    loans_completed = loan_queryset.filter(status=LoanStatus.COMPLETED).count()
    loans_default = loan_queryset.filter(status=LoanStatus.DEFAULT).count()
    loans_rejected = loan_queryset.filter(status=LoanStatus.REJECTED).count()
    
    total_principal = loan_queryset.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    total_payable = loan_queryset.aggregate(total=Sum('total_payable'))['total'] or Decimal('0.00')
    
    # Outstanding loans (active loans)
    outstanding_loans_amount = loan_queryset.filter(status=LoanStatus.ACTIVE).aggregate(
        total=Sum('total_payable')
    )['total'] or Decimal('0.00')
    
    # Loans disbursed (approved + active + completed)
    loans_disbursed = loan_queryset.filter(
        status__in=[LoanStatus.APPROVED, LoanStatus.ACTIVE, LoanStatus.COMPLETED]
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    
    loans_last_7_days = loan_queryset.filter(applied_date__gte=last_7_days).aggregate(
        total=Sum('principal_amount')
    )['total'] or Decimal('0.00')
    loans_last_30_days = loan_queryset.filter(applied_date__gte=last_30_days).aggregate(
        total=Sum('principal_amount')
    )['total'] or Decimal('0.00')
    
    recent_loans = loan_queryset.select_related('user').order_by('-applied_date', '-created_at')[:10]
    
    # Fund Management Statistics
    total_fund_management = fund_management_queryset.count()
    fund_management_pending = fund_management_queryset.filter(status=WithdrawalStatus.PENDING).count()
    fund_management_approved = fund_management_queryset.filter(status=WithdrawalStatus.APPROVED).count()
    fund_management_rejected = fund_management_queryset.filter(status=WithdrawalStatus.REJECTED).count()
    total_fund_management_amount = fund_management_queryset.filter(status=WithdrawalStatus.APPROVED).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    pending_fund_management_amount = fund_management_queryset.filter(status=WithdrawalStatus.PENDING).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    recent_fund_management = fund_management_queryset.order_by('-date', '-created_at')[:10]
    
    # Interest Payment Statistics
    total_interest_payments = interest_payment_queryset.count()
    interest_payments_pending = interest_payment_queryset.filter(payment_status=PaymentStatus.PENDING).count()
    interest_payments_paid = interest_payment_queryset.filter(payment_status=PaymentStatus.PAID).count()
    
    total_paid_interest = interest_payment_queryset.filter(payment_status=PaymentStatus.PAID).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    recent_interest_payments = interest_payment_queryset.select_related(
        'loan', 'loan__user'
    ).order_by('-paid_date', '-created_at')[:10]
    
    # Loan Status Distribution for Pie Chart
    loan_status_data = {
        'pending': loans_pending,
        'approved': loans_approved,
        'active': loans_active,
        'completed': loans_completed,
        'default': loans_default,
        'rejected': loans_rejected,
    }
    
    # Time-based data for charts (last 30 days)
    chart_data = []
    for i in range(30):
        date = today - timedelta(days=29-i)
        deposits_day = membership_deposit_queryset.filter(
            date=date,
            payment_status=PaymentStatus.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        loans_day = loan_queryset.filter(applied_date=date).aggregate(
            total=Sum('principal_amount')
        )['total'] or Decimal('0.00')
        chart_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'deposits': float(deposits_day),
            'loans': float(loans_day),
        })
    
    # Monthly data (last 12 months)
    monthly_data = []
    for i in range(12):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        if month_start.day != 1:
            month_start = month_start.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        deposits_month = membership_deposit_queryset.filter(
            date__gte=month_start,
            date__lte=month_end,
            payment_status=PaymentStatus.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        loans_month = loan_queryset.filter(
            applied_date__gte=month_start,
            applied_date__lte=month_end
        ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'deposits': float(deposits_month),
            'loans': float(loans_month),
        })
    monthly_data.reverse()
    
    # Serialize recent items
    recent_deposits_serialized = MonthlyMembershipDepositSerializer(recent_deposits, many=True).data
    recent_loans_serialized = LoanSerializer(recent_loans, many=True).data
    recent_fund_management_serialized = FundManagementSerializer(recent_fund_management, many=True).data
    recent_interest_payments_serialized = LoanInterestPaymentSerializer(recent_interest_payments, many=True).data
    
    data = {
        # User Statistics
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'frozen_users': frozen_users,
        'total_balance': str(total_balance),
        
        # Membership Deposit Statistics
        'total_deposits_amount': str(total_deposits_amount),
        'total_deposits_count': total_deposits_count,
        'deposits_last_7_days': str(deposits_last_7_days),
        'deposits_last_30_days': str(deposits_last_30_days),
        'recent_deposits': recent_deposits_serialized,
        
        # Loan Statistics
        'total_loans': total_loans,
        'loans_pending': loans_pending,
        'loans_approved': loans_approved,
        'loans_active': loans_active,
        'loans_completed': loans_completed,
        'loans_default': loans_default,
        'loans_rejected': loans_rejected,
        'total_principal': str(total_principal),
        'total_payable': str(total_payable),
        'outstanding_loans_amount': str(outstanding_loans_amount),
        'loans_disbursed': str(loans_disbursed),
        'loans_last_7_days': str(loans_last_7_days),
        'loans_last_30_days': str(loans_last_30_days),
        'recent_loans': recent_loans_serialized,
        'loan_status_data': loan_status_data,
        
        # Fund Management Statistics
        'total_fund_management': total_fund_management,
        'fund_management_pending': fund_management_pending,
        'fund_management_approved': fund_management_approved,
        'fund_management_rejected': fund_management_rejected,
        'total_fund_management_amount': str(total_fund_management_amount),
        'pending_fund_management_amount': str(pending_fund_management_amount),
        'recent_fund_management': recent_fund_management_serialized,
        
        # Interest Payment Statistics
        'total_interest_payments': total_interest_payments,
        'interest_payments_pending': interest_payments_pending,
        'interest_payments_paid': interest_payments_paid,
        'total_paid_interest': str(total_paid_interest),
        'recent_interest_payments': recent_interest_payments_serialized,
        
        # Chart Data
        'chart_data': chart_data,
        'monthly_data': monthly_data,
    }
    
    return Response(data, status=status.HTTP_200_OK)

