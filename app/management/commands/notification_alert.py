from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import (
    MonthlyMembershipDeposit, LoanInterestPayment, PaymentStatus, Penalty
)
from app.services.push_notification_service import send_notification_to_user
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sends push notifications to users for pending membership deposits, loan interest payments, and penalties'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending notifications (just show what would be sent)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Sending Payment Reminder Notifications'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Current Date: {today}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No notifications will be sent'))
        self.stdout.write('')
        
        # Process deposits
        self.stdout.write(self.style.SUCCESS('Processing Pending Membership Deposits...'))
        deposit_stats = self.send_deposit_notifications(dry_run)
        
        # Process interest payments
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Processing Pending Loan Interest Payments...'))
        interest_stats = self.send_interest_notifications(dry_run)
        
        # Process penalties
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Processing Pending Penalties...'))
        penalty_stats = self.send_penalty_notifications(dry_run)
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('Membership Deposits:')
        self.stdout.write(f'  Total pending: {deposit_stats["total"]}')
        self.stdout.write(f'  Notifications sent: {deposit_stats["sent"]}')
        self.stdout.write(f'  Skipped (no FCM token): {deposit_stats["skipped"]}')
        self.stdout.write(f'  Failed: {deposit_stats["failed"]}')
        self.stdout.write('')
        self.stdout.write('Loan Interest Payments:')
        self.stdout.write(f'  Total pending: {interest_stats["total"]}')
        self.stdout.write(f'  Notifications sent: {interest_stats["sent"]}')
        self.stdout.write(f'  Skipped (no FCM token): {interest_stats["skipped"]}')
        self.stdout.write(f'  Failed: {interest_stats["failed"]}')
        self.stdout.write('')
        self.stdout.write('Penalties:')
        self.stdout.write(f'  Total pending: {penalty_stats["total"]}')
        self.stdout.write(f'  Notifications sent: {penalty_stats["sent"]}')
        self.stdout.write(f'  Skipped (no FCM token): {penalty_stats["skipped"]}')
        self.stdout.write(f'  Failed: {penalty_stats["failed"]}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def send_deposit_notifications(self, dry_run):
        """Send notifications for pending membership deposits"""
        stats = {
            'total': 0,
            'sent': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Query all pending deposits with related user and membership
        pending_deposits = MonthlyMembershipDeposit.objects.filter(
            payment_status=PaymentStatus.PENDING
        ).select_related('user', 'membership')
        
        stats['total'] = pending_deposits.count()
        
        for deposit in pending_deposits:
            user = deposit.user
            
            # Check if user has FCM token
            if not user.fcm_token:
                stats['skipped'] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊘ Skipped: {user.name} - No FCM token - '
                        f'Deposit: Rs. {deposit.amount} for {deposit.membership.name} - {deposit.name}'
                    )
                )
                continue
            
            # Format notification message
            title = "Pending Membership Deposit"
            body = (
                f"You have a pending membership deposit of Rs. {deposit.amount} "
                f"for {deposit.membership.name} - {deposit.name} (Due: {deposit.date})"
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Would send: {user.name} - {title} - {body}'
                    )
                )
                stats['sent'] += 1
            else:
                try:
                    success = send_notification_to_user(
                        fcm_token=user.fcm_token,
                        title=title,
                        body=body
                    )
                    if success:
                        stats['sent'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent: {user.name} - Deposit: Rs. {deposit.amount} '
                                f'for {deposit.membership.name} - {deposit.name}'
                            )
                        )
                    else:
                        stats['failed'] += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed: {user.name} - Deposit: Rs. {deposit.amount} '
                                f'for {deposit.membership.name} - {deposit.name}'
                            )
                        )
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"Error sending deposit notification to {user.name}: {e}")
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error: {user.name} - {str(e)}'
                        )
                    )
        
        return stats

    def send_interest_notifications(self, dry_run):
        """Send notifications for pending loan interest payments"""
        stats = {
            'total': 0,
            'sent': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Query all pending interest payments with related loan and user
        pending_payments = LoanInterestPayment.objects.filter(
            payment_status=PaymentStatus.PENDING
        ).select_related('loan', 'loan__user')
        
        stats['total'] = pending_payments.count()
        
        for payment in pending_payments:
            user = payment.loan.user
            
            # Check if user has FCM token
            if not user.fcm_token:
                stats['skipped'] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊘ Skipped: {user.name} - No FCM token - '
                        f'Interest: Rs. {payment.amount} for Loan #{payment.loan.id} - {payment.name}'
                    )
                )
                continue
            
            # Format notification message
            title = "Pending Loan Interest Payment"
            due_date = payment.paid_date if payment.paid_date else "N/A"
            body = (
                f"You have a pending loan interest payment of Rs. {payment.amount} "
                f"for Loan #{payment.loan.id} - {payment.name} (Due: {due_date})"
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Would send: {user.name} - {title} - {body}'
                    )
                )
                stats['sent'] += 1
            else:
                try:
                    success = send_notification_to_user(
                        fcm_token=user.fcm_token,
                        title=title,
                        body=body
                    )
                    if success:
                        stats['sent'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent: {user.name} - Interest: Rs. {payment.amount} '
                                f'for Loan #{payment.loan.id} - {payment.name}'
                            )
                        )
                    else:
                        stats['failed'] += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed: {user.name} - Interest: Rs. {payment.amount} '
                                f'for Loan #{payment.loan.id} - {payment.name}'
                            )
                        )
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"Error sending interest notification to {user.name}: {e}")
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error: {user.name} - {str(e)}'
                        )
                    )
        
        return stats

    def send_penalty_notifications(self, dry_run):
        """Send notifications for pending penalties"""
        stats = {
            'total': 0,
            'sent': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # Query all pending penalties with related user
        pending_penalties = Penalty.objects.filter(
            payment_status=PaymentStatus.PENDING
        ).select_related('user')
        
        stats['total'] = pending_penalties.count()
        
        for penalty in pending_penalties:
            user = penalty.user
            
            # Check if user has FCM token
            if not user.fcm_token:
                stats['skipped'] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊘ Skipped: {user.name} - No FCM token - '
                        f'Penalty: Rs. {penalty.penalty_amount} ({penalty.get_penalty_type_display()}) - Month {penalty.month_number}'
                    )
                )
                continue
            
            # Format notification message
            title = "Pending Penalty Payment"
            penalty_type_display = penalty.get_penalty_type_display()
            body = (
                f"You have a pending penalty of Rs. {penalty.penalty_amount} "
                f"for {penalty_type_display} (Month {penalty.month_number}). "
                f"Total penalty due: Rs. {penalty.total_penalty} (Due: {penalty.due_date})"
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Would send: {user.name} - {title} - {body}'
                    )
                )
                stats['sent'] += 1
            else:
                try:
                    success = send_notification_to_user(
                        fcm_token=user.fcm_token,
                        title=title,
                        body=body
                    )
                    if success:
                        stats['sent'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent: {user.name} - Penalty: Rs. {penalty.penalty_amount} '
                                f'({penalty_type_display}) - Month {penalty.month_number}'
                            )
                        )
                    else:
                        stats['failed'] += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed: {user.name} - Penalty: Rs. {penalty.penalty_amount} '
                                f'({penalty_type_display}) - Month {penalty.month_number}'
                            )
                        )
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"Error sending penalty notification to {user.name}: {e}")
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error: {user.name} - {str(e)}'
                        )
                    )
        
        return stats

