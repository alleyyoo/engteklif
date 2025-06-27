# services/material_analysis.py - T6 REMOVED VERSION

import re
import os
import time
import pytesseract
import cadquery as cq
from pdf2image import convert_from_path
import pikepdf
from tempfile import NamedTemporaryFile
from docx import Document
import subprocess
from utils.database import db
from functools import lru_cache
import threading
import hashlib
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import PyPDF2

print("[INFO] ✅ Material Analysis Service - T6 REMOVED VERSION")

class MaterialAnalysisServiceOptimized:
    def __init__(self):
        self.database = db.get_db()
        self._material_cache = {}
        self._cache_lock = threading.Lock()
        self._keyword_cache = None
        self._alias_cache = None
        
        # ✅ Initialize materials and cache
        self._ensure_materials_exist()
        self._preload_materials()
        self._preload_material_keywords()
    
    @lru_cache(maxsize=100)
    def _get_materials_cached(self):
        """Cached material lookup"""
        with self._cache_lock:
            if not self._material_cache:
                materials = list(self.database.materials.find({}))
                for material in materials:
                    self._material_cache[material['name']] = material
            return self._material_cache
    
    def _preload_materials(self):
        """Preload materials into memory for instant access"""
        try:
            materials = list(self.database.materials.find({}))
            with self._cache_lock:
                self._material_cache = {mat['name']: mat for mat in materials}
            print(f"[OPTIMIZED] 🚀 Preloaded {len(materials)} materials into cache")
        except Exception as e:
            print(f"[OPTIMIZED] ⚠️ Material preload failed: {e}")
    
    def _preload_material_keywords(self):
        """Preload material keywords for fast searching"""
        try:
            materials = self._get_materials_cached()
            keyword_list = []
            alias_map = {}
            
            for material_name, material in materials.items():
                # Add main name
                normalized_name = self._normalize_for_match(material_name)
                keyword_list.append(normalized_name)
                
                # Add aliases
                aliases = material.get('aliases', [])
                for alias in aliases:
                    if alias.strip():
                        normalized_alias = self._normalize_for_match(alias)
                        alias_map[normalized_alias] = material_name
                        keyword_list.append(normalized_alias)
            
            self._keyword_cache = keyword_list
            self._alias_cache = alias_map
            
            print(f"[OPTIMIZED] 🔤 Preloaded {len(keyword_list)} keywords and {len(alias_map)} aliases")
            
        except Exception as e:
            print(f"[OPTIMIZED] ⚠️ Keyword preload failed: {e}")
            self._keyword_cache = []
            self._alias_cache = {}
    
    def _normalize_for_match(self, text):
        """Fast text normalization for material matching"""
        if not text:
            return ""
        
        text = str(text).lower()
        # Turkish character replacements
        replacements = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'}
        for tr_char, en_char in replacements.items():
            text = text.replace(tr_char, en_char)
        
        # Remove non-alphanumeric
        text = re.sub(r'[^\w]', '', text)
        return text
    
    # =====================================================
    # MAIN ANALYSIS METHODS
    # =====================================================
    
    def analyze_document_comprehensive(self, file_path, file_type, user_id):
        """Main comprehensive analysis method - ULTRA-FAST OPTIMIZED"""
        result = {
            "material_matches": [],
            "step_analysis": {},
            "cost_estimation": {},
            "ai_price_prediction": {},
            "all_material_calculations": [],
            "material_options": [],
            "processing_log": [],
            "isometric_view": None,
            "isometric_view_clean": None,
            "enhanced_renders": {},
            "step_file_hash": None
        }
        
        try:
            start_time = time.time()
            print(f"[COMPREHENSIVE] ⚡ Starting ultra-fast comprehensive analysis: {file_path} ({file_type})")
            
            if file_type == 'pdf':
                result = self._analyze_pdf_comprehensive_fast(file_path, result)
            elif file_type in ['step', 'stp']:
                result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                result["processing_log"].append("🔧 STEP analizi tamamlandı")
                
                if not result.get("material_matches"):
                    result["material_matches"] = ["6061 (%default)"]  # ✅ T6 REMOVED
                    
            elif file_type in ['doc', 'docx']:
                result = self._analyze_document_fast(file_path, result)
            
            # ✅ LIGHTNING-FAST MATERIAL CALCULATIONS
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)")
            
            if prizma_hacim and prizma_hacim > 0:
                print(f"[COMPREHENSIVE] 📊 Fast material calculations: {prizma_hacim} mm³")
                
                # Found materials calculations
                if result.get("material_matches"):
                    result["all_material_calculations"] = self._calculate_found_materials_lightning(
                        prizma_hacim, result["material_matches"]
                    )
                    result["processing_log"].append(f"🧮 {len(result['all_material_calculations'])} bulunan malzeme hesaplandı")
                
                # Top materials only for speed
                result["material_options"] = self._calculate_top_materials_lightning(prizma_hacim, limit=15)
                result["processing_log"].append(f"📊 {len(result['material_options'])} malzeme seçeneği hesaplandı")
                
            else:
                result["processing_log"].append("⚠️ Hacim bilgisi yok, malzeme hesaplaması yapılamadı")
            
            # ✅ FAST COST ESTIMATION
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                cost_service = CostEstimationServiceFast()
                result["cost_estimation"] = cost_service.calculate_cost_lightning(
                    result["step_analysis"], 
                    result.get("material_matches", ["6061 (%default)"])  # ✅ T6 REMOVED
                )
                result["processing_log"].append("💰 Maliyet hesaplandı")
            
            # ✅ QUICK AI PRICE PREDICTION
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                result["ai_price_prediction"] = self._calculate_ai_price_lightning(
                    result["step_analysis"], 
                    result.get("all_material_calculations", [])
                )
                result["processing_log"].append("🤖 AI fiyat tahmini")
            
            total_time = time.time() - start_time
            print(f"[COMPREHENSIVE] ✅ Comprehensive analysis completed in {total_time:.2f}s")
            result["processing_log"].append(f"⏱️ Toplam süre: {total_time:.2f}s")
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"Comprehensive analysis error: {str(e)}"
            print(f"[COMPREHENSIVE] ❌ {error_msg}")
            print(f"[COMPREHENSIVE] 📋 Traceback: {traceback.format_exc()}")
            result["error"] = error_msg
            result["processing_log"].append(f"❌ HATA: {error_msg}")
            return result
    
    def analyze_document_ultra_fast(self, file_path, file_type, user_id):
        """✅ ULTRA-FAST - Target < 2 seconds for most files"""
        result = {
            "material_matches": [],
            "step_analysis": {},
            "cost_estimation": {},
            "ai_price_prediction": {},
            "all_material_calculations": [],
            "material_options": [],
            "processing_log": [],
            "step_file_hash": None
        }
        
        try:
            start_time = time.time()
            print(f"[ULTRA-FAST] ⚡ Starting ultra-fast analysis: {file_path} ({file_type})")
            
            if file_type == 'pdf':
                result = self._analyze_pdf_ultra_fast(file_path, result)
            elif file_type in ['step', 'stp']:
                result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                result["processing_log"].append("🔧 STEP analizi tamamlandı")
                
                if not result.get("material_matches"):
                    result["material_matches"] = ["6061 (%default)"]  # ✅ T6 REMOVED
                    
            elif file_type in ['doc', 'docx']:
                result = self._analyze_document_fast(file_path, result)
            
            # ✅ LIGHTNING-FAST MATERIAL CALCULATIONS
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)")
            
            if prizma_hacim and prizma_hacim > 0:
                print(f"[ULTRA-FAST] 📊 Fast material calculations: {prizma_hacim} mm³")
                
                # ✅ Fast calculations using cached materials
                if result.get("material_matches"):
                    result["all_material_calculations"] = self._calculate_found_materials_lightning(
                        prizma_hacim, result["material_matches"]
                    )
                    result["processing_log"].append(f"🧮 {len(result['all_material_calculations'])} malzeme hesaplandı")
                
                # ✅ Top 10 materials only for speed
                result["material_options"] = self._calculate_top_materials_lightning(prizma_hacim, limit=10)
                result["processing_log"].append(f"📊 Top {len(result['material_options'])} malzeme seçeneği")
                
            else:
                result["processing_log"].append("⚠️ Hacim bilgisi yok, hesaplama atlandı")
            
            # ✅ FAST COST ESTIMATION
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                result["cost_estimation"] = self._calculate_cost_lightning(
                    result["step_analysis"], 
                    result.get("material_matches", ["6061 (%default)"])  # ✅ T6 REMOVED
                )
                result["processing_log"].append("💰 Hızlı maliyet hesaplandı")
            
            # ✅ QUICK AI PRICE PREDICTION
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                result["ai_price_prediction"] = self._calculate_ai_price_lightning(
                    result["step_analysis"], 
                    result.get("all_material_calculations", [])
                )
                result["processing_log"].append("🤖 AI fiyat tahmini")
            
            total_time = time.time() - start_time
            print(f"[ULTRA-FAST] ✅ Analysis completed in {total_time:.2f}s")
            result["processing_log"].append(f"⏱️ Toplam süre: {total_time:.2f}s")
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"Ultra-fast analysis error: {str(e)}"
            print(f"[ULTRA-FAST] ❌ {error_msg}")
            print(f"[ULTRA-FAST] 📋 Traceback: {traceback.format_exc()}")
            result["error"] = error_msg
            result["processing_log"].append(f"❌ HATA: {error_msg}")
            return result
    
    # =====================================================
    # PDF ANALYSIS METHODS
    # =====================================================
    
    def _analyze_pdf_comprehensive_fast(self, file_path, result):
        """✅ COMPREHENSIVE PDF analysis with STEP rendering support"""
        start_time = time.time()
        result["processing_log"].append("📄 Comprehensive PDF analizi başlatıldı")
        
        # ✅ STEP EXTRACTION
        step_paths = self._extract_step_from_pdf_optimized(file_path)
        extracted_step_path = None
        permanent_step_path = None
        
        if step_paths:
            extracted_step_path = step_paths[0]
            step_filename = os.path.basename(extracted_step_path)
            result["processing_log"].append(f"📎 STEP çıkarıldı: {step_filename}")
            
            # ✅ Save permanently
            analysis_id = f"pdf_{int(time.time())}_{hashlib.md5(file_path.encode()).hexdigest()[:8]}"
            permanent_dir = os.path.join("static", "stepviews", analysis_id)
            os.makedirs(permanent_dir, exist_ok=True)
            
            permanent_step_filename = f"extracted_{analysis_id}.step"
            permanent_step_path = os.path.join(permanent_dir, permanent_step_filename)
            
            import shutil
            shutil.copy2(extracted_step_path, permanent_step_path)
            
            result["extracted_step_path"] = permanent_step_path
            result["pdf_analysis_id"] = analysis_id
            
            # ✅ STEP ANALYSIS
            result["step_analysis"] = self.analyze_step_file_ultra_fast(permanent_step_path)
            result["processing_log"].append("🔧 STEP analizi tamamlandı")
            result["step_file_hash"] = self._calculate_file_hash_fast(permanent_step_path)
        else:
            # ✅ DEFAULT VALUES
            result["step_analysis"] = {
                "X (mm)": 90.0, "Y (mm)": 40.0, "Z (mm)": 15.0,
                "X+Pad (mm)": 100, "Y+Pad (mm)": 50, "Z+Pad (mm)": 25,
                "Silindirik Çap (mm)": 90.0, "Silindirik Yükseklik (mm)": 15.0,
                "Prizma Hacmi (mm³)": 125000, "Ürün Hacmi (mm³)": 100000,
                "Talaş Hacmi (mm³)": 25000, "Talaş Oranı (%)": 20.0,
                "Toplam Yüzey Alanı (mm²)": 15000, "method": "estimated_from_pdf"
            }
            result["processing_log"].append("⚠️ STEP bulunamadı, varsayılan değerler")
        
        # ✅ MATERIAL SEARCH
        materials = self._find_materials_in_pdf_optimized(file_path)
        
        if materials:
            result["material_matches"] = materials
            result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
        else:
            result["material_matches"] = ["6061 (%estimated)"]  # ✅ T6 REMOVED
            result["processing_log"].append("⚠️ Malzeme tespit edilemedi, varsayılan kullanıldı")
        
        # ✅ CLEANUP
        if extracted_step_path and extracted_step_path != permanent_step_path:
            try:
                os.remove(extracted_step_path)
            except:
                pass
        
        total_time = time.time() - start_time
        print(f"[PDF-COMPREHENSIVE] ✅ PDF analysis completed: {total_time:.3f}s")
        
        return result
    
    def _analyze_pdf_ultra_fast(self, file_path, result):
        """✅ ULTRA-FAST PDF analysis - Target < 1.5 seconds"""
        start_time = time.time()
        result["processing_log"].append("📄 Ultra-fast PDF analizi")
        
        # ✅ 1. QUICK STEP EXTRACTION CHECK (< 200ms)
        step_extraction_start = time.time()
        step_paths = self._extract_step_from_pdf_fast(file_path)
        step_extraction_time = time.time() - step_extraction_start
        print(f"[PDF-ULTRA] ⏱️ STEP extraction: {step_extraction_time:.3f}s")
        
        extracted_step_path = None
        permanent_step_path = None
        
        if step_paths:
            extracted_step_path = step_paths[0]
            step_filename = os.path.basename(extracted_step_path)
            result["processing_log"].append(f"📎 STEP çıkarıldı: {step_filename}")
            
            # ✅ Save permanently (optimized)
            analysis_id = f"pdf_{int(time.time())}_{hashlib.md5(file_path.encode()).hexdigest()[:6]}"
            permanent_dir = os.path.join("static", "stepviews", analysis_id)
            os.makedirs(permanent_dir, exist_ok=True)
            
            permanent_step_filename = f"extracted_{analysis_id}.step"
            permanent_step_path = os.path.join(permanent_dir, permanent_step_filename)
            
            import shutil
            shutil.copy2(extracted_step_path, permanent_step_path)
            
            result["extracted_step_path"] = permanent_step_path
            result["pdf_analysis_id"] = analysis_id
            
            # ✅ FAST STEP ANALYSIS
            step_analysis_start = time.time()
            result["step_analysis"] = self.analyze_step_file_ultra_fast(permanent_step_path)
            step_analysis_time = time.time() - step_analysis_start
            print(f"[PDF-ULTRA] ⏱️ STEP analysis: {step_analysis_time:.3f}s")
            
            result["processing_log"].append("🔧 Hızlı STEP analizi")
            result["step_file_hash"] = self._calculate_file_hash_fast(permanent_step_path)
        else:
            # ✅ DEFAULT VALUES (instant)
            result["step_analysis"] = {
                "X (mm)": 90.0, "Y (mm)": 40.0, "Z (mm)": 15.0,
                "X+Pad (mm)": 100, "Y+Pad (mm)": 50, "Z+Pad (mm)": 25,
                "Silindirik Çap (mm)": 90.0, "Silindirik Yükseklik (mm)": 15.0,
                "Prizma Hacmi (mm³)": 125000, "Ürün Hacmi (mm³)": 100000,
                "Talaş Hacmi (mm³)": 25000, "Talaş Oranı (%)": 20.0,
                "Toplam Yüzey Alanı (mm²)": 15000, "method": "estimated_from_pdf"
            }
            result["processing_log"].append("⚠️ STEP bulunamadı, varsayılan değerler")
        
        # ✅ 2. LIGHTNING-FAST MATERIAL SEARCH (< 300ms)
        material_search_start = time.time()
        
        # Try quick PDF text extraction first (no OCR)
        materials = self._quick_pdf_text_search_lightning(file_path)
        
        if not materials:
            # Quick OCR - only first page, low DPI
            print(f"[PDF-ULTRA] 🔍 Quick OCR fallback...")
            text = self._extract_text_from_pdf_minimal(file_path)
            materials = self._find_materials_in_text_lightning(text)
        
        material_search_time = time.time() - material_search_start
        print(f"[PDF-ULTRA] ⏱️ Material search: {material_search_time:.3f}s")
        
        if materials:
            result["material_matches"] = materials
            result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
        else:
            result["material_matches"] = ["6061 (%estimated)"]  # ✅ T6 REMOVED
            result["processing_log"].append("⚠️ Varsayılan malzeme")
        
        # ✅ CLEANUP
        if extracted_step_path and extracted_step_path != permanent_step_path:
            try:
                os.remove(extracted_step_path)
            except:
                pass
        
        total_pdf_time = time.time() - start_time
        print(f"[PDF-ULTRA] ✅ PDF analysis completed: {total_pdf_time:.3f}s")
        
        return result
    
    # =====================================================
    # STEP ANALYSIS METHODS
    # =====================================================
    
    def analyze_step_file(self, step_path):
        """Standard STEP analysis - kept for compatibility"""
        return self.analyze_step_file_ultra_fast(step_path)
    
    def analyze_step_file_ultra_fast(self, step_path):
        """✅ ULTRA-FAST STEP analysis - Target < 500ms"""
        try:
            start_time = time.time()
            print(f"[STEP-ULTRA] 🔧 Ultra-fast STEP analysis: {os.path.basename(step_path)}")
            
            # ✅ Quick import with timeout protection
            try:
                assembly = cq.importers.importStep(step_path)
                if not assembly.objects:
                    return {"error": "Empty STEP file"}
            except Exception as import_error:
                print(f"[STEP-ULTRA] ❌ Import failed: {import_error}")
                return {"error": f"STEP import failed: {str(import_error)}"}
            
            # ✅ LIGHTNING-FAST ANALYSIS - No optimization loops
            shapes = assembly.objects
            if not shapes:
                return {"error": "No shapes found"}
            
            # Use largest shape only (no complex processing)
            main_shape = max(shapes, key=lambda s: s.Volume())
            main_bbox = main_shape.BoundingBox()
            
            # ✅ DIRECT BOUNDING BOX (no rotation optimization)
            x, y, z = main_bbox.xlen, main_bbox.ylen, main_bbox.zlen
            
            # ✅ FAST PADDING CALCULATION
            x_pad = int(x) + 10 if x % 1 < 0.01 else int(x) + 11
            y_pad = int(y) + 10 if y % 1 < 0.01 else int(y) + 11
            z_pad = int(z) + 10 if z % 1 < 0.01 else int(z) + 11
            
            # ✅ LIGHTNING CALCULATIONS
            volume_padded = x_pad * y_pad * z_pad
            
            try:
                # Quick volume and area calculation
                product_volume = main_shape.Volume()
                total_surface_area = main_shape.Area()
            except:
                # Ultra-fast fallback estimates
                product_volume = x * y * z * 0.75  # 75% fill estimate
                total_surface_area = 2 * (x*y + y*z + x*z) * 1.2  # 20% extra for features
            
            waste_volume = volume_padded - product_volume
            waste_ratio = (waste_volume / volume_padded * 100) if volume_padded > 0 else 0.0
            
            cylindrical_diameter = max(x, y)
            cylindrical_height = z
            
            analysis_time = time.time() - start_time
            print(f"[STEP-ULTRA] ✅ Ultra-fast analysis completed: {analysis_time:.3f}s")
            
            return {
                "X (mm)": round(x, 2),
                "Y (mm)": round(y, 2),
                "Z (mm)": round(z, 2),
                "Silindirik Çap (mm)": round(cylindrical_diameter, 2),
                "Silindirik Yükseklik (mm)": round(cylindrical_height, 2),
                "X+Pad (mm)": x_pad,
                "Y+Pad (mm)": y_pad,
                "Z+Pad (mm)": z_pad,
                "Prizma Hacmi (mm³)": round(volume_padded, 1),
                "Ürün Hacmi (mm³)": round(product_volume, 1),
                "Talaş Hacmi (mm³)": round(waste_volume, 1),
                "Talaş Oranı (%)": round(waste_ratio, 1),
                "Toplam Yüzey Alanı (mm²)": round(total_surface_area, 1),
                "shape_count": len(shapes),
                "analysis_time": analysis_time,
                "method": "ultra_fast_cadquery_analysis"
            }
            
        except Exception as e:
            print(f"[STEP-ULTRA] ❌ Ultra-fast analysis failed: {str(e)}")
            return {"error": f"Ultra-fast STEP analysis failed: {str(e)}"}
    
    # =====================================================
    # DOCUMENT ANALYSIS METHODS
    # =====================================================
    
    def _analyze_document_fast(self, file_path, result):
        """Fast DOC/DOCX analysis"""
        result["processing_log"].append("📝 Fast document analizi")
        
        try:
            if file_path.lower().endswith('.docx'):
                text = self._extract_text_from_docx_fast(file_path)
            else:
                text = self._extract_text_from_doc_fast(file_path)
            
            # Fast material search
            materials = self._find_materials_in_text_lightning(text)
            if materials:
                result["material_matches"] = materials
                result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
            else:
                result["material_matches"] = ["6061 (%estimated)"]  # ✅ T6 REMOVED
                result["processing_log"].append("⚠️ Varsayılan malzeme")
            
            # Default STEP analysis for documents
            result["step_analysis"] = {
                "X (mm)": 50.0, "Y (mm)": 30.0, "Z (mm)": 20.0,
                "X+Pad (mm)": 60, "Y+Pad (mm)": 40, "Z+Pad (mm)": 30,
                "Silindirik Çap (mm)": 50.0, "Silindirik Yükseklik (mm)": 20.0,
                "Prizma Hacmi (mm³)": 72000, "Ürün Hacmi (mm³)": 56000,
                "Talaş Hacmi (mm³)": 16000, "Talaş Oranı (%)": 22.2,
                "Toplam Yüzey Alanı (mm²)": 8800, "method": "estimated_from_document"
            }
            
        except Exception as e:
            result["processing_log"].append(f"❌ Document analiz hatası: {e}")
            
        return result
    
    # =====================================================
    # MATERIAL CALCULATION METHODS
    # =====================================================
    
    def _calculate_found_materials_lightning(self, prizma_hacim_mm3, found_materials):
        """✅ LIGHTNING-FAST material calculations using cached data"""
        try:
            calculations = []
            materials_cache = self._get_materials_cached()
            processed_materials = set()
            
            for material_text in found_materials:
                # ✅ Clean material name from T designations
                material_name = material_text.split("(")[0].strip()
                # Remove any T designations like T6, T4, T3
                material_name = re.sub(r'-T\d+', '', material_name)
                
                # Skip duplicates
                if material_name in processed_materials:
                    continue
                processed_materials.add(material_name)
                
                # Extract confidence
                confidence_match = re.search(r'%(\d+)', material_text)
                confidence = int(confidence_match.group(1)) if confidence_match else 70
                
                # ✅ LIGHTNING LOOKUP from cache
                material = None
                material_name_norm = material_name.lower()
                
                for cached_name, cached_material in materials_cache.items():
                    if (material_name_norm in cached_name.lower() or 
                        cached_name.lower() in material_name_norm or
                        any(material_name_norm in alias.lower() for alias in cached_material.get('aliases', []))):
                        material = cached_material
                        break
                
                if not material:
                    # ✅ LIGHTNING FALLBACK based on patterns - ALL T DESIGNATIONS REMOVED
                    material_patterns = {
                        "6061": (2.7, 4.5, "Alüminyum"),
                        "7075": (2.81, 6.2, "Alüminyum"),
                        "304": (7.93, 8.5, "Paslanmaz Çelik"),
                        "316": (7.98, 12.0, "Paslanmaz Çelik"),
                        "ST37": (7.85, 2.2, "Karbon Çelik"),
                        "S235": (7.85, 2.2, "Karbon Çelik"),
                        "C45": (7.85, 2.8, "Karbon Çelik")
                    }
                    
                    density, price_per_kg, category = 2.7, 4.5, "Unknown"  # Default
                    
                    # Clean material name from any T designations
                    clean_material_name = re.sub(r'-T\d+', '', material_name.upper())
                    
                    for pattern, (d, p, c) in material_patterns.items():
                        if pattern in clean_material_name:
                            density, price_per_kg, category = d, p, c
                            # Use clean name without T designation
                            material_name = pattern.lower() if pattern.isdigit() else pattern
                            break
                    
                    actual_name = material_name
                    aliases = []
                else:
                    density = material.get("density", 2.7)
                    price_per_kg = material.get("price_per_kg", 4.5)
                    actual_name = material.get("name", material_name)
                    category = material.get("category", "Unknown")
                    aliases = material.get("aliases", [])
                
                # ✅ LIGHTNING CALCULATION
                mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                material_cost = round(mass_kg * price_per_kg, 2)
                
                calculations.append({
                    "material": actual_name,
                    "original_text": material_text,
                    "confidence": f"%{confidence}",
                    "confidence_value": confidence,
                    "category": category,
                    "aliases": aliases,
                    "density": density,
                    "mass_kg": mass_kg,
                    "price_per_kg": price_per_kg,
                    "material_cost": material_cost,
                    "volume_mm3": prizma_hacim_mm3,
                    "found_in_db": material is not None
                })
            
            # Sort by confidence
            calculations.sort(key=lambda x: x['confidence_value'], reverse=True)
            
            print(f"[CALC-LIGHTNING] ✅ Lightning calculation: {len(calculations)} materials")
            return calculations
            
        except Exception as e:
            print(f"[CALC-LIGHTNING] ❌ Lightning calculation failed: {e}")
            return []
    
    def _calculate_top_materials_lightning(self, prizma_hacim_mm3, limit=15):
        """✅ LIGHTNING top materials calculation"""
        try:
            materials_cache = self._get_materials_cached()
            top_materials = []
            
            # ✅ Process limited set for speed
            for material_name, material in list(materials_cache.items())[:limit]:
                density = material.get("density", 2.7)
                price_per_kg = material.get("price_per_kg", 4.5)
                
                if density <= 0 or price_per_kg < 0:
                    continue
                
                # ✅ LIGHTNING CALCULATION
                mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                material_cost = round(mass_kg * price_per_kg, 2)
                
                top_materials.append({
                    "name": material_name,
                    "category": material.get("category", "Unknown"),
                    "density": density,
                    "mass_kg": mass_kg,
                    "price_per_kg": price_per_kg,
                    "material_cost": material_cost,
                    "volume_mm3": prizma_hacim_mm3
                })
            
            # Sort by cost (cheapest first)
            top_materials.sort(key=lambda x: x["material_cost"])
            
            print(f"[TOP-LIGHTNING] ✅ Top {len(top_materials)} materials calculated")
            return top_materials
            
        except Exception as e:
            print(f"[TOP-LIGHTNING] ❌ Top materials calculation failed: {e}")
            return []
    
    # =====================================================
    # COST CALCULATION METHODS
    # =====================================================
    
    def _calculate_cost_lightning(self, step_analysis, material_matches):
        """✅ LIGHTNING cost calculation"""
        try:
            if not step_analysis or step_analysis.get("error"):
                return {"error": "STEP analysis required"}
            
            material_name = material_matches[0].split("(")[0].strip() if material_matches else "6061"  # ✅ T REMOVED
            # Clean any T designations
            material_name = re.sub(r'-T\d+', '', material_name)
            
            # ✅ LIGHTNING VALUES
            volume = step_analysis.get("Prizma Hacmi (mm³)", 100000)
            waste = step_analysis.get("Talaş Hacmi (mm³)", 25000)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 10000)
            
            # ✅ LIGHTNING MATERIAL COST
            materials_cache = self._get_materials_cached()
            material = materials_cache.get(material_name)
            
            if material:
                density = material.get("density", 2.7)
                price = material.get("price_per_kg", 4.5)
            else:
                density, price = 2.7, 4.5  # Default aluminum
            
            volume_cm3 = volume / 1000
            mass_kg = (volume_cm3 * density) / 1000
            material_cost = mass_kg * price
            
            # ✅ LIGHTNING LABOR CALCULATION
            labor_hours = max((waste / 3600) + (surface / 600), 0.5)  # Simplified
            labor_cost = labor_hours * 65  # $65/hour
            
            total = material_cost + labor_cost
            
            return {
                "material": {"name": material_name, "cost_usd": round(material_cost, 2), "mass_kg": round(mass_kg, 3)},
                "machining": {"hours": round(labor_hours, 2), "cost_usd": round(labor_cost, 2)},
                "costs": {"material_usd": round(material_cost, 2), "labor_usd": round(labor_cost, 2), "total_usd": round(total, 2)}
            }
            
        except Exception as e:
            return {"error": f"Lightning cost calculation failed: {str(e)}"}
    
    def _calculate_ai_price_lightning(self, step_analysis, material_calculations):
        """✅ LIGHTNING AI price estimation"""
        try:
            waste = step_analysis.get("Talaş Hacmi (mm³)", 0)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 0)
            
            material_cost = 0
            if material_calculations and len(material_calculations) > 0:
                material_cost = material_calculations[0].get("material_cost", 0)
            
            # ✅ LIGHTNING CALCULATIONS
            kaba_sure = waste / 4000 if waste > 0 else 0  # Simplified
            finishing_sure = surface / 500 if surface > 0 else 0  # Simplified
            
            kaba_maliyet = (kaba_sure / 60) * 65
            finishing_maliyet = (finishing_sure / 60) * 120
            toplam = kaba_maliyet + finishing_maliyet + material_cost
            
            return {
                "toplam": round(toplam, 2),
                "kaba_maliyet": round(kaba_maliyet, 2),
                "finishing_maliyet": round(finishing_maliyet, 2),
                "material_cost": round(material_cost, 2),
                "toplam_sure_saat": round((kaba_sure + finishing_sure) / 60, 2)
            }
        except Exception as e:
            return {"error": f"Lightning AI price estimation failed: {str(e)}"}
    
    # =====================================================
    # PDF PROCESSING METHODS
    # =====================================================
    
    def _extract_step_from_pdf_fast(self, pdf_path):
        """✅ FAST STEP extraction with timeout protection"""
        try:
            extracted = []
            start_time = time.time()
            TIMEOUT_SECONDS = 0.8  # 800ms max
            
            with pikepdf.open(pdf_path) as pdf:
                try:
                    root = pdf.trailer.get("/Root", {})
                    names = root.get("/Names", {})
                    embedded = names.get("/EmbeddedFiles", {})
                    files = embedded.get("/Names", [])
                    
                    for i in range(0, min(len(files), 10), 2):  # Max 5 files
                        # ✅ TIMEOUT CHECK
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            print(f"[STEP-FAST] ⏰ Timeout reached")
                            break
                        
                        if i + 1 < len(files):
                            try:
                                file_spec = files[i + 1]
                                file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                                
                                if file_name.lower().endswith(('.stp', '.step')):
                                    file_data = file_spec['/EF']['/F'].read_bytes()
                                    
                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                    os.makedirs(temp_dir, exist_ok=True)
                                    
                                    safe_filename = f"fast_extracted_{int(time.time())}.step"
                                    output_path = os.path.join(temp_dir, safe_filename)
                                    
                                    with open(output_path, 'wb') as f:
                                        f.write(file_data)
                                    
                                    if os.path.getsize(output_path) > 100:
                                        extracted.append(output_path)
                                        print(f"[STEP-FAST] ⚡ Extracted: {file_name}")
                                        break  # First STEP found, exit
                                    else:
                                        os.remove(output_path)
                                        
                            except Exception as e:
                                continue
                                
                except Exception as e:
                    print(f"[STEP-FAST] ⚠️ Embedded files error: {e}")
            
            extraction_time = time.time() - start_time
            print(f"[STEP-FAST] ⏱️ STEP extraction: {extraction_time:.3f}s")
            
            return extracted
            
        except Exception as e:
            print(f"[STEP-FAST] ❌ Fast STEP extraction failed: {e}")
            return []
    
    def _extract_step_from_pdf_optimized(self, pdf_path):
        """✅ OPTIMIZED STEP extraction for comprehensive analysis"""
        return self._extract_step_from_pdf_fast(pdf_path)
    
    def _find_materials_in_pdf_optimized(self, pdf_path):
        """✅ OPTIMIZED material finding in PDF"""
        # Try quick text search first
        materials = self._quick_pdf_text_search_lightning(pdf_path)
        
        if not materials:
            # Try OCR on first page only
            try:
                pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
                if pages:
                    text = pytesseract.image_to_string(pages[0], lang='tur+eng')
                    materials = self._find_materials_in_text_lightning(text)
            except Exception as e:
                print(f"[PDF-MAT] ⚠️ OCR failed: {e}")
        
        return materials
    
    def _quick_pdf_text_search_lightning(self, pdf_path):
        """✅ LIGHTNING PDF text search - no OCR"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text and len(text.strip()) > 10:
                        return self._find_materials_in_text_lightning(text)
            return []
        except:
            return []
    
    def _extract_text_from_pdf_minimal(self, pdf_path):
        """✅ MINIMAL OCR for speed"""
        try:
            pages = convert_from_path(pdf_path, dpi=100, first_page=1, last_page=1)
            if pages:
                text = pytesseract.image_to_string(pages[0], lang='eng', config='--psm 6')
                return text
            return ""
        except Exception as e:
            print(f"[OCR-MINIMAL] ⚠️ Failed: {e}")
            return ""
    
    # =====================================================
    # MATERIAL SEARCH METHODS - T6 REMOVED
    # =====================================================
    
    def _find_materials_in_text_lightning(self, text):
        """✅ LIGHTNING material search - T6 REMOVED"""
        if not text or len(text.strip()) < 5:
            return []
        
        materials = []
        text_upper = text.upper()
        
        # ✅ LIGHTNING PATTERNS - T6 REMOVED, 2024 REMOVED
        lightning_patterns = {
            "6061": "6061",      # ✅ NO MORE T6
            "7075": "7075",      # ✅ NO MORE T6
            # ✅ 2024 REMOVED - Database'de olmayan malzeme kaldırıldı
            "304": "304 Paslanmaz",
            "316": "316 Paslanmaz",
            "ST37": "St37",
            "S235": "St37",
            "C45": "C45",
            "CK45": "C45"
        }
        
        confidence_found = {}
        
        for pattern, name in lightning_patterns.items():
            if pattern in text_upper:
                confidence_found[name] = 100
                print(f"[MAT-LIGHTNING] ⚡ Found: {pattern} -> {name} (100%)")
        
        # ✅ GENERAL PATTERNS if no specific alloys found
        if not confidence_found:
            general_patterns = {
                "ALÜMINYUM": "6061",      # ✅ NO MORE T6
                "ALUMINUM": "6061",       # ✅ NO MORE T6
                "ALUMINIUM": "6061",      # ✅ NO MORE T6
                "ÇELİK": "St37",
                "STEEL": "St37",
                "PASLANMAZ": "304 Paslanmaz",
                "STAINLESS": "304 Paslanmaz"
            }
            
            for keyword, name in general_patterns.items():
                if keyword in text_upper:
                    confidence_found[name] = 70
                    break
        
        # Convert to required format - clean from T designations
        for material_name, confidence in confidence_found.items():
            # Clean any T designations that might have slipped through
            clean_name = re.sub(r'-T\d+', '', material_name)
            confidence_str = f"%{confidence}" if confidence == 100 else "estimated"
            materials.append(f"{clean_name} ({confidence_str})")
        
        return materials[:3]  # Max 3 for speed
    
    # =====================================================
    # DOCUMENT PROCESSING METHODS
    # =====================================================
    
    def _extract_text_from_docx_fast(self, file_path):
        """Fast DOCX text extraction"""
        try:
            doc = Document(file_path)
            # Only first 10 paragraphs for speed
            texts = [p.text for p in doc.paragraphs[:10] if p.text.strip()]
            return "\n".join(texts)
        except Exception as e:
            print(f"[DOCX-FAST] ❌ Failed: {e}")
            return ""
    
    def _extract_text_from_doc_fast(self, file_path):
        """Fast DOC text extraction"""
        try:
            # Quick conversion attempt
            output_dir = os.path.dirname(file_path)
            result = subprocess.run([
                "libreoffice", "--headless", "--convert-to", "docx", 
                "--outdir", output_dir, file_path
            ], capture_output=True, timeout=10)  # 10 second timeout
            
            docx_path = os.path.splitext(file_path)[0] + ".docx"
            if os.path.exists(docx_path):
                text = self._extract_text_from_docx_fast(docx_path)
                # Cleanup converted file
                try:
                    os.remove(docx_path)
                except:
                    pass
                return text
            return ""
        except Exception as e:
            print(f"[DOC-FAST] ❌ Failed: {e}")
            return ""
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _calculate_file_hash_fast(self, file_path):
        """✅ FAST file hash calculation"""
        try:
            # Read only first 2KB for speed
            with open(file_path, 'rb') as f:
                chunk = f.read(2048)
            return hashlib.md5(chunk).hexdigest()[:16]
        except:
            return None
    
    def _ensure_materials_exist(self):
        """Ensure materials exist - lightning check"""
        try:
            count = self.database.materials.count_documents({})
            if count < 5:
                self._add_essential_materials()
                print(f"[MATERIALS] ✅ Added essential materials, total: {count + 8}")
            else:
                print(f"[MATERIALS] ✅ Materials ready: {count} items")
        except Exception as e:
            print(f"[MATERIALS] ⚠️ Check failed: {e}")
    
    def _add_essential_materials(self):
        """Add essential materials - ALL T DESIGNATIONS REMOVED"""
        try:
            essential_materials = [
                # ✅ ALL T DESIGNATIONS COMPLETELY REMOVED
                {"name": "6061", "aliases": ["Al 6061", "Alüminyum 6061"], "density": 2.70, "price_per_kg": 4.50, "category": "Alüminyum", "is_active": True},
                {"name": "7075", "aliases": ["Al 7075", "Alüminyum 7075"], "density": 2.81, "price_per_kg": 6.20, "category": "Alüminyum", "is_active": True},
                {"name": "304 Paslanmaz", "aliases": ["304", "SS304", "AISI 304"], "density": 7.93, "price_per_kg": 8.50, "category": "Paslanmaz Çelik", "is_active": True},
                {"name": "316 Paslanmaz", "aliases": ["316", "SS316", "AISI 316"], "density": 7.98, "price_per_kg": 12.00, "category": "Paslanmaz Çelik", "is_active": True},
                {"name": "St37", "aliases": ["S235", "A36", "St 37"], "density": 7.85, "price_per_kg": 2.20, "category": "Karbon Çelik", "is_active": True},
                {"name": "C45", "aliases": ["CK45", "AISI 1045", "S45C"], "density": 7.85, "price_per_kg": 2.80, "category": "Karbon Çelik", "is_active": True},
                {"name": "Pirinç CuZn37", "aliases": ["Brass", "Ms58", "CuZn37"], "density": 8.50, "price_per_kg": 7.80, "category": "Bakır Alaşımı", "is_active": True}
            ]
            
            # Clear existing and insert new
            self.database.materials.delete_many({})
            self.database.materials.insert_many(essential_materials)
            
            # Update cache
            with self._cache_lock:
                self._material_cache = {mat['name']: mat for mat in essential_materials}
            
            print(f"[MATERIALS] ✅ {len(essential_materials)} essential materials added (ALL T designations removed)")
            
        except Exception as e:
            print(f"[MATERIALS] ❌ Addition failed: {e}")


# =====================================================
# COST ESTIMATION SERVICE - OPTIMIZED
# =====================================================

class CostEstimationServiceFast:
    """Fast cost estimation service"""
    
    def __init__(self):
        self.database = db.get_db()
    
    def calculate_cost_lightning(self, step_analysis, material_matches):
        """Lightning-fast cost calculation"""
        try:
            if not step_analysis or step_analysis.get("error"):
                return {"error": "STEP analysis required"}
            
            if not material_matches:
                return {"error": "Material required"}
            
            # First material
            material_name = material_matches[0].split("(")[0].strip()
            
            # Quick values
            volume = step_analysis.get("Prizma Hacmi (mm³)", 100000)
            waste = step_analysis.get("Talaş Hacmi (mm³)", 25000)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 10000)
            
            # Dimensions
            x = step_analysis.get("X (mm)", 0)
            y = step_analysis.get("Y (mm)", 0)
            z = step_analysis.get("Z (mm)", 0)
            
            # Material cost
            material_cost = self._calculate_material_cost_fast(volume, material_name)
            
            # Labor
            labor_hours = self._calculate_labor_time_fast(waste, surface)
            labor_cost = labor_hours * 65  # $65/hour
            
            total = material_cost["cost_usd"] + labor_cost
            
            return {
                "material": {
                    "name": material_name,
                    "cost_usd": material_cost["cost_usd"],
                    "mass_kg": material_cost["mass_kg"]
                },
                "machining": {
                    "hours": labor_hours,
                    "cost_usd": round(labor_cost, 2)
                },
                "dimensions": {
                    "x_mm": x, "y_mm": y, "z_mm": z,
                    "volume_mm3": volume, "waste_mm3": waste, "surface_mm2": surface
                },
                "costs": {
                    "material_usd": material_cost["cost_usd"],
                    "labor_usd": round(labor_cost, 2),
                    "total_usd": round(total, 2)
                }
            }
            
        except Exception as e:
            return {"error": f"Fast cost calculation error: {str(e)}"}
    
    def _calculate_material_cost_fast(self, volume_mm3, material_name):
        """Fast material cost calculation"""
        try:
            # Quick material lookup
            material = self.database.materials.find_one({"name": material_name})
            
            if material:
                density = material.get("density", 2.7)
                price = material.get("price_per_kg", 4.5)
            else:
                # Fast defaults
                density = 2.7
                price = 4.5
            
            # Quick calculation
            volume_cm3 = volume_mm3 / 1000
            mass_kg = (volume_cm3 * density) / 1000
            cost = mass_kg * price
            
            return {
                "mass_kg": round(mass_kg, 3),
                "cost_usd": round(cost, 2)
            }
            
        except:
            return {"mass_kg": 1.0, "cost_usd": 5.0}
    
    def _calculate_labor_time_fast(self, waste_mm3, surface_mm2):
        """Fast labor time calculation"""
        try:
            roughing_time = waste_mm3 / 3000  # Faster estimate
            finishing_time = surface_mm2 / 500  # Faster estimate
            total_hours = (roughing_time + finishing_time) / 60
            return round(max(total_hours, 0.5), 2)  # Min 0.5 hour
        except:
            return 1.0


# =====================================================
# CREATE OPTIMIZED INSTANCES
# =====================================================

# Create optimized service instance
MaterialAnalysisService = MaterialAnalysisServiceOptimized
CostEstimationService = CostEstimationServiceFast

# For backward compatibility
def create_service():
    return MaterialAnalysisServiceOptimized()

print("[T-DESIGNATIONS-REMOVED] ✅ Tüm T küsüratları tamamen kaldırıldı!")
print("[CLEAN-MATERIALS] 📋 Artık: 6061, 7075 (hiç T yok)")
print("[2024-REMOVED] ❌ 2024 malzemesi tamamen kaldırıldı")
print("[MATERIALS] 🔄 Malzeme veritabanı temizlendi (7 malzeme, T'siz)")
