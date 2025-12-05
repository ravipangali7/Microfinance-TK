from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from app.models import PaymentTransaction
from .helpers import is_member, get_role_context


@login_required
def payment_transaction_list(request):
    from decimal import Decimal
    from app.models import User
    from .filter_helpers import (
        get_default_date_range, parse_date_range, format_date_range,
        apply_date_filter
    )
    
    user = request.user
    # Members can only see their own payment transactions
    if is_member(user):
        transactions = PaymentTransaction.objects.filter(user=user).select_related('user')
    else:
        # Admin/Board/Staff can see all transactions
        transactions = PaymentTransaction.objects.all().select_related('user')
    
    # Apply filters
    search = request.GET.get('search', '')
    user_id = request.GET.get('user_id', '')
    payment_type = request.GET.get('payment_type', '')
    status = request.GET.get('status', '')
    date_range_str = request.GET.get('date_range', '')
    
    # Parse date range
    start_date, end_date = None, None
    if date_range_str:
        date_range = parse_date_range(date_range_str)
        if date_range:
            start_date, end_date = date_range
    else:
        # Default to last 1 month
        start_date, end_date = get_default_date_range()
        date_range_str = format_date_range(start_date, end_date)
    
    # Apply search filter
    if search:
        search = search.strip()
        if search:
            search_filter = Q(
                upi_txn_id__icontains=search
            ) | Q(
                user__phone__icontains=search
            ) | Q(
                user__name__icontains=search
            ) | Q(
                client_txn_id__icontains=search
            ) | Q(
                customer_name__icontains=search
            )
            # Also search in order_id if it's numeric
            try:
                order_id = int(search)
                search_filter |= Q(order_id=order_id)
            except (ValueError, TypeError):
                pass
            transactions = transactions.filter(search_filter)
    
    # Apply filters
    if user_id and not is_member(user):
        transactions = transactions.filter(user_id=user_id)
    if payment_type:
        transactions = transactions.filter(payment_type=payment_type)
    if status:
        transactions = transactions.filter(status=status)
    
    # Apply date filter (on txn_date or created_at)
    if start_date or end_date:
        date_filter = Q()
        if start_date and end_date:
            date_filter = (Q(txn_date__gte=start_date, txn_date__lte=end_date) | 
                          Q(txn_date__isnull=True, created_at__date__gte=start_date, created_at__date__lte=end_date))
        elif start_date:
            date_filter = Q(txn_date__gte=start_date) | Q(txn_date__isnull=True, created_at__date__gte=start_date)
        elif end_date:
            date_filter = Q(txn_date__lte=end_date) | Q(txn_date__isnull=True, created_at__date__lte=end_date)
        if date_filter:
            transactions = transactions.filter(date_filter)
    
    # Order by
    transactions = transactions.order_by('-created_at')
    
    # Calculate stats from filtered queryset
    total_transactions = transactions.count()
    total_amount = sum(t.amount for t in transactions)
    success_count = transactions.filter(status='success').count()
    pending_count = transactions.filter(status='pending').count()
    failed_count = transactions.filter(status='failed').count()
    
    context = {
        'transactions': transactions,
        'stats': {
            'total': total_transactions,
            'total_amount': total_amount,
            'success': success_count,
            'pending': pending_count,
            'failed': failed_count,
        },
        'filters': {
            'search': search,
            'user_id': user_id,
            'payment_type': payment_type,
            'status': status,
            'date_range': date_range_str,
        },
        'all_users': User.objects.filter(payment_transactions__isnull=False).distinct().order_by('name') if not is_member(user) else [],
        'payment_types': PaymentTransaction.PAYMENT_TYPE_CHOICES,
        'transaction_statuses': PaymentTransaction.TRANSACTION_STATUS_CHOICES,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/payment_transaction_list.html', context)


@login_required
def payment_transaction_view(request, pk):
    transaction = get_object_or_404(PaymentTransaction, pk=pk)
    
    # Members can only view their own payment transactions
    if is_member(request.user) and transaction.user != request.user:
        messages.error(request, 'Access denied. You can only view your own payment transactions.')
        return redirect('payment_transaction_list')
    
    # Get related object based on payment type
    related_object = None
    if transaction.payment_type == 'deposit':
        from app.models import MonthlyMembershipDeposit
        try:
            related_object = MonthlyMembershipDeposit.objects.get(pk=transaction.related_object_id)
        except MonthlyMembershipDeposit.DoesNotExist:
            pass
    elif transaction.payment_type == 'interest':
        from app.models import LoanInterestPayment
        try:
            related_object = LoanInterestPayment.objects.select_related('loan', 'loan__user').get(pk=transaction.related_object_id)
        except LoanInterestPayment.DoesNotExist:
            pass
    elif transaction.payment_type == 'principle':
        from app.models import LoanPrinciplePayment
        try:
            related_object = LoanPrinciplePayment.objects.select_related('loan', 'loan__user').get(pk=transaction.related_object_id)
        except LoanPrinciplePayment.DoesNotExist:
            pass
    
    context = {
        'transaction': transaction,
        'related_object': related_object
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/payment_transaction_view.html', context)

