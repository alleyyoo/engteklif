# services/file_grouping_service.py - Backend File Grouping and Analysis Merging

import os
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from models.file_analysis import FileAnalysis
from models.user import User
import logging

logger = logging.getLogger(__name__)

class FileGroupingService:
    """
    Aynı isimli farklı uzantılı dosyaları gruplayıp analizlerini birleştiren servis
    """
    
    def __init__(self):
        self.group_cache = {}
        self.merge_timeout_minutes = 30  # 30 dakika içinde gelen dosyalar gruplandırılır
    
    @staticmethod
    def extract_base_filename(filename: str) -> str:
        """Dosya adından uzantıyı çıkarıp base name'i döndür"""
        if '.' in filename:
            return filename.rsplit('.', 1)[0]
        return filename
    
    @staticmethod
    def get_file_type_category(file_type: str) -> str:
        """Dosya tipini kategorize et"""
        if file_type == 'pdf':
            return 'document'
        elif file_type in ['step', 'stp']:
            return 'cad'
        elif file_type in ['doc', 'docx']:
            return 'document'
        else:
            return 'unknown'
    
    def find_related_files(self, user_id: str, original_filename: str, analysis_id: str = None) -> List[Dict[str, Any]]:
        """
        Aynı base name'e sahip diğer dosyaları bul
        
        Args:
            user_id: Kullanıcı ID'si
            original_filename: Dosya adı
            analysis_id: Mevcut analiz ID'si (kendisini hariç tut)
            
        Returns:
            List: İlgili dosyalar listesi
        """
        try:
            base_filename = self.extract_base_filename(original_filename)
            
            # Son 30 dakikada yüklenmiş aynı base name'li dosyaları bul
            since_time = datetime.utcnow() - timedelta(minutes=self.merge_timeout_minutes)
            
            # MongoDB sorgusu
            query = {
                "user_id": user_id,
                "created_at": {"$gte": since_time}
            }
            
            # Analysis ID varsa kendisini hariç tut
            if analysis_id:
                query["_id"] = {"$ne": analysis_id}
            
            all_analyses = FileAnalysis.get_collection().find(query)
            related_files = []
            
            for analysis in all_analyses:
                analysis_base = self.extract_base_filename(analysis.get('original_filename', ''))
                
                # Base filename eşleşiyorsa ekle
                if analysis_base.lower() == base_filename.lower():
                    analysis['id'] = str(analysis['_id'])
                    del analysis['_id']
                    related_files.append(analysis)
            
            logger.info(f"[FILE-GROUP] Base: '{base_filename}' için {len(related_files)} ilgili dosya bulundu")
            return related_files
            
        except Exception as e:
            logger.error(f"[FILE-GROUP] İlgili dosya arama hatası: {str(e)}")
            return []
    
    def merge_analysis_results(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Birden fazla analizin sonuçlarını birleştir
        
        Strategy:
        - PDF'ten: material_matches, best_material_block
        - STEP'ten: step_analysis, enhanced_renders, geometrik veriler
        - DOC'tan: ek material bilgileri
        - En iyi veriler seçilir (quality score'a göre)
        
        Args:
            analyses: Analiz listesi
            
        Returns:
            Dict: Birleştirilmiş analiz sonucu
        """
        try:
            logger.info(f"[MERGE] {len(analyses)} analiz birleştiriliyor...")
            
            # Sonuç template'i
            merged_result = {
                "group_info": {
                    "total_files": len(analyses),
                    "file_types": [],
                    "merge_timestamp": datetime.utcnow().isoformat(),
                    "merge_strategy": "best_from_each_type"
                },
                "material_matches": [],
                "step_analysis": {},
                "enhanced_renders": {},
                "all_material_calculations": [],
                "material_options": [],
                "cost_estimation": {},
                "ai_price_prediction": {},
                "processing_log": [],
                "source_files": []
            }
            
            # Dosya türlerine göre grupla
            by_type = {
                'pdf': [],
                'step': [],
                'doc': []
            }
            
            for analysis in analyses:
                file_type = analysis.get('file_type', 'unknown')
                
                # Source file info ekle
                merged_result["source_files"].append({
                    "id": analysis.get('id'),
                    "filename": analysis.get('original_filename'),
                    "file_type": file_type,
                    "analysis_status": analysis.get('analysis_status'),
                    "created_at": analysis.get('created_at')
                })
                
                if file_type in by_type:
                    by_type[file_type].append(analysis)
                
                merged_result["group_info"]["file_types"].append(file_type)
            
            # Her tip için en iyi analizi seç ve birleştir
            merged_result.update(self._merge_by_strategy(by_type))
            
            # Quality score hesapla
            merged_result["quality_score"] = self._calculate_merge_quality(merged_result, by_type)
            
            logger.info(f"[MERGE] ✅ Birleştirme tamamlandı. Quality score: {merged_result['quality_score']}")
            return merged_result
            
        except Exception as e:
            logger.error(f"[MERGE] ❌ Birleştirme hatası: {str(e)}")
            return {"error": f"Merge failed: {str(e)}"}
    
    def _merge_by_strategy(self, by_type: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Tip bazlı birleştirme stratejisi"""
        result = {
            "material_matches": [],
            "step_analysis": {},
            "enhanced_renders": {},
            "all_material_calculations": [],
            "material_options": [],
            "cost_estimation": {},
            "ai_price_prediction": {},
            "processing_log": []
        }
        
        # 1. PDF'ten en iyi material bilgilerini al
        if by_type['pdf']:
            best_pdf = self._select_best_analysis(by_type['pdf'], 'material_quality')
            if best_pdf:
                result["material_matches"] = best_pdf.get("material_matches", [])
                result["processing_log"].append(f"📄 Malzeme bilgileri PDF'ten alındı: {best_pdf.get('original_filename')}")
                
                # PDF'ten gelen material calculations
                pdf_materials = best_pdf.get("all_material_calculations", [])
                if pdf_materials:
                    result["all_material_calculations"].extend(pdf_materials)
        
        # 2. STEP'ten en iyi geometrik bilgileri al
        if by_type['step']:
            best_step = self._select_best_analysis(by_type['step'], 'geometric_quality')
            if best_step:
                result["step_analysis"] = best_step.get("step_analysis", {})
                result["enhanced_renders"] = best_step.get("enhanced_renders", {})
                result["processing_log"].append(f"🔧 Geometrik bilgiler STEP'ten alındı: {best_step.get('original_filename')}")
                
                # STEP'ten gelen material options
                step_materials = best_step.get("material_options", [])
                if step_materials:
                    result["material_options"] = step_materials
                
                # STEP'ten cost estimation
                if best_step.get("cost_estimation"):
                    result["cost_estimation"] = best_step.get("cost_estimation")
                
                # STEP'ten AI prediction
                if best_step.get("ai_price_prediction"):
                    result["ai_price_prediction"] = best_step.get("ai_price_prediction")
        
        # 3. DOC'tan ek material bilgileri
        if by_type['doc']:
            best_doc = self._select_best_analysis(by_type['doc'], 'material_quality')
            if best_doc:
                doc_materials = best_doc.get("material_matches", [])
                # PDF'te bulunamayanları ekle
                existing = set(result["material_matches"])
                for mat in doc_materials:
                    if mat not in existing:
                        result["material_matches"].append(mat)
                
                result["processing_log"].append(f"📝 Ek malzeme bilgileri DOC'tan alındı: {best_doc.get('original_filename')}")
        
        # 4. Hybrid calculations - PDF materyalleri + STEP geometrisi
        if result["material_matches"] and result["step_analysis"]:
            hybrid_calculations = self._create_hybrid_calculations(
                result["material_matches"], 
                result["step_analysis"]
            )
            if hybrid_calculations:
                result["all_material_calculations"].extend(hybrid_calculations)
                result["processing_log"].append("🔥 Hybrid hesaplamalar oluşturuldu (PDF malzeme + STEP geometri)")
        
        return result
    
    def _select_best_analysis(self, analyses: List[Dict], quality_type: str) -> Optional[Dict]:
        """Belirtilen kalite tipine göre en iyi analizi seç"""
        if not analyses:
            return None
        
        best_analysis = None
        best_score = -1
        
        for analysis in analyses:
            score = self._calculate_analysis_score(analysis, quality_type)
            if score > best_score:
                best_score = score
                best_analysis = analysis
        
        return best_analysis
    
    def _calculate_analysis_score(self, analysis: Dict, quality_type: str) -> float:
        """Analiz kalite skoru hesapla"""
        score = 0.0
        
        if quality_type == 'material_quality':
            # Material quality için skorlama
            materials = analysis.get("material_matches", [])
            score += len(materials) * 10  # Her material +10
            
            # %100 confidence varsa bonus
            for mat in materials:
                if "%100" in str(mat):
                    score += 20
                elif "%" in str(mat):
                    # Percentage çıkar
                    import re
                    pct_match = re.search(r'%(\d+)', str(mat))
                    if pct_match:
                        score += int(pct_match.group(1)) / 5  # %95 = +19 point
            
            # Material calculations varsa bonus
            if analysis.get("all_material_calculations"):
                score += len(analysis["all_material_calculations"]) * 5
        
        elif quality_type == 'geometric_quality':
            # Geometric quality için skorlama
            step_data = analysis.get("step_analysis", {})
            
            # Temel boyutlar varsa
            if step_data.get("X (mm)") and step_data.get("Y (mm)") and step_data.get("Z (mm)"):
                score += 30
            
            # Hacim bilgisi varsa
            if step_data.get("Prizma Hacmi (mm³)"):
                score += 20
            
            # Enhanced renders varsa
            renders = analysis.get("enhanced_renders", {})
            score += len(renders) * 5
            
            # Processing time düşükse bonus (hızlı = kaliteli)
            proc_time = analysis.get("processing_time", 999)
            if proc_time < 5:
                score += 10
        
        # Genel kalite faktörleri
        if analysis.get("analysis_status") == "completed":
            score += 15
        
        if not analysis.get("error_message"):
            score += 10
        
        return score
    
    def _create_hybrid_calculations(self, materials: List[str], step_analysis: Dict) -> List[Dict]:
        """PDF'ten gelen malzemeler + STEP'ten gelen geometri = Hybrid hesaplamalar"""
        try:
            hybrid_calcs = []
            
            # STEP'ten hacim al
            volume_mm3 = step_analysis.get("Prizma Hacmi (mm³)")
            if not volume_mm3 or volume_mm3 <= 0:
                return []
            
            # Her material için hesaplama yap
            from utils.database import db
            materials_db = db.get_db().materials
            
            for material_text in materials:
                # Material name çıkar
                material_name = material_text.split("(")[0].strip()
                
                # DB'den material bul
                material = materials_db.find_one({
                    "$or": [
                        {"name": {"$regex": f"^{material_name}$", "$options": "i"}},
                        {"aliases": {"$in": [material_name]}}
                    ]
                })
                
                if material:
                    density = material.get("density", 2.7)
                    price_per_kg = material.get("price_per_kg", 4.5)
                    
                    # Hesaplama
                    mass_kg = round((volume_mm3 * density) / 1_000_000, 3)
                    material_cost = round(mass_kg * price_per_kg, 2)
                    
                    hybrid_calcs.append({
                        "material": material_name,
                        "original_text": material_text,
                        "category": material.get("category", "Unknown"),
                        "density": density,
                        "mass_kg": mass_kg,
                        "price_per_kg": price_per_kg,
                        "material_cost": material_cost,
                        "volume_mm3": volume_mm3,
                        "source": "hybrid_pdf_step",
                        "confidence": "high" if "%100" in material_text else "medium"
                    })
            
            logger.info(f"[HYBRID] {len(hybrid_calcs)} hybrid hesaplama oluşturuldu")
            return hybrid_calcs
            
        except Exception as e:
            logger.error(f"[HYBRID] Hesaplama hatası: {str(e)}")
            return []
    
    def _calculate_merge_quality(self, merged_result: Dict, by_type: Dict) -> float:
        """Birleştirme kalitesi skoru hesapla"""
        score = 0.0
        
        # Dosya çeşitliliği bonusu
        unique_types = len([t for t, files in by_type.items() if files])
        score += unique_types * 20  # Her tip +20
        
        # Material quality
        if merged_result.get("material_matches"):
            score += len(merged_result["material_matches"]) * 5
        
        # Geometric quality
        if merged_result.get("step_analysis") and merged_result["step_analysis"].get("Prizma Hacmi (mm³)"):
            score += 25
        
        # Render quality
        if merged_result.get("enhanced_renders"):
            score += len(merged_result["enhanced_renders"]) * 3
        
        # Hybrid bonus
        hybrid_count = len([calc for calc in merged_result.get("all_material_calculations", []) 
                           if calc.get("source") == "hybrid_pdf_step"])
        score += hybrid_count * 15
        
        # Normalize to 0-100
        return min(score, 100.0)
    
    def create_group_analysis(self, primary_analysis_id: str, user_id: str) -> Dict[str, Any]:
        """
        Primary analiz için grup analizi oluştur
        
        Args:
            primary_analysis_id: Ana analiz ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Grup analizi sonucu
        """
        try:
            # Primary analizi al
            primary_analysis = FileAnalysis.find_by_id(primary_analysis_id)
            if not primary_analysis:
                return {"success": False, "message": "Primary analiz bulunamadı"}
            
            if primary_analysis['user_id'] != user_id:
                return {"success": False, "message": "Yetki hatası"}
            
            # İlgili dosyaları bul
            related_files = self.find_related_files(
                user_id, 
                primary_analysis['original_filename'],
                primary_analysis_id
            )
            
            # Primary analizi de ekle
            all_analyses = [primary_analysis] + related_files
            
            if len(all_analyses) == 1:
                # Tek dosya varsa normal analizi döndür
                return {
                    "success": True,
                    "is_group": False,
                    "analysis": primary_analysis,
                    "message": "Tek dosya analizi"
                }
            
            # Birleştirme yap
            merged_analysis = self.merge_analysis_results(all_analyses)
            
            if "error" in merged_analysis:
                return {"success": False, "message": merged_analysis["error"]}
            
            # Merged analizi primary analysis'e kaydet
            update_data = {
                "group_analysis": merged_analysis,
                "is_group_primary": True,
                "group_members": [a.get('id') for a in all_analyses],
                "group_merge_timestamp": datetime.utcnow()
            }
            
            FileAnalysis.update_analysis(primary_analysis_id, update_data)
            
            # Diğer dosyaları da güncelle (group reference)
            for related in related_files:
                FileAnalysis.update_analysis(related['id'], {
                    "group_primary_id": primary_analysis_id,
                    "is_group_member": True
                })
            
            logger.info(f"[GROUP] ✅ Grup analizi oluşturuldu: {primary_analysis_id}, {len(all_analyses)} dosya")
            
            return {
                "success": True,
                "is_group": True,
                "group_analysis": merged_analysis,
                "primary_analysis": primary_analysis,
                "related_files": related_files,
                "total_files": len(all_analyses),
                "quality_score": merged_analysis.get("quality_score", 0)
            }
            
        except Exception as e:
            logger.error(f"[GROUP] ❌ Grup analizi hatası: {str(e)}")
            return {"success": False, "message": f"Grup analizi oluşturulamadı: {str(e)}"}
    
    def get_group_analysis(self, analysis_id: str, user_id: str) -> Dict[str, Any]:
        """
        Grup analizini getir (mevcut ise)
        
        Args:
            analysis_id: Analiz ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict: Grup analizi (varsa) veya normal analiz
        """
        try:
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis or analysis['user_id'] != user_id:
                return {"success": False, "message": "Analiz bulunamadı"}
            
            # Bu analiz grup primary'si mi?
            if analysis.get('is_group_primary') and analysis.get('group_analysis'):
                return {
                    "success": True,
                    "is_group": True,
                    "analysis": analysis,
                    "group_analysis": analysis['group_analysis'],
                    "group_members": analysis.get('group_members', [])
                }
            
            # Bu analiz grup üyesi mi?
            elif analysis.get('is_group_member') and analysis.get('group_primary_id'):
                primary_id = analysis['group_primary_id']
                primary_analysis = FileAnalysis.find_by_id(primary_id)
                
                if primary_analysis and primary_analysis.get('group_analysis'):
                    return {
                        "success": True,
                        "is_group": True,
                        "analysis": primary_analysis,
                        "group_analysis": primary_analysis['group_analysis'],
                        "group_members": primary_analysis.get('group_members', []),
                        "redirected_from": analysis_id
                    }
            
            # Normal analiz
            return {
                "success": True,
                "is_group": False,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"[GROUP] Grup analizi getirme hatası: {str(e)}")
            return {"success": False, "message": str(e)}


# Utility functions
def normalize_filename_for_grouping(filename: str) -> str:
    """Dosya adını gruplama için normalize et"""
    # Uzantıyı çıkar
    if '.' in filename:
        base = filename.rsplit('.', 1)[0]
    else:
        base = filename
    
    # Küçük harfe çevir
    base = base.lower()
    
    # Özel karakterleri temizle
    import re
    base = re.sub(r'[^\w\-_]', '', base)
    
    return base


def should_merge_files(file1_name: str, file2_name: str, time_diff_minutes: float = 30) -> bool:
    """İki dosyanın birleştirilip birleştirilmeyeceğini belirle"""
    base1 = normalize_filename_for_grouping(file1_name)
    base2 = normalize_filename_for_grouping(file2_name)
    
    # Aynı base name ve zaman aralığında
    return base1 == base2


# Global service instance
grouping_service = FileGroupingService()
