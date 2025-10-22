# services/material_analysis.py - COMPLETE ENHANCED VERSION WITH PRIORITIZED DETECTION

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
# PRIORITIZED MATERIAL DETECTION
# =====================================================

def extract_material_keywords_lightning(text):
    """Enhanced keyword extraction with CORRECT PRIORITY ORDER"""
    if not text or len(text.strip()) < 3:
        return []
    
    print(f"[EXTRACT-PRIORITY] Processing {len(text)} chars with PRIORITIZED detection")
    
    # PRIORITY 1: MALZEME: ile açıkça belirtilen alanlar (EN YÜKSEK ÖNCELİK)
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials:
        print(f"[EXTRACT-PRIORITY] PRIORITY 1 - Explicit MALZEME: fields found {len(explicit_materials)} materials")
        return explicit_materials[:5]
    
    # PRIORITY 2: NOTLAR bölümü
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                print(f"[EXTRACT-PRIORITY] PRIORITY 2 - NOTLAR section found {len(notlar_materials)} materials")
                return notlar_materials[:5]
    
    # PRIORITY 3: Genel arama (düşük güvenilirlikle)
    material_keywords = extract_material_keywords_from_text_fixed(text)
    
    if material_keywords:
        # Parça tanımlarından gelen sonuçları filtrele veya düşük güvenilirlik ver
        filtered_keywords = filter_out_part_descriptions(material_keywords, text)
        print(f"[EXTRACT-PRIORITY] PRIORITY 3 - General search found {len(filtered_keywords)} materials")
        return filtered_keywords[:5]
    
    print(f"[EXTRACT-PRIORITY] No materials found with any priority level")
    return []

def extract_explicit_material_fields(text):
    """Extract only explicit MALZEME: fields with FLEXIBLE spacing - HIGHEST PRIORITY"""
    if not text:
        return []
    
    # Flexible MALZEME: patterns - handles various spacing
    explicit_patterns = [
        # Standard patterns with flexible spacing (0-10 spaces allowed)
        r'(?:^|\n)\s*MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})',
        r'(?:^|\n)\s*MATERIAL\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})',
        r'MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})(?:\n|$)',
        r'MATERIAL\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})(?:\n|$)',
        
        # Numbered items in NOTLAR
        r'\d+[-\.]\s{0,5}MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})',
        
        # With STANDART
        r'MALZEME\s{0,5}[/\\]\s{0,5}STANDART\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/]{2,50})',
        
        # Special case for "5- MALZEME: AL 6061-T651" format
        r'5[-\.]\s{0,5}MALZEME\s{0,10}[:]\s{0,10}([A-Z0-9\s\-\+\.\/T]{2,50})',
        
        # Capture next 100 chars after MALZEME: for analysis
        r'MALZEME\s{0,10}[:]\s{0,10}(.{1,100})',
    ]
    
    found_materials = []
    text_upper = text.upper()
    
    print(f"[EXPLICIT-FIELD] Searching for MALZEME: patterns in {len(text_upper)} chars")
    
    for pattern_idx, pattern in enumerate(explicit_patterns):
        try:
            matches = re.finditer(pattern, text_upper, re.MULTILINE | re.DOTALL)
            for match in matches:
                if match.group(1):
                    material_content = match.group(1).strip()
                    
                    # Get context around the match
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text_upper), match.end() + 50)
                    context = text_upper[start_pos:end_pos]
                    
                    print(f"[EXPLICIT-FIELD] Pattern {pattern_idx} found: '{material_content[:50]}...'")
                    print(f"[EXPLICIT-FIELD] Context: ...{context}...")
                    
                    # Clean up the material content
                    # Remove common non-material words that might appear after MALZEME:
                    stop_words = ['ISLEMLER', 'ISLEM', 'NOTLAR', 'NOTE', 'TOLERANS', 'OLCU', 
                                  'BOLGE', 'ZONE', 'SAYFA', 'PAGE', 'REV', 'TARIH', 'DATE']
                    
                    for stop_word in stop_words:
                        if stop_word in material_content:
                            material_content = material_content.split(stop_word)[0].strip()
                    
                    # Extract only the material designation
                    material_patterns = [
                        # Complex specifications
                        r'LEVHA\s+PSZCL\s+(AISI\d{3}[A-Z]?)',  # LEVHA PSZCL AISI316L
                        r'LEVHA\s+.*?(AISI\d{3}[A-Z]?)',  # LEVHA ... AISI316L
                        r'(AISI\s*\d{3}[A-Z]?)',  # AISI316L or AISI 316L
                        r'(AL\s+\d{4}[-\s]*T\d+)',  # AL 6061-T651
                        r'(AA\s+\d{4}[-\s]*T\d+)',  # AA 7075-T6
                        r'([A-Z]{2,4}\s+\d{4}[-\s]*T\d+)',  # Generic aluminum
                        r'(\d{4}[-\s]*T\d+)',  # 6061-T6
                        r'([A-Z0-9]{2,15})',  # Generic material code
                    ]
                    
                    extracted_material = None
                    for mat_pattern in material_patterns:
                        mat_match = re.search(mat_pattern, material_content)
                        if mat_match:
                            extracted_material = mat_match.group(1).strip()
                            print(f"[EXPLICIT-FIELD] Extracted: '{extracted_material}' from '{material_content[:50]}'")
                            break
                    
                    if not extracted_material:
                        # Take first 20 chars as material
                        extracted_material = re.sub(r'[^\w\-\+\s]+', ' ', material_content[:20]).strip()
                    
                    if len(extracted_material) >= 2:
                        # Check if it's not a part description
                        if not is_part_description(extracted_material, text_upper, match.start()):
                            # Resolve material from database
                            resolved_material = resolve_material_from_database(extracted_material)
                            if resolved_material:
                                found_materials.append({
                                    'keyword': extracted_material,
                                    'material_name': resolved_material,
                                    'position': match.start(),
                                    'confidence': 99,  # Highest confidence
                                    'pattern_type': 'explicit_material_field',
                                    'source': 'MALZEME: field',
                                    'pattern_index': pattern_idx,
                                    'context': context
                                })
                                print(f"[EXPLICIT-FIELD] ✅ Found: MALZEME: {extracted_material} -> {resolved_material}")
                            else:
                                print(f"[EXPLICIT-FIELD] ⚠️ Could not resolve: {extracted_material}")
                        else:
                            print(f"[EXPLICIT-FIELD] ❌ Part description ignored: {extracted_material}")
                    
        except re.error as e:
            print(f"[EXPLICIT-FIELD] Pattern {pattern_idx} regex error: {e}")
            continue
    
    print(f"[EXPLICIT-FIELD] Total found: {len(found_materials)} explicit materials")
    return found_materials

def is_part_description(material_text, full_text, position):
    """Check if the material text is actually a part description"""
    # Parça tanımı göstergeleri
    part_indicators = [
        'TANIM', 'NOMENCLATURE', 'DESCRIPTION', 'TITLE',
        'PARÇA', 'PART', 'KAPAMA', 'SULUK', 'ASSEMBLY'
    ]
    
    # Pozisyon etrafındaki metni kontrol et
    context_start = max(0, position - 100)
    context_end = min(len(full_text), position + 100)
    context = full_text[context_start:context_end].upper()
    
    # Eğer parça tanımı göstergesi varsa, düşük öncelik
    for indicator in part_indicators:
        if indicator in context:
            # Ama eğer "MALZEME:" ile başlıyorsa yine de kabul et
            if position > 0 and full_text[max(0, position-10):position].strip().endswith('MALZEME:'):
                return False
            return True
    
    return False

def filter_out_part_descriptions(keywords, text):
    """Filter out keywords that come from part descriptions"""
    filtered = []
    text_upper = text.upper()
    
    for keyword_info in keywords:
        keyword = keyword_info.get('keyword', '')
        position = keyword_info.get('position', 0)
        
        # Parça tanımından geliyorsa güvenilirliği düşür
        if is_part_description(keyword, text_upper, position):
            keyword_info['confidence'] = max(keyword_info.get('confidence', 50) - 30, 20)
            keyword_info['pattern_type'] = 'part_description_low_confidence'
        
        filtered.append(keyword_info)
    
    # Güvenilirliğe göre sırala
    filtered.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    return filtered

def extract_technical_drawing_fields(text):
    """Teknik çizimlerden MALZEME kutucuğunu çıkar - PRIORITIZED VERSION"""
    if not text:
        return {}
    
    # Önce explicit MALZEME: alanlarını ara
    explicit_fields = {}
    text_upper = text.upper()
    
    # Açık MALZEME: tanımlamaları
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
                            'content': field_content,
                            'pattern_index': i,
                            'confidence': 99,  # En yüksek güvenilirlik
                            'type': 'explicit_material_field'
                        }
                        print(f"[TECHNICAL-FIELD-EXPLICIT] Found: MALZEME: {field_content}")
        except re.error:
            continue
    
    # Eğer explicit alan bulunduysa, sadece onu döndür
    if explicit_fields:
        return explicit_fields
    
    # Yoksa diğer technical field'ları ara (daha düşük güvenilirlikle)
    other_field_patterns = [
       r'MATERIAL\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'STANDART\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'STANDARD\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'SPEC\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
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
                    
                    if (len(field_content) >= 2 and 
                        field_content not in ['MM', 'CM', 'INCH', 'TOLERANS', 'BOYUT', 'ÖLÇEK', 'KONTROL', 'ONAY'] and
                        not field_content.isdigit()):
                        
                        field_key = f'field_{len(found_fields)}'
                        found_fields[field_key] = {
                            'content': field_content,
                            'pattern_index': i,
                            'confidence': 85,  # Daha düşük güvenilirlik
                            'type': 'technical_field'
                        }
                        print(f"[TECHNICAL-FIELD] Found field: '{field_content}' (pattern {i})")
        except re.error:
            continue
    
    return found_fields

# =====================================================
# NOTLAR SECTION EXTRACTION (remains same)
# =====================================================

def extract_notlar_section(text):
    """Extract NOTLAR/NOTES section from text"""
    if not text:
        return ""
    
    notlar_patterns = [
        r'NOTLAR\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)',
        r'NOTES\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)',
        r'NOT\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)',
        r'AÇIKLAMALAR\s*:?\s*(.*?)(?=\n\s*[A-Z]{3,}[^a-z]*:|$)'
    ]
    
    text_upper = text.upper()
    
    for pattern in notlar_patterns:
        match = re.search(pattern, text_upper, re.DOTALL | re.MULTILINE)
        if match:
            notlar_content = match.group(1).strip()
            if len(notlar_content) > 10:
                print(f"[NOTLAR-EXTRACT] Found NOTLAR section: {len(notlar_content)} chars")
                return notlar_content
    
    print("[NOTLAR-EXTRACT] No NOTLAR section found")
    return ""

def extract_notlar_items(notlar_text):
    """Extract numbered items from NOTLAR section"""
    if not notlar_text:
        return []
    
    item_pattern = r'(\d+\..*?)(?=\d+\.|$)'
    items = re.findall(item_pattern, notlar_text, re.DOTALL)
    
    processed_items = []
    for i, item in enumerate(items, 1):
        clean_item = item.strip()
        if len(clean_item) > 10:
            processed_items.append({
                'number': i,
                'content': clean_item,
                'length': len(clean_item)
            })
            print(f"[NOTLAR-ITEM-{i}] Found item: {clean_item[:100]}...")
    
    return processed_items

def find_materials_in_notlar_items(items):
    """Find materials in NOTLAR items using enhanced patterns"""
    all_materials = []
    notlar_patterns = lightning_cache.get_notlar_patterns()
    
    for item in items:
        item_content = item['content'].upper()
        item_number = item['number']
        
        print(f"[NOTLAR-MATERIAL-{item_number}] Processing item {item_number}...")
        
        # Önce explicit MALZEME: tanımlamalarını ara
        explicit_pattern = r'MALZEME\s*[:]\s*([A-Z0-9\s\-\+\.\/]{2,50})'
        explicit_match = re.search(explicit_pattern, item_content)
        
        if explicit_match:
            material_text = explicit_match.group(1).strip()
            resolved_material = resolve_material_from_database(material_text)
            
            if resolved_material:
                all_materials.append({
                    'keyword': material_text,
                    'material_name': resolved_material,
                    'position': explicit_match.start(),
                    'confidence': 98,  # Yüksek güvenilirlik
                    'pattern_type': 'notlar_explicit_material',
                    'notlar_item': item_number,
                    'context': item_content[max(0, explicit_match.start()-30):explicit_match.end()+30]
                })
                print(f"[NOTLAR-MATERIAL-{item_number}] Explicit: MALZEME: {material_text} -> {resolved_material}")
                continue
        
        # Diğer pattern'leri dene
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
                    
                    if match.groups():
                        match_text = match.group(1)
                    
                    found_materials.append({
                        'keyword': match_text,
                        'material_name': material_name,
                        'position': match.start(),
                        'confidence': confidence,
                        'pattern_type': pattern_type,
                        'notlar_item': item_number,
                        'context': item_content[max(0, match.start()-30):match.end()+30]
                    })
                    
                    print(f"[NOTLAR-MATERIAL-{item_number}] Found: {match_text} -> {material_name} ({confidence}%)")
                    
            except re.error:
                continue
        
        all_materials.extend(found_materials)
    
    return all_materials

def find_materials_in_technical_fields(fields, materials_cache):
    """Teknik form alanlarından malzeme eşleştir - PRIORITIZED VERSION"""
    if not fields or not materials_cache:
        return []
    
    found_materials = []
    
    for field_key, field_data in fields.items():
        field_content = field_data['content'].strip()
        confidence_base = field_data['confidence']
        
        # Explicit field'lar için daha yüksek güvenilirlik
        if field_data.get('type') == 'explicit_material_field':
            confidence_base = 99
        
        print(f"[TECHNICAL-MATCH] Searching for: '{field_content}' (confidence base: {confidence_base})")
        
        # Direct name matching
        if field_content in materials_cache:
            found_materials.append({
                'keyword': field_content,
                'material_name': field_content,
                'position': 0,
                'confidence': confidence_base,
                'pattern_type': 'technical_field_direct',
                'source': 'technical_drawing_field'
            })
            print(f"[TECHNICAL-MATCH] Direct match: {field_content}")
            continue
        
        # Alias matching
        match_found = False
        for material_name, material_data in materials_cache.items():
            aliases = material_data.get('aliases', [])
            
            # Case insensitive name match
            if material_name.upper() == field_content.upper():
                found_materials.append({
                    'keyword': field_content,
                    'material_name': material_name,
                    'position': 0,
                    'confidence': confidence_base,
                    'pattern_type': 'technical_field_name_match',
                    'source': 'technical_drawing_field'
                })
                print(f"[TECHNICAL-MATCH] Name match: {field_content} -> {material_name}")
                match_found = True
                break
            
            # Alias matching
            for alias in aliases:
                if str(alias).upper() == field_content.upper():
                    found_materials.append({
                        'keyword': field_content,
                        'material_name': material_name,
                        'position': 0,
                        'confidence': confidence_base - 2,
                        'pattern_type': 'technical_field_alias_match',
                        'source': 'technical_drawing_field'
                    })
                    print(f"[TECHNICAL-MATCH] Alias match: {field_content} -> {material_name}")
                    match_found = True
                    break
            
            if match_found:
                break
        
        # Partial matching if no exact match (düşük güvenilirlikle)
        if not match_found:
            for material_name, material_data in materials_cache.items():
                if field_content in material_name.upper():
                    found_materials.append({
                        'keyword': field_content,
                        'material_name': material_name,
                        'position': 0,
                        'confidence': confidence_base - 20,  # Çok düşük güvenilirlik
                        'pattern_type': 'technical_field_partial_match',
                        'source': 'technical_drawing_field'
                    })
                    print(f"[TECHNICAL-MATCH] Partial match: {field_content} -> {material_name}")
                    break
    
    return found_materials

def resolve_material_from_database(captured_material):
    """Resolve captured material text to database material name"""
    try:
        database = db.get_db()
        captured_clean = captured_material.strip().upper()
        
        # Special handling for common materials
        material_mappings = {
            'AL 6061-T651': '6061',
            'AL6061-T651': '6061',
            '6061-T651': '6061',
            'AL 6061': '6061',
            'AL6061': '6061',
            'AL 7075': '7075',
            'AL7075': '7075',
            '7075-T6': '7075',
            'AL 2024': '2024',
            'AL2024': '2024',
            'AISI 304': 'aisi304',
            'AISI304': 'aisi304',
            'AISI 316': 'aisi316',
            'AISI316': 'aisi316',
            'PA6GF30': 'GF30-PA66',
            'PA6 GF30': 'GF30-PA66',
            'POM': 'POM',
            'DELRIN': 'Delrin',
            'TEFLON': 'Teflon',
            'PTFE': 'Teflon',
        }
        
        # Check known mappings first
        for pattern, material_name in material_mappings.items():
            if pattern in captured_clean or captured_clean == pattern:
                return material_name
        
        # Direct name match
        material = database.materials.find_one(
            {"name": {"$regex": f"^{re.escape(captured_clean)}$", "$options": "i"}},
            {"name": 1}
        )
        
        if material:
            return material.get("name")
        
        # Alias match
        material = database.materials.find_one(
            {"aliases": {"$regex": f"^{re.escape(captured_clean)}$", "$options": "i"}},
            {"name": 1}
        )
        
        if material:
            return material.get("name")
        
        # Partial match for common materials
        common_patterns = [
            (r'6061.*', '6061'),
            (r'7075.*', '7075'), 
            (r'2024.*', '2024'),
            (r'304.*', 'aisi304'),
            (r'316.*', 'aisi316'),
            (r'PA6GF30.*', 'GF30-PA66'),
            (r'POM.*', 'POM'),
            (r'DELRIN.*', 'Delrin'),
        ]
        
        for pattern, material_name in common_patterns:
            if re.match(pattern, captured_clean):
                return material_name
        
        return None
        
    except Exception:
        return None

# =====================================================
# HELPER FUNCTIONS (keep existing)
# =====================================================

def normalize_text_lightning(text):
    """Lightning-fast text normalization with aggressive optimizations"""
    if not text or len(text) < 3:
        return ""
    
    text_upper = text.upper()
    
    char_map = str.maketrans({
        'Ç': 'C', 'Ğ': 'G', 'I': 'I', 'İ': 'I',
        'Ö': 'O', 'Ş': 'S', 'Ü': 'U',
        '0': 'O',  # Zero to O in some contexts
        '|': 'I',  # Pipe to I
        '1': 'I'   # 1 to I in some contexts
    })
    
    text_upper = text_upper.translate(char_map)
    
    ocr_corrections = [
        (r'606I\b', '6061'), (r'6O6I\b', '6061'), (r'6O61\b', '6061'),
        (r'7O7S\b', '7075'), (r'7O75\b', '7075'), (r'70T5\b', '7075'),
        (r'2O24\b', '2024'), (r'Z024\b', '2024'),
        (r'3O4\b', '304'), (r'3I6\b', '316'), (r'3I6L\b', '316L'),
        (r'S083\b', '5083'), (r'7OSO\b', '7050'),
        # Plastic OCR corrections
        (r'PA6GF3O\b', 'PA6GF30'), (r'PA6G F30\b', 'PA6GF30'),
    ]
    
    for pattern, replacement in ocr_corrections:
        text_upper = re.sub(pattern, replacement, text_upper)
    
    return text_upper

def clean_ocr_artifacts(text):
    """Enhanced OCR artifact cleaning"""
    if not text:
        return text
    
    cleaning_patterns = [
        (r'([A-Z0-9]{1,3})(BRASS|STEEL|ALUMINUM)', r'\1 \2'),
        (r'([A-Z0-9]{1,3})(BRONZE|COPPER|TITANIUM)', r'\1 \2'),
        # Enhanced cleaning for TECHNICAL sections
        (r'(AA)(\d+)', r'\1 \2'),  # AA6061 -> AA 6061
        (r'(\d+)(T\d+)', r'\1 \2'),  # 6061T6 -> 6061 T6
        (r'(T\d+)([\/\-])(\d+)', r'\1\2\3'),  # Keep T6/651 format
        # Technical drawing field cleaning
        (r'MALZEME[/\\\s]*:?\s*', 'MALZEME: '),  # Normalize MALZEME field
        (r'MATERIAL[:\s]*', 'MATERIAL: '),  # Normalize MATERIAL field
        (r'\s+', ' '),
    ]
    
    cleaned_text = text
    for pattern, replacement in cleaning_patterns:
        cleaned_text = re.sub(pattern, replacement, cleaned_text)
    
    return cleaned_text.strip()

def should_accept_match(match_text, pattern_type, full_text, position):
    """Enhanced pattern acceptance logic"""
    if len(match_text) < 2:
        return False
    
    context_start = max(0, position - 30)
    context_end = min(len(full_text), position + len(match_text) + 30)
    context = full_text[context_start:context_end]
    
    # Enhanced acceptance for explicit material fields
    if 'explicit' in pattern_type.lower():
        return True
    
    # Enhanced acceptance for TECHNICAL and NOTLAR context
    if ('technical' in pattern_type.lower() or 
        'notlar' in pattern_type.lower() or 
        'context' in pattern_type.lower()):
        return True
    
    if 'flexible' in pattern_type:
        if position > 0:
            prev_char = full_text[position - 1]
            if prev_char.isalpha():
                if not any(artifact in full_text[max(0, position-5):position] 
                          for artifact in ['A4', 'SAYFA', 'SECTION', 'OLCEK']):
                    return False
        
        if position + len(match_text) < len(full_text):
            next_char = full_text[position + len(match_text)]
            if next_char.isalpha():
                return False
    
    match_upper = match_text.upper()
    
    if match_upper == 'BRASS':
        material_indicators = ['MATERIAL', 'MALZEME', 'MAT:', 'SPEC:', 'A4']
        if any(indicator in context for indicator in material_indicators):
            return True
        return True
    
    if match_upper.isdigit() and len(match_upper) == 4:
        if match_upper in ['2024', '2025', '2026', '2027', '2028', '2029', '2030']:
            if any(year_indicator in context for year_indicator in ['/', 'YEAR', 'YIL', 'TARIH']):
                return False
        return True
    
    return True

def extract_material_keywords_from_text_fixed(text):
    """Enhanced keyword extraction method - PRIORITIZED VERSION"""
    if not text:
        return []
    
    # First check for explicit MALZEME: fields
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials:
        print(f"[EXTRACT-FIXED] Explicit MALZEME: fields found {len(explicit_materials)} materials")
        return explicit_materials
    
    # Then try NOTLAR section extraction
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                print(f"[EXTRACT-FIXED] NOTLAR priority found {len(notlar_materials)} materials")
                return notlar_materials
    
    # Fallback to general pattern matching
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
                    # Check if it's from a part description and reduce confidence
                    if is_part_description(match_text, text_upper, match.start()):
                        confidence = max(confidence - 30, 20)
                    
                    found_keywords.append({
                        'keyword': match_text,
                        'material_name': material_name,
                        'position': match.start(),
                        'confidence': confidence,
                        'pattern_type': pattern_type,
                        'context': cleaned_text[max(0, match.start()-20):match.end()+20]
                    })
                
        except re.error:
            continue
    
    # Filter and sort
    unique_keywords = []
    seen = {}
    
    sorted_keywords = sorted(found_keywords, key=lambda x: (
        -x['confidence'],
        0 if 'exact' in x['pattern_type'] else 1
    ))
    
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
    """Get patterns from EVERY material in database - PRIORITIZED VERSION"""
    try:
        database = db.get_db()
        materials_cursor = database.materials.find()
        materials_list = list(materials_cursor)
        
        patterns = []
        
        # HIGHEST PRIORITY: Explicit MALZEME: patterns
        explicit_material_patterns = [
            {'pattern': r'(?:^|\n)\s*MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'explicit_malzeme_field'},
            {'pattern': r'MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})(?:\n|$)', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'explicit_malzeme_field_end'},
            {'pattern': r'\d+[-\.]\s*MALZEME\s*[:]\s*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 98, 'type': 'notlar_explicit_malzeme'},
        ]
        
        patterns.extend(explicit_material_patterns)
        print(f"[PATTERN-BUILD] Added {len(explicit_material_patterns)} EXPLICIT MALZEME patterns")
        
        # MEDIUM PRIORITY: Technical drawing patterns
        technical_drawing_patterns = [
            {'pattern': r'MATERIAL[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 90, 'type': 'technical_material_field'},
            {'pattern': r'STANDART[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_standard_field'},
            {'pattern': r'GRADE[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_grade_field'},
            {'pattern': r'SPEC[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 85, 'type': 'technical_spec_field'},
        ]
        
        patterns.extend(technical_drawing_patterns)
        
        # STRONG direct patterns for known materials
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
        
        # Process materials from database with lower confidence
        for material in materials_list:
            material_name = material.get('name', '').strip()
            aliases = material.get('aliases', [])
            
            if material_name:
                if len(material_name) >= 2:
                    escaped_name = re.escape(material_name)
                    
                    patterns.append({
                        'pattern': f'\\b{escaped_name}\\b',
                        'material_name': material_name,
                        'confidence': 70,  # Lower confidence for general matches
                        'type': 'exact_match',
                        'source': 'material_name_exact'
                    })
                
                if aliases:
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip()
                            escaped_alias = re.escape(alias_clean)
                            
                            patterns.append({
                                'pattern': f'\\b{escaped_alias}\\b',
                                'material_name': material_name,
                                'confidence': 65,  # Even lower for aliases
                                'type': 'alias_exact',
                                'source': f'alias_exact:{alias_clean}'
                            })
        
        print(f"[PATTERN-BUILD] Built {len(patterns)} patterns with PRIORITIZED confidence")
        return patterns
        
    except Exception as e:
        print(f"[PATTERN-BUILD] Error: {e}")
        return []

def find_materials_in_text_database_only_proven(text):
    """Enhanced proven method with CORRECT PRIORITY"""
    if not text or len(text.strip()) < 5:
        return []
    
    print(f"[MATERIAL-PROVEN] Using PRIORITIZED proven method for {len(text)} chars")
    
    # PRIORITY 1: MALZEME: ile açıkça belirtilen alanlar
    explicit_materials = extract_explicit_material_fields(text)
    if explicit_materials:
        proven_format_materials = []
        for material in explicit_materials:
            confidence = material['confidence']
            material_name = material['material_name'] 
            formatted_material = f"{material_name} (%{confidence})"
            proven_format_materials.append(formatted_material)
        
        print(f"[MATERIAL-PROVEN] Explicit MALZEME: found {len(proven_format_materials)} materials")
        return proven_format_materials[:5]
    
    # PRIORITY 2: NOTLAR section
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                proven_format_materials = []
                for material in notlar_materials:
                    confidence = material['confidence']
                    material_name = material['material_name'] 
                    formatted_material = f"{material_name} (%{confidence})"
                    proven_format_materials.append(formatted_material)
                
                print(f"[MATERIAL-PROVEN] NOTLAR section found {len(proven_format_materials)} materials")
                return proven_format_materials[:5]
    
    # PRIORITY 3: General search with normalization
    normalized_text = comprehensive_turkish_normalization_from_working(text)
    
    if not normalized_text:
        return []
    
    material_keywords = extract_material_keywords_from_text_fixed(normalized_text)
    
    if not material_keywords:
        print("[MATERIAL-PROVEN] No keywords found with prioritized method")
        return []
    
    # Database lookup
    try:
        database = db.get_db()
        materials_cursor = database.materials.find(
            {},
            {"name": 1, "density": 1, "price_per_kg": 1, "category": 1, "aliases": 1, "is_active": 1}
        )
        materials_list = list(materials_cursor)
        
        materials_cache = {}
        for material in materials_list:
            material_name = material.get('name')
            if material_name and str(material_name).strip() != "":
                materials_cache[material_name] = material
        
        if not materials_cache:
            print("[MATERIAL-PROVEN] No materials in database")
            return []
            
    except Exception as e:
        print(f"[MATERIAL-PROVEN] Database error: {e}")
        return []
    
    found_materials = {}
    
    for keyword_info in material_keywords:
        keyword = keyword_info['keyword']
        material_name = keyword_info['material_name']
        confidence = keyword_info['confidence']
        pattern_type = keyword_info['pattern_type']
        
        if material_name in materials_cache:
            found_materials[material_name] = {
                'confidence': confidence,
                'matched_term': f"prioritized_{keyword}",
                'material': materials_cache[material_name],
                'strategy': 'prioritized_proven_method',
                'source_keyword': keyword,
                'pattern_type': pattern_type
            }
            print(f"[MATERIAL-PROVEN] Found: {material_name} ({confidence}%)")
    
    if found_materials:
        sorted_materials = sorted(found_materials.items(), 
                                key=lambda x: x[1]['confidence'], reverse=True)
        
        result_materials = []
        for material_name, match_info in sorted_materials[:5]:
            confidence = match_info['confidence']
            formatted_material = f"{material_name} (%{confidence})"
            result_materials.append(formatted_material)
        
        print(f"[MATERIAL-PROVEN] Returning {len(result_materials)} prioritized materials")
        return result_materials
    
    print("[MATERIAL-PROVEN] No materials found in prioritized database lookup")
    return []

def comprehensive_turkish_normalization_from_working(text):
    """Enhanced normalization with better material support"""
    if not text:
        return ""
    
    original_text = str(text)
    text = original_text.upper()
    
    material_corrections = {
        "MALZEME": "MALZEME",
        "MATERIEL": "MATERIAL", 
        "MATER1AL": "MATERIAL",
        "MATER_AL": "MATERIAL",
        "AA 7075": "AA7075",
        "AA-7075": "AA7075", 
        "AA_7075": "AA7075",
        "AA 6061": "AA6061",
        "AA-6061": "AA6061",
        "AA_6061": "AA6061",
        "AA 2024": "AA2024",
        "AA-2024": "AA2024",
        "AL 6061-T651": "AL 6061-T651",  # Keep full designation
        "AL6061-T651": "AL 6061-T651",
        "7O75": "7075",
        "7075-T6": "7075T6",
        "7075-T651": "7075T651",
        "6O61": "6061",
        "6061-T6": "6061T6", 
        "6061-T651": "6061T651",
        "2024-T3": "2024T3",
        "PA6GF3O": "PA6GF30",
        "PA6G F30": "PA6GF30",
        "PA 6GF30": "PA6GF30",
    }
    
    for error, correction in material_corrections.items():
        if error in text:
            text = text.replace(error, correction)
            print(f"[NORMALIZE] Fixed: {error} -> {correction}")
    
    turkish_replacements = {
        'Ç': 'C', 'ç': 'C',
        'Ğ': 'G', 'ğ': 'G', 
        'I': 'I', 'ı': 'I',
        'İ': 'I', 'i': 'I',
        'Ö': 'O', 'ö': 'O',
        'Ş': 'S', 'ş': 'S',
        'Ü': 'U', 'ü': 'U'
    }
    
    for turkish_char, english_char in turkish_replacements.items():
        if turkish_char in text:
            text = text.replace(turkish_char, english_char)
    
    final_text = re.sub(r'\s+', ' ', text).strip()
    print(f"[NORMALIZE] Final text sample: {final_text[:200]}...")
    return final_text

# Keep all other existing functions and classes unchanged...
# (LightningPatternCache, optimize_image_for_ocr_lightning, extract_text_with_lightning_ocr, etc.)

# =====================================================
# PATTERN CACHE CLASS (keep existing implementation)
# =====================================================

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
        if self._technical_patterns is None:
            self._technical_patterns = self._build_technical_patterns()
        return self._technical_patterns
    
    def _build_technical_patterns(self):
        try:
            materials = self._database.materials.find({}, {"name": 1, "aliases": 1})
            technical_patterns = []
            
            # Prioritized technical contexts
            technical_contexts = [
                r'(?:^|\n)\s*MALZEME\s*[:]\s*({material}[\w\d\-\s\/]*)',  # Highest priority
                r'MALZEME[/\\\s]*:?\s*({material}[\w\d\-\s\/]*)',
                r'MATERIAL[:\s]*({material}[\w\d\-\s\/]*)',
                r'STANDART[:\s]*({material}[\w\d\-\s\/]*)',
            ]
            
            for material in materials:
                material_name = material.get('name', '').strip()
                aliases = material.get('aliases', [])
                
                if not material_name or len(material_name) < 2:
                    continue
                
                all_names = [material_name] + [str(alias).strip() for alias in aliases if alias]
                
                for name in all_names:
                    if len(name) < 2:
                        continue
                        
                    escaped_name = re.escape(name)
                    
                    for i, context_pattern in enumerate(technical_contexts):
                        pattern = context_pattern.format(material=escaped_name)
                        # Higher confidence for explicit MALZEME: patterns
                        confidence = 99 if i == 0 else (95 - i*2)
                        technical_patterns.append({
                            'pattern': pattern,
                            'material_name': material_name,
                            'confidence': confidence,
                            'type': 'technical_context',
                            'source': f'technical_{name}'
                        })
            
            print(f"[TECHNICAL-PATTERNS] Built {len(technical_patterns)} prioritized technical patterns")
            return technical_patterns
            
        except Exception as e:
            print(f"[TECHNICAL-PATTERNS] Error: {e}")
            return []
    
    def get_notlar_patterns(self):
        if self._notlar_patterns is None:
            self._notlar_patterns = self._build_notlar_patterns()
        return self._notlar_patterns
    
    def _build_notlar_patterns(self):
        try:
            materials = self._database.materials.find({}, {"name": 1, "aliases": 1})
            notlar_patterns = []
            
            # Prioritized NOTLAR contexts
            notlar_contexts = [
                r'MALZEME\s*:?\s*({material}[\w\d\-\s\/]*)',  # Highest priority
                r'MATERIAL\s*:?\s*({material}[\w\d\-\s\/]*)',
                r'ASTM\s+[A-Z]?\d+[A-Z\d\-]*.*?({material}[\w\d\-\s\/]*)',
                r'EN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)', 
                r'DIN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)',
            ]
            
            for material in materials:
                material_name = material.get('name', '').strip()
                aliases = material.get('aliases', [])
                
                if not material_name or len(material_name) < 2:
                    continue
                
                all_names = [material_name] + [str(alias).strip() for alias in aliases if alias]
                
                for name in all_names:
                    if len(name) < 2:
                        continue
                        
                    escaped_name = re.escape(name)
                    
                    for i, context_pattern in enumerate(notlar_contexts):
                        pattern = context_pattern.format(material=escaped_name)
                        # Higher confidence for explicit MALZEME: patterns
                        confidence = 98 if i == 0 else (92 - i*2)
                        notlar_patterns.append({
                            'pattern': pattern,
                            'material_name': material_name,
                            'confidence': confidence,
                            'type': 'notlar_context',
                            'source': f'notlar_{name}'
                        })
            
            print(f"[NOTLAR-PATTERNS] Built {len(notlar_patterns)} prioritized NOTLAR patterns")
            return notlar_patterns
            
        except Exception as e:
            print(f"[NOTLAR-PATTERNS] Error: {e}")
            return []
    
    def get_lightning_patterns(self):
        if self._quick_patterns is None:
            self._quick_patterns = {
                # Common aluminum patterns with lower confidence
                '6061': ('6061', 70), '606I': ('6061', 65), '6O61': ('6061', 65),
                '7075': ('7075', 70), '7O75': ('7075', 65), '70T5': ('7075', 60),
                '2024': ('2024', 70), '2O24': ('2024', 65), 'Z024': ('2024', 60),
                
                # Steel patterns with lower confidence
                '304': ('aisi304', 65), '3O4': ('aisi304', 60), 'AISI304': ('aisi304', 70),
                '316': ('aisi316', 65), '3I6': ('aisi316', 60), 'AISI316': ('aisi316', 70),
                
                # Plastic patterns with lower confidence
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
                if material not in self._material_lookup:
                    self._material_lookup[material] = []
                self._material_lookup[material].append((key, confidence))
        
        return self._material_lookup
    
    def get_cached_patterns(self):
        current_time = time.time()
        
        if (self._pattern_cache is None or 
            current_time - self._pattern_cache_timestamp > self._pattern_cache_ttl):
            
            print("[PATTERN-CACHE] Refreshing prioritized pattern cache...")
            self._pattern_cache = self._build_lightning_patterns()
            self._pattern_cache_timestamp = current_time
            print(f"[PATTERN-CACHE] {len(self._pattern_cache)} prioritized patterns cached")
        
        return self._pattern_cache
    
    def _build_lightning_patterns(self):
        try:
            patterns = []
            materials = self._database.materials.find()
            
            for material in materials:
                name = material.get('name')
                if name:
                    patterns.append({
                        'pattern': name.upper(),
                        'material_name': name,
                        'confidence': 60  # Lower confidence for general patterns
                    })
                    
                    aliases = material.get('aliases', [])
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip().upper()
                            patterns.append({
                                'pattern': alias_clean,
                                'material_name': name,
                                'confidence': 55  # Even lower for aliases
                            })
            
            print(f"[PATTERN-BUILD] Built {len(patterns)} patterns with lower confidence")
            return patterns
            
        except Exception as e:
            print(f"[PATTERN-BUILD] Error: {e}")
            return []

# Global cache instance
lightning_cache = LightningPatternCache()

# =====================================================
# OCR OPTIMIZATION
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

def extract_text_with_lightning_ocr(pdf_path):
    """Enhanced OCR with better technical drawing detection"""
    try:
        print("[OCR-ENHANCED] Using enhanced OCR methods for technical drawings...")
        
        # METHOD 1: Enhanced Tesseract with better config
        try:
            print("[OCR-ENHANCED] Method 1: Enhanced Tesseract for technical drawings...")
            pages = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            
            if pages:
                # Try multiple OCR configurations
                configs = [
                    '--psm 6 --oem 3',  # Standard config
                    '--psm 4 --oem 3',  # Multiple columns
                    '--psm 3 --oem 3',  # Fully automatic
                    '--psm 1 --oem 3',  # Orientation and script detection
                ]
                
                best_text = ""
                best_length = 0
                
                for config in configs:
                    try:
                        text = pytesseract.image_to_string(pages[0], lang='eng+tur', config=config)
                        if text and len(text.strip()) > best_length:
                            best_text = text
                            best_length = len(text.strip())
                            print(f"[OCR-ENHANCED] Config '{config}': {len(text)} chars")
                    except:
                        continue
                
                if best_text and len(best_text.strip()) > 50:
                    print(f"[OCR-ENHANCED] Enhanced Tesseract success: {len(best_text)} chars")
                    return best_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Enhanced Tesseract failed: {e}")
        
        # METHOD 2: Image preprocessing + OCR
        try:
            print("[OCR-ENHANCED] Method 2: Preprocessed image OCR...")
            pages = convert_from_path(pdf_path, dpi=600, first_page=1, last_page=1)
            
            if pages:
                image = pages[0]
                
                # Convert to numpy array for opencv
                import numpy as np
                import cv2
                
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
                
                # Apply various preprocessing techniques
                preprocessed_images = []
                
                # 1. Threshold
                _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                preprocessed_images.append(thresh1)
                
                # 2. Morphological operations
                kernel = np.ones((1,1), np.uint8)
                morph = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
                preprocessed_images.append(morph)
                
                # 3. Gaussian blur + threshold
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                _, thresh2 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                preprocessed_images.append(thresh2)
                
                best_text = ""
                best_length = 0
                
                for i, processed_img in enumerate(preprocessed_images):
                    try:
                        # Convert back to PIL Image
                        pil_image = Image.fromarray(processed_img)
                        text = pytesseract.image_to_string(pil_image, lang='eng+tur', 
                                                        config='--psm 6 --oem 3')
                        
                        if text and len(text.strip()) > best_length:
                            best_text = text
                            best_length = len(text.strip())
                            print(f"[OCR-ENHANCED] Preprocessing {i}: {len(text)} chars")
                    except:
                        continue
                
                if best_text and len(best_text.strip()) > 30:
                    print(f"[OCR-ENHANCED] Preprocessed OCR success: {len(best_text)} chars")
                    return best_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Preprocessed OCR failed: {e}")
        
        # METHOD 3: PyPDF2 fallback
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text and len(text.strip()) > 30:
                        if extract_explicit_material_fields(text):
                            print(f"[OCR-ENHANCED] PyPDF2 with EXPLICIT MATERIAL FIELDS: {len(text)} chars")
                            return text
                        elif extract_notlar_section(text):
                            print(f"[OCR-ENHANCED] PyPDF2 with NOTLAR: {len(text)} chars")
                            return text
                        elif len(text.strip()) > 100:
                            print(f"[OCR-ENHANCED] PyPDF2 success: {len(text)} chars")
                            return text
        except Exception as e:
            print(f"[OCR-ENHANCED] PyPDF2 fallback failed: {e}")
        
        # METHOD 2: Enhanced Tesseract OCR - ALL PAGES
        try:
            print("[OCR-ENHANCED] Using Tesseract for ALL pages...")
            pages = convert_from_path(pdf_path, dpi=600)
            all_text = ""
            
            for page_num, page_image in enumerate(pages):
                try:
                    page_text = pytesseract.image_to_string(page_image, lang='eng+tur', 
                                                    config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-/: ')
                    
                    if page_text:
                        all_text += f"\n--- PAGE {page_num + 1} ---\n" + page_text
                        print(f"[OCR-ENHANCED] Tesseract Page {page_num + 1}: {len(page_text)} chars")
                except Exception as page_error:
                    print(f"[OCR-ENHANCED] Tesseract Page {page_num + 1} error: {page_error}")
                    continue
            
            if all_text and len(all_text.strip()) > 20:
                print(f"[OCR-ENHANCED] Tesseract total: {len(all_text)} chars from {len(pages)} pages")
                return all_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Enhanced Tesseract failed: {e}")
        
        # METHOD 3: Alternative OCR with preprocessing - ALL PAGES
        try:
            print("[OCR-ENHANCED] Trying preprocessed OCR for ALL pages...")
            pages = convert_from_path(pdf_path, dpi=600)
            all_text = ""
            
            for page_num, page_image in enumerate(pages):
                try:
                    enhanced_image = optimize_image_for_ocr_lightning(page_image)
                    page_text = pytesseract.image_to_string(enhanced_image, lang='eng', config='--psm 3')
                    
                    if page_text:
                        all_text += f"\n--- PAGE {page_num + 1} ---\n" + page_text
                        print(f"[OCR-ENHANCED] Preprocessed Page {page_num + 1}: {len(page_text)} chars")
                except Exception as page_error:
                    print(f"[OCR-ENHANCED] Preprocessed Page {page_num + 1} error: {page_error}")
                    continue
            
            if all_text and len(all_text.strip()) > 10:
                print(f"[OCR-ENHANCED] Preprocessed total: {len(all_text)} chars from {len(pages)} pages")
                return all_text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Preprocessed OCR failed: {e}")
        
        print(f"[OCR-ENHANCED] All OCR methods failed")
        return ""
        
    except Exception as e:
        print(f"[OCR-ENHANCED] OCR fatal error: {e}")
        return ""

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
        
        print("[INIT] MaterialAnalysisService PRIORITIZED initializing...")
        try:
            self.database.command('ping')
            print("[INIT] Database connection OK")
            self._preload_essential_materials_lightning()
            print(f"[INIT] PRIORITIZED MaterialAnalysisService ready with {len(self._material_cache)} materials")
        except Exception as init_error:
            print(f"[INIT] Initialization failed: {init_error}")
    
    def _preload_essential_materials_lightning(self):
        """Load ALL materials from database"""
        try:
            print("[CACHE] Loading ALL materials from database...")
            materials_cursor = self.database.materials.find()
            materials_list = list(materials_cursor)
            print(f"[CACHE] Found {len(materials_list)} materials from database")
            
            with self._cache_lock:
                self._material_cache = {}
                
                for material in materials_list:
                    material_name = material.get('name')
                    if material_name:
                        density = material.get('density', 2.7)
                        price_per_kg = material.get('price_per_kg', 10)
                        
                        if density <= 0:
                            density = 2.7
                        if price_per_kg < 0:
                            price_per_kg = 10
                        
                        self._material_cache[material_name] = {
                            'name': material_name,
                            'density': float(density),
                            'price_per_kg': float(price_per_kg),
                            'category': material.get('category', 'Unknown'),
                            'aliases': material.get('aliases', []),
                            'is_active': material.get('is_active', True)
                        }
            
            self._last_cache_update = time.time()
            print(f"[CACHE] ALL {len(self._material_cache)} materials cached")
            
        except Exception as e:
            print(f"[CACHE] Failed: {e}")

    def _get_materials_cached_lightning(self):
        current_time = time.time()
        
        if (not self._material_cache or 
            current_time - self._last_cache_update > self._cache_ttl):
            self._preload_essential_materials_lightning()
        
        return self._material_cache

    def _find_materials_in_text_ultra_fast(self, text):
        """Enhanced material finding with PRIORITIZED detection"""
        if not text or len(text.strip()) < 3:
            return []
        
        print(f"[MATERIAL-ENHANCED] Using PRIORITIZED method for {len(text)} chars")
        materials = find_materials_in_text_database_only_proven(text)
        
        if materials:
            print(f"[MATERIAL-ENHANCED] PRIORITIZED method found: {len(materials)} materials")
            return materials
        
        print("[MATERIAL-ENHANCED] No materials found with prioritized method")
        return []

    def _extract_text_from_pdf_optimized(self, pdf_path):
        return extract_text_with_lightning_ocr(pdf_path)

    def _analyze_pdf_ultra_fast_optimized(self, file_path, result, matched_step_path=None):
        """Enhanced PDF analysis with PRIORITIZED material detection"""
        start_time = time.time()
        result["processing_log"].append("📄 PRIORITIZED PDF analysis starting")
        
        print(f"[PDF-ENHANCED] Prioritized PDF analysis: {os.path.basename(file_path)}")
        
        # MATCHED STEP HANDLING
        if matched_step_path and os.path.exists(matched_step_path):
            print(f"[PDF-ENHANCED] Using matched STEP: {matched_step_path}")
            result["processing_log"].append(f"🔗 Using matched STEP: {os.path.basename(matched_step_path)}")
            
            try:
                result["step_analysis"] = self.analyze_step_file_ultra_fast(matched_step_path)
                result["matched_step_used"] = True
                result["step_source"] = "matched"
                result["extracted_step_path"] = matched_step_path
                result["pdf_step_extracted"] = False
                print(f"[PDF-ENHANCED] Matched STEP analyzed")
            except Exception as e:
                print(f"[PDF-ENHANCED] Matched STEP error: {e}")
                matched_step_path = None
        
        # PRIORITIZED MATERIAL DETECTION
        materials = []
        ocr_method = "none"
        raw_text = ""
        
        try:
            # STRATEGY 1: Enhanced PyPDF2 with PRIORITIZED detection - ALL PAGES
            print("[PDF-ENHANCED] Strategy 1: Enhanced PyPDF2 with PRIORITIZED detection...")
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                all_text = ""
                
                # READ ALL PAGES
                for page_num in range(len(reader.pages)):
                    try:
                        page_text = reader.pages[page_num].extract_text()
                        if page_text:
                            all_text += f"\n--- PAGE {page_num + 1} ---\n" + page_text
                            print(f"[PDF-ENHANCED] Page {page_num + 1}: {len(page_text)} chars extracted")
                    except Exception as page_error:
                        print(f"[PDF-ENHANCED] Page {page_num + 1} extraction error: {page_error}")
                        continue
                
                if all_text and len(all_text.strip()) > 20:
                    print(f"[PDF-ENHANCED] Total PyPDF2 text: {len(all_text)} chars from {len(reader.pages)} pages")
                    
                    # Check for explicit MALZEME: fields first
                    explicit_fields = extract_explicit_material_fields(all_text)
                    if explicit_fields:
                        print("[PDF-ENHANCED] Explicit MALZEME: fields detected in PyPDF2 text")
                        materials = self._find_materials_in_text_ultra_fast(all_text)
                        if materials:
                            print(f"[PDF-ENHANCED] PyPDF2+EXPLICIT found {len(materials)} materials")
                            ocr_method = "pypdf2_explicit_prioritized"
                            raw_text = all_text[:3000]  # Increased to capture more
                    else:
                        # Check for NOTLAR section
                        notlar_section = extract_notlar_section(all_text)
                        if notlar_section and len(notlar_section) > 50:  # Ensure it's a real NOTLAR section
                            print(f"[PDF-ENHANCED] NOTLAR section detected ({len(notlar_section)} chars)")
                            materials = self._find_materials_in_text_ultra_fast(all_text)
                            if materials:
                                print(f"[PDF-ENHANCED] PyPDF2+NOTLAR found {len(materials)} materials")
                                ocr_method = "pypdf2_notlar_prioritized"
                                raw_text = all_text[:3000]
                        else:
                            materials = self._find_materials_in_text_ultra_fast(all_text)
                            if materials:
                                print(f"[PDF-ENHANCED] PyPDF2 found {len(materials)} materials")
                                ocr_method = "pypdf2_prioritized"
                                raw_text = all_text[:3000]
        
        except Exception as pdf_error:
            print(f"[PDF-ENHANCED] Enhanced PyPDF2 strategy failed: {pdf_error}")
        
        # STRATEGY 2: Enhanced OCR with PRIORITIZED detection
        if not materials:
            try:
                print("[PDF-ENHANCED] Strategy 2: Enhanced OCR with PRIORITIZED detection...")
                ocr_text = self._extract_text_from_pdf_optimized(file_path)
                if ocr_text:
                    explicit_fields = extract_explicit_material_fields(ocr_text)
                    if explicit_fields:
                        print("[PDF-ENHANCED] Explicit MALZEME: fields detected in OCR text")
                        ocr_method = "tesseract_explicit_prioritized"
                    else:
                        notlar_section = extract_notlar_section(ocr_text)
                        if notlar_section:
                            print("[PDF-ENHANCED] NOTLAR section detected in OCR text")
                            ocr_method = "tesseract_notlar_prioritized"
                        else:
                            ocr_method = "tesseract_prioritized"
                    
                    materials = self._find_materials_in_text_ultra_fast(ocr_text)
                    if materials:
                        raw_text = ocr_text[:2000]
                        print(f"[PDF-ENHANCED] Enhanced OCR found {len(materials)} materials")
                    
            except Exception as ocr_error:
                print(f"[PDF-ENHANCED] Enhanced OCR strategy failed: {ocr_error}")
        
        # STRATEGY 3: NO DEFAULT MATERIALS - keep empty if none found
        if not materials:
            print("[PDF-ENHANCED] No materials found - keeping empty result")
            materials = []
            ocr_method = "prioritized_no_materials"
        
        # Set material results
        result["material_matches"] = materials
        result["ocr_method"] = ocr_method
        result["raw_ocr_output"] = raw_text
        result["ocr_confidence"] = 99 if "explicit" in ocr_method else (95 if "notlar" in ocr_method else (80 if "prioritized" in ocr_method else 70))
        result["ocr_method_used"] = ocr_method
        result["ocr_processing_time"] = time.time() - start_time
        
        # STEP EXTRACTION (only if needed)
        if not result.get("step_analysis") and materials:
            try:
                print("[PDF-ENHANCED] Enhanced STEP extraction...")
                step_paths = self._extract_step_from_pdf_lightning(file_path)
                
                if step_paths:
                    extracted_step_path = step_paths[0]
                    result["extracted_step_path"] = extracted_step_path
                    result["pdf_step_extracted"] = True
                    result["step_source"] = "extracted"
                    result["step_analysis"] = self.analyze_step_file_ultra_fast(extracted_step_path)
                    print("[PDF-ENHANCED] STEP extracted and analyzed")
                    
                else:
                    result["step_analysis"] = self._get_zero_step_defaults_lightning()
                    result["pdf_step_extracted"] = False
                    result["step_source"] = "none"
                    
            except Exception as step_error:
                print(f"[PDF-ENHANCED] STEP extraction error: {step_error}")
                result["step_analysis"] = self._get_zero_step_defaults_lightning()
        
        if "material_matches" not in result:
            result["material_matches"] = materials
        
        result["material_confidence"] = 99 if "explicit" in ocr_method else (95 if "notlar" in ocr_method else (85 if materials else 0))
        
        total_time = time.time() - start_time
        result["processing_log"].append(f"⚡ PRIORITIZED total time: {total_time:.2f}s")
        
        print(f"[PDF-ENHANCED] Completed in {total_time:.3f}s with {len(result.get('material_matches', []))} materials")
        
        return result

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

    def analyze_document_ultra_fast(self, file_path, file_type, user_id, matched_step_path=None):
        """PRIORITIZED main analysis method"""
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
            print(f"[ENHANCED] PRIORITIZED analysis: {file_path} ({file_type})")
            
            if matched_step_path:
                print(f"[ENHANCED] With matched STEP: {matched_step_path}")
            
            # FILE TYPE SPECIFIC ANALYSIS
            if file_type == 'pdf':
                print("[ENHANCED] Processing PDF with PRIORITIZED analysis...")
                result = self._analyze_pdf_ultra_fast_optimized(file_path, result, matched_step_path)
                
            elif file_type in ['step', 'stp']:
                print("[ENHANCED] Processing STEP with enhanced analysis...")
                try:
                    result["step_analysis"] = self.analyze_step_file_ultra_fast(file_path)
                    result["processing_log"].append("🔧 Enhanced STEP analysis completed")
                except Exception as step_error:
                    print(f"[ENHANCED] STEP analysis error: {step_error}")
                    result["step_analysis"] = self._get_zero_step_defaults_lightning()
                
                if not result.get("material_matches"):
                    result["material_matches"] = []
                        
            elif file_type in ['doc', 'docx']:
                print("[ENHANCED] Processing document with enhanced analysis...")
                result = self._analyze_document_lightning(file_path, result)
            
            # MATERIAL OPTIONS CALCULATION
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)", 0)
            
            if prizma_hacim and prizma_hacim > 0:
                print(f"[ENHANCED] Calculating ALL materials for volume: {prizma_hacim}")
                result["material_options"] = self._calculate_top_materials_lightning(prizma_hacim)
            else:
                result["material_options"] = []
            
            # FOUND MATERIALS CALCULATION
            if result.get("material_matches") and prizma_hacim and prizma_hacim > 0:
                result["all_material_calculations"] = self._calculate_found_materials_lightning(
                    prizma_hacim, result["material_matches"]
                )
            
            # Get ALL database materials if no material options
            if not result.get("material_options") and prizma_hacim and prizma_hacim > 0:
                result["material_options"] = self._get_database_only_materials(prizma_hacim)
            
            if "material_matches" not in result:
                result["material_matches"] = []
            
            total_time = time.time() - start_time
            result["processing_log"].append(f"⚡ PRIORITIZED total time: {total_time:.2f}s")
            
            print(f"[ENHANCED] PRIORITIZED analysis completed in {total_time:.3f}s")
            print(f"[ENHANCED] Materials: {len(result.get('material_matches', []))}, Options: {len(result.get('material_options', []))}")
            
            return result
            
        except Exception as e:
            error_msg = f"PRIORITIZED analysis error: {str(e)}"
            print(f"[ENHANCED] {error_msg}")
            
            result["error"] = error_msg
            result["material_matches"] = []
            result["material_options"] = []
            
            return result

    def _get_database_only_materials(self, prizma_hacim_mm3):
        """Get ALL materials from database"""
        try:
            if prizma_hacim_mm3 <= 0:
                return []
            
            materials_cache = self._get_materials_cached_lightning()
            if not materials_cache:
                return []
            
            materials_list = []
            volume_cm3 = prizma_hacim_mm3 / 1000
            
            print(f"[DATABASE-MATERIALS] Processing ALL {len(materials_cache)} materials...")
            
            for material_name, material in materials_cache.items():
                try:
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    
                    if density <= 0:
                        density = 2.7
                    if price_per_kg < 0:
                        price_per_kg = 10
                    
                    mass_kg = (volume_cm3 * density) / 1000
                    material_cost = mass_kg * price_per_kg
                    
                    materials_list.append({
                        "name": material_name,
                        "category": category,
                        "density": round(density, 2),
                        "mass_kg": round(mass_kg, 3),
                        "price_per_kg": round(price_per_kg, 2),
                        "material_cost": round(material_cost, 2),
                        "volume_mm3": prizma_hacim_mm3,
                        "source": "database_only"
                    })
                    
                except Exception:
                    continue
            
            materials_list.sort(key=lambda x: x["material_cost"])
            result = materials_list
            
            print(f"[DATABASE-MATERIALS] ALL {len(result)} database materials calculated")
            return result
            
        except Exception as e:
            print(f"[DATABASE-MATERIALS] Error: {e}")
            return []
    
    def _calculate_top_materials_lightning(self, prizma_hacim_mm3, limit=None):
        """Calculate top materials"""
        try:
            if prizma_hacim_mm3 <= 0:
                return []
            
            materials_cache = self._get_materials_cached_lightning()
            if not materials_cache:
                return []
            
            top_materials = []
            volume_cm3 = prizma_hacim_mm3 / 1000
            
            print(f"[TOP-MATERIALS] Processing {len(materials_cache)} materials...")
            
            for material_name, material in materials_cache.items():
                try:
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    
                    if density <= 0:
                        density = 2.7
                    if price_per_kg < 0:
                        price_per_kg = 10
                    
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
                        "source": "prioritized_cache"
                    })
                    
                except Exception:
                        continue
            
            top_materials.sort(key=lambda x: x["material_cost"])
            
            if limit:
                result = top_materials[:limit]
            else:
                result = top_materials
            
            print(f"[TOP-MATERIALS-ENHANCED] {len(result)} materials calculated")
            return result
            
        except Exception as e:
            print(f"[TOP-MATERIALS-ENHANCED] Error: {e}")
            return []

    def _calculate_found_materials_lightning(self, prizma_hacim_mm3, found_materials):
        """Calculate found materials"""
        try:
            if prizma_hacim_mm3 <= 0 or not found_materials:
                return []
                
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
                
                if not material:
                    continue
                
                try:
                    density = material.get("density", 2.7)
                    price_per_kg = material.get("price_per_kg", 10)
                    
                    if density <= 0 or price_per_kg < 0:
                        continue
                    
                    confidence_match = re.search(r'%(\d+)', material_text)
                    confidence = int(confidence_match.group(1)) if confidence_match else 80
                    
                    mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                    material_cost = round(mass_kg * price_per_kg, 2)
                    
                    calculations.append({
                        "material": material.get("name", material_name),
                        "confidence": f"%{confidence}",
                        "density": density,
                        "mass_kg": mass_kg,
                        "price_per_kg": price_per_kg,
                        "material_cost": material_cost,
                        "volume_mm3": prizma_hacim_mm3,
                        "source": "prioritized_cache"
                    })
                    
                except Exception:
                    continue
            
            print(f"[CALC-ENHANCED] {len(calculations)} materials calculated")
            return calculations
            
        except Exception as e:
            print(f"[CALC-ENHANCED] Error: {e}")
            return []

    def _calculate_found_materials_database_only(self, prizma_hacim_mm3, found_materials):
        """Database-only found materials calculation"""
        try:
            print(f"[CALC-DB-ONLY] Database-only calculation for {len(found_materials)} materials")
            
            if prizma_hacim_mm3 <= 0 or not found_materials:
                return []
                
            calculations = []
            
            for material_text in found_materials[:3]:
                material_name = material_text.split("(")[0].strip()
                
                try:
                    material = self.database.materials.find_one(
                        {"name": material_name},
                        {"name": 1, "density": 1, "price_per_kg": 1, "category": 1}
                    )
                    
                    if not material:
                        material = self.database.materials.find_one(
                            {"name": {"$regex": f"^{re.escape(material_name)}$", "$options": "i"}},
                            {"name": 1, "density": 1, "price_per_kg": 1, "category": 1}
                        )
                    
                    if material:
                        density = material.get("density", 2.7)
                        price_per_kg = material.get("price_per_kg", 10)
                        category = material.get("category", "Unknown")
                        
                        if density <= 0:
                            density = 2.7
                        if price_per_kg is None or price_per_kg < 0:
                            price_per_kg = 10
                        
                        confidence_match = re.search(r'%(\d+)', material_text)
                        confidence = int(confidence_match.group(1)) if confidence_match else 80
                        
                        mass_kg = round((prizma_hacim_mm3 * density) / 1_000_000, 3)
                        material_cost = round(mass_kg * price_per_kg, 2)
                        
                        calculations.append({
                            "material": material.get("name", material_name),
                            "confidence": f"%{confidence}",
                            "density": density,
                            "mass_kg": mass_kg,
                            "price_per_kg": price_per_kg,
                            "material_cost": material_cost,
                            "volume_mm3": prizma_hacim_mm3,
                            "category": category,
                            "source": "database_only"
                        })
                        
                        print(f"[CALC-DB-ONLY] {material_name}: {mass_kg}kg, ${material_cost}")
                    
                except Exception as material_error:
                    print(f"[CALC-DB-ONLY] Material {material_name} error: {material_error}")
                    continue
            
            print(f"[CALC-DB-ONLY] {len(calculations)} materials calculated from database")
            return calculations
            
        except Exception as e:
            print(f"[CALC-DB-ONLY] Database calculation error: {e}")
            return []

    def _calculate_top_materials_database_only(self, prizma_hacim_mm3, limit=None):
        """Database-only top materials calculation"""
        try:
            if prizma_hacim_mm3 <= 0:
                return []
            
            materials_cursor = self.database.materials.find(
                {},
                {"name": 1, "density": 1, "price_per_kg": 1, "category": 1}
            )
            
            top_materials = []
            volume_cm3 = prizma_hacim_mm3 / 1000
            
            for material in materials_cursor:
                try:
                    material_name = material.get("name")
                    if not material_name:
                        continue
                    
                    density = float(material.get("density", 2.7))
                    price_per_kg = float(material.get("price_per_kg", 10))
                    category = material.get("category", "Unknown")
                    
                    if density <= 0:
                        density = 2.7
                    if price_per_kg < 0:
                        price_per_kg = 10
                    
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
                        "source": "database_only"
                    })
                    
                except Exception:
                    continue
            
            top_materials.sort(key=lambda x: x["material_cost"])
            
            if limit:
                result = top_materials[:limit]
            else:
                result = top_materials
            
            print(f"[TOP-MATERIALS-DB-ONLY] {len(result)} materials calculated from database")
            return result
            
        except Exception as e:
            print(f"[TOP-MATERIALS-DB-ONLY] Error: {e}")
            return []

    def _analyze_document_lightning(self, file_path, result):
        """Document analysis"""
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
            result["processing_log"].append(f"🔍 Document: {len(materials)} materials found")
            result["step_analysis"] = self._get_zero_step_defaults_lightning()
            
        except Exception as e:
            result["processing_log"].append(f"❌ Document analysis error: {e}")
            result["material_matches"] = []
            result["step_analysis"] = self._get_zero_step_defaults_lightning()
            
        return result

    def _extract_text_from_docx_lightning(self, file_path):
        try:
            doc = Document(file_path)
            texts = [p.text for p in doc.paragraphs[:5] if p.text.strip()]
            return "\n".join(texts)
        except Exception as e:
            print(f"[DOCX-ENHANCED] Failed: {e}")
            return ""
    
    def _extract_text_from_doc_lightning(self, file_path):
        try:
            output_dir = os.path.dirname(file_path)
            result = subprocess.run([
                "libreoffice", "--headless", "--convert-to", "docx", 
                "--outdir", output_dir, file_path
            ], capture_output=True, timeout=5)
            
            docx_path = os.path.splitext(file_path)[0] + ".docx"
            if os.path.exists(docx_path):
                text = self._extract_text_from_docx_lightning(docx_path)
                try:
                    os.remove(docx_path)
                except:
                    pass
                return text
            return ""
        except Exception as e:
            print(f"[DOC-ENHANCED] Failed: {e}")
            return ""

    def analyze_step_file_ultra_fast(self, step_path):
        """STEP analysis"""
        try:
            start_time = time.time()
            
            try:
                assembly = cq.importers.importStep(step_path)
                if not assembly.objects:
                    return self._get_zero_step_defaults("Empty STEP file")
            except Exception as import_error:
                return self._get_zero_step_defaults(f"Import failed: {str(import_error)}")
            
            shapes = assembly.objects
            if not shapes:
                return self._get_zero_step_defaults("No shapes found")
            
            main_shape = max(shapes, key=lambda s: s.Volume())
            main_bbox = main_shape.BoundingBox()
            
            x, y, z = main_bbox.xlen, main_bbox.ylen, main_bbox.zlen
            
            x_pad = max(int(x) + 10, 10) if x > 0 else 0
            y_pad = max(int(y) + 10, 10) if y > 0 else 0
            z_pad = max(int(z) + 10, 10) if z > 0 else 0
            
            volume_padded = x_pad * y_pad * z_pad if x_pad > 0 and y_pad > 0 and z_pad > 0 else 0
            
            try:
                product_volume = main_shape.Volume()
                total_surface_area = main_shape.Area()
            except:
                product_volume = x * y * z * 0.75 if x > 0 and y > 0 and z > 0 else 0
                total_surface_area = 2 * (x*y + y*z + x*z) * 1.2 if x > 0 and y > 0 and z > 0 else 0
            
            waste_volume = max(volume_padded - product_volume, 0) if volume_padded > 0 else 0
            waste_ratio = (waste_volume / volume_padded * 100) if volume_padded > 0 else 0
            
            analysis_time = time.time() - start_time
            
            result = {
                "X (mm)": round(x, 2),
                "Y (mm)": round(y, 2),
                "Z (mm)": round(z, 2),
                "Silindirik Çap (mm)": round(max(x, y), 2) if x > 0 and y > 0 else 0,
                "Silindirik Yükseklik (mm)": round(z, 2),
                "X+Pad (mm)": x_pad,
                "Y+Pad (mm)": y_pad,
                "Z+Pad (mm)": z_pad,
                "Prizma Hacmi (mm³)": round(volume_padded, 1),
                "Ürün Hacmi (mm³)": round(product_volume, 1),
                "Talaş Hacmi (mm³)": round(waste_volume, 1),
                "Talaş Oranı (%)": round(waste_ratio, 1),
                "Toplam Yüzey Alanı (mm²)": round(total_surface_area, 1),
                "analysis_time": analysis_time,
                "method": "prioritized_optimized"
            }
            
            print(f"[STEP-ENHANCED] Analysis completed in {analysis_time:.3f}s")
            return result
            
        except Exception as e:
            print(f"[STEP-ENHANCED] Analysis failed: {str(e)}")
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
        """Fast STEP extraction - ENHANCED VERSION"""
        try:
            extracted = []
            start_time = time.time()
            TIMEOUT_SECONDS = 10.0  # Artırıldı
            
            print(f"[STEP-EXTRACT] Starting enhanced STEP search: {os.path.basename(pdf_path)}")
            
            with pikepdf.open(pdf_path) as pdf:
                
                # METHOD 1: Embedded Files (mevcut kod geliştirildi)
                try:
                    print("[STEP-EXTRACT] Method 1: Embedded Files...")
                    root = pdf.trailer.get("/Root", {})
                    if root:
                        names = root.get("/Names", {})
                        if names:
                            embedded = names.get("/EmbeddedFiles", {})
                            if embedded:
                                files = embedded.get("/Names", [])
                                print(f"[STEP-EXTRACT] Found {len(files)//2} embedded files")
                                
                                for i in range(0, min(len(files), 20), 2):
                                    if time.time() - start_time > TIMEOUT_SECONDS:
                                        break
                                    
                                    if i + 1 < len(files):
                                        try:
                                            file_spec = files[i + 1]
                                            file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                                            print(f"[STEP-EXTRACT] Checking embedded: {file_name}")
                                            
                                            if file_name.lower().endswith(('.stp', '.step')):
                                                ef = file_spec.get('/EF', {})
                                                if ef and '/F' in ef:
                                                    file_data = ef['/F'].read_bytes()
                                                    
                                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                                    os.makedirs(temp_dir, exist_ok=True)
                                                    
                                                    safe_filename = f"embedded_{int(time.time())}.step"
                                                    output_path = os.path.join(temp_dir, safe_filename)
                                                    
                                                    with open(output_path, 'wb') as f:
                                                        f.write(file_data)
                                                    
                                                    if os.path.getsize(output_path) > 100:
                                                        extracted.append(output_path)
                                                        print(f"[STEP-EXTRACT] ✅ Embedded STEP found: {file_name}")
                                                        return extracted
                                                    else:
                                                        os.remove(output_path)
                                                
                                        except Exception as e:
                                            print(f"[STEP-EXTRACT] Embedded file error: {e}")
                                            continue
                            else:
                                print("[STEP-EXTRACT] No EmbeddedFiles found")
                        else:
                            print("[STEP-EXTRACT] No Names dictionary found")
                    else:
                        print("[STEP-EXTRACT] No Root found")
                                        
                except Exception as e:
                    print(f"[STEP-EXTRACT] Embedded files method error: {e}")
                
                # METHOD 2: FileAttachment Annotations
                try:
                    print("[STEP-EXTRACT] Method 2: FileAttachment annotations...")
                    for page_num, page in enumerate(pdf.pages):
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            break
                            
                        if "/Annots" in page:
                            annotations = page["/Annots"]
                            print(f"[STEP-EXTRACT] Page {page_num+1} has {len(annotations)} annotations")
                            
                            for annot_ref in annotations:
                                try:
                                    annot_obj = pdf.get_object(annot_ref)
                                    subtype = annot_obj.get("/Subtype")
                                    
                                    if subtype == "/FileAttachment":
                                        file_spec = annot_obj.get("/FS")
                                        if file_spec:
                                            file_name = str(file_spec.get("/UF", file_spec.get("/F", ""))).strip("()")
                                            print(f"[STEP-EXTRACT] Found attachment: {file_name}")
                                            
                                            if file_name.lower().endswith(('.stp', '.step')):
                                                ef = file_spec.get("/EF")
                                                if ef and "/F" in ef:
                                                    stream = ef["/F"]
                                                    file_data = stream.read_bytes()
                                                    
                                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                                    os.makedirs(temp_dir, exist_ok=True)
                                                    output_path = os.path.join(temp_dir, f"attachment_{int(time.time())}.step")
                                                    
                                                    with open(output_path, 'wb') as f:
                                                        f.write(file_data)
                                                    
                                                    if os.path.getsize(output_path) > 100:
                                                        extracted.append(output_path)
                                                        print(f"[STEP-EXTRACT] ✅ Extracted STEP from annotation: {file_name}")
                                                        return extracted
                                                    else:
                                                        os.remove(output_path)
                                except Exception as annot_error:
                                    print(f"[STEP-EXTRACT] Annotation error: {annot_error}")
                                    continue
                                    
                except Exception as e:
                    print(f"[STEP-EXTRACT] Annotation method error: {e}")
                
                # METHOD 3: Scan all objects for STEP data
                try:
                    print("[STEP-EXTRACT] Method 3: Scanning objects for STEP data...")
                    max_objects_to_check = min(len(pdf.objects), 500)  # Check first 500 objects
                    
                    for obj_num in range(max_objects_to_check):
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            break
                            
                        try:
                            obj = pdf.objects[obj_num]
                            if obj and hasattr(obj, 'read_bytes'):
                                data = obj.read_bytes()
                                
                                # Check if this is STEP data
                                if self._is_step_data_fast(data):
                                    print(f"[STEP-EXTRACT] Found STEP data in object {obj_num}")
                                    
                                    temp_dir = os.path.join(os.getcwd(), "temp")
                                    os.makedirs(temp_dir, exist_ok=True)
                                    output_path = os.path.join(temp_dir, f"object_{obj_num}_{int(time.time())}.step")
                                    
                                    with open(output_path, 'wb') as f:
                                        f.write(data)
                                    
                                    if os.path.getsize(output_path) > 100:
                                        extracted.append(output_path)
                                        print(f"[STEP-EXTRACT] ✅ Extracted STEP from object {obj_num}")
                                        return extracted
                                    else:
                                        os.remove(output_path)
                        except:
                            continue
                            
                except Exception as e:
                    print(f"[STEP-EXTRACT] Object scanning error: {e}")
                
                # METHOD 4: Check 3D annotations
                try:
                    print("[STEP-EXTRACT] Method 4: 3D annotations...")
                    for page_num, page in enumerate(pdf.pages):
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            break
                            
                        if "/Annots" in page:
                            for annot_ref in page["/Annots"]:
                                try:
                                    annot = pdf.get_object(annot_ref)
                                    if annot.get("/Subtype") == "/3D":
                                        print(f"[STEP-EXTRACT] Found 3D annotation on page {page_num+1}")
                                        
                                        # Check for 3DD stream
                                        streams = annot.get("/3DD")
                                        if streams:
                                            stream_data = streams.read_bytes()
                                            
                                            if self._is_step_data_fast(stream_data):
                                                temp_dir = os.path.join(os.getcwd(), "temp")
                                                os.makedirs(temp_dir, exist_ok=True)
                                                output_path = os.path.join(temp_dir, f"3d_model_{int(time.time())}.step")
                                                
                                                with open(output_path, 'wb') as f:
                                                    f.write(stream_data)
                                                
                                                if os.path.getsize(output_path) > 100:
                                                    extracted.append(output_path)
                                                    print(f"[STEP-EXTRACT] ✅ Extracted STEP from 3D annotation")
                                                    return extracted
                                                else:
                                                    os.remove(output_path)
                                except:
                                    continue
                                    
                except Exception as e:
                    print(f"[STEP-EXTRACT] 3D annotation method error: {e}")
                
                # METHOD 5: Check for U3D or PRC data (can contain STEP)
                try:
                    print("[STEP-EXTRACT] Method 5: U3D/PRC data...")
                    for obj_num in range(min(len(pdf.objects), 200)):
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            break
                            
                        try:
                            obj = pdf.objects[obj_num]
                            if obj and hasattr(obj, 'get'):
                                subtype = obj.get("/Subtype")
                                if subtype in ["/U3D", "/PRC"]:
                                    print(f"[STEP-EXTRACT] Found {subtype} object")
                                    
                                    if hasattr(obj, 'read_bytes'):
                                        data = obj.read_bytes()
                                        
                                        # Check if contains STEP data
                                        if b'STEP' in data or b'ISO-10303' in data:
                                            # Try to extract STEP portion
                                            step_start = data.find(b'ISO-10303-21')
                                            if step_start >= 0:
                                                step_data = data[step_start:]
                                                
                                                temp_dir = os.path.join(os.getcwd(), "temp")
                                                os.makedirs(temp_dir, exist_ok=True)
                                                output_path = os.path.join(temp_dir, f"u3d_step_{int(time.time())}.step")
                                                
                                                with open(output_path, 'wb') as f:
                                                    f.write(step_data)
                                                
                                                if os.path.getsize(output_path) > 100:
                                                    extracted.append(output_path)
                                                    print(f"[STEP-EXTRACT] ✅ Extracted STEP from {subtype}")
                                                    return extracted
                        except:
                            continue
                            
                except Exception as e:
                    print(f"[STEP-EXTRACT] U3D/PRC method error: {e}")
                
                # Final summary
                if not extracted:
                    print(f"[STEP-EXTRACT] ❌ No STEP files found after checking all methods")
                    print(f"[STEP-EXTRACT] Total time: {time.time() - start_time:.2f}s")
                
                return extracted
                
        except Exception as e:
            print(f"[STEP-EXTRACT] Fatal STEP extraction error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _is_step_data_fast(self, data):
        """Check if data is STEP format"""
        try:
            if len(data) < 100:
                return False
            
            # Check for STEP file signatures
            step_signatures = [
                b'ISO-10303-21',
                b'HEADER;',
                b'FILE_DESCRIPTION',
                b'FILE_NAME',
                b'STEP AP'
            ]
            
            for signature in step_signatures:
                if signature in data[:1000]:
                    return True
            
            return False
        except:
            return False
    
    def _save_step_data_fast(self, data, filename):
        """Save STEP data to file"""
        try:
            temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            output_path = os.path.join(temp_dir, filename)
            
            with open(output_path, 'wb') as f:
                f.write(data)
            
            if os.path.getsize(output_path) > 100:
                return [output_path]
            else:
                os.remove(output_path)
                return []
        except:
            return []
    
    def refresh_material_cache(self):
        with self._cache_lock:
            self._material_cache = {}
            self._last_cache_update = 0
        
        self._preload_essential_materials_lightning()
        lightning_cache._pattern_cache = None
        lightning_cache._notlar_patterns = None
        lightning_cache._technical_patterns = None
        print("[CACHE] PRIORITIZED material cache refreshed")

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
                "material": {
                    "name": material_name,
                    "cost_usd": material_cost["cost_usd"],
                    "mass_kg": material_cost["mass_kg"]
                },
                "machining": {
                    "hours": round(labor_hours, 2),
                    "cost_usd": round(labor_cost, 2)
                },
                "costs": {
                    "material_usd": material_cost["cost_usd"],
                    "labor_usd": round(labor_cost, 2),
                    "total_usd": round(total, 2)
                }
            }
            
        except Exception as e:
            return {"error": f"Cost calculation error: {str(e)}"}
    
    def _calculate_material_cost_lightning(self, volume_mm3, material_name):
        try:
            if volume_mm3 <= 0:
                return {"mass_kg": 0, "cost_usd": 0}
            
            current_time = time.time()
            cache_key = material_name
            
            if (cache_key in self._price_cache and 
                current_time - self._cache_timestamp < self._cache_ttl):
                cached_data = self._price_cache[cache_key]
                density = cached_data['density']
                price = cached_data['price']
            else:
                material = self.database.materials.find_one(
                    {"name": material_name}, 
                    {"density": 1, "price_per_kg": 1}
                )
                
                if material:
                    density = material.get("density", 2.7)
                    price = material.get("price_per_kg", 10)
                else:
                    if any(pattern in material_name.lower() for pattern in ['6061', '7075', '2024', 'aluminum', 'aluminium']):
                        density, price = 2.7, 5.0
                    elif any(pattern in material_name.lower() for pattern in ['304', '316', 'steel', 'stainless']):
                        density, price = 7.93, 9.0
                    elif 'brass' in material_name.lower():
                        density, price = 8.5, 13.0
                    elif 'copper' in material_name.lower():
                        density, price = 8.96, 15.0
                    elif any(pattern in material_name.lower() for pattern in ['pa6gf30', 'pom', 'delrin', 'pmma', 'plastic']):
                        density, price = 1.4, 20.0
                    else:
                        density, price = 2.7, 12
                
                self._price_cache[cache_key] = {'density': density, 'price': price}
                self._cache_timestamp = current_time
            
            volume_cm3 = volume_mm3 / 1000
            mass_kg = (volume_cm3 * density) / 1000
            cost = mass_kg * price
            
            return {
                "mass_kg": round(mass_kg, 3),
                "cost_usd": round(cost, 2)
            }
            
        except Exception as e:
            return {"mass_kg": 0, "cost_usd": 0, "error": str(e)}

# =====================================================
# CLASS ALIASES AND COMPATIBILITY
# =====================================================

MaterialAnalysisService = MaterialAnalysisServiceOptimized
CostEstimationService = CostEstimationServiceFast

def create_service():
    return MaterialAnalysisServiceOptimized()

# =====================================================
# COMPATIBILITY FUNCTIONS
# =====================================================

def extract_enhanced_ocr_data(result, pdf_path, file_type):
    """Extract OCR data from analysis result"""
    try:
        ocr_data = {
            'raw_text': result.get('raw_ocr_output', ''),
            'confidence': result.get('ocr_confidence', 0),
            'method': result.get('ocr_method_used', 'unknown'),
            'processing_time': result.get('ocr_processing_time', 0),
            'normalization_applied': True,
            'debug_info': {},
            'material_keywords_found': [],
            'errors_corrected': [],
            'quality_metrics': {},
            'text_blocks': [],
            'confidence_distribution': {},
            'language_detected': 'tr/en',
            'has_turkish_content': True
        }
        
        # Extract material keywords with positions
        if result.get('material_matches'):
            for material in result['material_matches']:
                material_name = material.split('(')[0].strip()
                confidence_match = re.search(r'%(\d+)', material)
                confidence = int(confidence_match.group(1)) if confidence_match else 80
                
                keyword_info = {
                    'keyword': material_name,
                    'positions': [0],  # Default position
                    'confidence': confidence,
                    'type': 'material'
                }
                ocr_data['material_keywords_found'].append(keyword_info)
        
        return ocr_data
        
    except Exception as e:
        print(f"[OCR-DATA-EXTRACT] Error: {e}")
        return {
            'raw_text': '',
            'confidence': 0,
            'method': 'error',
            'processing_time': 0,
            'material_keywords_found': []
        }

def get_material_cache():
    try:
        service = MaterialAnalysisService()
        return service._get_materials_cached_lightning()
    except Exception as e:
        print(f"[CACHE-COMPAT] Error: {e}")
        return {}

def refresh_pattern_cache():
    try:
        lightning_cache._pattern_cache = None
        lightning_cache._notlar_patterns = None
        lightning_cache._technical_patterns = None
        lightning_cache._pattern_cache_timestamp = 0
        print("[CACHE-COMPAT] Pattern cache refreshed")
        return True
    except Exception as e:
        print(f"[CACHE-COMPAT] Error: {e}")
        return False

# Export all functions
__all__ = [
    'MaterialAnalysisService',
    'MaterialAnalysisServiceOptimized', 
    'CostEstimationService',
    'CostEstimationServiceFast',
    'extract_enhanced_ocr_data',
    'get_material_cache',
    'refresh_pattern_cache',
    'create_service',
    'lightning_cache',
    'normalize_text_lightning',
    'extract_material_keywords_lightning',
    'extract_text_with_lightning_ocr',
    'extract_notlar_section',
    'extract_notlar_items',
    'find_materials_in_notlar_items',
    'extract_explicit_material_fields',
    'extract_technical_drawing_fields',
    'find_materials_in_technical_fields',
    'resolve_material_from_database',
    'find_materials_in_text_database_only_proven'
]

# =====================================================
# INITIALIZATION
# =====================================================

try:
    lightning_cache._database = db.get_db()
    print("[INIT] Lightning cache database connection established")
except Exception as e:
    print(f"[INIT] Lightning cache database connection failed: {e}")

print("\n" + "="*60)
print("🔧 PRIORITIZED MATERIAL ANALYSIS VERIFICATION")
print("="*60)

# Test explicit material field extraction
test_text_explicit = "MALZEME: AL 6061-T651\nTOLERANS: DIN ISO 2768"
explicit_fields = extract_explicit_material_fields(test_text_explicit)
print(f"✅ Explicit material extraction: {len(explicit_fields)} materials found")

# Test NOTLAR extraction  
test_text_notlar = "NOTLAR:\n1-MALZEME: AL 6061-T651 KULLANILACAKTIR.\n2-KESKİN KÖŞELER KIRILACAKTIR."
notlar = extract_notlar_section(test_text_notlar)
print(f"✅ NOTLAR extraction: {'Found' if notlar else 'Not found'}")

# Test material matching
try:
    service = MaterialAnalysisService()
    cache_size = len(service._get_materials_cached_lightning())
    print(f"✅ Material cache: {cache_size} materials loaded")
except Exception as e:
    print(f"❌ Material cache error: {e}")

print("="*60)
print("🎯 PRIORITIZED FUNCTIONALITY READY!")
print("="*60)

print("\n" + "🚀 PRIORITIZED MATERIAL ANALYSIS SERVICE FULLY LOADED! 🚀")
print("📋 Priority order:")
print("  1. Explicit MALZEME: fields (99% confidence)")
print("  2. NOTLAR section materials (95-98% confidence)")
print("  3. General search (20-70% confidence)")
print("\n✨ Ready to detect materials with correct priority! ✨")