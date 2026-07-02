import os
import logging
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def _initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(settings.BASE_DIR, settings.FIREBASE_CREDENTIALS_PATH)
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully.")
            else:
                logger.warning(f"Firebase credentials not found at {cred_path}. Push notifications will fail.")
        except Exception as e:
            logger.error(f"Error initializing Firebase Admin SDK: {e}")

_initialize_firebase()

def send_push_notification(fcm_token, title, body):
    """
    Sends a push message to one device token.
    Returns True on success, False on failure.
    """
    if not fcm_token:
        logger.error("No FCM token provided.")
        return False
        
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK is not initialized.")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=fcm_token,
        )
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification to {fcm_token}: {e}")
        return False
