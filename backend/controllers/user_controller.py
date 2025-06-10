from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.user_service import UserService
from models.user import User, UserRole

user_bp = Blueprint('users', __name__, url_prefix='/api/users')

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

@user_bp.route('', methods=['GET'])
@jwt_required()
def get_users():
    """Tüm kullanıcıları getir (sadece admin)"""
    try:
        current_user = get_current_user()
        
        if not current_user or current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        # Query parametreleri
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '', type=str)
        role_filter = request.args.get('role', '', type=str)
        
        result = UserService.get_all_users()
        
        if result['success']:
            users = result['users']
            
            # Search filtresi
            if search:
                users = [user for user in users if 
                        search.lower() in user.get('username', '').lower() or
                        search.lower() in user.get('name', '').lower() or
                        search.lower() in user.get('surname', '').lower() or
                        search.lower() in user.get('email', '').lower()]
            
            # Role filtresi
            if role_filter and role_filter in [UserRole.ADMIN, UserRole.USER]:
                users = [user for user in users if user.get('role') == role_filter]
            
            # Pagination
            total = len(users)
            start = (page - 1) * limit
            end = start + limit
            paginated_users = users[start:end]
            
            return jsonify({
                "success": True,
                "users": paginated_users,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total + limit - 1) // limit,
                    "total_users": total,
                    "users_per_page": limit
                }
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Belirli bir kullanıcıyı getir"""
    try:
        current_user = get_current_user()
        
        # Sadece admin veya kendi bilgilerini görebilir
        if current_user['role'] != UserRole.ADMIN and current_user['id'] != user_id:
            return jsonify({
                "success": False,
                "message": "Bu işlem için yetkiniz yok"
            }), 403
        
        result = UserService.get_user_by_id(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Kullanıcıyı güncelle"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "Güncellenecek veri gönderilmedi"
            }), 400
        
        result = UserService.update_user(user_id, data, current_user)
        
        if result['success']:
            return jsonify(result), 200
        else:
            status_code = 403 if "yetki" in result['message'] else 400
            return jsonify(result), status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Kullanıcıyı sil (sadece admin)"""
    try:
        current_user = get_current_user()
        
        result = UserService.delete_user(user_id, current_user)
        
        if result['success']:
            return jsonify(result), 200
        else:
            status_code = 403 if "yetki" in result['message'] else 400
            return jsonify(result), status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>/activate', methods=['PUT'])
@jwt_required()
def activate_user(user_id):
    """Kullanıcıyı aktifleştir (sadece admin)"""
    try:
        current_user = get_current_user()
        
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        result = UserService.update_user(user_id, {"is_active": True}, current_user)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "Kullanıcı aktifleştirildi",
                "user": result['user']
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>/deactivate', methods=['PUT'])
@jwt_required()
def deactivate_user(user_id):
    """Kullanıcıyı deaktifleştir (sadece admin)"""
    try:
        current_user = get_current_user()
        
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        # Kendini deaktifleştirmeye çalışıyor mu?
        if current_user['id'] == user_id:
            return jsonify({
                "success": False,
                "message": "Kendi hesabınızı deaktifleştiremezsiniz"
            }), 400
        
        result = UserService.update_user(user_id, {"is_active": False}, current_user)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "Kullanıcı deaktifleştirildi",
                "user": result['user']
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/<user_id>/role', methods=['PUT'])
@jwt_required()
def change_user_role(user_id):
    """Kullanıcı rolünü değiştir (sadece admin)"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        if not data or 'role' not in data:
            return jsonify({
                "success": False,
                "message": "Yeni rol belirtilmedi"
            }), 400
        
        new_role = data['role']
        if new_role not in [UserRole.ADMIN, UserRole.USER]:
            return jsonify({
                "success": False,
                "message": "Geçersiz rol. Sadece 'admin' veya 'user' olabilir"
            }), 400
        
        # Kendine admin rolü vermeye çalışıyor mu?
        if current_user['id'] == user_id and new_role != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Kendi admin rolünüzü değiştiremezsiniz"
            }), 400
        
        result = UserService.update_user(user_id, {"role": new_role}, current_user)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": f"Kullanıcı rolü {new_role} olarak değiştirildi",
                "user": result['user']
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@user_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Kullanıcı istatistikleri (sadece admin)"""
    try:
        current_user = get_current_user()
        
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        result = UserService.get_all_users()
        
        if result['success']:
            users = result['users']
            
            stats = {
                "total_users": len(users),
                "active_users": len([u for u in users if u.get('is_active', True)]),
                "inactive_users": len([u for u in users if not u.get('is_active', True)]),
                "admin_users": len([u for u in users if u.get('role') == UserRole.ADMIN]),
                "regular_users": len([u for u in users if u.get('role') == UserRole.USER]),
                "recent_registrations": len([u for u in users if 
                    (u.get('created_at') and 
                     (u['created_at'] - users[0].get('created_at', u['created_at'])).days <= 7)
                ])
            }
            
            return jsonify({
                "success": True,
                "stats": stats
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500