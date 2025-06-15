# services/step_meta_reader.py
import re
from typing import Dict, Any, Optional

def extract_step_metadata_ocp(step_path: str) -> Optional[Dict[str, Any]]:
    """
    STEP dosyasından metadata çıkarır
    OpenCascade Python ile STEP dosyasından header bilgilerini okur
    """
    try:
        metadata = {}
        
        # STEP dosyasını metin olarak oku
        with open(step_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # Header bölümünü bul
        header_match = re.search(r'HEADER;(.*?)ENDSEC;', content, re.DOTALL)
        if not header_match:
            return None
        
        header_content = header_match.group(1)
        
        # FILE_DESCRIPTION
        file_desc_match = re.search(r"FILE_DESCRIPTION\s*\(\s*\(\s*'([^']+)'\s*\)", header_content)
        if file_desc_match:
            metadata['file_description'] = file_desc_match.group(1)
        
        # FILE_NAME
        file_name_match = re.search(r"FILE_NAME\s*\(\s*'([^']+)'", header_content)
        if file_name_match:
            metadata['original_filename'] = file_name_match.group(1)
        
        # Timestamp
        timestamp_match = re.search(r"'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'", header_content)
        if timestamp_match:
            metadata['timestamp'] = timestamp_match.group(1)
        
        # Author/Creator
        author_match = re.search(r"\(\s*'([^']+)'\s*\)\s*,\s*\(\s*'([^']+)'\s*\)", header_content)
        if author_match:
            metadata['author'] = author_match.group(1)
            metadata['organization'] = author_match.group(2)
        
        # FILE_SCHEMA
        schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'\s*\)", header_content)
        if schema_match:
            metadata['schema'] = schema_match.group(1)
        
        # CAD Software bilgisi (eğer varsa)
        software_patterns = [
            r"'(SolidWorks[^']*)'",
            r"'(Inventor[^']*)'", 
            r"'(CATIA[^']*)'",
            r"'(NX[^']*)'",
            r"'(Fusion\s*360[^']*)'",
            r"'(AutoCAD[^']*)'",
            r"'(Creo[^']*)'",
            r"'(SOLIDEDGE[^']*)'",
            r"'(Rhino[^']*)'",
            r"'(FreeCAD[^']*)'",
            r"'(onshape[^']*)'",
        ]
        
        for pattern in software_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['cad_software'] = match.group(1)
                break
        
        # Unit bilgisi
        unit_patterns = [
            r"'MILLIMETRE'",
            r"'MM'",
            r"'METRE'", 
            r"'INCH'",
            r"'FOOT'"
        ]
        
        for i, pattern in enumerate(unit_patterns):
            if re.search(pattern, content, re.IGNORECASE):
                units = ['mm', 'mm', 'm', 'inch', 'foot']
                metadata['units'] = units[i]
                break
        
        # Tolerans bilgisi (eğer varsa)
        tolerance_match = re.search(r"GEOMETRIC_TOLERANCE.*?([0-9]+\.?[0-9]*)", content)
        if tolerance_match:
            metadata['geometric_tolerance'] = float(tolerance_match.group(1))
        
        # Malzeme bilgisi (STEP dosyasındaki property'lerden)
        material_patterns = [
            r"'MATERIAL'.*?'([^']+)'",
            r"'STEEL'",
            r"'ALUMINUM'",
            r"'ALUMINIUM'",
            r"'BRASS'",
            r"'COPPER'",
            r"'PLASTIC'",
            r"'TITANIUM'"
        ]
        
        for pattern in material_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if match.groups():
                    metadata['embedded_material'] = match.group(1)
                else:
                    metadata['embedded_material'] = match.group(0).strip("'")
                break
        
        return metadata if metadata else None
        
    except Exception as e:
        print(f"[ERROR] STEP metadata okuma hatası: {e}")
        return None

def extract_step_entities_info(step_path: str) -> Optional[Dict[str, Any]]:
    """
    STEP dosyasındaki entity türlerini ve sayılarını çıkarır
    """
    try:
        with open(step_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # DATA bölümünü bul
        data_match = re.search(r'DATA;(.*?)ENDSEC;', content, re.DOTALL)
        if not data_match:
            return None
        
        data_content = data_match.group(1)
        
        # Entity sayıları
        entities = {}
        
        # Yaygın STEP entity'leri
        entity_patterns = {
            'CARTESIAN_POINT': r'CARTESIAN_POINT',
            'DIRECTION': r'DIRECTION',
            'VECTOR': r'VECTOR',
            'LINE': r'LINE',
            'CIRCLE': r'CIRCLE',
            'PLANE': r'PLANE',
            'CYLINDRICAL_SURFACE': r'CYLINDRICAL_SURFACE',
            'ADVANCED_FACE': r'ADVANCED_FACE',
            'CLOSED_SHELL': r'CLOSED_SHELL',
            'MANIFOLD_SOLID_BREP': r'MANIFOLD_SOLID_BREP',
            'VERTEX_POINT': r'VERTEX_POINT',
            'EDGE_CURVE': r'EDGE_CURVE',
            'FACE_SURFACE': r'FACE_SURFACE'
        }
        
        for entity_name, pattern in entity_patterns.items():
            matches = re.findall(pattern, data_content)
            if matches:
                entities[entity_name.lower() + '_count'] = len(matches)
        
        # Toplam entity sayısı
        total_entities = len(re.findall(r'#\d+\s*=', data_content))
        entities['total_entities'] = total_entities
        
        # Komplekslik tahmini
        if total_entities > 10000:
            entities['complexity'] = 'high'
        elif total_entities > 1000:
            entities['complexity'] = 'medium'
        else:
            entities['complexity'] = 'low'
        
        return entities
        
    except Exception as e:
        print(f"[ERROR] STEP entity analizi hatası: {e}")
        return None

def get_step_file_info(step_path: str) -> Dict[str, Any]:
    """
    STEP dosyası hakkında kapsamlı bilgi toplar
    """
    import os
    
    info = {
        'file_size_bytes': 0,
        'file_size_mb': 0,
        'metadata': None,
        'entities': None,
        'error': None
    }
    
    try:
        # Dosya boyutu
        if os.path.exists(step_path):
            info['file_size_bytes'] = os.path.getsize(step_path)
            info['file_size_mb'] = round(info['file_size_bytes'] / (1024 * 1024), 2)
        
        # Metadata çıkar
        metadata = extract_step_metadata_ocp(step_path)
        if metadata:
            info['metadata'] = metadata
        
        # Entity bilgileri
        entities = extract_step_entities_info(step_path)
        if entities:
            info['entities'] = entities
            
    except Exception as e:
        info['error'] = str(e)
    
    return info