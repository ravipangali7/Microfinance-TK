from django.shortcuts import render
from django.db.models import Sum
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from decimal import Decimal
import json
from app.models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, PaymentTransaction,
    OrganizationalWithdrawal, MySetting,
    UserStatus, LoanStatus, PaymentStatus, WithdrawalStatus
)
from .helpers import is_member, get_role_context


@login_required
def dashboard_view(request):
    """Dashboard view with comprehensive microfinance statistics"""
    
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
    withdrawal_queryset = OrganizationalWithdrawal.objects.all()
    interest_payment_queryset = LoanInterestPayment.objects.all()
    principle_payment_queryset = LoanPrinciplePayment.objects.all()
    payment_transaction_queryset = PaymentTransaction.objects.all()
    
    # Filter for Member users (only own data)
    if is_member_user:
        user_queryset = User.objects.filter(id=user.id)
        membership_deposit_queryset = MonthlyMembershipDeposit.objects.filter(user=user)
        loan_queryset = Loan.objects.filter(user=user)
        interest_payment_queryset = LoanInterestPayment.objects.filter(loan__user=user)
        principle_payment_queryset = LoanPrinciplePayment.objects.filter(loan__user=user)
        payment_transaction_queryset = PaymentTransaction.objects.filter(user=user)
    
    # User Statistics (only for Admin/Board/Staff)
    total_users = user_queryset.count() if not is_member_user else 0
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
    
    # Organizational Withdrawal Statistics
    total_withdrawals = withdrawal_queryset.count()
    withdrawals_pending = withdrawal_queryset.filter(status=WithdrawalStatus.PENDING).count()
    withdrawals_approved = withdrawal_queryset.filter(status=WithdrawalStatus.APPROVED).count()
    withdrawals_rejected = withdrawal_queryset.filter(status=WithdrawalStatus.REJECTED).count()
    total_withdrawals_amount = withdrawal_queryset.filter(status=WithdrawalStatus.APPROVED).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    pending_withdrawals_amount = withdrawal_queryset.filter(status=WithdrawalStatus.PENDING).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    recent_withdrawals = withdrawal_queryset.order_by('-date', '-created_at')[:10]
    
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
    
    # Loan Principle Payment Statistics
    total_principle_payments = principle_payment_queryset.count()
    principle_payments_pending = principle_payment_queryset.filter(payment_status=PaymentStatus.PENDING).count()
    principle_payments_paid = principle_payment_queryset.filter(payment_status=PaymentStatus.PAID).count()
    
    total_paid_principle = principle_payment_queryset.filter(payment_status=PaymentStatus.PAID).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    recent_principle_payments = principle_payment_queryset.select_related(
        'loan', 'loan__user'
    ).order_by('-paid_date', '-created_at')[:10]
    
    # Payment Transaction Statistics (only for Admin/Board/Staff)
    if not is_member_user:
        total_payment_transactions = payment_transaction_queryset.count()
        transactions_success = payment_transaction_queryset.filter(status='success').count()
        transactions_pending = payment_transaction_queryset.filter(status='pending').count()
        transactions_failed = payment_transaction_queryset.filter(status='failed').count()
        transactions_cancelled = payment_transaction_queryset.filter(status='cancelled').count()
        
        total_transaction_amount = payment_transaction_queryset.filter(status='success').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        transactions_last_7_days = payment_transaction_queryset.filter(
            created_at__date__gte=last_7_days,
            status='success'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        transactions_last_30_days = payment_transaction_queryset.filter(
            created_at__date__gte=last_30_days,
            status='success'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        recent_payment_transactions = payment_transaction_queryset.select_related('user').order_by('-created_at')[:10]
    else:
        total_payment_transactions = 0
        transactions_success = 0
        transactions_pending = 0
        transactions_failed = 0
        transactions_cancelled = 0
        total_transaction_amount = Decimal('0.00')
        transactions_last_7_days = Decimal('0.00')
        transactions_last_30_days = Decimal('0.00')
        recent_payment_transactions = []
    
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
    
    # Get role context
    role_context = get_role_context(request)
    
    context = {
        # User Statistics
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'frozen_users': frozen_users,
        'total_balance': total_balance,
        
        # Membership Deposit Statistics
        'total_deposits_amount': total_deposits_amount,
        'total_deposits_count': total_deposits_count,
        'deposits_last_7_days': deposits_last_7_days,
        'deposits_last_30_days': deposits_last_30_days,
        'recent_deposits': recent_deposits,
        
        # Loan Statistics
        'total_loans': total_loans,
        'loans_pending': loans_pending,
        'loans_approved': loans_approved,
        'loans_active': loans_active,
        'loans_completed': loans_completed,
        'loans_default': loans_default,
        'loans_rejected': loans_rejected,
        'total_principal': total_principal,
        'total_payable': total_payable,
        'outstanding_loans_amount': outstanding_loans_amount,
        'loans_disbursed': loans_disbursed,
        'loans_last_7_days': loans_last_7_days,
        'loans_last_30_days': loans_last_30_days,
        'recent_loans': recent_loans,
        'loan_status_data': loan_status_data,
        
        # Withdrawal Statistics
        'total_withdrawals': total_withdrawals,
        'withdrawals_pending': withdrawals_pending,
        'withdrawals_approved': withdrawals_approved,
        'withdrawals_rejected': withdrawals_rejected,
        'total_withdrawals_amount': total_withdrawals_amount,
        'pending_withdrawals_amount': pending_withdrawals_amount,
        'recent_withdrawals': recent_withdrawals,
        
        # Interest Payment Statistics
        'total_interest_payments': total_interest_payments,
        'interest_payments_pending': interest_payments_pending,
        'interest_payments_paid': interest_payments_paid,
        'total_paid_interest': total_paid_interest,
        'recent_interest_payments': recent_interest_payments,
        
        # Principle Payment Statistics
        'total_principle_payments': total_principle_payments,
        'principle_payments_pending': principle_payments_pending,
        'principle_payments_paid': principle_payments_paid,
        'total_paid_principle': total_paid_principle,
        'recent_principle_payments': recent_principle_payments,
        
        # Payment Transaction Statistics
        'total_payment_transactions': total_payment_transactions,
        'transactions_success': transactions_success,
        'transactions_pending': transactions_pending,
        'transactions_failed': transactions_failed,
        'transactions_cancelled': transactions_cancelled,
        'total_transaction_amount': total_transaction_amount,
        'transactions_last_7_days': transactions_last_7_days,
        'transactions_last_30_days': transactions_last_30_days,
        'recent_payment_transactions': recent_payment_transactions,
        
        # Chart Data (JSON serialized)
        'chart_data': mark_safe(json.dumps(chart_data)),
        'monthly_data': mark_safe(json.dumps(monthly_data)),
    }
    
    # Add role context variables
    context.update(role_context)
    
    return render(request, 'core/dashboard.html', context)

