from django.conf import settings
from .models import UserProfile, Team
import jwt
import time

def get_JWT_from_backend(user):
    if not user or not user.is_authenticated:
        print("[WARNING] Invalid user profile provided; cannot generate Chatbase token.")
        return None

    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    user_id = user_profile.external_uuid if user_profile else user.id

    if not user_id:
        print("[WARNING] User profile has no external_uuid or id; cannot generate Chatbase token.")
        return None
    
    secret = settings.CHATBASE_SECRET_KEY
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + (60 * 60)
    }

    if user_profile:
        payload["name"] = user_profile.get_display_name()
        payload["phonenumber"] = user_profile.cell_phone

    try:
        token = jwt.encode(payload, secret, algorithm='HS256')
        return token

    except Exception as e:
        print(f"[ERROR] Failed to generate JWT token: {e}")
        return None