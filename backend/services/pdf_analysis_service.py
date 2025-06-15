import os
import re
import tempfile
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from pdf2image import convert_from_path
from pytesseract import image_to_string
import PyPDF2
from fuzzywuzzy import fuzz
from models.material import Material
from models.user import User

class PDFAnalysisService:
    
    @staticmethod
    def extract_text_with_tesseract(pdf_path: str, max_pages: int = 3) -> str:
        """PDF'den OCR ile metin çıkar"""
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, dpi=300)
            if not images:
                return "Hata: PDF'den görüntü elde edilemedi"

            all_text = []
            for i, image in enumerate(images[:2], start=1):
                text = image_to_string(image, lang='tur').strip()
                print(f"\n[OCR Çıktısı] Sayfa {i}:\n{text}\n{'='*80}")
                all_text.append(text)

            combined_text = "\n".join(all_text)
            normalized = PDFAnalysisService._normalize_text(
                PDFAnalysisService._fix_common_misreads(
                    PDFAnalysisService._fix_turkish_chars(combined_text)
                )
            )
            
            return combined_text
        except Exception as e:
            return f"Hata (Tesseract): {str(e)}"
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Metni normalize et"""
        return unicodedata.normalize("NFKC", text).lower()
    
    @staticmethod
    def _fix_turkish_chars(text: str) -> str:
        """Türkçe karakter düzeltmeleri"""
        if not text:
            return ""
        replacements = {
            "C::": "Ç", "G::": "Ğ", "I::": "İ", "O::": "Ö", "S::": "Ş", "U::": "Ü",
            "c::": "ç", "g::": "ğ", "i::": "ı", "o::": "ö", "s::": "ş", "u::": "ü"
        }
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        return text
    
    @staticmethod
    def _fix_common_misreads(text: str) -> str:
        """OCR hata düzeltmeleri"""
        if not text:
            return ""
        misread_map = {
            "l": "1", "O": "0", "I": "1", "B": "8", "S": "5", "Z": "2", "G": "6"
        }
        for wrong, correct in misread_map.items():
            text = re.sub(
                rf"(?<=\b){wrong}(?=\d)|(?<=\d){wrong}(?=\b)|(?<=\d){wrong}(?=\d)", 
                correct, text
            )
        return text
    
    @staticmethod
    def find_all_matches_in_text_block(text_block: str, keyword_list: List[str], alias_map: Dict[str, str]) -> List[str]:
        """Metin bloğunda malzeme eşleşmeleri bul"""
        def normalize_for_match(s):
            s = s.lower().replace("i̇", "i").replace("ı", "i")
            s = unicodedata.normalize("NFKD", s)
            s = "".join(c for c in s if not unicodedata.combining(c))
            return re.sub(r'\W+|\s+', '', s)

        def generate_ngrams(words, n):
            return [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]

        ignore_words = [
            "t6", "t651", "t4", "t5", "t7", "t8", "h112",
            "nyum", "alüminyum", "aluminyum", "aluminium"
        ]

        raw_candidates = re.findall(r"\b([a-zA-Z0-9\-]+)\b", text_block)
        ngrams = raw_candidates + generate_ngrams(raw_candidates, 2) + generate_ngrams(raw_candidates, 3)
        found = []

        for raw in ngrams:
            norm = normalize_for_match(raw)
            if len(norm) < 4 or norm in ignore_words:
                continue

            # Alias kontrolü
            for alias_norm, original_name in alias_map.items():
                if alias_norm in norm or norm in alias_norm:
                    found.append(f"{original_name} (alias: {alias_norm}, %100)")
                    break
            else:
                # Keyword kontrolü
                for keyword in keyword_list:
                    norm_kw = normalize_for_match(keyword)
                    if norm == norm_kw:
                        found.append(f"{keyword} (keyword, %100)")
                        break
                else:
                    # Fuzzy matching
                    best_score = -1
                    best_keyword = None
                    for keyword in keyword_list:
                        score = fuzz.ratio(norm, normalize_for_match(keyword))
                        if score > best_score:
                            best_score = score
                            best_keyword = keyword
                    if best_score >= 85:
                        found.append(f"{best_keyword} (fuzzy, %{best_score})")

        found = list(dict.fromkeys(found)) if found else []
        if any("%100" in match for match in found):
            found = [match for match in found if "%100" in match]
        return found
    
    @staticmethod
    def get_all_material_blocks(text: str) -> Optional[List[Tuple[str, List[str]]]]:
        """Metinden malzeme bloklarını çıkar"""
        text = PDFAnalysisService._normalize_text(
            PDFAnalysisService._fix_common_misreads(
                PDFAnalysisService._fix_turkish_chars(text)
            )
        )

        high_priority_patterns = [
            (r"MALZEME:\s*(.*?)\n", lambda m: text[max(0, m.start(1)-100):m.start(1)+300]),
            (r"\b(malzeme|material|materi̇al)\b[^a-zA-Z0-9]{0,5}(.*?)(?:\n|$)", 
             lambda m: text[max(0, m.start(2)-100):m.start(2)+300]),
            (r"\bmalzeme/material\b\s*[:：]?", lambda m: text[m.end():m.end()+100]),
            (r"\bmalzemesi\b", lambda m: text[m.end():m.end()+100]),
            (r"\bmalzemeden\b", lambda m: text[max(0, m.start()-100):m.start()]),
        ]

        keyword_list, alias_map = Material.get_materials_for_matching()
        all_blocks = []
        
        for pattern, block_func in high_priority_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                block = block_func(match)
                found = PDFAnalysisService.find_all_matches_in_text_block(block, keyword_list, alias_map)
                if found:
                    all_blocks.append((block, found))

        return all_blocks if all_blocks else None
    
    @staticmethod
    def rotate_pdf_90_deg(input_path: str, output_path: str) -> None:
        """PDF'i 90 derece döndür"""
        with open(input_path, "rb") as infile:
            reader = PyPDF2.PdfReader(infile)
            writer = PyPDF2.PdfWriter()

            for page in reader.pages:
                page.rotate(90)
                writer.add_page(page)

            if "/Names" in reader.trailer["/Root"]:
                writer._root_object.update({
                    PyPDF2.generic.NameObject("/Names"): reader.trailer["/Root"]["/Names"]
                })

            with open(output_path, "wb") as outfile:
                writer.write(outfile)
    
    @staticmethod
    def analyze_pdf_file(file_path: str, user_id: str) -> Dict[str, Any]:
        """Tam PDF analizi"""
        try:
            file_name = os.path.basename(file_path)
            name_only = os.path.splitext(file_name)[0]
            working_file = file_path
            matches = []
            rotation_count = 0
            best_block = None

            # 4 defa döndürme denemesi
            for attempt in range(4):
                text = PDFAnalysisService.extract_text_with_tesseract(working_file)
                if not text:
                    continue

                blocks = PDFAnalysisService.get_all_material_blocks(text)

                if blocks:
                    for block_text, found_materials in blocks:
                        found_100 = [m for m in found_materials if "%100" in m]
                        if found_100:
                            # 6061 önceliği
                            if any("6061" in m for m in found_100):
                                matches = [m for m in found_100 if "6061" in m]
                                best_block = block_text
                                break
                            elif not matches:
                                matches = found_100
                                best_block = block_text

                    if matches:
                        matches = list(dict.fromkeys(matches))
                        break

                # Eşleşme yoksa döndür
                temp_rotated = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_rotated.close()
                PDFAnalysisService.rotate_pdf_90_deg(working_file, temp_rotated.name)
                working_file = temp_rotated.name
                rotation_count += 1

            # Temizlik
            if working_file != file_path and os.path.exists(working_file):
                os.unlink(working_file)

            return {
                "success": True,
                "filename": name_only,
                "matches": matches,
                "best_block": best_block,
                "rotation_count": rotation_count,
                "analysis_type": "pdf_ocr"
            }

        except Exception as e:
            return {
                "success": False,
                "filename": name_only if 'name_only' in locals() else "unknown",
                "error": str(e),
                "matches": [],
                "rotation_count": 0
            }
    
    @staticmethod
    def analyze_multiple_pdfs(file_paths: List[str], user_id: str) -> List[Dict[str, Any]]:
        """Birden fazla PDF analizi"""
        results = []
        
        for file_path in file_paths:
            result = PDFAnalysisService.analyze_pdf_file(file_path, user_id)
            results.append(result)
        
        return results
    
    @staticmethod
    def extract_material_names_from_matches(matches: List[str]) -> List[str]:
        """Eşleşmelerden malzeme isimlerini çıkar"""
        material_names = []
        for match in matches:
            # "6061 (alias: ..., %100)" formatından "6061" çıkar
            if "(" in match:
                name = match.split("(")[0].strip()
            else:
                name = match.strip()
            material_names.append(name)
        return list(set(material_names))  # Tekrarları kaldır
    
    @staticmethod
    def calculate_material_costs(matches: List[str], volume_mm3: Optional[float] = None) -> List[Dict[str, Any]]:
        """Malzeme maliyetlerini hesapla"""
        if not matches or not volume_mm3:
            return []
        
        material_names = PDFAnalysisService.extract_material_names_from_matches(matches)
        results = []
        
        for name in material_names:
            material = Material.find_by_name(name)
            if material and material.get('density') and material.get('price_per_kg'):
                # Hacim mm³ -> cm³ -> kg
                volume_cm3 = volume_mm3 / 1000
                mass_kg = (volume_cm3 * material['density']) / 1000
                total_cost = mass_kg * material['price_per_kg']
                
                results.append({
                    "material_name": name,
                    "density": material['density'],
                    "price_per_kg": material['price_per_kg'],
                    "mass_kg": round(mass_kg, 3),
                    "total_cost": round(total_cost, 2)
                })
        
        return results