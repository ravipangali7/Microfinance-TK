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


class WithdrawalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


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
        
        # Create cash payment transaction when payment is marked as paid
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID:
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
        
        # Update balance based on loan status changes (disbursement)
        if is_new:
            # New loan: subtract from balance if active (disbursed)
            if self.status == LoanStatus.ACTIVE:
                update_system_balance(self.principal_amount, operation='subtract')
        else:
            # Existing loan: handle status and principal changes
            if old_status != self.status:
                # Status changed
                if old_status == LoanStatus.ACTIVE:
                    # Was active (disbursed), now other status: add back to balance
                    update_system_balance(old_principal, operation='add')
                if self.status == LoanStatus.ACTIVE:
                    # Now active (disbursed): subtract from balance
                    update_system_balance(self.principal_amount, operation='subtract')
            elif self.status == LoanStatus.ACTIVE and old_principal != self.principal_amount:
                # Principal changed while active: adjust balance
                difference = self.principal_amount - old_principal
                if difference > 0:
                    update_system_balance(difference, operation='subtract')
                else:
                    update_system_balance(abs(difference), operation='add')
    
    def get_total_paid_principle(self):
        """Calculate total paid principle from all paid principle payments"""
        return sum(
            payment.amount for payment in self.principle_payments.filter(payment_status=PaymentStatus.PAID)
        )
    
    def get_remaining_principle(self):
        """Calculate remaining principle amount"""
        return self.principal_amount - self.get_total_paid_principle()

    def delete(self, *args, **kwargs):
        # If loan was active (disbursed), add back to balance
        if self.status == LoanStatus.ACTIVE:
            update_system_balance(self.principal_amount, operation='add')
        super().delete(*args, **kwargs)


# LoanInterestPayment Model
class LoanInterestPayment(TimeStampedModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='interest_payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_date = models.DateField(blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, help_text='Auto-generated format: YYYY MMM (e.g., "2025 Oct")')

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
        
        # Create cash payment transaction when payment is marked as paid
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID:
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

    def delete(self, *args, **kwargs):
        # If payment was paid, subtract from balance
        if self.payment_status == PaymentStatus.PAID:
            update_system_balance(self.amount, operation='subtract')
        super().delete(*args, **kwargs)


# OrganizationalWithdrawal Model
class OrganizationalWithdrawal(TimeStampedModel):
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING)
    purpose = models.TextField()

    class Meta:
        verbose_name = 'Organizational Withdrawal'
        verbose_name_plural = 'Organizational Withdrawals'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.amount} - {self.date} - {self.status}"

    def save(self, *args, **kwargs):
        # Track previous state if updating
        is_new = self.pk is None
        old_status = None
        old_amount = None
        
        if not is_new:
            try:
                old_instance = OrganizationalWithdrawal.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_amount = old_instance.amount
            except OrganizationalWithdrawal.DoesNotExist:
                pass
        
        # Save the instance first
        super().save(*args, **kwargs)
        
        # Update balance based on status changes
        if is_new:
            # New withdrawal: subtract from balance if approved
            if self.status == WithdrawalStatus.APPROVED:
                update_system_balance(self.amount, operation='subtract')
        else:
            # Existing withdrawal: handle status and amount changes
            if old_status != self.status:
                # Status changed
                if old_status == WithdrawalStatus.APPROVED:
                    # Was approved, now pending/rejected: add back to balance
                    update_system_balance(old_amount, operation='add')
                if self.status == WithdrawalStatus.APPROVED:
                    # Now approved: subtract from balance
                    update_system_balance(self.amount, operation='subtract')
            elif self.status == WithdrawalStatus.APPROVED and old_amount != self.amount:
                # Amount changed while approved: adjust balance
                difference = self.amount - old_amount
                if difference > 0:
                    update_system_balance(difference, operation='subtract')
                else:
                    update_system_balance(abs(difference), operation='add')

    def delete(self, *args, **kwargs):
        # If withdrawal was approved, add back to balance
        if self.status == WithdrawalStatus.APPROVED:
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
        
        # Create cash payment transaction when payment is marked as paid
        # Only create transaction when status is PAID (never for pending)
        if self.payment_status == PaymentStatus.PAID:
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
        # If payment was paid, subtract from balance
        if self.payment_status == PaymentStatus.PAID:
            update_system_balance(self.amount, operation='subtract')
        super().delete(*args, **kwargs)


# Payment Transaction Model (for UPI Gateway)
class PaymentTransaction(TimeStampedModel):
    PAYMENT_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('interest', 'Interest Payment'),
        ('principle', 'Principle Payment'),
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
