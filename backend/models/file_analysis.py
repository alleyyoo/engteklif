# models/file_analysis.py - UPDATED WITH PDF STEP RENDERING SUPPORT

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
    
    # ✅ ENHANCED RENDERING FIELDS - PDF STEP SUPPORT
    isometric_view: Optional[str] = Field(None, description="Ana izometrik render dosyası")
    isometric_view_clean: Optional[str] = Field(None, description="Excel uyumlu izometrik render")
    enhanced_renders: Optional[Dict[str, Any]] = Field(default={}, description="Tüm render görünümleri")
    render_quality: Optional[str] = Field(default="none", description="Render kalitesi")
    
    # ✅ PDF STEP EXTRACTION FIELDS
    pdf_step_extracted: Optional[bool] = Field(default=False, description="PDF'den STEP çıkarıldı mı")
    step_file_hash: Optional[str] = Field(None, description="STEP dosya hash'i")
    pdf_rotation_count: Optional[int] = Field(default=0, description="PDF döndürme sayısı")
    
    # ✅ ENHANCED MATERIAL CALCULATIONS
    all_material_calculations: Optional[List[Dict[str, Any]]] = Field(default=[], description="Bulunan malzemeler için hesaplamalar")
    material_options: Optional[List[Dict[str, Any]]] = Field(default=[], description="Tüm malzeme seçenekleri")
    
    # Maliyet hesaplamaları
    material_costs: Optional[List[Dict[str, Any]]] = Field(default=[], description="Malzeme maliyetleri")
    total_cost_estimate: Optional[float] = Field(None, description="Toplam maliyet tahmini")
    cost_estimation: Optional[Dict[str, Any]] = Field(default={}, description="Detaylı maliyet analizi")
    ai_price_prediction: Optional[Dict[str, Any]] = Field(default={}, description="AI fiyat tahmini")
    
    # Meta veriler
    processing_time: Optional[float] = Field(None, description="İşlem süresi (saniye)")
    processing_log: Optional[List[str]] = Field(default=[], description="İşlem log'ları")
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
    
    # ✅ ENHANCED RESPONSE FIELDS
    enhanced_renders: Dict[str, Any]
    pdf_step_extracted: bool
    step_file_hash: Optional[str]
    render_quality: str

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
    
    # ✅ ENHANCED UPDATE FIELDS
    isometric_view: Optional[str] = None
    isometric_view_clean: Optional[str] = None
    enhanced_renders: Optional[Dict[str, Any]] = None
    render_quality: Optional[str] = None
    pdf_step_extracted: Optional[bool] = None
    step_file_hash: Optional[str] = None
    pdf_rotation_count: Optional[int] = None
    all_material_calculations: Optional[List[Dict[str, Any]]] = None
    material_options: Optional[List[Dict[str, Any]]] = None
    cost_estimation: Optional[Dict[str, Any]] = None
    ai_price_prediction: Optional[Dict[str, Any]] = None
    processing_log: Optional[List[str]] = None

class FileAnalysis:
    collection = None
    
    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = db.get_db().file_analyses
            # Enhanced index'ler oluştur
            cls.collection.create_index("user_id")
            cls.collection.create_index("filename")
            cls.collection.create_index("file_type")
            cls.collection.create_index("analysis_status")
            cls.collection.create_index("created_at")
            cls.collection.create_index([("user_id", 1), ("created_at", -1)])
            # ✅ PDF STEP için yeni index'ler
            cls.collection.create_index("pdf_step_extracted")
            cls.collection.create_index("step_file_hash")
            cls.collection.create_index([("file_type", 1), ("pdf_step_extracted", 1)])
        return cls.collection
    
    @classmethod
    def create_analysis(cls, analysis_data: dict) -> Dict[str, Any]:
        """Yeni dosya analizi oluştur - Enhanced"""
        collection = cls.get_collection()
        
        analysis_data['created_at'] = datetime.utcnow()
        analysis_data['updated_at'] = datetime.utcnow()
        
        # ✅ Default values for new fields
        analysis_data.setdefault('pdf_step_extracted', False)
        analysis_data.setdefault('enhanced_renders', {})
        analysis_data.setdefault('render_quality', 'none')
        analysis_data.setdefault('all_material_calculations', [])
        analysis_data.setdefault('material_options', [])
        analysis_data.setdefault('processing_log', [])
        
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
        """Analiz güncelle - Enhanced"""
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
        """Analizlerde arama yap - Enhanced"""
        collection = cls.get_collection()
        
        query = {
            "user_id": user_id,
            "$or": [
                {"filename": {"$regex": search_term, "$options": "i"}},
                {"original_filename": {"$regex": search_term, "$options": "i"}},
                {"material_matches": {"$regex": search_term, "$options": "i"}},
                {"step_file_hash": {"$regex": search_term, "$options": "i"}}  # ✅ NEW
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
    
    # ✅ NEW METHODS FOR PDF STEP SUPPORT
    
    @classmethod
    def get_pdf_step_analyses(cls, user_id: str) -> List[Dict[str, Any]]:
        """PDF'den STEP çıkarılan analizleri getir"""
        collection = cls.get_collection()
        analyses = list(collection.find({
            "user_id": user_id,
            "file_type": "pdf",
            "pdf_step_extracted": True
        }).sort("created_at", -1))
        
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def get_analyses_with_renders(cls, user_id: str) -> List[Dict[str, Any]]:
        """Render'ı olan analizleri getir"""
        collection = cls.get_collection()
        analyses = list(collection.find({
            "user_id": user_id,
            "enhanced_renders": {"$ne": {}, "$exists": True}
        }).sort("created_at", -1))
        
        for analysis in analyses:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analyses
    
    @classmethod
    def find_by_step_hash(cls, step_hash: str) -> Optional[Dict[str, Any]]:
        """STEP hash'i ile analiz bul"""
        collection = cls.get_collection()
        analysis = collection.find_one({"step_file_hash": step_hash})
        if analysis:
            analysis['id'] = str(analysis['_id'])
            del analysis['_id']
        return analysis
    
    @classmethod
    def get_user_statistics_enhanced(cls, user_id: str) -> Dict[str, Any]:
        """Kullanıcı için gelişmiş istatistikler"""
        collection = cls.get_collection()
        
        # Temel sayılar
        total_files = collection.count_documents({"user_id": user_id})
        completed_analyses = collection.count_documents({"user_id": user_id, "analysis_status": "completed"})
        failed_analyses = collection.count_documents({"user_id": user_id, "analysis_status": "failed"})
        
        # PDF STEP istatistikleri
        pdf_files = collection.count_documents({"user_id": user_id, "file_type": "pdf"})
        pdf_step_extracted = collection.count_documents({"user_id": user_id, "pdf_step_extracted": True})
        
        # Render istatistikleri
        files_with_renders = collection.count_documents({
            "user_id": user_id, 
            "enhanced_renders": {"$ne": {}, "$exists": True}
        })
        
        # Dosya türü dağılımı
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$file_type", "count": {"$sum": 1}}}
        ]
        file_type_distribution = {item["_id"]: item["count"] for item in collection.aggregate(pipeline)}
        
        return {
            "total_files": total_files,
            "completed_analyses": completed_analyses,
            "failed_analyses": failed_analyses,
            "success_rate": (completed_analyses / max(total_files, 1)) * 100,
            "pdf_files": pdf_files,
            "pdf_step_extracted": pdf_step_extracted,
            "pdf_step_extraction_rate": (pdf_step_extracted / max(pdf_files, 1)) * 100,
            "files_with_renders": files_with_renders,
            "render_generation_rate": (files_with_renders / max(completed_analyses, 1)) * 100,
            "file_type_distribution": file_type_distribution
        }
    
    @classmethod
    def get_render_statistics(cls, user_id: str) -> Dict[str, Any]:
        """Render istatistikleri"""
        collection = cls.get_collection()
        
        # Render'ı olan dosyalar
        analyses_with_renders = list(collection.find({
            "user_id": user_id,
            "enhanced_renders": {"$ne": {}, "$exists": True}
        }))
        
        if not analyses_with_renders:
            return {"total_rendered_files": 0, "render_types": {}, "average_renders_per_file": 0}
        
        # Render türü sayıları
        render_type_counts = {}
        total_renders = 0
        
        for analysis in analyses_with_renders:
            enhanced_renders = analysis.get('enhanced_renders', {})
            for render_type, render_data in enhanced_renders.items():
                if render_data.get('success'):
                    render_type_counts[render_type] = render_type_counts.get(render_type, 0) + 1
                    total_renders += 1
        
        return {
            "total_rendered_files": len(analyses_with_renders),
            "total_renders": total_renders,
            "average_renders_per_file": total_renders / len(analyses_with_renders),
            "render_types": render_type_counts,
            "most_common_render": max(render_type_counts.items(), key=lambda x: x[1])[0] if render_type_counts else None
        }