# services/cad_converter.py - Enhanced PRT/CATPART to STEP Converter with Physical File Saving

import os
import subprocess
import tempfile
import time
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
from datetime import datetime

# Import NX converter service
try:
    from services.nx_converter_service import nx_converter, get_nx_conversion_help
    NX_CONVERTER_AVAILABLE = True
except ImportError:
    NX_CONVERTER_AVAILABLE = False
    nx_converter = None
    get_nx_conversion_help = None

logger = logging.getLogger(__name__)

class CADConverterService:
    """
    PRT ve CATPART dosyalarını fiziksel STEP formatına çeviren gelişmiş servis
    Enhanced for Docker environment with physical file saving capabilities
    """
    
    def __init__(self, output_base_dir: str = None):
        self.supported_formats = {
            '.prt': 'nx_part',
            '.catpart': 'catia_part', 
            '.step': 'step',
            '.stp': 'step'
        }
        
        # Fiziksel dosya kaydetme için klasör yapısı
        self.output_base_dir = output_base_dir or os.path.join(os.getcwd(), "converted_files")
        self.temp_dir = os.path.join(os.getcwd(), "temp", "cad_conversion")
        
        print(f"[CAD-CONVERTER-INIT] 📁 Output base dir: {self.output_base_dir}")
        print(f"[CAD-CONVERTER-INIT] 📁 Temp dir: {self.temp_dir}")
        
        # Ana klasörleri oluştur - CRITICAL
        try:
            os.makedirs(self.output_base_dir, exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)
            print(f"[CAD-CONVERTER-INIT] ✅ Main directories created")
        except Exception as dir_error:
            print(f"[CAD-CONVERTER-INIT] ❌ Failed to create main directories: {dir_error}")
            raise
        
        # Alt klasörler oluştur
        try:
            self._create_output_structure()
            print(f"[CAD-CONVERTER-INIT] ✅ Output structure created")
        except Exception as struct_error:
            print(f"[CAD-CONVERTER-INIT] ❌ Failed to create output structure: {struct_error}")
            # Bu critical değil, devam edebiliriz
        
        # Docker environment setup
        self._setup_docker_environment()
        
        # Converter tool paths
        self.freecad_path = self._find_freecad()
        self.python_api_available = self._check_python_api()
        
        logger.info(f"🔧 CAD Converter initialized - Output Dir: {self.output_base_dir}")
        logger.info(f"   FreeCAD: {bool(self.freecad_path)}, Python API: {self.python_api_available}")
        
        # Verify critical directories
        print(f"[CAD-CONVERTER-INIT] 🔍 Directory verification:")
        print(f"   - Output base: {os.path.exists(self.output_base_dir)} ({self.output_base_dir})")
        print(f"   - Temp: {os.path.exists(self.temp_dir)} ({self.temp_dir})")
        if hasattr(self, 'step_files_dir'):
            print(f"   - STEP files: {os.path.exists(self.step_files_dir)} ({self.step_files_dir})")
        if hasattr(self, 'original_files_dir'):
            print(f"   - Original files: {os.path.exists(self.original_files_dir)} ({self.original_files_dir})")

    def _create_output_structure(self):
        """Çıkış dosyaları için klasör yapısını oluşturur - ENHANCED"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            self.daily_output_dir = os.path.join(self.output_base_dir, today)
            self.step_files_dir = os.path.join(self.daily_output_dir, "step_files")
            self.original_files_dir = os.path.join(self.daily_output_dir, "original_files")
            self.log_dir = os.path.join(self.daily_output_dir, "conversion_logs")
            
            directories_to_create = [
                self.daily_output_dir,
                self.step_files_dir, 
                self.original_files_dir,
                self.log_dir
            ]
            
            print(f"[CAD-CONVERTER-STRUCT] 📁 Creating {len(directories_to_create)} directories...")
            
            for dir_path in directories_to_create:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"[CAD-CONVERTER-STRUCT] ✅ Created: {dir_path}")
                    
                    # Verify directory was created and is writable
                    if not os.path.exists(dir_path):
                        raise Exception(f"Directory creation failed: {dir_path}")
                    
                    # Test write permissions
                    test_file = os.path.join(dir_path, ".write_test")
                    try:
                        with open(test_file, 'w') as f:
                            f.write("test")
                        os.remove(test_file)
                        print(f"[CAD-CONVERTER-STRUCT] ✅ Write test passed: {dir_path}")
                    except Exception as write_error:
                        print(f"[CAD-CONVERTER-STRUCT] ⚠️ Write test failed: {dir_path} - {write_error}")
                        
                except Exception as dir_error:
                    print(f"[CAD-CONVERTER-STRUCT] ❌ Failed to create {dir_path}: {dir_error}")
                    raise
            
            logger.info(f"📁 Output structure created: {self.daily_output_dir}")
            print(f"[CAD-CONVERTER-STRUCT] ✅ All directories created successfully")
            
        except Exception as e:
            print(f"[CAD-CONVERTER-STRUCT] ❌ Critical error in _create_output_structure: {e}")
            import traceback
            print(f"[CAD-CONVERTER-STRUCT] 📋 Traceback: {traceback.format_exc()}")
            raise
   
    def _setup_docker_environment(self):
        """Docker container için environment setup"""
        try:
            # Virtual display için DISPLAY variable
            if not os.environ.get('DISPLAY'):
                os.environ['DISPLAY'] = ':99'
                logger.info("🐳 DISPLAY set to :99 for headless operation")
            
            # FreeCAD için gerekli environment variables
            freecad_home = os.path.join(os.getcwd(), 'freecad_home')
            if not os.environ.get('FREECAD_USER_HOME'):
                os.environ['FREECAD_USER_HOME'] = freecad_home
            
            os.environ['CADQUERY_DISABLE_JUPYTER'] = '1'
            
            # Create FreeCAD user directory
            os.makedirs(freecad_home, exist_ok=True)
            
            # FreeCAD Python path için
            freecad_python_paths = [
                "/usr/lib/freecad-python3/lib",
                "/usr/lib/freecad/lib",
                "/usr/share/freecad/lib"
            ]
            
            current_python_path = os.environ.get('PYTHONPATH', '')
            for path in freecad_python_paths:
                if os.path.exists(path) and path not in current_python_path:
                    current_python_path = f"{path}:{current_python_path}" if current_python_path else path
            
            if current_python_path:
                os.environ['PYTHONPATH'] = current_python_path
            
            logger.info("🐳 Docker environment configured")
            
        except Exception as e:
            logger.warning(f"⚠️ Docker environment setup warning: {str(e)}")
    
    def _check_python_api(self) -> bool:
        """FreeCAD Python API'sinin kullanılabilir olup olmadığını kontrol eder"""
        try:
            import FreeCAD
            import Import
            import Part
            logger.info("✅ FreeCAD Python API available")
            return True
        except ImportError as e:
            logger.warning(f"⚠️ FreeCAD Python API not available: {str(e)}")
            return False
    
    def _find_freecad(self) -> Optional[str]:
        """FreeCAD executable'ını bulur"""
        
        # Docker container'da öncelik sırası
        docker_priority_paths = [
            "/usr/bin/freecad",
            "/usr/bin/freecad-daily",
            "/usr/local/bin/freecad"
        ]
        
        # Docker paths'i önce kontrol et
        for path in docker_priority_paths:
            if os.path.exists(path):
                logger.info(f"✅ FreeCAD found at: {path}")
                return path
        
        # Diğer olası path'ler
        possible_paths = [
            "/opt/freecad/bin/freecad",
            "C:\\Program Files\\FreeCAD\\bin\\FreeCAD.exe",
            "C:\\Program Files (x86)\\FreeCAD\\bin\\FreeCAD.exe",
            "/Applications/FreeCAD.app/Contents/MacOS/FreeCAD",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ FreeCAD found at: {path}")
                return path
        
        # PATH'de ara
        try:
            result = subprocess.run(["which", "freecad"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"✅ FreeCAD found in PATH: {path}")
                return path
        except:
            pass
        
        # Python API varsa, command line gerektirmeyebilir
        if self._check_python_api():
            logger.info("✅ FreeCAD Python API available, command line not required")
            return "python_api_only"
        
        logger.warning("⚠️ FreeCAD not found. PRT/CATPART conversion will not be available.")
        return None
    
    def is_supported_format(self, file_path: str) -> bool:
        """Dosya formatının desteklenip desteklenmediğini kontrol eder"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats
    
    def needs_conversion(self, file_path: str) -> bool:
        """Dosyanın STEP'e çevrilmesi gerekip gerekmediğini kontrol eder"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in ['.prt', '.catpart']
    
    def _analyze_prt_file(self, file_path: str) -> Dict[str, Any]:
        """PRT dosyasının formatını analiz eder - ENHANCED WITH DEBUG"""
        try:
            file_size = os.path.getsize(file_path)
            print(f"[PRT-ANALYZE] 📁 Analyzing file: {file_path}")
            print(f"[PRT-ANALYZE] 📊 File size: {file_size} bytes")
            
            with open(file_path, 'rb') as f:
                # Read more data for better detection
                header_data = f.read(4096)  # Read 4KB instead of 1KB
                
                # Debug: Print first 100 bytes as hex
                print(f"[PRT-ANALYZE] 🔍 First 100 bytes (hex): {header_data[:100].hex()}")
                
                # Debug: Print first 50 bytes as raw
                print(f"[PRT-ANALYZE] 🔍 First 50 bytes (raw): {header_data[:50]}")
                
                # Text olarak da oku
                try:
                    header_text = header_data.decode('utf-8', errors='ignore')
                    header_text_upper = header_text.upper()
                    # Debug: Print readable text preview
                    readable_preview = ''.join(c if c.isprintable() or c.isspace() else '.' for c in header_text[:200])
                    print(f"[PRT-ANALYZE] 📝 Readable preview: {readable_preview}")
                except:
                    header_text = ""
                    header_text_upper = ""
                
                # Try different encodings
                encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
                for encoding in encodings:
                    try:
                        alt_text = header_data.decode(encoding, errors='ignore')[:500]
                        if any(keyword in alt_text.upper() for keyword in ['PARASOLID', 'UNIGRAPHICS', 'NX', 'CREO', 'CATIA', 'SOLIDWORKS']):
                            print(f"[PRT-ANALYZE] 🔍 Found keyword with {encoding} encoding")
                            header_text_upper = alt_text.upper()
                            break
                    except:
                        continue
                
                # Extended format detection
                
                # 1. NX/Unigraphics - Check more patterns
                if any(pattern in header_data for pattern in [b'UNIGRAPHICS', b'NX', b'UG', b'Siemens', b'UGII']):
                    print(f"[PRT-ANALYZE] ✅ Detected NX/Unigraphics pattern")
                    return {"format": "NX/Unigraphics", "confidence": 90}
                
                # 2. Check for NX by file structure
                if header_data[:4] == b'\x00\x00\x00\x00' and header_data[4:8] != b'\x00\x00\x00\x00':
                    # Possible NX binary format
                    print(f"[PRT-ANALYZE] 🔍 Possible NX binary structure")
                    return {"format": "NX/Unigraphics", "confidence": 70}
                
                # 3. Creo/Pro-E
                if any(pattern in header_data for pattern in [b'#UGC', b'#Creo', b'PTC', b'Pro/ENGINEER']):
                    print(f"[PRT-ANALYZE] ✅ Detected Creo/Pro-E pattern")
                    return {"format": "Creo/Pro-E", "confidence": 85}
                
                # 4. Parasolid - Multiple patterns
                if any(pattern in header_data for pattern in [b'**PARA', b'PARASOLID', b'**PART', b'**ASSEMBLY']):
                    print(f"[PRT-ANALYZE] ✅ Detected Parasolid pattern")
                    return {"format": "Parasolid", "confidence": 85}
                
                # Check text patterns
                if 'PARASOLID' in header_text_upper or '**PARA' in header_text_upper:
                    print(f"[PRT-ANALYZE] ✅ Detected Parasolid in text")
                    return {"format": "Parasolid", "confidence": 85}
                
                # 5. STEP
                if 'ISO-10303' in header_text_upper or 'STEP' in header_text_upper:
                    print(f"[PRT-ANALYZE] ✅ Detected STEP format")
                    return {"format": "STEP", "confidence": 95}
                
                # 6. IGES
                if header_text.startswith('                                                                        S      1'):
                    print(f"[PRT-ANALYZE] ✅ Detected IGES format")
                    return {"format": "IGES", "confidence": 90}
                
                # 7. SolidWorks (sometimes uses .prt)
                if header_data[:4] == b'\xd0\xcf\x11\xe0':  # OLE header
                    print(f"[PRT-ANALYZE] 🔍 Detected OLE format (possibly SolidWorks)")
                    return {"format": "SolidWorks", "confidence": 60}
                
                # 8. CATIA
                if any(pattern in header_data for pattern in [b'CATIA', b'V5', b'V4', b'ENOVIA']):
                    print(f"[PRT-ANALYZE] ✅ Detected CATIA pattern")
                    return {"format": "CATIA", "confidence": 75}
                
                # 9. Check for binary patterns common in CAD files
                # Check if file is mostly binary (non-text)
                text_chars = sum(1 for byte in header_data[:1000] if 32 <= byte <= 126 or byte in [9, 10, 13])
                binary_ratio = 1 - (text_chars / min(1000, len(header_data)))
                
                print(f"[PRT-ANALYZE] 📊 Binary ratio: {binary_ratio:.2f}")
                
                if binary_ratio > 0.8:
                    # Highly binary file - likely proprietary CAD format
                    # Try to guess based on patterns
                    if b'\x00\x00\x00' in header_data[:20]:  # Common in many CAD formats
                        print(f"[PRT-ANALYZE] 🔍 Binary CAD file with null bytes pattern")
                        return {"format": "Binary CAD (Unknown vendor)", "confidence": 40}
                
                # 10. Last resort - check file extension patterns in the content
                if 'PRT' in header_text_upper and binary_ratio > 0.5:
                    print(f"[PRT-ANALYZE] 🔍 Found PRT reference in content")
                    return {"format": "Generic PRT", "confidence": 30}
                
                print(f"[PRT-ANALYZE] ❌ Could not determine format")
                return {"format": "unknown", "confidence": 0}
                
        except Exception as e:
            print(f"[PRT-ANALYZE] ❌ Analysis error: {str(e)}")
            import traceback
            print(f"[PRT-ANALYZE] 📋 Traceback: {traceback.format_exc()}")
            return {"format": "unknown", "confidence": 0}

    def _try_alternative_prt_conversion(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """PRT dosyaları için alternatif conversion yöntemleri - ENHANCED VERSION"""
        try:
            print(f"[PRT-FALLBACK] 🔧 Trying alternative PRT conversion methods...")
            
            # Get file size first
            file_size = os.path.getsize(input_path)
            
            # First, analyze the file
            file_analysis = self._analyze_prt_file(input_path)
            print(f"[PRT-FALLBACK] 📊 File analysis: {file_analysis['format']} (confidence: {file_analysis['confidence']}%)")
            
            # Method 1: Check if it's actually a disguised STEP/IGES file
            if file_analysis['format'] == 'STEP' and file_analysis['confidence'] > 80:
                print(f"[PRT-FALLBACK] 🔍 File appears to be STEP format despite .prt extension")
                shutil.copy2(input_path, output_path)
                if os.path.exists(output_path):
                    return {
                        "success": True,
                        "processing_time": 0.1,
                        "message": "PRT file was actually STEP format",
                        "method": "direct_copy",
                        "detected_format": "STEP"
                    }
            
            elif file_analysis['format'] == 'IGES' and file_analysis['confidence'] > 80:
                print(f"[PRT-FALLBACK] 🔍 File appears to be IGES format, attempting conversion...")
                try:
                    import FreeCAD
                    import Import
                    
                    # Create temp IGES file
                    temp_iges = input_path + ".iges"
                    shutil.copy2(input_path, temp_iges)
                    
                    doc = FreeCAD.newDocument("IGESConv")
                    Import.insert(temp_iges, doc.Name)
                    
                    shapes = []
                    for obj in doc.Objects:
                        if hasattr(obj, 'Shape') and obj.Shape and obj.Shape.isValid():
                            shapes.append(obj.Shape)
                    
                    if shapes:
                        import Part
                        if len(shapes) == 1:
                            compound = shapes[0]
                        else:
                            compound = Part.makeCompound(shapes)
                        compound.exportStep(output_path)
                        
                        FreeCAD.closeDocument(doc.Name)
                        os.remove(temp_iges)
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                            return {
                                "success": True,
                                "processing_time": 1.0,
                                "message": "Converted IGES (disguised as PRT) to STEP",
                                "method": "iges_conversion",
                                "detected_format": "IGES"
                            }
                    
                    FreeCAD.closeDocument(doc.Name)
                    os.remove(temp_iges)
                except Exception as iges_error:
                    print(f"[PRT-FALLBACK] ❌ IGES conversion failed: {iges_error}")
            
            # Method 2: If it's NX/Unigraphics, use NX converter service
            if file_analysis['format'] == 'NX/Unigraphics' and NX_CONVERTER_AVAILABLE:
                print(f"[PRT-FALLBACK] 🔧 Using NX Converter Service...")
                
                # First try external conversion if available
                nx_result = nx_converter.convert_nx_to_step_external(input_path, output_path)
                if nx_result.get('success'):
                    return nx_result
                
                # Get detailed help for user
                help_info = get_nx_conversion_help(
                    filename=os.path.basename(input_path),
                    file_size=file_size
                )
                
                # Return detailed error with NX-specific help
                return {
                    "success": False,
                    "error": "NX/Unigraphics format requires licensed NX software for conversion",
                    "detected_format": "NX/Unigraphics",
                    "format_confidence": file_analysis['confidence'],
                    "file_size": file_size,
                    "nx_help": help_info,
                    "conversion_options": help_info['conversion_options'],
                    "alternative_workflow": help_info['alternative_workflow'],
                    "recommendations": [
                        "Use NX software: File → Export → STEP",
                        "Contact CAD support for conversion assistance",
                        "Upload technical drawing PDF as alternative"
                    ],
                    "support_contact": help_info.get('support_contact', {})
                }
            
            # Method 3: If it's Parasolid, try specific approach
            if file_analysis['format'] == 'Parasolid':
                print(f"[PRT-FALLBACK] 🔧 Trying Parasolid conversion...")
                try:
                    import FreeCAD
                    import Part
                    
                    # Try direct Part.read for Parasolid
                    try:
                        shape = Part.read(input_path)
                        if shape and shape.isValid():
                            shape.exportStep(output_path)
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                                return {
                                    "success": True,
                                    "processing_time": 1.0,
                                    "message": "Converted Parasolid to STEP",
                                    "method": "parasolid_direct",
                                    "detected_format": "Parasolid"
                                }
                    except Exception as parasolid_error:
                        print(f"[PRT-FALLBACK] ❌ Parasolid conversion failed: {parasolid_error}")
                
                except Exception as e:
                    print(f"[PRT-FALLBACK] ❌ Parasolid approach failed: {e}")
            
            # Method 3: Try generic/unknown format approaches
            print(f"[PRT-FALLBACK] 🔧 Trying generic conversion approaches for {file_analysis['format']} format...")
            
            # Try FreeCAD with file extension workarounds
            try:
                import FreeCAD
                import Part
                
                # Approach 1: Try renaming to different extensions
                extensions_to_try = ['.x_t', '.x_b', '.xmt_txt', '.xmt_bin']
                
                for ext in extensions_to_try:
                    try:
                        temp_file = input_path + ext
                        shutil.copy2(input_path, temp_file)
                        
                        print(f"[PRT-FALLBACK] 🔄 Trying as {ext} format...")
                        shape = Part.read(temp_file)
                        
                        if shape and shape.isValid():
                            shape.exportStep(output_path)
                            os.remove(temp_file)
                            
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                                return {
                                    "success": True,
                                    "processing_time": 2.0,
                                    "message": f"Converted by treating as {ext} format",
                                    "method": f"extension_trick_{ext}",
                                    "detected_format": file_analysis['format']
                                }
                        
                        os.remove(temp_file)
                    except Exception as ext_error:
                        print(f"[PRT-FALLBACK] ❌ {ext} approach failed: {ext_error}")
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                
            except Exception as generic_error:
                print(f"[PRT-FALLBACK] ❌ Generic approaches failed: {generic_error}")
            
            # Method 4: Use command line converter if available
            if self.freecad_path and self.freecad_path not in ["python_api_only"]:
                try:
                    print(f"[PRT-FALLBACK] 🔧 Trying command line with basic script...")
                    
                    # Create a simple conversion script
                    simple_script = f'''
import FreeCAD
import Part
import sys

try:
    print("[SCRIPT] Starting PRT conversion...")
    print("[SCRIPT] File: {input_path}")
    
    # Try different methods
    shape = None
    
    # Method 1: Direct Part.read
    try:
        shape = Part.read("{input_path}")
        print("[SCRIPT] Part.read successful")
    except:
        print("[SCRIPT] Part.read failed")
        
        # Method 2: Part.Shape().read
        try:
            shape = Part.Shape()
            shape.read("{input_path}")
            print("[SCRIPT] Part.Shape.read successful")
        except:
            print("[SCRIPT] Part.Shape.read failed")
            sys.exit(1)
    
    if shape and shape.isValid():
        shape.exportStep("{output_path}")
        print("[SCRIPT] STEP export successful")
        sys.exit(0)
    else:
        print("[SCRIPT] No valid shape found")
        sys.exit(1)
        
except Exception as e:
    print(f"[SCRIPT] Error: {{e}}")
    sys.exit(1)
'''
                    
                    script_path = os.path.join(self.temp_dir, f"simple_prt_script_{uuid.uuid4().hex[:8]}.py")
                    
                    with open(script_path, 'w', encoding='utf-8') as f:
                        f.write(simple_script)
                    
                    # Run the script
                    cmd = [self.freecad_path, "--console", script_path]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=self.temp_dir,
                        env=os.environ.copy()
                    )
                    
                    os.remove(script_path)
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        return {
                            "success": True,
                            "processing_time": 3.0,
                            "message": "Conversion successful with command line script",
                            "method": "command_line_simple",
                            "stdout": result.stdout,
                            "detected_format": file_analysis['format']
                        }
                    else:
                        print(f"[PRT-FALLBACK] ❌ Command line script failed: {result.stderr}")
                        
                except Exception as cmd_error:
                    print(f"[PRT-FALLBACK] ❌ Command line approach failed: {cmd_error}")
            
            # Method 4: Check if file is empty or corrupted
            file_size = os.path.getsize(input_path)
            if file_size < 100:
                return {
                    "success": False,
                    "error": f"PRT file is too small ({file_size} bytes), possibly corrupted",
                    "detected_format": file_analysis.get('format', 'unknown')
                }
            
            # Provide detailed error with recommendations
            error_msg = f"PRT conversion not supported for {file_analysis['format']} format"
            recommendations = []
            nx_help = None
            support_contact = None
            
            if file_analysis['format'] == 'NX/Unigraphics':
                if NX_CONVERTER_AVAILABLE:
                    # Get detailed NX help
                    help_info = get_nx_conversion_help(
                        filename=os.path.basename(input_path),
                        file_size=file_size
                    )
                    nx_help = help_info
                    support_contact = help_info.get('support_contact')
                    recommendations = [
                        "NX yazılımında: File → Export → STEP 214",
                        "CAD desteğe başvurun: cad-support@company.com",
                        "Alternatif: Teknik çizim PDF'ini yükleyin"
                    ]
                else:
                    recommendations = [
                        "This is an NX/Unigraphics file. Please export as STEP from NX.",
                        "Use File > Export > STEP 214 or STEP 203 in NX software"
                    ]
            elif file_analysis['format'] == 'Creo/Pro-E':
                recommendations = [
                    "This is a Creo/Pro-ENGINEER file. Please export as STEP from Creo.",
                    "Use File > Save As > Save a Copy > STEP in Creo"
                ]
            elif file_analysis['format'] == 'Parasolid':
                recommendations = [
                    "This is a Parasolid file. Limited support in FreeCAD.",
                    "Consider using a CAD system that supports Parasolid import/export"
                ]
            elif file_analysis['format'] == 'SolidWorks':
                recommendations = [
                    "This appears to be a SolidWorks file.",
                    "Use File > Save As > STEP (*.step) in SolidWorks"
                ]
            elif file_analysis['format'] == 'Binary CAD (Unknown vendor)':
                recommendations = [
                    "Binary CAD format detected but vendor unknown.",
                    "Please identify the source CAD software.",
                    "Export as STEP AP203 or AP214 from the original software."
                ]
            else:
                # Unknown format - provide comprehensive help
                recommendations = [
                    "PRT dosya formatı tespit edilemedi.",
                    "Lütfen aşağıdaki bilgileri kontrol edin:",
                    "1. Dosyanın hangi CAD yazılımından geldiğini öğrenin",
                    "2. Orijinal CAD yazılımından STEP formatında export yapın",
                    "3. Yaygın CAD yazılımları: NX, Creo, SolidWorks, CATIA",
                    "4. STEP AP203 veya AP214 formatları önerilir"
                ]
            
            # Add file size info
            if file_size < 1000:
                recommendations.append(f"Dosya çok küçük ({file_size} bytes), bozuk olabilir.")
            
            result = {
                "success": False,
                "error": error_msg,
                "methods_tried": ["format_detection", "iges_conversion", "parasolid_conversion", "generic_approaches", "command_line"],
                "file_size": file_size,
                "detected_format": file_analysis['format'],
                "format_confidence": file_analysis['confidence'],
                "recommendations": recommendations,
                "debug_info": {
                    "first_bytes_hex": header_data[:20].hex() if 'header_data' in locals() else None,
                    "binary_ratio": binary_ratio if 'binary_ratio' in locals() else None
                }
            }
            
            # Add NX-specific help if available
            if nx_help:
                result["nx_help"] = nx_help
                result["conversion_options"] = nx_help.get('conversion_options', {})
                result["alternative_workflow"] = nx_help.get('alternative_workflow', {})
            
            if support_contact:
                result["support_contact"] = support_contact
            
            return result
            
        except Exception as e:
            print(f"[PRT-FALLBACK] ❌ Fallback conversion error: {str(e)}")
            return {
                "success": False,
                "error": f"PRT fallback conversion failed: {str(e)}"
            }
    
    def convert_to_step(self, input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Temel çevirme fonksiyonu - FIXED VERSION WITH BETTER PRT SUPPORT
        """
        try:
            print(f"[CAD-CONVERT] 🔧 Starting conversion: {input_path}")
            
            if not os.path.exists(input_path):
                return {
                    "success": False,
                    "error": f"Input file not found: {input_path}"
                }
            
            file_ext = Path(input_path).suffix.lower()

            # For PRT files, always try fallback methods first
            if file_ext.lower() == '.prt':
                print(f"[CAD-CONVERT] 🔄 PRT file detected, using fallback methods directly...")
                
                # Ensure output path
                if not output_path:
                    base_name = Path(input_path).stem
                    os.makedirs(self.temp_dir, exist_ok=True)
                    output_path = os.path.join(self.temp_dir, f"{base_name}_{uuid.uuid4().hex[:8]}.step")
                else:
                    output_dir = os.path.dirname(output_path)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                
                # Try PRT-specific methods
                fallback_result = self._try_alternative_prt_conversion(input_path, output_path)
                
                if fallback_result["success"]:
                    fallback_result["method_used"] = "prt_fallback"
                    fallback_result["conversion_needed"] = True
                    fallback_result["input_format"] = file_ext
                    fallback_result["output_format"] = ".step"
                    fallback_result["output_path"] = output_path
                    return fallback_result
                else:
                    # PRT conversion failed completely
                    return {
                        "success": False,
                        "error": f"PRT file conversion not supported: {fallback_result.get('error', 'Unknown error')}",
                        "input_format": file_ext,
                        "output_format": ".step",
                        "conversion_needed": True,
                        "methods_tried": fallback_result.get('methods_tried', [])
                    }
            
            if not self.needs_conversion(input_path):
                if file_ext in ['.step', '.stp']:
                    if output_path and input_path != output_path:
                        import shutil
                        # Output directory oluştur
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        shutil.copy2(input_path, output_path)
                    return {
                        "success": True,
                        "output_path": output_path or input_path,
                        "conversion_needed": False,
                        "message": "File is already in STEP format"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported file format: {file_ext}"
                    }
            
            # Output path belirle ve directory oluştur
            if not output_path:
                base_name = Path(input_path).stem
                # Temp directory'nin var olduğundan emin ol
                os.makedirs(self.temp_dir, exist_ok=True)
                output_path = os.path.join(self.temp_dir, f"{base_name}_{uuid.uuid4().hex[:8]}.step")
            else:
                # Output directory'nin var olduğundan emin ol
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
            
            print(f"[CAD-CONVERT] 📂 Output path: {output_path}")
            print(f"[CAD-CONVERT] 📁 Output directory exists: {os.path.exists(os.path.dirname(output_path))}")
            
            # For CATPART files, try standard methods
            if file_ext == '.catpart':
                # Method 1: Python API (Öncelikli - Docker'da daha güvenilir)
                if self.python_api_available:
                    logger.info("🚀 Trying FreeCAD Python API method for CATPART...")
                    try:
                        result = self._convert_catpart_with_python_api(input_path, output_path)
                        if result["success"]:
                            result["method_used"] = "python_api"
                            result["conversion_needed"] = True
                            result["input_format"] = file_ext
                            result["output_format"] = ".step"
                            print(f"[CAD-CONVERT] ✅ Python API conversion successful")
                            return result
                        else:
                            logger.warning(f"⚠️ Python API failed: {result.get('error')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Python API method failed: {str(e)}")
                
                # Method 2: Command Line (Fallback)
                if self.freecad_path and self.freecad_path not in ["python_api_only"]:
                    logger.info("🔄 Falling back to command line method for CATPART...")
                    try:
                        result = self._convert_with_freecad(input_path, output_path, file_ext)
                        if result["success"]:
                            result["method_used"] = "command_line"
                            result["conversion_needed"] = True
                            result["input_format"] = file_ext
                            result["output_format"] = ".step"
                            print(f"[CAD-CONVERT] ✅ Command line conversion successful")
                            return result
                    except Exception as e:
                        logger.warning(f"⚠️ Command line method failed: {str(e)}")
            
            # Tüm methodlar başarısız
            return {
                "success": False,
                "error": "All conversion methods failed. FreeCAD may not be properly installed or the format is not supported.",
                "methods_tried": ["python_api" if self.python_api_available else None, 
                                "command_line" if self.freecad_path else None],
                "freecad_available": bool(self.freecad_path),
                "python_api_available": self.python_api_available,
                "input_path": input_path,
                "intended_output_path": output_path
            }
                
        except Exception as e:
            logger.error(f"❌ CAD conversion error: {str(e)}")
            import traceback
            print(f"[CAD-CONVERT] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Conversion failed: {str(e)}",
                "input_path": input_path,
                "intended_output_path": output_path
            }

    def _convert_catpart_with_python_api(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """CATPART dosyasını Python API ile çevir"""
        try:
            start_time = time.time()
            
            import FreeCAD
            import Import
            import Part
            
            # Yeni doküman oluştur
            doc_name = f"CatpartConv_{uuid.uuid4().hex[:8]}"
            doc = FreeCAD.newDocument(doc_name)
            
            try:
                # CATPART dosyasını import et
                Import.insert(input_path, doc.Name)
                
                # Dokümanı yenile
                doc.recompute()
                
                # Objeleri kontrol et
                objects = doc.Objects
                if not objects:
                    return {
                        "success": False,
                        "error": "No objects found in CATPART file"
                    }
                
                # Valid shapes topla
                shapes = []
                for obj in objects:
                    if hasattr(obj, 'Shape') and obj.Shape and obj.Shape.isValid():
                        shapes.append(obj.Shape)
                
                if not shapes:
                    return {
                        "success": False,
                        "error": "No valid shapes found in CATPART file"
                    }
                
                # Compound oluştur ve export et
                if len(shapes) == 1:
                    compound = shapes[0]
                else:
                    compound = Part.makeCompound(shapes)
                
                compound.exportStep(output_path)
                
                processing_time = time.time() - start_time
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                    return {
                        "success": True,
                        "processing_time": processing_time,
                        "objects_count": len(objects),
                        "shapes_count": len(shapes),
                        "output_path": output_path,
                        "message": "Successfully converted CATPART to STEP"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Export file not created or too small"
                    }
                    
            finally:
                FreeCAD.closeDocument(doc.Name)
                
        except Exception as e:
            return {
                "success": False,
                "error": f"CATPART conversion failed: {str(e)}"
            }

    def _convert_with_freecad(self, input_path: str, output_path: str, input_format: str) -> Dict[str, Any]:
        """FreeCAD command line kullanarak çeviri"""
        try:
            start_time = time.time()
            
            # FreeCAD script oluştur
            script_content = self._create_freecad_script(input_path, output_path, input_format)
            
            # Script dosyasını kaydet
            script_path = os.path.join(self.temp_dir, f"convert_script_{uuid.uuid4().hex[:8]}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            try:
                # FreeCAD'i çalıştır
                cmd = [self.freecad_path, "-c", script_path]
                
                logger.info(f"🔧 Running FreeCAD conversion: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.temp_dir,
                    env=os.environ.copy()
                )
                
                processing_time = time.time() - start_time
                
                if result.returncode == 0:
                    logger.info(f"✅ FreeCAD command line conversion successful")
                    return {
                        "success": True,
                        "processing_time": processing_time,
                        "stdout": result.stdout,
                        "output_path": output_path,
                        "message": "FreeCAD conversion successful"
                    }
                else:
                    logger.error(f"❌ FreeCAD conversion failed: {result.stderr}")
                    return {
                        "success": False,
                        "error": f"FreeCAD conversion failed: {result.stderr}",
                        "stdout": result.stdout,
                        "processing_time": processing_time
                    }
                    
            finally:
                # Script dosyasını temizle
                try:
                    os.remove(script_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("❌ FreeCAD conversion timeout")
            return {
                "success": False,
                "error": "FreeCAD conversion timeout (120 seconds)"
            }
        except Exception as e:
            logger.error(f"❌ FreeCAD execution error: {str(e)}")
            return {
                "success": False,
                "error": f"FreeCAD execution error: {str(e)}"
            }
    
    def _create_freecad_script(self, input_path: str, output_path: str, input_format: str) -> str:
        """FreeCAD conversion script - SIMPLIFIED FOR PRT"""
        script_template = f'''
import FreeCAD
import Part
import sys

try:
    print("[SCRIPT] Starting conversion...")
    print("[SCRIPT] Input: {input_path}")
    print("[SCRIPT] Output: {output_path}")
    print("[SCRIPT] Format: {input_format}")
    
    # For PRT files, use Part.read directly
    if "{input_format}".lower() == ".prt":
        try:
            shape = Part.read("{input_path}")
            if shape and shape.isValid():
                shape.exportStep("{output_path}")
                print("[SCRIPT] PRT conversion successful")
                sys.exit(0)
            else:
                print("[SCRIPT] Invalid shape from PRT file")
                sys.exit(1)
        except Exception as e:
            print(f"[SCRIPT] PRT conversion error: {{e}}")
            sys.exit(1)
    
    # For other formats, use Import
    else:
        import Import
        doc = FreeCAD.newDocument("ConversionDoc")
        Import.insert("{input_path}", doc.Name)
        doc.recompute()
        
        objects = doc.Objects
        if len(objects) == 0:
            print("[SCRIPT] No objects found")
            sys.exit(1)
        
        shapes = []
        for obj in objects:
            if hasattr(obj, 'Shape') and obj.Shape and obj.Shape.isValid():
                shapes.append(obj.Shape)
        
        if not shapes:
            print("[SCRIPT] No valid shapes found")
            sys.exit(1)
        
        if len(shapes) == 1:
            compound = shapes[0]
        else:
            compound = Part.makeCompound(shapes)
        
        compound.exportStep("{output_path}")
        FreeCAD.closeDocument(doc.Name)
        print("[SCRIPT] Conversion successful")
        sys.exit(0)
        
except Exception as e:
    print(f"[SCRIPT] Error: {{e}}")
    sys.exit(1)
'''
        return script_template

    def convert_to_step_with_save(self, input_path: str, 
                                 custom_output_name: str = None,
                                 save_original: bool = True) -> Dict[str, Any]:
        """
        CAD dosyasını STEP'e çevirir ve fiziksel olarak kaydeder
        """
        try:
            print(f"[CAD-CONVERT-SAVE] 🔧 Starting convert_to_step_with_save")
            print(f"[CAD-CONVERT-SAVE] 📂 Input: {input_path}")
            print(f"[CAD-CONVERT-SAVE] 📋 Input exists: {os.path.exists(input_path)}")
            
            if not os.path.exists(input_path):
                return {
                    "success": False,
                    "error": f"Input file not found: {input_path}"
                }
            
            file_path = Path(input_path)
            file_ext = file_path.suffix.lower()
            base_name = file_path.stem
            
            print(f"[CAD-CONVERT-SAVE] 📋 File extension: {file_ext}")
            print(f"[CAD-CONVERT-SAVE] 📋 Base name: {base_name}")
            
            # Çıkış dosya adını belirle
            if custom_output_name:
                output_filename = f"{custom_output_name}.step"
            else:
                timestamp = datetime.now().strftime("%H%M%S")
                output_filename = f"{base_name}_{timestamp}.step"
            
            # Final output path oluştur
            final_output_path = os.path.join(self.step_files_dir, output_filename)
            
            print(f"[CAD-CONVERT-SAVE] 📁 Final output: {final_output_path}")
            print(f"[CAD-CONVERT-SAVE] 📁 Output dir exists: {os.path.exists(self.step_files_dir)}")
            
            # Output directory'nin var olduğundan emin ol
            os.makedirs(self.step_files_dir, exist_ok=True)
            os.makedirs(self.original_files_dir, exist_ok=True)
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Çevirme işlemi
            if self.needs_conversion(input_path):
                logger.info(f"🔄 Converting {file_ext} to STEP: {file_path.name}")
                
                # Geçici çıkış dosyası - temp directory'nin var olduğundan emin ol
                os.makedirs(self.temp_dir, exist_ok=True)
                temp_output = os.path.join(self.temp_dir, f"temp_{uuid.uuid4().hex[:8]}.step")
                
                print(f"[CAD-CONVERT-SAVE] 🔧 Temp output: {temp_output}")
                print(f"[CAD-CONVERT-SAVE] 📁 Temp dir exists: {os.path.exists(self.temp_dir)}")
                
                # Çevirme işlemini yap
                conversion_result = self.convert_to_step(input_path, temp_output)
                
                print(f"[CAD-CONVERT-SAVE] 📊 Conversion result: {conversion_result.get('success', False)}")
                
                if not conversion_result["success"]:
                    print(f"[CAD-CONVERT-SAVE] ❌ Conversion failed: {conversion_result.get('error')}")
                    # Add detailed format info to the result
                    conversion_result["input_path"] = input_path
                    conversion_result["original_filename"] = file_path.name
                    return conversion_result
                
                # Check if temp file exists
                if os.path.exists(temp_output):
                    # Başarılı çevirme - fiziksel dosyayı final konuma taşı
                    try:
                        shutil.move(temp_output, final_output_path)
                        print(f"[CAD-CONVERT-SAVE] 💾 STEP file moved: {temp_output} -> {final_output_path}")
                    except Exception as move_error:
                        print(f"[CAD-CONVERT-SAVE] ❌ File move failed: {move_error}")
                        # Fallback: copy
                        try:
                            shutil.copy2(temp_output, final_output_path)
                            os.remove(temp_output)
                            print(f"[CAD-CONVERT-SAVE] 💾 STEP file copied: {final_output_path}")
                        except Exception as copy_error:
                            return {
                                "success": False,
                                "error": f"Failed to move/copy temp file: {copy_error}",
                                "temp_file": temp_output,
                                "final_path": final_output_path
                            }
                else:
                    print(f"[CAD-CONVERT-SAVE] ❌ Temp STEP file not created: {temp_output}")
                    return {
                        "success": False,
                        "error": f"Temp STEP file not created: {temp_output}",
                        "conversion_result": conversion_result
                    }
                
            else:
                # Zaten STEP formatında - direkt kopyala
                if file_ext in ['.step', '.stp']:
                    shutil.copy2(input_path, final_output_path)
                    logger.info(f"📋 STEP file copied: {final_output_path}")
                    conversion_result = {
                        "success": True,
                        "conversion_needed": False,
                        "message": "File was already in STEP format"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported file format: {file_ext}"
                    }
            
            # Final dosyanın var olduğunu kontrol et
            if not os.path.exists(final_output_path):
                return {
                    "success": False,
                    "error": f"Final STEP file not created: {final_output_path}",
                    "conversion_result": conversion_result
                }
            
            # Orijinal dosyayı da kaydet
            original_saved_path = None
            if save_original:
                original_filename = f"{base_name}_original{file_ext}"
                original_saved_path = os.path.join(self.original_files_dir, original_filename)
                try:
                    shutil.copy2(input_path, original_saved_path)
                    logger.info(f"📁 Original file saved: {original_saved_path}")
                except Exception as orig_error:
                    print(f"[CAD-CONVERT-SAVE] ⚠️ Original file save failed: {orig_error}")
                    original_saved_path = None
            
            # Log dosyası oluştur
            log_file = self._create_conversion_log(input_path, final_output_path, 
                                                  conversion_result, original_saved_path)
            
            # Dosya boyutlarını kontrol et
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(final_output_path) if os.path.exists(final_output_path) else 0
            
            result = {
                "success": True,
                "input_path": input_path,
                "output_path": final_output_path,
                "original_saved_path": original_saved_path,
                "log_file": log_file,
                "input_format": file_ext,
                "output_format": ".step",
                "input_size_bytes": input_size,
                "output_size_bytes": output_size,
                "conversion_needed": conversion_result.get("conversion_needed", True),
                "processing_time": conversion_result.get("processing_time", 0),
                "method_used": conversion_result.get("method_used", "direct_copy"),
                "objects_count": conversion_result.get("objects_count", 1),
                "shapes_count": conversion_result.get("shapes_count", 1),
                "message": f"Successfully converted and saved {file_path.name} to {output_filename}"
            }
            
            logger.info(f"✅ Conversion and save completed: {output_filename}")
            print(f"[CAD-CONVERT-SAVE] ✅ SUCCESS: {final_output_path} ({output_size} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Convert and save error: {str(e)}")
            import traceback
            print(f"[CAD-CONVERT-SAVE] ❌ Exception: {str(e)}")
            print(f"[CAD-CONVERT-SAVE] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Convert and save failed: {str(e)}",
                "input_path": input_path,
                "traceback": traceback.format_exc()
            }
    
    def _create_conversion_log(self, input_path: str, output_path: str, 
                              conversion_result: Dict, original_path: str = None) -> str:
        """Çevirme işlemi için log dosyası oluşturur"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_name = Path(input_path).name
            log_filename = f"conversion_{input_name}_{timestamp}.log"
            log_path = os.path.join(self.log_dir, log_filename)
            
            log_content = f"""
=== CAD CONVERSION LOG ===
Timestamp: {datetime.now().isoformat()}
Input File: {input_path}
Input Size: {os.path.getsize(input_path)} bytes
Output File: {output_path}
Output Size: {os.path.getsize(output_path) if os.path.exists(output_path) else 0} bytes
Original Saved: {original_path if original_path else 'No'}

Conversion Details:
{'-' * 30}
Success: {conversion_result.get('success', False)}
Method Used: {conversion_result.get('method_used', 'Unknown')}
Processing Time: {conversion_result.get('processing_time', 0):.2f} seconds
Conversion Needed: {conversion_result.get('conversion_needed', True)}
Objects Count: {conversion_result.get('objects_count', 'N/A')}
Shapes Count: {conversion_result.get('shapes_count', 'N/A')}

Message: {conversion_result.get('message', 'No message')}

Environment Info:
{'-' * 30}
FreeCAD Available: {bool(self.freecad_path)}
Python API Available: {self.python_api_available}
Output Base Dir: {self.output_base_dir}
Temp Dir: {self.temp_dir}

Status: COMPLETED SUCCESSFULLY
=== END LOG ===
"""
            
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return log_path
            
        except Exception as e:
            logger.error(f"❌ Log creation error: {str(e)}")
            return None
    
    def batch_convert_with_save(self, file_paths: list, custom_prefix: str = None) -> Dict[str, Any]:
        """Birden fazla dosyayı toplu olarak çevirir ve kaydeder"""
        results = []
        
        logger.info(f"🔄 Starting batch conversion with save of {len(file_paths)} files")
        
        for i, file_path in enumerate(file_paths):
            logger.info(f"📁 Processing file {i+1}/{len(file_paths)}: {Path(file_path).name}")
            
            # Özel isim belirle
            custom_name = None
            if custom_prefix:
                custom_name = f"{custom_prefix}_{i+1:03d}"
            
            result = self.convert_to_step_with_save(
                file_path, 
                custom_output_name=custom_name,
                save_original=True
            )
            
            results.append({
                "input_path": file_path,
                "result": result
            })
        
        successful = len([r for r in results if r["result"]["success"]])
        
        logger.info(f"✅ Batch conversion completed: {successful}/{len(file_paths)} successful")
        
        return {
            "success": successful > 0,
            "total_files": len(file_paths),
            "successful_conversions": successful,
            "failed_conversions": len(file_paths) - successful,
            "output_directory": self.step_files_dir,
            "original_files_directory": self.original_files_dir,
            "log_directory": self.log_dir,
            "results": results
        }
    
    def get_output_directory_info(self) -> Dict[str, Any]:
        """Çıkış dizini hakkında bilgi verir"""
        try:
            step_files = list(Path(self.step_files_dir).glob("*.step"))
            original_files = list(Path(self.original_files_dir).glob("*"))
            log_files = list(Path(self.log_dir).glob("*.log"))
            
            return {
                "base_output_dir": self.output_base_dir,
                "daily_output_dir": self.daily_output_dir,
                "step_files_dir": self.step_files_dir,
                "original_files_dir": self.original_files_dir,
                "log_dir": self.log_dir,
                "step_files_count": len(step_files),
                "original_files_count": len(original_files),
                "log_files_count": len(log_files),
                "step_files": [str(f) for f in step_files],
                "original_files": [str(f) for f in original_files],
                "log_files": [str(f) for f in log_files]
            }
        except Exception as e:
            return {
                "error": f"Failed to get directory info: {str(e)}"
            }
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Eski geçici dosyaları temizler"""
        try:
            current_time = time.time()
            removed_count = 0
            
            for file_path in Path(self.temp_dir).glob("*"):
                if file_path.is_file():
                    file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                    if file_age_hours > max_age_hours:
                        file_path.unlink()
                        removed_count += 1
            
            logger.info(f"🗑️ Cleaned up {removed_count} old temporary files")
            return removed_count
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {str(e)}")
            return 0
    
    def get_status(self) -> Dict[str, Any]:
        """Converter durumunu döndürür"""
        return {
            "conversion_ready": bool(self.freecad_path or self.python_api_available),
            "freecad_available": bool(self.freecad_path),
            "python_api_available": self.python_api_available,
            "supported_formats": self.supported_formats,
            "output_directory": self.output_base_dir,
            "temp_directory": self.temp_dir
        }

# Utility functions
def get_file_type_enhanced(filename: str) -> str:
    """Enhanced file type detection"""
    if '.' in filename:
        extension = filename.rsplit('.', 1)[1].lower()
        
        type_mapping = {
            'pdf': 'pdf',
            'doc': 'document', 
            'docx': 'document',
            'step': 'step',
            'stp': 'step',
            'prt': 'cad_part',
            'catpart': 'cad_part'
        }
        
        return type_mapping.get(extension, 'unknown')
    
    return 'unknown'

def is_cad_file(filename: str) -> bool:
    """CAD dosyası kontrolü"""
    file_type = get_file_type_enhanced(filename)
    return file_type in ['step', 'cad_part']

def needs_step_conversion(filename: str) -> bool:
    """STEP çevirme gereksinimi kontrolü"""
    if '.' in filename:
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in ['prt', 'catpart']
    return False

# Global converter instance with custom output directory
cad_converter = CADConverterService(output_base_dir="./cad_conversions")

# Enhanced test function
def test_physical_conversion():
    """Fiziksel kaydetme ile çevirmeyi test eder"""
    print("🔧 CAD Converter Test - Physical File Saving")
    print("=" * 60)
    
    # Status bilgileri
    status = cad_converter.get_status()
    print(f"Conversion Ready: {status['conversion_ready']}")
    print(f"Supported Formats: {list(status['supported_formats'].keys())}")
    
    # Directory info
    dir_info = cad_converter.get_output_directory_info()
    print(f"\n📁 Output Directories:")
    print(f"  Base Dir: {dir_info['base_output_dir']}")
    print(f"  Daily Dir: {dir_info['daily_output_dir']}")
    print(f"  STEP Files: {dir_info['step_files_dir']}")
    print(f"  Original Files: {dir_info['original_files_dir']}")
    print(f"  Logs: {dir_info['log_dir']}")
    
    print(f"\n📊 Current Files:")
    print(f"  STEP files: {dir_info['step_files_count']}")
    print(f"  Original files: {dir_info['original_files_count']}")
    print(f"  Log files: {dir_info['log_files_count']}")

if __name__ == "__main__":
    test_physical_conversion()