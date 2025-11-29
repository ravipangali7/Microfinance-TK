from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import IntegrityError
from datetime import datetime
from app.models import (
    PaymentTransaction, MonthlyMembershipDeposit, 
    LoanInterestPayment, LoanPrinciplePayment, User
)
from app.services.payment_gateway_service import PaymentGatewayService
from decimal import Decimal
import traceback


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order_api(request):
    """
    Create payment order with UPI gateway
    
    Request body:
    {
        "payment_type": "deposit", "interest", or "principle",
        "payment_id": <id of deposit, interest payment, or principle payment>,
        "amount": <amount>
    }
    """
    payment_type = request.data.get('payment_type')
    payment_id = request.data.get('payment_id')
    amount = request.data.get('amount')
    
    # Validate inputs
    if not payment_type or payment_type not in ['deposit', 'interest', 'principle']:
        return Response(
            {'error': 'Invalid payment_type. Must be "deposit", "interest", or "principle".'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not payment_id:
        return Response(
            {'error': 'payment_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not amount:
        return Response(
            {'error': 'amount is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        amount_decimal = Decimal(str(amount))
    except:
        return Response(
            {'error': 'Invalid amount format.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get the payment object
    if payment_type == 'deposit':
        payment_obj = get_object_or_404(MonthlyMembershipDeposit, pk=payment_id)
        # Verify user owns this deposit
        if payment_obj.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own deposits.'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif payment_type == 'interest':
        payment_obj = get_object_or_404(LoanInterestPayment, pk=payment_id)
        # Verify user owns this loan
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own loan payments.'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:  # principle
        payment_obj = get_object_or_404(LoanPrinciplePayment, pk=payment_id)
        # Verify user owns this loan
        if payment_obj.loan.user.id != request.user.id:
            return Response(
                {'error': 'You can only create payment orders for your own loan payments.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Check if payment is already paid
    if payment_obj.payment_status == 'paid':
        return Response(
            {'error': 'This payment has already been completed.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate user fields before processing
    if not request.user.name:
        print(f"[ERROR] create_payment_order_api: User {request.user.id} missing name field")
        return Response(
            {'error': 'User profile is incomplete. Please update your name.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not request.user.phone:
        print(f"[ERROR] create_payment_order_api: User {request.user.id} missing phone field")
        return Response(
            {'error': 'User profile is incomplete. Please update your phone number.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate redirect URL
    redirect_url = f"{settings.UPI_PAYMENT_REDIRECT_URL_BASE}/api/payment/callback/"
    
    # Create payment order
    try:
        order_result = PaymentGatewayService.create_payment_order(
            payment_type=payment_type,
            payment_id=payment_id,
            user=request.user,
            amount=amount_decimal,
            redirect_url=redirect_url
        )
    except Exception as e:
        print(f"[ERROR] create_payment_order_api: Exception in PaymentGatewayService.create_payment_order")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Exception: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return Response(
            {'error': 'Failed to create payment order. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    if not order_result.get('success'):
        error_msg = order_result.get('error', 'Failed to create payment order')
        print(f"[ERROR] create_payment_order_api: Payment gateway returned error")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Gateway Error: {error_msg}")
        return Response(
            {'error': error_msg},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Create payment transaction record with exception handling
    try:
        payment_transaction = PaymentTransaction.objects.create(
            payment_type=payment_type,
            related_object_id=payment_id,
            user=request.user,
            client_txn_id=order_result['client_txn_id'],
            order_id=order_result.get('order_id'),
            amount=amount_decimal,
            status='pending',
            gateway_response={'create_order': order_result}
        )
    except IntegrityError as e:
        # Handle duplicate client_txn_id constraint violation
        print(f"[ERROR] create_payment_order_api: IntegrityError - Duplicate client_txn_id")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Client TXN ID: {order_result.get('client_txn_id')}")
        print(f"[ERROR] Exception: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Try to get existing transaction
        try:
            existing_transaction = PaymentTransaction.objects.get(
                client_txn_id=order_result['client_txn_id']
            )
            print(f"[INFO] Found existing transaction with same client_txn_id: {existing_transaction.id}")
            return Response({
                'success': True,
                'transaction_id': existing_transaction.id,
                'client_txn_id': existing_transaction.client_txn_id,
                'order_id': order_result.get('order_id'),
                'payment_url': order_result.get('payment_url'),
                'upi_intent': order_result.get('upi_intent', {}),
            }, status=status.HTTP_201_CREATED)
        except PaymentTransaction.DoesNotExist:
            return Response(
                {'error': 'Failed to create payment transaction. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        print(f"[ERROR] create_payment_order_api: Exception creating PaymentTransaction")
        print(f"[ERROR] User ID: {request.user.id}, Payment Type: {payment_type}, Payment ID: {payment_id}")
        print(f"[ERROR] Client TXN ID: {order_result.get('client_txn_id')}")
        print(f"[ERROR] Exception: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return Response(
            {'error': 'Failed to create payment transaction. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    print(f"[INFO] create_payment_order_api: Successfully created payment transaction {payment_transaction.id}")
    return Response({
        'success': True,
        'transaction_id': payment_transaction.id,
        'client_txn_id': payment_transaction.client_txn_id,
        'order_id': order_result.get('order_id'),
        'payment_url': order_result.get('payment_url'),
        'upi_intent': order_result.get('upi_intent', {}),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_payment_status_api(request):
    """
    Check payment status from gateway
    
    Request body:
    {
        "client_txn_id": "<client transaction id>",
        "txn_date": "DD-MM-YYYY" (optional)
    }
    """
    client_txn_id = request.data.get('client_txn_id')
    txn_date = request.data.get('txn_date')
    
    if not client_txn_id:
        return Response(
            {'error': 'client_txn_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get payment transaction
    try:
        payment_transaction = PaymentTransaction.objects.get(client_txn_id=client_txn_id)
        # Verify user owns this transaction
        if payment_transaction.user.id != request.user.id:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
    except PaymentTransaction.DoesNotExist:
        return Response(
            {'error': 'Payment transaction not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check status from gateway
    status_result = PaymentGatewayService.check_payment_status(
        client_txn_id=client_txn_id,
        txn_date=txn_date
    )
    
    if not status_result.get('success'):
        return Response({
            'success': False,
            'status': payment_transaction.status,
            'error': status_result.get('error', 'Failed to check payment status'),
        }, status=status.HTTP_200_OK)
    
    # Update payment status if successful
    gateway_status = status_result.get('status', '').lower()
    if gateway_status == 'success':
        PaymentGatewayService.update_payment_status(payment_transaction, status_result)
        payment_transaction.refresh_from_db()
    
    return Response({
        'success': True,
        'status': gateway_status,
        'transaction_status': payment_transaction.status,
        'order_id': status_result.get('order_id'),
        'upi_txn_id': status_result.get('upi_txn_id'),
        'amount': float(status_result.get('amount', 0)),
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([])  # No authentication required for callback
def payment_callback_api(request):
    """
    Payment callback endpoint for redirect_url
    This is called by the payment gateway after payment
    """
    client_txn_id = request.GET.get('client_txn_id') or request.data.get('client_txn_id')
    
    if not client_txn_id:
        # Return a simple HTML page with error
        return Response(
            '<html><body><h1>Payment Error</h1><p>Invalid callback parameters.</p></body></html>',
            content_type='text/html',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get payment transaction
    try:
        payment_transaction = PaymentTransaction.objects.get(client_txn_id=client_txn_id)
    except PaymentTransaction.DoesNotExist:
        return Response(
            '<html><body><h1>Payment Error</h1><p>Transaction not found.</p></body></html>',
            content_type='text/html',
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check payment status
    txn_date = timezone.now().strftime('%d-%m-%Y')
    status_result = PaymentGatewayService.check_payment_status(
        client_txn_id=client_txn_id,
        txn_date=txn_date
    )
    
    # Update payment status if successful
    if status_result.get('success'):
        gateway_status = status_result.get('status', '').lower()
        if gateway_status == 'success':
            PaymentGatewayService.update_payment_status(payment_transaction, status_result)
            payment_transaction.refresh_from_db()
    
    # Return HTML page with result
    if payment_transaction.status == 'success':
        html = f'''
        <html>
        <head>
            <title>Payment Success</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #10B981;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #10B981;
                    margin: 0 0 10px 0;
                }}
                p {{
                    color: #6B7280;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>Payment Successful!</h1>
                <p>Your payment has been processed successfully.</p>
                <p>Transaction ID: {payment_transaction.client_txn_id}</p>
                <p>You can close this window and return to the app.</p>
            </div>
        </body>
        </html>
        '''
    else:
        html = f'''
        <html>
        <head>
            <title>Payment Status</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }}
                .pending-icon {{
                    font-size: 64px;
                    color: #F59E0B;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #F59E0B;
                    margin: 0 0 10px 0;
                }}
                p {{
                    color: #6B7280;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="pending-icon">⏳</div>
                <h1>Payment Pending</h1>
                <p>Your payment is being processed.</p>
                <p>Transaction ID: {payment_transaction.client_txn_id}</p>
                <p>Please check back in a few moments or return to the app.</p>
            </div>
        </body>
        </html>
        '''
    
    return Response(html, content_type='text/html', status=status.HTTP_200_OK)

