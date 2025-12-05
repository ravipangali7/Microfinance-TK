from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import Loan, LoanInterestPayment, LoanPrinciplePayment
from app.forms import LoanForm, LoanCreateForm
from .helpers import is_admin, is_member, get_role_context


@login_required
def loan_list(request):
    from decimal import Decimal
    from app.models import LoanStatus
    from .filter_helpers import (
        get_default_date_range, parse_date_range, format_date_range,
        apply_text_search, apply_date_filter, apply_amount_range_filter
    )
    
    user = request.user
    # Members can only see their own loans
    if is_member(user):
        loans = Loan.objects.filter(user=user).select_related('user', 'action_by')
    else:
        loans = Loan.objects.select_related('user', 'action_by')
    
    # Apply filters
    search = request.GET.get('search', '')
    user_id = request.GET.get('user_id', '')
    status = request.GET.get('status', '')
    from_amount = request.GET.get('from_amount', '')
    to_amount = request.GET.get('to_amount', '')
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
    if search and not is_member(user):
        loans = apply_text_search(loans, search, ['user__name', 'user__phone'])
    if user_id and not is_member(user):
        loans = loans.filter(user_id=user_id)
    if status:
        loans = loans.filter(status=status)
    if from_amount or to_amount:
        loans = apply_amount_range_filter(loans, 'principal_amount', from_amount, to_amount)
    
    # Apply date filter
    loans = apply_date_filter(loans, 'applied_date', start_date, end_date)
    
    # Order by
    loans = loans.order_by('-applied_date', '-created_at')
    
    # Calculate stats from filtered queryset
    total_loans = loans.count()
    total_principal = sum(l.principal_amount for l in loans)
    total_payable = sum(l.total_payable for l in loans)
    active_count = loans.filter(status=LoanStatus.ACTIVE).count()
    pending_count = loans.filter(status=LoanStatus.PENDING).count()
    approved_count = loans.filter(status=LoanStatus.APPROVED).count()
    completed_count = loans.filter(status=LoanStatus.COMPLETED).count()
    
    context = {
        'loans': loans,
        'stats': {
            'total': total_loans,
            'total_principal': total_principal,
            'total_payable': total_payable,
            'active': active_count,
            'pending': pending_count,
            'approved': approved_count,
            'completed': completed_count,
        },
        'filters': {
            'search': search,
            'user_id': user_id,
            'status': status,
            'from_amount': from_amount,
            'to_amount': to_amount,
            'date_range': date_range_str,
        },
        'all_users': Loan.objects.values_list('user', flat=True).distinct() if not is_member(user) else [],
        'all_statuses': LoanStatus.choices,
    }
    # Get user objects for dropdown
    if not is_member(user) and context['all_users']:
        from app.models import User
        context['all_users'] = User.objects.filter(id__in=context['all_users']).order_by('name')
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_create(request):
    # Members cannot create loans
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot create loans.')
        return redirect('loan_list')
    
    if request.method == 'POST':
        form = LoanCreateForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('loan_list')
    else:
        form = LoanCreateForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_update(request, pk):
    obj = get_object_or_404(Loan, pk=pk)
    
    # Members cannot edit loans
    if is_member(request.user):
        if obj.user != request.user:
            messages.error(request, 'Access denied. You can only edit your own loans.')
            return redirect('loan_list')
        messages.error(request, 'Access denied. Members cannot edit loans.')
        return redirect('loan_list')
    
    # Check if loan has interest payments
    has_payments = LoanInterestPayment.objects.filter(loan=obj).exists()
    
    if request.method == 'POST':
        form = LoanForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Loan updated successfully.')
            return redirect('loan_view', pk=pk)
    else:
        form = LoanForm(instance=obj)
    
    context = {'form': form, 'obj': obj, 'has_payments': has_payments}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_edit.html', context)


@login_required
def loan_view(request, pk):
    obj = get_object_or_404(Loan, pk=pk)
    
    # Members can only view their own loans
    if is_member(request.user) and obj.user != request.user:
        messages.error(request, 'Access denied. You can only view your own loans.')
        return redirect('loan_list')
    
    # Get all interest payments for this loan
    interest_payments = obj.interest_payments.all().order_by('-paid_date')
    
    # Get all principle payments for this loan
    principle_payments = obj.principle_payments.all().order_by('-paid_date')
    
    # Calculate remaining principle
    remaining_principle = obj.get_remaining_principle()
    total_paid_principle = obj.get_total_paid_principle()
    
    context = {
        'obj': obj,
        'interest_payments': interest_payments,
        'principle_payments': principle_payments,
        'remaining_principle': remaining_principle,
        'total_paid_principle': total_paid_principle,
    }
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_view.html', context)


@login_required
@require_http_methods(["POST"])
def loan_delete(request, pk):
    obj = get_object_or_404(Loan, pk=pk)
    
    # Members cannot delete loans
    if is_member(request.user):
        if obj.user != request.user:
            return JsonResponse({'success': False, 'message': 'Access denied. You can only delete your own loans.'}, status=403)
        return JsonResponse({'success': False, 'message': 'Access denied. Members cannot delete loans.'}, status=403)
    
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Loan deleted successfully'})

