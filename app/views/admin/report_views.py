from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta
from decimal import Decimal
import calendar
import json
from dateutil.relativedelta import relativedelta

from app.models import (
    MonthlyMembershipDeposit, Loan, LoanInterestPayment, LoanPrinciplePayment,
    User, PaymentTransaction, MySetting, PaymentStatus, LoanStatus,
    FundManagement, UserStatus, WithdrawalStatus, FundManagementType
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
    
    selected_user = None
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
            selected_user = User.objects.get(pk=user_id)
            
            # Get deposits within date range
            deposits = MonthlyMembershipDeposit.objects.filter(
                user=selected_user,
                date__gte=from_date_obj,
                date__lte=to_date_obj
            ).select_related('membership').order_by('-date', '-created_at')
            
            # Get loans within date range
            loans = Loan.objects.filter(
                user=selected_user,
                applied_date__gte=from_date_obj,
                applied_date__lte=to_date_obj
            ).select_related('action_by').prefetch_related('interest_payments', 'principle_payments').order_by('-applied_date', '-created_at')
            
            # Get interest payments within date range
            interest_payments = LoanInterestPayment.objects.filter(
                loan__user=selected_user,
                paid_date__gte=from_date_obj,
                paid_date__lte=to_date_obj
            ).select_related('loan').order_by('-paid_date', '-created_at')
            
            # Get principle payments within date range
            principle_payments = LoanPrinciplePayment.objects.filter(
                loan__user=selected_user,
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
        'selected_user': selected_user,
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


@login_required
def share_report(request):
    """Share Report showing monthly trends of total share and per-member share"""
    
    # Get current date and calculate months
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    
    # Calculate last 12 months
    months_data = []
    chart_data = []
    
    # Calculate monthly data for last 12 months
    for i in range(11, -1, -1):  # From 11 months ago to current month
        month_date = today - relativedelta(months=i)
        month_start = month_date.replace(day=1)
        # Get last day of month
        last_day = calendar.monthrange(month_date.year, month_date.month)[1]
        month_end = month_date.replace(day=last_day)
        
        # Calculate system balance at end of this month by summing all transactions
        # Income (adds to balance):
        # - Paid deposits
        total_deposits = MonthlyMembershipDeposit.objects.filter(
            payment_status=PaymentStatus.PAID,
            date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # - Paid interest payments
        total_interest = LoanInterestPayment.objects.filter(
            payment_status=PaymentStatus.PAID,
            paid_date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # - Paid principal payments (money coming back)
        total_principal = LoanPrinciplePayment.objects.filter(
            payment_status=PaymentStatus.PAID,
            paid_date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # - Approved fund management credits
        total_credits = FundManagement.objects.filter(
            type=FundManagementType.CREDIT,
            status=WithdrawalStatus.APPROVED,
            date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # Expenses (subtracts from balance):
        # - Loans disbursed (active loans with disbursed_date)
        total_loans_disbursed = Loan.objects.filter(
            disbursed_date__isnull=False,
            disbursed_date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('principal_amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # - Approved fund management debits
        total_debits = FundManagement.objects.filter(
            type=FundManagementType.DEBIT,
            status=WithdrawalStatus.APPROVED,
            date__lte=month_end
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # Calculate balance: deposits + interest + principal + credits - loans - debits
        # Starting from 0 and building up from all transactions
        month_balance = total_deposits + total_interest + total_principal + total_credits - total_loans_disbursed - total_debits
        
        # Count active members at end of this month
        active_members = User.objects.filter(
            status=UserStatus.ACTIVE,
            created_at__date__lte=month_end
        ).count()
        
        # Calculate per-member share
        if active_members > 0:
            per_member_share = month_balance / active_members
        else:
            per_member_share = Decimal('0.00')
        
        month_label = month_date.strftime('%b %Y')
        
        # Calculate change from previous month
        change_from_previous = None
        if months_data:
            prev_month_data = months_data[-1]
            change_from_previous = month_balance - prev_month_data['total_share']
        
        months_data.append({
            'month': month_label,
            'month_date': month_date,
            'month_start': month_start,
            'month_end': month_end,
            'total_share': month_balance,
            'active_members': active_members,
            'per_member_share': per_member_share,
            'change_from_previous': change_from_previous,
        })
        
        chart_data.append({
            'month': month_label,
            'total_share': float(month_balance),
            'per_member_share': float(per_member_share),
        })
    
    # Get current month data (last item in months_data)
    current_month_data = months_data[-1] if months_data else None
    last_month_data = months_data[-2] if len(months_data) >= 2 else None
    
    # Calculate changes
    if current_month_data and last_month_data:
        total_share_change = current_month_data['total_share'] - last_month_data['total_share']
        per_member_share_change = current_month_data['per_member_share'] - last_month_data['per_member_share']
        
        if last_month_data['total_share'] > 0:
            total_share_change_percent = (total_share_change / last_month_data['total_share']) * 100
        else:
            total_share_change_percent = Decimal('0.00')
        
        if last_month_data['per_member_share'] > 0:
            per_member_share_change_percent = (per_member_share_change / last_month_data['per_member_share']) * 100
        else:
            per_member_share_change_percent = Decimal('0.00')
    else:
        total_share_change = Decimal('0.00')
        per_member_share_change = Decimal('0.00')
        total_share_change_percent = Decimal('0.00')
        per_member_share_change_percent = Decimal('0.00')
    
    # Use actual current balance from MySetting for current month
    try:
        settings = MySetting.get_settings()
        current_balance = settings.balance
        current_active_members = User.objects.filter(status=UserStatus.ACTIVE).count()
        if current_active_members > 0:
            current_per_member_share = current_balance / current_active_members
        else:
            current_per_member_share = Decimal('0.00')
        
        # Update current month data with actual values
        if current_month_data:
            current_month_data['total_share'] = current_balance
            current_month_data['active_members'] = current_active_members
            current_month_data['per_member_share'] = current_per_member_share
            # Update chart data too
            if chart_data:
                chart_data[-1]['total_share'] = float(current_balance)
                chart_data[-1]['per_member_share'] = float(current_per_member_share)
    except:
        pass
    
    # Calculate member count change
    if current_month_data and last_month_data:
        member_count_change = current_month_data['active_members'] - last_month_data['active_members']
    else:
        member_count_change = 0
    
    context = {
        'chart_data': mark_safe(json.dumps(chart_data)),
        'months_data': months_data,
        'current_month_data': current_month_data,
        'last_month_data': last_month_data,
        'total_share_change': total_share_change,
        'per_member_share_change': per_member_share_change,
        'total_share_change_percent': total_share_change_percent,
        'per_member_share_change_percent': per_member_share_change_percent,
        'member_count_change': member_count_change,
    }
    context.update(get_role_context(request))
    return render(request, 'core/reports/share_report.html', context)

