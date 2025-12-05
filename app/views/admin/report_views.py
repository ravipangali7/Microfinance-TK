from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from app.models import (
    MonthlyMembershipDeposit, Loan, LoanInterestPayment, LoanPrinciplePayment,
    User, PaymentTransaction, MySetting, PaymentStatus, LoanStatus
)
from .helpers import get_role_context


@login_required
def membership_deposit_report(request):
    """Membership Deposit Report with date range filter"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Default to last 30 days if no dates provided
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date().isoformat()
    if not to_date:
        to_date = timezone.now().date().isoformat()
    
    # Parse dates
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date_obj = (timezone.now() - timedelta(days=30)).date()
        to_date_obj = timezone.now().date()
    
    # Query deposits within date range
    deposits = MonthlyMembershipDeposit.objects.filter(
        date__gte=from_date_obj,
        date__lte=to_date_obj
    ).select_related('user', 'membership').order_by('-date', '-created_at')
    
    # Calculate summary statistics
    total_paid = deposits.filter(payment_status=PaymentStatus.PAID).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_pending = deposits.filter(payment_status=PaymentStatus.PENDING).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_count = deposits.count()
    paid_count = deposits.filter(payment_status=PaymentStatus.PAID).count()
    pending_count = deposits.filter(payment_status=PaymentStatus.PENDING).count()
    
    avg_amount = deposits.aggregate(
        avg=Coalesce(Avg('amount'), Decimal('0.00'), output_field=DecimalField())
    )['avg'] or Decimal('0.00')
    
    # Deposits by membership type
    deposits_by_membership = deposits.values('membership__name').annotate(
        count=Count('id'),
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-total')
    
    context = {
        'deposits': deposits,
        'from_date': from_date,
        'to_date': to_date,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'total_count': total_count,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'avg_amount': avg_amount,
        'deposits_by_membership': deposits_by_membership,
    }
    context.update(get_role_context(request))
    return render(request, 'core/reports/membership_deposit_report.html', context)


@login_required
def loan_report(request):
    """Loan Report with date range filter"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Default to last 30 days if no dates provided
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date().isoformat()
    if not to_date:
        to_date = timezone.now().date().isoformat()
    
    # Parse dates
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date_obj = (timezone.now() - timedelta(days=30)).date()
        to_date_obj = timezone.now().date()
    
    # Query loans within date range (based on applied_date)
    loans = Loan.objects.filter(
        applied_date__gte=from_date_obj,
        applied_date__lte=to_date_obj
    ).select_related('user', 'action_by').prefetch_related('interest_payments', 'principle_payments').order_by('-applied_date', '-created_at')
    
    # Calculate summary statistics
    total_principal = loans.aggregate(
        total=Coalesce(Sum('principal_amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_payable = loans.aggregate(
        total=Coalesce(Sum('total_payable'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_interest = total_payable - total_principal
    
    # Calculate total paid principal
    total_paid_principal = Decimal('0.00')
    total_remaining_principal = Decimal('0.00')
    for loan in loans:
        total_paid_principal += loan.get_total_paid_principle()
        total_remaining_principal += loan.get_remaining_principle()
    
    avg_loan_amount = loans.aggregate(
        avg=Coalesce(Avg('principal_amount'), Decimal('0.00'), output_field=DecimalField())
    )['avg'] or Decimal('0.00')
    
    # Loans by status
    loans_by_status = loans.values('status').annotate(
        count=Count('id'),
        total=Coalesce(Sum('principal_amount'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-count')
    
    active_loans_count = loans.filter(status=LoanStatus.ACTIVE).count()
    
    context = {
        'loans': loans,
        'from_date': from_date,
        'to_date': to_date,
        'total_principal': total_principal,
        'total_payable': total_payable,
        'total_interest': total_interest,
        'total_paid_principal': total_paid_principal,
        'total_remaining_principal': total_remaining_principal,
        'avg_loan_amount': avg_loan_amount,
        'loans_by_status': loans_by_status,
        'active_loans_count': active_loans_count,
    }
    context.update(get_role_context(request))
    return render(request, 'core/reports/loan_report.html', context)


@login_required
def user_report(request):
    """User Report with user filter and date range filter"""
    user_id = request.GET.get('user_id')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Default to last 30 days if no dates provided
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date().isoformat()
    if not to_date:
        to_date = timezone.now().date().isoformat()
    
    # Parse dates
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date_obj = (timezone.now() - timedelta(days=30)).date()
        to_date_obj = timezone.now().date()
    
    # Get all users for dropdown
    all_users = User.objects.all().order_by('name')
    
    user = None
    deposits = MonthlyMembershipDeposit.objects.none()
    loans = Loan.objects.none()
    interest_payments = LoanInterestPayment.objects.none()
    principle_payments = LoanPrinciplePayment.objects.none()
    
    # Summary statistics
    total_deposits_paid = Decimal('0.00')
    total_deposits_pending = Decimal('0.00')
    total_loans_count = 0
    total_loans_amount = Decimal('0.00')
    active_loans_count = 0
    completed_loans_count = 0
    total_interest_paid = Decimal('0.00')
    total_principal_paid = Decimal('0.00')
    
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
            
            # Get deposits within date range
            deposits = MonthlyMembershipDeposit.objects.filter(
                user=user,
                date__gte=from_date_obj,
                date__lte=to_date_obj
            ).select_related('membership').order_by('-date', '-created_at')
            
            # Get loans within date range
            loans = Loan.objects.filter(
                user=user,
                applied_date__gte=from_date_obj,
                applied_date__lte=to_date_obj
            ).select_related('action_by').prefetch_related('interest_payments', 'principle_payments').order_by('-applied_date', '-created_at')
            
            # Get interest payments within date range
            interest_payments = LoanInterestPayment.objects.filter(
                loan__user=user,
                paid_date__gte=from_date_obj,
                paid_date__lte=to_date_obj
            ).select_related('loan').order_by('-paid_date', '-created_at')
            
            # Get principle payments within date range
            principle_payments = LoanPrinciplePayment.objects.filter(
                loan__user=user,
                paid_date__gte=from_date_obj,
                paid_date__lte=to_date_obj
            ).select_related('loan').order_by('-paid_date', '-created_at')
            
            # Calculate summary statistics
            total_deposits_paid = deposits.filter(payment_status=PaymentStatus.PAID).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            
            total_deposits_pending = deposits.filter(payment_status=PaymentStatus.PENDING).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            
            total_loans_count = loans.count()
            total_loans_amount = loans.aggregate(
                total=Coalesce(Sum('principal_amount'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            
            active_loans_count = loans.filter(status=LoanStatus.ACTIVE).count()
            completed_loans_count = loans.filter(status=LoanStatus.COMPLETED).count()
            
            total_interest_paid = interest_payments.filter(payment_status=PaymentStatus.PAID).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            
            total_principal_paid = principle_payments.filter(payment_status=PaymentStatus.PAID).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            
        except User.DoesNotExist:
            pass
    
    context = {
        'user': user,
        'all_users': all_users,
        'user_id': user_id,
        'from_date': from_date,
        'to_date': to_date,
        'deposits': deposits,
        'loans': loans,
        'interest_payments': interest_payments,
        'principle_payments': principle_payments,
        'total_deposits_paid': total_deposits_paid,
        'total_deposits_pending': total_deposits_pending,
        'total_loans_count': total_loans_count,
        'total_loans_amount': total_loans_amount,
        'active_loans_count': active_loans_count,
        'completed_loans_count': completed_loans_count,
        'total_interest_paid': total_interest_paid,
        'total_principal_paid': total_principal_paid,
    }
    context.update(get_role_context(request))
    return render(request, 'core/reports/user_report.html', context)


@login_required
def main_report(request):
    """Main System Report with date range filter"""
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Default to last 30 days if no dates provided
    if not from_date:
        from_date = (timezone.now() - timedelta(days=30)).date().isoformat()
    if not to_date:
        to_date = timezone.now().date().isoformat()
    
    # Parse dates
    try:
        from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
        to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        from_date_obj = (timezone.now() - timedelta(days=30)).date()
        to_date_obj = timezone.now().date()
    
    # Get system balance
    settings = MySetting.get_settings()
    system_balance = settings.balance
    
    # Calculate summary statistics
    # Total membership deposits (paid) within date range
    total_deposits_paid = MonthlyMembershipDeposit.objects.filter(
        payment_status=PaymentStatus.PAID,
        date__gte=from_date_obj,
        date__lte=to_date_obj
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Total loans disbursed (active loans) within date range
    total_loans_disbursed = Loan.objects.filter(
        status=LoanStatus.ACTIVE,
        disbursed_date__gte=from_date_obj,
        disbursed_date__lte=to_date_obj
    ).aggregate(
        total=Coalesce(Sum('principal_amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Total interest collected within date range
    total_interest_collected = LoanInterestPayment.objects.filter(
        payment_status=PaymentStatus.PAID,
        paid_date__gte=from_date_obj,
        paid_date__lte=to_date_obj
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Total principal collected within date range
    total_principal_collected = LoanPrinciplePayment.objects.filter(
        payment_status=PaymentStatus.PAID,
        paid_date__gte=from_date_obj,
        paid_date__lte=to_date_obj
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Total active users
    total_active_users = User.objects.filter(status='active').count()
    
    # Total active loans
    total_active_loans = Loan.objects.filter(status=LoanStatus.ACTIVE).count()
    
    # Total pending deposits
    total_pending_deposits = MonthlyMembershipDeposit.objects.filter(
        payment_status=PaymentStatus.PENDING
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Total pending payments (interest + principle)
    total_pending_interest = LoanInterestPayment.objects.filter(
        payment_status=PaymentStatus.PENDING
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_pending_principle = LoanPrinciplePayment.objects.filter(
        payment_status=PaymentStatus.PENDING
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_pending_payments = total_pending_interest + total_pending_principle
    total_pending_all = total_pending_deposits + total_pending_payments
    
    # Top users by deposits (within date range)
    top_users_by_deposits = User.objects.filter(
        monthly_membership_deposits__date__gte=from_date_obj,
        monthly_membership_deposits__date__lte=to_date_obj,
        monthly_membership_deposits__payment_status=PaymentStatus.PAID
    ).annotate(
        total_deposits=Coalesce(Sum('monthly_membership_deposits__amount'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('-total_deposits')[:10]
    
    # Top users by loans (within date range)
    top_users_by_loans = User.objects.filter(
        loans__applied_date__gte=from_date_obj,
        loans__applied_date__lte=to_date_obj
    ).annotate(
        total_loans=Coalesce(Sum('loans__principal_amount'), Decimal('0.00'), output_field=DecimalField()),
        loans_count=Count('loans')
    ).order_by('-total_loans')[:10]
    
    # Recent transactions summary (last 10)
    recent_transactions = PaymentTransaction.objects.filter(
        txn_date__gte=from_date_obj,
        txn_date__lte=to_date_obj
    ).select_related('user').order_by('-txn_date', '-created_at')[:10]
    
    context = {
        'from_date': from_date,
        'to_date': to_date,
        'system_balance': system_balance,
        'total_deposits_paid': total_deposits_paid,
        'total_loans_disbursed': total_loans_disbursed,
        'total_interest_collected': total_interest_collected,
        'total_principal_collected': total_principal_collected,
        'total_active_users': total_active_users,
        'total_active_loans': total_active_loans,
        'total_pending_deposits': total_pending_deposits,
        'total_pending_payments': total_pending_payments,
        'total_pending_all': total_pending_all,
        'top_users_by_deposits': top_users_by_deposits,
        'top_users_by_loans': top_users_by_loans,
        'recent_transactions': recent_transactions,
    }
    context.update(get_role_context(request))
    return render(request, 'core/reports/main_report.html', context)

