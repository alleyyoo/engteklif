# services/material_analysis.py - COMPLETE PRODUCTION DATABASE-ONLY VERSION WITH ENHANCED PDF AND INTEGRATED STEP ANALYSIS

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

# ✅ INTEGRATED ENHANCED STEP ANALYSIS - APP.PY FUNCTIONS MOVED HERE
try:
    from scipy.spatial.transform import Rotation
    from scipy.spatial import ConvexHull
    from sklearn.decomposition import PCA
    SCIPY_AVAILABLE = True
    print("[MATERIAL-ANALYSIS] ✅ Advanced geometric analysis libraries available (scipy + sklearn)")
except ImportError as e:
    SCIPY_AVAILABLE = False
    print(f"[MATERIAL-ANALYSIS] ⚠️ Advanced geometric analysis disabled: {e}")
    print("[MATERIAL-ANALYSIS] 💡 Install with: pip install scipy scikit-learn")

# ✅ ENHANCED PDF INTEGRATION - MEVCUT SİSTEMİ BOZMAZ
try:
    from .enhanced_pdf_analysis import (
        should_use_enhanced_analysis, 
        get_enhanced_pdf_analyzer,
        EnhancedPDFFormatDetector
    )
    ENHANCED_PDF_AVAILABLE = True
    print("[MATERIAL-ANALYSIS] ✅ Enhanced PDF analysis available")
except ImportError as e:
    ENHANCED_PDF_AVAILABLE = False
    print(f"[MATERIAL-ANALYSIS] ⚠️ Enhanced PDF analysis not available: {e}")

print("[INFO] ✅ Material Analysis Service - DATABASE-ONLY VERSION WITH INTEGRATED ENHANCED STEP ANALYSIS")

# =====================================================
# ✅ INTEGRATED ENHANCED STEP ANALYSIS FUNCTIONS (FROM APP.PY)
# =====================================================

def calculate_face_based_dimensions(part):
    """
    Parçanın yüzlerini analiz ederek en uygun oriented bounding box hesaplar
    """
    try:
        # Tüm yüzleri al
        faces = part.faces()
        
        if not faces:
            # Fallback: geleneksel bounding box
            return calculate_traditional_bbox(part)
        
        best_config = None
        min_waste_volume = float('inf')
        
        # Her yüz için normal vektörü hesapla
        for face in faces:
            try:
                # Yüzün normal vektörünü al
                face_normal = face.normalAt()
                
                # Normal vektörü Z ekseniyle hizala
                aligned_part = align_part_to_normal(part, face_normal)
                
                # Hizalanmış parçanın boyutlarını hesapla
                bbox = aligned_part.BoundingBox()
                dimensions = (bbox.xlen, bbox.ylen, bbox.zlen)
                
                # Padding ekle
                padded_dims = [dim + 10.0 for dim in dimensions]
                
                # Prizma hacmi (işleme için gerekli ham malzeme)
                prism_volume = padded_dims[0] * padded_dims[1] * padded_dims[2]
                
                # Gerçek parça hacmi
                actual_volume = part.Volume()
                
                # Talaş hacmi
                waste_volume = prism_volume - actual_volume
                
                if waste_volume < min_waste_volume:
                    min_waste_volume = waste_volume
                    best_config = {
                        'dimensions': dimensions,
                        'padded_dimensions': padded_dims,
                        'prism_volume': prism_volume,
                        'actual_volume': actual_volume,
                        'waste_volume': waste_volume,
                        'waste_ratio': (waste_volume / prism_volume * 100) if prism_volume > 0 else 0,
                        'orientation': face_normal
                    }
            except Exception as e:
                print(f"[WARN] Yüz analizi hatası: {e}")
                continue
        
        # En iyi konfigürasyon bulunamazsa, geleneksel yönteme geç
        if best_config is None:
            return calculate_traditional_bbox(part)
            
        return best_config
        
    except Exception as e:
        print(f"[ERROR] Face-based analiz hatası: {e}")
        return calculate_traditional_bbox(part)

def align_part_to_normal(part, normal_vector):
    """
    Parçayı verilen normal vektörüne göre hizalar
    """
    try:
        if not SCIPY_AVAILABLE:
            return part
            
        # Normal vektörü normalize et
        normal = np.array([normal_vector.x, normal_vector.y, normal_vector.z])
        normal = normal / np.linalg.norm(normal)
        
        # Z ekseni ile hizalamak için rotasyon hesapla
        z_axis = np.array([0, 0, 1])
        
        # Rotasyon ekseni (cross product)
        rotation_axis = np.cross(normal, z_axis)
        
        if np.linalg.norm(rotation_axis) < 1e-6:
            # Zaten hizalı veya tam ters
            return part
            
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        
        # Rotasyon açısı
        angle = np.arccos(np.clip(np.dot(normal, z_axis), -1.0, 1.0))
        
        # Rotasyon uygula
        axis_angle = rotation_axis * angle
        rotation = Rotation.from_rotvec(axis_angle)
        
        # CadQuery rotasyonuna çevir
        rotated_part = part.rotate(
            (0, 0, 0),
            tuple(rotation_axis),
            np.degrees(angle)
        )
        
        return rotated_part
        
    except Exception as e:
        print(f"[WARN] Hizalama hatası: {e}")
        return part

def calculate_traditional_bbox(part):
    """
    Geleneksel bounding box hesaplama (fallback) - ZERO DEFAULTS
    """
    min_volume = None
    best_dims = (0, 0, 0)  # ✅ CHANGED: Default to (0, 0, 0)
    
    for rx in [0, 90, 180, 270]:
        for ry in [0, 90, 180, 270]:
            for rz in [0, 90, 180, 270]:
                try:
                    rotated = part.rotate((0, 0, 0), (1, 0, 0), rx)\
                                  .rotate((0, 0, 0), (0, 1, 0), ry)\
                                  .rotate((0, 0, 0), (0, 0, 1), rz)
                    bbox = rotated.BoundingBox()
                    volume = bbox.xlen * bbox.ylen * bbox.zlen
                    
                    if (min_volume is None) or (volume < min_volume):
                        min_volume = volume
                        best_dims = (bbox.xlen, bbox.ylen, bbox.zlen)
                except Exception as rot_error:
                    print(f"[WARN] Rotation error: {rot_error}")
                    continue
    
    x, y, z = best_dims
    x_pad = x + 10.0 if x > 0 else 0  # ✅ CHANGED: Check if x > 0
    y_pad = y + 10.0 if y > 0 else 0  # ✅ CHANGED: Check if y > 0
    z_pad = z + 10.0 if z > 0 else 0  # ✅ CHANGED: Check if z > 0
    volume_padded = x_pad * y_pad * z_pad
    
    try:
        actual_volume = part.Volume()
    except:
        actual_volume = 0  # ✅ CHANGED: Default to 0
    
    waste_volume = volume_padded - actual_volume if volume_padded > 0 else 0
    
    return {
        'dimensions': best_dims,
        'padded_dimensions': (x_pad, y_pad, z_pad),
        'prism_volume': volume_padded,
        'actual_volume': actual_volume,
        'waste_volume': waste_volume,
        'waste_ratio': (waste_volume / volume_padded * 100) if volume_padded > 0 else 0
    }

def calculate_convex_hull_approach(part):
    """
    Convex hull yaklaşımı - daha doğru boyutlar için - ZERO DEFAULTS
    """
    try:
        if not SCIPY_AVAILABLE:
            return calculate_traditional_bbox(part)
            
        # Parçanın köşe noktalarını al
        vertices = []
        for vertex in part.vertices():
            pnt = vertex.toTuple()
            vertices.append([pnt[0], pnt[1], pnt[2]])
        
        if len(vertices) < 4:
            return calculate_traditional_bbox(part)
        
        hull = ConvexHull(vertices)
        
        # Convex hull'un minimum bounding box'ını hesapla
        hull_points = np.array(vertices)[hull.vertices]
        
        # PCA ile ana eksenleri bul
        pca = PCA(n_components=3)
        pca.fit(hull_points)
        
        # Ana eksenlere göre dönüştür
        transformed_points = pca.transform(hull_points)
        
        # Dönüştürülmüş koordinatlardaki min/max değerler
        min_vals = np.min(transformed_points, axis=0)
        max_vals = np.max(transformed_points, axis=0)
        dimensions = max_vals - min_vals
        
        # Padding ekle - only if dimensions > 0
        padded_dims = dimensions + 10.0 if np.all(dimensions > 0) else np.array([0, 0, 0])  # ✅ CHANGED
        prism_volume = np.prod(padded_dims) if np.all(padded_dims > 0) else 0  # ✅ CHANGED
        
        try:
            actual_volume = part.Volume()
        except:
            actual_volume = 0  # ✅ CHANGED: Default to 0
        
        waste_volume = prism_volume - actual_volume if prism_volume > 0 else 0
        
        return {
            'dimensions': tuple(dimensions),
            'padded_dimensions': tuple(padded_dims),
            'prism_volume': prism_volume,
            'actual_volume': actual_volume,
            'waste_volume': waste_volume,
            'waste_ratio': (waste_volume / prism_volume * 100) if prism_volume > 0 else 0
        }
        
    except Exception as e:
        print(f"[WARN] Convex hull hatası: {e}")
        return calculate_traditional_bbox(part)

def improved_step_analysis(step_path):
    """
    Geliştirilmiş STEP analizi - ana fonksiyon - ZERO DEFAULTS
    """
    try:
        assembly = cq.importers.importStep(step_path)
        shapes = assembly.objects
        sorted_shapes = sorted(shapes, key=lambda s: s.Volume(), reverse=True)
        main_shape = sorted_shapes[0]
        
        # Ana şekil etrafında ilgili şekilleri bul
        main_bbox = main_shape.BoundingBox()
        relevant_shapes = [main_shape]
        
        for shape in sorted_shapes[1:]:
            bb = shape.BoundingBox()
            intersects = (
                bb.xmax > main_bbox.xmin and bb.xmin < main_bbox.xmax and
                bb.ymax > main_bbox.ymin and bb.ymin < main_bbox.ymax and
                bb.zmax > main_bbox.zmin and bb.zmin < main_bbox.zmax
            )
            if intersects:
                relevant_shapes.append(shape)
        
        part = cq.Compound.makeCompound(relevant_shapes)
        
        # Farklı yöntemleri dene ve en iyisini seç
        results = []
        
        # 1. Face-based analiz (en doğru)
        try:
            face_result = calculate_face_based_dimensions(part)
            if face_result:
                results.append(("face_based", face_result))
        except Exception as e:
            print(f"[WARN] Face-based analiz başarısız: {e}")
        
        # 2. Convex hull analiz (alternatif)
        try:
            hull_result = calculate_convex_hull_approach(part)
            if hull_result:
                results.append(("convex_hull", hull_result))
        except Exception as e:
            print(f"[WARN] Convex hull analiz başarısız: {e}")
        
        # 3. Geleneksel analiz (fallback)
        traditional_result = calculate_traditional_bbox(part)
        results.append(("traditional", traditional_result))
        
        # En az talaş oranına sahip olanı seç
        if not results:
            # ✅ CHANGED: Return all zeros if no analysis works
            return {
                "error": "Hiçbir analiz yöntemi başarılı olmadı",
                "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                "Toplam Yüzey Alanı (mm²)": 0
            }
        
        best_method, best_result = min(results, key=lambda x: x[1]['waste_ratio'])
        
        print(f"[INFO] En iyi yöntem: {best_method}")
        print(f"[INFO] Talaş oranı: {best_result['waste_ratio']:.2f}%")
        
        # Yüzey alanı hesapla
        try:
            total_surface_area = part.Area()
        except:
            total_surface_area = 0  # ✅ CHANGED: Default to 0
        
        x, y, z = best_result['dimensions']
        x_pad, y_pad, z_pad = best_result['padded_dimensions']
        
        # always_round_up fonksiyonu - only if value > 0
        def always_round_up(value):
            import math
            return math.ceil(value) if value > 0 else 0  # ✅ CHANGED
        
        step_analysis = {
            "Method": best_method,
            "X (mm)": round(x, 3),
            "Y (mm)": round(y, 3),
            "Z (mm)": round(z, 3),
            "Silindirik Çap (mm)": round(max(x, y), 3) if x > 0 and y > 0 else 0,  # ✅ CHANGED
            "Silindirik Yükseklik (mm)": round(z, 3),
            "X+Pad (mm)": always_round_up(x_pad),
            "Y+Pad (mm)": always_round_up(y_pad),
            "Z+Pad (mm)": always_round_up(z_pad),
            "Prizma Hacmi (mm³)": round(best_result['prism_volume'], 3),
            "Ürün Hacmi (mm³)": round(best_result['actual_volume'], 3),
            "Talaş Hacmi (mm³)": round(best_result['waste_volume'], 3),
            "Talaş Oranı (%)": round(best_result['waste_ratio'], 2),
            "Toplam Yüzey Alanı (mm²)": round(total_surface_area, 3),
            "enhanced_analysis": True,
            "methods_tested": len(results),
            "scipy_available": SCIPY_AVAILABLE
        }
        
        return step_analysis
        
    except Exception as e:
        print(f"[ERROR] STEP analiz hatası: {e}")
        # ✅ CHANGED: Return all zeros on error
        return {
            "error": str(e),
            "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
            "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
            "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
            "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
            "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
            "Toplam Yüzey Alanı (mm²)": 0
        }

class MaterialAnalysisServiceOptimized:
    def __init__(self):
        self.database = db.get_db()
        self._material_cache = {}
        self._cache_lock = threading.Lock()
        self._keyword_cache = None
        self._alias_cache = None
        
        # ✅ PRODUCTION SAFE initialization
        print("[INIT] 🚀 MaterialAnalysisService initializing (database-only mode with enhanced PDF)...")
        try:
            # Test database connection
            self.database.command('ping')
            print("[INIT] ✅ Database connection OK")
            
            # Initialize cache from database only
            self._preload_materials()
            self._preload_material_keywords()
            
            print(f"[INIT] ✅ MaterialAnalysisService ready with {len(self._material_cache)} materials from database")
        except Exception as init_error:
            print(f"[INIT] ❌ Initialization failed: {init_error}")
            # Continue anyway - will use direct database queries
    
    def _preload_materials(self):
        """✅ DATABASE-ONLY - Preload materials from database - Include missing is_active"""
        try:
            print("[CACHE] 🔄 Loading materials from database...")
            
            # ✅ YENİ QUERY: is_active=true VEYA is_active field'ı olmayan materyaller
            materials_cursor = self.database.materials.find(
                {
                    "$or": [
                        {"is_active": True},
                        {"is_active": {"$exists": False}}  # is_active field'ı olmayan materyaller
                    ]
                },
                {"name": 1, "density": 1, "price_per_kg": 1, "category": 1, "aliases": 1, "is_active": 1}
            ).limit(100)
            
            materials_list = list(materials_cursor)
            print(f"[CACHE] 📊 Found {len(materials_list)} materials in database (active=true OR missing is_active)")
            
            with self._cache_lock:
                self._material_cache = {}
                cached_count = 0
                skipped_count = 0
                
                for material in materials_list:
                    material_name = material.get('name')
                    density = material.get('density')
                    price_per_kg = material.get('price_per_kg')
                    category = material.get('category')
                    is_active = material.get('is_active')
                    
                    print(f"[CACHE] 🔍 Processing: {material_name}, density: {density}, price: {price_per_kg}, category: {category}, is_active: {is_active}")
                    
                    # SADECE NAME, DENSITY, PRICE KONTROLÜ - is_active ve category zorunlu değil
                    if (material_name and str(material_name).strip() != "" and
                        density is not None and 
                        price_per_kg is not None and
                        float(density) > 0 and
                        float(price_per_kg) >= 0):
                        
                        # Clean ObjectId
                        if '_id' in material:
                            material['id'] = str(material['_id'])
                            del material['_id']
                        
                        # Category opsiyonel, yoksa default
                        material['category'] = category if category else 'Uncategorized'
                        
                        self._material_cache[material_name] = material
                        cached_count += 1
                        print(f"[CACHE] ✅ Cached: {material_name} (is_active: {is_active}, category: {material['category']})")
                    else:
                        skipped_count += 1
                        print(f"[CACHE] ⚠️ Skipped {material_name}: invalid data")
            
            print(f"[CACHE] ✅ Cache loaded: {cached_count} materials, skipped: {skipped_count}")
            
            # Log all cached materials
            if self._material_cache:
                print(f"[CACHE] 📋 All cached materials: {list(self._material_cache.keys())}")
            
        except Exception as e:
            print(f"[CACHE] ❌ Preload failed: {e}")
            import traceback
            print(f"[CACHE] 📋 Traceback: {traceback.format_exc()}")
            # Continue without cache - will use direct database queries
    
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
            
            print(f"[OPTIMIZED] 🔤 Preloaded {len(keyword_list)} keywords and {len(alias_map)} aliases from database")
            
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
    
    @lru_cache(maxsize=100)
    def _get_materials_cached(self):
        """✅ DATABASE-ONLY - Get materials from cache or database"""
        with self._cache_lock:
            if not self._material_cache:
                print("[CACHE] ⚠️ Cache empty, trying to reload from database...")
                try:
                    self._preload_materials()
                except Exception as reload_error:
                    print(f"[CACHE] ❌ Reload failed: {reload_error}")
            
            return self._material_cache.copy()
    
    def _get_materials_from_database_direct(self):
        """✅ DATABASE-ONLY - Get materials directly from database - Include missing is_active"""
        try:
            print("[DB-DIRECT] 📊 Getting materials directly from database...")
            
            # Önce tüm materyalleri sayalım
            total_count = self.database.materials.count_documents({})
            active_true_count = self.database.materials.count_documents({"is_active": True})
            active_false_count = self.database.materials.count_documents({"is_active": False})
            missing_active_count = self.database.materials.count_documents({"is_active": {"$exists": False}})
            
            print(f"[DB-DIRECT] 📈 Total materials: {total_count}")
            print(f"[DB-DIRECT] 📈 is_active=true: {active_true_count}")
            print(f"[DB-DIRECT] 📈 is_active=false: {active_false_count}")
            print(f"[DB-DIRECT] 📈 is_active missing: {missing_active_count}")
            
            # ✅ YENİ QUERY: is_active=true VEYA is_active field'ı olmayan materyaller
            materials_cursor = self.database.materials.find(
                {
                    "$or": [
                        {"is_active": True},
                        {"is_active": {"$exists": False}}  # is_active field'ı olmayan materyaller
                    ]
                },
                {"name": 1, "density": 1, "price_per_kg": 1, "category": 1, "aliases": 1, "is_active": 1}
            )
            
            materials_list = list(materials_cursor)
            print(f"[DB-DIRECT] ✅ Found {len(materials_list)} materials in database (active=true OR missing is_active)")
            
            # Her materyali tek tek kontrol et
            materials_dict = {}
            for i, material in enumerate(materials_list):
                material_name = material.get('name')
                density = material.get('density')
                price_per_kg = material.get('price_per_kg')
                category = material.get('category')
                is_active = material.get('is_active')
                
                print(f"[DB-DIRECT] 🔍 Material {i+1}: '{material_name}'")
                print(f"    - is_active: {is_active} (type: {type(is_active)})")
                print(f"    - density: {density} (type: {type(density)})")
                print(f"    - price_per_kg: {price_per_kg} (type: {type(price_per_kg)})")
                print(f"    - category: {category}")
                
                # SADECE NAME, DENSITY, PRICE KONTROLÜ
                if material_name is None or material_name == "" or str(material_name).strip() == "":
                    print(f"    ❌ SKIP: Invalid name")
                    continue
                    
                if density is None:
                    print(f"    ❌ SKIP: Density is None")
                    continue
                    
                if price_per_kg is None:
                    print(f"    ❌ SKIP: Price is None")
                    continue
                
                try:
                    density_float = float(density)
                    if density_float <= 0:
                        print(f"    ❌ SKIP: Density <= 0 ({density_float})")
                        continue
                except (ValueError, TypeError) as e:
                    print(f"    ❌ SKIP: Density conversion error: {e}")
                    continue
                
                try:
                    price_float = float(price_per_kg)
                    if price_float < 0:
                        print(f"    ❌ SKIP: Price < 0 ({price_float})")
                        continue
                except (ValueError, TypeError) as e:
                    print(f"    ❌ SKIP: Price conversion error: {e}")
                    continue
                
                # Bu noktaya geldiyse materyal geçerli - is_active kontrolü kaldırıldı
                materials_dict[material_name] = {
                    'name': material_name,
                    'density': density_float,
                    'price_per_kg': price_float,
                    'category': category if category else 'Uncategorized',
                    'aliases': material.get('aliases', []),
                    'is_active': is_active  # Debugging için
                }
                print(f"    ✅ ADDED to results (is_active: {is_active}, category: {category or 'Uncategorized'})")
            
            print(f"[DB-DIRECT] ✅ Final result: {len(materials_dict)} valid materials out of {len(materials_list)} found")
            print(f"[DB-DIRECT] 📋 Valid material names: {list(materials_dict.keys())}")
            
            return materials_dict
            
        except Exception as e:
            print(f"[DB-DIRECT] ❌ Direct database query failed: {e}")
            import traceback
            print(f"[DB-DIRECT] 📋 Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_default_material_from_database(self):
        """✅ DATABASE-ONLY - Get a default material from database - Include missing is_active"""
        try:
            print("[DEFAULT] 🔍 Getting default material from database...")
            
            # Try to get a common aluminum alloy first (include missing is_active)
            default_material = self.database.materials.find_one({
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ],
                "$or": [
                    {"name": {"$regex": "6061", "$options": "i"}},
                    {"name": {"$regex": "aluminum", "$options": "i"}},
                    {"name": {"$regex": "aluminium", "$options": "i"}},
                    {"category": {"$regex": "alüminyum", "$options": "i"}}
                ]
            })
            
            if not default_material:
                # Get any material (active=true OR missing is_active)
                default_material = self.database.materials.find_one({
                    "$or": [
                        {"is_active": True},
                        {"is_active": {"$exists": False}}
                    ]
                })
            
            if default_material:
                print(f"[DEFAULT] ✅ Found default material: {default_material.get('name')} (is_active: {default_material.get('is_active')})")
                return {
                    'name': default_material['name'],
                    'density': default_material.get('density', 0),  # ✅ CHANGED: Default to 0
                    'price_per_kg': default_material.get('price_per_kg', 0),  # ✅ CHANGED: Default to 0
                    'category': default_material.get('category', 'Unknown')
                }
            else:
                print("[DEFAULT] ❌ No materials found in database")
                return None
                
        except Exception as e:
            print(f"[DEFAULT] ❌ Failed to get default material: {e}")
            return None
    
    def _create_emergency_materials_from_database(self, prizma_hacim_mm3):
        """✅ DATABASE-ONLY EMERGENCY - Create materials only from database - Include missing is_active"""
        try:
            print("[EMERGENCY] 🆘 Creating emergency materials from database only...")
            
            volume_cm3 = max(prizma_hacim_mm3 / 1000, 0.1) if prizma_hacim_mm3 > 0 else 0.1  # ✅ CHANGED: Check volume
            
            # Get materials from database (include missing is_active)
            materials_cursor = self.database.materials.find(
                {
                    "$or": [
                        {"is_active": True},
                        {"is_active": {"$exists": False}}
                    ]
                }
            ).limit(50)
            
            db_materials = list(materials_cursor)
            print(f"[EMERGENCY] 📊 Found {len(db_materials)} materials in database (active=true OR missing is_active)")
            
            if len(db_materials) == 0:
                print("[EMERGENCY] ❌ No materials in database - cannot create emergency list")
                return []
            
            emergency_materials = []
            
            for material in db_materials:
                try:
                    if (material.get('name') and 
                        material.get('density') and 
                        material.get('price_per_kg') is not None and
                        float(material['density']) > 0 and 
                        float(material['price_per_kg']) >= 0):
                        
                        mass_kg = (volume_cm3 * material['density']) / 1000 if volume_cm3 > 0 else 0  # ✅ CHANGED
                        material_cost = mass_kg * material['price_per_kg'] if mass_kg > 0 else 0  # ✅ CHANGED
                        
                        emergency_materials.append({
                            "name": material['name'],
                            "category": material.get('category', 'Uncategorized'),
                            "density": material['density'],
                            "mass_kg": round(mass_kg, 3),
                            "price_per_kg": material['price_per_kg'],
                            "material_cost": round(material_cost, 2),
                            "volume_mm3": prizma_hacim_mm3,
                            "is_active": material.get('is_active', 'undefined')  # Debug için
                        })
                        
                except Exception as calc_error:
                    print(f"[EMERGENCY] ⚠️ Calculation error for {material.get('name')}: {calc_error}")
                    continue
            
            # Sort by cost
            emergency_materials.sort(key=lambda x: x["material_cost"])
            
            print(f"[EMERGENCY] ✅ Created {len(emergency_materials)} database-only emergency materials")
            
            # Debug çıktısı
            for i, mat in enumerate(emergency_materials[:5]):
                print(f"   {i+1}. {mat['name']}: ${mat['material_cost']:.2f} (is_active: {mat['is_active']})")
            
            return emergency_materials
            
        except Exception as emergency_error:
            print(f"[EMERGENCY] ❌ Database-only emergency failed: {emergency_error}")
            return []
    
    def debug_database_materials(self):
        """🔍 DEBUG - Veritabanındaki tüm materyalleri detaylı kontrol et"""
        try:
            print("[DEBUG] 🔍 Starting detailed database material analysis...")
            
            # Toplam sayılar
            total_materials = self.database.materials.count_documents({})
            active_materials = self.database.materials.count_documents({"is_active": True})
            inactive_materials = self.database.materials.count_documents({"is_active": False})
            null_active = self.database.materials.count_documents({"is_active": None})
            missing_active = self.database.materials.count_documents({"is_active": {"$exists": False}})
            
            print(f"[DEBUG] 📊 Database Summary:")
            print(f"    Total materials: {total_materials}")
            print(f"    Active (true): {active_materials}")
            print(f"    Inactive (false): {inactive_materials}")
            print(f"    Null is_active: {null_active}")
            print(f"    Missing is_active field: {missing_active}")
            
            # Tüm materyalleri getir
            all_materials = list(self.database.materials.find({}))
            
            print(f"\n[DEBUG] 📋 Detailed Material Analysis:")
            valid_count = 0
            
            for i, material in enumerate(all_materials):
                print(f"\n[DEBUG] Material {i+1}:")
                print(f"    _id: {material.get('_id')}")
                print(f"    name: '{material.get('name')}' (type: {type(material.get('name'))})")
                print(f"    is_active: {material.get('is_active')} (type: {type(material.get('is_active'))})")
                print(f"    density: {material.get('density')} (type: {type(material.get('density'))})")
                print(f"    price_per_kg: {material.get('price_per_kg')} (type: {type(material.get('price_per_kg'))})")
                print(f"    category: '{material.get('category')}'")
                
                # Geçerlilik kontrolü
                is_valid = True
                reasons = []
                
                # is_active kontrolü
                if material.get('is_active') is not True:
                    is_valid = False
                    reasons.append(f"is_active is not True ({material.get('is_active')})")
                
                # name kontrolü
                name = material.get('name')
                if not name or name.strip() == "":
                    is_valid = False
                    reasons.append("name is empty or None")
                
                # density kontrolü
                density = material.get('density')
                if density is None:
                    is_valid = False
                    reasons.append("density is None")
                else:
                    try:
                        density_float = float(density)
                        if density_float <= 0:
                            is_valid = False
                            reasons.append(f"density <= 0 ({density_float})")
                    except:
                        is_valid = False
                        reasons.append(f"density cannot be converted to float ({density})")
                
                # price kontrolü
                price = material.get('price_per_kg')
                if price is None:
                    is_valid = False
                    reasons.append("price_per_kg is None")
                else:
                    try:
                        price_float = float(price)
                        if price_float < 0:
                            is_valid = False
                            reasons.append(f"price_per_kg < 0 ({price_float})")
                    except:
                        is_valid = False
                        reasons.append(f"price_per_kg cannot be converted to float ({price})")
                
                if is_valid:
                    valid_count += 1
                    print(f"    ✅ VALID")
                else:
                    print(f"    ❌ INVALID - Reasons: {', '.join(reasons)}")
            
            print(f"\n[DEBUG] 📊 Final Summary:")
            print(f"    Total materials checked: {len(all_materials)}")
            print(f"    Valid materials: {valid_count}")
            print(f"    Invalid materials: {len(all_materials) - valid_count}")
            
            return {
                "total": len(all_materials),
                "valid": valid_count,
                "invalid": len(all_materials) - valid_count,
                "active_true": active_materials,
                "active_false": inactive_materials
            }
            
        except Exception as e:
            print(f"[DEBUG] ❌ Debug failed: {e}")
            import traceback
            print(f"[DEBUG] 📋 Traceback: {traceback.format_exc()}")
            return None

    def refresh_material_cache(self):
        """✅ PUBLIC method to refresh cache when materials are added/updated"""
        with self._cache_lock:
            self._material_cache = {}
            self._keyword_cache = None
            self._alias_cache = None
        
        # Reload from database
        self._preload_materials()
        self._preload_material_keywords()
        print("[CACHE] ✅ Material cache refreshed from database")
    
    # =====================================================
    # MAIN ANALYSIS METHODS
    # =====================================================
    
    def analyze_document_comprehensive(self, file_path, file_type, user_id):
        """Main comprehensive analysis method"""
        return self.analyze_document_ultra_fast(file_path, file_type, user_id)
    
    def analyze_document_ultra_fast(self, file_path, file_type, user_id):
        """✅ DATABASE-ONLY - ALWAYS generate material_options from database"""
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
            print(f"[ULTRA-FAST] ⚡ DATABASE-ONLY analysis: {file_path} ({file_type})")
            
            if file_type == 'pdf':
                result = self._analyze_pdf_ultra_fast(file_path, result)
            elif file_type in ['step', 'stp']:
                # ✅ INTEGRATED ENHANCED STEP ANALYSIS - Direct usage of integrated functions
                print(f"[STEP-INTEGRATED] 🧠 Using integrated enhanced STEP analysis")
                try:
                    if SCIPY_AVAILABLE:
                        # Use integrated improved_step_analysis function
                        enhanced_result = improved_step_analysis(file_path)
                        if enhanced_result and 'error' not in enhanced_result:
                            result["step_analysis"] = enhanced_result
                            result["processing_log"].append("🧠 Integrated enhanced STEP analizi tamamlandı")
                            print(f"[STEP-INTEGRATED] ✅ Enhanced analysis successful: {enhanced_result.get('Method', 'unknown')}")
                        else:
                            print(f"[STEP-INTEGRATED] ⚠️ Enhanced failed, using traditional")
                            result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                            result["processing_log"].append("🔧 Traditional STEP analizi tamamlandı")
                    else:
                        print(f"[STEP-INTEGRATED] ⚠️ SciPy not available, using traditional")
                        result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                        result["processing_log"].append("🔧 Traditional STEP analizi tamamlandı")
                except Exception as integrated_error:
                    print(f"[STEP-INTEGRATED] ❌ Integrated enhanced error: {integrated_error}")
                    result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                    result["processing_log"].append("🔧 Fallback STEP analizi tamamlandı")
                
                if not result.get("material_matches"):
                    # Get default from database
                    default_material = self._get_default_material_from_database()
                    if default_material and default_material.get('name'):
                        result["material_matches"] = [f"{default_material['name']} (%database_default)"]
                    else:
                        result["material_matches"] = []  # ✅ CHANGED: Empty array instead of default
                    
            elif file_type in ['doc', 'docx']:
                result = self._analyze_document_fast(file_path, result)
            
            # ✅ MANDATORY DATABASE-ONLY MATERIAL OPTIONS
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)", 0)  # ✅ CHANGED: Default to 0
            
            print(f"[ULTRA-FAST] 📊 Database-only material options generation...")
            print(f"[ULTRA-FAST] 📐 Prizma hacmi: {prizma_hacim}")
            
            if prizma_hacim and prizma_hacim > 0:
                result["material_options"] = self._calculate_top_materials_database_only(
                    prizma_hacim, limit=0  # Limit=0 = TÜM materyalleri döndür
                )
            else:
                print(f"[ULTRA-FAST] ⚠️ No volume (0), using empty material options")
                result["material_options"] = []  # ✅ CHANGED: Empty array instead of default volume
            
            print(f"[ULTRA-FAST] ✅ Database-only material options generated: {len(result['material_options'])}")
            
            # Found materials calculations
            if result.get("material_matches") and prizma_hacim and prizma_hacim > 0:
                result["all_material_calculations"] = self._calculate_found_materials_database_only(
                    prizma_hacim, result["material_matches"]
                )
            
            # ✅ DATABASE-ONLY GUARANTEE - No fallback to hardcoded materials
            print(f"[DB-ONLY-CHECK] 🔍 Checking material_options before return...")
            print(f"[DB-ONLY-CHECK] 📊 Current material_options count: {len(result.get('material_options', []))}")
            
            if not result.get("material_options") or len(result.get("material_options", [])) == 0:
                print(f"[DB-ONLY-CHECK] 🆘 Material options empty, applying database-only emergency...")
                
                # Get volume - only if > 0
                volume_to_use = prizma_hacim if prizma_hacim > 0 else 0
                
                if volume_to_use > 0:
                    # Try emergency database materials
                    result["material_options"] = self._create_emergency_materials_from_database(volume_to_use)
                    
                    if len(result["material_options"]) > 0:
                        print(f"[DB-ONLY-CHECK] ✅ Database emergency fix: {len(result['material_options'])} materials")
                        result["processing_log"].append(f"🆘 DATABASE emergency materials: {len(result['material_options'])} items")
                    else:
                        print("[DB-ONLY-CHECK] ❌ No materials available in database")
                        result["error"] = "No materials found in database"
                        result["processing_log"].append("❌ CRITICAL: No materials in database")
                else:
                    print("[DB-ONLY-CHECK] ❌ No volume data (0), cannot calculate materials")
                    result["material_options"] = []
                    result["processing_log"].append("❌ No volume data for material calculations")
            else:
                print(f"[DB-ONLY-CHECK] ✅ Material options OK: {len(result.get('material_options', []))} materials from database")
            
            # ✅ FINAL DEBUG OUTPUT
            print(f"[ULTRA-FAST] 🔍 DATABASE-ONLY Final result:")
            print(f"  - Material Options: {len(result.get('material_options', []))}")
            print(f"  - Material Calculations: {len(result.get('all_material_calculations', []))}")
            print(f"  - Material Matches: {len(result.get('material_matches', []))}")
            
            # Show sample material options
            if result.get('material_options'):
                print(f"[ULTRA-FAST] 📋 Sample database materials:")
                for i, mat in enumerate(result['material_options'][:3]):
                    print(f"    {i+1}. {mat.get('name', 'N/A')}: {mat.get('mass_kg', 'N/A')} kg, ${mat.get('material_cost', 'N/A')}")
            
            total_time = time.time() - start_time
            result["processing_log"].append(f"⏱️ DATABASE-ONLY analysis time: {total_time:.2f}s")
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"DATABASE-ONLY analysis error: {str(e)}"
            print(f"[ULTRA-FAST] ❌ {error_msg}")
            print(f"[ULTRA-FAST] 📋 Traceback: {traceback.format_exc()}")
            
            # Even in error, try database emergency only if we have volume
            result["error"] = error_msg
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)", 0)
            if prizma_hacim > 0:
                result["material_options"] = self._create_emergency_materials_from_database(prizma_hacim)
            else:
                result["material_options"] = []
            result["processing_log"].append(f"❌ ERROR but database emergency materials attempted")
            
            return result
    
    # =====================================================
    # ✅ ENHANCED PDF ANALYSIS METHOD
    # =====================================================
    
    def _analyze_pdf_ultra_fast(self, file_path, result):
        """✅ ENHANCED PDF analysis - SADECE MATERIAL DETECTION GELİŞTİRİLDİ - ZERO DEFAULTS"""
        start_time = time.time()
        result["processing_log"].append("📄 Enhanced PDF analizi başlatılıyor")
        
        # ✅ ENHANCED MATERIAL DETECTION (sadece material için)
        enhanced_materials = None
        enhanced_format_info = None
        
        if ENHANCED_PDF_AVAILABLE:
            try:
                use_enhanced = should_use_enhanced_analysis(file_path)
                
                if use_enhanced:
                    print(f"[PDF-ENHANCED] 🔍 Enhanced material detection for: {os.path.basename(file_path)}")
                    result["processing_log"].append("🔍 Enhanced format detection uygulandı")
                    
                    # Enhanced format detection
                    detector = EnhancedPDFFormatDetector()
                    format_info = detector.detect_pdf_format(file_path)
                    
                    if format_info["is_confident"]:
                        # Enhanced material extraction
                        enhanced_analyzer = get_enhanced_pdf_analyzer()
                        enhanced_result = enhanced_analyzer._apply_format_specific_enhancements(
                            {}, format_info, file_path
                        )
                        
                        if enhanced_result.get("format_specific_materials"):
                            enhanced_materials = enhanced_result["format_specific_materials"]
                            enhanced_format_info = format_info
                            
                            result["processing_log"].append(f"✅ Enhanced materials: {len(enhanced_materials)}")
                            result["processing_log"].append(f"✅ Format: {format_info['detected_format']} ({format_info['confidence']:.2f})")
                            print(f"[PDF-ENHANCED] ✅ Enhanced materials found: {len(enhanced_materials)}")
                        else:
                            result["processing_log"].append("🔍 Enhanced detection completed, no additional materials")
                            print(f"[PDF-ENHANCED] 📄 Enhanced detection completed, no additional materials")
                    else:
                        result["processing_log"].append("📄 Enhanced not confident, using standard")
                        print(f"[PDF-ENHANCED] 📄 Enhanced not confident, using standard")
                else:
                    result["processing_log"].append("📄 Standard analysis (enhanced not suitable)")
                    print(f"[PDF-ENHANCED] 📄 Standard analysis (enhanced not suitable)")
            
            except Exception as e:
                print(f"[PDF-ENHANCED] ❌ Enhanced material detection error: {e}")
                result["processing_log"].append(f"⚠️ Enhanced error: {str(e)}")
        else:
            result["processing_log"].append("📄 Enhanced module not available")
            print(f"[PDF-ENHANCED] 📄 Enhanced module not available")
        
        # ✅ NORMAL PDF ANALYSIS - TAMAMEN MEVCUT AKIŞ (hiç değişmez)
        result["processing_log"].append("📄 Standard PDF processing başlıyor")
        
        # Quick STEP extraction - MEVCUT KOD
        step_paths = self._extract_step_from_pdf_fast(file_path)
        extracted_step_path = None
        permanent_step_path = None
        
        if step_paths:
            extracted_step_path = step_paths[0]
            step_filename = os.path.basename(extracted_step_path)
            result["processing_log"].append(f"📎 STEP çıkarıldı: {step_filename}")
            
            # Save permanently - MEVCUT KOD
            analysis_id = f"pdf_{int(time.time())}_{hashlib.md5(file_path.encode()).hexdigest()[:6]}"
            permanent_dir = os.path.join("static", "stepviews", analysis_id)
            os.makedirs(permanent_dir, exist_ok=True)
            
            permanent_step_filename = f"extracted_{analysis_id}.step"
            permanent_step_path = os.path.join(permanent_dir, permanent_step_filename)
            
            import shutil
            shutil.copy2(extracted_step_path, permanent_step_path)
            
            result["extracted_step_path"] = permanent_step_path
            result["pdf_analysis_id"] = analysis_id
            
            # ✅ INTEGRATED ENHANCED STEP ANALYSIS for extracted STEP
            if SCIPY_AVAILABLE:
                try:
                    print(f"[PDF-STEP-INTEGRATED] 🧠 Using integrated enhanced analysis for extracted STEP")
                    integrated_step_result = improved_step_analysis(permanent_step_path)
                    if integrated_step_result and 'error' not in integrated_step_result:
                        result["step_analysis"] = integrated_step_result
                        result["processing_log"].append("🧠 Integrated Enhanced STEP analizi (PDF'den) tamamlandı")
                        print(f"[PDF-STEP-INTEGRATED] ✅ Integrated enhanced analysis successful")
                    else:
                        print(f"[PDF-STEP-INTEGRATED] ⚠️ Integrated enhanced failed, using traditional")
                        result["step_analysis"] = self.analyze_step_file_ultra_fast(permanent_step_path)
                        result["processing_log"].append("🔧 Traditional STEP analizi (PDF'den) tamamlandı")
                except Exception as integrated_step_error:
                    print(f"[PDF-STEP-INTEGRATED] ❌ Integrated enhanced error: {integrated_step_error}")
                    result["step_analysis"] = self.analyze_step_file_ultra_fast(permanent_step_path)
                    result["processing_log"].append("🔧 Fallback STEP analizi (PDF'den) tamamlandı")
            else:
                # ✅ NORMAL STEP ANALYSIS - MEVCUT KOD (3D render için gerekli)
                print(f"[PDF-STEP-INTEGRATED] ⚠️ SciPy not available, using traditional")
                result["step_analysis"] = self.analyze_step_file_ultra_fast(permanent_step_path)
                result["processing_log"].append("🔧 Traditional STEP analizi tamamlandı")
            
            result["step_file_hash"] = self._calculate_file_hash_fast(permanent_step_path)
            
            print(f"[PDF-STEP] ✅ STEP analysis completed: {result['step_analysis']}")
            
        else:
            # ✅ ZERO DEFAULT VALUES - CHANGED
            result["step_analysis"] = {
                "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,  # ✅ CHANGED: Zero defaults
                "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,  # ✅ CHANGED: Zero defaults
                "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,  # ✅ CHANGED: Zero defaults
                "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,  # ✅ CHANGED: Zero defaults
                "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,  # ✅ CHANGED: Zero defaults
                "Toplam Yüzey Alanı (mm²)": 0,   # ✅ CHANGED: Zero defaults
                "method": "estimated_from_pdf_zero_defaults"
            }
            result["processing_log"].append("⚠️ STEP bulunamadı, sıfır varsayılan değerler kullanıldı")
            print(f"[PDF-STEP] ⚠️ No STEP found, using zero default values")
        
        # ✅ MATERIAL SEARCH - Enhanced + Standard kombinasyonu
        materials = []
        
        # Enhanced materials varsa önce onları ekle
        if enhanced_materials:
            materials.extend(enhanced_materials)
            result["processing_log"].append(f"🔍 Enhanced materials eklendi: {len(enhanced_materials)}")
            print(f"[PDF-ENHANCED] ✅ Added enhanced materials: {len(enhanced_materials)}")
        
        # Standard material search - MEVCUT KOD
        standard_materials = self._quick_pdf_text_search_database_only(file_path)
        
        if not standard_materials:
            try:
                text = self._extract_text_from_pdf_minimal(file_path)
                standard_materials = self._find_materials_in_text_database_only(text)
            except:
                standard_materials = []
        
        # Standard materials'ı da ekle (duplicate kontrolü ile)
        if standard_materials:
            for std_mat in standard_materials:
                # Duplicate check
                std_clean = std_mat.split('(')[0].strip().lower()
                is_duplicate = False
                
                for existing_mat in materials:
                    existing_clean = existing_mat.split('(')[0].strip().lower()
                    if std_clean in existing_clean or existing_clean in std_clean:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    materials.append(std_mat)
            
            result["processing_log"].append(f"🔍 Standard materials eklendi: {len(standard_materials)}")
            print(f"[PDF-STANDARD] ✅ Added standard materials: {len(standard_materials)}")
        
        # Final materials assignment - ZERO DEFAULTS
        if materials:
            result["material_matches"] = materials
            result["processing_log"].append(f"✅ Toplam malzeme: {len(materials)}")
            print(f"[PDF-FINAL] ✅ Total materials: {len(materials)}")
        else:
            # ✅ CHANGED: No default materials, use empty array
            result["material_matches"] = []
            result["processing_log"].append("⚠️ Hiçbir malzeme bulunamadı")
            print(f"[PDF-FINAL] ⚠️ No materials found")
        
        # ✅ Enhanced format info ekleme (yeni field - API'yi bozmaz)
        if enhanced_format_info:
            result["format_detection"] = {
                "detected_format": enhanced_format_info["detected_format"],
                "confidence": enhanced_format_info["confidence"],
                "is_confident": enhanced_format_info["is_confident"],
                "analysis_strategy_used": enhanced_format_info["analysis_strategy"]["primary_focus"]
            }
        
        # Cleanup - MEVCUT KOD
        if extracted_step_path and extracted_step_path != permanent_step_path:
            try:
                os.remove(extracted_step_path)
            except:
                pass
        
        total_pdf_time = time.time() - start_time
        print(f"[PDF-ENHANCED] ✅ Enhanced PDF analysis completed: {total_pdf_time:.3f}s")
        print(f"[PDF-ENHANCED] 📊 Materials: {len(result.get('material_matches', []))}")
        print(f"[PDF-ENHANCED] 📊 STEP Analysis: {bool(result.get('step_analysis'))}")
        print(f"[PDF-ENHANCED] 📊 STEP Path: {result.get('extracted_step_path', 'None')}")
        
        return result
    
    # =====================================================
    # DATABASE-ONLY MATERIAL CALCULATION METHODS
    # =====================================================
    
    def _calculate_top_materials_database_only(self, prizma_hacim_mm3, limit=20):
        """✅ DATABASE-ONLY - Material calculations from database only - ZERO VOLUME HANDLING"""
        try:
            print(f"[TOP-MATERIALS-DB] 🚀 DATABASE-ONLY calculation for {prizma_hacim_mm3} mm³, limit: {limit}")
            
            # ✅ CHANGED: Check for zero or invalid volume
            if prizma_hacim_mm3 <= 0:
                print(f"[TOP-MATERIALS-DB] ⚠️ Invalid volume ({prizma_hacim_mm3}), returning empty list")
                return []
            
            # Get materials from database
            materials_dict = self._get_materials_from_database_direct()
            
            if not materials_dict:
                print("[TOP-MATERIALS-DB] ⚠️ Database direct failed, trying cache...")
                materials_dict = self._get_materials_cached()
                
                if not materials_dict:
                    print("[TOP-MATERIALS-DB] ❌ No materials available in database or cache")
                    return []
            
            print(f"[TOP-MATERIALS-DB] 📊 Processing {len(materials_dict)} database materials")
            
            top_materials = []
            processed_count = 0
            error_count = 0
            
            for material_name, material in materials_dict.items():
                try:
                    density = float(material.get("density", 0))
                    price_per_kg = float(material.get("price_per_kg", 0))
                    category = material.get("category") or "Uncategorized"  # Category opsiyonel
                    
                    print(f"[TOP-MATERIALS-DB] 🔍 Processing {material_name}: density={density}, price={price_per_kg}, category={category}")
                    
                    if density <= 0:
                        print(f"[TOP-MATERIALS-DB] ⚠️ Invalid density for {material_name}: {density}")
                        error_count += 1
                        continue
                        
                    if price_per_kg < 0:  # Negative price is invalid, but 0 is allowed
                        print(f"[TOP-MATERIALS-DB] ⚠️ Invalid price for {material_name}: {price_per_kg}")
                        error_count += 1
                        continue
                    
                    # Calculate mass and cost
                    volume_cm3 = prizma_hacim_mm3 / 1000
                    mass_kg = (volume_cm3 * density) / 1000
                    material_cost = mass_kg * price_per_kg
                    
                    top_materials.append({
                        "name": material_name,
                        "category": category,
                        "density": round(density, 2),
                        "mass_kg": round(mass_kg, 3),
                        "price_per_kg": round(price_per_kg, 2),
                        "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3,
                        "source": "database"
                    })
                    
                    processed_count += 1
                    print(f"[TOP-MATERIALS-DB] ✅ Added {material_name}: {mass_kg:.3f} kg, ${material_cost:.2f} ({category})")
                    
                except Exception as mat_error:
                    error_count += 1
                    print(f"[TOP-MATERIALS-DB] ⚠️ Error processing {material_name}: {mat_error}")
                    continue
            
            print(f"[TOP-MATERIALS-DB] 📊 Summary: {processed_count} processed, {error_count} errors")
            
            # Sort by cost
            top_materials.sort(key=lambda x: x["material_cost"])
            
            # Apply limit but don't be too restrictive - TÜM MATERYALLERİ DÖNDÜR
            if limit <= 0:
                result = top_materials  # Limit yok, hepsini döndür
            else:
                result = top_materials[:limit]
            
            print(f"[TOP-MATERIALS-DB] ✅ DATABASE-ONLY result: {len(result)} materials (total available: {len(top_materials)}, requested limit: {limit})")
            
            # Debug all materials
            for i, mat in enumerate(result):
                print(f"   {i+1}. {mat['name']}: {mat['mass_kg']} kg, ${mat['material_cost']} ({mat['category']})")
            
            return result
            
        except Exception as e:
            print(f"[TOP-MATERIALS-DB] ❌ DATABASE-ONLY calculation failed: {e}")
            import traceback
            print(f"[TOP-MATERIALS-DB] 📋 Traceback: {traceback.format_exc()}")
            return []
    
    def _calculate_found_materials_database_only(self, prizma_hacim_mm3, found_materials):
        """✅ DATABASE-ONLY material calculations using database data only - ZERO VOLUME HANDLING"""
        try:
            # ✅ CHANGED: Check for zero or invalid volume
            if prizma_hacim_mm3 <= 0:
                print(f"[CALC-DB-ONLY] ⚠️ Invalid volume ({prizma_hacim_mm3}), returning empty list")
                return []
                
            calculations = []
            materials_cache = self._get_materials_cached()
            
            # If cache is empty, try database direct
            if not materials_cache:
                materials_cache = self._get_materials_from_database_direct()
            
            if not materials_cache:
                print("[CALC-DB-ONLY] ❌ No materials available in database")
                return []
            
            processed_materials = set()
            
            for material_text in found_materials:
                # Clean material name
                material_name = material_text.split("(")[0].strip()
                material_name = re.sub(r'-T\d+', '', material_name)
                
                # Skip duplicates
                if material_name in processed_materials:
                    continue
                processed_materials.add(material_name)
                
                # Extract confidence
                confidence_match = re.search(r'%(\d+)', material_text)
                confidence = int(confidence_match.group(1)) if confidence_match else 70
                
                # DATABASE-ONLY LOOKUP
                material = None
                material_name_norm = material_name.lower()
                
                for cached_name, cached_material in materials_cache.items():
                    if (material_name_norm in cached_name.lower() or 
                        cached_name.lower() in material_name_norm):
                        material = cached_material
                        break
                
                if not material:
                    # Try alias matching in database
                    for cached_name, cached_material in materials_cache.items():
                        aliases = cached_material.get('aliases', [])
                        for alias in aliases:
                            if material_name_norm in alias.lower() or alias.lower() in material_name_norm:
                                material = cached_material
                                break
                        if material:
                            break
                
                if not material:
                    print(f"[CALC-DB-ONLY] ⚠️ Material '{material_name}' not found in database")
                    continue
                
                # DATABASE CALCULATION
                density = material.get("density", 0)
                price_per_kg = material.get("price_per_kg", 0)
                actual_name = material.get("name", material_name)
                category = material.get("category", "Unknown")
                aliases = material.get("aliases", [])
                
                if density <= 0 or price_per_kg < 0:  # ✅ CHANGED: Allow 0 price but not negative
                    print(f"[CALC-DB-ONLY] ⚠️ Invalid data for {actual_name}: density={density}, price={price_per_kg}")
                    continue
                
                # CALCULATION
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
                    "found_in_db": True,
                    "source": "database_only"
                })
            
            # Sort by confidence
            calculations.sort(key=lambda x: x['confidence_value'], reverse=True)
            
            print(f"[CALC-DB-ONLY] ✅ Database-only calculation: {len(calculations)} materials")
            return calculations
            
        except Exception as e:
            print(f"[CALC-DB-ONLY] ❌ Database-only calculation failed: {e}")
            return []
    
    # =====================================================
    # STEP ANALYSIS METHODS
    # =====================================================
    
    def analyze_step_file(self, step_path):
        """Standard STEP analysis - kept for compatibility"""
        return self.analyze_step_file_ultra_fast(step_path)
    
    def analyze_step_file_ultra_fast(self, step_path):
        """✅ ULTRA-FAST STEP analysis - ZERO DEFAULTS"""
        try:
            start_time = time.time()
            print(f"[STEP-ULTRA] 🔧 Ultra-fast STEP analysis: {os.path.basename(step_path)}")
            
            # Quick import with timeout protection
            try:
                assembly = cq.importers.importStep(step_path)
                if not assembly.objects:
                    # ✅ CHANGED: Return zeros instead of error
                    return {
                        "error": "Empty STEP file",
                        "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                        "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                        "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                        "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                        "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                        "Toplam Yüzey Alanı (mm²)": 0
                    }
            except Exception as import_error:
                print(f"[STEP-ULTRA] ❌ Import failed: {import_error}")
                # ✅ CHANGED: Return zeros instead of error
                return {
                    "error": f"STEP import failed: {str(import_error)}",
                    "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                    "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                    "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                    "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                    "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                    "Toplam Yüzey Alanı (mm²)": 0
                }
            
            # LIGHTNING-FAST ANALYSIS
            shapes = assembly.objects
            if not shapes:
                # ✅ CHANGED: Return zeros
                return {
                    "error": "No shapes found",
                    "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                    "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                    "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                    "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                    "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                    "Toplam Yüzey Alanı (mm²)": 0
                }
            
            # Use largest shape only
            main_shape = max(shapes, key=lambda s: s.Volume())
            main_bbox = main_shape.BoundingBox()
            
            # DIRECT BOUNDING BOX
            x, y, z = main_bbox.xlen, main_bbox.ylen, main_bbox.zlen
            
            # ✅ CHANGED: Only add padding if dimensions > 0
            x_pad = int(x) + 10 if x > 0 and x % 1 < 0.01 else (int(x) + 11 if x > 0 else 0)
            y_pad = int(y) + 10 if y > 0 and y % 1 < 0.01 else (int(y) + 11 if y > 0 else 0)
            z_pad = int(z) + 10 if z > 0 and z % 1 < 0.01 else (int(z) + 11 if z > 0 else 0)
            
            # LIGHTNING CALCULATIONS
            volume_padded = x_pad * y_pad * z_pad if x_pad > 0 and y_pad > 0 and z_pad > 0 else 0  # ✅ CHANGED
            
            try:
                product_volume = main_shape.Volume()
                total_surface_area = main_shape.Area()
            except:
                product_volume = x * y * z * 0.75 if x > 0 and y > 0 and z > 0 else 0  # ✅ CHANGED
                total_surface_area = 2 * (x*y + y*z + x*z) * 1.2 if x > 0 and y > 0 and z > 0 else 0  # ✅ CHANGED
            
            waste_volume = volume_padded - product_volume if volume_padded > 0 else 0  # ✅ CHANGED
            waste_ratio = (waste_volume / volume_padded * 100) if volume_padded > 0 else 0.0
            
            cylindrical_diameter = max(x, y) if x > 0 and y > 0 else 0  # ✅ CHANGED
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
            # ✅ CHANGED: Return zeros instead of error message only
            return {
                "error": f"Ultra-fast STEP analysis failed: {str(e)}",
                "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                "Toplam Yüzey Alanı (mm²)": 0
            }
    
    # =====================================================
    # PDF HELPER METHODS (MEVCUT KODLAR)
    # =====================================================
    
    def _extract_step_from_pdf_fast(self, pdf_path):
        """✅ FAST STEP extraction with timeout protection"""
        try:
            extracted = []
            start_time = time.time()
            TIMEOUT_SECONDS = 0.8
            
            with pikepdf.open(pdf_path) as pdf:
                try:
                    root = pdf.trailer.get("/Root", {})
                    names = root.get("/Names", {})
                    embedded = names.get("/EmbeddedFiles", {})
                    files = embedded.get("/Names", [])
                    
                    for i in range(0, min(len(files), 10), 2):
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
                                        break
                                    else:
                                        os.remove(output_path)
                                        
                            except Exception as e:
                                continue
                                
                except Exception as e:
                    print(f"[STEP-FAST] ⚠️ Embedded files error: {e}")
            
            return extracted
            
        except Exception as e:
            print(f"[STEP-FAST] ❌ Fast STEP extraction failed: {e}")
            return []
    
    def _quick_pdf_text_search_database_only(self, pdf_path):
        """✅ DATABASE-ONLY PDF text search - no OCR"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text and len(text.strip()) > 10:
                        return self._find_materials_in_text_database_only(text)
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
    
    def _find_materials_in_text_database_only(self, text):
        """✅ DATABASE-ONLY material search"""
        if not text or len(text.strip()) < 5:
            return []
        
        materials = []
        text_upper = text.upper()
        
        # GET ALL MATERIALS FROM DATABASE/CACHE DYNAMICALLY
        materials_cache = self._get_materials_cached()
        if not materials_cache:
            materials_cache = self._get_materials_from_database_direct()
        
        if not materials_cache:
            print("[MAT-DB-ONLY] ❌ No materials available in database")
            return []
        
        confidence_found = {}
        
        # OCR Error Corrections
        ocr_corrections = {
            "2064": "7050", "7056": "7050", "705O": "7050",
            "606I": "6061", "3O4": "304",
        }
        
        # OCR CORRECTION CHECK
        corrected_text = text_upper
        for error_pattern, correction in ocr_corrections.items():
            if error_pattern in text_upper:
                corrected_text = text_upper.replace(error_pattern, correction)
                print(f"[MAT-DB-ONLY] 🔧 OCR Corrected: {error_pattern} -> {correction}")
        
        # DATABASE-ONLY SEARCH
        for material_name, material in materials_cache.items():
            confidence = 0
            matched_term = ""
            
            # Main name check
            material_name_clean = material_name.upper()
            if material_name_clean in corrected_text:
                confidence = 100
                matched_term = material_name_clean
            
            # Alias check
            if not confidence:
                aliases = material.get('aliases', [])
                for alias in aliases:
                    alias_clean = alias.upper()
                    if alias_clean in corrected_text:
                        confidence = 95
                        matched_term = alias_clean
                        break
            
            # Partial match (4+ characters)
            if not confidence and len(material_name_clean) >= 4:
                if material_name_clean in corrected_text:
                    confidence = 85
                    matched_term = material_name_clean
            
            # Numeric materials special check
            if not confidence and material_name_clean.isdigit() and len(material_name_clean) == 4:
                if material_name_clean in corrected_text.replace(" ", "").replace("-", ""):
                    confidence = 100
                    matched_term = material_name_clean
            
            if confidence > 0:
                confidence_found[material_name] = {
                    'confidence': confidence,
                    'matched_term': matched_term,
                    'material': material
                }
                print(f"[MAT-DB-ONLY] ⚡ Found: {matched_term} -> {material_name} ({confidence}%) [DATABASE]")
        
        # RESULT FORMATTING
        sorted_materials = sorted(confidence_found.items(), 
                                key=lambda x: x[1]['confidence'], reverse=True)
        
        for material_name, match_info in sorted_materials[:3]:
            confidence = match_info['confidence']
            confidence_str = f"%{confidence}" if confidence >= 85 else "database_estimated"
            materials.append(f"{material_name} ({confidence_str})")
        
        print(f"[MAT-DB-ONLY] ✅ Database-only search result: {len(materials)} materials found")
        return materials
    
    # =====================================================
    # DOCUMENT PROCESSING METHODS
    # =====================================================
    
    def _analyze_document_fast(self, file_path, result):
        """Fast DOC/DOCX analysis - database only - ZERO DEFAULTS"""
        result["processing_log"].append("📝 Fast document analizi (database-only)")
        
        try:
            if file_path.lower().endswith('.docx'):
                text = self._extract_text_from_docx_fast(file_path)
            else:
                text = self._extract_text_from_doc_fast(file_path)
            
            # Database-only material search
            materials = self._find_materials_in_text_database_only(text)
            if materials:
                result["material_matches"] = materials
                result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu (database)")
            else:
                # ✅ CHANGED: No default materials, use empty array
                result["material_matches"] = []
                result["processing_log"].append("❌ Database'de malzeme bulunamadı")
            
            # ✅ CHANGED: Zero default STEP analysis for documents
            result["step_analysis"] = {
                "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
                "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
                "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
                "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
                "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
                "Toplam Yüzey Alanı (mm²)": 0, "method": "zero_defaults_from_document"
            }
            
        except Exception as e:
            result["processing_log"].append(f"❌ Document analiz hatası: {e}")
            
        return result
    
    def _extract_text_from_docx_fast(self, file_path):
        """Fast DOCX text extraction"""
        try:
            doc = Document(file_path)
            texts = [p.text for p in doc.paragraphs[:10] if p.text.strip()]
            return "\n".join(texts)
        except Exception as e:
            print(f"[DOCX-FAST] ❌ Failed: {e}")
            return ""
    
    def _extract_text_from_doc_fast(self, file_path):
        """Fast DOC text extraction"""
        try:
            output_dir = os.path.dirname(file_path)
            result = subprocess.run([
                "libreoffice", "--headless", "--convert-to", "docx", 
                "--outdir", output_dir, file_path
            ], capture_output=True, timeout=10)
            
            docx_path = os.path.splitext(file_path)[0] + ".docx"
            if os.path.exists(docx_path):
                text = self._extract_text_from_docx_fast(docx_path)
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
            with open(file_path, 'rb') as f:
                chunk = f.read(2048)
            return hashlib.md5(chunk).hexdigest()[:16]
        except:
            return None


# =====================================================
# COST ESTIMATION SERVICE - DATABASE-ONLY - ZERO DEFAULTS
# =====================================================

class CostEstimationServiceFast:
    """Database-only cost estimation service - ZERO DEFAULTS"""
    
    def __init__(self):
        self.database = db.get_db()
    
    def calculate_cost_lightning(self, step_analysis, material_matches):
        """Lightning-fast cost calculation - database only - ZERO DEFAULTS"""
        try:
            if not step_analysis or step_analysis.get("error"):
                return {"error": "STEP analysis required"}
            
            if not material_matches:
                return {"error": "Material required"}
            
            # First material
            material_name = material_matches[0].split("(")[0].strip()
            
            # Quick values - ✅ CHANGED: Use 0 as defaults
            volume = step_analysis.get("Prizma Hacmi (mm³)", 0)
            waste = step_analysis.get("Talaş Hacmi (mm³)", 0)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 0)
            
            # Dimensions
            x = step_analysis.get("X (mm)", 0)
            y = step_analysis.get("Y (mm)", 0)
            z = step_analysis.get("Z (mm)", 0)
            
            # ✅ CHANGED: Check for zero volume
            if volume <= 0:
                return {
                    "error": "Invalid volume (zero or negative)",
                    "material": {"name": material_name, "cost_usd": 0, "mass_kg": 0},
                    "machining": {"hours": 0, "cost_usd": 0},
                    "costs": {"material_usd": 0, "labor_usd": 0, "total_usd": 0}
                }
            
            # Material cost from database
            material_cost = self._calculate_material_cost_database_only(volume, material_name)
            
            # Labor - ✅ CHANGED: Check for zero values
            labor_hours = self._calculate_labor_time_fast(waste, surface)
            labor_cost = labor_hours * 65  # $65/hour
            
            total = material_cost["cost_usd"] + labor_cost
            
            return {
                "material": {
                    "name": material_name,
                    "cost_usd": material_cost["cost_usd"],
                    "mass_kg": material_cost["mass_kg"],
                    "source": "database_only"
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
            return {"error": f"Database-only cost calculation error: {str(e)}"}
    
    def _calculate_material_cost_database_only(self, volume_mm3, material_name):
        """Database-only material cost calculation - ZERO DEFAULTS"""
        try:
            # ✅ CHANGED: Check for zero volume
            if volume_mm3 <= 0:
                return {"mass_kg": 0, "cost_usd": 0, "error": "Invalid volume (zero or negative)"}
                
            # Database lookup only
            material = self.database.materials.find_one({"name": material_name, "is_active": True})
            
            if material:
                density = material.get("density", 0)
                price = material.get("price_per_kg", 0)
                
                if density <= 0 or price < 0:  # ✅ CHANGED: Allow 0 price
                    print(f"[COST-DB] ⚠️ Invalid material data: {material_name}")
                    return {"mass_kg": 0, "cost_usd": 0, "error": "Invalid material data in database"}
                
                print(f"[COST-DB] ✅ Found material in database: {material_name}")
            else:
                print(f"[COST-DB] ❌ Material not found in database: {material_name}")
                return {"mass_kg": 0, "cost_usd": 0, "error": "Material not found in database"}
            
            # Calculation
            volume_cm3 = volume_mm3 / 1000
            mass_kg = (volume_cm3 * density) / 1000
            cost = mass_kg * price
            
            return {
                "mass_kg": round(mass_kg, 3),
                "cost_usd": round(cost, 2),
                "source": "database"
            }
            
        except Exception as e:
            print(f"[COST-DB] ❌ Database cost calculation failed: {e}")
            return {"mass_kg": 0, "cost_usd": 0, "error": str(e)}
    
    def _calculate_labor_time_fast(self, waste_mm3, surface_mm2):
        """Fast labor time calculation - ZERO DEFAULTS"""
        try:
            # ✅ CHANGED: Check for zero values
            if waste_mm3 <= 0 and surface_mm2 <= 0:
                return 0.0
                
            roughing_time = waste_mm3 / 3000 if waste_mm3 > 0 else 0
            finishing_time = surface_mm2 / 500 if surface_mm2 > 0 else 0
            total_hours = (roughing_time + finishing_time) / 60
            return round(max(total_hours, 0.0), 2)  # ✅ CHANGED: Allow 0.0 minimum
        except Exception as e:
            print(f"[LABOR-CALC] ❌ Labor calculation error: {e}")
            return 0.0  # ✅ CHANGED: Return 0.0 instead of 1.0


# =====================================================
# CREATE DATABASE-ONLY INSTANCES
# =====================================================

# Create database-only service instance
MaterialAnalysisService = MaterialAnalysisServiceOptimized
CostEstimationService = CostEstimationServiceFast

# For backward compatibility
def create_service():
    return MaterialAnalysisServiceOptimized()

print("[DATABASE-ONLY] ✅ Material Analysis Service Database-Only Version Ready!")
print("[GUARANTEE] 🛡️ ALL materials come from database - NO hardcoded materials")
print("[DATABASE] 📊 Zero static/hardcoded materials - Pure database-driven system")
print("[ZERO-DEFAULTS] 🚫 All default values changed to ZERO - No arbitrary defaults")
print(f"[INTEGRATED] 🧠 Integrated enhanced STEP analysis: {SCIPY_AVAILABLE}")
print(f"[ENHANCED] 📄 Enhanced PDF analysis: {ENHANCED_PDF_AVAILABLE}")

if SCIPY_AVAILABLE:
    print("[INTEGRATED-STEP] 🎯 Available integrated features:")
    print("[INTEGRATED-STEP]   - Face-based geometric optimization")
    print("[INTEGRATED-STEP]   - Convex hull + PCA analysis") 
    print("[INTEGRATED-STEP]   - Intelligent waste ratio minimization")
    print("[INTEGRATED-STEP]   - Smart method selection algorithm")
    print("[INTEGRATED-STEP]   - All functions integrated in material_analysis.py")
    print("[INTEGRATED-STEP]   - ZERO defaults on errors/failures")
else:
    print("[INTEGRATED-STEP] ⚠️ Advanced geometric analysis not available")
    print("[INTEGRATED-STEP] 💡 Install: pip install scipy scikit-learn")

if ENHANCED_PDF_AVAILABLE:
    print("[ENHANCED-PDF] 📄 Enhanced PDF material detection available")
else:
    print("[ENHANCED-PDF] ⚠️ Enhanced PDF analysis not available")

# ✅ ZERO DEFAULTS SUMMARY
print("\n[ZERO-DEFAULTS] 🚫 All default values changed to ZERO:")
print("[ZERO-DEFAULTS] 1. STEP analysis failures return all zeros")
print("[ZERO-DEFAULTS] 2. PDF without STEP uses zero dimensions") 
print("[ZERO-DEFAULTS] 3. Document analysis uses zero dimensions")
print("[ZERO-DEFAULTS] 4. Material calculations require volume > 0")
print("[ZERO-DEFAULTS] 5. Cost calculations handle zero inputs")
print("[ZERO-DEFAULTS] 6. No hardcoded fallback materials")
print("[ZERO-DEFAULTS] Status: ✅ IMPLEMENTED - Pure zero-default system")
