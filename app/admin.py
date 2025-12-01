from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils import timezone
from .models import (
    User, Membership, MembershipUser, MonthlyMembershipDeposit,
    Loan, LoanInterestPayment, LoanPrinciplePayment, OrganizationalWithdrawal, MySetting,
    PaymentTransaction, PushNotification,
    LoanStatus, PaymentStatus, WithdrawalStatus
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
    list_display = ['user', 'membership', 'amount', 'date', 'payment_status', 'created_at']
    list_filter = ['payment_status', 'membership', 'date', 'created_at']
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
    list_display = ['loan', 'amount', 'payment_status', 'paid_date', 'created_at']
    list_filter = ['payment_status', 'paid_date', 'created_at']
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
    list_display = ['loan', 'amount', 'payment_status', 'paid_date', 'created_at']
    list_filter = ['payment_status', 'paid_date', 'created_at']
    search_fields = ['loan__user__name', 'loan__user__phone']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['loan']
    date_hierarchy = 'paid_date'
    ordering = ['-paid_date', '-created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'loan__user')


@admin.register(OrganizationalWithdrawal)
class OrganizationalWithdrawalAdmin(admin.ModelAdmin):
    list_display = ['amount', 'date', 'status', 'purpose', 'created_at']
    list_filter = ['status', 'date', 'created_at']
    search_fields = ['purpose']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    @admin.action(description='Approve selected withdrawals')
    def approve_withdrawals(self, request, queryset):
        updated = queryset.filter(status=WithdrawalStatus.PENDING).update(
            status=WithdrawalStatus.APPROVED
        )
        self.message_user(request, f'{updated} withdrawal(s) approved.')
    
    @admin.action(description='Reject selected withdrawals')
    def reject_withdrawals(self, request, queryset):
        updated = queryset.filter(status=WithdrawalStatus.PENDING).update(
            status=WithdrawalStatus.REJECTED
        )
        self.message_user(request, f'{updated} withdrawal(s) rejected.')


@admin.register(MySetting)
class MySettingAdmin(admin.ModelAdmin):
    list_display = ['membership_deposit_date', 'loan_interest_payment_date', 'loan_interest_rate', 'loan_timeline', 'balance']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not MySetting.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['client_txn_id', 'user', 'payment_type', 'amount', 'status', 'order_id', 'created_at']
    list_filter = ['payment_type', 'status', 'created_at']
    search_fields = ['client_txn_id', 'order_id', 'upi_txn_id', 'user__name', 'user__phone']
    readonly_fields = ['created_at', 'updated_at', 'gateway_response']
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'payment_type', 'related_object_id', 'amount', 'status')
        }),
        ('Gateway Information', {
            'fields': ('client_txn_id', 'order_id', 'upi_txn_id', 'txn_date')
        }),
        ('Additional Information', {
            'fields': ('gateway_response', 'created_at', 'updated_at')
        }),
    )
