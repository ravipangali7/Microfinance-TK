from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models as django_models
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, MembershipUser, Loan,
    MySetting, PaymentStatus, LoanStatus
)


class Command(BaseCommand):
    help = 'Creates pending deposits and interest payments for missing months'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without creating any records (just show what would be created)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Creating Pending Payments'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Current Date: {today}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No records will be created'))
        self.stdout.write('')
        
        # Get settings
        settings = MySetting.get_settings()
        membership_deposit_date = settings.membership_deposit_date or 10
        loan_interest_payment_date = settings.loan_interest_payment_date or 10
        
        self.stdout.write(f'Membership Deposit Date: Day {membership_deposit_date}')
        self.stdout.write(f'Loan Interest Payment Date: Day {loan_interest_payment_date}')
        self.stdout.write('')
        
        # Process deposits
        self.stdout.write(self.style.SUCCESS('Processing Monthly Membership Deposits...'))
        deposit_count = self.create_pending_deposits(today, membership_deposit_date, dry_run)
        
        # Process interest payments
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Processing Loan Interest Payments...'))
        interest_count = self.create_pending_interest_payments(today, loan_interest_payment_date, dry_run)
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Deposits created: {deposit_count}')
        self.stdout.write(f'Interest payments created: {interest_count}')
        self.stdout.write('')

    def create_pending_deposits(self, today, deposit_date, dry_run):
        """Create pending deposits for missing months"""
        count = 0
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Determine if we should check current month
        check_current_month = today.day >= deposit_date
        
        # Get all membership users
        membership_users = MembershipUser.objects.select_related('user', 'membership').all()
        
        for membership_user in membership_users:
            # Start from membership user created_at
            start_date = membership_user.created_at.date() if membership_user.created_at else today
            
            # Get months to check
            months_to_check = self.get_months_to_check(start_date, today, check_current_month)
            
            for year, month in months_to_check:
                # Check if deposit exists for this year-month (paid or pending)
                # Check by date field or by name as fallback
                month_name = f"{year} {month_names[month - 1]}"
                deposit_exists = MonthlyMembershipDeposit.objects.filter(
                    user=membership_user.user,
                    membership=membership_user.membership
                ).filter(
                    django_models.Q(date__year=year, date__month=month) |
                    django_models.Q(name=month_name)
                ).exists()
                
                if not deposit_exists:
                    # Calculate deposit date for this month
                    try:
                        # Use the deposit_date day, but handle edge cases (e.g., Feb 30)
                        day = min(deposit_date, monthrange(year, month)[1])
                        deposit_date_obj = date(year, month, day)
                    except (ValueError, OverflowError):
                        # Fallback to last day of month
                        deposit_date_obj = date(year, month, monthrange(year, month)[1])
                    
                    # Generate name
                    name = f"{year} {month_names[month - 1]}"
                    
                    if not dry_run:
                        MonthlyMembershipDeposit.objects.create(
                            user=membership_user.user,
                            membership=membership_user.membership,
                            amount=membership_user.membership.amount,
                            date=deposit_date_obj,
                            payment_status=PaymentStatus.PENDING,
                            name=name
                        )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created pending deposit: {membership_user.user.name} - '
                            f'{membership_user.membership.name} - {name}'
                        )
                    )
                    count += 1
        
        return count

    def create_pending_interest_payments(self, today, payment_date, dry_run):
        """Create pending interest payments for missing months"""
        count = 0
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Determine if we should check current month
        check_current_month = today.day >= payment_date
        
        # Get all active/approved loans
        loans = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.APPROVED]
        ).select_related('user')
        
        for loan in loans:
            # Start from loan created_at
            start_date = loan.created_at.date() if loan.created_at else today
            
            # Get months to check
            months_to_check = self.get_months_to_check(start_date, today, check_current_month)
            
            # Calculate monthly interest amount
            if loan.principal_amount and loan.interest_rate:
                monthly_interest = (loan.principal_amount * loan.interest_rate / Decimal('100')) / Decimal('12')
            else:
                monthly_interest = Decimal('0.00')
            
            for year, month in months_to_check:
                # Check if payment exists for this year-month (paid or pending)
                # Check by paid_date if set, or by name as fallback
                month_name = f"{year} {month_names[month - 1]}"
                payment_exists = LoanInterestPayment.objects.filter(
                    loan=loan
                ).filter(
                    django_models.Q(paid_date__year=year, paid_date__month=month) |
                    django_models.Q(name=month_name)
                ).exists()
                
                if not payment_exists:
                    # Calculate payment date for this month
                    try:
                        # Use the payment_date day, but handle edge cases
                        day = min(payment_date, monthrange(year, month)[1])
                        payment_date_obj = date(year, month, day)
                    except (ValueError, OverflowError):
                        # Fallback to last day of month
                        payment_date_obj = date(year, month, monthrange(year, month)[1])
                    
                    # Generate name
                    name = f"{year} {month_names[month - 1]}"
                    
                    if not dry_run:
                        LoanInterestPayment.objects.create(
                            loan=loan,
                            amount=monthly_interest,
                            paid_date=payment_date_obj,
                            payment_status=PaymentStatus.PENDING,
                            name=name
                        )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created pending interest payment: {loan.user.name} - '
                            f'Loan #{loan.id} - {name} - Amount: {monthly_interest}'
                        )
                    )
                    count += 1
        
        return count

    def get_months_to_check(self, start_date, end_date, include_current_month):
        """Get list of (year, month) tuples to check"""
        months = []
        
        # Start from start_date month
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        # Determine end month
        if include_current_month:
            # Include current month (end_date month)
            end = end_month
        else:
            # Exclude current month - go back one month from end_date
            if end_date.month == 1:
                end = end_date.replace(year=end_date.year - 1, month=12, day=1)
            else:
                end = end_date.replace(month=end_date.month - 1, day=1)
            
            # Special case: If start_date is in the current month and we're not checking current month,
            # we should still check the start_date month (current month) if it's the same as start_date
            # This handles the case where membership/loan was created in current month
            if current.year == end_month.year and current.month == end_month.month:
                # Start date is in current month, include it even though we're not checking current month normally
                end = end_month
        
        # Generate all months from start to end (inclusive)
        while current <= end:
            months.append((current.year, current.month))
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return months

