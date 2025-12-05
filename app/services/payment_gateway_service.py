import requests
import json
from decimal import Decimal
from urllib.parse import quote
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from app.models import PaymentTransaction, MonthlyMembershipDeposit, LoanInterestPayment, LoanPrinciplePayment, User


class PaymentGatewayService:
    """Service to handle UPI payment gateway operations"""
    
    @staticmethod
    def generate_client_txn_id(payment_type, payment_id):
        """Generate unique client transaction ID"""
        timestamp = int(timezone.now().timestamp())
        return f"{payment_type}_{payment_id}_{timestamp}"
    
    @staticmethod
    def create_payment_order(payment_type, payment_id, user, amount, redirect_url):
        """
        Create payment order with ekqr.in gateway
        
        Args:
            payment_type: 'deposit' or 'interest'
            payment_id: ID of MonthlyMembershipDeposit or LoanInterestPayment
            user: User object
            amount: Payment amount
            redirect_url: URL to redirect after payment
        
        Returns:
            dict with order_id, payment_url, upi_intent links
        """
        client_txn_id = PaymentGatewayService.generate_client_txn_id(payment_type, payment_id)
        
        # Validate user fields
        if not user.name:
            print(f"[ERROR] PaymentGatewayService.create_payment_order: User {user.id} missing name")
            return {
                'success': False,
                'error': 'User name is required for payment processing',
            }
        
        if not user.phone:
            print(f"[ERROR] PaymentGatewayService.create_payment_order: User {user.id} missing phone")
            return {
                'success': False,
                'error': 'User phone number is required for payment processing',
            }
        
        # Prepare request body
        # Include client_txn_id in redirect URL for callback
        # URL-encode the client_txn_id to handle special characters and prevent truncation
        encoded_client_txn_id = quote(client_txn_id, safe='')
        redirect_url_with_params = f"{redirect_url}?client_txn_id={encoded_client_txn_id}"
        
        # Safely process phone number
        phone_cleaned = str(user.phone).replace('+', '').replace(' ', '') if user.phone else ''
        
        # Set payment info text based on payment type
        if payment_type == 'deposit':
            p_info = "Membership Deposit"
        elif payment_type == 'interest':
            p_info = "Loan Interest Payment"
        else:  # principle
            p_info = "Loan Principle Payment"
        
        request_data = {
            "key": settings.UPI_PAYMENT_GATEWAY_KEY,
            "client_txn_id": client_txn_id,
            "amount": str(int(amount)),  # Amount as string, in rupees (no paise)
            "p_info": p_info,
            "customer_name": user.name,
            "customer_email": user.email or f"{phone_cleaned}@microfinance.local",
            "customer_mobile": phone_cleaned,
            "redirect_url": redirect_url_with_params,
            "udf1": payment_type,
            "udf2": str(payment_id),
            "udf3": str(user.id),
        }
        
        try:
            response = requests.post(
                settings.UPI_PAYMENT_GATEWAY_CREATE_ORDER_URL,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') and result.get('data'):
                data = result['data']
                return {
                    'success': True,
                    'order_id': data.get('order_id'),
                    'payment_url': data.get('payment_url'),
                    'upi_id_hash': data.get('upi_id_hash'),
                    'upi_intent': data.get('upi_intent', {}),
                    'client_txn_id': client_txn_id,
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', 'Failed to create payment order'),
                }
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] PaymentGatewayService.create_payment_order: RequestException")
            print(f"[ERROR] User ID: {user.id}, Client TXN ID: {client_txn_id}")
            print(f"[ERROR] Exception: {str(e)}")
            return {
                'success': False,
                'error': f'Payment gateway error: {str(e)}',
            }
        except Exception as e:
            import traceback
            print(f"[ERROR] PaymentGatewayService.create_payment_order: Unexpected error")
            print(f"[ERROR] User ID: {user.id}, Client TXN ID: {client_txn_id}")
            print(f"[ERROR] Exception: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
            }
    
    @staticmethod
    def check_payment_status(client_txn_id, txn_date=None):
        """
        Check payment status from gateway
        
        Args:
            client_txn_id: Client transaction ID
            txn_date: Transaction date in DD-MM-YYYY format (optional)
        
        Returns:
            dict with payment status and details
        """
        if not txn_date:
            # Use today's date in DD-MM-YYYY format
            txn_date = timezone.now().strftime('%d-%m-%Y')
        
        request_data = {
            "key": settings.UPI_PAYMENT_GATEWAY_KEY,
            "client_txn_id": client_txn_id,
            "txn_date": txn_date,
        }
        
        try:
            response = requests.post(
                settings.UPI_PAYMENT_GATEWAY_CHECK_STATUS_URL,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') and result.get('data'):
                data = result['data']
                return {
                    'success': True,
                    'status': data.get('status'),  # 'success', 'pending', 'failed'
                    'order_id': data.get('id'),
                    'amount': data.get('amount'),
                    'upi_txn_id': data.get('upi_txn_id'),
                    'customer_name': data.get('customer_name'),
                    'customer_email': data.get('customer_email'),
                    'customer_mobile': data.get('customer_mobile'),
                    'txnAt': data.get('txnAt'),
                    'createdAt': data.get('createdAt'),
                    'full_data': data,
                }
            else:
                return {
                    'success': False,
                    'error': result.get('msg', 'Transaction not found'),
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Payment gateway error: {str(e)}',
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
            }
    
    @staticmethod
    def create_payment_transaction_on_success(client_txn_id, payment_type, payment_id, status_response):
        """
        Create PaymentTransaction when gateway payment is successful
        
        Args:
            client_txn_id: Client transaction ID
            payment_type: 'deposit', 'interest', or 'principle'
            payment_id: ID of related payment object
            status_response: Response from check_payment_status with success status
        
        Returns:
            PaymentTransaction instance
        """
        # Get the related payment object to get user and amount
        user = None
        amount = Decimal('0.00')
        
        if payment_type == 'deposit':
            try:
                deposit = MonthlyMembershipDeposit.objects.get(pk=payment_id)
                user = deposit.user
                amount = deposit.amount
            except MonthlyMembershipDeposit.DoesNotExist:
                print(f"[ERROR] create_payment_transaction_on_success: Deposit {payment_id} not found")
                return None
        elif payment_type == 'interest':
            try:
                interest_payment = LoanInterestPayment.objects.get(pk=payment_id)
                user = interest_payment.loan.user
                amount = interest_payment.amount
            except LoanInterestPayment.DoesNotExist:
                print(f"[ERROR] create_payment_transaction_on_success: Interest payment {payment_id} not found")
                return None
        elif payment_type == 'principle':
            try:
                principle_payment = LoanPrinciplePayment.objects.get(pk=payment_id)
                user = principle_payment.loan.user
                amount = principle_payment.amount
            except LoanPrinciplePayment.DoesNotExist:
                print(f"[ERROR] create_payment_transaction_on_success: Principle payment {payment_id} not found")
                return None
        
        if not user:
            print(f"[ERROR] create_payment_transaction_on_success: Could not determine user for payment_type={payment_type}, payment_id={payment_id}")
            return None
        
        # Create PaymentTransaction with success status
        try:
            payment_transaction = PaymentTransaction.objects.create(
                payment_type=payment_type,
                related_object_id=payment_id,
                user=user,
                client_txn_id=client_txn_id,
                order_id=status_response.get('order_id'),
                amount=amount,
                status='success',
                payment_method='gateway',
                upi_txn_id=status_response.get('upi_txn_id'),
                customer_name=status_response.get('customer_name'),
                gateway_response=status_response.get('full_data', {}),
            )
            
            # Set transaction date
            if status_response.get('txnAt'):
                try:
                    from datetime import datetime
                    txn_date = datetime.strptime(status_response['txnAt'], '%Y-%m-%d').date()
                    payment_transaction.txn_date = txn_date
                except:
                    payment_transaction.txn_date = timezone.now().date()
            else:
                payment_transaction.txn_date = timezone.now().date()
            
            payment_transaction.save()
            
            # Update the related payment object to 'paid'
            if payment_type == 'deposit':
                try:
                    deposit = MonthlyMembershipDeposit.objects.get(pk=payment_id)
                    deposit.payment_status = 'paid'
                    if not deposit.paid_date:
                        deposit.paid_date = payment_transaction.txn_date
                    deposit.save()
                except MonthlyMembershipDeposit.DoesNotExist:
                    pass
            elif payment_type == 'interest':
                try:
                    interest_payment = LoanInterestPayment.objects.get(pk=payment_id)
                    interest_payment.payment_status = 'paid'
                    if not interest_payment.paid_date:
                        interest_payment.paid_date = payment_transaction.txn_date
                    interest_payment.save()
                except LoanInterestPayment.DoesNotExist:
                    pass
            elif payment_type == 'principle':
                try:
                    principle_payment = LoanPrinciplePayment.objects.get(pk=payment_id)
                    principle_payment.payment_status = 'paid'
                    if not principle_payment.paid_date:
                        principle_payment.paid_date = payment_transaction.txn_date
                    principle_payment.save()
                except LoanPrinciplePayment.DoesNotExist:
                    pass
            
            print(f"[INFO] create_payment_transaction_on_success: Created PaymentTransaction {payment_transaction.id} for {payment_type} {payment_id}")
            return payment_transaction
            
        except Exception as e:
            import traceback
            print(f"[ERROR] create_payment_transaction_on_success: Exception creating PaymentTransaction")
            print(f"[ERROR] Payment Type: {payment_type}, Payment ID: {payment_id}")
            print(f"[ERROR] Exception: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def update_payment_status(payment_transaction, status_response):
        """
        Update payment status based on gateway response
        
        Args:
            payment_transaction: PaymentTransaction instance
            status_response: Response from check_payment_status
        
        Returns:
            bool: True if payment was successfully updated
        """
        if not status_response.get('success'):
            return False
        
        gateway_status = status_response.get('status', '').lower()
        
        # Update transaction status
        if gateway_status == 'success':
            payment_transaction.status = 'success'
            payment_transaction.upi_txn_id = status_response.get('upi_txn_id')
            payment_transaction.customer_name = status_response.get('customer_name')
            payment_transaction.gateway_response = status_response.get('full_data', {})
            if status_response.get('txnAt'):
                try:
                    # Parse date from gateway response
                    from datetime import datetime
                    txn_date = datetime.strptime(status_response['txnAt'], '%Y-%m-%d').date()
                    payment_transaction.txn_date = txn_date
                except:
                    payment_transaction.txn_date = timezone.now().date()
            payment_transaction.save()
            
            # Update the related payment object
            if payment_transaction.payment_type == 'deposit':
                try:
                    deposit = MonthlyMembershipDeposit.objects.get(pk=payment_transaction.related_object_id)
                    deposit.payment_status = 'paid'
                    deposit.save()
                except MonthlyMembershipDeposit.DoesNotExist:
                    pass
            elif payment_transaction.payment_type == 'interest':
                try:
                    interest_payment = LoanInterestPayment.objects.get(pk=payment_transaction.related_object_id)
                    interest_payment.payment_status = 'paid'
                    interest_payment.save()
                except LoanInterestPayment.DoesNotExist:
                    pass
            elif payment_transaction.payment_type == 'principle':
                try:
                    principle_payment = LoanPrinciplePayment.objects.get(pk=payment_transaction.related_object_id)
                    principle_payment.payment_status = 'paid'
                    principle_payment.save()
                except LoanPrinciplePayment.DoesNotExist:
                    pass
            
            return True
        elif gateway_status in ['failed', 'cancelled']:
            payment_transaction.status = gateway_status
            payment_transaction.gateway_response = status_response.get('full_data', {})
            payment_transaction.save()
            return False
        
        return False

