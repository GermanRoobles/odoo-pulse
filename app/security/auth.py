import bcrypt
from itsdangerous import URLSafeTimedSerializer
from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_session_token(user_id: int) -> str:
    s = URLSafeTimedSerializer(settings.admin_session_secret)
    return s.dumps({"user_id": user_id})


def verify_session_token(token: str, max_age: int = 86400 * 7):
    s = URLSafeTimedSerializer(settings.admin_session_secret)
    try:
        data = s.loads(token, max_age=max_age)
        return data
    except Exception:
        return None
