from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from utils.database import db

class FileAnalysisModel(BaseModel):
    user_id: str = Field(..., description="Kullanıcı ID'si")
    filename: str = Field(..., min_length=1, max_length=255, description="Dosya adı")
    original_filename: str = Field(..., min_length=1, max_length=255, description="Orijinal dosya adı")
    file_type: str = Field(..., description="Dosya türü (pdf, doc, docx, step, stp)")
    file_size: Optional[int] = Field(None, description="Dosya boyutu (bytes)")
    file_path: Optional[str] = Field(None, description="Dosya yolu")
    
    # Analiz sonuçları
    analysis_status: str = Field(default="pending", description="Analiz durumu")
    material_matches: Optional[List[str]] = Field(default=[], description="Bulunan malzeme eşleşmeleri")
    best_material_block: Optional[str] = Field(None, description="En iyi malzeme bloğu")
    rotation_count: Optional[int] = Field(default=0, description="PDF döndürme sayısı")
    
    # STEP analiz sonuçları
    step_analysis: Optional[Dict[str, Any]] = Field(default={}, description="STEP dosya analizi")
    isometric_view_path: Optional[str] = Field(None, description="İzometrik görünüm yolu")
    
    # Maliyet hesaplamaları
    material_costs: Optional[List[Dict[str, Any]]] = Field(default=[], description="Malzeme maliyetleri")
    total_cost_estimate: Optional[float] = Field(None, description="Toplam maliyet tahmini")
    
    # Meta veriler
    processing_time: Optional[float] = Field(None, description="İşlem süresi (saniye)")
    error_message: Optional[str] = Field(None, description="Hata mesajı")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class FileAnalysisResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    original_filename: str
    file_type: str
    analysis_status: str
    material_matches: List[str]
    step_analysis: Dict[str, Any]
    material_costs: List[Dict[str, Any]]
    total_cost_estimate: Optional[float]
    processing_time: Optional[float]
    created_at: datetime

class FileAnalysisCreate(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: Optional[int] = None
    file_path: Optional[str] = None

class FileAnalysisUpdate(BaseModel):
    analysis_status: Optional[str] = None
    material_matches: Optional[List[str]] = None
    best_material_block: Optional[str] = None
    rotation_count: Optional[int] = None
    step_analysis: Optional[Dict[str, Any]] = None
    isometric_view_path: Optional[str] = None
    material_costs: Optional[List[Dict[str, Any]]] = None
    total_cost_estimate: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None

class FileAnalysis:
    collection = None
    
    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = db.get_db().file_analyses
            # Index'leri oluştur
            cls.collection.create_index("user_id")
            cls.collection.create_index("filename")
            cls.collection.create_index("file_type")
            cls.collection.create_index("analysis_status")
            cls.collection.create_index("created_at")
            cls.collection.create_index([("user_id", 1), ("created_at", -1)])
        return cls.collection
    
    @classmethod
    def create_analysis(cls, analysis_data: dict) -> Dict[str, Any]:
        """Yeni dosya analizi oluştur"""
        collection = cls.get_collection()
        
        analysis_data['created_at'] = datetime.utcnow()
        analysis_data['updated_at'] = datetime.utcnow()
        
        # Analizi kaydet
        result = collection.insert_one(analysis_data)
        
        # Analizi geri döndür
        analysis = collection.find_one({"_id": result.inserted_id})
        if analysis:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analysis
    
    @classmethod
    def find_by_id(cls, analysis_id: str) -> Optional[Dict[str, Any]]:
        """ID ile analiz bul"""
        collection = cls.get_collection()
        analysis = collection.find_one({"_id": ObjectId(analysis_id)})
        if analysis:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analysis
    
    @classmethod
    def get_user_analyses(cls, user_id: str, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Kullanıcının analizlerini getir"""
        collection = cls.get_collection()
        analyses = list(collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit).skip(skip))
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def get_all_analyses(cls, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """Tüm analizleri getir (admin için)"""
        collection = cls.get_collection()
        analyses = list(collection.find({}).sort("created_at", -1).limit(limit).skip(skip))
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def update_analysis(cls, analysis_id: str, update_data: dict) -> bool:
        """Analiz güncelle"""
        collection = cls.get_collection()
        update_data['updated_at'] = datetime.utcnow()
        
        result = collection.update_one(
            {"_id": ObjectId(analysis_id)}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete_analysis(cls, analysis_id: str) -> bool:
        """Analiz sil"""
        collection = cls.get_collection()
        result = collection.delete_one({"_id": ObjectId(analysis_id)})
        return result.deleted_count > 0
    
    @classmethod
    def get_user_analysis_count(cls, user_id: str) -> int:
        """Kullanıcının analiz sayısı"""
        collection = cls.get_collection()
        return collection.count_documents({"user_id": user_id})
    
    @classmethod
    def get_total_analysis_count(cls) -> int:
        """Toplam analiz sayısı"""
        collection = cls.get_collection()
        return collection.count_documents({})
    
    @classmethod
    def search_analyses(cls, user_id: str, search_term: str) -> List[Dict[str, Any]]:
        """Analizlerde arama yap"""
        collection = cls.get_collection()
        
        query = {
            "user_id": user_id,
            "$or": [
                {"filename": {"$regex": search_term, "$options": "i"}},
                {"original_filename": {"$regex": search_term, "$options": "i"}},
                {"material_matches": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        analyses = list(collection.find(query).sort("created_at", -1))
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def get_analyses_by_status(cls, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Duruma göre analizleri getir"""
        collection = cls.get_collection()
        analyses = list(collection.find({"user_id": user_id, "analysis_status": status}).sort("created_at", -1))
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def get_analyses_by_file_type(cls, user_id: str, file_type: str) -> List[Dict[str, Any]]:
        """Dosya türüne göre analizleri getir"""
        collection = cls.get_collection()
        analyses = list(collection.find({"user_id": user_id, "file_type": file_type}).sort("created_at", -1))
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def get_recent_analyses(cls, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Son X günün analizleri"""
        from datetime import timedelta
        collection = cls.get_collection()
        
        since_date = datetime.utcnow() - timedelta(days=days)
        analyses = list(collection.find({
            "user_id": user_id, 
            "created_at": {"$gte": since_date}
        }).sort("created_at", -1))
        
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses