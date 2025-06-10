import os
from datetime import timedelta

class Config:
    MONGO_URL = os.getenv('MONGO_URL', 'mongodb://mongodb:27017/engteklif')
    DATABASE_NAME = 'engteklif'
    
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-super-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    BCRYPT_LOG_ROUNDS = 12
    
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'engteklif')