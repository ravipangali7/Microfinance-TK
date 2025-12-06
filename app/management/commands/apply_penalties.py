from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, MySetting,
    PaymentStatus, Penalty, PenaltyType
)
from app.services.push_notification_service import send_notification_to_user
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Applies compounding penalties to overdue deposits and interest payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without creating any records (just show what would be created)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Process penalties for a specific user only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculate penalties even if they already exist',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        force = options.get('force', False)
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Applying Penalties'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Current Date: {today}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No records will be created'))
        if user_id:
            self.stdout.write(f'Processing user ID: {user_id}')
        if force:
            self.stdout.write(self.style.WARNING('FORCE MODE - Will recalculate existing penalties'))
        self.stdout.write('')
        
        # Get settings
        settings = MySetting.get_settings()
        penalty_amount = settings.default_penalty_amount or Decimal('1000.00')
        grace_period_days = settings.penalty_grace_period_days or 0
        
        self.stdout.write(f'Penalty Base Amount: {penalty_amount}')
        self.stdout.write(f'Grace Period: {grace_period_days} days')
        self.stdout.write('')
        
        # Process deposits
        self.stdout.write(self.style.SUCCESS('Processing Overdue Deposits...'))
        deposit_stats = self.process_deposits(today, penalty_amount, grace_period_days, user_id, force, dry_run)
        
        # Process interest payments
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Processing Overdue Interest Payments...'))
        interest_stats = self.process_interest_payments(today, penalty_amount, grace_period_days, user_id, force, dry_run)
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('Deposits:')
        self.stdout.write(f'  Processed: {deposit_stats["processed"]}')
        self.stdout.write(f'  Penalties created: {deposit_stats["penalties_created"]}')
        self.stdout.write(f'  Total penalty amount: {deposit_stats["total_amount"]}')
        self.stdout.write('Interest Payments:')
        self.stdout.write(f'  Processed: {interest_stats["processed"]}')
        self.stdout.write(f'  Penalties created: {interest_stats["penalties_created"]}')
        self.stdout.write(f'  Total penalty amount: {interest_stats["total_amount"]}')
        self.stdout.write('')

    def process_deposits(self, today, penalty_amount, grace_period_days, user_id, force, dry_run):
        """Process overdue deposits and apply penalties"""
        stats = {
            'processed': 0,
            'penalties_created': 0,
            'total_amount': Decimal('0.00')
        }
        
        # Find overdue deposits
        query = MonthlyMembershipDeposit.objects.filter(
            payment_status=PaymentStatus.PENDING
        ).select_related('user')
        
        if user_id:
            query = query.filter(user_id=user_id)
        
        overdue_deposits = []
        for deposit in query:
            due_date = deposit.date
            penalty_start_date = due_date + timedelta(days=grace_period_days)
            
            if today > penalty_start_date:
                overdue_deposits.append(deposit)
        
        for deposit in overdue_deposits:
            stats['processed'] += 1
            due_date = deposit.date
            penalty_start_date = due_date + timedelta(days=grace_period_days)
            
            # Calculate months overdue
            months_overdue = self.calculate_months_overdue(penalty_start_date, today)
            
            if months_overdue <= 0:
                continue
            
            # Get existing penalties for this deposit
            existing_penalties = Penalty.objects.filter(
                penalty_type=PenaltyType.DEPOSIT,
                related_object_id=deposit.pk
            )
            
            if not force:
                # Get existing month numbers
                existing_months = set(existing_penalties.values_list('month_number', flat=True))
            else:
                existing_months = set()
            
            # Create penalties for missing months
            for month_num in range(1, months_overdue + 1):
                if month_num in existing_months and not force:
                    continue
                
                # Calculate penalty amount for this month
                penalty_amt = penalty_amount * (Decimal(2) ** (month_num - 1))
                
                # Calculate due date for this penalty (first day of the month after due date)
                penalty_due_date = penalty_start_date + relativedelta(months=month_num - 1)
                penalty_due_date = penalty_due_date.replace(day=1)
                
                if not dry_run:
                    # Delete existing penalty for this month if force mode
                    if force and month_num in existing_months:
                        existing_penalties.filter(month_number=month_num).delete()
                    
                    # Create penalty
                    penalty = Penalty.objects.create(
                        user=deposit.user,
                        penalty_type=PenaltyType.DEPOSIT,
                        related_object_id=deposit.pk,
                        related_object_type='deposit',
                        base_amount=penalty_amount,
                        month_number=month_num,
                        penalty_amount=penalty_amt,
                        payment_status=PaymentStatus.PENDING,
                        due_date=penalty_due_date
                    )
                    
                    # Send notification
                    try:
                        send_notification_to_user(
                            deposit.user,
                            'Penalty Applied',
                            f'Penalty of {penalty_amt} applied for overdue deposit (Month {month_num}). Total penalty: {penalty.total_penalty}',
                        )
                    except Exception as e:
                        logger.error(f'Failed to send notification: {e}')
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created penalty: {deposit.user.name} - Deposit #{deposit.pk} - '
                            f'Month {month_num} - Amount: {penalty_amt}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would create penalty: {deposit.user.name} - Deposit #{deposit.pk} - '
                            f'Month {month_num} - Amount: {penalty_amt}'
                        )
                    )
                
                stats['penalties_created'] += 1
                stats['total_amount'] += penalty_amt
        
        return stats

    def process_interest_payments(self, today, penalty_amount, grace_period_days, user_id, force, dry_run):
        """Process overdue interest payments and apply penalties"""
        stats = {
            'processed': 0,
            'penalties_created': 0,
            'total_amount': Decimal('0.00')
        }
        
        # Find overdue interest payments
        query = LoanInterestPayment.objects.filter(
            payment_status=PaymentStatus.PENDING
        ).select_related('loan', 'loan__user')
        
        if user_id:
            query = query.filter(loan__user_id=user_id)
        
        overdue_payments = []
        for payment in query:
            # Use paid_date if available, otherwise use a calculated date based on name
            if payment.paid_date:
                due_date = payment.paid_date
            else:
                # Try to parse from name (format: "YYYY MMM")
                try:
                    year_month = payment.name.split()
                    if len(year_month) == 2:
                        year = int(year_month[0])
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month = month_names.index(year_month[1]) + 1
                        # Use the payment date from settings or default to 1st
                        settings = MySetting.get_settings()
                        day = settings.loan_interest_payment_date or 1
                        due_date = date(year, month, min(day, 28))
                    else:
                        due_date = payment.created_at.date()
                except (ValueError, IndexError, AttributeError):
                    due_date = payment.created_at.date()
            
            penalty_start_date = due_date + timedelta(days=grace_period_days)
            
            if today > penalty_start_date:
                overdue_payments.append(payment)
        
        for payment in overdue_payments:
            stats['processed'] += 1
            
            # Determine due date
            if payment.paid_date:
                due_date = payment.paid_date
            else:
                try:
                    year_month = payment.name.split()
                    if len(year_month) == 2:
                        year = int(year_month[0])
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month = month_names.index(year_month[1]) + 1
                        settings = MySetting.get_settings()
                        day = settings.loan_interest_payment_date or 1
                        due_date = date(year, month, min(day, 28))
                    else:
                        due_date = payment.created_at.date()
                except (ValueError, IndexError, AttributeError):
                    due_date = payment.created_at.date()
            
            penalty_start_date = due_date + timedelta(days=grace_period_days)
            
            # Calculate months overdue
            months_overdue = self.calculate_months_overdue(penalty_start_date, today)
            
            if months_overdue <= 0:
                continue
            
            # Get existing penalties for this payment
            existing_penalties = Penalty.objects.filter(
                penalty_type=PenaltyType.INTEREST,
                related_object_id=payment.pk
            )
            
            if not force:
                # Get existing month numbers
                existing_months = set(existing_penalties.values_list('month_number', flat=True))
            else:
                existing_months = set()
            
            # Create penalties for missing months
            for month_num in range(1, months_overdue + 1):
                if month_num in existing_months and not force:
                    continue
                
                # Calculate penalty amount for this month
                penalty_amt = penalty_amount * (Decimal(2) ** (month_num - 1))
                
                # Calculate due date for this penalty
                penalty_due_date = penalty_start_date + relativedelta(months=month_num - 1)
                penalty_due_date = penalty_due_date.replace(day=1)
                
                if not dry_run:
                    # Delete existing penalty for this month if force mode
                    if force and month_num in existing_months:
                        existing_penalties.filter(month_number=month_num).delete()
                    
                    # Create penalty
                    penalty = Penalty.objects.create(
                        user=payment.loan.user,
                        penalty_type=PenaltyType.INTEREST,
                        related_object_id=payment.pk,
                        related_object_type='interest',
                        base_amount=penalty_amount,
                        month_number=month_num,
                        penalty_amount=penalty_amt,
                        payment_status=PaymentStatus.PENDING,
                        due_date=penalty_due_date
                    )
                    
                    # Send notification
                    try:
                        send_notification_to_user(
                            payment.loan.user,
                            'Penalty Applied',
                            f'Penalty of {penalty_amt} applied for overdue interest payment (Month {month_num}). Total penalty: {penalty.total_penalty}',
                        )
                    except Exception as e:
                        logger.error(f'Failed to send notification: {e}')
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created penalty: {payment.loan.user.name} - Interest Payment #{payment.pk} - '
                            f'Month {month_num} - Amount: {penalty_amt}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would create penalty: {payment.loan.user.name} - Interest Payment #{payment.pk} - '
                            f'Month {month_num} - Amount: {penalty_amt}'
                        )
                    )
                
                stats['penalties_created'] += 1
                stats['total_amount'] += penalty_amt
        
        return stats

    def calculate_months_overdue(self, start_date, end_date):
        """Calculate number of months overdue"""
        if end_date <= start_date:
            return 0
        
        # Calculate difference in months
        delta = relativedelta(end_date, start_date)
        months = delta.years * 12 + delta.months
        
        # If we're past the start of the current month, add 1
        if end_date.day >= start_date.day or delta.days > 0:
            months += 1
        
        return max(0, months)

