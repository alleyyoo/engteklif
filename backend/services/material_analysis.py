# services/material_analysis.py - ENHANCED WITH PDF STEP RENDERING
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
from services.step_renderer import StepRendererEnhanced

print("[INFO] ✅ Material Analysis Service - Enhanced with PDF STEP Rendering")

class MaterialAnalysisService:
    def __init__(self):
        self.database = db.get_db()
        self._ensure_materials_exist()
        # Initialize STEP renderer
        self.step_renderer = StepRendererEnhanced()
    
    def analyze_document_comprehensive(self, file_path, file_type, user_id):
        """Ana analiz fonksiyonu - TÜM MALZEME HESAPLAMALARI İLE + ENHANCED PDF STEP RENDERING"""
        result = {
            "material_matches": [],
            "step_analysis": {},
            "cost_estimation": {},
            "ai_price_prediction": {},
            "all_material_calculations": [],  
            "material_options": [],           
            "processing_log": [],
            "isometric_view": None,           # ← Ana render dosyası
            "isometric_view_clean": None,     # ← Excel uyumlu versiyon
            "enhanced_renders": {},           # ← Tüm render'lar
            "step_file_hash": None            # ← STEP dosya hash'i
        }
        
        try:
            print(f"[DEBUG] Analiz başlatılıyor: {file_path} ({file_type})")
            
            if file_type == 'pdf':
                result = self._analyze_pdf_with_step_rendering(file_path, result)
            elif file_type in ['step', 'stp']:
                result["step_analysis"] = self.analyze_step_file(file_path)
                result["processing_log"].append("🔧 STEP analizi tamamlandı")
                
                # ✅ STEP dosyası için rendering
                render_result = self._render_step_file(file_path, f"step_{int(time.time())}")
                if render_result["success"]:
                    result["enhanced_renders"] = render_result["renders"]
                    result["isometric_view"] = render_result.get("main_render")
                    result["isometric_view_clean"] = render_result.get("excel_render")
                    result["processing_log"].append(f"🎨 {len(render_result['renders'])} render oluşturuldu")
                else:
                    result["processing_log"].append(f"⚠️ Render hatası: {render_result.get('message')}")
                
                if not result.get("material_matches"):
                    result["material_matches"] = ["6061-T6 (%default)"]
                    
            elif file_type in ['doc', 'docx']:
                result = self._analyze_document(file_path, result)
            
            # ✅ MALZEME HESAPLAMA - STEP analizi varsa
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)")
            
            if prizma_hacim and prizma_hacim > 0:
                print(f"[DEBUG] Prizma hacim bulundu: {prizma_hacim} mm³")
                
                # Bulunan malzemeler için detaylı hesaplama
                if result.get("material_matches"):
                    result["all_material_calculations"] = self._calculate_found_materials(
                        prizma_hacim, result["material_matches"]
                    )
                    result["processing_log"].append(f"🧮 {len(result['all_material_calculations'])} bulunan malzeme hesaplandı")
                
                # Tüm mevcut malzemeler için hesaplama
                result["material_options"] = self._calculate_all_materials(prizma_hacim)
                result["processing_log"].append(f"📊 {len(result['material_options'])} malzeme seçeneği hesaplandı")
                
            else:
                result["processing_log"].append("⚠️ Hacim bilgisi yok, malzeme hesaplaması yapılamadı")
            
            # Maliyet hesaplama
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                cost_service = CostEstimationService()
                result["cost_estimation"] = cost_service.calculate_cost(
                    result["step_analysis"], 
                    result.get("material_matches", ["6061-T6 (%default)"])
                )
                result["processing_log"].append("💰 Maliyet hesaplandı")
            
            # AI fiyat tahmini
            if result.get("step_analysis") and not result["step_analysis"].get("error"):
                result["ai_price_prediction"] = self._calculate_ai_price(
                    result["step_analysis"], 
                    result.get("all_material_calculations", [])
                )
                result["processing_log"].append("🤖 AI fiyat tahmini")
            
            print(f"[SUCCESS] Analiz tamamlandı - {len(result.get('material_options', []))} malzeme seçeneği")
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"Analiz hatası: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[TRACEBACK] {traceback.format_exc()}")
            result["error"] = error_msg
            result["processing_log"].append(f"❌ HATA: {error_msg}")
            return result
    
    def _analyze_pdf_with_step_rendering(self, file_path, result):
        """✅ PDF analizi - ENHANCED WITH STEP RENDERING"""
        result["processing_log"].append("📄 PDF analizi başlatıldı")
        
        # ✅ STEP çıkarma - Enhanced
        step_paths = self._extract_step_from_pdf(file_path)
        extracted_step_path = None
        permanent_step_path = None  # ✅ Kalıcı STEP dosya yolu
        
        if step_paths:
            extracted_step_path = step_paths[0]
            step_filename = os.path.basename(extracted_step_path)
            result["processing_log"].append(f"📎 STEP çıkarıldı: {step_filename}")
            
            # ✅ STEP dosyasını kalıcı olarak sakla
            # Analysis ID'yi file path'den türet
            import hashlib
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            analysis_id = f"pdf_{int(time.time())}_{file_hash}"
            
            # Kalıcı dizin oluştur
            permanent_dir = os.path.join("static", "stepviews", analysis_id)
            os.makedirs(permanent_dir, exist_ok=True)
            
            # STEP dosyasını kopyala
            permanent_step_filename = f"extracted_{analysis_id}.step"
            permanent_step_path = os.path.join(permanent_dir, permanent_step_filename)
            
            import shutil
            shutil.copy2(extracted_step_path, permanent_step_path)
            print(f"[PDF-STEP] 📁 STEP dosyası kalıcı olarak kaydedildi: {permanent_step_path}")
            
            # Result'a kalıcı STEP path'i ekle
            result["extracted_step_path"] = permanent_step_path
            result["pdf_analysis_id"] = analysis_id
            
            # ✅ STEP ANALİZİ
            result["step_analysis"] = self.analyze_step_file(permanent_step_path)  # ✅ Kalıcı dosyayı kullan
            result["processing_log"].append("🔧 STEP analizi tamamlandı")
            
            # ✅ STEP RENDERING - PDF'den çıkarılan dosya için
            if not result["step_analysis"].get("error"):
                print(f"[PDF-RENDER] 🎨 PDF'den çıkarılan STEP rendering başlıyor: {step_filename}")
                
                render_result = self._render_step_file(permanent_step_path, analysis_id)  # ✅ Kalıcı dosyayı kullan
                
                if render_result["success"]:
                    result["enhanced_renders"] = render_result["renders"]
                    result["isometric_view"] = render_result.get("main_render")
                    result["isometric_view_clean"] = render_result.get("excel_render")
                    result["step_file_hash"] = self._calculate_file_hash(permanent_step_path)
                    result["processing_log"].append(f"🎨 PDF STEP render tamamlandı - {len(render_result['renders'])} görünüm")
                    print(f"[PDF-RENDER] ✅ Rendering başarılı - {len(render_result['renders'])} görünüm oluşturuldu")
                    
                    # ✅ STL OLUŞTUR
                    try:
                        import cadquery as cq
                        from cadquery import exporters
                        
                        stl_filename = f"model_{analysis_id}.stl"
                        stl_path = os.path.join(permanent_dir, stl_filename)
                        
                        # STEP'ten STL oluştur
                        assembly = cq.importers.importStep(permanent_step_path)
                        shape = assembly.val()
                        exporters.export(shape, stl_path)
                        
                        if os.path.exists(stl_path):
                            stl_relative = f"/static/stepviews/{analysis_id}/{stl_filename}"
                            result["stl_generated"] = True
                            result["stl_path"] = stl_relative
                            result["stl_file_size"] = os.path.getsize(stl_path)
                            result["processing_log"].append(f"🎯 STL oluşturuldu: {stl_filename}")
                            print(f"[PDF-STL] ✅ STL oluşturuldu: {stl_path}")
                            
                    except Exception as stl_error:
                        print(f"[PDF-STL] ⚠️ STL oluşturma hatası: {stl_error}")
                        result["processing_log"].append(f"⚠️ STL oluşturulamadı: {str(stl_error)}")
                        
                else:
                    result["processing_log"].append(f"⚠️ PDF STEP render hatası: {render_result.get('message')}")
                    print(f"[PDF-RENDER] ❌ Rendering başarısız: {render_result.get('message')}")
            else:
                result["processing_log"].append("⚠️ STEP analizi başarısız, render yapılamadı")
                
        else:
            result["processing_log"].append("⚠️ PDF'de STEP bulunamadı, varsayılan boyutlar kullanılacak")
            # Varsayılan STEP analizi
            result["step_analysis"] = {
                "X (mm)": 90.0,
                "Y (mm)": 40.0, 
                "Z (mm)": 15.0,
                "X+Pad (mm)": 100,
                "Y+Pad (mm)": 50,
                "Z+Pad (mm)": 25,
                "Silindirik Çap (mm)": 90.0,
                "Silindirik Yükseklik (mm)": 15.0,
                "Prizma Hacmi (mm³)": 125000,
                "Ürün Hacmi (mm³)": 100000,
                "Talaş Hacmi (mm³)": 25000,
                "Talaş Oranı (%)": 20.0,
                "Toplam Yüzey Alanı (mm²)": 15000,
                "method": "estimated_from_pdf"
            }
        
        # Malzeme arama (4 kez döndürme ile)
        working_file = file_path
        for attempt in range(4):
            text = self._extract_text_from_pdf(working_file)
            materials = self._find_materials_in_text(text)
            
            if materials:
                result["material_matches"] = materials
                result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
                break
            
            if attempt < 3:
                working_file = self._rotate_pdf(working_file)
                result["processing_log"].append(f"🔄 PDF döndürüldü ({attempt + 1})")
        
        # Malzeme bulunamazsa varsayılan
        if not result.get("material_matches"):
            result["material_matches"] = ["6061-T6 (%estimated)"]
            result["processing_log"].append("⚠️ Malzeme tespit edilemedi, varsayılan kullanıldı")
        
        # ✅ GEÇİCİ STEP dosyasını temizle AMA KALICI OLANINI SAKLA
        if extracted_step_path and extracted_step_path != permanent_step_path and os.path.exists(extracted_step_path):
            try:
                os.remove(extracted_step_path)
                print(f"[CLEANUP] 🗑️ Geçici STEP dosyası temizlendi: {os.path.basename(extracted_step_path)}")
            except Exception as cleanup_error:
                print(f"[CLEANUP] ⚠️ Temizlik hatası: {cleanup_error}")
        
        return result
    
    def _render_step_file(self, step_path, analysis_id):
        """✅ STEP dosyası rendering wrapper"""
        try:
            print(f"[STEP-RENDER] 🎨 Rendering başlıyor: {os.path.basename(step_path)}")
            
            # StepRendererEnhanced kullan
            render_result = self.step_renderer.generate_comprehensive_views(
                step_path=step_path,
                analysis_id=analysis_id,
                include_dimensions=True,
                include_materials=True,
                high_quality=True
            )
            
            if render_result["success"]:
                # Ana render dosyasını belirle (isometric öncelikli)
                main_render = None
                excel_render = None
                
                if "isometric" in render_result["renders"]:
                    isometric_data = render_result["renders"]["isometric"]
                    if isometric_data.get("success"):
                        main_render = isometric_data.get("file_path")
                        excel_render = isometric_data.get("excel_path")
                
                # Ana render bulunamazsa ilk başarılı render'ı kullan
                if not main_render:
                    for view_name, view_data in render_result["renders"].items():
                        if view_data.get("success") and view_data.get("file_path"):
                            main_render = view_data["file_path"]
                            break
                
                return {
                    "success": True,
                    "renders": render_result["renders"],
                    "main_render": main_render,
                    "excel_render": excel_render,
                    "session_id": render_result.get("session_id"),
                    "total_views": len(render_result["renders"])
                }
            else:
                return {
                    "success": False,
                    "message": render_result.get("message", "Rendering başarısız"),
                    "renders": {}
                }
                
        except Exception as e:
            import traceback
            print(f"[STEP-RENDER] ❌ Rendering hatası: {str(e)}")
            print(f"[STEP-RENDER] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Rendering hatası: {str(e)}",
                "error": str(e)
            }
    
    def _calculate_file_hash(self, file_path):
        """Dosya hash'i hesapla"""
        try:
            import hashlib
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            print(f"[HASH] ⚠️ Hash hesaplama hatası: {e}")
            return None
    
    def _analyze_document(self, file_path, result):
        """DOC/DOCX analizi"""
        result["processing_log"].append("📝 Document analizi başlatıldı")
        
        try:
            if file_path.lower().endswith('.docx'):
                text = self._extract_text_from_docx(file_path)
            else:
                text = self._extract_text_from_doc(file_path)
            
            # Malzeme arama
            materials = self._find_materials_in_text(text)
            if materials:
                result["material_matches"] = materials
                result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
            else:
                result["material_matches"] = ["6061-T6 (%estimated)"]
                result["processing_log"].append("⚠️ Malzeme tespit edilemedi, varsayılan kullanıldı")
            
            # Varsayılan STEP analizi (document için)
            result["step_analysis"] = {
                "X (mm)": 50.0,
                "Y (mm)": 30.0, 
                "Z (mm)": 20.0,
                "X+Pad (mm)": 60,
                "Y+Pad (mm)": 40,
                "Z+Pad (mm)": 30,
                "Silindirik Çap (mm)": 50.0,
                "Silindirik Yükseklik (mm)": 20.0,
                "Prizma Hacmi (mm³)": 72000,
                "Ürün Hacmi (mm³)": 56000,
                "Talaş Hacmi (mm³)": 16000,
                "Talaş Oranı (%)": 22.2,
                "Toplam Yüzey Alanı (mm²)": 8800,
                "method": "estimated_from_document"
            }
            
        except Exception as e:
            result["processing_log"].append(f"❌ Document analiz hatası: {e}")
            
        return result
    
    def analyze_step_file(self, step_path):
        """STEP dosyası analizi - app.py referansıyla"""
        try:
            print(f"[DEBUG] STEP analizi başlıyor: {step_path}")
            
            assembly = cq.importers.importStep(step_path)
            if not assembly.objects:
                return {"error": "STEP dosyasında obje yok"}
            
            # Ana şekil ve bounding box
            shapes = assembly.objects
            sorted_shapes = sorted(shapes, key=lambda s: s.Volume(), reverse=True)
            main_shape = sorted_shapes[0]
            main_bbox = main_shape.BoundingBox()
            
            # İlgili şekilleri bul
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
            
            # Compound oluştur
            part = cq.Compound.makeCompound(relevant_shapes)
            
            # Optimal yönlendirme bulma
            min_volume = None
            best_dims = (0, 0, 0)
            
            print(f"[DEBUG] Optimal yönlendirme hesaplanıyor...")
            
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
                            continue
            
            # Boyutları al
            x, y, z = best_dims
            
            # Padding ekleme
            def always_round_up(value):
                return int(value) if abs(value - int(value)) < 0.01 else int(value) + 1
            
            x_pad = always_round_up(x + 10.0)
            y_pad = always_round_up(y + 10.0)
            z_pad = always_round_up(z + 10.0)
            
            # Hacim hesaplamaları
            volume_padded = x_pad * y_pad * z_pad
            product_volume = part.Volume()
            waste_volume = volume_padded - product_volume
            waste_ratio = (waste_volume / volume_padded * 100) if volume_padded > 0 else 0.0
            total_surface_area = part.Area()
            
            # Silindirik boyutlar
            cylindrical_diameter = max(x, y)
            cylindrical_height = z
            
            print(f"[SUCCESS] STEP analizi tamamlandı - X:{x:.1f}, Y:{y:.1f}, Z:{z:.1f}")
            
            return {
                "X (mm)": round(x, 3),
                "Y (mm)": round(y, 3),
                "Z (mm)": round(z, 3),
                "Silindirik Çap (mm)": round(cylindrical_diameter, 3),
                "Silindirik Yükseklik (mm)": round(cylindrical_height, 3),
                "X+Pad (mm)": round(x_pad, 3),
                "Y+Pad (mm)": round(y_pad, 3),
                "Z+Pad (mm)": round(z_pad, 3),
                "Prizma Hacmi (mm³)": round(volume_padded, 3),
                "Ürün Hacmi (mm³)": round(product_volume, 3),
                "Talaş Hacmi (mm³)": round(waste_volume, 3),
                "Talaş Oranı (%)": round(waste_ratio, 2),
                "Toplam Yüzey Alanı (mm²)": round(total_surface_area, 3),
                "shape_count": len(shapes),
                "relevant_shape_count": len(relevant_shapes),
                "optimization_iterations": 64,
                "method": "cadquery_analysis"
            }
            
        except Exception as e:
            import traceback
            print(f"[ERROR] STEP analizi hatası: {str(e)}")
            print(f"[TRACEBACK] {traceback.format_exc()}")
            return {"error": f"STEP analiz hatası: {str(e)}"}
    
    def _calculate_found_materials(self, prizma_hacim_mm3, found_materials):
        """✅ BULUNAN MALZEMELER İÇİN DETAYLI HESAPLAMA - MongoDB'den veri alarak"""
        try:
            calculations = []
            print(f"[DEBUG] Bulunan malzemeler hesaplanıyor: {found_materials}")
            print(f"[DEBUG] MongoDB'deki malzeme sayısı: {self.database.materials.count_documents({})}")
            
            for material_text in found_materials:
                # Malzeme adını temizle
                material_name = material_text.split("(")[0].strip()
                confidence = "100%" if "%100" in material_text else "estimated"
                
                print(f"[DEBUG] Aranan malzeme: '{material_name}'")
                
                # MongoDB'den malzeme bilgisi al - daha geniş arama
                material = self.database.materials.find_one({
                    "$or": [
                        {"name": {"$regex": f"^{material_name}$", "$options": "i"}},  # Exact match (case insensitive)
                        {"name": {"$regex": material_name, "$options": "i"}},        # Partial match
                        {"aliases": {"$in": [material_name]}},                      # Alias match
                        {"aliases": {"$elemMatch": {"$regex": material_name, "$options": "i"}}}  # Alias partial match
                    ]
                })
                
                if material:
                    print(f"[SUCCESS] MongoDB'de bulundu: {material.get('name')}")
                    density = material.get("density", 2.7)
                    price_per_kg = material.get("price_per_kg", 4.5)
                    actual_name = material.get("name", material_name)
                    category = material.get("category", "Unknown")
                    aliases = material.get("aliases", [])
                else:
                    print(f"[WARNING] MongoDB'de bulunamadı: {material_name}, varsayılan kullanılıyor")
                    # Varsayılan değerler - yaygın malzemeler için
                    if "6061" in material_name.upper():
                        density, price_per_kg = 2.7, 4.5
                        category = "Alüminyum"
                    elif "7075" in material_name.upper():
                        density, price_per_kg = 2.81, 6.2
                        category = "Alüminyum"
                    elif "304" in material_name.upper():
                        density, price_per_kg = 7.93, 8.5
                        category = "Paslanmaz Çelik"
                    elif "316" in material_name.upper():
                        density, price_per_kg = 7.98, 12.0
                        category = "Paslanmaz Çelik"
                    elif "ST37" in material_name.upper() or "S235" in material_name.upper():
                        density, price_per_kg = 7.85, 2.2
                        category = "Karbon Çelik"
                    else:
                        density, price_per_kg = 2.7, 4.5
                        category = "Unknown"
                    
                    actual_name = material_name
                    aliases = []
                
                # Kütle hesaplama (mm³ -> cm³ -> kg)
                # Prizma hacmi (mm³) * yoğunluk (g/cm³) / 1,000,000 = kütle (kg)
                mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                material_cost = round(mass_kg * price_per_kg, 2)
                
                calculation = {
                    "material": actual_name,
                    "original_text": material_text,
                    "confidence": confidence,
                    "category": category,
                    "aliases": aliases,
                    "density": density,          # ← ÖZKÜTLE (g/cm³)
                    "mass_kg": mass_kg,          # ← KÜTLE (kg)
                    "price_per_kg": price_per_kg, # ← KG FİYATI (USD)
                    "material_cost": material_cost, # ← TOPLAM MALİYET (USD)
                    "volume_mm3": prizma_hacim_mm3,
                    "found_in_db": material is not None
                }
                
                calculations.append(calculation)
                print(f"[CALC-FOUND] {actual_name}: {density}g/cm³ x {mass_kg}kg x ${price_per_kg} = ${material_cost}")
            
            print(f"[SUCCESS] {len(calculations)} bulunan malzeme hesaplandı")
            return calculations
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Bulunan malzeme hesaplama hatası: {e}")
            print(f"[TRACEBACK] {traceback.format_exc()}")
            return []
    
    def _calculate_all_materials(self, prizma_hacim_mm3):
        """✅ TÜM MEVCUT MALZEMELER İÇİN HESAPLAMA - MongoDB'den tam liste"""
        try:
            all_materials = []
            print(f"[DEBUG] MongoDB'den tüm malzemeler alınıyor...")
            
            # MongoDB'den tüm aktif malzemeleri al
            materials_cursor = self.database.materials.find({})
            materials = list(materials_cursor)
            
            print(f"[DEBUG] MongoDB'de {len(materials)} malzeme bulundu")
            
            if len(materials) == 0:
                print("[WARNING] MongoDB'de malzeme yok, varsayılan malzemeler ekleniyor")
                self._add_default_materials()
                materials = list(self.database.materials.find({}))
                print(f"[INFO] {len(materials)} varsayılan malzeme eklendi")
            
            for material in materials:
                name = material.get("name", "Unknown")
                density = material.get("density", 2.7)
                price_per_kg = material.get("price_per_kg", 4.5)
                category = material.get("category", "Unknown")
                aliases = material.get("aliases", [])
                
                # Güvenlik kontrolü - sayısal değerler
                if not isinstance(density, (int, float)) or density <= 0:
                    print(f"[WARNING] Geçersiz density: {name} - {density}, varsayılan kullanılıyor")
                    density = 2.7
                
                if not isinstance(price_per_kg, (int, float)) or price_per_kg < 0:
                    print(f"[WARNING] Geçersiz price: {name} - {price_per_kg}, varsayılan kullanılıyor")
                    price_per_kg = 4.5
                
                # Kütle ve maliyet hesaplama
                mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                material_cost = round(mass_kg * price_per_kg, 2)
                
                material_option = {
                    "name": name,
                    "category": category,
                    "aliases": aliases,
                    "density": density,          # ← ÖZKÜTLE (g/cm³)
                    "mass_kg": mass_kg,          # ← KÜTLE (kg)
                    "price_per_kg": price_per_kg, # ← KG FİYATI (USD)
                    "material_cost": material_cost, # ← TOPLAM MALİYET (USD)
                    "volume_mm3": prizma_hacim_mm3
                }
                
                all_materials.append(material_option)
            
            # Fiyata göre sırala (en ucuzdan en pahalıya)
            all_materials.sort(key=lambda x: x["material_cost"])
            
            print(f"[SUCCESS] {len(all_materials)} malzeme için hesaplama tamamlandı")
            
            # İlk 5'ini logla
            for i, mat in enumerate(all_materials[:5]):
                print(f"[TOP-{i+1}] {mat['name']}: {mat['mass_kg']}kg x ${mat['price_per_kg']} = ${mat['material_cost']}")
            
            return all_materials
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Tüm malzemeler hesaplama hatası: {e}")
            print(f"[TRACEBACK] {traceback.format_exc()}")
            return []
    
    def _add_default_materials(self):
        """MongoDB'ye varsayılan malzemeleri ekle"""
        try:
            default_materials = [
                {
                    "name": "6061-T6",
                    "aliases": ["6061", "Al 6061", "AA6061"],
                    "density": 2.70,
                    "price_per_kg": 4.50,
                    "category": "Alüminyum",
                    "description": "Genel amaçlı alüminyum alaşımı",
                    "is_active": True
                },
                {
                    "name": "7075-T6", 
                    "aliases": ["7075", "Al 7075", "AA7075"],
                    "density": 2.81,
                    "price_per_kg": 6.20,
                    "category": "Alüminyum",
                    "description": "Yüksek mukavemetli alüminyum alaşımı",
                    "is_active": True
                },
                {
                    "name": "304 Paslanmaz",
                    "aliases": ["304", "SS304", "AISI 304", "1.4301"],
                    "density": 7.93,
                    "price_per_kg": 8.50,
                    "category": "Paslanmaz Çelik",
                    "description": "Genel amaçlı paslanmaz çelik",
                    "is_active": True
                },
                {
                    "name": "316 Paslanmaz",
                    "aliases": ["316", "SS316", "AISI 316", "1.4401"],
                    "density": 7.98,
                    "price_per_kg": 12.00,
                    "category": "Paslanmaz Çelik",
                    "description": "Kimyasal dayanımlı paslanmaz çelik",
                    "is_active": True
                },
                {
                    "name": "St37",
                    "aliases": ["S235", "A36", "St 37", "DIN St37"],
                    "density": 7.85,
                    "price_per_kg": 2.20,
                    "category": "Karbon Çelik",
                    "description": "Genel yapı çeliği",
                    "is_active": True
                },
                {
                    "name": "C45",
                    "aliases": ["CK45", "AISI 1045", "S45C"],
                    "density": 7.85,
                    "price_per_kg": 2.80,
                    "category": "Karbon Çelik",
                    "description": "Orta karbonlu çelik",
                    "is_active": True
                },
                {
                    "name": "Ti-6Al-4V",
                    "aliases": ["Grade 5", "Ti64", "Titanium Grade 5"],
                    "density": 4.43,
                    "price_per_kg": 45.00,
                    "category": "Titanyum",
                    "description": "Havacılık titanyum alaşımı",
                    "is_active": True
                },
                {
                    "name": "Pirinç CuZn37",
                    "aliases": ["Brass", "Ms58", "CuZn37"],
                    "density": 8.50,
                    "price_per_kg": 7.80,
                    "category": "Bakır Alaşımı",
                    "description": "Standart pirinç",
                    "is_active": True
                }
            ]
            
            # Mevcut malzemeleri temizle ve yenilerini ekle
            self.database.materials.delete_many({})
            result = self.database.materials.insert_many(default_materials)
            print(f"[INFO] {len(result.inserted_ids)} varsayılan malzeme MongoDB'ye eklendi")
            
        except Exception as e:
            print(f"[ERROR] Varsayılan malzeme ekleme hatası: {e}")
    
    def _ensure_materials_exist(self):
        """Malzeme veritabanını kontrol et ve debug bilgisi ver"""
        try:
            count = self.database.materials.count_documents({})
            print(f"[DEBUG] MongoDB'de {count} malzeme mevcut")
            
            # MongoDB'deki malzemeleri logla
            if count > 0:
                sample_materials = list(self.database.materials.find({}).limit(3))
                print("[DEBUG] MongoDB'deki örnek malzemeler:")
                for mat in sample_materials:
                    print(f"  - {mat.get('name')}: {mat.get('density')}g/cm³, ${mat.get('price_per_kg')}/kg")
            
            if count < 5:
                print("[INFO] Yetersiz malzeme, varsayılan malzemeler ekleniyor...")
                self._add_default_materials()
                
        except Exception as e:
            print(f"[WARN] Malzeme kontrol hatası: {e}")
            try:
                # Fallback - en temel malzemeler
                basic_materials = [
                    {"name": "6061-T6", "aliases": ["6061"], "density": 2.70, "price_per_kg": 4.50, "category": "Alüminyum"},
                    {"name": "St37", "aliases": ["S235"], "density": 7.85, "price_per_kg": 2.20, "category": "Karbon Çelik"}
                ]
                self.database.materials.insert_many(basic_materials)
                print(f"[FALLBACK] {len(basic_materials)} temel malzeme eklendi")
            except Exception as fallback_error:
                print(f"[ERROR] Fallback malzeme ekleme de başarısız: {fallback_error}")
    
    def _find_materials_in_text(self, text):
        """Metinde malzeme arama"""
        if not text or len(text.strip()) < 10:
            return []
        
        materials = []
        text_upper = text.upper()
        
        print(f"[DEBUG] Metin analizi - uzunluk: {len(text)} karakter")
        
        # Alaşım kodları
        alloy_patterns = {
            "6061": "6061-T6",
            "7075": "7075-T6", 
            "2024": "2024-T3",
            "304": "304 Paslanmaz",
            "316": "316 Paslanmaz",
            "ST37": "St37",
            "S235": "St37",
            "C45": "C45",
            "CK45": "C45"
        }
        
        for pattern, name in alloy_patterns.items():
            if pattern in text_upper:
                materials.append(f"{name} (%100)")
                print(f"[FOUND] Alaşım: {pattern} -> {name}")
        
        # Genel malzeme isimleri
        general_materials = {
            "ALÜMINYUM": "6061-T6",
            "ALUMINUM": "6061-T6", 
            "ALUMINIUM": "6061-T6",
            "ÇELİK": "St37",
            "STEEL": "St37",
            "PASLANMAZ": "304 Paslanmaz",
            "STAINLESS": "304 Paslanmaz",
            "PIRINÇ": "Pirinç CuZn37",
            "BRASS": "Pirinç CuZn37"
        }
        
        for keyword, name in general_materials.items():
            if keyword in text_upper:
                material_text = f"{name} (%estimated)"
                if material_text not in materials:
                    materials.append(material_text)
                    print(f"[FOUND] Genel: {keyword} -> {name}")
        
        return list(set(materials))[:5]
    
    def _extract_text_from_pdf(self, pdf_path):
        """PDF'den metin çıkarma"""
        try:
            pages = convert_from_path(pdf_path, dpi=300)
            text = ""
            for page in pages[:2]:  # İlk 2 sayfa
                text += pytesseract.image_to_string(page, lang='tur+eng')
            return text
        except Exception as e:
            print(f"[ERROR] PDF metin çıkarma: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path):
        """DOCX'den metin çıkarma"""
        try:
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            print(f"[ERROR] DOCX metin çıkarma: {e}")
            return ""
    
    def _extract_text_from_doc(self, file_path):
        """DOC'tan metin çıkarma"""
        try:
            # LibreOffice ile DOC -> DOCX dönüştürme
            output_dir = os.path.dirname(file_path)
            result = subprocess.run([
                "libreoffice", "--headless", "--convert-to", "docx", 
                "--outdir", output_dir, file_path
            ], capture_output=True)
            
            docx_path = os.path.splitext(file_path)[0] + ".docx"
            if os.path.exists(docx_path):
                return self._extract_text_from_docx(docx_path)
            return ""
        except Exception as e:
            print(f"[ERROR] DOC metin çıkarma: {e}")
            return ""
    
    def _extract_step_from_pdf(self, pdf_path):
        """PDF'den STEP çıkarma - Enhanced with better error handling"""
        extracted = []
        try:
            print(f"[PDF-STEP] 🔍 PDF'den STEP aranıyor: {os.path.basename(pdf_path)}")
            
            with pikepdf.open(pdf_path) as pdf:
                # EmbeddedFiles method
                try:
                    root = pdf.trailer.get("/Root", {})
                    names = root.get("/Names", {})
                    embedded = names.get("/EmbeddedFiles", {})
                    files = embedded.get("/Names", [])
                    
                    print(f"[PDF-STEP] 📋 {len(files)//2} embedded dosya bulundu")
                    
                    for i in range(0, len(files), 2):
                        if i + 1 < len(files):
                            try:
                                file_spec = files[i + 1]
                                file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                                
                                print(f"[PDF-STEP] 📄 Embedded dosya: {file_name}")
                                
                                if file_name.lower().endswith(('.stp', '.step')):
                                    print(f"[PDF-STEP] 🎯 STEP dosyası tespit edildi: {file_name}")
                                    
                                    # Dosya verilerini çıkar
                                    file_data = file_spec['/EF']['/F'].read_bytes()
                                    
                                    # Güvenli dosya adı oluştur
                                    safe_filename = "".join(c for c in file_name if c.isalnum() or c in "._-")
                                    if not safe_filename.lower().endswith(('.stp', '.step')):
                                        safe_filename += '.stp'
                                    
                                    # Temp klasöründe kaydet
                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                    os.makedirs(temp_dir, exist_ok=True)
                                    
                                    output_path = os.path.join(temp_dir, safe_filename)
                                    
                                    with open(output_path, 'wb') as f:
                                        f.write(file_data)
                                    
                                    # Dosya boyutunu kontrol et
                                    file_size = os.path.getsize(output_path)
                                    print(f"[PDF-STEP] ✅ STEP çıkarıldı: {safe_filename} ({file_size} bytes)")
                                    
                                    if file_size > 100:  # En az 100 byte olmalı
                                        extracted.append(output_path)
                                    else:
                                        print(f"[PDF-STEP] ⚠️ Dosya çok küçük, geçersiz: {safe_filename}")
                                        os.remove(output_path)
                                        
                            except Exception as extract_error:
                                print(f"[PDF-STEP] ❌ Dosya çıkarma hatası: {extract_error}")
                                continue
                                
                except Exception as e:
                    print(f"[PDF-STEP] ⚠️ EmbeddedFiles okuma hatası: {e}")
                    
        except Exception as e:
            print(f"[PDF-STEP] ❌ PDF okuma hatası: {e}")
        
        print(f"[PDF-STEP] 📊 Toplam {len(extracted)} STEP dosyası çıkarıldı")
        return extracted
    
    def _rotate_pdf(self, input_path):
        """PDF döndürme"""
        try:
            temp_file = NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.close()
            
            with pikepdf.open(input_path) as pdf:
                for page in pdf.pages:
                    page.Rotate = (page.Rotate + 90) % 360
                pdf.save(temp_file.name)
            
            return temp_file.name
        except:
            return input_path
    
    def _calculate_ai_price(self, step_analysis, material_calculations=None):
        """AI fiyat tahmini"""
        try:
            waste = step_analysis.get("Talaş Hacmi (mm³)", 0)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 0)
            
            # İlk bulunan malzemenin maliyetini kullan
            material_cost = 0
            if material_calculations and len(material_calculations) > 0:
                material_cost = material_calculations[0].get("material_cost", 0)
            
            # Kaba talaş parametreleri
            feed_rate = min(8000 * 0.12 * 3, 3000)
            ap, ae = 1, 10
            kaba_sure = waste / (feed_rate * ap * ae) if (feed_rate * ap * ae) > 0 else 0
            
            # Finishing parametreleri
            finishing_sure = surface / 400 if surface > 0 else 0
            
            # Maliyetler ($65/saat kaba, $120/saat finishing)
            kaba_maliyet = (kaba_sure / 60) * 65
            finishing_maliyet = (finishing_sure / 60) * 120
            toplam = kaba_maliyet + finishing_maliyet + material_cost
            
            return {
                "toplam": round(toplam, 2),
                "kaba_maliyet": round(kaba_maliyet, 2),
                "finishing_maliyet": round(finishing_maliyet, 2),
                "material_cost": round(material_cost, 2),
                "kaba_sure_dakika": round(kaba_sure, 2),
                "finishing_sure_dakika": round(finishing_sure, 2),
                "toplam_sure_saat": round((kaba_sure + finishing_sure) / 60, 2)
            }
        except Exception as e:
            print(f"[ERROR] AI fiyat tahmini: {e}")
            return {"error": str(e)}


class CostEstimationService:
    def __init__(self):
        self.database = db.get_db()
    
    def calculate_cost(self, step_analysis, material_matches):
        """Maliyet hesaplama"""
        try:
            if not step_analysis or step_analysis.get("error"):
                return {"error": "STEP analizi gerekli"}
            
            if not material_matches:
                return {"error": "Malzeme gerekli"}
            
            # İlk malzeme
            material_name = material_matches[0].split("(")[0].strip()
            
            # Hacimler
            volume = step_analysis.get("Prizma Hacmi (mm³)", 100000)
            waste = step_analysis.get("Talaş Hacmi (mm³)", 25000)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 10000)
            
            # Boyutlar
            x = step_analysis.get("X (mm)", 0)
            y = step_analysis.get("Y (mm)", 0)
            z = step_analysis.get("Z (mm)", 0)
            
            # Malzeme maliyeti
            material_cost = self._calculate_material_cost(volume, material_name)
            
            # İşçilik
            labor_hours = self._calculate_labor_time(waste, surface)
            labor_cost = labor_hours * 65  # $65/saat
            
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
                    "x_mm": x,
                    "y_mm": y,
                    "z_mm": z,
                    "volume_mm3": volume,
                    "waste_mm3": waste,
                    "surface_mm2": surface
                },
                "costs": {
                    "material_usd": material_cost["cost_usd"],
                    "labor_usd": round(labor_cost, 2),
                    "total_usd": round(total, 2)
                }
            }
            
        except Exception as e:
            return {"error": f"Maliyet hatası: {str(e)}"}
    
    def _calculate_material_cost(self, volume_mm3, material_name):
        """Malzeme maliyet hesaplama"""
        try:
            # Malzeme bilgisi al
            material = self.database.materials.find_one({"name": material_name})
            
            if material:
                density = material.get("density", 2.7)
                price = material.get("price_per_kg", 4.5)
            else:
                # Varsayılan (6061)
                density = 2.7
                price = 4.5
            
            # Kütle hesapla
            volume_cm3 = volume_mm3 / 1000
            mass_kg = (volume_cm3 * density) / 1000
            cost = mass_kg * price
            
            return {
                "mass_kg": round(mass_kg, 3),
                "cost_usd": round(cost, 2)
            }
            
        except:
            return {"mass_kg": 1.0, "cost_usd": 5.0}
    
    def _calculate_labor_time(self, waste_mm3, surface_mm2):
        """İşçilik süresi hesaplama"""
        try:
            roughing_time = waste_mm3 / 2400  # dakika
            finishing_time = surface_mm2 / 400
            total_hours = (roughing_time + finishing_time) / 60
            return round(max(total_hours, 0.5), 2)  # Min 0.5 saat
        except:
            return 1.0