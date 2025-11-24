import requests
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from app.models import PaymentTransaction, MonthlyMembershipDeposit, LoanInterestPayment, User


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
        
        # Prepare request body
        # Include client_txn_id in redirect URL for callback
        redirect_url_with_params = f"{redirect_url}?client_txn_id={client_txn_id}"
        
        request_data = {
            "key": settings.UPI_PAYMENT_GATEWAY_KEY,
            "client_txn_id": client_txn_id,
            "amount": str(int(amount)),  # Amount as string, in rupees (no paise)
            "p_info": "Membership Deposit" if payment_type == 'deposit' else "Loan Interest Payment",
            "customer_name": user.name,
            "customer_email": user.email or f"{user.phone}@microfinance.local",
            "customer_mobile": user.phone.replace('+', '').replace(' ', ''),
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
            
            return True
        elif gateway_status in ['failed', 'cancelled']:
            payment_transaction.status = gateway_status
            payment_transaction.gateway_response = status_response.get('full_data', {})
            payment_transaction.save()
            return False
        
        return False

