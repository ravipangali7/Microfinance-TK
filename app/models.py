from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


# Choice Enums
class UserStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    FREEZE = 'freeze', 'Freeze'
    INACTIVE = 'inactive', 'Inactive'


class LoanStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    DEFAULT = 'default', 'Default'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'


class PenaltyType(models.TextChoices):
    DEPOSIT = 'deposit', 'Deposit'
    INTEREST = 'interest', 'Interest'


class WithdrawalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


class FundManagementType(models.TextChoices):
    CREDIT = 'credit', 'Credit'
    DEBIT = 'debit', 'Debit'


class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'


# Base Model with Timestamps
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# User Model
class User(AbstractUser, TimeStampedModel):
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    national_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    country_code = models.CharField(max_length=5, default='+977')
    country = models.CharField(max_length=100, default='Nepal')
    joined_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name', 'email']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def save(self, *args, **kwargs):
        # Automatically set username to phone
        if self.phone:
            self.username = self.phone
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.phone:
            # Check for duplicate phone numbers
            if User.objects.filter(phone=self.phone).exclude(pk=self.pk).exists():
                raise ValidationError({'phone': 'A user with this phone number already exists.'})


# Membership Model
class Membership(TimeStampedModel):
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'
        ordering = ['name']

    def __str__(self):
        return self.name


# MembershipUser Model
class MembershipUser(TimeStampedModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='membership_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='membership_users')

    class Meta:
        verbose_name = 'Membership User'
        verbose_name_plural = 'Membership Users'
        unique_together = ['membership', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.name} - {self.membership.name}"


# MonthlyMembershipDeposit Model
class MonthlyMembershipDeposit(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_membership_deposits')
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='monthly_deposits')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    name = models.CharField(max_length=50, blank=True, help_text='Auto-generated format: YYYY MMM (e.g., "2025 Apr")')
    paid_date = models.DateField(blank=True, null=True, help_text='Date when payment was completed')
    is_custom = models.BooleanField(default=False, help_text='If True, creates cash payment transaction when payment_status is paid')

    class Meta:
        verbose_name = 'Monthly Membership Deposit'
        verbose_name_plural = 'Monthly Membership Deposits'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.name} - {self.amount} - {self.date}"

    def save(self, *args, **kwargs):
        # Auto-generate name if not provided
        if not self.name and self.date:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            self.name = f"{self.date.year} {month_names[self.date.month - 1]}"
        
        # Ensure is_custom has a default value if not set
        if not hasattr(self, 'is_custom') or self.is_custom is None:
            self.is_custom = False
        
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_amount = None
        
        if not is_new:
            try:
                old_instance = MonthlyMembershipDeposit.objects.get(pk=self.pk)
                old_status = old_instance.payment_status
                old_amount = old_instance.amount
            except MonthlyMembershipDeposit.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Update balance based on payment status changes
        if is_new:
            # New deposit: add to balance if paid
            if self.payment_status == PaymentStatus.PAID:
                update_system_balance(self.amount, operation='add')
        else:
            # Existing deposit: handle status and amount changes
            if old_status != self.payment_status:
                # Status changed
                if old_status == PaymentStatus.PAID and self.payment_status == PaymentStatus.PENDING:
                    # Was paid, now pending: subtract from balance
                    update_system_balance(old_amount, operation='subtract')
                elif old_status == PaymentStatus.PENDING and self.payment_status == PaymentStatus.PAID:
                    # Was pending, now paid: add to balance
                    update_system_balance(self.amount, operation='add')
            elif self.payment_status == PaymentStatus.PAID and old_amount != self.amount:
                # Amount changed while paid: adjust balance
                difference = self.amount - old_amount
                if difference > 0:
                    update_system_balance(difference, operation='add')
                else:
                    update_system_balance(abs(difference), operation='subtract')
        
        # Create cash payment transaction when payment is marked as paid and is_custom is True
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID and self.is_custom:
            # Check if status changed to paid (new record with paid status, or status changed from non-paid to paid)
            should_create_transaction = False
            if is_new:
                should_create_transaction = True
            elif old_status != PaymentStatus.PAID:
                should_create_transaction = True
            
            if should_create_transaction:
                # Delete any existing PaymentTransaction for this deposit
                PaymentTransaction.objects.filter(
                    payment_type='deposit',
                    related_object_id=self.pk
                ).delete()
                
                # Create new cash payment transaction
                timestamp = int(timezone.now().timestamp())
                client_txn_id = f"cash_deposit_{self.pk}_{timestamp}"
                PaymentTransaction.objects.create(
                    payment_type='deposit',
                    related_object_id=self.pk,
                    user=self.user,
                    payment_method='cash',
                    client_txn_id=client_txn_id,
                    amount=self.amount,
                    status='success',
                    txn_date=self.paid_date if self.paid_date else timezone.now().date(),
                    customer_name=self.user.name if self.user.name else None
                )

    def get_total_penalties(self):
        """Calculate total penalties for this deposit"""
        # Lazy import to avoid circular reference
        from django.apps import apps
        try:
            Penalty = apps.get_model('app', 'Penalty')
            return sum(
                penalty.penalty_amount for penalty in Penalty.objects.filter(
                    penalty_type='deposit',
                    related_object_id=self.pk,
                    payment_status=PaymentStatus.PENDING
                )
            )
        except (LookupError, AttributeError):
            return Decimal('0.00')
    
    def delete(self, *args, **kwargs):
        # If deposit was paid, subtract from balance
        if self.payment_status == PaymentStatus.PAID:
            update_system_balance(self.amount, operation='subtract')
        super().delete(*args, **kwargs)


# Loan Model
class Loan(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    applied_date = models.DateField(default=timezone.now)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total_payable = models.DecimalField(max_digits=15, decimal_places=2)
    timeline = models.IntegerField(help_text='Timeline in months', default=12)
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='loan_actions')
    status = models.CharField(max_length=20, choices=LoanStatus.choices, default=LoanStatus.PENDING)
    approved_date = models.DateField(blank=True, null=True)
    disbursed_date = models.DateField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'
        ordering = ['-applied_date', '-created_at']

    def __str__(self):
        return f"{self.user.name} - {self.principal_amount} - {self.status}"

    def save(self, *args, **kwargs):
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_principal = None
        
        if not is_new:
            try:
                old_instance = Loan.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_principal = old_instance.principal_amount
            except Loan.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Note: Loans no longer affect system balance
    
    def get_total_paid_principle(self):
        """Calculate total paid principle from all paid principle payments"""
        return sum(
            payment.amount for payment in self.principle_payments.filter(payment_status=PaymentStatus.PAID)
        )
    
    def get_remaining_principle(self):
        """Calculate remaining principle amount"""
        return self.principal_amount - self.get_total_paid_principle()

    def delete(self, *args, **kwargs):
        # Note: Loans no longer affect system balance
        super().delete(*args, **kwargs)


# LoanInterestPayment Model
class LoanInterestPayment(TimeStampedModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='interest_payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, help_text='Auto-generated format: YYYY MMM (e.g., "2025 Oct")')
    is_custom = models.BooleanField(default=False, help_text='If True, creates cash payment transaction when payment_status is paid')

    class Meta:
        verbose_name = 'Loan Interest Payment'
        verbose_name_plural = 'Loan Interest Payments'
        ordering = ['-paid_date', '-created_at']

    def __str__(self):
        return f"{self.loan.user.name} - {self.amount} - {self.paid_date}"

    def save(self, *args, **kwargs):
        # Auto-update paid_date when status changes to paid
        if self.payment_status == PaymentStatus.PAID and not self.paid_date:
            self.paid_date = timezone.now().date()
        
        # Auto-generate name if not provided (use paid_date if available, otherwise use current date)
        if not self.name:
            date_to_use = self.paid_date if self.paid_date else timezone.now().date()
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            self.name = f"{date_to_use.year} {month_names[date_to_use.month - 1]}"
        
        # Ensure is_custom has a default value if not set
        if not hasattr(self, 'is_custom') or self.is_custom is None:
            self.is_custom = False
        
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_amount = None
        
        if not is_new:
            try:
                old_instance = LoanInterestPayment.objects.get(pk=self.pk)
                old_status = old_instance.payment_status
                old_amount = old_instance.amount
            except LoanInterestPayment.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Update balance based on payment status changes
        if is_new:
            # New payment: add to balance if paid
            if self.payment_status == PaymentStatus.PAID:
                update_system_balance(self.amount, operation='add')
        else:
            # Existing payment: handle status and amount changes
            if old_status != self.payment_status:
                # Status changed
                if old_status == PaymentStatus.PAID and self.payment_status == PaymentStatus.PENDING:
                    # Was paid, now pending: subtract from balance
                    update_system_balance(old_amount, operation='subtract')
                elif old_status == PaymentStatus.PENDING and self.payment_status == PaymentStatus.PAID:
                    # Was pending, now paid: add to balance
                    update_system_balance(self.amount, operation='add')
            elif self.payment_status == PaymentStatus.PAID and old_amount != self.amount:
                # Amount changed while paid: adjust balance
                difference = self.amount - old_amount
                if difference > 0:
                    update_system_balance(difference, operation='add')
                else:
                    update_system_balance(abs(difference), operation='subtract')
        
        # Create cash payment transaction when payment is marked as paid and is_custom is True
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID and self.is_custom:
            # Check if status changed to paid (new record with paid status, or status changed from non-paid to paid)
            should_create_transaction = False
            if is_new:
                should_create_transaction = True
            elif old_status != PaymentStatus.PAID:
                should_create_transaction = True
            
            if should_create_transaction:
                # Delete any existing PaymentTransaction for this interest payment
                PaymentTransaction.objects.filter(
                    payment_type='interest',
                    related_object_id=self.pk
                ).delete()
                
                # Create new cash payment transaction
                timestamp = int(timezone.now().timestamp())
                client_txn_id = f"cash_interest_{self.pk}_{timestamp}"
                PaymentTransaction.objects.create(
                    payment_type='interest',
                    related_object_id=self.pk,
                    user=self.loan.user,
                    payment_method='cash',
                    client_txn_id=client_txn_id,
                    amount=self.amount,
                    status='success',
                    txn_date=self.paid_date if self.paid_date else timezone.now().date(),
                    customer_name=self.loan.user.name if self.loan.user.name else None
                )

    def get_total_penalties(self):
        """Calculate total penalties for this interest payment"""
        # Lazy import to avoid circular reference
        from django.apps import apps
        try:
            Penalty = apps.get_model('app', 'Penalty')
            return sum(
                penalty.penalty_amount for penalty in Penalty.objects.filter(
                    penalty_type='interest',
                    related_object_id=self.pk,
                    payment_status=PaymentStatus.PENDING
                )
            )
        except (LookupError, AttributeError):
            return Decimal('0.00')
    
    def delete(self, *args, **kwargs):
        # If payment was paid, subtract from balance
        if self.payment_status == PaymentStatus.PAID:
            update_system_balance(self.amount, operation='subtract')
        super().delete(*args, **kwargs)


# FundManagement Model
class FundManagement(TimeStampedModel):
    type = models.CharField(max_length=20, choices=FundManagementType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING)
    purpose = models.TextField()

    class Meta:
        verbose_name = 'Fund Management'
        verbose_name_plural = 'Fund Management'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} - {self.date} - {self.status}"

    def save(self, *args, **kwargs):
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_amount = None
        old_type = None
        
        if not is_new:
            try:
                old_instance = FundManagement.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_amount = old_instance.amount
                old_type = old_instance.type
            except FundManagement.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Update balance based on status changes and type
        if is_new:
            # New record: apply balance change if approved
            if self.status == WithdrawalStatus.APPROVED:
                if self.type == FundManagementType.CREDIT:
                    update_system_balance(self.amount, operation='add')
                elif self.type == FundManagementType.DEBIT:
                    update_system_balance(self.amount, operation='subtract')
        else:
            # Existing record: handle status, amount, and type changes
            if old_status != self.status:
                # Status changed
                if old_status == WithdrawalStatus.APPROVED:
                    # Was approved, now pending/rejected: reverse old balance change
                    if old_type == FundManagementType.CREDIT:
                        update_system_balance(old_amount, operation='subtract')
                    elif old_type == FundManagementType.DEBIT:
                        update_system_balance(old_amount, operation='add')
                if self.status == WithdrawalStatus.APPROVED:
                    # Now approved: apply new balance change
                    if self.type == FundManagementType.CREDIT:
                        update_system_balance(self.amount, operation='add')
                    elif self.type == FundManagementType.DEBIT:
                        update_system_balance(self.amount, operation='subtract')
            elif self.status == WithdrawalStatus.APPROVED:
                # Status is approved, check for amount or type changes
                if old_amount != self.amount or old_type != self.type:
                    # Reverse old balance change
                    if old_type == FundManagementType.CREDIT:
                        update_system_balance(old_amount, operation='subtract')
                    elif old_type == FundManagementType.DEBIT:
                        update_system_balance(old_amount, operation='add')
                    
                    # Apply new balance change
                    if self.type == FundManagementType.CREDIT:
                        update_system_balance(self.amount, operation='add')
                    elif self.type == FundManagementType.DEBIT:
                        update_system_balance(self.amount, operation='subtract')

    def delete(self, *args, **kwargs):
        # If record was approved, reverse balance change
        if self.status == WithdrawalStatus.APPROVED:
            if self.type == FundManagementType.CREDIT:
                update_system_balance(self.amount, operation='subtract')
            elif self.type == FundManagementType.DEBIT:
                update_system_balance(self.amount, operation='add')
        super().delete(*args, **kwargs)


# MySetting Model (Singleton)
class MySetting(TimeStampedModel):
    membership_deposit_date = models.IntegerField(
        help_text='Day of month for membership deposits (1-31)',
        default=1
    )
    loan_interest_payment_date = models.IntegerField(
        help_text='Day of month for loan interest payments (1-31)',
        default=1
    )
    loan_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Default loan interest rate in percentage',
        default=Decimal('10.00')
    )
    loan_timeline = models.IntegerField(
        help_text='Default loan timeline in months',
        default=12
    )
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # App Update Management Fields
    latest_app_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Latest app version name (e.g., "1.0.1")',
        default='1.0.0'
    )
    latest_version_code = models.IntegerField(
        help_text='Latest app version code (e.g., 1, 2, 3...)',
        default=1
    )
    apk_file = models.FileField(
        upload_to='apk/',
        blank=True,
        null=True,
        help_text='Upload APK file for app updates'
    )
    update_message = models.TextField(
        blank=True,
        null=True,
        help_text='Message shown to users when update is available',
        default='A new version is available with bug fixes and improvements.'
    )
    release_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Release notes describing what\'s new in the update',
        default='Bug fixes and performance improvements'
    )
    mandatory_update = models.BooleanField(
        default=False,
        help_text='Mark this update as mandatory (users cannot skip)'
    )
    
    # Penalty Settings
    default_penalty_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Default penalty amount per month (compounds by doubling each month)',
        default=Decimal('1000.00')
    )
    penalty_grace_period_days = models.IntegerField(
        help_text='Number of days after due date before penalty is applied',
        default=0
    )

    class Meta:
        verbose_name = 'My Setting'
        verbose_name_plural = 'My Settings'

    def __str__(self):
        return 'System Settings'

    def clean(self):
        super().clean()
        # Validate day of month (1-31)
        if self.membership_deposit_date < 1 or self.membership_deposit_date > 31:
            raise ValidationError({
                'membership_deposit_date': 'Day of month must be between 1 and 31.'
            })
        if self.loan_interest_payment_date < 1 or self.loan_interest_payment_date > 31:
            raise ValidationError({
                'loan_interest_payment_date': 'Day of month must be between 1 and 31.'
            })
        # Validate penalty settings
        if self.default_penalty_amount < 0:
            raise ValidationError({
                'default_penalty_amount': 'Penalty amount must be greater than or equal to 0.'
            })
        if self.penalty_grace_period_days < 0:
            raise ValidationError({
                'penalty_grace_period_days': 'Grace period days must be greater than or equal to 0.'
            })

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# LoanPrinciplePayment Model
class LoanPrinciplePayment(TimeStampedModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='principle_payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_date = models.DateField(blank=True, null=True)
    is_custom = models.BooleanField(default=False, help_text='If True, creates cash payment transaction when payment_status is paid')

    class Meta:
        verbose_name = 'Loan Principle Payment'
        verbose_name_plural = 'Loan Principle Payments'
        ordering = ['-paid_date', '-created_at']

    def __str__(self):
        return f"{self.loan.user.name} - {self.amount} - {self.paid_date}"

    def save(self, *args, **kwargs):
        # Auto-update paid_date when status changes to paid
        if self.payment_status == PaymentStatus.PAID and not self.paid_date:
            self.paid_date = timezone.now().date()
        
        # Ensure is_custom has a default value if not set
        if not hasattr(self, 'is_custom') or self.is_custom is None:
            self.is_custom = False
        
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_amount = None
        
        if not is_new:
            try:
                old_instance = LoanPrinciplePayment.objects.get(pk=self.pk)
                old_status = old_instance.payment_status
                old_amount = old_instance.amount
            except LoanPrinciplePayment.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Note: Loan principle payments no longer affect system balance
        
        # Create cash payment transaction when payment is marked as paid and is_custom is True
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID and self.is_custom:
            # Check if status changed to paid (new record with paid status, or status changed from non-paid to paid)
            should_create_transaction = False
            if is_new:
                should_create_transaction = True
            elif old_status != PaymentStatus.PAID:
                should_create_transaction = True
            
            if should_create_transaction:
                # Delete any existing PaymentTransaction for this principle payment
                PaymentTransaction.objects.filter(
                    payment_type='principle',
                    related_object_id=self.pk
                ).delete()
                
                # Create new cash payment transaction
                timestamp = int(timezone.now().timestamp())
                client_txn_id = f"cash_principle_{self.pk}_{timestamp}"
                PaymentTransaction.objects.create(
                    payment_type='principle',
                    related_object_id=self.pk,
                    user=self.loan.user,
                    payment_method='cash',
                    client_txn_id=client_txn_id,
                    amount=self.amount,
                    status='success',
                    txn_date=self.paid_date if self.paid_date else timezone.now().date(),
                    customer_name=self.loan.user.name if self.loan.user.name else None
                )

    def delete(self, *args, **kwargs):
        # Note: Loan principle payments no longer affect system balance
        super().delete(*args, **kwargs)


# Payment Transaction Model (for UPI Gateway)
class PaymentTransaction(TimeStampedModel):
    PAYMENT_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('interest', 'Interest Payment'),
        ('principle', 'Principle Payment'),
        ('penalty', 'Penalty'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('gateway', 'Gateway/UPI'),
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    related_object_id = models.IntegerField(help_text='ID of MonthlyMembershipDeposit, LoanInterestPayment, or LoanPrinciplePayment')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    client_txn_id = models.CharField(max_length=255, unique=True, help_text='Unique transaction ID for gateway')
    order_id = models.BigIntegerField(null=True, blank=True, help_text='Order ID from payment gateway')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='gateway', help_text='Payment method: cash or gateway/UPI')
    gateway_response = models.JSONField(null=True, blank=True, help_text='Full response from payment gateway')
    upi_txn_id = models.CharField(max_length=255, null=True, blank=True, help_text='UPI transaction ID from gateway')
    customer_name = models.CharField(max_length=255, null=True, blank=True, help_text='Customer name from payment gateway')
    txn_date = models.DateField(null=True, blank=True, help_text='Transaction date from gateway')
    
    class Meta:
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client_txn_id']),
            models.Index(fields=['order_id']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.payment_type} - {self.client_txn_id} - {self.status}"


# Push Notification Model
class PushNotification(TimeStampedModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to='notifications/', blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text='When the notification was sent')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', help_text='User who sent the notification')
    
    class Meta:
        verbose_name = 'Push Notification'
        verbose_name_plural = 'Push Notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {'Sent' if self.sent_at else 'Draft'}"
    
    @property
    def is_sent(self):
        """Check if notification has been sent"""
        return self.sent_at is not None


# Popup Model
class Popup(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='popups/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Popup'
        verbose_name_plural = 'Popups'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {'Active' if self.is_active else 'Inactive'}"


# Support Ticket Status Choices
class SupportTicketStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    OPEN = 'open', 'Open'
    RESOLVED = 'resolved', 'Resolved'
    CLOSED = 'closed', 'Closed'


# Support Ticket Model
class SupportTicket(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=SupportTicketStatus.choices, default=SupportTicketStatus.PENDING)
    
    class Meta:
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.subject} - {self.status}"


# Support Ticket Reply Model
class SupportTicketReply(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_ticket_replies')
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='support_tickets/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Support Ticket Reply'
        verbose_name_plural = 'Support Ticket Replies'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Reply to {self.ticket.subject} by {self.user.name}"


# Penalty Model
class Penalty(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='penalties')
    penalty_type = models.CharField(max_length=20, choices=PenaltyType.choices)
    related_object_id = models.IntegerField(help_text='ID of MonthlyMembershipDeposit or LoanInterestPayment')
    related_object_type = models.CharField(max_length=50, help_text='Type of related object: deposit or interest')
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text='Base penalty amount from settings')
    month_number = models.IntegerField(help_text='Month number overdue (1, 2, 3, etc.)')
    penalty_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text='Calculated penalty amount (base × 2^(month-1))')
    total_penalty = models.DecimalField(max_digits=15, decimal_places=2, help_text='Total penalty amount for this payment (cumulative)')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    due_date = models.DateField(help_text='Date when penalty was applied')
    paid_date = models.DateField(blank=True, null=True, help_text='Date when penalty was paid')
    
    class Meta:
        verbose_name = 'Penalty'
        verbose_name_plural = 'Penalties'
        ordering = ['-due_date', '-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['penalty_type']),
            models.Index(fields=['related_object_id']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.get_penalty_type_display()} - Month {self.month_number} - {self.penalty_amount}"
    
    def calculate_penalty_amount(self):
        """Calculate penalty amount: base_amount × 2^(month_number-1)"""
        from decimal import Decimal
        multiplier = Decimal(2) ** (self.month_number - 1)
        return self.base_amount * multiplier
    
    def save(self, *args, **kwargs):
        # Auto-calculate penalty amount if not set
        if not self.penalty_amount or self.penalty_amount == 0:
            self.penalty_amount = self.calculate_penalty_amount()
        
        # Calculate total penalty for this payment
        if self.pk:
            # Get all penalties for this payment
            total = self.__class__.objects.filter(
                penalty_type=self.penalty_type,
                related_object_id=self.related_object_id,
                payment_status=PaymentStatus.PENDING
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('penalty_amount')
            )['total'] or Decimal('0.00')
            self.total_penalty = total + self.penalty_amount
        else:
            # For new penalty, calculate total including this one
            total = self.__class__.objects.filter(
                penalty_type=self.penalty_type,
                related_object_id=self.related_object_id,
                payment_status=PaymentStatus.PENDING
            ).aggregate(
                total=models.Sum('penalty_amount')
            )['total'] or Decimal('0.00')
            self.total_penalty = total + self.penalty_amount
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_total_for_payment(cls, penalty_type, related_object_id):
        """Get total penalty amount for a specific payment"""
        return sum(
            penalty.penalty_amount for penalty in cls.objects.filter(
                penalty_type=penalty_type,
                related_object_id=related_object_id,
                payment_status=PaymentStatus.PENDING
            )
        )


# Helper function to update system balance safely
def update_system_balance(amount, operation='add'):
    """
    Safely update MySetting.balance with database-level locking to prevent race conditions.
    
    Args:
        amount: Decimal amount to add or subtract
        operation: 'add' to increase balance, 'subtract' to decrease balance
    """
    with transaction.atomic():
        # Use select_for_update to lock the row
        settings = MySetting.objects.select_for_update().get(pk=1)
        if operation == 'add':
            settings.balance += amount
        elif operation == 'subtract':
            settings.balance -= amount
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be 'add' or 'subtract'")
        settings.save(update_fields=['balance'])
