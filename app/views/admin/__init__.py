# Admin views package
from .auth_views import login_view, logout_view
from .dashboard_views import dashboard_view
from .user_views import (
    user_list, user_create, user_update, user_delete, user_view,
    assign_membership_to_user, remove_membership_from_user
)
from .membership_views import (
    membership_list, membership_create, membership_update,
    membership_delete, membership_view,
    assign_user_to_membership, remove_user_from_membership
)
from .membership_user_views import (
    membership_user_list, membership_user_create, membership_user_update,
    membership_user_delete, membership_user_view
)
from .monthly_membership_deposit_views import (
    monthly_membership_deposit_list, monthly_membership_deposit_create,
    monthly_membership_deposit_update, monthly_membership_deposit_delete,
    monthly_membership_deposit_view, get_user_memberships
)
from .loan_views import (
    loan_list, loan_create, loan_update, loan_delete, loan_view
)
from .loan_interest_payment_views import (
    loan_interest_payment_list, loan_interest_payment_create,
    loan_interest_payment_update, loan_interest_payment_delete,
    loan_interest_payment_view, get_loan_interest_amount
)
from .loan_principle_payment_views import (
    loan_principle_payment_list, loan_principle_payment_create,
    loan_principle_payment_update, loan_principle_payment_delete,
    loan_principle_payment_view
)
from .organizational_withdrawal_views import (
    fund_management_list, fund_management_create,
    fund_management_update, fund_management_delete,
    fund_management_view
)
from .mysetting_views import (
    mysetting_view, mysetting_update
)
from .board_approval_views import (
    board_approval_view, approve_loan, reject_loan,
    update_loan_status, approve_fund_management, reject_fund_management,
    update_fund_management_status
)
from .push_notification_views import (
    push_notification_list, push_notification_create, push_notification_update,
    push_notification_delete, push_notification_view, send_push_notification_view
)
from .popup_views import (
    popup_list, popup_create, popup_update, popup_delete, popup_view
)
from .support_ticket_views import (
    support_ticket_list, support_ticket_view,
    support_ticket_update_status, support_ticket_add_reply
)
from .payment_transaction_views import (
    payment_transaction_list, payment_transaction_view
)
from .penalty_views import (
    penalty_list, penalty_view, penalty_edit, penalty_mark_paid, penalty_delete
)
from .report_views import (
    membership_deposit_report, loan_report, user_report, main_report, share_report
)

__all__ = [
    'login_view', 'logout_view',
    'dashboard_view',
    'user_list', 'user_create', 'user_update', 'user_delete', 'user_view',
    'assign_membership_to_user', 'remove_membership_from_user',
    'membership_list', 'membership_create', 'membership_update', 'membership_delete', 'membership_view',
    'assign_user_to_membership', 'remove_user_from_membership',
    'membership_user_list', 'membership_user_create', 'membership_user_update', 'membership_user_delete', 'membership_user_view',
    'monthly_membership_deposit_list', 'monthly_membership_deposit_create', 'monthly_membership_deposit_update', 'monthly_membership_deposit_delete', 'monthly_membership_deposit_view', 'get_user_memberships',
    'loan_list', 'loan_create', 'loan_update', 'loan_delete', 'loan_view',
    'loan_interest_payment_list', 'loan_interest_payment_create', 'loan_interest_payment_update', 'loan_interest_payment_delete', 'loan_interest_payment_view', 'get_loan_interest_amount',
    'loan_principle_payment_list', 'loan_principle_payment_create', 'loan_principle_payment_update', 'loan_principle_payment_delete', 'loan_principle_payment_view',
    'fund_management_list', 'fund_management_create', 'fund_management_update', 'fund_management_delete', 'fund_management_view',
    'mysetting_view', 'mysetting_update',
    'board_approval_view', 'approve_loan', 'reject_loan', 'update_loan_status',
    'approve_fund_management', 'reject_fund_management', 'update_fund_management_status',
    'push_notification_list', 'push_notification_create', 'push_notification_update',
    'push_notification_delete', 'push_notification_view', 'send_push_notification_view',
    'popup_list', 'popup_create', 'popup_update', 'popup_delete', 'popup_view',
    'support_ticket_list', 'support_ticket_view',
    'support_ticket_update_status', 'support_ticket_add_reply',
    'payment_transaction_list', 'payment_transaction_view',
    'penalty_list', 'penalty_view', 'penalty_edit', 'penalty_mark_paid', 'penalty_delete',
    'membership_deposit_report', 'loan_report', 'user_report', 'main_report', 'share_report',
]

