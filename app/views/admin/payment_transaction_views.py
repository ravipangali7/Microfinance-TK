from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from app.models import PaymentTransaction
from .helpers import is_member, get_role_context


@login_required
def payment_transaction_list(request):
    user = request.user
    # Members can only see their own payment transactions
    if is_member(user):
        transactions = PaymentTransaction.objects.filter(user=user).select_related('user').order_by('-created_at')
    else:
        # Admin/Board/Staff can see all transactions
        transactions = PaymentTransaction.objects.all().select_related('user').order_by('-created_at')
    
    context = {'transactions': transactions}
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

