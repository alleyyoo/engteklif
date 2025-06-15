# services/material_analysis.py
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

class MaterialAnalysisService:
    def __init__(self):
        self.database = db.get_db()
        self._ensure_materials_exist()
    
    def analyze_document_comprehensive(self, file_path, file_type, user_id):
        """Ana analiz fonksiyonu"""
        result = {
            "material_matches": [],
            "step_analysis": {},
            "cost_estimation": {},
            "ai_price_prediction": {},
            "processing_log": []
        }
        
        try:
            if file_type == 'pdf':
                result = self._analyze_pdf(file_path, result)
            elif file_type in ['step', 'stp']:
                result["step_analysis"] = self.analyze_step_file(file_path)
                result["processing_log"].append("🔧 STEP analizi tamamlandı")
            
            # Maliyet hesaplama - STEP analizi varsa
            if result.get("step_analysis"):
                cost_service = CostEstimationService()
                result["cost_estimation"] = cost_service.calculate_cost(
                    result["step_analysis"], result.get("material_matches", ["6061-T6 (%default)"])
                )
                result["processing_log"].append("💰 Maliyet hesaplandı")
            
            # AI fiyat tahmini - STEP analizi varsa
            if result.get("step_analysis"):
                result["ai_price_prediction"] = self._calculate_ai_price(result["step_analysis"])
                result["processing_log"].append("🤖 AI fiyat tahmini")
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["processing_log"].append(f"❌ HATA: {str(e)}")
            return result
    
    def _analyze_pdf(self, file_path, result):
        """PDF analizi"""
        result["processing_log"].append("📄 PDF analizi başlatıldı")
        
        # STEP çıkarma
        step_paths = self._extract_step_from_pdf(file_path)
        if step_paths:
            result["processing_log"].append(f"📎 STEP çıkarıldı: {os.path.basename(step_paths[0])}")
            result["step_analysis"] = self.analyze_step_file(step_paths[0])
        else:
            result["processing_log"].append("⚠️ PDF'de STEP bulunamadı, varsayılan boyutlar kullanılacak")
            # STEP bulunamazsa varsayılan boyutlar
            result["step_analysis"] = {
                "X+Pad (mm)": 100,
                "Y+Pad (mm)": 50,
                "Z+Pad (mm)": 25,
                "Prizma Hacmi (mm³)": 125000,
                "Ürün Hacmi (mm³)": 100000,
                "Talaş Hacmi (mm³)": 25000,
                "Toplam Yüzey Alanı (mm²)": 15000,
                "method": "estimated_from_pdf"
            }
        
        # Malzeme arama
        for attempt in range(4):
            text = self._extract_text_from_pdf(file_path)
            materials = self._find_materials_in_text(text)
            
            if materials:
                result["material_matches"] = materials
                result["processing_log"].append(f"🔍 {len(materials)} malzeme bulundu")
                break
            
            if attempt < 3:
                file_path = self._rotate_pdf(file_path)
                result["processing_log"].append(f"🔄 PDF döndürüldü ({attempt + 1})")
        
        # Malzeme bulunamazsa varsayılan
        if not result.get("material_matches"):
            result["material_matches"] = ["6061-T6 (%estimated)"]
            result["processing_log"].append("⚠️ Malzeme tespit edilemedi, varsayılan kullanıldı")
        
        return result
    
    def _find_materials_in_text(self, text):
        """Metinde malzeme arama - geliştirilmiş"""
        if not text or len(text.strip()) < 10:
            return []
        
        materials = []
        text_upper = text.upper()
        
        print(f"[DEBUG] Metin uzunluğu: {len(text)} karakter")
        print(f"[DEBUG] İlk 200 karakter: {text[:200]}")
        
        # Alaşım kodları - daha kapsamlı
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
                print(f"[SUCCESS] Bulunan alaşım: {pattern} -> {name}")
        
        # Genel malzeme isimleri
        general_materials = {
            "ALÜMINYUM": "6061-T6",
            "ALUMINUM": "6061-T6", 
            "ALUMINIUM": "6061-T6",
            "ÇELİK": "St37",
            "STEEL": "St37",
            "PASLANMAZ": "304 Paslanmaz",
            "STAINLESS": "304 Paslanmaz",
            "PIRINÇ": "Pirinç",
            "BRASS": "Pirinç"
        }
        
        for keyword, name in general_materials.items():
            if keyword in text_upper:
                material_text = f"{name} (%estimated)"
                if material_text not in materials:
                    materials.append(material_text)
                    print(f"[SUCCESS] Bulunan malzeme: {keyword} -> {name}")
        
        print(f"[INFO] Toplam {len(materials)} malzeme bulundu")
        return list(set(materials))[:5]
    
    def analyze_step_file(self, step_path):
        """STEP dosyası analizi"""
        try:
            assembly = cq.importers.importStep(step_path)
            if not assembly.objects:
                return {"error": "STEP dosyasında obje yok"}
            
            main_shape = max(assembly.objects, key=lambda s: s.Volume())
            bbox = main_shape.BoundingBox()
            
            # Boyutlar
            x, y, z = bbox.xlen, bbox.ylen, bbox.zlen
            x_pad, y_pad, z_pad = int(x + 10), int(y + 10), int(z + 10)
            
            # Hacimler
            bounding_volume = x_pad * y_pad * z_pad
            product_volume = main_shape.Volume()
            waste_volume = bounding_volume - product_volume
            surface_area = main_shape.Area()
            
            return {
                "X+Pad (mm)": x_pad,
                "Y+Pad (mm)": y_pad,
                "Z+Pad (mm)": z_pad,
                "Prizma Hacmi (mm³)": int(bounding_volume),
                "Ürün Hacmi (mm³)": int(product_volume),
                "Talaş Hacmi (mm³)": int(waste_volume),
                "Toplam Yüzey Alanı (mm²)": int(surface_area)
            }
            
        except Exception as e:
            return {"error": f"STEP analizi hatası: {str(e)}"}
    
    def _extract_text_from_pdf(self, pdf_path):
        """PDF'den metin çıkarma"""
        try:
            pages = convert_from_path(pdf_path, dpi=300)
            text = ""
            for page in pages:
                text += pytesseract.image_to_string(page, lang='tur+eng')
            return text
        except:
            return ""
    
    def _extract_step_from_pdf(self, pdf_path):
        """PDF'den STEP çıkarma - geliştirilmiş"""
        extracted = []
        try:
            with pikepdf.open(pdf_path) as pdf:
                # Method 1: EmbeddedFiles
                try:
                    root = pdf.trailer.get("/Root", {})
                    names = root.get("/Names", {})
                    embedded = names.get("/EmbeddedFiles", {})
                    files = embedded.get("/Names", [])
                    
                    for i in range(0, len(files), 2):
                        if i + 1 < len(files):
                            file_spec = files[i + 1]
                            file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                            
                            if file_name.lower().endswith(('.stp', '.step')):
                                try:
                                    file_data = file_spec['/EF']['/F'].read_bytes()
                                    output_path = os.path.join("temp", file_name)
                                    os.makedirs("temp", exist_ok=True)
                                    
                                    with open(output_path, 'wb') as f:
                                        f.write(file_data)
                                    extracted.append(output_path)
                                    print(f"[SUCCESS] STEP çıkarıldı: {file_name}")
                                except Exception as e:
                                    print(f"[ERROR] STEP çıkarma hatası: {e}")
                except Exception as e:
                    print(f"[WARN] EmbeddedFiles yöntemi başarısız: {e}")
                
                # Method 2: Annotations
                try:
                    for page in pdf.pages:
                        annots = page.get("/Annots", [])
                        for annot in annots:
                            try:
                                annot_obj = annot.get_object() if hasattr(annot, 'get_object') else annot
                                if annot_obj.get("/Subtype") == "/FileAttachment":
                                    fs = annot_obj.get("/FS")
                                    if fs:
                                        file_spec = fs.get_object() if hasattr(fs, 'get_object') else fs
                                        file_name = str(file_spec.get("/UF") or file_spec.get("/F") or "").strip("()")
                                        
                                        if file_name.lower().endswith(('.stp', '.step')):
                                            ef = file_spec.get("/EF")
                                            if ef:
                                                file_stream = ef.get("/F")
                                                file_data = file_stream.read_bytes()
                                                output_path = os.path.join("temp", file_name)
                                                os.makedirs("temp", exist_ok=True)
                                                
                                                with open(output_path, 'wb') as f:
                                                    f.write(file_data)
                                                extracted.append(output_path)
                                                print(f"[SUCCESS] Annotation STEP çıkarıldı: {file_name}")
                            except Exception as e:
                                print(f"[WARN] Annotation işleme hatası: {e}")
                                continue
                except Exception as e:
                    print(f"[WARN] Annotations yöntemi başarısız: {e}")
                    
        except Exception as e:
            print(f"[ERROR] PDF STEP çıkarma genel hatası: {e}")
        
        print(f"[INFO] Toplam {len(extracted)} STEP dosyası çıkarıldı")
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
    
    def _calculate_ai_price(self, step_analysis):
        """AI fiyat tahmini"""
        try:
            waste = step_analysis.get("Talaş Hacmi (mm³)", 0)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 0)
            
            roughing_time = waste / 3000  # dakika
            finishing_time = surface / 400
            
            roughing_cost = (roughing_time / 60) * 65
            finishing_cost = (finishing_time / 60) * 120
            
            return {
                "roughing_time_min": round(roughing_time, 1),
                "finishing_time_min": round(finishing_time, 1),
                "roughing_cost_usd": round(roughing_cost, 2),
                "finishing_cost_usd": round(finishing_cost, 2),
                "total_machining_usd": round(roughing_cost + finishing_cost, 2)
            }
        except:
            return {"error": "AI hesaplama hatası"}
    
    def _ensure_materials_exist(self):
        """MongoDB'de malzeme yoksa ekle"""
        try:
            count = self.database.materials.count_documents({})
            if count == 0:
                materials = [
                    {"name": "6061-T6", "aliases": ["6061"], "density": 2.70, "price_per_kg": 4.50},
                    {"name": "7075-T6", "aliases": ["7075"], "density": 2.81, "price_per_kg": 6.20},
                    {"name": "304 Paslanmaz", "aliases": ["304"], "density": 7.93, "price_per_kg": 8.50},
                    {"name": "316 Paslanmaz", "aliases": ["316"], "density": 7.98, "price_per_kg": 12.00}
                ]
                self.database.materials.insert_many(materials)
        except:
            pass


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