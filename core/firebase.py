import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)
_initialized = False

def _init_firebase():
  global _initialized
  if _initialized:
    return True
  
  try:
    # Try environment variable first 
    # (Railway production)
    firebase_creds_b64 = os.environ.get(
      'FIREBASE_CREDENTIALS_BASE64'
    )
    
    if firebase_creds_b64:
      # Decode base64 credentials
      creds_json = base64.b64decode(
        firebase_creds_b64
      ).decode('utf-8')
      creds_dict = json.loads(creds_json)
      cred = credentials.Certificate(
        creds_dict
      )
      logger.info(
        "Firebase: using base64 credentials from environment"
      )
    else:
      # Fall back to local file 
      # (development)
      creds_path = getattr(
        settings,
        'FIREBASE_CREDENTIALS_PATH',
        'firebase-credentials.json'
      )
      if not os.path.isabs(creds_path):
        creds_path = os.path.join(settings.BASE_DIR, creds_path)

      if not os.path.exists(creds_path):
        # Also check for any firebase-adminsdk json file in root
        candidates = [
          f for f in os.listdir(settings.BASE_DIR)
          if 'firebase-adminsdk' in f and f.endswith('.json')
        ]
        if candidates:
          creds_path = os.path.join(settings.BASE_DIR, candidates[0])

      if not os.path.exists(creds_path):
        logger.warning(
          "Firebase credentials not found. Push notifications disabled."
        )
        return False
      cred = credentials.Certificate(
        creds_path
      )
      logger.info(
        "Firebase: using local credentials file"
      )
    
    if not firebase_admin._apps:
      firebase_admin.initialize_app(cred)
    _initialized = True
    return True
    
  except Exception as e:
    logger.error(
      f"Firebase init failed: {e}"
    )
    return False

def send_push_notification(
  fcm_token, title, body
):
  if not _init_firebase():
    return False
  
  try:
    message = messaging.Message(
      notification=messaging.Notification(
        title=title,
        body=body,
      ),
      token=fcm_token,
    )
    messaging.send(message)
    return True
  except Exception as e:
    logger.error(
      f"FCM send failed: {e}"
    )
    return False
