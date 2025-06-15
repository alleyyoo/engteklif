from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from utils.database import db

class GeometricMeasurementModel(BaseModel):
    type: str = Field(..., min_length=1, max_length=100, description="Ölçüm türü")
    nominal_value: str = Field(..., min_length=1, max_length=50, description="Nominal değer")
    upper_deviation: Optional[float] = Field(None, description="Üst sapma")
    lower_deviation: Optional[float] = Field(None, description="Alt sapma")
    multiplier: float = Field(default=1.0, gt=0, description="Çarpan")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    @validator('multiplier')
    def validate_multiplier(cls, v):
        if v <= 0:
            raise ValueError('Çarpan sıfırdan büyük olmalı')
        return v

class GeometricMeasurementResponse(BaseModel):
    id: str
    type: str
    nominal_value: str
    upper_deviation: Optional[float]
    lower_deviation: Optional[float]
    multiplier: float
    created_at: datetime
    updated_at: datetime

class GeometricMeasurementCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=100)
    nominal_value: str = Field(..., min_length=1, max_length=50)
    upper_deviation: Optional[float] = None
    lower_deviation: Optional[float] = None
    multiplier: float = Field(default=1.0, gt=0)

class GeometricMeasurementUpdate(BaseModel):
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    nominal_value: Optional[str] = Field(None, min_length=1, max_length=50)
    upper_deviation: Optional[float] = None
    lower_deviation: Optional[float] = None
    multiplier: Optional[float] = Field(None, gt=0)

class GeometricMeasurement:
    collection = None
    
    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = db.get_db().geometric_measurements
            # Index'leri oluştur
            cls.collection.create_index([("type", 1), ("nominal_value", 1)])
            cls.collection.create_index("created_at")
        return cls.collection
    
    @classmethod
    def create_measurement(cls, measurement_data: dict) -> Dict[str, Any]:
        """Yeni ölçüm oluştur"""
        collection = cls.get_collection()
        
        measurement_data['created_at'] = datetime.utcnow()
        measurement_data['updated_at'] = datetime.utcnow()
        
        # Ölçümü kaydet
        result = collection.insert_one(measurement_data)
        
        # Ölçümü geri döndür
        measurement = collection.find_one({"_id": result.inserted_id})
        if measurement:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurement
    
    @classmethod
    def find_by_id(cls, measurement_id: str) -> Optional[Dict[str, Any]]:
        """ID ile ölçüm bul"""
        collection = cls.get_collection()
        measurement = collection.find_one({"_id": ObjectId(measurement_id)})
        if measurement:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurement
    
    @classmethod
    def get_all_measurements(cls, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """Tüm ölçümleri getir"""
        collection = cls.get_collection()
        measurements = list(collection.find({}).sort("created_at", -1).limit(limit).skip(skip))
        for measurement in measurements:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurements
    
    @classmethod
    def get_measurements_by_type(cls, measurement_type: str) -> List[Dict[str, Any]]:
        """Türe göre ölçümleri getir"""
        collection = cls.get_collection()
        measurements = list(collection.find({"type": measurement_type}).sort("created_at", -1))
        for measurement in measurements:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurements
    
    @classmethod
    def find_matching_measurement(cls, measurement_type: str, value: float) -> Optional[Dict[str, Any]]:
        """Değer aralığına uygun ölçüm bul"""
        collection = cls.get_collection()
        
        # Sayısal değer kontrolü
        try:
            query = {
                "type": measurement_type,
                "$and": [
                    {"$or": [{"lower_deviation": None}, {"lower_deviation": {"$lte": value}}]},
                    {"$or": [{"upper_deviation": None}, {"upper_deviation": {"$gte": value}}]}
                ]
            }
            measurement = collection.find_one(query)
        except:
            # String eşleşmesi
            measurement = collection.find_one({
                "type": measurement_type,
                "nominal_value": str(value)
            })
        
        if measurement:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurement
    
    @classmethod
    def update_measurement(cls, measurement_id: str, update_data: dict) -> bool:
        """Ölçüm güncelle"""
        collection = cls.get_collection()
        update_data['updated_at'] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(measurement_id)}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete_measurement(cls, measurement_id: str) -> bool:
        """Ölçüm sil"""
        collection = cls.get_collection()
        result = collection.delete_one({"_id": ObjectId(measurement_id)})
        return result.deleted_count > 0
    
    @classmethod
    def get_measurement_types(cls) -> List[str]:
        """Tüm ölçüm türlerini getir"""
        collection = cls.get_collection()
        return collection.distinct("type")
    
    @classmethod
    def get_count(cls) -> int:
        """Toplam ölçüm sayısı"""
        collection = cls.get_collection()
        return collection.count_documents({})
    
    @classmethod
    def search_measurements(cls, search_term: str) -> List[Dict[str, Any]]:
        """Ölçümlerde arama yap"""
        collection = cls.get_collection()
        
        # Text search
        query = {
            "$or": [
                {"type": {"$regex": search_term, "$options": "i"}},
                {"nominal_value": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        measurements = list(collection.find(query).sort("created_at", -1))
        for measurement in measurements:
            measurement['id'] = str(measurement['_id'])
            del measurement['_id']
        return measurements