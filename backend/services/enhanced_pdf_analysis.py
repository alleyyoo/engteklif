# backend/services/enhanced_pdf_analysis.py
# Enhanced PDF Format Detection and Analysis Service
# Bu servis mevcut sistemi bozmadan yeni PDF formatlarını destekler
# SADECE MATERIAL DETECTION'I GELİŞTİRİR - STEP analysis normal akışta kalır

import re
import os
import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class EnhancedPDFFormatDetector:
    """PDF format tespiti ve analiz stratejisi belirleme sınıfı"""
    
    def __init__(self):
        self.format_patterns = {
            "technical_drawing": {
                "keywords": ["çizim", "drawing", "plan", "görünüm", "view", "kesit", "section", "ölçü", "dimension"],
                "layout_features": ["title_block", "dimension_lines", "projection_views"],
                "confidence_threshold": 0.7
            },
            "material_specification": {
                "keywords": ["malzeme", "material", "spec", "özellik", "property", "şartname", "specification"],
                "layout_features": ["table_structure", "specification_list"],
                "confidence_threshold": 0.8
            },
            "assembly_drawing": {
                "keywords": ["montaj", "assembly", "poz", "parça", "part", "liste", "exploded"],
                "layout_features": ["parts_list", "balloon_numbers", "exploded_view"],
                "confidence_threshold": 0.75
            },
            "manufacturing_drawing": {
                "keywords": ["imalat", "manufacturing", "işlem", "process", "tolerans", "tolerance"],
                "layout_features": ["dimension_chains", "tolerance_callouts", "surface_finish"],
                "confidence_threshold": 0.7
            }
        }
        
        logger.info("[ENHANCED-PDF] 🚀 Enhanced PDF Format Detector initialized")
    
    def detect_pdf_format(self, pdf_path: str) -> Dict[str, Any]:
        """PDF formatını tespit et ve analiz stratejisi belirle"""
        try:
            logger.info(f"[PDF-FORMAT] 🔍 Format detection starting: {os.path.basename(pdf_path)}")
            
            # PDF'i görüntüye çevir (ilk sayfa)
            pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
            if not pages:
                return self._get_default_format()
            
            page_image = pages[0]
            
            # Paralel format analizi
            format_scores = {}
            
            # 1. OCR tabanlı text analizi
            text_analysis = self._analyze_text_content(page_image)
            
            # 2. Görsel layout analizi  
            layout_analysis = self._analyze_visual_layout(page_image)
            
            # 3. Geometrik özellik analizi
            geometric_analysis = self._analyze_geometric_features(page_image)
            
            # Her format için skor hesapla
            for format_name, format_config in self.format_patterns.items():
                score = self._calculate_format_score(
                    format_config, text_analysis, layout_analysis, geometric_analysis
                )
                format_scores[format_name] = score
                logger.debug(f"[PDF-FORMAT] 📊 {format_name}: {score:.3f}")
            
            # En yüksek skoru bul
            best_format = max(format_scores.items(), key=lambda x: x[1])
            format_name, confidence = best_format
            
            # Threshold kontrolü
            threshold = self.format_patterns[format_name]["confidence_threshold"]
            if confidence >= threshold:
                detected_format = format_name
                is_confident = True
            else:
                detected_format = "standard_pdf"  # Fallback
                is_confident = False
            
            logger.info(f"[PDF-FORMAT] ✅ Detected: {detected_format} (confidence: {confidence:.3f})")
            
            return {
                "detected_format": detected_format,
                "confidence": confidence,
                "is_confident": is_confident,
                "all_scores": format_scores,
                "analysis_strategy": self._get_analysis_strategy(detected_format),
                "processing_hints": self._get_processing_hints(detected_format, text_analysis, layout_analysis)
            }
            
        except Exception as e:
            logger.error(f"[PDF-FORMAT] ❌ Detection failed: {str(e)}")
            return self._get_default_format()
    
    def _analyze_text_content(self, image: Image.Image) -> Dict[str, Any]:
        """OCR ile text içeriği analizi"""
        try:
            # OCR ile text çıkar
            text = pytesseract.image_to_string(image, lang='tur+eng')
            text_lower = text.lower()
            
            # Keyword analizi
            keyword_matches = {}
            for format_name, config in self.format_patterns.items():
                matches = 0
                for keyword in config["keywords"]:
                    if keyword in text_lower:
                        matches += 1
                keyword_matches[format_name] = matches / len(config["keywords"])
            
            # Text density ve yapısal analiz
            text_density = len(text.strip()) / (image.width * image.height / 10000)
            
            # Sayısal değerler (ölçüler, toleranslar)
            numbers = re.findall(r'\d+[.,]?\d*', text)
            dimension_pattern = re.findall(r'\d+[.,]?\d*\s*[xX×]\s*\d+[.,]?\d*', text)
            tolerance_pattern = re.findall(r'[±]\s*\d+[.,]?\d*', text)
            
            return {
                "keyword_matches": keyword_matches,
                "text_density": text_density,
                "total_numbers": len(numbers),
                "dimension_patterns": len(dimension_pattern),
                "tolerance_patterns": len(tolerance_pattern),
                "text_length": len(text),
                "raw_text": text[:500]  # İlk 500 karakter
            }
            
        except Exception as e:
            logger.warning(f"[PDF-FORMAT] ⚠️ Text analysis failed: {e}")
            return {"keyword_matches": {}, "text_density": 0, "total_numbers": 0}
    
    def _analyze_visual_layout(self, image: Image.Image) -> Dict[str, Any]:
        """Görsel layout yapısını analiz et"""
        try:
            # PIL'den OpenCV'ye çevir
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Line detection (çizim çizgileri)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            line_count = len(lines) if lines is not None else 0
            
            # Contour detection (şekiller, tablolar)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Rectangular shapes (title blocks, tables)
            rectangles = []
            for contour in contours:
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                if len(approx) == 4:  # Rectangle
                    area = cv2.contourArea(contour)
                    if area > 1000:  # Minimum area threshold
                        rectangles.append(contour)
            
            # Title block detection (bottom right corner check)
            h, w = gray.shape
            bottom_right_region = gray[int(h*0.7):h, int(w*0.7):w]
            title_block_lines = cv2.HoughLines(
                cv2.Canny(bottom_right_region, 50, 150), 
                1, np.pi/180, threshold=20
            )
            has_title_block = title_block_lines is not None and len(title_block_lines) > 10
            
            # Table detection (regular patterns)
            horizontal_lines = []
            vertical_lines = []
            if lines is not None:
                for line in lines:
                    rho, theta = line[0]
                    if abs(theta) < 0.1 or abs(theta - np.pi) < 0.1:  # Horizontal
                        horizontal_lines.append(line)
                    elif abs(theta - np.pi/2) < 0.1:  # Vertical
                        vertical_lines.append(line)
            
            has_table_structure = len(horizontal_lines) > 5 and len(vertical_lines) > 3
            
            return {
                "total_lines": line_count,
                "horizontal_lines": len(horizontal_lines),
                "vertical_lines": len(vertical_lines),
                "rectangles": len(rectangles),
                "has_title_block": has_title_block,
                "has_table_structure": has_table_structure,
                "edge_density": np.sum(edges > 0) / edges.size,
                "contour_count": len(contours)
            }
            
        except Exception as e:
            logger.warning(f"[PDF-FORMAT] ⚠️ Layout analysis failed: {e}")
            return {"total_lines": 0, "has_title_block": False, "has_table_structure": False}
    
    def _analyze_geometric_features(self, image: Image.Image) -> Dict[str, Any]:
        """Geometrik özellikler analizi"""
        try:
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Circle detection (teknik çizimde delikler, vidalar)
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, 1, 20,
                param1=50, param2=30, minRadius=5, maxRadius=100
            )
            circle_count = len(circles[0]) if circles is not None else 0
            
            # Dimension line patterns (ok işaretleri)
            # Basit arrow head detection
            kernel_arrow_right = np.array([
                [0, 0, 1],
                [0, 1, 0], 
                [0, 0, 1]
            ], dtype=np.uint8)
            
            edges = cv2.Canny(gray, 50, 150)
            arrow_matches = cv2.matchTemplate(edges, kernel_arrow_right, cv2.TM_CCOEFF_NORMED)
            arrow_count = len(np.where(arrow_matches > 0.6)[0])
            
            # Symmetry analysis (technical drawings tend to be symmetric)
            h, w = gray.shape
            left_half = gray[:, :w//2]
            right_half = cv2.flip(gray[:, w//2:], 1)
            
            # Resize to same size for comparison
            min_width = min(left_half.shape[1], right_half.shape[1])
            left_resized = cv2.resize(left_half, (min_width, h))
            right_resized = cv2.resize(right_half, (min_width, h))
            
            # Calculate similarity
            similarity = cv2.matchTemplate(left_resized, right_resized, cv2.TM_CCOEFF_NORMED)[0, 0]
            
            return {
                "circle_count": circle_count,
                "arrow_count": arrow_count,
                "symmetry_score": float(similarity),
                "geometric_complexity": circle_count + arrow_count,
                "has_geometric_features": circle_count > 0 or arrow_count > 2
            }
            
        except Exception as e:
            logger.warning(f"[PDF-FORMAT] ⚠️ Geometric analysis failed: {e}")
            return {"circle_count": 0, "arrow_count": 0, "symmetry_score": 0}
    
    def _calculate_format_score(self, format_config: Dict, text_analysis: Dict, 
                              layout_analysis: Dict, geometric_analysis: Dict) -> float:
        """Format skoru hesapla"""
        try:
            score = 0.0
            
            # 1. Keyword matching (40% weight)
            format_name = None
            for name, config in self.format_patterns.items():
                if config == format_config:
                    format_name = name
                    break
            
            if format_name:
                keyword_score = text_analysis["keyword_matches"].get(format_name, 0)
                score += keyword_score * 0.4
            
            # 2. Layout features (35% weight)
            layout_score = 0
            feature_count = 0
            
            if "title_block" in format_config["layout_features"]:
                layout_score += 1 if layout_analysis["has_title_block"] else 0
                feature_count += 1
            
            if "table_structure" in format_config["layout_features"]:
                layout_score += 1 if layout_analysis["has_table_structure"] else 0
                feature_count += 1
            
            if "dimension_lines" in format_config["layout_features"]:
                # Dimension lines = many horizontal/vertical lines + arrows
                has_dimension_lines = (
                    layout_analysis["horizontal_lines"] > 10 and 
                    layout_analysis["vertical_lines"] > 5 and
                    geometric_analysis["arrow_count"] > 2
                )
                layout_score += 1 if has_dimension_lines else 0
                feature_count += 1
            
            if feature_count > 0:
                score += (layout_score / feature_count) * 0.35
            
            # 3. Content analysis (25% weight)
            content_score = 0
            
            # Format-specific content scoring
            if format_name == "technical_drawing":
                # Technical drawings have moderate text density
                ideal_density = 0.5
                density_score = 1 - abs(text_analysis["text_density"] - ideal_density) / max(ideal_density, 0.1)
                content_score += max(0, density_score) * 0.5
                
                # Should have dimensions and tolerances
                if text_analysis["dimension_patterns"] > 0:
                    content_score += 0.3
                if text_analysis["tolerance_patterns"] > 0:
                    content_score += 0.2
            
            elif format_name == "material_specification":
                # Material specs have high text density
                if text_analysis["text_density"] > 1.0:
                    content_score += 0.4
                if text_analysis["total_numbers"] > 10:
                    content_score += 0.3
                if layout_analysis["has_table_structure"]:
                    content_score += 0.3
            
            score += content_score * 0.25
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.warning(f"[PDF-FORMAT] ⚠️ Score calculation failed: {e}")
            return 0.0
    
    def _get_analysis_strategy(self, detected_format: str) -> Dict[str, Any]:
        """Format'a göre analiz stratejisi döndür"""
        strategies = {
            "technical_drawing": {
                "primary_focus": "dimensional_analysis",
                "ocr_regions": ["title_block", "dimension_text", "notes"],
                "material_detection": "secondary",
                "step_extraction": "primary",
                "processing_order": ["step_extraction", "dimensional_analysis", "material_detection"]
            },
            "material_specification": {
                "primary_focus": "material_analysis",
                "ocr_regions": ["specification_tables", "material_properties", "full_document"],
                "material_detection": "primary",
                "step_extraction": "none",
                "processing_order": ["material_analysis", "property_extraction", "specification_parsing"]
            },
            "assembly_drawing": {
                "primary_focus": "component_analysis",
                "ocr_regions": ["parts_list", "balloon_numbers", "assembly_notes"],
                "material_detection": "secondary",
                "step_extraction": "secondary",
                "processing_order": ["component_identification", "step_extraction", "material_analysis"]
            },
            "manufacturing_drawing": {
                "primary_focus": "process_analysis",
                "ocr_regions": ["process_notes", "tolerance_callouts", "surface_finish"],
                "material_detection": "primary",
                "step_extraction": "primary",
                "processing_order": ["process_analysis", "tolerance_extraction", "material_analysis"]
            },
            "standard_pdf": {
                "primary_focus": "general_analysis",
                "ocr_regions": ["full_document"],
                "material_detection": "primary",
                "step_extraction": "primary",
                "processing_order": ["step_extraction", "material_analysis", "general_ocr"]
            }
        }
        
        return strategies.get(detected_format, strategies["standard_pdf"])
    
    def _get_processing_hints(self, detected_format: str, text_analysis: Dict, layout_analysis: Dict) -> Dict[str, Any]:
        """İşleme ipuçları döndür"""
        hints = {
            "ocr_settings": {
                "language": "tur+eng",
                "psm": 6,  # Default
                "confidence_threshold": 60
            },
            "material_search_zones": [],
            "step_search_priority": "embedded_files",
            "rotation_needed": False,
            "preprocessing_filters": []
        }
        
        if detected_format == "technical_drawing":
            hints.update({
                "ocr_settings": {"psm": 11, "confidence_threshold": 70},  # Sparse text
                "material_search_zones": ["title_block", "notes_area"],
                "rotation_needed": layout_analysis.get("symmetry_score", 0) < 0.3,
                "preprocessing_filters": ["noise_reduction", "line_enhancement"]
            })
        
        elif detected_format == "material_specification":
            hints.update({
                "ocr_settings": {"psm": 6, "confidence_threshold": 80},  # Dense text
                "material_search_zones": ["full_document", "tables"],
                "preprocessing_filters": ["contrast_enhancement", "text_sharpening"]
            })
        
        return hints
    
    def _get_default_format(self) -> Dict[str, Any]:
        """Varsayılan format bilgisi"""
        return {
            "detected_format": "standard_pdf",
            "confidence": 0.5,
            "is_confident": False,
            "all_scores": {},
            "analysis_strategy": self._get_analysis_strategy("standard_pdf"),
            "processing_hints": self._get_processing_hints("standard_pdf", {}, {})
        }


class EnhancedPDFAnalyzer:
    """Geliştirilmiş PDF analiz sınıfı - SADECE MATERIAL DETECTION İÇİN"""
    
    def __init__(self):
        self.format_detector = EnhancedPDFFormatDetector()
        logger.info("[ENHANCED-PDF] 🚀 Enhanced PDF Analyzer initialized")
    
    def analyze_pdf_enhanced(self, file_path: str, file_type: str, user_id: str) -> Dict[str, Any]:
        """
        SADECE FORMAT VE MATERIAL DETECTION - STEP analysis'i normal akışa bırak
        """
        try:
            logger.info(f"[ENHANCED-PDF] 🔍 Enhanced material detection: {os.path.basename(file_path)}")
            
            # 1. Format detection
            format_info = self.format_detector.detect_pdf_format(file_path)
            detected_format = format_info["detected_format"]
            
            logger.info(f"[ENHANCED-PDF] 📋 Detected format: {detected_format}")
            
            # 2. SADECE format-specific material enhancements
            enhanced_result = self._apply_format_specific_enhancements(
                {}, format_info, file_path  # Boş base_result - sadece enhancement
            )
            
            # 3. Minimal result - STEP analysis yapmıyoruz
            final_result = {
                "format_detection": {
                    "detected_format": format_info["detected_format"],
                    "confidence": format_info["confidence"],
                    "is_confident": format_info["is_confident"],
                    "analysis_strategy_used": format_info["analysis_strategy"]["primary_focus"]
                },
                "processing_log": [
                    f"🔍 Format detected: {detected_format}",
                    f"🔍 Confidence: {format_info['confidence']:.2f}"
                ]
            }
            
            # Enhanced materials varsa ekle
            if enhanced_result.get("format_specific_materials"):
                final_result["material_matches"] = enhanced_result["format_specific_materials"]
                final_result["processing_log"].append(f"🔍 Enhanced materials: {len(enhanced_result['format_specific_materials'])}")
            
            # Enhanced processing notes
            if enhanced_result.get("processing_notes"):
                final_result["processing_log"].extend(enhanced_result["processing_notes"])
            
            logger.info(f"[ENHANCED-PDF] ✅ Enhanced material detection completed")
            return final_result
            
        except Exception as e:
            logger.error(f"[ENHANCED-PDF] ❌ Enhanced material detection failed: {str(e)}")
            return {"error": f"Enhanced material detection failed: {str(e)}"}
    
    def _apply_format_specific_enhancements(self, base_result: Dict, format_info: Dict, file_path: str) -> Dict[str, Any]:
        """Format'a özel geliştirmeler uygula - SADECE MATERIAL İÇİN"""
        try:
            detected_format = format_info["detected_format"]
            
            enhancements = {
                "format_specific_materials": [],
                "enhanced_step_analysis": {},
                "format_confidence": format_info["confidence"],
                "processing_notes": []
            }
            
            if detected_format == "technical_drawing":
                enhancements.update(self._enhance_technical_drawing_analysis(base_result, file_path))
            
            elif detected_format == "material_specification":
                enhancements.update(self._enhance_material_specification_analysis(base_result, file_path))
            
            elif detected_format == "assembly_drawing":
                enhancements.update(self._enhance_assembly_drawing_analysis(base_result, file_path))
            
            elif detected_format == "manufacturing_drawing":
                enhancements.update(self._enhance_manufacturing_drawing_analysis(base_result, file_path))
            
            return enhancements
            
        except Exception as e:
            logger.warning(f"[ENHANCED-PDF] ⚠️ Format-specific enhancement failed: {e}")
            return {"format_specific_materials": [], "processing_notes": [f"Enhancement failed: {str(e)}"]}
    
    def _enhance_technical_drawing_analysis(self, base_result: Dict, file_path: str) -> Dict[str, Any]:
        """Teknik çizim analizi geliştirmeleri - SADECE MATERIAL"""
        try:
            logger.info("[ENHANCED-PDF] 📐 Applying technical drawing enhancements...")
            
            enhancements = {
                "format_specific_materials": [],
                "processing_notes": ["Applied technical drawing analysis"]
            }
            
            # Teknik çizimlerde title block'tan material bilgisi çıkar
            pages = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
            if pages:
                page = pages[0]
                
                # Title block region (bottom-right corner)
                width, height = page.size
                title_block = page.crop((
                    int(width * 0.6), int(height * 0.7),
                    width, height
                ))
                
                # OCR on title block
                title_text = pytesseract.image_to_string(title_block, lang='tur+eng')
                
                # Material pattern matching for technical drawings
                material_patterns = [
                    r'MALZEME[:\s]*([A-Z0-9\-\s]+)',
                    r'MATERIAL[:\s]*([A-Z0-9\-\s]+)',
                    r'([A-Z]*\d{4}[A-Z]*)',  # Alloy numbers
                    r'(St\s*\d+)',  # Steel grades
                    r'(S\d{3})',   # Steel designations
                    r'(6061[\-\s]*[A-Z]\d*)',  # Aluminum alloys
                    r'(7075[\-\s]*[A-Z]\d*)',  # Aluminum alloys
                    r'(2024[\-\s]*[A-Z]\d*)',  # Aluminum alloys
                ]
                
                found_materials = []
                for pattern in material_patterns:
                    matches = re.findall(pattern, title_text, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, str) and len(match.strip()) > 1:
                            clean_match = re.sub(r'\s+', ' ', match.strip())
                            found_materials.append(f"{clean_match} (technical_drawing_source, %95)")
                
                # Full page OCR for additional materials
                full_text = pytesseract.image_to_string(page, lang='tur+eng')
                
                # Additional technical drawing patterns
                additional_patterns = [
                    r'(?:NORM|STANDARD)[\s:]*([A-Z0-9\.\-\s]{5,25})',
                    r'(EN\s*\d+)',  # European standards
                    r'(DIN\s*\d+)',  # German standards
                    r'(ASTM\s*[A-Z]?\d+)',  # ASTM standards
                ]
                
                for pattern in additional_patterns:
                    matches = re.findall(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        clean_match = re.sub(r'\s+', ' ', match.strip())
                        if len(clean_match) >= 3:
                            found_materials.append(f"{clean_match} (technical_standard, %90)")
                
                if found_materials:
                    # Remove duplicates
                    unique_materials = []
                    seen = set()
                    for material in found_materials:
                        material_clean = material.split('(')[0].strip().lower()
                        if material_clean not in seen:
                            seen.add(material_clean)
                            unique_materials.append(material)
                    
                    enhancements["format_specific_materials"] = unique_materials[:5]  # Limit to 5
                    enhancements["processing_notes"].append(f"Found {len(unique_materials)} materials in technical drawing")
            
            return enhancements
            
        except Exception as e:
            logger.warning(f"[ENHANCED-PDF] ⚠️ Technical drawing enhancement failed: {e}")
            return {"format_specific_materials": [], "processing_notes": [f"Technical enhancement failed: {str(e)}"]}
    
    def _enhance_material_specification_analysis(self, base_result: Dict, file_path: str) -> Dict[str, Any]:
        """Malzeme şartnamesi analizi geliştirmeleri"""
        try:
            logger.info("[ENHANCED-PDF] 📋 Applying material specification enhancements...")
            
            # Material specification documents have detailed material info
            pages = convert_from_path(file_path, dpi=250, first_page=1, last_page=2)
            
            enhanced_materials = []
            
            for i, page in enumerate(pages):
                # High-quality OCR for specifications
                text = pytesseract.image_to_string(page, lang='tur+eng', config='--psm 6')
                
                # Detailed material patterns for specifications
                spec_patterns = [
                    r'(?:MALZEME|MATERIAL)[\s:]*([A-Z0-9\-T\s]{3,20})',
                    r'(?:NORM|STANDARD)[\s:]*([A-Z0-9\.\-\s]{5,25})',
                    r'(?:KALİTE|GRADE|QUALITY)[\s:]*([A-Z0-9\-\s]{2,15})',
                    r'(\d{4}[\-\s]*[A-Z]\d+)',  # Aluminum alloys like 6061-T6
                    r'(EN\s*\d+)',  # European standards
                    r'(DIN\s*\d+)',  # German standards
                    r'(ASTM\s*[A-Z]?\d+)',  # ASTM standards
                    r'(S\d{3})',  # Steel grades
                    r'(St\s*\d+)',  # Steel grades
                ]
                
                for pattern in spec_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        clean_match = re.sub(r'\s+', ' ', match.strip())
                        if len(clean_match) >= 3:
                            enhanced_materials.append(f"{clean_match} (specification_source, %90)")
            
            # Remove duplicates
            unique_materials = []
            seen = set()
            for material in enhanced_materials:
                material_clean = material.split('(')[0].strip().lower()
                if material_clean not in seen:
                    seen.add(material_clean)
                    unique_materials.append(material)
            
            return {
                "format_specific_materials": unique_materials[:8],  # Limit to 8
                "processing_notes": [f"Material specification analysis: {len(unique_materials)} materials found"]
            }
            
        except Exception as e:
            logger.warning(f"[ENHANCED-PDF] ⚠️ Material specification enhancement failed: {e}")
            return {"format_specific_materials": [], "processing_notes": [f"Specification enhancement failed: {str(e)}"]}
    
    def _enhance_assembly_drawing_analysis(self, base_result: Dict, file_path: str) -> Dict[str, Any]:
        """Montaj çizimi analizi geliştirmeleri"""
        try:
            logger.info("[ENHANCED-PDF] 🔧 Applying assembly drawing enhancements...")
            
            # Assembly drawings may have parts lists with materials
            pages = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
            
            if pages:
                page = pages[0]
                text = pytesseract.image_to_string(page, lang='tur+eng')
                
                # Look for parts list patterns
                parts_patterns = [
                    r'(?:POS|POZ)[\s]*(\d+)[\s]*([A-Z0-9\-\s]+)[\s]*([A-Z0-9\-\s]*)',
                    r'(\d+)[\s]*ADET[\s]*([A-Z0-9\-\s]+)',
                    r'PARÇA[\s]*([A-Z0-9\-\s]+)[\s]*([A-Z0-9\-\s]*)',
                    r'(\d{4}[\-\s]*[A-Z]\d*)',  # Material codes in parts list
                ]
                
                assembly_materials = []
                for pattern in parts_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            for part in match:
                                part_clean = part.strip()
                                if len(part_clean) > 2 and any(c.isalnum() for c in part_clean):
                                    # Check if it looks like a material
                                    if any(char.isdigit() for char in part_clean) and len(part_clean) >= 4:
                                        assembly_materials.append(f"{part_clean} (assembly_parts_list, %80)")
                        else:
                            part_clean = match.strip()
                            if len(part_clean) > 2 and any(c.isalnum() for c in part_clean):
                                assembly_materials.append(f"{part_clean} (assembly_parts_list, %80)")
                
                # Remove duplicates
                unique_materials = []
                seen = set()
                for material in assembly_materials:
                    material_clean = material.split('(')[0].strip().lower()
                    if material_clean not in seen:
                        seen.add(material_clean)
                        unique_materials.append(material)
                
                return {
                    "format_specific_materials": unique_materials[:5],  # Limit to 5
                    "processing_notes": [f"Assembly analysis: {len(unique_materials)} parts identified"]
                }
            
            return {"format_specific_materials": [], "processing_notes": ["Assembly analysis completed"]}
            
        except Exception as e:
            logger.warning(f"[ENHANCED-PDF] ⚠️ Assembly enhancement failed: {e}")
            return {"format_specific_materials": [], "processing_notes": [f"Assembly enhancement failed: {str(e)}"]}
    
    def _enhance_manufacturing_drawing_analysis(self, base_result: Dict, file_path: str) -> Dict[str, Any]:
        """İmalat çizimi analizi geliştirmeleri"""
        try:
            logger.info("[ENHANCED-PDF] ⚚ Applying manufacturing drawing enhancements...")
            
            # Manufacturing drawings focus on processes and materials
            pages = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
            
            if pages:
                page = pages[0]
                text = pytesseract.image_to_string(page, lang='tur+eng')
                
                # Manufacturing-specific patterns
                manufacturing_patterns = [
                    r'(?:İŞLEM|PROCESS)[\s]*([A-Z0-9\-\s]+)',
                    r'(?:YÜZEYİNDE|SURFACE)[\s]*([A-Z0-9\-\s]+)',
                    r'(?:KAPLAMA|COATING)[\s]*([A-Z0-9\-\s]+)',
                    r'(?:ISIL|HEAT)[\s]*(?:İŞLEM|TREATMENT)[\s]*([A-Z0-9\-\s]+)',
                    r'(?:MALZEME|MATERIAL)[\s]*([A-Z0-9\-\s]+)',
                    r'(\d{4}[\-\s]*[A-Z]\d*)',  # Material codes
                ]
                
                manufacturing_materials = []
                for pattern in manufacturing_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        clean_match = re.sub(r'\s+', ' ', match.strip())
                        if len(clean_match) > 2:
                            manufacturing_materials.append(f"{clean_match} (manufacturing_process, %85)")
                
                # Remove duplicates
                unique_materials = []
                seen = set()
                for material in manufacturing_materials:
                    material_clean = material.split('(')[0].strip().lower()
                    if material_clean not in seen:
                        seen.add(material_clean)
                        unique_materials.append(material)
                
                return {
                    "format_specific_materials": unique_materials[:6],  # Limit to 6
                    "processing_notes": [f"Manufacturing analysis: {len(unique_materials)} process materials found"]
                }
            
            return {"format_specific_materials": [], "processing_notes": ["Manufacturing analysis completed"]}
            
        except Exception as e:
            logger.warning(f"[ENHANCED-PDF] ⚠️ Manufacturing enhancement failed: {e}")
            return {"format_specific_materials": [], "processing_notes": [f"Manufacturing enhancement failed: {str(e)}"]}


# Integration functions - mevcut sisteme entegrasyon
def get_enhanced_pdf_analyzer():
    """Enhanced PDF analyzer instance döndür"""
    return EnhancedPDFAnalyzer()


def should_use_enhanced_analysis(file_path: str) -> bool:
    """Enhanced analiz kullanılıp kullanılmayacağını belirle"""
    try:
        # Dosya boyutu ve tip kontrolü
        if not os.path.exists(file_path):
            return False
            
        file_size = os.path.getsize(file_path)
        
        # Küçük dosyalar için enhanced analiz kullanma (performans)
        if file_size > 10 * 1024 * 1024:  # 10MB'dan büyükse
            logger.info(f"[ENHANCED-CHECK] 📁 File too large for enhanced analysis: {file_size / (1024*1024):.1f}MB")
            return False
        
        # Quick format check
        try:
            detector = EnhancedPDFFormatDetector()
            format_info = detector.detect_pdf_format(file_path)
            
            # Eğer confident detection varsa enhanced kullan
            use_enhanced = format_info["is_confident"]
            
            logger.info(f"[ENHANCED-CHECK] 🎯 Enhanced analysis decision: {use_enhanced} "
                       f"(format: {format_info['detected_format']}, confidence: {format_info['confidence']:.2f})")
            
            return use_enhanced
        except Exception as detection_error:
            logger.warning(f"[ENHANCED-CHECK] ⚠️ Format detection failed: {detection_error}")
            return False
        
    except Exception as e:
        logger.warning(f"[ENHANCED-CHECK] ⚠️ Enhanced check failed: {e}")
        return False


# Main enhanced analysis function
def analyze_pdf_with_enhanced_detection(file_path: str, file_type: str = 'pdf', user_id: str = None) -> Dict[str, Any]:
    """
    Main function for enhanced PDF analysis
    Can be used as a standalone function or integrated into existing workflow
    """
    try:
        if should_use_enhanced_analysis(file_path):
            analyzer = get_enhanced_pdf_analyzer()
            return analyzer.analyze_pdf_enhanced(file_path, file_type, user_id)
        else:
            # Fallback to standard analysis
            logger.info("[ENHANCED-MAIN] 📄 Using fallback standard analysis")
            return {
                "material_matches": ["Unknown (standard_fallback)"],
                "processing_log": ["Standard fallback analysis"],
                "format_detection": {
                    "detected_format": "standard_pdf",
                    "confidence": 0.5,
                    "is_confident": False,
                    "analysis_strategy_used": "fallback"
                }
            }
    except Exception as e:
        logger.error(f"[ENHANCED-MAIN] ❌ Enhanced analysis failed: {e}")
        return {
            "error": f"Enhanced analysis failed: {str(e)}",
            "material_matches": [],
            "processing_log": [f"Error: {str(e)}"]
        }