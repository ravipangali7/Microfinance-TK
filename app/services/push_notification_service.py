import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from django.utils import timezone
from app.models import User, PushNotification
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (singleton pattern)
_firebase_app = None

def get_firebase_app():
    """Initialize and return Firebase Admin SDK app instance"""
    global _firebase_app
    if _firebase_app is None:
        try:
            # Get path to service account JSON file from settings
            service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', None)
            
            if not service_account_path:
                # Try default location
                base_dir = settings.BASE_DIR
                service_account_path = os.path.join(base_dir, 'firebase-service-account.json')
            
            if not os.path.exists(service_account_path):
                logger.error(f"Firebase service account file not found at: {service_account_path}")
                raise FileNotFoundError(f"Firebase service account file not found. Please download it from Firebase Console and place it at: {service_account_path}")
            
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Firebase Admin SDK: {e}")
            raise
    return _firebase_app


def send_notification_to_user(fcm_token, title, body, image_url=None):
    """
    Send a push notification to a single user
    
    Args:
        fcm_token: FCM token of the user
        title: Notification title
        body: Notification body text
        image_url: Optional image URL for the notification
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not fcm_token:
            logger.warning("FCM token is empty, skipping notification")
            return False
        
        get_firebase_app()
        
        # Build the notification message
        notification = messaging.Notification(
            title=title,
            body=body,
        )
        
        # Build Android-specific config with image
        android_config = None
        apns_config = None
        
        if image_url:
            # Android config with image
            android_notification = messaging.AndroidNotification(
                title=title,
                body=body,
                image=image_url,
            )
            android_config = messaging.AndroidConfig(
                notification=android_notification,
                priority='high',
            )
            
            # iOS config with image
            apns_notification = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        badge=1,
                    ),
                ),
                fcm_options=messaging.APNSFCMOptions(
                    image=image_url,
                ),
            )
            apns_config = apns_notification
        
        # Create the message
        message = messaging.Message(
            notification=notification,
            token=fcm_token,
            android=android_config,
            apns=apns_config,
        )
        
        # Send the message
        response = messaging.send(message)
        logger.info(f"Successfully sent notification to token {fcm_token[:20]}... Response: {response}")
        return True
        
    except messaging.UnregisteredError:
        logger.warning(f"FCM token {fcm_token[:20]}... is unregistered/invalid")
        return False
    except Exception as e:
        logger.error(f"Error sending notification to user: {e}")
        return False


def send_notification_to_all_users(title, body, image_url=None):
    """
    Send a push notification to all users who have FCM tokens
    
    Args:
        title: Notification title
        body: Notification body text
        image_url: Optional image URL for the notification
    
    Returns:
        dict: Statistics about the send operation
            {
                'total_users': int,
                'successful': int,
                'failed': int,
                'invalid_tokens': int
            }
    """
    try:
        get_firebase_app()
        
        # Get all users with FCM tokens
        users = User.objects.exclude(fcm_token__isnull=True).exclude(fcm_token='')
        
        stats = {
            'total_users': users.count(),
            'successful': 0,
            'failed': 0,
            'invalid_tokens': 0
        }
        
        # Send to each user
        for user in users:
            if send_notification_to_user(user.fcm_token, title, body, image_url):
                stats['successful'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Notification sent to all users. Stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error sending notification to all users: {e}")
        raise


def send_push_notification(notification_obj, sent_by_user):
    """
    Send a PushNotification object to all users and update its status
    
    Args:
        notification_obj: PushNotification instance
        sent_by_user: User who is sending the notification
    
    Returns:
        dict: Statistics about the send operation
    """
    try:
        # Get image URL if image exists
        image_url = None
        if notification_obj.image:
            # Construct full URL for the image
            # Use settings to get the base URL
            from django.conf import settings
            base_url = getattr(settings, 'UPI_PAYMENT_REDIRECT_URL_BASE', 'https://microfinance.sewabyapar.com')
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            # Remove leading slash from media_url if present
            if media_url.startswith('/'):
                media_url = media_url[1:]
            # Construct full URL
            image_url = f"{base_url}/{media_url}{notification_obj.image.name}"
            logger.info(f"Image URL: {image_url}")
        
        # Send notification
        stats = send_notification_to_all_users(
            title=notification_obj.title,
            body=notification_obj.body,
            image_url=image_url
        )
        
        # Update notification object
        notification_obj.sent_at = timezone.now()
        notification_obj.sent_by = sent_by_user
        notification_obj.save()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        raise

