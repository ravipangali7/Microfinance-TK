from django.urls import path
from app.views.api import (
    # Authentication
    login_api, logout_api, current_user_api,
    # Users
    user_list_api, user_create_api, user_detail_api, user_update_api, user_delete_api,
    # Memberships
    membership_list_api, membership_create_api, membership_detail_api, membership_update_api, membership_delete_api,
    # Membership Users
    membership_user_list_api, membership_user_create_api, membership_user_detail_api, membership_user_update_api, membership_user_delete_api,
    # Monthly Membership Deposits
    monthly_membership_deposit_list_api, monthly_membership_deposit_create_api, monthly_membership_deposit_detail_api, monthly_membership_deposit_update_api, monthly_membership_deposit_delete_api,
    # Loans
    loan_list_api, loan_create_api, loan_detail_api, loan_update_api, loan_delete_api, loan_details_api,
    # Loan Interest Payments
    loan_interest_payment_list_api, loan_interest_payment_create_api, loan_interest_payment_detail_api, loan_interest_payment_update_api, loan_interest_payment_delete_api,
    # Loan Principle Payments
    loan_principle_payment_list_api, loan_principle_payment_create_api, loan_principle_payment_detail_api, loan_principle_payment_update_api, loan_principle_payment_delete_api,
    # Fund Management
    fund_management_list_api, fund_management_create_api, fund_management_detail_api, fund_management_update_api, fund_management_delete_api,
    # Settings
    mysetting_detail_api, mysetting_update_api, loan_settings_api,
    # Dashboard
    dashboard_api,
    # Board Approval
    board_approval_list_api, approve_loan_api, reject_loan_api, update_loan_status_api, approve_fund_management_api, reject_fund_management_api,
    # Payment Check
    payment_check_api,
    # Payment Gateway
    create_payment_order_api,
    check_payment_status_api,
    payment_callback_api,
    # Payment Transactions
    payment_transaction_list_api,
    payment_transaction_detail_api,
    # Popups
    active_popup_api,
    # Support Tickets
    support_ticket_list_api,
    support_ticket_create_api,
    support_ticket_detail_api,
    support_ticket_reply_api,
    # App Update
    check_update_api,
)

urlpatterns = [
    # Authentication
    path('auth/login/', login_api, name='api_login'),
    path('auth/logout/', logout_api, name='api_logout'),
    path('auth/current-user/', current_user_api, name='api_current_user'),
    
    # Users
    path('users/', user_list_api, name='api_user_list'),
    path('users/create/', user_create_api, name='api_user_create'),
    path('users/<int:pk>/', user_detail_api, name='api_user_detail'),
    path('users/<int:pk>/update/', user_update_api, name='api_user_update'),
    path('users/<int:pk>/delete/', user_delete_api, name='api_user_delete'),
    
    # Memberships
    path('memberships/', membership_list_api, name='api_membership_list'),
    path('memberships/create/', membership_create_api, name='api_membership_create'),
    path('memberships/<int:pk>/', membership_detail_api, name='api_membership_detail'),
    path('memberships/<int:pk>/update/', membership_update_api, name='api_membership_update'),
    path('memberships/<int:pk>/delete/', membership_delete_api, name='api_membership_delete'),
    
    # Membership Users
    path('membership-users/', membership_user_list_api, name='api_membership_user_list'),
    path('membership-users/create/', membership_user_create_api, name='api_membership_user_create'),
    path('membership-users/<int:pk>/', membership_user_detail_api, name='api_membership_user_detail'),
    path('membership-users/<int:pk>/update/', membership_user_update_api, name='api_membership_user_update'),
    path('membership-users/<int:pk>/delete/', membership_user_delete_api, name='api_membership_user_delete'),
    
    # Monthly Membership Deposits
    path('monthly-membership-deposits/', monthly_membership_deposit_list_api, name='api_monthly_membership_deposit_list'),
    path('monthly-membership-deposits/create/', monthly_membership_deposit_create_api, name='api_monthly_membership_deposit_create'),
    path('monthly-membership-deposits/<int:pk>/', monthly_membership_deposit_detail_api, name='api_monthly_membership_deposit_detail'),
    path('monthly-membership-deposits/<int:pk>/update/', monthly_membership_deposit_update_api, name='api_monthly_membership_deposit_update'),
    path('monthly-membership-deposits/<int:pk>/delete/', monthly_membership_deposit_delete_api, name='api_monthly_membership_deposit_delete'),
    
    # Loans
    path('loans/', loan_list_api, name='api_loan_list'),
    path('loans/create/', loan_create_api, name='api_loan_create'),
    path('loans/<int:pk>/', loan_detail_api, name='api_loan_detail'),
    path('loans/<int:pk>/update/', loan_update_api, name='api_loan_update'),
    path('loans/<int:pk>/delete/', loan_delete_api, name='api_loan_delete'),
    path('loans/<int:pk>/details/', loan_details_api, name='api_loan_details'),
    
    # Loan Interest Payments
    path('loan-interest-payments/', loan_interest_payment_list_api, name='api_loan_interest_payment_list'),
    path('loan-interest-payments/create/', loan_interest_payment_create_api, name='api_loan_interest_payment_create'),
    path('loan-interest-payments/<int:pk>/', loan_interest_payment_detail_api, name='api_loan_interest_payment_detail'),
    path('loan-interest-payments/<int:pk>/update/', loan_interest_payment_update_api, name='api_loan_interest_payment_update'),
    path('loan-interest-payments/<int:pk>/delete/', loan_interest_payment_delete_api, name='api_loan_interest_payment_delete'),
    
    # Loan Principle Payments
    path('loan-principle-payments/', loan_principle_payment_list_api, name='api_loan_principle_payment_list'),
    path('loan-principle-payments/create/', loan_principle_payment_create_api, name='api_loan_principle_payment_create'),
    path('loan-principle-payments/<int:pk>/', loan_principle_payment_detail_api, name='api_loan_principle_payment_detail'),
    path('loan-principle-payments/<int:pk>/update/', loan_principle_payment_update_api, name='api_loan_principle_payment_update'),
    path('loan-principle-payments/<int:pk>/delete/', loan_principle_payment_delete_api, name='api_loan_principle_payment_delete'),
    
    # Fund Management
    path('fund-management/', fund_management_list_api, name='api_fund_management_list'),
    path('fund-management/create/', fund_management_create_api, name='api_fund_management_create'),
    path('fund-management/<int:pk>/', fund_management_detail_api, name='api_fund_management_detail'),
    path('fund-management/<int:pk>/update/', fund_management_update_api, name='api_fund_management_update'),
    path('fund-management/<int:pk>/delete/', fund_management_delete_api, name='api_fund_management_delete'),
    
    # Settings
    path('settings/', mysetting_detail_api, name='api_mysetting_detail'),
    path('settings/update/', mysetting_update_api, name='api_mysetting_update'),
    path('settings/loan-settings/', loan_settings_api, name='api_loan_settings'),
    
    # Dashboard
    path('dashboard/', dashboard_api, name='api_dashboard'),
    
    # Board Approval
    path('board-approval/', board_approval_list_api, name='api_board_approval_list'),
    path('board-approval/loans/<int:pk>/approve/', approve_loan_api, name='api_approve_loan'),
    path('board-approval/loans/<int:pk>/reject/', reject_loan_api, name='api_reject_loan'),
    path('board-approval/loans/<int:pk>/update-status/', update_loan_status_api, name='api_update_loan_status'),
    path('board-approval/fund-management/<int:pk>/approve/', approve_fund_management_api, name='api_approve_fund_management'),
    path('board-approval/fund-management/<int:pk>/reject/', reject_fund_management_api, name='api_reject_fund_management'),
    
    # Payment Check
    path('payment-check/', payment_check_api, name='api_payment_check'),
    
    # Payment Gateway
    path('payment/create-order/', create_payment_order_api, name='api_create_payment_order'),
    path('payment/check-status/', check_payment_status_api, name='api_check_payment_status'),
    path('payment/callback/', payment_callback_api, name='api_payment_callback'),
    
    # Payment Transactions
    path('payment-transactions/', payment_transaction_list_api, name='api_payment_transaction_list'),
    path('payment-transactions/<int:pk>/', payment_transaction_detail_api, name='api_payment_transaction_detail'),
    
    # Popups
    path('popups/active/', active_popup_api, name='api_active_popup'),
    
    # Support Tickets
    path('support-tickets/', support_ticket_list_api, name='api_support_ticket_list'),
    path('support-tickets/create/', support_ticket_create_api, name='api_support_ticket_create'),
    path('support-tickets/<int:pk>/', support_ticket_detail_api, name='api_support_ticket_detail'),
    path('support-tickets/<int:pk>/replies/', support_ticket_reply_api, name='api_support_ticket_reply'),
    
    # App Update
    path('app/check-update/', check_update_api, name='api_check_update'),
]
