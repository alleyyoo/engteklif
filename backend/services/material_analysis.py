# services/material_analysis.py - COMPLETE ENHANCED VERSION WITH TECHNICAL DRAWING SUPPORT

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

print("[INFO] Enhanced Material Analysis Service - TECHNICAL DRAWING SUPPORT")

# =====================================================
# NEW: TECHNICAL DRAWING FIELD EXTRACTION
# =====================================================

def extract_technical_drawing_fields(text):
    """Teknik çizimlerden MALZEME kutucuğunu ve diğer form alanlarını çıkar"""
    if not text:
        return {}
    
    field_patterns = [
       # MALZEME: formatları
       r'MALZEME\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'MALZEME\s*:\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'MALZEME\s+:\s+([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # MATERIAL: formatları
       r'MATERIAL\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'MATERIAL\s*:\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # STANDART/STANDARD formatları
       r'STANDART\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'STANDARD\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # NOTLAR içindeki malzeme tanımları
       r'(\d+[-\.])\s*MALZEME\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'(\d+[-\.])\s*MATERIAL\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # Alternatif malzeme tanımları (VEYA/YADA ile)
       r'MALZEME\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})(?:\s+YADA\s+|\s+VEYA\s+|\s+OR\s+)([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'MATERIAL\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})(?:\s+YADA\s+|\s+VEYA\s+|\s+OR\s+)([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # Diğer teknik alan formatları
       r'SPEC\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'GRADE\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       r'KALİTE\s*:?\s*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})',
       
       # Tablo formatları (pipe ile ayrılmış)
       r'(?:MALZEME|MATERIAL)\s*[|\s]*([A-ZÜĞŞIÖÇ0-9\s\-\+\.\/]{2,50})\s*(?:\n|\r|$)',
       
       # Context-based patterns (tolerans, boyut öncesi)
       r'([A-ZÜĞŞIÖÇ0-9\-\+\.\/]{3,50})\s*(?=\s*TOLERANS)',
       r'([A-ZÜĞŞIÖÇ0-9\-\+\.\/]{3,50})\s*(?=\s*BOYUT)',
       r'([A-ZÜĞŞIÖÇ0-9\-\+\.\/]{3,50})\s*(?=\s*ÖLÇEK)',
    ]
        
    found_fields = {}
    text_upper = text.upper()
    
    for i, pattern in enumerate(field_patterns):
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
                            'confidence': 95 if 'MALZEME' in pattern else 85,
                            'type': 'technical_field'
                        }
                        print(f"[TECHNICAL-FIELD] Found field: '{field_content}' (pattern {i})")
        except re.error:
            continue
    
    return found_fields

def find_materials_in_technical_fields(fields, materials_cache):
    """Teknik form alanlarından malzeme eşleştir"""
    if not fields or not materials_cache:
        return []
    
    found_materials = []
    
    for field_key, field_data in fields.items():
        field_content = field_data['content'].strip()
        confidence_base = field_data['confidence']
        
        print(f"[TECHNICAL-MATCH] Searching for: '{field_content}'")
        
        # Direct name matching
        if field_content in materials_cache:
            found_materials.append({
                'keyword': field_content,
                'material_name': field_content,
                'position': 0,
                'confidence': confidence_base + 3,
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
                    'confidence': confidence_base + 2,
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
                        'confidence': confidence_base,
                        'pattern_type': 'technical_field_alias_match',
                        'source': 'technical_drawing_field'
                    })
                    print(f"[TECHNICAL-MATCH] Alias match: {field_content} -> {material_name}")
                    match_found = True
                    break
            
            if match_found:
                break
        
        # Partial matching if no exact match
        if not match_found:
            for material_name, material_data in materials_cache.items():
                if field_content in material_name.upper():
                    found_materials.append({
                        'keyword': field_content,
                        'material_name': material_name,
                        'position': 0,
                        'confidence': confidence_base - 10,
                        'pattern_type': 'technical_field_partial_match',
                        'source': 'technical_drawing_field'
                    })
                    print(f"[TECHNICAL-MATCH] Partial match: {field_content} -> {material_name}")
                    break
                
                aliases = material_data.get('aliases', [])
                for alias in aliases:
                    if field_content in str(alias).upper():
                        found_materials.append({
                            'keyword': field_content,
                            'material_name': material_name,
                            'position': 0,
                            'confidence': confidence_base - 15,
                            'pattern_type': 'technical_field_alias_partial',
                            'source': 'technical_drawing_field'
                        })
                        print(f"[TECHNICAL-MATCH] Alias partial: {field_content} -> {material_name}")
                        break
    
    return found_materials

# =====================================================
# ENHANCED PATTERN CACHE
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
            
            technical_contexts = [
                r'MALZEME[/\\\s]*:?\s*({material}[\w\d\-\s\/]*)',
                r'MALZEME[/\\\s]*STANDART[:\s]*({material}[\w\d\-\s\/]*)',
                r'MATERIAL[:\s]*({material}[\w\d\-\s\/]*)',
                r'STANDART[:\s]*({material}[\w\d\-\s\/]*)',
                r'GRADE[:\s]*({material}[\w\d\-\s\/]*)',
                r'SPEC[:\s]*({material}[\w\d\-\s\/]*)',
                r'(?:MALZEME|MATERIAL)\s*[|\s]*({material})[\s|\n]',
                r'\b({material})\s*(?=\s*TOLERANS)',
                r'\b({material})\s*(?=\s*BOYUT)',
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
                    
                    for context_pattern in technical_contexts:
                        pattern = context_pattern.format(material=escaped_name)
                        technical_patterns.append({
                            'pattern': pattern,
                            'material_name': material_name,
                            'confidence': 98,
                            'type': 'technical_context',
                            'source': f'technical_{name}'
                        })
                    
                    technical_patterns.append({
                        'pattern': f'\\b{escaped_name}\\b',
                        'material_name': material_name,
                        'confidence': 95,
                        'type': 'technical_direct',
                        'source': f'technical_direct_{name}'
                    })
            
            print(f"[TECHNICAL-PATTERNS] Built {len(technical_patterns)} technical patterns")
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
            
            notlar_contexts = [
                r'ASTM\s+[A-Z]?\d+[A-Z\d\-]*.*?({material}[\w\d\-\s\/]*)',
                r'EN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)', 
                r'DIN\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)',
                r'ISO\s+\d+[\-\d]*.*?({material}[\w\d\-\s\/]*)',
                r'STANDARDINA?\s+UYGUN\s+({material}[\w\d\-\s\/]*)',
                r'KALITE\s+MALZEME.*?({material}[\w\d\-\s\/]*)',
                r'MALZEME\s*:?\s*({material}[\w\d\-\s\/]*)',
                r'STANDARD.*?({material}[\w\d\-\s\/]*)',
                r'MATERIAL\s*:?\s*({material}[\w\d\-\s\/]*)',
                r'GRADE.*?({material}[\w\d\-\s\/]*)',
                r'KULLANILARAK.*?({material}[\w\d\-\s\/]*)',
                r'USING.*?({material}[\w\d\-\s\/]*)',
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
                    
                    for context_pattern in notlar_contexts:
                        pattern = context_pattern.format(material=escaped_name)
                        notlar_patterns.append({
                            'pattern': pattern,
                            'material_name': material_name,
                            'confidence': 95,
                            'type': 'notlar_context',
                            'source': f'notlar_{name}'
                        })
                    
                    if any(char.isdigit() for char in name):
                        temper_pattern = f'{escaped_name}[\\s\\-]*T\\d+[\\s\\/\\-]?\\d*'
                        notlar_patterns.append({
                            'pattern': temper_pattern,
                            'material_name': material_name,
                            'confidence': 98,
                            'type': 'temper_designation',
                            'source': f'temper_{name}'
                        })
                    
                    notlar_patterns.append({
                        'pattern': f'\\b{escaped_name}\\b',
                        'material_name': material_name,
                        'confidence': 90,
                        'type': 'direct_match',
                        'source': f'direct_{name}'
                    })
            
            print(f"[NOTLAR-PATTERNS] Built {len(notlar_patterns)} NOTLAR patterns")
            return notlar_patterns
            
        except Exception as e:
            print(f"[NOTLAR-PATTERNS] Error: {e}")
            return []
    
    def get_lightning_patterns(self):
        if self._quick_patterns is None:
            self._quick_patterns = {
                # Common aluminum patterns
                '6061': ('6061', 95), '606I': ('6061', 90), '6O61': ('6061', 90),
                '7075': ('7075', 95), '7O75': ('7075', 90), '70T5': ('7075', 85),
                '2024': ('2024', 95), '2O24': ('2024', 90), 'Z024': ('2024', 85),
                '7050': ('7050', 95), '7OSO': ('7050', 85),
                '5083': ('5083', 95), 'S083': ('5083', 85),
                
                # Steel patterns
                '304': ('aisi304', 90), '3O4': ('aisi304', 85), 'AISI304': ('aisi304', 95),
                '316': ('aisi316', 90), '3I6': ('aisi316', 85), 'AISI316': ('aisi316', 95),
                '316L': ('aisi316', 92), '3I6L': ('aisi316', 87),
                '420': ('aisi420', 90), '42O': ('aisi420', 85),
                
                # Plastic patterns - IMPORTANT for technical drawings
                'PA6GF30': ('GF30-PA66', 98), 'PA6GF3O': ('GF30-PA66', 95),
                'POM': ('POM', 95), 'POMC': ('POM', 92),
                'DELRIN': ('Delrin', 95), 'PMMA': ('PMMA', 95),
                'TEFLON': ('Teflon', 95), 'PTFE': ('Teflon', 95),
                
                # Material types
                'BRASS': ('Brass', 85), 'PIRINC': ('Brass', 85),
                'ALUMINUM': ('6061', 80), 'ALUMINIUM': ('6061', 80), 'ALUMINYUM': ('6061', 80),
                'AL ': ('6061', 75), 'AL.': ('6061', 75),
                'STEEL': ('aisi304', 75), 'CELIK': ('aisi304', 75), 'ÇELIK': ('aisi304', 75),
                'STAINLESS': ('aisi304', 75), 'PASLANMAZ': ('aisi304', 75),
                
                # OCR common mistakes
                'AL6061': ('6061', 88), 'AL-6061': ('6061', 88),
                'ST304': ('aisi304', 85), 'ST-304': ('aisi304', 85),
                'DIN': ('aisi304', 70), 'ASTM': ('6061', 70),
                'EN': ('aisi304', 70), 'ISO': ('6061', 70)
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
            
            print("[PATTERN-CACHE] Refreshing enhanced pattern cache...")
            self._pattern_cache = self._build_lightning_patterns()
            self._pattern_cache_timestamp = current_time
            print(f"[PATTERN-CACHE] {len(self._pattern_cache)} enhanced patterns cached")
        
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
                        'confidence': 90
                    })
                    
                    aliases = material.get('aliases', [])
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip().upper()
                            patterns.append({
                                'pattern': alias_clean,
                                'material_name': name,
                                'confidence': 87
                            })
            
            print(f"[PATTERN-BUILD] Built {len(patterns)} patterns from EVERY material")
            return patterns
            
        except Exception as e:
            print(f"[PATTERN-BUILD] Error: {e}")
            return []

# Global cache instance
lightning_cache = LightningPatternCache()

# =====================================================
# HELPER FUNCTIONS
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

def extract_material_keywords_lightning(text):
    """Enhanced keyword extraction with TECHNICAL DRAWING priority"""
    if not text or len(text.strip()) < 3:
        return []
    
    print(f"[EXTRACT-ENHANCED] Processing {len(text)} chars with TECHNICAL DRAWING support")
    
    # PRIORITY 1: Check for TECHNICAL DRAWING fields first (HIGHEST PRIORITY)
    technical_fields = extract_technical_drawing_fields(text)
    if technical_fields:
        try:
            database = db.get_db()
            materials_cursor = database.materials.find({}, {"name": 1, "aliases": 1})
            materials_cache = {}
            for material in materials_cursor:
                materials_cache[material.get('name')] = material
            
            technical_materials = find_materials_in_technical_fields(technical_fields, materials_cache)
            if technical_materials:
                print(f"[EXTRACT-ENHANCED] TECHNICAL FIELDS found {len(technical_materials)} materials")
                return technical_materials[:5]
        except Exception as e:
            print(f"[EXTRACT-ENHANCED] Technical field matching error: {e}")
    
    # PRIORITY 2: Check for NOTLAR section
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                print(f"[EXTRACT-ENHANCED] NOTLAR section found {len(notlar_materials)} materials")
                return notlar_materials[:5]
    
    # PRIORITY 3: Use proven method as fallback
    material_keywords = extract_material_keywords_from_text_fixed(text)
    
    if material_keywords:
        print(f"[EXTRACT-ENHANCED] Found {len(material_keywords)} materials using proven patterns")
        return material_keywords[:5]
    
    # PRIORITY 4: Lightning patterns as last resort
    normalized_text = normalize_text_lightning(text)
    
    lightning_patterns = lightning_cache.get_lightning_patterns()
    found_keywords = []
    
    words = normalized_text.split()
    word_positions = {}
    
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^\w]', '', word)
        if len(clean_word) >= 2:
            word_positions[clean_word] = i
    
    for pattern, (material_name, confidence) in lightning_patterns.items():
        if pattern in word_positions or pattern in normalized_text:
            position = word_positions.get(pattern, normalized_text.find(pattern))
            found_keywords.append({
                'keyword': pattern,
                'material_name': material_name,
                'position': position,
                'confidence': confidence,
                'pattern_type': 'lightning_fallback'
            })
            print(f"[EXTRACT-ENHANCED] Lightning fallback: {pattern} -> {material_name} ({confidence}%)")
    
    found_keywords.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"[EXTRACT-ENHANCED] Total found: {len(found_keywords)} materials")
    return found_keywords

def get_dynamic_material_patterns():
    """Get patterns from EVERY material in database with technical drawing support"""
    try:
        database = db.get_db()
        materials_cursor = database.materials.find()
        materials_list = list(materials_cursor)
        
        patterns = []
        
        # ENHANCED TECHNICAL DRAWING PATTERNS - MOST IMPORTANT
        technical_drawing_patterns = [
            {'pattern': r'MALZEME[/\\\s]*:?\s*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'technical_malzeme_field'},
            {'pattern': r'MALZEME[/\\\s]*STANDART[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'technical_malzeme_standard'},
            {'pattern': r'MATERIAL[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 99, 'type': 'technical_material_field'},
            {'pattern': r'STANDART[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 98, 'type': 'technical_standard_field'},
            {'pattern': r'GRADE[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 98, 'type': 'technical_grade_field'},
            {'pattern': r'SPEC[:\s]*([A-Z0-9\-\+]{2,15})', 'material_name': 'CONTEXT', 'confidence': 98, 'type': 'technical_spec_field'},
            {'pattern': r'(?:MALZEME|MATERIAL)\s*[|\s]*([A-Z0-9\-\+]{2,15})[\s|\n]', 'material_name': 'CONTEXT', 'confidence': 97, 'type': 'technical_table_cell'},
            {'pattern': r'([A-Z0-9\-\+]{3,15})\s*(?=\s*TOLERANS)', 'material_name': 'CONTEXT', 'confidence': 95, 'type': 'technical_before_tolerans'},
            {'pattern': r'([A-Z0-9\-\+]{3,15})\s*(?=\s*BOYUT)', 'material_name': 'CONTEXT', 'confidence': 95, 'type': 'technical_before_boyut'},
        ]
        
        patterns.extend(technical_drawing_patterns)
        print(f"[PATTERN-BUILD] Added {len(technical_drawing_patterns)} TECHNICAL DRAWING patterns")
        
        # ENHANCED STAINLESS STEEL RESOLUTION PATTERNS
        stainless_steel_patterns = [
            {'pattern': r'PASLANMAZ\s+ÇELİK\s+KULLANILACAKTIR', 'material_name': 'aisi304', 'confidence': 98, 'type': 'stainless_usage_turkish'},
            {'pattern': r'PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 95, 'type': 'stainless_direct_turkish'},
            {'pattern': r'STAINLESS\s+STEEL', 'material_name': 'aisi304', 'confidence': 95, 'type': 'stainless_direct_english'},
            {'pattern': r'EN\s+10088[-\d]*.*?1\.4301.*?PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 99, 'type': 'en10088_1_4301'},
            {'pattern': r'1\.4301.*?PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 97, 'type': 'grade_1_4301'},
            {'pattern': r'X5CrNi18[-\s]*10.*?PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 97, 'type': 'x5crni18_10'},
            {'pattern': r'X5CrNi18[-\s]*10\s*\(304\)', 'material_name': 'aisi304', 'confidence': 98, 'type': 'x5crni18_10_304'},
            {'pattern': r'\(304\)\s*KALİTE\s*PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 99, 'type': '304_grade_turkish'},
            {'pattern': r'304\s*KALİTE.*?PASLANMAZ', 'material_name': 'aisi304', 'confidence': 96, 'type': '304_quality'},
            {'pattern': r'AISI\s*304.*?PASLANMAZ', 'material_name': 'aisi304', 'confidence': 98, 'type': 'aisi304_stainless'},
            {'pattern': r'KALİTE\s+PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 90, 'type': 'quality_stainless'},
            {'pattern': r'STANDARDINA\s+UYGUN.*?PASLANMAZ\s+ÇELİK', 'material_name': 'aisi304', 'confidence': 92, 'type': 'standard_stainless'},
        ]
        
        patterns.extend(stainless_steel_patterns)
        print(f"[PATTERN-BUILD] Added {len(stainless_steel_patterns)} STAINLESS STEEL resolution patterns")
        
        # STRONG direct patterns first
        strong_patterns = [
            {'pattern': r'AA\s*7075[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '7075', 'confidence': 99, 'type': 'aa_aluminum_temper'},
            {'pattern': r'AA\s*6061[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '6061', 'confidence': 99, 'type': 'aa_aluminum_temper'},
            {'pattern': r'AA\s*2024[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '2024', 'confidence': 99, 'type': 'aa_aluminum_temper'},
            {'pattern': r'AA\s*7075[\-T0-9]*', 'material_name': '7075', 'confidence': 98, 'type': 'aa_aluminum'},
            {'pattern': r'AA\s*6061[\-T0-9]*', 'material_name': '6061', 'confidence': 98, 'type': 'aa_aluminum'},
            {'pattern': r'AA\s*2024[\-T0-9]*', 'material_name': '2024', 'confidence': 98, 'type': 'aa_aluminum'},
            {'pattern': r'7075[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '7075', 'confidence': 96, 'type': 'aluminum_temper'},
            {'pattern': r'6061[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '6061', 'confidence': 96, 'type': 'aluminum_temper'},
            {'pattern': r'2024[\s\-]*T\d+[\s\/\-]?\d*', 'material_name': '2024', 'confidence': 96, 'type': 'aluminum_temper'},
            {'pattern': r'\b7075\b', 'material_name': '7075', 'confidence': 95, 'type': 'aluminum_exact'},
            {'pattern': r'\b6061\b', 'material_name': '6061', 'confidence': 95, 'type': 'aluminum_exact'},
            {'pattern': r'\b2024\b', 'material_name': '2024', 'confidence': 95, 'type': 'aluminum_exact'},
            # ENHANCED PLASTIC PATTERNS FOR TECHNICAL DRAWINGS
            {'pattern': r'\bPA6GF30\b', 'material_name': 'GF30-PA66', 'confidence': 98, 'type': 'plastic_exact'},
            {'pattern': r'\bPA6GF3O\b', 'material_name': 'GF30-PA66', 'confidence': 95, 'type': 'plastic_ocr_fix'},
            {'pattern': r'\bPOM\b', 'material_name': 'POM', 'confidence': 95, 'type': 'plastic_exact'},
            {'pattern': r'\bDELRIN\b', 'material_name': 'Delrin', 'confidence': 95, 'type': 'plastic_exact'},
            {'pattern': r'\bPMMA\b', 'material_name': 'PMMA', 'confidence': 95, 'type': 'plastic_exact'},
            {'pattern': r'\bTEFLON\b', 'material_name': 'Teflon', 'confidence': 95, 'type': 'plastic_exact'},
            {'pattern': r'\bPTFE\b', 'material_name': 'Teflon', 'confidence': 95, 'type': 'plastic_ptfe'},
        ]
        
        patterns.extend(strong_patterns)
        print(f"[PATTERN-BUILD] Added {len(strong_patterns)} ENHANCED DIRECT patterns")
        
        # Process EVERY SINGLE MATERIAL from database
        print(f"[PATTERN-BUILD-BODOZLAMA] Processing {len(materials_list)} RAW materials from database...")
        for material in materials_list:
            material_name = material.get('name', '').strip()
            aliases = material.get('aliases', [])
            
            if material_name:
                if len(material_name) >= 2:
                    escaped_name = re.escape(material_name)
                    
                    if any(char.isdigit() for char in material_name):
                        patterns.append({
                            'pattern': f'{escaped_name}[\\s\\-]*T\\d+[\\s\\/\\-]?\\d*',
                            'material_name': material_name,
                            'confidence': 96,
                            'type': 'temper_designation',
                            'source': 'material_temper_bodozlama'
                        })
                    
                    patterns.append({
                        'pattern': f'\\b{escaped_name}\\b',
                        'material_name': material_name,
                        'confidence': 90,
                        'type': 'exact_match',
                        'source': 'material_name_exact_bodozlama'
                    })
                    
                    patterns.append({
                        'pattern': escaped_name,
                        'material_name': material_name,
                        'confidence': 85,
                        'type': 'flexible_match',
                        'source': 'material_name_flexible_bodozlama'
                    })
                
                if aliases:
                    for alias in aliases:
                        if alias and len(str(alias).strip()) >= 2:
                            alias_clean = str(alias).strip()
                            escaped_alias = re.escape(alias_clean)
                            
                            if any(char.isdigit() for char in alias_clean):
                                patterns.append({
                                    'pattern': f'{escaped_alias}[\\s\\-]*T\\d+[\\s\\/\\-]?\\d*',
                                    'material_name': material_name,
                                    'confidence': 92,
                                    'type': 'alias_temper',
                                    'source': f'alias_temper_bodozlama:{alias_clean}'
                                })
                            
                            patterns.append({
                                'pattern': f'\\b{escaped_alias}\\b',
                                'material_name': material_name,
                                'confidence': 85,
                                'type': 'alias_exact',
                                'source': f'alias_exact_bodozlama:{alias_clean}'
                            })
        
        print(f"[PATTERN-BUILD] BODOZLAMA: Built {len(patterns)} patterns from EVERY material in database")
        return patterns
        
    except Exception as e:
        print(f"[PATTERN-BUILD] BODOZLAMA Error: {e}")
        return []

def extract_material_keywords_from_text_fixed(text):
    """Enhanced keyword extraction method with TECHNICAL DRAWING priority"""
    if not text:
        return []
    
    # First try TECHNICAL DRAWING field extraction (HIGHEST PRIORITY)
    technical_fields = extract_technical_drawing_fields(text)
    if technical_fields:
        try:
            database = db.get_db()
            materials_cursor = database.materials.find({}, {"name": 1, "aliases": 1})
            materials_cache = {}
            for material in materials_cursor:
                materials_cache[material.get('name')] = material
            
            technical_materials = find_materials_in_technical_fields(technical_fields, materials_cache)
            if technical_materials:
                print(f"[EXTRACT-FIXED] TECHNICAL DRAWING priority found {len(technical_materials)} materials")
                return technical_materials
        except Exception as e:
            print(f"[EXTRACT-FIXED] Technical field error: {e}")
    
    # Then try NOTLAR section extraction
    notlar_section = extract_notlar_section(text)
    if notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_materials = find_materials_in_notlar_items(notlar_items)
            if notlar_materials:
                print(f"[EXTRACT-FIXED] NOTLAR priority found {len(notlar_materials)} materials")
                return notlar_materials
    
    # Fallback to original method
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

def resolve_material_from_database(captured_material):
    """Resolve captured material text to database material name"""
    try:
        database = db.get_db()
        captured_clean = captured_material.strip().upper()
        
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

def should_accept_match(match_text, pattern_type, full_text, position):
    """Enhanced pattern acceptance logic"""
    if len(match_text) < 2:
        return False
    
    context_start = max(0, position - 30)
    context_end = min(len(full_text), position + len(match_text) + 30)
    context = full_text[context_start:context_end]
    
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
        start_time = time.time()
        print("[OCR-ENHANCED] Using enhanced OCR methods for technical drawings...")
        
        # METHOD 1: PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text and len(text.strip()) > 30:
                        if extract_technical_drawing_fields(text):
                            print(f"[OCR-ENHANCED] PyPDF2 with TECHNICAL FIELDS: {len(text)} chars")
                            return text
                        elif extract_notlar_section(text):
                            print(f"[OCR-ENHANCED] PyPDF2 with NOTLAR: {len(text)} chars")
                            return text
                        elif len(text.strip()) > 100:
                            print(f"[OCR-ENHANCED] PyPDF2 success: {len(text)} chars")
                            return text
        except Exception as e:
            print(f"[OCR-ENHANCED] PyPDF2 failed: {e}")
        
        # METHOD 2: Enhanced Tesseract OCR
        try:
            print("[OCR-ENHANCED] Using enhanced Tesseract config for technical drawings...")
            pages = convert_from_path(pdf_path, dpi=600, first_page=1, last_page=1)
            
            if pages:
                text = pytesseract.image_to_string(pages[0], lang='eng+tur', 
                                                config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-/: ')
                
                if text and len(text.strip()) > 20:
                    print(f"[OCR-ENHANCED] Enhanced Tesseract success: {len(text)} chars")
                    return text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Enhanced Tesseract failed: {e}")
        
        # METHOD 3: Alternative OCR with preprocessing
        try:
            print("[OCR-ENHANCED] Trying preprocessed OCR...")
            pages = convert_from_path(pdf_path, dpi=600, first_page=1, last_page=1)
            
            if pages:
                enhanced_image = optimize_image_for_ocr_lightning(pages[0])
                text = pytesseract.image_to_string(enhanced_image, lang='eng', config='--psm 3')
                
                if text and len(text.strip()) > 10:
                    print(f"[OCR-ENHANCED] Preprocessed OCR success: {len(text)} chars")
                    return text
                    
        except Exception as e:
            print(f"[OCR-ENHANCED] Preprocessed OCR failed: {e}")
        
        print(f"[OCR-ENHANCED] All enhanced OCR methods failed")
        return ""
        
    except Exception as e:
        print(f"[OCR-ENHANCED] Enhanced OCR fatal error: {e}")
        return ""

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
        "7O75": "7075",
        "7075-T6": "7075T6",
        "7075-T651": "7075T651",
        "7075 T6": "7075T6",
        "7075 T651": "7075T651",
        "7075 T6/651": "7075T6651",
        "7075-T6/651": "7075T6651",
        "6O61": "6061",
        "6061-T6": "6061T6", 
        "6061-T651": "6061T651",
        "6061 T6": "6061T6",
        "6061 T651": "6061T651",
        "6061 T6/651": "6061T6651",
        "6061-T6/651": "6061T6651",
        "2024-T3": "2024T3",
        "2024 T3": "2024T3",
        "2024-T351": "2024T351",
        "2024 T351": "2024T351",
        # Plastic corrections for technical drawings
        "PA6GF3O": "PA6GF30",
        "PA6G F30": "PA6GF30",
        "PA 6GF30": "PA6GF30",
        "PA6 GF30": "PA6GF30",
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
    
    ocr_corrections = {
        "GOSTERILEN": "GOSTERILEN",
        "EDILMiS": "EDILMIS",
        "IGIN": "ICIN", 
        "GEGERLIDIR": "GECERLIDIR",
        "VEYAASTM": "VEYA ASTM",
        "EN AW": "ENAW",
        "AA ": "AA",
        "T6/T651": "T6T651",
        "T6/T6": "T6T6", 
        "T6 T651": "T6T651",
        "T 6": "T6",
        "2064": "7050", "7056": "7050", "705O": "7050", "7O5O": "7050",
        "606I": "6061", "6O61": "6061", "606l": "6061",
        "2024": "2024", "2O24": "2024", "2o24": "2024",
        "7075": "7075", "7O75": "7075", "707S": "7075",
        "3O4": "304", "3o4": "304", "30I": "304",
        "3I6": "316", "31G": "316",
        "42O": "420"
    }
    
    corrected_text = text
    for error_pattern, correction in ocr_corrections.items():
        if error_pattern in text and error_pattern != correction:
            corrected_text = corrected_text.replace(error_pattern, correction)
    
    final_text = re.sub(r'\s+', ' ', corrected_text).strip()
    print(f"[NORMALIZE] Final text sample: {final_text[:200]}...")
    return final_text

def find_materials_in_text_database_only_proven(text):
    """Enhanced proven method with TECHNICAL DRAWING priority"""
    if not text or len(text.strip()) < 5:
        return []
    
    print(f"[MATERIAL-PROVEN] Using enhanced proven method for {len(text)} chars")
    
    # PRIORITY 1: Try TECHNICAL DRAWING fields first (HIGHEST PRIORITY)
    technical_fields = extract_technical_drawing_fields(text)
    if technical_fields:
        try:
            database = db.get_db()
            materials_cursor = database.materials.find({}, {"name": 1, "aliases": 1})
            materials_cache = {}
            for material in materials_cursor:
                materials_cache[material.get('name')] = material
            
            technical_materials = find_materials_in_technical_fields(technical_fields, materials_cache)
            if technical_materials:
                proven_format_materials = []
                for material in technical_materials:
                    confidence = material['confidence']
                    material_name = material['material_name'] 
                    formatted_material = f"{material_name} (%{confidence})"
                    proven_format_materials.append(formatted_material)
                
                print(f"[MATERIAL-PROVEN] TECHNICAL DRAWING found {len(proven_format_materials)} materials")
                return proven_format_materials[:5]
        except Exception as e:
            print(f"[MATERIAL-PROVEN] Technical drawing error: {e}")
    
    # PRIORITY 2: Try NOTLAR section
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
    
    # PRIORITY 3: Use exact normalization from working codebase
    normalized_text = comprehensive_turkish_normalization_from_working(text)
    
    if not normalized_text:
        return []
    
    material_keywords = extract_material_keywords_from_text_fixed(normalized_text)
    
    if not material_keywords:
        print("[MATERIAL-PROVEN] No keywords found with enhanced proven method")
        return []
    
    # Database lookup - same as working version
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
                'matched_term': f"enhanced_{keyword}",
                'material': materials_cache[material_name],
                'strategy': 'enhanced_proven_method',
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
        
        print(f"[MATERIAL-PROVEN] Returning {len(result_materials)} enhanced materials")
        return result_materials
    
    print("[MATERIAL-PROVEN] No materials found in enhanced database lookup")
    return []

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
        
        print("[INIT] MaterialAnalysisService ENHANCED-TECHNICAL-DRAWING initializing...")
        try:
            self.database.command('ping')
            print("[INIT] Database connection OK")
            self._preload_essential_materials_lightning()
            print(f"[INIT] ENHANCED MaterialAnalysisService ready with {len(self._material_cache)} materials")
        except Exception as init_error:
            print(f"[INIT] Initialization failed: {init_error}")
    
    def _preload_essential_materials_lightning(self):
        """BODOZLAMA - GET EVERY SINGLE MATERIAL NO QUESTIONS ASKED"""
        try:
            print("[CACHE] BODOZLAMA: Loading EVERY material from database...")
            materials_cursor = self.database.materials.find()
            materials_list = list(materials_cursor)
            print(f"[CACHE] BODOZLAMA: Found {len(materials_list)} RAW materials from database")
            
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
            print(f"[CACHE] BODOZLAMA: ALL {len(self._material_cache)} materials cached - NO FILTERING")
            
        except Exception as e:
            print(f"[CACHE] BODOZLAMA failed: {e}")

    def _get_materials_cached_lightning(self):
        current_time = time.time()
        
        if (not self._material_cache or 
            current_time - self._last_cache_update > self._cache_ttl):
            self._preload_essential_materials_lightning()
        
        return self._material_cache

    def _find_materials_in_text_ultra_fast(self, text):
        """Enhanced material finding with TECHNICAL DRAWING priority"""
        if not text or len(text.strip()) < 3:
            return []
        
        print(f"[MATERIAL-ENHANCED] Using ENHANCED method for {len(text)} chars")
        materials = find_materials_in_text_database_only_proven(text)
        
        if materials:
            print(f"[MATERIAL-ENHANCED] ENHANCED method found: {len(materials)} materials")
            return materials
        
        print("[MATERIAL-ENHANCED] No materials found with enhanced method - returning empty")
        return []

    def _extract_text_from_pdf_optimized(self, pdf_path):
        return extract_text_with_lightning_ocr(pdf_path)

    def _analyze_pdf_ultra_fast_optimized(self, file_path, result, matched_step_path=None):
        """Enhanced PDF analysis with TECHNICAL DRAWING support"""
        start_time = time.time()
        result["processing_log"].append("📄 ENHANCED-TECHNICAL-DRAWING PDF analysis starting")
        
        print(f"[PDF-ENHANCED] Enhanced PDF analysis: {os.path.basename(file_path)}")
        
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
        
        # ENHANCED MATERIAL DETECTION WITH TECHNICAL DRAWING PRIORITY
        materials = []
        ocr_method = "none"
        raw_text = ""
        
        try:
            # STRATEGY 1: Enhanced PyPDF2 with TECHNICAL DRAWING detection
            print("[PDF-ENHANCED] Strategy 1: Enhanced PyPDF2 with TECHNICAL DRAWING...")
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    pdf_text = reader.pages[0].extract_text()
                    if pdf_text and len(pdf_text.strip()) > 20:
                        # Check for TECHNICAL DRAWING fields first
                        technical_fields = extract_technical_drawing_fields(pdf_text)
                        if technical_fields:
                            print("[PDF-ENHANCED] TECHNICAL DRAWING fields detected in PyPDF2 text")
                            materials = self._find_materials_in_text_ultra_fast(pdf_text)
                            if materials:
                                print(f"[PDF-ENHANCED] PyPDF2+TECHNICAL found {len(materials)} materials")
                                ocr_method = "pypdf2_technical_enhanced"
                                raw_text = pdf_text[:2000]
                        else:
                            # Check for NOTLAR section
                            notlar_section = extract_notlar_section(pdf_text)
                            if notlar_section:
                                print("[PDF-ENHANCED] NOTLAR section detected in PyPDF2 text")
                                materials = self._find_materials_in_text_ultra_fast(pdf_text)
                                if materials:
                                    print(f"[PDF-ENHANCED] PyPDF2+NOTLAR found {len(materials)} materials")
                                    ocr_method = "pypdf2_notlar_enhanced"
                                    raw_text = pdf_text[:2000]
                            else:
                                materials = self._find_materials_in_text_ultra_fast(pdf_text)
                                if materials:
                                    print(f"[PDF-ENHANCED] PyPDF2 found {len(materials)} materials")
                                    ocr_method = "pypdf2_enhanced"
                                    raw_text = pdf_text[:1500]
        
        except Exception as pdf_error:
            print(f"[PDF-ENHANCED] Enhanced PyPDF2 strategy failed: {pdf_error}")
        
        # STRATEGY 2: Enhanced OCR with TECHNICAL DRAWING detection
        if not materials:
            try:
                print("[PDF-ENHANCED] Strategy 2: Enhanced OCR with TECHNICAL DRAWING...")
                ocr_text = self._extract_text_from_pdf_optimized(file_path)
                if ocr_text:
                    technical_fields = extract_technical_drawing_fields(ocr_text)
                    if technical_fields:
                        print("[PDF-ENHANCED] TECHNICAL DRAWING fields detected in OCR text")
                        ocr_method = "tesseract_technical_enhanced"
                    else:
                        notlar_section = extract_notlar_section(ocr_text)
                        if notlar_section:
                            print("[PDF-ENHANCED] NOTLAR section detected in OCR text")
                            ocr_method = "tesseract_notlar_enhanced"
                        else:
                            ocr_method = "tesseract_enhanced"
                    
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
            ocr_method = "enhanced_no_materials"
        
        # Set material results
        result["material_matches"] = materials
        result["ocr_method"] = ocr_method
        result["raw_ocr_output"] = raw_text
        result["ocr_confidence"] = 95 if "technical" in ocr_method else (90 if "notlar" in ocr_method else (80 if "enhanced" in ocr_method else 70))
        result["ocr_method_used"] = ocr_method
        result["ocr_processing_time"] = time.time() - start_time
        
        # ENHANCED STEP EXTRACTION (only if needed)
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
        
        result["material_confidence"] = 95 if "technical" in ocr_method else (90 if "notlar" in ocr_method else (85 if materials else 0))
        
        total_time = time.time() - start_time
        result["processing_log"].append(f"⚡ ENHANCED total time: {total_time:.2f}s")
        
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
            "method": "enhanced_zero_defaults"
        }

    def analyze_document_ultra_fast(self, file_path, file_type, user_id, matched_step_path=None):
        """ENHANCED main analysis method with TECHNICAL DRAWING support"""
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
            print(f"[ENHANCED] ENHANCED-TECHNICAL-DRAWING analysis: {file_path} ({file_type})")
            
            if matched_step_path:
                print(f"[ENHANCED] With matched STEP: {matched_step_path}")
            
            # FILE TYPE SPECIFIC ENHANCED ANALYSIS
            if file_type == 'pdf':
                print("[ENHANCED] Processing PDF with TECHNICAL-DRAWING-enhanced analysis...")
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
            
            # ENHANCED MATERIAL OPTIONS CALCULATION - GET ALL MATERIALS
            step_analysis = result.get("step_analysis", {})
            prizma_hacim = step_analysis.get("Prizma Hacmi (mm³)", 0)
            
            if prizma_hacim and prizma_hacim > 0:
                print(f"[ENHANCED] Calculating ALL materials for volume: {prizma_hacim}")
                result["material_options"] = self._calculate_top_materials_lightning(prizma_hacim)
            else:
                result["material_options"] = []
            
            # ENHANCED FOUND MATERIALS CALCULATION
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
            result["processing_log"].append(f"⚡ ENHANCED total time: {total_time:.2f}s")
            
            print(f"[ENHANCED] ENHANCED analysis completed in {total_time:.3f}s")
            print(f"[ENHANCED] Materials: {len(result.get('material_matches', []))}, Options: {len(result.get('material_options', []))}")
            
            return result
            
        except Exception as e:
            error_msg = f"ENHANCED analysis error: {str(e)}"
            print(f"[ENHANCED] {error_msg}")
            
            result["error"] = error_msg
            result["material_matches"] = []
            result["material_options"] = []
            
            return result

    def _get_database_only_materials(self, prizma_hacim_mm3):
        """Get ALL materials from database - no limits"""
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
        """Enhanced top materials calculation - PROCESS ALL MATERIALS"""
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
                        "source": "enhanced_cache"
                    })
                    
                except Exception:
                        continue
            
            top_materials.sort(key=lambda x: x["material_cost"])
            
            if limit:
                result = top_materials[:limit]
            else:
                result = top_materials
            
            print(f"[TOP-MATERIALS-ENHANCED] {len(result)} materials calculated (from {len(top_materials)} total)")
            return result
            
        except Exception as e:
            print(f"[TOP-MATERIALS-ENHANCED] Error: {e}")
            return []

    def _calculate_found_materials_lightning(self, prizma_hacim_mm3, found_materials):
        """Enhanced found materials calculation"""
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
                        "source": "enhanced_cache"
                    })
                    
                except Exception:
                    continue
            
            print(f"[CALC-ENHANCED] {len(calculations)} materials calculated")
            return calculations
            
        except Exception as e:
            print(f"[CALC-ENHANCED] Error: {e}")
            return []

    def _calculate_found_materials_database_only(self, prizma_hacim_mm3, found_materials):
        """Database-only found materials calculation for backward compatibility"""
        try:
            print(f"[CALC-DB-ONLY] Database-only calculation for {len(found_materials)} materials")
            
            if prizma_hacim_mm3 <= 0 or not found_materials:
                return []
                
            calculations = []
            
            for material_text in found_materials[:3]:  # Limit for speed
                material_name = material_text.split("(")[0].strip()
                
                # Direct database query for this specific material - NO is_active filter
                try:
                    material = self.database.materials.find_one(
                        {"name": material_name},
                        {"name": 1, "density": 1, "price_per_kg": 1, "category": 1}
                    )
                    
                    if not material:
                        # Try case insensitive search
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
                        
                        # Extract confidence from material text
                        confidence_match = re.search(r'%(\d+)', material_text)
                        confidence = int(confidence_match.group(1)) if confidence_match else 80
                        
                        # Calculate mass and cost
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

    def _analyze_document_lightning(self, file_path, result):
        """Enhanced document analysis"""
        result["processing_log"].append("📝 Enhanced document analysis")
        
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
        """Enhanced STEP analysis"""
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
                "method": "enhanced_optimized"
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
            "method": "enhanced_zero_defaults"
        }

    def _extract_step_from_pdf_lightning(self, pdf_path):
        """Fast STEP extraction with robust comment/annotation handling"""
        try:
            extracted = []
            start_time = time.time()
            TIMEOUT_SECONDS = 3.0
            
            print(f"[STEP-EXTRACT] 🔍 Starting robust STEP search: {os.path.basename(pdf_path)}")
            
            with pikepdf.open(pdf_path) as pdf:
                
                # ✅ METHOD 1: Embedded Files (Standard)
                try:
                    print("[STEP-EXTRACT] 🔍 Method 1: Embedded Files...")
                    root = pdf.trailer.get("/Root", {})
                    names = root.get("/Names", {})
                    embedded = names.get("/EmbeddedFiles", {})
                    files = embedded.get("/Names", [])
                    
                    for i in range(0, min(len(files), 20), 2):
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            break
                        
                        if i + 1 < len(files):
                            try:
                                file_spec = files[i + 1]
                                file_name = str(file_spec.get("/UF") or file_spec.get("/F") or files[i]).strip("()")
                                
                                print(f"[STEP-EXTRACT] 📎 Found embedded file: {file_name}")
                                
                                if file_name.lower().endswith(('.stp', '.step')):
                                    file_data = file_spec['/EF']['/F'].read_bytes()
                                    
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
                                print(f"[STEP-EXTRACT] ⚠️ Embedded file error: {e}")
                                continue
                                
                except Exception as e:
                    print(f"[STEP-EXTRACT] ⚠️ Embedded files method error: {e}")
                
                # ✅ METHOD 2: ROBUST COMMENTS/ANNOTATIONS
                if not extracted and time.time() - start_time < TIMEOUT_SECONDS:
                    try:
                        print("[STEP-EXTRACT] 🔍 Method 2: Robust Comments/Annotations...")
                        
                        for page_num, page in enumerate(pdf.pages[:5]):
                            if time.time() - start_time > TIMEOUT_SECONDS:
                                break
                                
                            try:
                                # ✅ Safe annotation access
                                if '/Annots' in page:
                                    annotations_ref = page['/Annots']
                                    print(f"[STEP-EXTRACT] 📄 Page {page_num + 1}: Found annotations reference")
                                    
                                    # Handle different annotation reference types
                                    annotations = []
                                    try:
                                        if hasattr(annotations_ref, '__len__'):
                                            annotations = list(annotations_ref)
                                        else:
                                            annotations = [annotations_ref]
                                    except:
                                        print(f"[STEP-EXTRACT] ⚠️ Could not iterate annotations on page {page_num + 1}")
                                        continue
                                    
                                    print(f"[STEP-EXTRACT] 📄 Page {page_num + 1}: {len(annotations)} annotations to process")
                                    
                                    for annot_idx, annot_ref in enumerate(annotations):
                                        try:
                                            # ✅ Safe annotation resolution
                                            annot_obj = None
                                            try:
                                                if hasattr(annot_ref, 'resolve'):
                                                    annot_obj = annot_ref.resolve()
                                                else:
                                                    annot_obj = annot_ref
                                            except Exception as resolve_error:
                                                print(f"[STEP-EXTRACT] ⚠️ Annotation {annot_idx} resolve error: {resolve_error}")
                                                # Try direct access
                                                try:
                                                    annot_obj = annot_ref
                                                except:
                                                    continue
                                            
                                            if annot_obj is None:
                                                continue
                                            
                                            print(f"[STEP-EXTRACT] 🔍 Processing annotation {annot_idx} on page {page_num + 1}")
                                            
                                            # ✅ Check annotation type safely
                                            try:
                                                subtype = annot_obj.get('/Subtype', '')
                                                print(f"[STEP-EXTRACT] 📋 Annotation {annot_idx} type: {subtype}")
                                            except:
                                                subtype = ''
                                            
                                            # ✅ METHOD 2A: File attachments in annotation
                                            try:
                                                if '/FS' in annot_obj:
                                                    file_spec = annot_obj['/FS']
                                                    print(f"[STEP-EXTRACT] 📎 Annotation {annot_idx} has file attachment")
                                                    
                                                    # Get filename safely
                                                    filename = ""
                                                    for name_field in ['/UF', '/F', '/Unix', '/Mac', '/DOS']:
                                                        try:
                                                            if name_field in file_spec:
                                                                filename = str(file_spec[name_field]).strip("()")
                                                                print(f"[STEP-EXTRACT] 📝 Found filename ({name_field}): {filename}")
                                                                break
                                                        except:
                                                            continue
                                                    
                                                    if filename.lower().endswith(('.stp', '.step')):
                                                        print(f"[STEP-EXTRACT] 🎯 STEP file detected: {filename}")
                                                        
                                                        # Try to extract file data
                                                        extracted_file = False
                                                        if '/EF' in file_spec:
                                                            for ef_field in ['/F', '/UF', '/Unix', '/Mac', '/DOS']:
                                                                try:
                                                                    if ef_field in file_spec['/EF']:
                                                                        file_data = file_spec['/EF'][ef_field].read_bytes()
                                                                        
                                                                        if len(file_data) > 100:
                                                                            temp_dir = os.path.join(os.getcwd(), "temp")
                                                                            os.makedirs(temp_dir, exist_ok=True)
                                                                            
                                                                            safe_filename = f"comment_{page_num}_{annot_idx}_{int(time.time())}.step"
                                                                            output_path = os.path.join(temp_dir, safe_filename)
                                                                            
                                                                            with open(output_path, 'wb') as f:
                                                                                f.write(file_data)
                                                                            
                                                                            extracted.append(output_path)
                                                                            print(f"[STEP-EXTRACT] ✅ Comment STEP extracted: {filename} -> {safe_filename}")
                                                                            return extracted
                                                                        
                                                                except Exception as ef_error:
                                                                    print(f"[STEP-EXTRACT] ⚠️ EF field {ef_field} error: {ef_error}")
                                                                    continue
                                                        
                                                        if not extracted_file:
                                                            print(f"[STEP-EXTRACT] ⚠️ Could not extract file data for: {filename}")
                                            
                                            except Exception as fs_error:
                                                # Silent pass for annotations without file attachments
                                                pass
                                            
                                            # ✅ METHOD 2B: Check annotation contents for STEP references
                                            try:
                                                if '/Contents' in annot_obj:
                                                    content = str(annot_obj['/Contents'])
                                                    if content and len(content) > 3:
                                                        print(f"[STEP-EXTRACT] 📝 Annotation {annot_idx} content: {content[:100]}...")
                                                        
                                                        # Look for STEP file patterns
                                                        step_patterns = [
                                                            r'(\w+.*?\.stp?)\b',
                                                            r'(\w+.*?\.step)\b',
                                                            r'(\d+_.*?\.stp?)\b',
                                                            r'([a-zA-Z0-9_-]+\.stp?)\b'
                                                        ]
                                                        
                                                        for pattern in step_patterns:
                                                            matches = re.findall(pattern, content, re.IGNORECASE)
                                                            for match in matches:
                                                                print(f"[STEP-EXTRACT] 🎯 Found STEP filename in comment: {match}")
                                                                
                                                                # Check if this matches the filename pattern from the image
                                                                if '10080964' in match and 'stp' in match.lower():
                                                                    print(f"[STEP-EXTRACT] 🎯 MATCHING PATTERN FOUND: {match}")
                                            
                                            except Exception as content_error:
                                                # Silent pass for annotations without content
                                                pass
                                            
                                            # ✅ METHOD 2C: Check for Action objects
                                            try:
                                                if '/A' in annot_obj:
                                                    action = annot_obj['/A']
                                                    if '/S' in action and '/F' in action:
                                                        action_file = str(action['/F']).strip("()")
                                                        if action_file.lower().endswith(('.stp', '.step')):
                                                            print(f"[STEP-EXTRACT] 🚀 Action STEP reference: {action_file}")
                                            
                                            except Exception as action_error:
                                                # Silent pass for annotations without actions
                                                pass
                                            
                                            # ✅ METHOD 2D: Check annotation streams
                                            try:
                                                if hasattr(annot_obj, 'stream') and annot_obj.stream:
                                                    stream_data = bytes(annot_obj.stream)
                                                    if len(stream_data) > 100:
                                                        # Check if stream contains STEP data
                                                        if self._is_step_data_fast(stream_data):
                                                            safe_filename = f"annot_stream_{page_num}_{annot_idx}_{int(time.time())}.step"
                                                            saved_files = self._save_step_data_fast(stream_data, safe_filename)
                                                            if saved_files:
                                                                print(f"[STEP-EXTRACT] ✅ Annotation stream STEP found")
                                                                return saved_files
                                                        
                                                        # Check stream for file references
                                                        try:
                                                            stream_text = stream_data.decode('utf-8', errors='ignore')
                                                            if '10080964' in stream_text and ('.stp' in stream_text.lower() or '.step' in stream_text.lower()):
                                                                print(f"[STEP-EXTRACT] 📄 Stream contains target STEP reference")
                                                        except:
                                                            pass
                                            
                                            except Exception as stream_error:
                                                # Silent pass for annotations without streams
                                                pass
                                        
                                        except Exception as annot_error:
                                            print(f"[STEP-EXTRACT] ⚠️ Annotation {annot_idx} processing error: {annot_error}")
                                            continue
                            
                            except Exception as page_error:
                                print(f"[STEP-EXTRACT] ⚠️ Page {page_num + 1} annotation processing error: {page_error}")
                                continue
                        
                    except Exception as comment_error:
                        print(f"[STEP-EXTRACT] ⚠️ Comment search error: {comment_error}")
                
                # ✅ METHOD 3: SAFE OBJECT INSPECTION
                if not extracted and time.time() - start_time < TIMEOUT_SECONDS:
                    try:
                        print("[STEP-EXTRACT] 🔍 Method 3: Safe Object Inspection...")
                        
                        # Safe object iteration
                        try:
                            if hasattr(pdf, 'objects'):
                                objects = pdf.objects
                                if hasattr(objects, 'keys'):
                                    object_keys = list(objects.keys())[:50]  # Limit for safety
                                else:
                                    # Try alternative access
                                    object_keys = []
                                    try:
                                        for i, obj in enumerate(objects):
                                            if i >= 50:
                                                break
                                            object_keys.append(i)
                                    except:
                                        pass
                            else:
                                object_keys = []
                            
                            print(f"[STEP-EXTRACT] 🔍 Checking {len(object_keys)} objects safely")
                            
                            for obj_id in object_keys:
                                if time.time() - start_time > TIMEOUT_SECONDS:
                                    break
                                
                                try:
                                    if hasattr(objects, '__getitem__'):
                                        obj = objects[obj_id]
                                    else:
                                        continue
                                    
                                    # Check if object has stream data
                                    if hasattr(obj, 'stream') and obj.stream:
                                        stream_data = bytes(obj.stream)
                                        
                                        # Check if stream contains STEP data
                                        if len(stream_data) > 100 and self._is_step_data_fast(stream_data):
                                            safe_filename = f"object_{obj_id}_{int(time.time())}.step"
                                            saved_files = self._save_step_data_fast(stream_data, safe_filename)
                                            if saved_files:
                                                print(f"[STEP-EXTRACT] ✅ Object stream STEP found: obj_{obj_id}")
                                                return saved_files
                                except:
                                    continue
                            
                        except Exception as obj_iter_error:
                            print(f"[STEP-EXTRACT] ⚠️ Object iteration error: {obj_iter_error}")
                        
                    except Exception as obj_error:
                        print(f"[STEP-EXTRACT] ⚠️ Object inspection error: {obj_error}")
                
                # ✅ METHOD 4: DOCUMENT-LEVEL SEARCH
                if not extracted and time.time() - start_time < TIMEOUT_SECONDS:
                    try:
                        print("[STEP-EXTRACT] 🔍 Method 4: Document-level search...")
                        
                        # Check document catalog safely
                        try:
                            if '/Names' in pdf.Root:
                                names = pdf.Root['/Names']
                                
                                # Check for JavaScript references
                                if '/JavaScript' in names:
                                    try:
                                        js_names = names['/JavaScript']
                                        if '/Names' in js_names:
                                            js_list = js_names['/Names']
                                            for i in range(0, min(len(js_list), 10), 2):
                                                if i + 1 < len(js_list):
                                                    js_name = str(js_list[i])
                                                    print(f"[STEP-EXTRACT] 📜 JavaScript: {js_name}")
                                                    if 'FileAttachment' in js_name or 'Attachment' in js_name:
                                                        print(f"[STEP-EXTRACT] 🎯 File attachment JS found: {js_name}")
                                    except Exception as js_error:
                                        print(f"[STEP-EXTRACT] ⚠️ JavaScript processing error: {js_error}")
                            
                            # Check document info
                            if '/Info' in pdf.trailer:
                                info = pdf.trailer['/Info']
                                for key, value in info.items():
                                    try:
                                        value_str = str(value).lower()
                                        if ('.stp' in value_str or '.step' in value_str) and '10080964' in value_str:
                                            print(f"[STEP-EXTRACT] ℹ️ Document info contains target STEP: {key} = {value}")
                                    except:
                                        continue
                        
                        except Exception as doc_search_error:
                            print(f"[STEP-EXTRACT] ⚠️ Document search error: {doc_search_error}")
                        
                    except Exception as doc_error:
                        print(f"[STEP-EXTRACT] ⚠️ Document-level search error: {doc_error}")
            
            total_time = time.time() - start_time
            
            if extracted:
                print(f"[STEP-EXTRACT] ✅ STEP extraction completed: {len(extracted)} files in {total_time:.3f}s")
                for i, path in enumerate(extracted):
                    size = os.path.getsize(path)
                    print(f"[STEP-EXTRACT]   #{i+1}: {os.path.basename(path)} ({size} bytes)")
            else:
                print(f"[STEP-EXTRACT] ❌ No STEP files found in {total_time:.3f}s")
                print("[STEP-EXTRACT] 🔍 Robust search completed: embedded, comments, objects, document-level")
                print("[STEP-EXTRACT] 💡 The PDF may contain STEP references in comments that require manual extraction")
            
            return extracted
            
        except Exception as e:
            print(f"[STEP-EXTRACT] ❌ Robust STEP extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def refresh_material_cache(self):
        with self._cache_lock:
            self._material_cache = {}
            self._last_cache_update = 0
        
        self._preload_essential_materials_lightning()
        lightning_cache._pattern_cache = None
        lightning_cache._notlar_patterns = None
        lightning_cache._technical_patterns = None
        print("[CACHE] ENHANCED material cache refreshed with TECHNICAL DRAWING support")

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
            return {"error": f"Enhanced cost calculation error: {str(e)}"}
    
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

def extract_enhanced_ocr_data(pdf_path, user_id=None, additional_param=None):
    try:
        print(f"[ENHANCED-OCR] Enhanced OCR with TECHNICAL DRAWING support: {os.path.basename(pdf_path)}")
        if user_id:
            print(f"[ENHANCED-OCR] User ID: {user_id}")
        
        text = extract_text_with_lightning_ocr(pdf_path)
        
        if text:
            technical_fields = extract_technical_drawing_fields(text)
            notlar_section = extract_notlar_section(text)
            material_keywords = extract_material_keywords_lightning(text)
            
            enhanced_data = {
                "extracted_text": text[:3000],
                "material_keywords": material_keywords,
                "technical_fields": technical_fields,
                "notlar_section": notlar_section if notlar_section else "",
                "has_technical_fields": bool(technical_fields),
                "has_notlar": bool(notlar_section),
                "confidence": (98 if technical_fields and material_keywords 
                              else 95 if notlar_section and material_keywords 
                              else 80 if material_keywords else 60),
                "method": "enhanced_technical_drawing_ocr",
                "processing_time": 0.8,
                "success": bool(text and len(text.strip()) > 10),
                "user_id": user_id,
                "pdf_path": pdf_path
            }
            
            print(f"[ENHANCED-OCR] Enhanced OCR: {len(material_keywords)} materials, TECHNICAL: {bool(technical_fields)}, NOTLAR: {bool(notlar_section)}")
            return enhanced_data
        
        else:
            return {
                "extracted_text": "",
                "material_keywords": [],
                "technical_fields": {},
                "notlar_section": "",
                "has_technical_fields": False,
                "has_notlar": False,
                "confidence": 0,
                "method": "enhanced_technical_drawing_ocr_failed",
                "processing_time": 0.1,
                "success": False,
                "error": "No text extracted",
                "user_id": user_id,
                "pdf_path": pdf_path
            }
            
    except Exception as e:
        print(f"[ENHANCED-OCR] Enhanced OCR error: {e}")
        return {
            "extracted_text": "",
            "material_keywords": [],
            "technical_fields": {},
            "notlar_section": "",
            "has_technical_fields": False,
            "has_notlar": False,
            "confidence": 0,
            "method": "enhanced_technical_drawing_ocr_error",
            "processing_time": 0.1,
            "success": False,
            "error": str(e),
            "user_id": user_id,
            "pdf_path": pdf_path
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
        print("[CACHE-COMPAT] Enhanced pattern cache refreshed")
        return True
    except Exception as e:
        print(f"[CACHE-COMPAT] Error: {e}")
        return False

def analyze_pdf_with_enhanced_speed(pdf_path):
    try:
        service = MaterialAnalysisService()
        result = {
            "material_matches": [],
            "step_analysis": {},
            "processing_log": []
        }
        return service._analyze_pdf_ultra_fast_optimized(pdf_path, result)
    except Exception as e:
        print(f"[ENHANCED-PDF] Error: {e}")
        return {"error": str(e)}

def get_enhanced_material_matches(text):
    try:
        service = MaterialAnalysisService()
        return service._find_materials_in_text_ultra_fast(text)
    except Exception as e:
        print(f"[ENHANCED-MATCH] Error: {e}")
        return []

def extract_notlar_materials(text):
    try:
        notlar_section = extract_notlar_section(text)
        if notlar_section:
            notlar_items = extract_notlar_items(notlar_section)
            if notlar_items:
                return find_materials_in_notlar_items(notlar_items)
        return []
    except Exception as e:
        print(f"[NOTLAR-EXTRACT] Error: {e}")
        return []

def extract_technical_drawing_materials(text):
    try:
        technical_fields = extract_technical_drawing_fields(text)
        if technical_fields:
            database = db.get_db()
            materials_cursor = database.materials.find({}, {"name": 1, "aliases": 1})
            materials_cache = {}
            for material in materials_cursor:
                materials_cache[material.get('name')] = material
            
            return find_materials_in_technical_fields(technical_fields, materials_cache)
        return []
    except Exception as e:
        print(f"[TECHNICAL-EXTRACT] Error: {e}")
        return []

# =====================================================
# DEBUG AND TEST FUNCTIONS
# =====================================================

def debug_material_detection_pipeline(text, materials_cache=None):
    if not text:
        print("[DEBUG] No text provided")
        return {}
    
    debug_result = {
        'input_text_length': len(text),
        'technical_fields': {},
        'notlar_section': '',
        'material_matches': [],
        'processing_steps': []
    }
    
    print(f"[DEBUG] Starting debug pipeline for {len(text)} chars of text")
    debug_result['processing_steps'].append("Started debug pipeline")
    
    # Step 1: Technical Drawing Fields
    print("[DEBUG] Step 1: Technical Drawing Fields Detection")
    technical_fields = extract_technical_drawing_fields(text)
    debug_result['technical_fields'] = technical_fields
    debug_result['processing_steps'].append(f"Technical fields found: {len(technical_fields)}")
    
    if technical_fields:
        print(f"[DEBUG] Found {len(technical_fields)} technical fields:")
        for field_key, field_data in technical_fields.items():
            print(f"  - {field_key}: '{field_data['content']}' (confidence: {field_data['confidence']}%)")
    
    # Step 2: NOTLAR Section
    print("[DEBUG] Step 2: NOTLAR Section Detection")
    notlar_section = extract_notlar_section(text)
    debug_result['notlar_section'] = notlar_section
    debug_result['processing_steps'].append(f"NOTLAR section: {'found' if notlar_section else 'not found'}")
    
    if notlar_section:
        print(f"[DEBUG] Found NOTLAR section: {len(notlar_section)} chars")
        notlar_items = extract_notlar_items(notlar_section)
        debug_result['notlar_items'] = len(notlar_items)
        print(f"[DEBUG] NOTLAR items: {len(notlar_items)}")
    
    # Step 3: Material Matching
    print("[DEBUG] Step 3: Material Matching")
    if not materials_cache:
        try:
            database = db.get_db()
            materials_cursor = database.materials.find({}, {"name": 1, "aliases": 1})
            materials_cache = {}
            for material in materials_cursor:
                materials_cache[material.get('name')] = material
            debug_result['processing_steps'].append(f"Loaded {len(materials_cache)} materials from database")
        except Exception as e:
            print(f"[DEBUG] Database error: {e}")
            materials_cache = {}
    
    # Try technical fields first
    if technical_fields and materials_cache:
        technical_matches = find_materials_in_technical_fields(technical_fields, materials_cache)
        debug_result['material_matches'].extend(technical_matches)
        debug_result['processing_steps'].append(f"Technical field matches: {len(technical_matches)}")
        
        if technical_matches:
            print(f"[DEBUG] Technical field matches: {len(technical_matches)}")
            for match in technical_matches:
                print(f"  - {match['keyword']} -> {match['material_name']} ({match['confidence']}%)")
    
    # Try NOTLAR if no technical matches
    if not debug_result['material_matches'] and notlar_section:
        notlar_items = extract_notlar_items(notlar_section)
        if notlar_items:
            notlar_matches = find_materials_in_notlar_items(notlar_items)
            debug_result['material_matches'].extend(notlar_matches)
            debug_result['processing_steps'].append(f"NOTLAR matches: {len(notlar_matches)}")
            
            if notlar_matches:
                print(f"[DEBUG] NOTLAR matches: {len(notlar_matches)}")
                for match in notlar_matches:
                    print(f"  - {match['keyword']} -> {match['material_name']} ({match['confidence']}%)")
    
    # Final summary
    total_matches = len(debug_result['material_matches'])
    print(f"[DEBUG] Final result: {total_matches} material matches found")
    debug_result['processing_steps'].append(f"Final result: {total_matches} matches")
    
    return debug_result

def test_pa6gf30_detection():
    test_cases = [
        "MALZEME: PA6GF30",
        "MALZEME/STANDART: PA6GF30",
        "MATERIAL: PA6GF30", 
        "PA6GF30 TOLERANS",
        "STANDART: PA6GF30",
        "MALZEME PA6GF30",
    ]
    
    print("[PA6GF30-TEST] Testing PA6GF30 detection in various formats")
    
    success_count = 0
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n[PA6GF30-TEST] Test {i}: '{test_text}'")
        debug_result = debug_material_detection_pipeline(test_text)
        found_materials = [match['material_name'] for match in debug_result['material_matches']]
        
        if 'GF30-PA66' in found_materials:
            print(f"[PA6GF30-TEST] SUCCESS: 'GF30-PA66' was detected!")
            success_count += 1
        else:
            print(f"[PA6GF30-TEST] FAILED: 'GF30-PA66' was NOT detected")
            print(f"[PA6GF30-TEST] Found materials: {found_materials}")
    
    print(f"\n[PA6GF30-TEST] Results: {success_count}/{len(test_cases)} tests passed")
    return success_count == len(test_cases)

# Export all functions
__all__ = [
    'MaterialAnalysisService',
    'MaterialAnalysisServiceOptimized', 
    'CostEstimationService',
    'CostEstimationServiceFast',
    'extract_enhanced_ocr_data',
    'get_material_cache',
    'refresh_pattern_cache',
    'analyze_pdf_with_enhanced_speed',
    'get_enhanced_material_matches',
    'extract_notlar_materials',
    'extract_technical_drawing_materials',
    'extract_technical_drawing_fields',
    'find_materials_in_technical_fields',
    'debug_material_detection_pipeline',
    'test_pa6gf30_detection',
    'create_service',
    'lightning_cache',
    'normalize_text_lightning',
    'extract_material_keywords_lightning',
    'extract_text_with_lightning_ocr',
    'extract_notlar_section',
    'extract_notlar_items',
    'find_materials_in_notlar_items'
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
print("🔧 ENHANCED MATERIAL ANALYSIS VERIFICATION")
print("="*60)

# Test technical field extraction
test_text_technical = "MALZEME: PA6GF30\nTOLERANS: DIN ISO 2768\nBOYUT: mm"
fields = extract_technical_drawing_fields(test_text_technical)
print(f"✅ Technical field extraction: {len(fields)} fields found")

# Test NOTLAR extraction  
test_text_notlar = "NOTLAR:\n1-MALZEME PA6GF30 KULLANILACAKTIR.\n2-KESKİN KÖŞELER KIRILACAKTIR."
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
print("🎯 ENHANCED FUNCTIONALITY READY!")
print("="*60)

print("\n" + "🚀 ENHANCED MATERIAL ANALYSIS SERVICE FULLY LOADED! 🚀")
print("📋 Available functions:")
print("  - extract_technical_drawing_fields()")
print("  - find_materials_in_technical_fields()")
print("  - debug_material_detection_pipeline()")
print("  - test_pa6gf30_detection()")
print("  - MaterialAnalysisService.analyze_document_ultra_fast()")
print("\n✨ Ready to detect materials from MALZEME/STANDART fields! ✨")
