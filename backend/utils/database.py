from pymongo import MongoClient
from config import Config

class Database:
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        if self._client is None:
            self._client = MongoClient(Config.MONGO_URL)
            self._db = self._client[Config.DATABASE_NAME]
            print(f"MongoDB'ye bağlanıldı: {Config.DATABASE_NAME}")
        return self._db
    
    def get_db(self):
        if self._db is None:
            return self.connect()
        return self._db
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            print("MongoDB bağlantısı kapatıldı")

db = Database()            