from typing import Optional, Dict, Any
from models.user import User, UserRole, RegisterRequest, LoginRequest
from utils.auth_utils import create_tokens, hash_password
from config import Config

class AuthService:
    
    @staticmethod
    def register_user(register_data: RegisterRequest) -> Dict[str, Any]:
        """Kullanıcı kaydı"""
        try:
            # Username kontrolü
            if User.username_exists(register_data.username):
                return {
                    "success": False,
                    "message": "Bu kullanıcı adı zaten kullanılıyor"
                }
            
            # Email kontrolü
            if User.email_exists(register_data.email):
                return {
                    "success": False,
                    "message": "Bu email adresi zaten kullanılıyor"
                }
            
            # Kullanıcı oluştur
            user_data = register_data.dict()
            user = User.create_user(user_data)
            
            # Token oluştur
            tokens = create_tokens(user['id'], user['role'])
            
            return {
                "success": True,
                "message": "Kullanıcı başarıyla kaydedildi",
                "user": user,
                "tokens": tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Kayıt sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def login_user(login_data: LoginRequest) -> Dict[str, Any]:
        """Kullanıcı girişi"""
        try:
            # Kullanıcıyı doğrula
            user = User.verify_password(login_data.username, login_data.password)
            
            if not user:
                return {
                    "success": False,
                    "message": "Kullanıcı adı veya şifre hatalı"
                }
            
            # Aktif kullanıcı kontrolü
            if not user.get('is_active', True):
                return {
                    "success": False,
                    "message": "Hesabınız deaktif durumda"
                }
            
            # Token oluştur
            tokens = create_tokens(user['id'], user['role'])
            
            return {
                "success": True,
                "message": "Giriş başarılı",
                "user": user,
                "tokens": tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Giriş sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def refresh_token(user_id: str) -> Dict[str, Any]:
        """Token yenile"""
        try:
            user = User.find_by_id(user_id)
            
            if not user:
                return {
                    "success": False,
                    "message": "Kullanıcı bulunamadı"
                }
            
            if not user.get('is_active', True):
                return {
                    "success": False,
                    "message": "Hesabınız deaktif durumda"
                }
            
            # Yeni token oluştur
            tokens = create_tokens(user['id'], user['role'])
            
            return {
                "success": True,
                "message": "Token yenilendi",
                "tokens": tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Token yenileme hatası: {str(e)}"
            }
    
    @staticmethod
    def logout_user(user_id: str) -> Dict[str, Any]:
        """Kullanıcı çıkışı"""
        try:
            # Şu an için basit logout
            # İleride token blacklisting eklenebilir
            return {
                "success": True,
                "message": "Başarıyla çıkış yapıldı"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Çıkış sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def create_admin_if_not_exists():
        """İlk admin kullanıcısını oluştur"""
        try:
            if not User.username_exists(Config.ADMIN_USERNAME):
                admin_data = {
                    "username": Config.ADMIN_USERNAME,
                    "name": "Admin",
                    "surname": "User",
                    "email": "admin@example.com",
                    "password": Config.ADMIN_PASSWORD,
                    "role": UserRole.ADMIN,
                    "is_active": True
                }
                User.create_user(admin_data)
                print(f"✅ Admin kullanıcısı oluşturuldu: {Config.ADMIN_USERNAME}")
            else:
                print(f"ℹ️  Admin kullanıcısı zaten mevcut: {Config.ADMIN_USERNAME}")
        except Exception as e:
            print(f"❌ Admin oluşturma hatası: {e}")
    
    @staticmethod
    def change_password(user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """Şifre değiştir"""
        try:
            user = User.find_by_id(user_id)
            
            if not user:
                return {
                    "success": False,
                    "message": "Kullanıcı bulunamadı"
                }
            
            # Eski şifreyi doğrula
            user_with_password = User.get_collection().find_one({"_id": user_id})
            from utils.auth_utils import verify_password
            
            if not verify_password(old_password, user_with_password['password']):
                return {
                    "success": False,
                    "message": "Mevcut şifre yanlış"
                }
            
            # Yeni şifreyi hash'le ve güncelle
            new_hashed_password = hash_password(new_password)
            success = User.update_user(user_id, {"password": new_hashed_password})
            
            if success:
                return {
                    "success": True,
                    "message": "Şifre başarıyla değiştirildi"
                }
            else:
                return {
                    "success": False,
                    "message": "Şifre değiştirme başarısız"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Şifre değiştirme hatası: {str(e)}"
            }
    
    @staticmethod
    def validate_user_permissions(user_role: str, required_role: str) -> bool:
        """Kullanıcı yetkilerini doğrula"""
        role_hierarchy = {
            UserRole.USER: 1,
            UserRole.ADMIN: 2
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level