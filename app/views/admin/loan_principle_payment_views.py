from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import LoanPrinciplePayment, Loan
from app.forms import LoanPrinciplePaymentForm
from .helpers import is_admin, is_member, get_role_context


@login_required
def loan_principle_payment_list(request):
    from decimal import Decimal
    from app.models import PaymentStatus, Loan, User
    from .filter_helpers import (
        get_default_date_range, parse_date_range, format_date_range,
        apply_date_filter
    )
    
    user = request.user
    # Members can only see their own principle payments
    if is_member(user):
        payments = LoanPrinciplePayment.objects.filter(loan__user=user).select_related('loan', 'loan__user')
    else:
        payments = LoanPrinciplePayment.objects.select_related('loan', 'loan__user')
    
    # Apply filters
    user_id = request.GET.get('user_id', '')
    loan_id = request.GET.get('loan_id', '')
    payment_status = request.GET.get('payment_status', '')
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
    
    # Apply filters
    if user_id and not is_member(user):
        payments = payments.filter(loan__user_id=user_id)
    if loan_id:
        payments = payments.filter(loan_id=loan_id)
    if payment_status:
        payments = payments.filter(payment_status=payment_status)
    
    # Apply date filter
    payments = apply_date_filter(payments, 'paid_date', start_date, end_date)
    
    # Order by
    payments = payments.order_by('-paid_date', '-created_at')
    
    # Calculate stats from filtered queryset
    total_payments = payments.count()
    total_amount = sum(p.amount for p in payments)
    paid_payments = payments.filter(payment_status=PaymentStatus.PAID)
    paid_count = paid_payments.count()
    paid_amount = sum(p.amount for p in paid_payments)
    pending_payments = payments.filter(payment_status=PaymentStatus.PENDING)
    pending_count = pending_payments.count()
    pending_amount = sum(p.amount for p in pending_payments)
    
    context = {
        'payments': payments,
        'stats': {
            'total': total_payments,
            'total_amount': total_amount,
            'paid_count': paid_count,
            'paid_amount': paid_amount,
            'pending_count': pending_count,
            'pending_amount': pending_amount,
        },
        'filters': {
            'user_id': user_id,
            'loan_id': loan_id,
            'payment_status': payment_status,
            'date_range': date_range_str,
        },
        'all_users': User.objects.filter(loans__isnull=False).distinct().order_by('name') if not is_member(user) else [],
        'all_loans': Loan.objects.all().order_by('-applied_date') if not is_member(user) else Loan.objects.filter(user=user).order_by('-applied_date'),
        'payment_statuses': PaymentStatus.choices,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_principle_payment_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_principle_payment_create(request):
    # Members cannot create principle payments (they use the app)
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot create principle payments through the admin interface.')
        return redirect('loan_principle_payment_list')
    
    if request.method == 'POST':
        form = LoanPrinciplePaymentForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('loan_principle_payment_list')
    else:
        form = LoanPrinciplePaymentForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_principle_payment_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_principle_payment_update(request, pk):
    obj = get_object_or_404(LoanPrinciplePayment, pk=pk)
    
    # Members cannot edit principle payments
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot edit principle payments.')
        return redirect('loan_principle_payment_list')
    
    if request.method == 'POST':
        form = LoanPrinciplePaymentForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('loan_principle_payment_list')
    else:
        form = LoanPrinciplePaymentForm(instance=obj)
    
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_principle_payment_edit.html', context)


@login_required
def loan_principle_payment_view(request, pk):
    obj = get_object_or_404(LoanPrinciplePayment, pk=pk)
    
    # Members can only view their own principle payments
    if is_member(request.user) and obj.loan.user != request.user:
        messages.error(request, 'Access denied. You can only view your own principle payments.')
        return redirect('loan_principle_payment_list')
    
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_principle_payment_view.html', context)


@login_required
@require_http_methods(["POST"])
def loan_principle_payment_delete(request, pk):
    obj = get_object_or_404(LoanPrinciplePayment, pk=pk)
    
    # Members cannot delete principle payments
    if is_member(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Members cannot delete principle payments.'}, status=403)
    
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Loan Principle Payment deleted successfully'})

