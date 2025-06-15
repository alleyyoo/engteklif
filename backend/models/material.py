# models/material.py (FIXED)
import re
import unicodedata
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.database import db

class MaterialModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Malzeme adı")
    aliases: Optional[List[str]] = Field(default=[], description="Alternatif isimler")
    density: Optional[float] = Field(None, gt=0, description="Yoğunluk (g/cm³)")
    price_per_kg: Optional[float] = Field(None, ge=0, description="Kg başına fiyat (USD)")
    description: Optional[str] = Field(None, max_length=500, description="Açıklama")
    category: Optional[str] = Field(None, max_length=50, description="Kategori")
    is_active: bool = Field(default=True, description="Aktif durumu")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @validator('aliases')
    def validate_aliases(cls, v):
        if v is None:
            return []
        return [alias.strip() for alias in v if alias.strip()]

class MaterialResponse(BaseModel):
    id: str
    name: str
    aliases: List[str]
    density: Optional[float]
    price_per_kg: Optional[float]
    description: Optional[str]
    category: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    aliases: Optional[List[str]] = Field(default=[])
    density: Optional[float] = Field(None, gt=0)
    price_per_kg: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)

class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    aliases: Optional[List[str]] = None
    density: Optional[float] = Field(None, gt=0)
    price_per_kg: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

class Material:
    collection = None
    
    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = db.get_db().materials
            # Index'leri oluştur
            cls.collection.create_index("name", unique=True)
            cls.collection.create_index("aliases")
            cls.collection.create_index("category")
            cls.collection.create_index("is_active")
            cls.collection.create_index("created_at")
        return cls.collection
    
    @classmethod
    def create_material(cls, material_data: dict) -> Dict[str, Any]:
        """Yeni malzeme oluştur"""
        collection = cls.get_collection()
        
        material_data['created_at'] = datetime.utcnow()
        material_data['updated_at'] = datetime.utcnow()
        
        # Malzemeyi kaydet
        result = collection.insert_one(material_data)
        
        # Malzemeyi geri döndür
        material = collection.find_one({"_id": result.inserted_id})
        if material:
            material['id'] = str(material['_id'])
            del material['_id']
        return material
    
    @classmethod
    def find_by_id(cls, material_id: str) -> Optional[Dict[str, Any]]:
        """ID ile malzeme bul"""
        collection = cls.get_collection()
        material = collection.find_one({"_id": ObjectId(material_id)})
        if material:
            material['id'] = str(material['_id'])
            del material['_id']
        return material
    
    @classmethod
    def find_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """İsim ile malzeme bul"""
        collection = cls.get_collection()
        material = collection.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
        if material:
            material['id'] = str(material['_id'])
            del material['_id']
        return material
    
    @classmethod
    def get_all_materials(cls, limit: int = 100, skip: int = 0, active_only: bool = True) -> List[Dict[str, Any]]:
        """Tüm malzemeleri getir"""
        collection = cls.get_collection()
        query = {"is_active": True} if active_only else {}
        materials = list(collection.find(query).sort("name", 1).limit(limit).skip(skip))
        for material in materials:
            material['id'] = str(material['_id'])
            del material['_id']
        return materials
    
    @classmethod
    def get_materials_for_matching(cls) -> tuple:
        """Malzeme eşleştirme için veri hazırla"""
        def normalize_for_match(s):
            s = s.lower().replace("i̇", "i").replace("ı", "i")
            s = unicodedata.normalize("NFKD", s)
            s = "".join(c for c in s if not unicodedata.combining(c))
            return re.sub(r'\W+|\s+', '', s)
        
        collection = cls.get_collection()
        materials = list(collection.find({"is_active": True, "density": {"$ne": None}}))
        
        keyword_list = []
        alias_map = {}
        
        for material in materials:
            name = material['name']
            keyword_list.append(normalize_for_match(name))
            
            aliases = material.get('aliases', [])
            if aliases:
                for alias in aliases:
                    if alias.strip():
                        alias_map[normalize_for_match(alias)] = name
        
        return keyword_list, alias_map
    
    @classmethod
    def get_material_prices(cls) -> Dict[str, float]:
        """Malzeme fiyatlarını getir"""
        collection = cls.get_collection()
        materials = list(collection.find(
            {"is_active": True, "price_per_kg": {"$ne": None}},
            {"name": 1, "price_per_kg": 1}
        ))
        return {material['name']: material['price_per_kg'] for material in materials}
    
    @classmethod
    def search_materials(cls, search_term: str, category: str = None) -> List[Dict[str, Any]]:
        """Malzemelerde arama yap"""
        collection = cls.get_collection()
        
        query = {
            "is_active": True,
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"aliases": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        if category:
            query["category"] = category
        
        materials = list(collection.find(query).sort("name", 1))
        for material in materials:
            material['id'] = str(material['_id'])
            del material['_id']
        return materials
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Tüm kategorileri getir"""
        collection = cls.get_collection()
        return collection.distinct("category", {"category": {"$ne": None}})
    
    @classmethod
    def name_exists(cls, name: str, exclude_id: str = None) -> bool:
        """İsim var mı kontrol et"""
        collection = cls.get_collection()
        query = {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}
        return collection.find_one(query) is not None
    
    @classmethod
    def update_material(cls, material_id: str, update_data: dict) -> bool:
        """Malzeme güncelle"""
        collection = cls.get_collection()
        update_data['updated_at'] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(material_id)}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete_material(cls, material_id: str) -> bool:
        """Malzeme sil (soft delete)"""
        collection = cls.get_collection()
        result = collection.update_one(
            {"_id": ObjectId(material_id)}, 
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @classmethod
    def get_count(cls, active_only: bool = True) -> int:
        """Toplam malzeme sayısı"""
        collection = cls.get_collection()
        query = {"is_active": True} if active_only else {}
        return collection.count_documents(query)
    
    @classmethod
    def bulk_update_prices(cls, price_updates: Dict[str, float]) -> int:
        """Toplu fiyat güncelleme"""
        collection = cls.get_collection()
        updated_count = 0
        
        for name, price in price_updates.items():
            result = collection.update_one(
                {"name": name},
                {"$set": {"price_per_kg": price, "updated_at": datetime.utcnow()}}
            )
            updated_count += result.modified_count
        
        return updated_count