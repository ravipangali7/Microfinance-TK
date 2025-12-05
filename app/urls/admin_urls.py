from django.urls import path
from app.views.admin import (
    login_view, logout_view,
    dashboard_view,
    user_list, user_create, user_update, user_delete, user_view,
    assign_membership_to_user, remove_membership_from_user,
    membership_list, membership_create, membership_update, membership_delete, membership_view,
    assign_user_to_membership, remove_user_from_membership,
    membership_user_list, membership_user_create, membership_user_update, membership_user_delete, membership_user_view,
    monthly_membership_deposit_list, monthly_membership_deposit_create, monthly_membership_deposit_update, monthly_membership_deposit_delete, monthly_membership_deposit_view, get_user_memberships,
    loan_list, loan_create, loan_update, loan_delete, loan_view,
    loan_interest_payment_list, loan_interest_payment_create, loan_interest_payment_update, loan_interest_payment_delete, loan_interest_payment_view, get_loan_interest_amount,
    loan_principle_payment_list, loan_principle_payment_create, loan_principle_payment_update, loan_principle_payment_delete, loan_principle_payment_view,
    organizational_withdrawal_list, organizational_withdrawal_create, organizational_withdrawal_update, organizational_withdrawal_delete, organizational_withdrawal_view,
    mysetting_view, mysetting_update,
    board_approval_view, approve_loan, reject_loan, update_loan_status,
    push_notification_list, push_notification_create, push_notification_update,
    push_notification_delete, push_notification_view, send_push_notification_view,
    payment_transaction_list, payment_transaction_view,
    membership_deposit_report, loan_report, user_report, main_report,
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', dashboard_view, name='dashboard'),
    
    # User CRUD
    path('users/', user_list, name='user_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/<int:pk>/', user_view, name='user_view'),
    path('users/<int:pk>/edit/', user_update, name='user_update'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),
    path('users/<int:user_id>/assign-membership/<int:membership_id>/', assign_membership_to_user, name='assign_membership_to_user'),
    path('users/<int:user_id>/remove-membership/<int:membership_id>/', remove_membership_from_user, name='remove_membership_from_user'),
    
    # Membership CRUD
    path('memberships/', membership_list, name='membership_list'),
    path('memberships/create/', membership_create, name='membership_create'),
    path('memberships/<int:pk>/', membership_view, name='membership_view'),
    path('memberships/<int:pk>/edit/', membership_update, name='membership_update'),
    path('memberships/<int:pk>/delete/', membership_delete, name='membership_delete'),
    path('memberships/<int:membership_id>/assign-user/<int:user_id>/', assign_user_to_membership, name='assign_user_to_membership'),
    path('memberships/<int:membership_id>/remove-user/<int:user_id>/', remove_user_from_membership, name='remove_user_from_membership'),
    
    # MembershipUser CRUD
    path('membership-users/', membership_user_list, name='membership_user_list'),
    path('membership-users/create/', membership_user_create, name='membership_user_create'),
    path('membership-users/<int:pk>/', membership_user_view, name='membership_user_view'),
    path('membership-users/<int:pk>/edit/', membership_user_update, name='membership_user_update'),
    path('membership-users/<int:pk>/delete/', membership_user_delete, name='membership_user_delete'),
    
    # MonthlyMembershipDeposit CRUD
    path('monthly-membership-deposits/', monthly_membership_deposit_list, name='monthly_membership_deposit_list'),
    path('monthly-membership-deposits/create/', monthly_membership_deposit_create, name='monthly_membership_deposit_create'),
    path('monthly-membership-deposits/<int:pk>/', monthly_membership_deposit_view, name='monthly_membership_deposit_view'),
    path('monthly-membership-deposits/<int:pk>/edit/', monthly_membership_deposit_update, name='monthly_membership_deposit_update'),
    path('monthly-membership-deposits/<int:pk>/delete/', monthly_membership_deposit_delete, name='monthly_membership_deposit_delete'),
    path('monthly-membership-deposits/get-user-memberships/<int:user_id>/', get_user_memberships, name='get_user_memberships'),
    
    # Loan CRUD
    path('loans/', loan_list, name='loan_list'),
    path('loans/create/', loan_create, name='loan_create'),
    path('loans/<int:pk>/', loan_view, name='loan_view'),
    path('loans/<int:pk>/edit/', loan_update, name='loan_update'),
    path('loans/<int:pk>/delete/', loan_delete, name='loan_delete'),
    path('loans/<int:pk>/update-status/', update_loan_status, name='update_loan_status'),
    
    # Loan Interest Payment CRUD
    path('loan-interest-payments/', loan_interest_payment_list, name='loan_interest_payment_list'),
    path('loan-interest-payments/create/', loan_interest_payment_create, name='loan_interest_payment_create'),
    path('loan-interest-payments/<int:pk>/', loan_interest_payment_view, name='loan_interest_payment_view'),
    path('loan-interest-payments/<int:pk>/edit/', loan_interest_payment_update, name='loan_interest_payment_update'),
    path('loan-interest-payments/<int:pk>/delete/', loan_interest_payment_delete, name='loan_interest_payment_delete'),
    path('loan-interest-payments/get-loan-interest-amount/<int:loan_id>/', get_loan_interest_amount, name='get_loan_interest_amount'),
    
    # Loan Principle Payment CRUD
    path('loan-principle-payments/', loan_principle_payment_list, name='loan_principle_payment_list'),
    path('loan-principle-payments/create/', loan_principle_payment_create, name='loan_principle_payment_create'),
    path('loan-principle-payments/<int:pk>/', loan_principle_payment_view, name='loan_principle_payment_view'),
    path('loan-principle-payments/<int:pk>/edit/', loan_principle_payment_update, name='loan_principle_payment_update'),
    path('loan-principle-payments/<int:pk>/delete/', loan_principle_payment_delete, name='loan_principle_payment_delete'),
    
    # Organizational Withdrawal CRUD
    path('organizational-withdrawals/', organizational_withdrawal_list, name='organizational_withdrawal_list'),
    path('organizational-withdrawals/create/', organizational_withdrawal_create, name='organizational_withdrawal_create'),
    path('organizational-withdrawals/<int:pk>/', organizational_withdrawal_view, name='organizational_withdrawal_view'),
    path('organizational-withdrawals/<int:pk>/edit/', organizational_withdrawal_update, name='organizational_withdrawal_update'),
    path('organizational-withdrawals/<int:pk>/delete/', organizational_withdrawal_delete, name='organizational_withdrawal_delete'),
    
    # MySetting
    path('settings/', mysetting_view, name='mysetting_view'),
    path('settings/edit/', mysetting_update, name='mysetting_update'),
    
    # Board Approval
    path('board-approval/', board_approval_view, name='board_approval'),
    path('board-approval/loans/<int:pk>/approve/', approve_loan, name='approve_loan'),
    path('board-approval/loans/<int:pk>/reject/', reject_loan, name='reject_loan'),
    
    # Push Notification CRUD
    path('push-notifications/', push_notification_list, name='push_notification_list'),
    path('push-notifications/create/', push_notification_create, name='push_notification_create'),
    path('push-notifications/<int:pk>/', push_notification_view, name='push_notification_view'),
    path('push-notifications/<int:pk>/edit/', push_notification_update, name='push_notification_update'),
    path('push-notifications/<int:pk>/delete/', push_notification_delete, name='push_notification_delete'),
    path('push-notifications/<int:pk>/send/', send_push_notification_view, name='send_push_notification'),
    
    # Payment Transaction
    path('payment-transactions/', payment_transaction_list, name='payment_transaction_list'),
    path('payment-transactions/<int:pk>/', payment_transaction_view, name='payment_transaction_view'),
    
    # Reports
    path('reports/membership-deposits/', membership_deposit_report, name='membership_deposit_report'),
    path('reports/loans/', loan_report, name='loan_report'),
    path('reports/users/', user_report, name='user_report'),
    path('reports/main/', main_report, name='main_report'),
]

