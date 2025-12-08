# services/material_analysis.py - COMPLETE ENHANCED VERSION WITH GLOBAL TIMEOUT

import re
import os
import time
import pytesseract
import cadquery as cq
from cadquery import exporters # Import exporters explicitly
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
import cv2
import json
from PIL import Image, ImageDraw, ImageEnhance

# Optimized imports
try:
    from w_db_pdf_v2 import (
        get_keywords_from_db,
        extract_text_with_tesseract as advanced_extract_text_from_pdf,
        get_all_material_blocks,
        find_all_matches_in_text_block,
        rotate_pdf_90_deg
    )
    ADVANCED_OCR_AVAILABLE = True
    print("[MATERIAL-ANALYSIS] Advanced OCR available (speed optimized)")
except ImportError:
    ADVANCED_OCR_AVAILABLE = False
    print("[MATERIAL-ANALYSIS] Advanced OCR not available")

try:
    from scipy.spatial.transform import Rotation
    from scipy.spatial import ConvexHull
    from sklearn.decomposition import PCA
    SCIPY_AVAILABLE = True
    print("[MATERIAL-ANALYSIS] Advanced geometric analysis available")
except ImportError:
    SCIPY_AVAILABLE = False
    print("[MATERIAL-ANALYSIS] Advanced geometric analysis disabled")

try:
    from .enhanced_pdf_analysis import (
        should_use_enhanced_analysis, 
        get_enhanced_pdf_analyzer,
        EnhancedPDFFormatDetector
    )
    ENHANCED_PDF_AVAILABLE = True
    print("[MATERIAL-ANALYSIS] Enhanced PDF analysis available")
except ImportError:
    ENHANCED_PDF_AVAILABLE = False
    print("[MATERIAL-ANALYSIS] Enhanced PDF analysis not available")

print("[INFO] Enhanced Material Analysis Service - PRIORITIZED DETECTION")

# =====================================================
# OCR OPTIMIZATION WITH GLOBAL TIMEOUT
# =====================================================

def optimize_image_for_ocr_lightning(image):
    """Lightning-fast image optimization for OCR"""
    try:
        if image.mode != 'L':
            image = image.convert('L')
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        return image
        
    except Exception as e:
        print(f"[OCR-OPTIMIZE] Image optimization failed: {e}")
        return image

def extract_text_with_lightning_ocr(pdf_path, global_start_time=None, timeout=60):
    """
    Enhanced OCR with GLOBAL TIMEOUT protection.
    Checks elapsed time against the global start time.
    """
    try:
        # Eğer global start time verilmemişse, şu anı başlangıç kabul et
        if global_start_time is None:
            global_start_time = time.time()
            
        def check_timeout(stage="unknown"):
            elapsed = time.time() - global_start_time
            if elapsed > timeout:
                print(f"[OCR-ENHANCED] ⏱️ GLOBAL TIMEOUT reached at {stage} ({elapsed:.2f}s > {timeout}s). Stopping.")
                return True
            return False

        if check_timeout("start"):
            return ""

        print(f"[OCR-ENHANCED] Starting OCR (Time elapsed so far: {time.time() - global_start_time:.2f}s)...")
        
        # METHOD 1: Enhanced Tesseract (First Page - Most Critical)
        try:
            print("[OCR-ENHANCED] Method 1: Enhanced Tesseract for technical drawings...")
            # Bu işlem bloklayıcıdır, timeout veremeyiz ama bitince kontrol ederiz
            pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            
            if check_timeout("after_convert_from_path"):
                return ""

            if pages:
                # Hızlıdan yavaşa sıralı konfigürasyonlar
                configs = [
                    '--psm 6 --oem 3',  # Standard (Hızlı ve Genelde İyi)
                    '--psm 3 --oem 3',  # Auto
                    '--psm 4 --oem 3',  # Column
                ]
                
                best_text = ""
                
                for config in configs:
                    if check_timeout(f"before_config_{config}"):
                        return best_text if len(best_text) > 50 else ""

                    try:
                        t0 = time.time()
                        text = pytesseract.image_to_string(pages[0], lang='eng+tur', config=config)
                        duration = time.time() - t0
                        text_len = len(text.strip())
                        
                        print(f"[OCR-ENHANCED] Config '{config}': {text_len} chars ({duration:.2f}s)")
                        
                        # OPTİMİZASYON: Yeterli metin varsa diğerlerini deneme
                        if text_len > 500:
                            print(f"[OCR-ENHANCED] ✅ Sufficient text found ({text_len} chars), skipping others.")
                            return text
                            
                        if text_len > len(best_text):
                            best_text = text
                    except:
                        continue
                
                if best_text and len(best_text.strip()) > 50:
                    print(f"[OCR-ENHANCED] Enhanced Tesseract success: {len(best_text)} chars")
                    return best_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Enhanced Tesseract failed: {e}")
        
        # METHOD 2: Image preprocessing + OCR (First Page)
        if check_timeout("before_method_2"):
            return ""

        try:
            print("[OCR-ENHANCED] Method 2: Preprocessed image OCR...")
            pages = convert_from_path(pdf_path, dpi=600, first_page=1, last_page=1)
            
            if check_timeout("after_convert_method_2"):
                return ""

            if pages:
                image = optimize_image_for_ocr_lightning(pages[0])
                text = pytesseract.image_to_string(image, lang='eng+tur', config='--psm 6 --oem 3')
                
                if text and len(text.strip()) > 50:
                    print(f"[OCR-ENHANCED] Preprocessed OCR success: {len(text)} chars")
                    return text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Preprocessed OCR failed: {e}")
        
        # METHOD 3: PyPDF2 fallback (Very Fast but tried last if others fail/timeout)
        # Aslında PyPDF2 en hızlısıdır, ama OCR gerektiren (resim bazlı) PDF'lerde işe yaramaz.
        # Bu aşamaya geldiysek OCR başarısız olmuştur veya timeout'a yaklaşıyoruzdur.
        
        if check_timeout("before_method_3"):
            return ""

        # METHOD 4: All Pages Scan (Last Resort)
        # Bu çok uzun sürer, timeout riski varsa hiç girmeyelim
        elapsed = time.time() - global_start_time
        if elapsed > (timeout * 0.8): # Eğer sürenin %80'ini yediysek buna hiç girme
            print(f"[OCR-ENHANCED] ⏱️ Low time ({elapsed:.2f}s), skipping full page scan.")
            return ""

        try:
            print("[OCR-ENHANCED] Method 4: Scanning ALL pages (Last Resort)...")
            pages = convert_from_path(pdf_path, dpi=200) # DPI düşürüldü hız için
            all_text = ""
            
            for page_num, page_image in enumerate(pages):
                if check_timeout(f"page_{page_num}"):
                    break

                try:
                    page_text = pytesseract.image_to_string(page_image, lang='eng+tur', config='--psm 6')
                    if page_text:
                        all_text += f"\n--- PAGE {page_num + 1} ---\n" + page_text
                except:
                    continue
            
            if all_text and len(all_text.strip()) > 20:
                print(f"[OCR-ENHANCED] All pages total: {len(all_text)} chars")
                return all_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] All pages scan failed: {e}")
        
        print(f"[OCR-ENHANCED] All OCR methods failed or timed out")
        return ""
        
    except Exception as e:
        print(f"[OCR-ENHANCED] OCR fatal error: {e}")
        return ""

# ... (Previous helper functions like apply_6061_priority_to_materials, extract_explicit_material_fields etc. remain unchanged) ...
# ... (Assuming they are present in the file context) ...

def apply_6061_priority_to_materials(material_list):
    if not material_list: return material_list
    material_6061_found = []
    other_materials = []
    for material in material_list:
        material_text = ""
        if isinstance(material, dict):
            material_text = (material.get('material_name', '') + ' ' + material.get('keyword', '')).upper()
        else:
            material_text = str(material).upper()
        if any(pattern in material_text for pattern in ['6061', 'AL 6061', 'AA6061', 'AL6061', 'AA 6061']):
            material_6061_found.append(material)
        else:
            other_materials.append(material)
    if material_6061_found:
        return material_6061_found[:1]
    return material_list

def extract_material_keywords_lightning(text):
    if not text or len(text.strip()) < 3: return []
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials: return explicit_materials[:5]
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials: return notlar_materials[:5]
    material_keywords = extract_material_keywords_from_text_fixed(text)
    if material_keywords:
        filtered_keywords = filter_out_part_descriptions(material_keywords, text)
        return filtered_keywords[:5]
    return []

def extract_explicit_material_fields(text):
    if not text: return []
    explicit_patterns = [
        r'(?:^|\n)\s*MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,]{2,100})',
        r'(?:^|\n)\s*MATERIAL\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,]{2,100})',
        r'MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,]{2,100})(?:\n|$)',
        r'MATERIAL\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,]{2,100})(?:\n|$)',
        r'\d+[-\.]\s{0,5}MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,VEYA]{2,100})',
        r'MALZEME\s{0,5}[/\\]\s{0,5}STANDART\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/,]{2,100})',
        r'5[-\.]\s{0,5}MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/T,]{2,100})',
        r'MALZEME\s{0,10}[:]\s{0,10}(.{1,200})',
    ]
    found_materials = []
    text_upper = text.upper()
    for pattern_idx, pattern in enumerate(explicit_patterns):
        try:
            matches = re.finditer(pattern, text_upper, re.MULTILINE | re.DOTALL)
            for match in matches:
                if match.group(1):
                    material_content = match.group(1).strip()
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text_upper), match.end() + 100)
                    context = text_upper[start_pos:end_pos]
                    multiple_materials = []
                    if 'VEYA' in material_content or 'OR' in material_content:
                        parts = re.split(r'\s+(?:VEYA|OR)\s+', material_content)
                        for part in parts:
                            sub_parts = part.split(',')
                            for sub_part in sub_parts:
                                sub_part = sub_part.strip()
                                if sub_part and len(sub_part) > 2: multiple_materials.append(sub_part)
                    elif ',' in material_content:
                        parts = material_content.split(',')
                        for part in parts:
                            part = part.strip()
                            if part and len(part) > 2: multiple_materials.append(part)
                    else: multiple_materials = [material_content]
                    for material_item in multiple_materials:
                        stop_words = ['ISLEMLER', 'ISLEM', 'NOTLAR', 'NOTE', 'TOLERANS', 'OLCU', 'BOLGE', 'ZONE', 'SAYFA', 'PAGE', 'REV', 'TARIH', 'DATE', 'MATERIAL']
                        for stop_word in stop_words:
                            if stop_word in material_item: material_item = material_item.split(stop_word)[0].strip()
                        material_patterns = [
                            r'(AL\s+7075[-\s]*T\d+)', r'(AL\s+6061[-\s]*T\d+)', r'(AL\s+2024[-\s]*T\d+)',
                            r'(AA\s+\d{4}[-\s]*T\d+)', r'(\d{4}[-\s]*T\d+)', r'(AISI\s*\d{3}[A-Z]?)', r'([A-Z0-9]{2,15})',
                        ]
                        extracted_material = None
                        for mat_pattern in material_patterns:
                            mat_match = re.search(mat_pattern, material_item)
                            if mat_match:
                                extracted_material = mat_match.group(1).strip()
                                break
                        if not extracted_material: extracted_material = re.sub(r'[^\w\-\+\s]+', ' ', material_item[:20]).strip()
                        if len(extracted_material) >= 2:
                            if not is_part_description(extracted_material, text_upper, match.start()):
                                resolved_material = resolve_material_from_database(extracted_material)
                                if resolved_material:
                                    found_materials.append({
                                        'keyword': extracted_material, 'material_name': resolved_material, 'position': match.start(),
                                        'confidence': 99, 'pattern_type': 'explicit_material_field', 'source': 'MALZEME: field',
                                        'pattern_index': pattern_idx, 'context': context
                                    })
                                else:
                                    if '6061' in extracted_material or '7075' in extracted_material:
                                        if '6061' in extracted_material: resolved_material = '6061'
                                        elif '7075' in extracted_material: resolved_material = '7075'
                                        else: resolved_material = extracted_material
                                        found_materials.append({
                                            'keyword': extracted_material, 'material_name': resolved_material, 'position': match.start(),
                                            'confidence': 99, 'pattern_type': 'explicit_material_field', 'source': 'MALZEME: field',
                                            'pattern_index': pattern_idx, 'context': context
                                        })
                    if found_materials and any('6061' in str(m.get('material_name', '')).upper() for m in found_materials):
                        found_materials = apply_6061_priority_to_materials(found_materials)
                        return found_materials
        except re.error: continue
    if found_materials: found_materials = apply_6061_priority_to_materials(found_materials)
    return found_materials

def is_part_description(material_text, full_text, position):
    part_indicators = ['TANIM', 'NOMENCLATURE', 'DESCRIPTION', 'TITLE', 'PARÇA', 'PART', 'KAPAMA', 'SULUK', 'ASSEMBLY']
    context_start = max(0, position - 100)
    context_end = min(len(full_text), position + 100)
    context = full_text[context_start:context_end].upper()
    for indicator in part_indicators:
        if indicator in context:
            if position > 0 and full_text[max(0, position-10):position].strip().endswith('MALZEME:'): return False
            return True
    return False

def filter_out_part_descriptions(keywords, text):
    filtered = []
    text_upper = text.upper()
    for keyword_info in keywords:
        keyword = keyword_info.get('keyword', '')
        position = keyword_info.get('position', 0)
        if is_part_description(keyword, text_upper, position):
            keyword_info['confidence'] = max(keyword_info.get('confidence', 50) - 30, 20)
            keyword_info['pattern_type'] = 'part_description_low_confidence'
        filtered.append(keyword_info)
    filtered.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    return filtered

def extract_technical_drawing_fields(text):
    if not text: return {}
    explicit_fields = {}
    text_upper = text.upper()
    explicit_patterns = [
        r'(?:^|\n)\s*MALZEME\s*[:]\s*([A-Z0-9\s\-\+\.\/]{2,50})',
        r'MALZEME\s*[:]\s*([A-Z0-9\s\-\+\.\/]{2,50})(?:\n|$)',
        r'\d+[-\.]\s*MALZEME\s*[:]\s*([A-Z0-9\s\-\+\.\/]{2,50})',
    ]
    for i, pattern in enumerate(explicit_patterns):
        try:
            matches = re.finditer(pattern, text_upper, re.MULTILINE)
            for match in matches:
                if match.group(1):
                    field_content = match.group(1).strip()
                    field_content = re.sub(r'[^\w\-\+]+', ' ', field_content).strip()
                    if len(field_content) >= 2:
                        field_key = f'explicit_field_{len(explicit_fields)}'
                        explicit_fields[field_key] = {
                            'content': field_content, 'pattern_index': i, 'confidence': 99, 'type': 'explicit_material_field'
                        }
        except re.error: continue
    if explicit_fields: return explicit_fields
    other_field_patterns = [
       r'MATERIAL\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})', r'STANDART\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'STANDARD\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})', r'SPEC\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'GRADE\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
    ]
    found_fields = {}
    for i, pattern in enumerate(other_field_patterns):
        try:
            matches = re.finditer(pattern, text_upper, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if match.group(1):
                    field_content = match.group(1).strip()
                    field_content = re.sub(r'[^\w\-\+]+', '', field_content).strip()
                    if (len(field_content) >= 2 and field_content not in ['MM', 'CM', 'INCH', 'TOLERANS', 'BOYUT', 'ÖLÇEK', 'KONTROL', 'ONAY'] and not field_content.isdigit()):
                        field_key = f'field_{len(found_fields)}'
                        found_fields[field_key] = {
                            'content': field_content, 'pattern_index': i, 'confidence': 85, 'type': 'technical_field'
                        }
        except re.error: continue
    return found_fields

def extract_notlar_section(text):
    if not text: return ""
    notlar_patterns = [
        r'NOTLAR\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)', r'NOTES\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)',
        r'NOT\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)', r'AÇIKLAMALAR\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)'
    ]
    text_upper = text.upper()
    for pattern in notlar_patterns:
        match = re.search(pattern, text_upper, re.DOTALL | re.MULTILINE)
        if match:
            notlar_content = match.group(1).strip()
            if len(notlar_content) > 10: return notlar_content
    return ""

def extract_notlar_items(notlar_text):
    if not notlar_text: return []
    item_pattern = r'(\d+\..*?)(?=\d+\.|$)'
    items = re.findall(item_pattern, notlar_text, re.DOTALL)
    processed_items = []
    for i, item in enumerate(items, 1):
        clean_item = item.strip()
        if len(clean_item) > 10: processed_items.append({'number': i, 'content': clean_item, 'length': len(clean_item)})
    return processed_items

def find_materials_in_notlar_items(items):
    all_materials = []
    notlar_patterns = lightning_cache.get_notlar_patterns()
    for item in items:
        item_content = item['content'].upper()
        item_number = item['number']
        explicit_pattern = r'MALZEME\s*[:]\s*([A-Z0-9\s\-\+\.\/]{2,50})'
        explicit_match = re.search(explicit_pattern, item_content)
        if explicit_match:
            material_text = explicit_match.group(1).strip()
            resolved_material = resolve_material_from_database(material_text)
            if resolved_material:
                all_materials.append({
                    'keyword': material_text, 'material_name': resolved_material, 'position': explicit_match.start(),
                    'confidence': 98, 'pattern_type': 'notlar_explicit_material', 'notlar_item': item_number,
                    'context': item_content[max(0, explicit_match.start()-30):explicit_match.end()+30]
                })
                continue
        found_materials = []
        for pattern_data in notlar_patterns:
            pattern = pattern_data['pattern']
            material_name = pattern_data['material_name']
            confidence = pattern_data['confidence']
            pattern_type = pattern_data['type']
            try:
                matches = re.finditer(pattern, item_content, re.IGNORECASE)
                for match in matches:
                    match_text = match.group(0)
                    if match.groups(): match_text = match.group(1)
                    found_materials.append({
                        'keyword': match_text, 'material_name': material_name, 'position': match.start(),
                        'confidence': confidence, 'pattern_type': pattern_type, 'notlar_item': item_number,
                        'context': item_content[max(0, match.start()-30):match.end()+30]
                    })
            except re.error: continue
        all_materials.extend(found_materials)
    return all_materials

def find_materials_in_technical_fields(fields, materials_cache):
    if not fields or not materials_cache: return []
    found_materials = []
    for field_key, field_data in fields.items():
        field_content = field_data['content'].strip()
        confidence_base = field_data['confidence']
        if field_data.get('type') == 'explicit_material_field': confidence_base = 99
        if field_content in materials_cache:
            found_materials.append({
                'keyword': field_content, 'material_name': field_content, 'position': 0,
                'confidence': confidence_base, 'pattern_type': 'technical_field_direct', 'source': 'technical_drawing_field'
            })
            continue
        match_found = False
        for material_name, material_data in materials_cache.items():
            aliases = material_data.get('aliases', [])
            if material_name.upper() == field_content.upper():
                found_materials.append({
                    'keyword': field_content, 'material_name': material_name, 'position': 0,
                    'confidence': confidence_base, 'pattern_type': 'technical_field_name_match', 'source': 'technical_drawing_field'
                })
                match_found = True
                break
            for alias in aliases:
                if str(alias).upper() == field_content.upper():
                    found_materials.append({
                        'keyword': field_content, 'material_name': material_name, 'position': 0,
                        'confidence': confidence_base - 2, 'pattern_type': 'technical_field_alias_match', 'source': 'technical_drawing_field'
                    })
                    match_found = True
                    break
            if match_found: break
        if not match_found:
            for material_name, material_data in materials_cache.items():
                if field_content in material_name.upper():
                    found_materials.append({
                        'keyword': field_content, 'material_name': material_name, 'position': 0,
                        'confidence': confidence_base - 20, 'pattern_type': 'technical_field_partial_match', 'source': 'technical_drawing_field'
                    })
                    break
    return found_materials

def resolve_material_from_database(captured_material):
    try:
        database = db.get_db()
        captured_clean = captured_material.strip().upper()
        material_mappings = {
            'AL 6061-T651': '6061', 'AL6061-T651': '6061', '6061-T651': '6061', 'AL 6061': '6061',
            'AL6061': '6061', 'AL 7075': '7075', 'AL7075': '7075', '7075-T6': '7075',
            'AL 2024': '2024', 'AL2024': '2024', 'AISI 304': 'aisi304', 'AISI304': 'aisi304',
            'AISI 316': 'aisi316', 'AISI316': 'aisi316', 'PA6GF30': 'GF30-PA66', 'PA6 GF30': 'GF30-PA66',
            'POM': 'POM', 'DELRIN': 'Delrin', 'TEFLON': 'Teflon', 'PTFE': 'Teflon',
        }
        for pattern, material_name in material_mappings.items():
            if pattern in captured_clean or captured_clean == pattern: return material_name
        material = database.materials.find_one({"name": {"$regex": f"^{re.escape(captured_clean)}$", "$options": "i"}}, {"name": 1})
        if material: return material.get("name")
        material = database.materials.find_one({"aliases": {"$regex": f"^{re.escape(captured_clean)}$", "$options": "i"}}, {"name": 1})
        if material: return material.get("name")
        common_patterns = [
            (r'6061.*', '6061'), (r'7075.*', '7075'), (r'2024.*', '2024'), (r'304.*', 'aisi304'),
            (r'316.*', 'aisi316'), (r'PA6GF30.*', 'GF30-PA66'), (r'POM.*', 'POM'), (r'DELRIN.*', 'Delrin'),
        ]
        for pattern, material_name in common_patterns:
            if re.match(pattern, captured_clean): return material_name
        return None
    except Exception: return None

def normalize_text_lightning(text):
    if not text or len(text) < 3: return ""
    text_upper = text.upper()
    char_map = str.maketrans({
        'Ç': 'C', 'Ğ': 'G', 'I': 'I', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U',
        '0': 'O', '1': 'I', '|': 'I'
    })
    text_upper = text_upper.translate(char_map)
    ocr_corrections = [
        (r'606I\b', '6061'), (r'6O6I\b', '6061'), (r'6O61\b', '6061'),
        (r'7O7S\b', '7075'), (r'7O75\b', '7075'), (r'70T5\b', '7075'),
        (r'2O24\b', '2024'), (r'Z024\b', '2024'), (r'3O4\b', '304'),
        (r'3I6\b', '316'), (r'3I6L\b', '316L'), (r'S083\b', '5083'),
        (r'7OSO\b', '7050'), (r'PA6GF3O\b', 'PA6GF30'), (r'PA6G F30\b', 'PA6GF30'),
    ]
    for pattern, replacement in ocr_corrections:
        text_upper = re.sub(pattern, replacement, text_upper)
    return text_upper

def clean_ocr_artifacts(text):
    if not text: return text
    cleaning_patterns = [
        (r'([A-Z0-9]{1,3})(BRASS|STEEL|ALUMINUM)', r'\1 \2'),
        (r'([A-Z0-9]{1,3})(BRONZE|COPPER|TITANIUM)', r'\1 \2'),
        (r'(AA)(\d+)', r'\1 \2'), (r'(\d+)(T\d+)', r'\1 \2'),
        (r'(T\d+)([\/\-])(\d+)', r'\1\2\3'), (r'MALZEME[/\\\s]*:?\s*', 'MALZEME: '),
        (r'MATERIAL[:\s]*', 'MATERIAL: '), (r'\s+', ' '),
    ]
    cleaned_text = text
    for pattern, replacement in cleaning_patterns:
        cleaned_text = re.sub(pattern, replacement, cleaned_text)
    return cleaned_text.strip()

def should_accept_match(match_text, pattern_type, full_text, position):
    if len(match_text) < 2: return False
    context_start = max(0, position - 30)
    context_end = min(len(full_text), position + len(match_text) + 30)
    context = full_text[context_start:context_end]
    if 'explicit' in pattern_type.lower() or 'technical' in pattern_type.lower() or 'notlar' in pattern_type.lower(): return True
    if 'flexible' in pattern_type:
        if position > 0:
            prev_char = full_text[position - 1]
            if prev_char.isalpha():
                if not any(artifact in full_text[max(0, position-5):position] for artifact in ['A4', 'SAYFA', 'SECTION', 'OLCEK']): return False
        if position + len(match_text) < len(full_text):
            next_char = full_text[position + len(match_text)]
            if next_char.isalpha(): return False
    match_upper = match_text.upper()
    if match_upper.isdigit() and len(match_upper) == 4:
        if match_upper in ['2024', '2025', '2026', '2027', '2028', '2029', '2030']:
            if any(year_indicator in context for year_indicator in ['/', 'YEAR', 'YIL', 'TARIH']): return False
        return True
    return True

def extract_material_keywords_from_text_fixed(text):
    if not text: return []
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials: return explicit_materials
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials: return notlar_materials
    cleaned_text = clean_ocr_artifacts(text)
    text_upper = cleaned_text.upper()
    patterns = get_dynamic_material_patterns()
    found_keywords = []
    for pattern_data in patterns:
        pattern = pattern_data['pattern']
        material_name = pattern_data['material_name']
        confidence = pattern_data['confidence']
        pattern_type = pattern_data['type']
        try:
            matches = re.finditer(pattern, text_upper, re.IGNORECASE)
            for match in matches:
                match_text = match.group(0)
                if match.groups() and match.group(1):
                    captured_material = match.group(1).strip()
                    if len(captured_material) >= 3:
                        resolved_material = resolve_material_from_database(captured_material)
                        if resolved_material:
                            material_name = resolved_material
                            match_text = captured_material
                if should_accept_match(match_text, pattern_type, text_upper, match.start()):
                    if is_part_description(match_text, text_upper, match.start()):
                        confidence = max(confidence - 30, 20)
                    found_keywords.append({
                        'keyword': match_text, 'material_name': material_name, 'position': match.start(),
                        'confidence': confidence, 'pattern_type': pattern_type, 'context': cleaned_text[max(0, match.start()-20):match.end()+20]
                    })
        except re.error: continue
    unique_keywords = []
    seen = {}
    sorted_keywords = sorted(found_keywords, key=lambda x: (-x['confidence'], 0 if 'exact' in x['pattern_type'] else 1))
    for keyword in sorted_keywords:
        material_key = keyword['material_name'].lower()
        if material_key not in seen:
            seen[material_key] = keyword
            unique_keywords.append(keyword)
        else:
            if keyword['confidence'] > seen[material_key]['confidence']:
                for i, uk in enumerate(unique_keywords):
                    if uk['material_name'].lower() == material_key:
                        unique_keywords[i] = keyword
                        seen[material_key] = keyword
                        break
    return unique_keywords

def get_dynamic_material_patterns():
    try:
        database = db.get_db()
        materials_cursor = database.materials.find()
        materials_list = list(materials_cursor)
        patterns = []
        explicit_material_patterns = [
            {'pattern': r'(?:^|\n)\s*MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'explicit_malzeme_field'},
            {'pattern': r'MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})(?:\n|$)', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'explicit_malzeme_field_end'},
            {'pattern': r'\d+[-\.]\s*MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 98, 'type': 'notlar_explicit_malzeme'},
        ]
        patterns.extend(explicit_material_patterns)
        technical_drawing_patterns = [
            {'pattern': r'MATERIAL[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 90, 'type': 'technical_material_field'},
            {'pattern': r'STANDART[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_standard_field'},
            {'pattern': r'GRADE[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_grade_field'},
            {'pattern': r'SPEC[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_spec_field'},
        ]
        patterns.extend(technical_drawing_patterns)
        strong_patterns = [
            {'pattern': r'AA\s*7075[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '7075', 'confidence': 95, 'type': 'aa_aluminum_temper'},
            {'pattern': r'AA\s*6061[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '6061', 'confidence': 95, 'type': 'aa_aluminum_temper'},
            {'pattern': r'AA\s*2024[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '2024', 'confidence': 95, 'type': 'aa_aluminum_temper'},
            {'pattern': r'\b7075\b', 'material_name': '7075', 'confidence': 80, 'type': 'aluminum_exact'},
            {'pattern': r'\b6061\b', 'material_name': '6061', 'confidence': 80, 'type': 'aluminum_exact'},
            {'pattern': r'\b2024\b', 'material_name': '2024', 'confidence': 80, 'type': 'aluminum_exact'},
            {'pattern': r'\bPA6GF30\b', 'material_name': 'GF30-PA66', 'confidence': 85, 'type': 'plastic_exact'},
            {'pattern': r'\bPOM\b', 'material_name': 'POM', 'confidence': 80, 'type': 'plastic_exact'},
            {'pattern': r'\bDELRIN\b', 'material_name': 'Delrin', 'confidence': 80, 'type': 'plastic_exact'},
        ]
        patterns.extend(strong_patterns)
        for material in materials_list:
            material_name = material.get('name', '').strip()
            aliases = material.get('aliases', [])
            if material_name:
                if len(material_name) >= 2:
                    escaped_name = re.escape(material_name)
                    patterns.append({
                        'pattern': f'\\b{escaped_name}\\b', 'material_name': material_name, 'confidence': 70, 'type': 'exact_match', 'source': 'material_name_exact'
                    })
                if aliases:
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip()
                            escaped_alias = re.escape(alias_clean)
                            patterns.append({
                                'pattern': f'\\b{escaped_alias}\\b', 'material_name': material_name, 'confidence': 65, 'type': 'alias_exact', 'source': f'alias_exact:{alias_clean}'
                            })
        return patterns
    except Exception: return []

def find_materials_in_text_database_only_proven(text):
    if not text or len(text.strip()) < 5: return []
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials:
        explicit_materials = apply_6061_priority_to_materials(explicit_materials)
        proven_format_materials = []
        for material in explicit_materials:
            confidence = material['confidence']
            material_name = material['material_name'] 
            formatted_material = f"{material_name} (%{confidence})"
            proven_format_materials.append(formatted_material)
        return proven_format_materials[:5]
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                notlar_materials = apply_6061_priority_to_materials(notlar_materials)
                proven_format_materials = []
                for material in notlar_materials:
                    confidence = material['confidence']
                    material_name = material['material_name'] 
                    formatted_material = f"{material_name} (%{confidence})"
                    proven_format_materials.append(formatted_material)
                return proven_format_materials[:5]
    normalized_text = comprehensive_turkish_normalization_from_working(text)
    if not normalized_text: return []
    material_keywords = extract_material_keywords_from_text_fixed(normalized_text)
    if not material_keywords: return []
    material_keywords = apply_6061_priority_to_materials(material_keywords)
    try:
        database = db.get_db()
        materials_cursor = database.materials.find({}, {"name": 1, "density": 1, "price_per_kg": 1, "category": 1, "aliases": 1, "is_active": 1})
        materials_list = list(materials_cursor)
        materials_cache = {}
        for material in materials_list:
            material_name = material.get('name')
            if material_name and str(material_name).strip() != "": materials_cache[material_name] = material
        if not materials_cache: return []
    except Exception: return []
    found_materials = {}
    for keyword_info in material_keywords:
        keyword = keyword_info['keyword']
        material_name = keyword_info['material_name']
        confidence = keyword_info['confidence']
        pattern_type = keyword_info['pattern_type']
        if material_name in materials_cache:
            found_materials[material_name] = {
                'confidence': confidence, 'matched_term': f"prioritized_{keyword}",
                'material': materials_cache[material_name], 'strategy': 'prioritized_proven_method',
                'source_keyword': keyword, 'pattern_type': pattern_type
            }
    if found_materials:
        sorted_materials = sorted(found_materials.items(), key=lambda x: x[1]['confidence'], reverse=True)
        result_materials = []
        for material_name, match_info in sorted_materials[:5]:
            confidence = match_info['confidence']
            formatted_material = f"{material_name} (%{confidence})"
            result_materials.append(formatted_material)
        result_materials = apply_6061_priority_to_materials(result_materials)
        return result_materials
    return []

def comprehensive_turkish_normalization_from_working(text):
    if not text: return ""
    original_text = str(text)
    text = original_text.upper()
    material_corrections = {
        "MALZEME": "MALZEME", "MATERIEL": "MATERIAL", "MATER1AL": "MATERIAL", "MATER_AL": "MATERIAL",
        "AA 7075": "AA7075", "AA-7075": "AA7075", "AA_7075": "AA7075", "AA 6061": "AA6061", "AA-6061": "AA6061", "AA_6061": "AA6061",
        "AA 2024": "AA2024", "AA-2024": "AA2024", "AL 6061-T651": "AL 6061-T651", "AL6061-T651": "AL 6061-T651",
        "7O75": "7075", "7075-T6": "7075T6", "7075-T651": "7075T651", "6O61": "6061", "6061-T6": "6061T6",
        "6061-T651": "6061T651", "2024-T3": "2024T3", "PA6GF3O": "PA6GF30", "PA6G F30": "PA6GF30", "PA 6GF30": "PA6GF30",
    }
    for error, correction in material_corrections.items():
        if error in text: text = text.replace(error, correction)
    turkish_replacements = {
        'Ç': 'C', 'ç': 'C', 'Ğ': 'G', 'ğ': 'G', 'I': 'I', 'ı': 'I', 'İ': 'I', 'i': 'I',
        'Ö': 'O', 'ö': 'O', 'Ş': 'S', 'ş': 'S', 'Ü': 'U', 'ü': 'U'
    }
    for turkish_char, english_char in turkish_replacements.items():
        if turkish_char in text: text = text.replace(turkish_char, english_char)
    final_text = re.sub(r'\s+', ' ', text).strip()
    return final_text

class LightningPatternCache:
    def __init__(self):
        self._pattern_cache = None
        self._pattern_cache_timestamp = 0
        self._pattern_cache_ttl = 1800
        self._quick_patterns = None
        self._material_lookup = None
        self._notlar_patterns = None
        self._technical_patterns = None
        self._database = db.get_db()
    
    def get_technical_patterns(self):
        if self._technical_patterns is None: self._technical_patterns = self._build_technical_patterns()
        return self._technical_patterns
    
    def _build_technical_patterns(self):
        try:
            materials = self._database.materials.find({}, {"name": 1, "aliases": 1})
            technical_patterns = []
            technical_contexts = [
                r'(?:^|\n)\s*MALZEME\s*[:]\s*({material}[\w\d\-\s\/]*)', r'MALZEME[/\\\s]*:?\s*({material}[\w\d\-\s\/]*)',
                r'MATERIAL[:\s]*({material}[\w\d\-\s\/]*)', r'STANDART[:\s]*({material}[\w\d\-\s\/]*)',
            ]
            for material in materials:
                material_name = material.get('name', '').strip()
                aliases = material.get('aliases', [])
                if not material_name or len(material_name) < 2: continue
                all_names = [material_name] + [str(alias).strip() for alias in aliases if alias]
                for name in all_names:
                    if len(name) < 2: continue
                    escaped_name = re.escape(name)
                    for i, context_pattern in enumerate(technical_contexts):
                        pattern = context_pattern.format(material=escaped_name)
                        confidence = 99 if i == 0 else (95 - i*2)
                        technical_patterns.append({
                            'pattern': pattern, 'material_name': material_name, 'confidence': confidence,
                            'type': 'technical_context', 'source': f'technical_{name}'
                        })
            return technical_patterns
        except Exception: return []
    
    def get_notlar_patterns(self):
        if self._notlar_patterns is None: self._notlar_patterns = self._build_notlar_patterns()
        return self._notlar_patterns
    
    def _build_notlar_patterns(self):
        try:
            materials = self._database.materials.find({}, {"name": 1, "aliases": 1})
            notlar_patterns = []
            notlar_contexts = [
                r'MALZEME\s*:?\s*({material}[\w\d\-\s\/]*)', r'MATERIAL\s*:?\s*({material}[\w\d\-\s\/]*)',
                r'ASTM\s+[A-Z]?\d+[A-Z\d\-]*.*?({material}[\w\d\-\s\/]*)', r'EN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)', 
                r'DIN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)',
            ]
            for material in materials:
                material_name = material.get('name', '').strip()
                aliases = material.get('aliases', [])
                if not material_name or len(material_name) < 2: continue
                all_names = [material_name] + [str(alias).strip() for alias in aliases if alias]
                for name in all_names:
                    if len(name) < 2: continue
                    escaped_name = re.escape(name)
                    for i, context_pattern in enumerate(notlar_contexts):
                        pattern = context_pattern.format(material=escaped_name)
                        confidence = 98 if i == 0 else (92 - i*2)
                        notlar_patterns.append({
                            'pattern': pattern, 'material_name': material_name, 'confidence': confidence,
                            'type': 'notlar_context', 'source': f'notlar_{name}'
                        })
            return notlar_patterns
        except Exception: return []
    
    def get_lightning_patterns(self):
        if self._quick_patterns is None:
            self._quick_patterns = {
                '6061': ('6061', 70), '606I': ('6061', 65), '6O61': ('6061', 65),
                '7075': ('7075', 70), '7O75': ('7075', 65), '70T5': ('7075', 60),
                '2024': ('2024', 70), '2O24': ('2024', 65), 'Z024': ('2024', 60),
                '304': ('aisi304', 65), '3O4': ('aisi304', 60), 'AISI304': ('aisi304', 70),
                '316': ('aisi316', 65), '3I6': ('aisi316', 60), 'AISI316': ('aisi316', 70),
                'PA6GF30': ('GF30-PA66', 75), 'PA6GF3O': ('GF30-PA66', 70),
                'POM': ('POM', 70), 'POMC': ('POM', 65),
                'DELRIN': ('Delrin', 70), 'PMMA': ('PMMA', 70),
                'TEFLON': ('Teflon', 70), 'PTFE': ('Teflon', 70),
            }
        return self._quick_patterns
    
    def get_material_lookup(self):
        if self._material_lookup is None:
            self._material_lookup = {}
            quick_patterns = self.get_lightning_patterns()
            for pattern, (material, confidence) in quick_patterns.items():
                key = pattern.upper()
                if material not in self._material_lookup: self._material_lookup[material] = []
                self._material_lookup[material].append((key, confidence))
        return self._material_lookup
    
    def get_cached_patterns(self):
        current_time = time.time()
        if (self._pattern_cache is None or current_time - self._pattern_cache_timestamp > self._pattern_cache_ttl):
            self._pattern_cache = self._build_lightning_patterns()
            self._pattern_cache_timestamp = current_time
        return self._pattern_cache
    
    def _build_lightning_patterns(self):
        try:
            patterns = []
            materials = self._database.materials.find()
            for material in materials:
                name = material.get('name')
                if name:
                    patterns.append({'pattern': name.upper(), 'material_name': name, 'confidence': 60})
                    aliases = material.get('aliases', [])
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip().upper()
                            patterns.append({'pattern': alias_clean, 'material_name': name, 'confidence': 55})
            return patterns
        except Exception: return []

lightning_cache = LightningPatternCache()

# =====================================================
# MAIN SERVICE CLASS
# =====================================================

class MaterialAnalysisServiceOptimized:
    def __init__(self):
        self.database = db.get_db()
        self._material_cache = {}
        self._cache_lock = threading.Lock()
        self._last_cache_update = 0
        self._cache_ttl = 600
        try:
            self._preload_essential_materials_lightning()
        except Exception as e: print(f"[INIT] Initialization failed: {e}")
    
    def _preload_essential_materials_lightning(self):
        try:
            materials_cursor = self.database.materials.find()
            with self._cache_lock:
                self._material_cache = {}
                for material in materials_cursor:
                    material_name = material.get('name')
                    if material_name:
                        density = material.get('density', 2.7)
                        price_per_kg = material.get('price_per_kg', 10)
                        self._material_cache[material_name] = {
                            'name': material_name, 'density': float(density), 'price_per_kg': float(price_per_kg),
                            'category': material.get('category', 'Unknown'), 'aliases': material.get('aliases', []),
                            'is_active': material.get('is_active', True)
                        }
            self._last_cache_update = time.time()
        except Exception: pass

    def _get_materials_cached_lightning(self):
        current_time = time.time()
        if (not self._material_cache or current_time - self._last_cache_update > self._cache_ttl):
            self._preload_essential_materials_lightning()
        return self._material_cache

    def _find_materials_in_text_ultra_fast(self, text):
        if not text or len(text.strip()) < 3: return []
        materials = find_materials_in_text_database_only_proven(text)
        if materials and len(materials) > 1:
            has_6061 = any('6061' in str(mat).upper() for mat in materials)
            has_other = any('6061' not in str(mat).upper() for mat in materials)
            if has_6061 and has_other: materials = apply_6061_priority_to_materials(materials)
        return materials

    def _extract_text_from_pdf_optimized(self, pdf_path, start_time=None, timeout=60):
        return extract_text_with_lightning_ocr(pdf_path, global_start_time=start_time, timeout=timeout)

    def _analyze_pdf_ultra_fast_optimized(self, file_path, result, matched_step_path=None, start_time=None, timeout=60):
        if start_time is None: start_time = time.time()
        
        # Check global timeout
        if time.time() - start_time > timeout:
            result["processing_log"].append("⏱️ Analysis timed out before PDF processing.")
            return result

        if matched_step_path and os.path.exists(matched_step_path):
            result["processing_log"].append(f"🔗 Using matched STEP: {os.path.basename(matched_step_path)}")
            try:
                # Check timeout before step analysis
                if time.time() - start_time > timeout:
                    result["step_analysis"] = self._get_zero_step_defaults_lightning()
                else:
                    step_analysis_result = self.analyze_step_file_ultra_fast(matched_step_path)
                    is_valid_result = (
                        step_analysis_result.get('Prizma Hacmi (mm³)', 0) > 0 and
                        step_analysis_result.get('method') != 'prioritized_zero_defaults' and
                        not step_analysis_result.get('error')
                    )
                    if is_valid_result:
                        result["step_analysis"] = step_analysis_result
                        result["matched_step_used"] = True
                        result["step_source"] = "matched"
                        result["extracted_step_path"] = matched_step_path
                        result["pdf_step_extracted"] = False
                    else: matched_step_path = None
            except Exception: matched_step_path = None
        
        materials = []
        ocr_method = "none"
        raw_text = ""
        
        # Check timeout before PyPDF2
        if time.time() - start_time < timeout:
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    all_text = ""
                    for page in reader.pages:
                        try:
                            text = page.extract_text()
                            if text: all_text += "\n" + text
                        except: continue
                    if all_text and len(all_text.strip()) > 20:
                        raw_text = all_text
                        materials = self._find_materials_in_text_ultra_fast(all_text)
                        if materials: ocr_method = "pypdf2_prioritized"
            except Exception: pass
        
        # Check timeout before OCR
        if not materials and (time.time() - start_time < timeout):
            try:
                # Pass start_time and timeout to OCR function
                ocr_text = self._extract_text_from_pdf_optimized(file_path, start_time=start_time, timeout=timeout)
                if ocr_text:
                    raw_text = ocr_text
                    materials = self._find_materials_in_text_ultra_fast(ocr_text)
                    if materials: ocr_method = "tesseract_prioritized"
            except Exception: pass
        
        if not materials:
            materials = []
            ocr_method = "prioritized_no_materials_or_timeout"
        
        result["material_matches"] = materials
        result["ocr_method"] = ocr_method
        result["raw_ocr_output"] = raw_text[:3000] if raw_text else ""
        result["ocr_confidence"] = 85 if materials else 0
        
        # Check timeout before step extraction/generation
        if not result.get("step_analysis") and (time.time() - start_time < timeout):
            if materials:
                try:
                    step_paths = self._extract_step_from_pdf_lightning(file_path)
                    if step_paths:
                        extracted_step_path = step_paths[0]
                        result["extracted_step_path"] = extracted_step_path
                        result["pdf_step_extracted"] = True
                        result["step_source"] = "extracted"
                        result["step_analysis"] = self.analyze_step_file_ultra_fast(extracted_step_path)
                    else:
                        generated_step_path = self._auto_generate_step_from_pdf(raw_text, file_path)
                        if generated_step_path and os.path.exists(generated_step_path):
                            result["extracted_step_path"] = generated_step_path
                            result["pdf_step_extracted"] = False
                            result["step_source"] = "auto_generated"
                            result["step_analysis"] = self.analyze_step_file_ultra_fast(generated_step_path)
                        else:
                            result["step_analysis"] = self._get_estimated_step_defaults()
                            result["pdf_step_extracted"] = False
                            result["step_source"] = "estimated"
                except Exception:
                    result["step_analysis"] = self._get_estimated_step_defaults()
                    result["step_source"] = "estimated"
        elif not result.get("step_analysis"):
             # Timeout reached or no materials, use defaults
             result["step_analysis"] = self._get_estimated_step_defaults()
             result["step_source"] = "timeout_defaults"

        if "material_matches" not in result: result["material_matches"] = materials
        result["material_confidence"] = 85 if materials else 0
        return result

    def _auto_generate_step_from_pdf(self, pdf_text, pdf_path):
        try:
            import re
            dimensions = {}
            numbers = re.findall(r'(\d+\.?\d*)', pdf_text)
            float_numbers = []
            for num in numbers:
                try:
                    val = float(num)
                    if 1 < val < 500: float_numbers.append(val)
                except: continue
            if len(float_numbers) >= 3:
                sorted_nums = sorted(set(float_numbers), reverse=True)
                dimensions['x'] = sorted_nums[0] if sorted_nums else 20
                dimensions['y'] = sorted_nums[1] if len(sorted_nums) > 1 else 15
                dimensions['z'] = sorted_nums[2] if len(sorted_nums) > 2 else 10
            else: dimensions = {'x': 20, 'y': 15, 'z': 10}
            
            x = dimensions.get('x', 20)
            y = dimensions.get('y', 15)
            z = dimensions.get('z', 10)
            hole_d = dimensions.get('hole_diameter', 0)
            fillet_r = dimensions.get('fillet_radius', 0.5)
            
            try:
                result = cq.Workplane("XY").box(x, y, z)
                if hole_d > 0 and hole_d < min(x, y): result = result.faces(">Z").workplane().hole(hole_d)
                try:
                    if fillet_r > 0 and fillet_r < min(x, y, z) / 4: result = result.edges().fillet(fillet_r)
                except: pass
                
                temp_dir = os.path.join(os.getcwd(), "temp")
                os.makedirs(temp_dir, exist_ok=True)
                timestamp = int(time.time())
                output_path = os.path.join(temp_dir, f"auto_gen_{timestamp}.step")
                
                # FIXED: Correct exporters syntax
                exporters.export(result, output_path, exportType='STEP')
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100: return output_path
                else: return None
            except Exception: return None
        except Exception: return None

    def _get_estimated_step_defaults(self):
        return {
            "X (mm)": 20, "Y (mm)": 15, "Z (mm)": 10,
            "X+Pad (mm)": 30, "Y+Pad (mm)": 25, "Z+Pad (mm)": 20,
            "Silindirik Çap (mm)": 30, "Silindirik Yükseklik (mm)": 20,
            "Prizma Hacmi (mm³)": 15000, "Ürün Hacmi (mm³)": 3000,
            "Talaş Hacmi (mm³)": 12000, "Talaş Oranı (%)": 80,
            "Toplam Yüzey Alanı (mm²)": 1300,
            "method": "estimated_defaults",
            "warning": "STEP dosyası bulunamadı veya oluşturulamadı, tahmini değerler kullanılıyor"
        }

    def _get_zero_step_defaults_lightning(self):
        return {
            "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
            "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
            "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
            "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
            "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
            "Toplam Yüzey Alanı (mm²)": 0,
            "method": "prioritized_zero_defaults"
        }

    def analyze_document_ultra_fast(self, file_path, file_type, user_id, matched_step_path=None, timeout=60):
        # GLOBAL TIMEOUT START
        start_time = time.time()
        
        result = {
            "material_matches": [], "step_analysis": {}, "cost_estimation": {},
            "ai_price_prediction": {}, "all_material_calculations": [],
            "material_options": [], "processing_log": [], "step_file_hash": None
        }
        
        try:
            if file_type == 'pdf':
                # Pass start_time and timeout to PDF analysis
                result = self._analyze_pdf_ultra_fast_optimized(file_path, result, matched_step_path, start_time=start_time, timeout=timeout)
            elif file_type in ['step', 'stp']:
                try:
                    result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                except Exception:
                    result["step_analysis"] = self._get_zero_step_defaults_lightning()
            elif file_type in ['doc', 'docx']:
                result = self._analyze_document_lightning(file_path, result)
            
            # Check timeout before calculations
            if time.time() - start_time < timeout:
                step_analysis = result.get("step_analysis", {})
                prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)", 0)
                
                if prizma_hacim and prizma_hacim > 0:
                    result["material_options"] = self._calculate_top_materials_lightning(prizma_hacim)
                
                if result.get("material_matches") and prizma_hacim and prizma_hacim > 0:
                    result["all_material_calculations"] = self._calculate_found_materials_lightning(
                        prizma_hacim, result["material_matches"]
                    )
                
                if not result.get("material_options") and prizma_hacim and prizma_hacim > 0:
                    result["material_options"] = self._get_database_only_materials(prizma_hacim)
            
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    def _get_database_only_materials(self, prizma_hacim_mm3):
        try:
            if prizma_hacim_mm3 <= 0: return []
            materials_cache = self._get_materials_cached_lightning()
            if not materials_cache: return []
            materials_list = []
            for material_name, material in materials_cache.items():
                try:
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    mass_kg = (prizma_hacim_mm3 * density) / 1_000_000
                    material_cost = mass_kg * price_per_kg
                    materials_list.append({
                        "name": material_name, "category": category,
                        "density": round(density, 2), "mass_kg": round(mass_kg, 3),
                        "price_per_kg": round(price_per_kg, 2), "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3, "source": "database_only"
                    })
                except Exception: continue
            materials_list.sort(key=lambda x: x["material_cost"])
            return materials_list
        except Exception: return []

    def _calculate_top_materials_lightning(self, prizma_hacim_mm3, limit=None):
        try:
            if prizma_hacim_mm3 <= 0: return []
            materials_cache = self._get_materials_cached_lightning()
            if not materials_cache: return []
            top_materials = []
            for material_name, material in materials_cache.items():
                try:
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    mass_kg = (prizma_hacim_mm3 * density) / 1_000_000
                    material_cost = mass_kg * price_per_kg
                    top_materials.append({
                        "name": material_name, "category": category,
                        "density": round(density, 2), "mass_kg": round(mass_kg, 3),
                        "price_per_kg": round(price_per_kg, 2), "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3, "source": "prioritized_cache"
                    })
                except Exception: continue
            top_materials.sort(key=lambda x: x["material_cost"])
            if limit: return top_materials[:limit]
            return top_materials
        except Exception: return []

    def _calculate_found_materials_lightning(self, prizma_hacim_mm3, found_materials):
        try:
            if prizma_hacim_mm3 <= 0 or not found_materials: return []
            calculations = []
            materials_cache = self._get_materials_cached_lightning()
            for material_text in found_materials[:5]:
                material_name = material_text.split("(")[0].strip()
                material = materials_cache.get(material_name)
                if not material:
                    material_lower = material_name.lower()
                    for cached_name, cached_material in materials_cache.items():
                        if cached_name.lower() == material_lower:
                            material = cached_material
                            break
                if not material: continue
                try:
                    density = material.get("density", 2.7)
                    price_per_kg = material.get("price_per_kg", 10)
                    confidence_match = re.search(r'%(\d+)', material_text)
                    confidence = int(confidence_match.group(1)) if confidence_match else 80
                    mass_kg = (prizma_hacim_mm3 * density) / 1_000_000
                    material_cost = mass_kg * price_per_kg
                    calculations.append({
                        "material": material.get("name", material_name),
                        "confidence": f"%{confidence}",
                        "density": density, "mass_kg": round(mass_kg, 3),
                        "price_per_kg": price_per_kg, "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3, "source": "prioritized_cache"
                    })
                except Exception: continue
            return calculations
        except Exception: return []

    def _calculate_found_materials_database_only(self, prizma_hacim_mm3, found_materials):
        try:
            if prizma_hacim_mm3 <= 0 or not found_materials: return []
            calculations = []
            for material_text in found_materials[:3]:
                material_name = material_text.split("(")[0].strip()
                try:
                    material = self.database.materials.find_one({"name": material_name}, {"name": 1, "density": 1, "price_per_kg": 1, "category": 1})
                    if not material:
                        material = self.database.materials.find_one({"name": {"$regex": f"^{re.escape(material_name)}$", "$options": "i"}}, {"name": 1, "density": 1, "price_per_kg": 1, "category": 1})
                    if material:
                        density = material.get("density", 2.7)
                        price_per_kg = material.get("price_per_kg", 10)
                        category = material.get("category", "Unknown")
                        confidence_match = re.search(r'%(\d+)', material_text)
                        confidence = int(confidence_match.group(1)) if confidence_match else 80
                        mass_kg = (prizma_hacim_mm3 * density) / 1_000_000
                        material_cost = mass_kg * price_per_kg
                        calculations.append({
                            "material": material.get("name", material_name),
                            "confidence": f"%{confidence}", "density": density,
                            "mass_kg": round(mass_kg, 3), "price_per_kg": price_per_kg,
                            "material_cost": round(material_cost, 2), "volume_mm3": prizma_hacim_mm3,
                            "category": category, "source": "database_only"
                        })
                except Exception: continue
            return calculations
        except Exception: return []

    def _calculate_top_materials_database_only(self, prizma_hacim_mm3, limit=None):
        try:
            if prizma_hacim_mm3 <= 0: return []
            materials_cursor = self.database.materials.find({}, {"name": 1, "density": 1, "price_per_kg": 1, "category": 1})
            top_materials = []
            for material in materials_cursor:
                try:
                    material_name = material.get("name")
                    if not material_name: continue
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    mass_kg = (prizma_hacim_mm3 * density) / 1_000_000
                    material_cost = mass_kg * price_per_kg
                    top_materials.append({
                        "name": material_name, "category": category,
                        "density": round(density, 2), "mass_kg": round(mass_kg, 3),
                        "price_per_kg": round(price_per_kg, 2), "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3, "source": "database_only"
                    })
                except Exception: continue
            top_materials.sort(key=lambda x: x["material_cost"])
            if limit: return top_materials[:limit]
            return top_materials
        except Exception: return []

    def _analyze_document_lightning(self, file_path, result):
        result["processing_log"].append("📝 Document analysis")
        try:
            if file_path.lower().endswith('.docx'):
                text = self._extract_text_from_docx_lightning(file_path)
            else:
                text = self._extract_text_from_doc_lightning(file_path)
            if text:
                materials = self._find_materials_in_text_ultra_fast(text)
            else:
                materials = []
            result["material_matches"] = materials
            result["step_analysis"] = self._get_zero_step_defaults_lightning()
        except Exception as e:
            result["material_matches"] = []
            result["step_analysis"] = self._get_zero_step_defaults_lightning()
        return result

    def _extract_text_from_docx_lightning(self, file_path):
        try:
            doc = Document(file_path)
            texts = [p.text for p in doc.paragraphs[:5] if p.text.strip()]
            return "\n".join(texts)
        except Exception: return ""
    
    def _extract_text_from_doc_lightning(self, file_path):
        try:
            output_dir = os.path.dirname(file_path)
            subprocess.run(["libreoffice", "--headless", "--convert-to", "docx", "--outdir", output_dir, file_path], capture_output=True, timeout=5)
            docx_path = os.path.splitext(file_path)[0] + ".docx"
            if os.path.exists(docx_path):
                text = self._extract_text_from_docx_lightning(docx_path)
                try: os.remove(docx_path)
                except: pass
                return text
            return ""
        except Exception: return ""

    def analyze_step_file_ultra_fast(self, step_path):
        try:
            start_time = time.time()
            try:
                assembly = cq.importers.importStep(step_path)
                if not assembly.objects:
                    return self._get_zero_step_defaults("Empty STEP file - no objects")
            except Exception as import_error:
                return self._get_zero_step_defaults(f"Import failed: {str(import_error)}")
            
            shapes = assembly.objects
            if not shapes:
                return self._get_zero_step_defaults("No shapes found")
            
            main_shape = max(shapes, key=lambda s: s.Volume())
            main_bbox = main_shape.BoundingBox()
            
            x = float(main_bbox.xlen)
            y = float(main_bbox.ylen)
            z = float(main_bbox.zlen)
            
            if x <= 0 or y <= 0 or z <= 0:
                return self._get_zero_step_defaults("Invalid bounding box dimensions")
            
            x_pad = round(x + 10, 1)
            y_pad = round(y + 10, 1)
            z_pad = round(z + 10, 1)
            
            volume_padded = x_pad * y_pad * z_pad
            
            try:
                product_volume = main_shape.Volume()
                total_surface_area = main_shape.Area()
            except Exception:
                product_volume = x * y * z * 0.75
                total_surface_area = 2 * (x*y + y*z + x*z) * 1.2
            
            waste_volume = max(volume_padded - product_volume, 0)
            waste_ratio = (waste_volume / volume_padded * 100) if volume_padded > 0 else 0
            
            cylinder_diameter = round(max(x, y) + 10, 1)
            cylinder_height = round(z + 10, 1)
            
            analysis_time = time.time() - start_time
            
            result = {
                "X (mm)": round(x, 2), "Y (mm)": round(y, 2), "Z (mm)": round(z, 2),
                "Silindirik Çap (mm)": cylinder_diameter, "Silindirik Yükseklik (mm)": cylinder_height,
                "X+Pad (mm)": x_pad, "Y+Pad (mm)": y_pad, "Z+Pad (mm)": z_pad,
                "Prizma Hacmi (mm³)": round(volume_padded, 2), "Ürün Hacmi (mm³)": round(product_volume, 2),
                "Talaş Hacmi (mm³)": round(waste_volume, 2), "Talaş Oranı (%)": round(waste_ratio, 1),
                "Toplam Yüzey Alanı (mm²)": round(total_surface_area, 2),
                "analysis_time": analysis_time, "method": "prioritized_optimized_fixed_verbose"
            }
            return result
        except Exception as e:
            return self._get_zero_step_defaults(f"Analysis failed: {str(e)}")

    def _get_zero_step_defaults(self, error_msg=""):
        return {
            "error": error_msg,
            "X (mm)": 0, "Y (mm)": 0, "Z (mm)": 0,
            "Silindirik Çap (mm)": 0, "Silindirik Yükseklik (mm)": 0,
            "X+Pad (mm)": 0, "Y+Pad (mm)": 0, "Z+Pad (mm)": 0,
            "Prizma Hacmi (mm³)": 0, "Ürün Hacmi (mm³)": 0,
            "Talaş Hacmi (mm³)": 0, "Talaş Oranı (%)": 0,
            "Toplam Yüzey Alanı (mm²)": 0,
            "method": "prioritized_zero_defaults"
        }

    def _extract_step_from_pdf_lightning(self, pdf_path):
        try:
            extracted = []
            start_time = time.time()
            TIMEOUT_SECONDS = 10.0
            
            with pikepdf.open(pdf_path) as pdf:
                # METHOD 1: Embedded Files
                try:
                    root = pdf.trailer.get("/Root", {})
                    if root:
                        names = root.get("/Names", {})
                        if names:
                            embedded = names.get("/EmbeddedFiles", {})
                            if embedded:
                                files = embedded.get("/Names", [])
                                for i in range(0, min(len(files), 20), 2):
                                    if time.time() - start_time > TIMEOUT_SECONDS: break
                                    if i + 1 < len(files):
                                        try:
                                            file_spec = files[i + 1]
                                            file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                                            if file_name.lower().endswith(('.stp', '.step')):
                                                ef = file_spec.get('/EF', {})
                                                if ef and '/F' in ef:
                                                    file_data = ef['/F'].read_bytes()
                                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                                    os.makedirs(temp_dir, exist_ok=True)
                                                    safe_filename = f"embedded_{int(time.time())}.step"
                                                    output_path = os.path.join(temp_dir, safe_filename)
                                                    with open(output_path, 'wb') as f: f.write(file_data)
                                                    if os.path.getsize(output_path) > 100:
                                                        extracted.append(output_path)
                                                        return extracted
                                                    else: os.remove(output_path)
                                        except Exception: continue
                except Exception: pass
                
                # METHOD 2: FileAttachment Annotations
                try:
                    for page in pdf.pages:
                        if time.time() - start_time > TIMEOUT_SECONDS: break
                        if "/Annots" in page:
                            annotations = page["/Annots"]
                            for annot_ref in annotations:
                                try:
                                    annot_obj = pdf.get_object(annot_ref)
                                    subtype = annot_obj.get("/Subtype")
                                    if subtype == "/FileAttachment":
                                        file_spec = annot_obj.get("/FS")
                                        if file_spec:
                                            file_name = str(file_spec.get("/UF", file_spec.get("/F", ""))).strip("()")
                                            if file_name.lower().endswith(('.stp', '.step')):
                                                ef = file_spec.get("/EF")
                                                if ef and "/F" in ef:
                                                    stream = ef["/F"]
                                                    file_data = stream.read_bytes()
                                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                                    os.makedirs(temp_dir, exist_ok=True)
                                                    output_path = os.path.join(temp_dir, f"attachment_{int(time.time())}.step")
                                                    with open(output_path, 'wb') as f: f.write(file_data)
                                                    if os.path.getsize(output_path) > 100:
                                                        extracted.append(output_path)
                                                        return extracted
                                                    else: os.remove(output_path)
                                except Exception: continue
                except Exception: pass
                
                return extracted
        except Exception: return []

    def _is_step_data_fast(self, data):
        try:
            if len(data) < 100: return False
            step_signatures = [b'ISO-10303-21', b'HEADER;', b'FILE_DESCRIPTION', b'FILE_NAME', b'STEP AP']
            for signature in step_signatures:
                if signature in data[:1000]: return True
            return False
        except: return False
    
    def _save_step_data_fast(self, data, filename):
        try:
            temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            output_path = os.path.join(temp_dir, filename)
            with open(output_path, 'wb') as f: f.write(data)
            if os.path.getsize(output_path) > 100: return [output_path]
            else:
                os.remove(output_path)
                return []
        except: return []
    
    def refresh_material_cache(self):
        with self._cache_lock:
            self._material_cache = {}
            self._last_cache_update = 0
        self._preload_essential_materials_lightning()
        lightning_cache._pattern_cache = None
        lightning_cache._notlar_patterns = None
        lightning_cache._technical_patterns = None

# =====================================================
# COST ESTIMATION SERVICE
# =====================================================

class CostEstimationServiceFast:
    def __init__(self):
        self.database = db.get_db()
        self._price_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 900
    
    def calculate_cost_lightning(self, step_analysis, material_matches):
        try:
            if not step_analysis or step_analysis.get("error"):
                return {"error": "STEP analysis required"}
            if not material_matches:
                return {"error": "Material required"}
            material_name = material_matches[0].split("(")[0].strip()
            volume = step_analysis.get("Prizma Hacmi (mm³)", 0)
            if volume <= 0:
                return {
                    "error": "Invalid volume",
                    "material": {"name": material_name, "cost_usd": 0, "mass_kg": 0},
                    "machining": {"hours": 0, "cost_usd": 0},
                    "costs": {"material_usd": 0, "labor_usd": 0, "total_usd": 0}
                }
            material_cost = self._calculate_material_cost_lightning(volume, material_name)
            waste = step_analysis.get("Talaş Hacmi (mm³)", 0)
            surface = step_analysis.get("Toplam Yüzey Alanı (mm²)", 0)
            labor_hours = max((waste / 5000 + surface / 2000) / 60, 0.1)
            labor_cost = labor_hours * 70
            total = material_cost["cost_usd"] + labor_cost
            return {
                "material": {"name": material_name, "cost_usd": material_cost["cost_usd"], "mass_kg": material_cost["mass_kg"]},
                "machining": {"hours": round(labor_hours, 2), "cost_usd": round(labor_cost, 2)},
                "costs": {"material_usd": material_cost["cost_usd"], "labor_usd": round(labor_cost, 2), "total_usd": round(total, 2)}
            }
        except Exception as e:
            return {"error": f"Cost calculation error: {str(e)}"}
    
    def _calculate_material_cost_lightning(self, volume_mm3, material_name):
        try:
            if volume_mm3 <= 0: return {"mass_kg": 0, "cost_usd": 0}
            current_time = time.time()
            cache_key = material_name
            if (cache_key in self._price_cache and 
                current_time - self._cache_timestamp < self._cache_ttl):
                cached_data = self._price_cache[cache_key]
                density = cached_data['density']
                price = cached_data['price']
            else:
                material = self.database.materials.find_one({"name": material_name}, {"density": 1, "price_per_kg": 1})
                if material:
                    density = material.get("density", 2.7)
                    price = material.get("price_per_kg", 10)
                else:
                    if any(pattern in material_name.lower() for pattern in ['6061', '7075', '2024', 'aluminum', 'aluminium']): density, price = 2.7, 5.0
                    elif any(pattern in material_name.lower() for pattern in ['304', '316', 'steel', 'stainless']): density, price = 7.93, 9.0
                    elif 'brass' in material_name.lower(): density, price = 8.5, 13.0
                    elif 'copper' in material_name.lower(): density, price = 8.96, 15.0
                    elif any(pattern in material_name.lower() for pattern in ['pa6gf30', 'pom', 'delrin', 'pmma', 'plastic']): density, price = 1.4, 20.0
                    else: density, price = 2.7, 12
                self._price_cache[cache_key] = {'density': density, 'price': price}
                self._cache_timestamp = current_time
            mass_kg = (volume_mm3 * density) / 1_000_000
            cost = mass_kg * price
            return {"mass_kg": round(mass_kg, 3), "cost_usd": round(cost, 2)}
        except Exception as e:
            return {"mass_kg": 0, "cost_usd": 0, "error": str(e)}

# =====================================================
# CLASS ALIASES AND COMPATIBILITY
# =====================================================

MaterialAnalysisService = MaterialAnalysisServiceOptimized
CostEstimationService = CostEstimationServiceFast

def create_service():
    return MaterialAnalysisServiceOptimized()

def extract_enhanced_ocr_data(result, pdf_path, file_type):
    try:
        ocr_data = {
            'raw_text': result.get('raw_ocr_output', ''),
            'confidence': result.get('ocr_confidence', 0),
            'method': result.get('ocr_method_used', 'unknown'),
            'processing_time': result.get('ocr_processing_time', 0),
            'normalization_applied': True, 'debug_info': {}, 'material_keywords_found': [],
            'errors_corrected': [], 'quality_metrics': {}, 'text_blocks': [],
            'confidence_distribution': {}, 'language_detected': 'tr/en', 'has_turkish_content': True
        }
        if result.get('material_matches'):
            for material in result['material_matches']:
                material_name = material.split('(')[0].strip()
                confidence_match = re.search(r'%(\d+)', material)
                confidence = int(confidence_match.group(1)) if confidence_match else 80
                ocr_data['material_keywords_found'].append({
                    'keyword': material_name, 'positions': [0], 'confidence': confidence, 'type': 'material'
                })
        return ocr_data
    except Exception:
        return {'raw_text': '', 'confidence': 0, 'method': 'error', 'processing_time': 0, 'material_keywords_found': []}

def get_material_cache():
    try:
        service = MaterialAnalysisService()
        return service._get_materials_cached_lightning()
    except Exception: return {}

def refresh_pattern_cache():
    try:
        lightning_cache._pattern_cache = None
        lightning_cache._notlar_patterns = None
        lightning_cache._technical_patterns = None
        return True
    except Exception: return False

__all__ = [
    'MaterialAnalysisService', 'MaterialAnalysisServiceOptimized', 'CostEstimationService', 'CostEstimationServiceFast',
    'extract_enhanced_ocr_data', 'get_material_cache', 'refresh_pattern_cache', 'create_service', 'lightning_cache',
    'normalize_text_lightning', 'extract_material_keywords_lightning', 'extract_text_with_lightning_ocr',
    'extract_notlar_section', 'extract_notlar_items', 'find_materials_in_notlar_items', 'extract_explicit_material_fields',
    'extract_technical_drawing_fields', 'find_materials_in_technical_fields', 'resolve_material_from_database',
    'find_materials_in_text_database_only_proven'
]

try:
    lightning_cache._database = db.get_db()
except Exception: pass