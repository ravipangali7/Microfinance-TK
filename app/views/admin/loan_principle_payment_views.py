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
    user = request.user
    # Members can only see their own principle payments
    if is_member(user):
        payments = LoanPrinciplePayment.objects.filter(loan__user=user).select_related('loan', 'loan__user').order_by('-paid_date', '-created_at')
    else:
        payments = LoanPrinciplePayment.objects.select_related('loan', 'loan__user').order_by('-paid_date', '-created_at')
    
    context = {'payments': payments}
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

