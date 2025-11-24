from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from app.models import LoanInterestPayment, Loan
from app.forms import LoanInterestPaymentForm
from .helpers import is_admin, is_member, get_role_context


@login_required
def loan_interest_payment_list(request):
    user = request.user
    # Members can only see their own interest payments
    if is_member(user):
        payments = LoanInterestPayment.objects.filter(loan__user=user).select_related('loan', 'loan__user').order_by('-paid_date', '-created_at')
    else:
        payments = LoanInterestPayment.objects.select_related('loan', 'loan__user').order_by('-paid_date', '-created_at')
    
    context = {'payments': payments}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_interest_payment_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_interest_payment_create(request):
    # Members cannot create interest payments
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot create interest payments.')
        return redirect('loan_interest_payment_list')
    
    if request.method == 'POST':
        form = LoanInterestPaymentForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect('loan_interest_payment_list')
    else:
        form = LoanInterestPaymentForm()
    
    context = {'form': form}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_interest_payment_add.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def loan_interest_payment_update(request, pk):
    obj = get_object_or_404(LoanInterestPayment, pk=pk)
    
    # Members cannot edit interest payments
    if is_member(request.user):
        messages.error(request, 'Access denied. Members cannot edit interest payments.')
        return redirect('loan_interest_payment_list')
    
    if request.method == 'POST':
        form = LoanInterestPaymentForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            return redirect('loan_interest_payment_list')
    else:
        form = LoanInterestPaymentForm(instance=obj)
    
    context = {'form': form, 'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_interest_payment_edit.html', context)


@login_required
def loan_interest_payment_view(request, pk):
    obj = get_object_or_404(LoanInterestPayment, pk=pk)
    
    # Members can only view their own interest payments
    if is_member(request.user) and obj.loan.user != request.user:
        messages.error(request, 'Access denied. You can only view your own interest payments.')
        return redirect('loan_interest_payment_list')
    
    context = {'obj': obj}
    context.update(get_role_context(request))
    return render(request, 'core/crud/loan_interest_payment_view.html', context)


@login_required
@require_http_methods(["POST"])
def loan_interest_payment_delete(request, pk):
    obj = get_object_or_404(LoanInterestPayment, pk=pk)
    
    # Members cannot delete interest payments
    if is_member(request.user):
        return JsonResponse({'success': False, 'message': 'Access denied. Members cannot delete interest payments.'}, status=403)
    
    obj.delete()
    return JsonResponse({'success': True, 'message': 'Loan Interest Payment deleted successfully'})


@login_required
def get_loan_interest_amount(request, loan_id):
    """API endpoint to get loan's calculated monthly interest amount"""
    loan = get_object_or_404(Loan, pk=loan_id)
    
    # Calculate monthly interest payment: (principal * interest_rate / 100) / timeline
    if loan.principal_amount and loan.interest_rate and loan.timeline:
        total_interest = (loan.principal_amount * loan.interest_rate) / Decimal('100')
        monthly_interest = total_interest / Decimal(str(loan.timeline))
        interest_amount = str(monthly_interest.quantize(Decimal('0.01')))
    else:
        interest_amount = '0.00'
    
    return JsonResponse({
        'success': True,
        'loan_id': loan.id,
        'principal_amount': str(loan.principal_amount),
        'interest_rate': str(loan.interest_rate),
        'timeline': loan.timeline,
        'monthly_interest_amount': interest_amount
    })

