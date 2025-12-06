from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils import timezone
from .models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, FundManagement, MySetting,
    PaymentTransaction, PushNotification, Popup, SupportTicket, SupportTicketReply,
    Penalty, LoanStatus, PaymentStatus, WithdrawalStatus, SupportTicketStatus
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'status', 'joined_date', 'created_at']
    list_filter = ['status', 'gender', 'country', 'joined_date', 'created_at']
    search_fields = ['name', 'phone', 'email', 'national_id', 'address']
    readonly_fields = ['created_at', 'updated_at', 'date_joined', 'last_login']
    fieldsets = (
        ('Authentication', {
            'fields': ('phone', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('name', 'gender', 'date_of_birth', 'address', 'national_id')
        }),
        ('Location', {
            'fields': ('country_code', 'country')
        }),
        ('Account Information', {
            'fields': ('status', 'joined_date')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at')
        }),
    )
    ordering = ['-created_at']
    
    def save_model(self, request, obj, form, change):
        """Override save_model to assign 'Member' group to new users with no groups"""
        is_new = not change  # change is False for new objects
        super().save_model(request, obj, form, change)
        
        # Assign "Member" group to new users if they have no groups
        if is_new and obj.groups.count() == 0:
            try:
                member_group = Group.objects.get(name='Member')
                obj.groups.add(member_group)
            except Group.DoesNotExist:
                # If Member group doesn't exist, create it
                member_group = Group.objects.create(name='Member')
                obj.groups.add(member_group)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']


@admin.register(MembershipUser)
class MembershipUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'membership', 'created_at']
    list_filter = ['membership', 'created_at']
    search_fields = ['user__name', 'user__phone', 'membership__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'membership']
    ordering = ['-created_at']


@admin.register(MonthlyMembershipDeposit)
class MonthlyMembershipDepositAdmin(admin.ModelAdmin):
    list_display = ['user', 'membership', 'amount', 'date', 'payment_status', 'is_custom', 'created_at']
    list_filter = ['payment_status', 'is_custom', 'membership', 'date', 'created_at']
    search_fields = ['user__name', 'user__phone', 'membership__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'membership']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['user', 'principal_amount', 'total_payable', 'timeline', 'status', 'applied_date', 'action_by']
    list_filter = ['status', 'applied_date', 'created_at']
    search_fields = ['user__name', 'user__phone']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'action_by']
    date_hierarchy = 'applied_date'
    fieldsets = (
        ('Loan Information', {
            'fields': ('user', 'applied_date', 'principal_amount', 'interest_rate', 'total_payable', 'timeline')
        }),
        ('Status', {
            'fields': ('status', 'action_by', 'approved_date', 'disbursed_date', 'completed_date')
        }),
        ('Additional Information', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    ordering = ['-applied_date', '-created_at']
    
    actions = ['approve_loans', 'reject_loans', 'mark_as_active', 'mark_as_completed']
    
    @admin.action(description='Approve selected loans')
    def approve_loans(self, request, queryset):
        updated = queryset.filter(status=LoanStatus.PENDING).update(
            status=LoanStatus.APPROVED,
            action_by=request.user,
            approved_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} loan(s) approved.')
    
    @admin.action(description='Reject selected loans')
    def reject_loans(self, request, queryset):
        updated = queryset.filter(status=LoanStatus.PENDING).update(
            status=LoanStatus.REJECTED,
            action_by=request.user
        )
        self.message_user(request, f'{updated} loan(s) rejected.')
    
    @admin.action(description='Mark selected loans as active')
    def mark_as_active(self, request, queryset):
        updated = queryset.filter(status=LoanStatus.APPROVED).update(
            status=LoanStatus.ACTIVE,
            disbursed_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} loan(s) marked as active.')
    
    @admin.action(description='Mark selected loans as completed')
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status=LoanStatus.ACTIVE).update(
            status=LoanStatus.COMPLETED,
            completed_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} loan(s) marked as completed.')


@admin.register(LoanInterestPayment)
class LoanInterestPaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'payment_status', 'is_custom', 'paid_date', 'created_at']
    list_filter = ['payment_status', 'is_custom', 'paid_date', 'created_at']
    search_fields = ['loan__user__name', 'loan__user__phone']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['loan']
    date_hierarchy = 'paid_date'
    ordering = ['-paid_date', '-created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'loan__user')


@admin.register(LoanPrinciplePayment)
class LoanPrinciplePaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'payment_status', 'is_custom', 'paid_date', 'created_at']
    list_filter = ['payment_status', 'is_custom', 'paid_date', 'created_at']
    search_fields = ['loan__user__name', 'loan__user__phone']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['loan']
    date_hierarchy = 'paid_date'
    ordering = ['-paid_date', '-created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'loan__user')


@admin.register(FundManagement)
class FundManagementAdmin(admin.ModelAdmin):
    list_display = ['type', 'amount', 'date', 'status', 'purpose', 'created_at']
    list_filter = ['type', 'status', 'date', 'created_at']
    search_fields = ['purpose']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    
    actions = ['approve_fund_management', 'reject_fund_management']
    
    @admin.action(description='Approve selected fund management records')
    def approve_fund_management(self, request, queryset):
        updated = queryset.filter(status=WithdrawalStatus.PENDING).update(
            status=WithdrawalStatus.APPROVED
        )
        self.message_user(request, f'{updated} fund management record(s) approved.')
    
    @admin.action(description='Reject selected fund management records')
    def reject_fund_management(self, request, queryset):
        updated = queryset.filter(status=WithdrawalStatus.PENDING).update(
            status=WithdrawalStatus.REJECTED
        )
        self.message_user(request, f'{updated} fund management record(s) rejected.')


@admin.register(MySetting)
class MySettingAdmin(admin.ModelAdmin):
    list_display = ['membership_deposit_date', 'loan_interest_payment_date', 'loan_interest_rate', 'loan_timeline', 'balance', 'latest_app_version', 'latest_version_code']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('System Settings', {
            'fields': ('membership_deposit_date', 'loan_interest_payment_date', 'loan_interest_rate', 'loan_timeline', 'balance')
        }),
        ('Penalty Settings', {
            'fields': ('default_penalty_amount', 'penalty_grace_period_days')
        }),
        ('App Update Settings', {
            'fields': ('latest_app_version', 'latest_version_code', 'apk_file', 'update_message', 'release_notes', 'mandatory_update')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not MySetting.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['client_txn_id', 'user', 'payment_type', 'payment_method', 'amount', 'status', 'order_id', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'status', 'created_at']
    search_fields = ['client_txn_id', 'order_id', 'upi_txn_id', 'customer_name', 'user__name', 'user__phone']
    readonly_fields = ['created_at', 'updated_at', 'gateway_response']
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'payment_type', 'payment_method', 'related_object_id', 'amount', 'status')
        }),
        ('Gateway Information', {
            'fields': ('client_txn_id', 'order_id', 'upi_txn_id', 'customer_name', 'txn_date')
        }),
        ('Additional Information', {
            'fields': ('gateway_response', 'created_at', 'updated_at')
        }),
    )


@admin.register(Popup)
class PopupAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__name', 'user__phone', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('user', 'subject', 'message', 'status')
        }),
        ('Additional Information', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(SupportTicketReply)
class SupportTicketReplyAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['ticket__subject', 'user__name', 'message']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['ticket', 'user']
    date_hierarchy = 'created_at'
    ordering = ['created_at']


@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'penalty_type', 'month_number', 'penalty_amount', 'total_penalty', 'payment_status', 'due_date', 'created_at']
    list_filter = ['penalty_type', 'payment_status', 'due_date', 'created_at']
    search_fields = ['user__name', 'user__phone']
    readonly_fields = ['created_at', 'updated_at', 'total_penalty']
    raw_id_fields = ['user']
    date_hierarchy = 'due_date'
    ordering = ['-due_date', '-created_at']
    actions = ['mark_as_paid', 'send_notification']
    
    fieldsets = (
        ('Penalty Information', {
            'fields': ('user', 'penalty_type', 'related_object_id', 'related_object_type')
        }),
        ('Penalty Details', {
            'fields': ('base_amount', 'month_number', 'penalty_amount', 'total_penalty')
        }),
        ('Payment Status', {
            'fields': ('payment_status', 'due_date', 'paid_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def mark_as_paid(self, request, queryset):
        """Mark selected penalties as paid"""
        from django.utils import timezone
        updated = queryset.filter(payment_status=PaymentStatus.PENDING).update(
            payment_status=PaymentStatus.PAID,
            paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} penalty(ies) marked as paid.')
    mark_as_paid.short_description = 'Mark selected penalties as paid'
    
    def send_notification(self, request, queryset):
        """Send notification to users with selected penalties"""
        from app.services.push_notification_service import send_notification_to_user
        sent = 0
        for penalty in queryset:
            try:
                send_notification_to_user(
                    penalty.user,
                    'Penalty Reminder',
                    f'You have an outstanding penalty of {penalty.penalty_amount} for {penalty.get_penalty_type_display()}. Total due: {penalty.total_penalty}',
                )
                sent += 1
            except Exception as e:
                self.message_user(request, f'Failed to send notification to {penalty.user.name}: {str(e)}', level='ERROR')
        self.message_user(request, f'Notifications sent to {sent} user(s).')
    send_notification.short_description = 'Send notification to users'
