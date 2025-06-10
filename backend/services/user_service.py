from typing import List, Dict, Any, Optional
from models.user import User, UserRole
from bson import ObjectId

class UserService:
    
    @staticmethod
    def get_all_users() -> Dict[str, Any]:
        try:
            users = User.get_all_users()
            return {
                "success": True,
                "users": users,
                "count": len(users)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Kullanıcılar getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Dict[str, Any]:
        try:
            if not ObjectId.is_valid(user_id):
                return {
                    "success": False,
                    "message": "Geçersiz kullanıcı ID'si"
                }
            
            user = User.find_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "message": "Kullanıcı bulunamadı"
                }
            
            return {
                "success": True,
                "user": user
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Kullanıcı getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def update_user(user_id: str, update_data: dict, current_user: dict) -> Dict[str, Any]:
        try:
            if not ObjectId.is_valid(user_id):
                return {
                    "success": False,
                    "message": "Geçersiz kullanıcı ID'si"
                }
            
            if current_user['role'] != UserRole.ADMIN and current_user['id'] != user_id:
                return {
                    "success": False,
                    "message": "Bu işlem için yetkiniz yok"
                }
            
            existing_user = User.find_by_id(user_id)
            if not existing_user:
                return {
                    "success": False,
                    "message": "Kullanıcı bulunamadı"
                }
            
            allowed_fields = ['name', 'surname', 'email']
            if current_user['role'] == UserRole.ADMIN:
                allowed_fields.extend(['is_active', 'role'])
            
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not filtered_data:
                return {
                    "success": False,
                    "message": "Güncellenecek veri bulunamadı"
                }
            
            if 'email' in filtered_data and filtered_data['email'] != existing_user['email']:
                if User.email_exists(filtered_data['email']):
                    return {
                        "success": False,
                        "message": "Bu email adresi zaten kullanılıyor"
                    }
            
            success = User.update_user(user_id, filtered_data)
            if success:
                updated_user = User.find_by_id(user_id)
                return {
                    "success": True,
                    "message": "Kullanıcı başarıyla güncellendi",
                    "user": updated_user
                }
            else:
                return {
                    "success": False,
                    "message": "Güncelleme başarısız"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Güncelleme sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def delete_user(user_id: str, current_user: dict) -> Dict[str, Any]:
        try:
            if not ObjectId.is_valid(user_id):
                return {
                    "success": False,
                    "message": "Geçersiz kullanıcı ID'si"
                }
            
            if current_user['role'] != UserRole.ADMIN:
                return {
                    "success": False,
                    "message": "Bu işlem için admin yetkisi gerekli"
                }
            
            if current_user['id'] == user_id:
                return {
                    "success": False,
                    "message": "Kendi hesabınızı silemezsiniz"
                }
            
            user = User.find_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "message": "Kullanıcı bulunamadı"
                }
            
            # Sil
            success = User.delete_user(user_id)
            if success:
                return {
                    "success": True,
                    "message": "Kullanıcı başarıyla silindi"
                }
            else:
                return {
                    "success": False,
                    "message": "Silme işlemi başarısız"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Silme sırasında hata: {str(e)}"
            }