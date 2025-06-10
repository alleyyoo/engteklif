from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from bson import ObjectId
from utils.database import db
from utils.auth_utils import hash_password, verify_password

class UserRole:
    ADMIN = "admin"
    USER = "user"

class UserModel(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    surname: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @validator('role')
    def validate_role(cls, v):
        if v not in [UserRole.ADMIN, UserRole.USER]:
            raise ValueError('Role must be admin or user')
        return v

class UserResponse(BaseModel):
    id: str
    username: str
    name: str
    surname: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    name: str
    surname: str
    email: EmailStr
    password: str
    role: Optional[str] = UserRole.USER

class User:
    collection = None
    
    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = db.get_db().users
            # Index'leri oluştur
            cls.collection.create_index("username", unique=True)
            cls.collection.create_index("email", unique=True)
        return cls.collection
    
    @classmethod
    def create_user(cls, user_data: dict) -> Dict[str, Any]:
        """Yeni kullanıcı oluştur"""
        collection = cls.get_collection()
        
        # Şifreyi hash'le
        user_data['password'] = hash_password(user_data['password'])
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = datetime.utcnow()
        
        # Kullanıcıyı kaydet
        result = collection.insert_one(user_data)
        
        # Kullanıcıyı geri döndür (şifre olmadan)
        user = collection.find_one({"_id": result.inserted_id})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
            del user['password']
        return user
    
    @classmethod
    def find_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        """Username ile kullanıcı bul"""
        collection = cls.get_collection()
        user = collection.find_one({"username": username})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
        return user
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional[Dict[str, Any]]:
        """Email ile kullanıcı bul"""
        collection = cls.get_collection()
        user = collection.find_one({"email": email})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
        return user
    
    @classmethod
    def find_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """ID ile kullanıcı bul"""
        collection = cls.get_collection()
        user = collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
        return user
    
    @classmethod
    def verify_password(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Kullanıcı adı ve şifre doğrula"""
        collection = cls.get_collection()
        user = collection.find_one({"username": username})
        
        if user and verify_password(password, user['password']):
            user['id'] = str(user['_id'])
            del user['_id']
            del user['password']  # Şifreyi response'dan çıkar
            return user
        return None
    
    @classmethod
    def username_exists(cls, username: str) -> bool:
        """Username var mı kontrol et"""
        collection = cls.get_collection()
        return collection.find_one({"username": username}) is not None
    
    @classmethod
    def email_exists(cls, email: str) -> bool:
        """Email var mı kontrol et"""
        collection = cls.get_collection()
        return collection.find_one({"email": email}) is not None
    
    @classmethod
    def get_all_users(cls) -> list:
        """Tüm kullanıcıları getir"""
        collection = cls.get_collection()
        users = list(collection.find({}, {"password": 0}))  # Şifreleri dahil etme
        for user in users:
            user['id'] = str(user['_id'])
            del user['_id']
        return users
    
    @classmethod
    def update_user(cls, user_id: str, update_data: dict) -> bool:
        """Kullanıcı güncelle"""
        collection = cls.get_collection()
        update_data['updated_at'] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(user_id)}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete_user(cls, user_id: str) -> bool:
        """Kullanıcı sil"""
        collection = cls.get_collection()
        result = collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0