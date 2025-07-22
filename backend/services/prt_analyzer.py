# prt_analyzer.py - PRT dosya analiz aracı

import os
import struct

def analyze_prt_file(file_path):
    """PRT dosyasının türünü ve formatını analiz eder"""
    
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    
    file_size = os.path.getsize(file_path)
    
    analysis = {
        "file_path": file_path,
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "detected_format": "unknown",
        "confidence": 0,
        "header_info": {},
        "recommendations": []
    }
    
    try:
        with open(file_path, 'rb') as f:
            # İlk 1KB'ı oku
            header_data = f.read(1024)
            
            # Header'ı string olarak da kontrol et
            try:
                header_text = header_data.decode('utf-8', errors='ignore')
                header_text_upper = header_text.upper()
            except:
                header_text = ""
                header_text_upper = ""
            
            # Binary header (ilk 100 byte)
            header_hex = header_data[:100].hex()
            
            analysis["header_info"]["first_100_bytes_hex"] = header_hex
            analysis["header_info"]["first_20_bytes"] = header_data[:20]
            
            # Format tespiti
            
            # 1. NX/Unigraphics PRT
            if b'UNIGRAPHICS' in header_data or b'NX' in header_data:
                analysis["detected_format"] = "NX/Unigraphics"
                analysis["confidence"] = 90
                analysis["recommendations"].append("Use NX software for best compatibility")
                
            # 2. Pro/ENGINEER veya Creo
            elif header_data.startswith(b'#UGC') or b'#Creo' in header_data:
                analysis["detected_format"] = "Creo/Pro-E"
                analysis["confidence"] = 85
                analysis["recommendations"].append("Use Creo software for conversion")
                
            # 3. CATIA V5 Part (bazen .prt uzantılı olabilir)
            elif header_data.startswith(b'V5_CFG') or b'CATIA' in header_data:
                analysis["detected_format"] = "CATIA V5"
                analysis["confidence"] = 80
                analysis["recommendations"].append("Try renaming to .CATPart and retry")
                
            # 4. SolidWorks Part (bazen .prt uzantılı)
            elif header_data[:4] == b'\xd0\xcf\x11\xe0':  # OLE header
                analysis["detected_format"] = "Possibly SolidWorks"
                analysis["confidence"] = 60
                analysis["recommendations"].append("Check if it's a SolidWorks file")
                
            # 5. Parasolid
            elif b'**PARA' in header_data or b'PARASOLID' in header_text_upper:
                analysis["detected_format"] = "Parasolid"
                analysis["confidence"] = 85
                analysis["recommendations"].append("FreeCAD may support this with proper plugin")
                
            # 6. STEP in disguise
            elif 'ISO-10303' in header_text_upper or 'STEP' in header_text_upper:
                analysis["detected_format"] = "STEP (wrong extension)"
                analysis["confidence"] = 95
                analysis["recommendations"].append("Rename to .step and retry")
                
            # 7. IGES in disguise
            elif header_text.startswith('                                                                        S      1'):
                analysis["detected_format"] = "IGES (wrong extension)"
                analysis["confidence"] = 90
                analysis["recommendations"].append("Rename to .iges and retry")
                
            # 8. Binary STL
            elif len(header_data) >= 84:
                # STL binary format check
                try:
                    # Skip 80 byte header, read triangle count
                    f.seek(80)
                    triangle_count = struct.unpack('<I', f.read(4))[0]
                    expected_size = 80 + 4 + (triangle_count * 50)
                    if abs(file_size - expected_size) < 100:
                        analysis["detected_format"] = "Binary STL (wrong extension)"
                        analysis["confidence"] = 80
                        analysis["recommendations"].append("Rename to .stl and use as mesh")
                except:
                    pass
            
            # Text-based format detection
            if analysis["detected_format"] == "unknown" and header_text:
                # Look for text patterns
                if "SOLID" in header_text_upper and "ENDSOLID" in header_text_upper:
                    analysis["detected_format"] = "ASCII STL (wrong extension)"
                    analysis["confidence"] = 75
                    analysis["recommendations"].append("Rename to .stl")
                    
                elif any(word in header_text_upper for word in ["MCAD", "MASTERCAM", "POWERMILL"]):
                    analysis["detected_format"] = "CAM Software Output"
                    analysis["confidence"] = 50
                    analysis["recommendations"].append("May need specialized converter")
            
            # Additional checks
            if analysis["detected_format"] == "unknown":
                # Check if it's a text file
                try:
                    text_content = header_data.decode('ascii')
                    if len(text_content) > len(header_data) * 0.8:  # Mostly ASCII
                        analysis["detected_format"] = "Text-based format"
                        analysis["confidence"] = 40
                        analysis["recommendations"].append("Check if it's a human-readable CAD format")
                except:
                    analysis["detected_format"] = "Binary format (unknown type)"
                    analysis["confidence"] = 30
                    analysis["recommendations"].append("Binary format - need to identify source CAD system")
            
            # Sample content for debugging
            analysis["header_info"]["readable_preview"] = header_text[:200].replace('\x00', '').strip()
            
            # Magic number info
            magic_numbers = {
                "first_4_bytes": header_data[:4].hex(),
                "bytes_4_8": header_data[4:8].hex(),
                "bytes_8_12": header_data[8:12].hex()
            }
            analysis["header_info"]["magic_numbers"] = magic_numbers
            
    except Exception as e:
        analysis["error"] = f"Analysis error: {str(e)}"
    
    # General recommendations
    if analysis["confidence"] < 70:
        analysis["recommendations"].append("Consider asking for the original CAD software information")
        analysis["recommendations"].append("Request STEP or IGES export from source")
    
    return analysis

# Test function
def test_prt_analysis(file_path):
    """Test PRT dosya analizi"""
    print("=" * 60)
    print(f"PRT FILE ANALYSIS: {file_path}")
    print("=" * 60)
    
    result = analyze_prt_file(file_path)
    
    print(f"File Size: {result['file_size_mb']} MB")
    print(f"Detected Format: {result['detected_format']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"\nHeader Info:")
    for key, value in result['header_info'].items():
        if key == 'readable_preview' and value:
            print(f"  {key}: {value[:100]}...")
        elif key != 'first_100_bytes_hex':
            print(f"  {key}: {value}")
    
    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  • {rec}")
    
    return result

if __name__ == "__main__":
    # Test with a sample file
    import sys
    if len(sys.argv) > 1:
        test_prt_analysis(sys.argv[1])
    else:
        print("Usage: python prt_analyzer.py <prt_file_path>")