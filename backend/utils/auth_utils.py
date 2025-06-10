import bcrypt
import jwt
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token, create_refresh_token
from config import Config

def hash_password(password: str) -> str:
    """Şifreyi hash'le"""
    salt = bcrypt.gensalt(rounds=Config.BCRYPT_LOG_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Şifreyi doğrula"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_tokens(user_id: str, user_role: str) -> dict:
    """Access ve refresh token oluştur"""
    additional_claims = {
        "user_id": user_id,
        "role": user_role
    }
    
    access_token = create_access_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=Config.JWT_ACCESS_TOKEN_EXPIRES
    )
    
    refresh_token = create_refresh_token(
        identity=user_id,
        additional_claims=additional_claims,
        expires_delta=Config.JWT_REFRESH_TOKEN_EXPIRES
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
    }

def decode_token(token: str) -> dict:
    """Token'ı decode et"""
    try:
        payload = jwt.decode(
            token, 
            Config.JWT_SECRET_KEY, 
            algorithms=["HS256"]
        )
        return {
            "success": True,
            "payload": payload
        }
    except jwt.ExpiredSignatureError:
        return {
            "success": False,
            "message": "Token süresi dolmuş"
        }
    except jwt.InvalidTokenError:
        return {
            "success": False,
            "message": "Geçersiz token"
        }

def is_admin(user_role: str) -> bool:
    """Admin kontrolü"""
    return user_role == "admin"

def is_user_or_admin(user_role: str) -> bool:
    """User veya admin kontrolü"""
    return user_role in ["user", "admin"]

def generate_reset_token(user_id: str) -> str:
    """Şifre sıfırlama token'ı oluştur"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1),  # 1 saat geçerli
        "type": "password_reset"
    }
    
    return jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm="HS256"
    )

def verify_reset_token(token: str) -> dict:
    """Şifre sıfırlama token'ını doğrula"""
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        
        if payload.get("type") != "password_reset":
            return {
                "success": False,
                "message": "Geçersiz token tipi"
            }
        
        return {
            "success": True,
            "user_id": payload["user_id"]
        }
        
    except jwt.ExpiredSignatureError:
        return {
            "success": False,
            "message": "Token süresi dolmuş"
        }
    except jwt.InvalidTokenError:
        return {
            "success": False,
            "message": "Geçersiz token"
        }