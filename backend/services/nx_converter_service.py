# nx_converter_service.py - NX/Unigraphics PRT to STEP converter

import os
import subprocess
import tempfile
import uuid
from typing import Dict, Any, Optional

class NXConverterService:
    """
    NX/Unigraphics PRT dosyalarını STEP'e dönüştürmek için özel servis
    """
    
    def __init__(self):
        self.conversion_methods = []
        self._check_available_methods()
    
    def _check_available_methods(self):
        """Kullanılabilir dönüştürme metodlarını kontrol et"""
        
        # Method 1: Check for NX installation
        nx_paths = [
            "C:\\Program Files\\Siemens\\NX\\UGII\\ugraf.exe",
            "C:\\Program Files\\Siemens\\NX 12.0\\UGII\\ugraf.exe",
            "/opt/siemens/nx/ugii/ugraf",
            "/usr/local/nx/ugii/ugraf"
        ]
        
        for path in nx_paths:
            if os.path.exists(path):
                self.conversion_methods.append(("nx_native", path))
                break
        
        # Method 2: Check for specialized converters
        converters = {
            "nxconvert": ["nxconvert", "--help"],
            "ug_convert": ["ug_convert", "-h"],
            "datakit": ["datakit_nx2step", "--version"]
        }
        
        for name, cmd in converters.items():
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                if result.returncode in [0, 1]:  # Success or help shown
                    self.conversion_methods.append((name, cmd[0]))
            except:
                pass
    
    def convert_nx_to_step_external(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        External API veya servis kullanarak dönüştürme
        """
        # Bu bölüm ticari servislere bağlanabilir
        # Örnek: CADExchanger, HOOPS Exchange, etc.
        
        return {
            "success": False,
            "error": "External conversion service not configured",
            "recommendation": "Contact IT for NX file conversion setup"
        }
    
    def create_nx_macro_script(self, input_path: str, output_path: str) -> str:
        """
        NX için macro script oluştur
        """
        macro_content = f"""
' NX Journal Script for STEP Export
' Auto-generated for file conversion

Option Strict Off
Imports System
Imports NXOpen
Imports NXOpen.UF

Module NXJournal
    Sub Main()
        Dim theSession As Session = Session.GetSession()
        Dim workPart As Part = theSession.Parts.Work
        
        Try
            ' Open the PRT file
            Dim basePart1 As BasePart
            Dim partLoadStatus1 As PartLoadStatus
            basePart1 = theSession.Parts.OpenBaseDisplay("{input_path}", partLoadStatus1)
            partLoadStatus1.Dispose()
            
            ' Export to STEP
            Dim stepCreator1 As StepCreator
            stepCreator1 = theSession.DexManager.CreateStepCreator()
            
            stepCreator1.ExportAs = StepCreator.ExportAsOption.Ap214
            stepCreator1.ObjectTypes.Solids = True
            stepCreator1.ObjectTypes.Surfaces = True
            stepCreator1.ObjectTypes.Curves = True
            stepCreator1.OutputFile = "{output_path}"
            
            Dim nXObject1 As NXObject
            nXObject1 = stepCreator1.Commit()
            
            stepCreator1.Destroy()
            
            ' Close without saving
            workPart.Close(BasePart.CloseWholeTree.False, BasePart.CloseModified.UseResponses, Nothing)
            
        Catch ex As Exception
            Console.WriteLine("Error: " & ex.Message)
        End Try
    End Sub
End Module
"""
        return macro_content
    
    def get_conversion_instructions(self) -> Dict[str, Any]:
        """
        Kullanıcı için dönüştürme talimatları
        """
        return {
            "manual_conversion": {
                "NX_Native": [
                    "1. NX yazılımını açın",
                    "2. File → Open ile PRT dosyasını açın",
                    "3. File → Export → STEP seçin",
                    "4. Export Options'da:",
                    "   - Type: STEP 214 veya STEP 203",
                    "   - Export Solids: ✓",
                    "   - Export Surfaces: ✓",
                    "5. Export butonuna tıklayın"
                ],
                "Alternative_Tools": [
                    "• Siemens PLM Software tarafından sağlanan JT2Go (ücretsiz viewer)",
                    "• CADExchanger (ticari)",
                    "• HOOPS Exchange (ticari)",
                    "• Datakit CrossManager (ticari)"
                ]
            },
            "batch_conversion": {
                "description": "Çok sayıda dosya için toplu dönüştürme",
                "options": [
                    "NX Journal/Macro kullanımı",
                    "NX komut satırı arayüzü",
                    "Ticari dönüştürme servisleri"
                ]
            },
            "online_services": [
                {
                    "name": "CAD Exchanger Cloud",
                    "url": "https://cloud.cadexchanger.com",
                    "type": "Paid service"
                },
                {
                    "name": "ShareCAD",
                    "url": "https://www.sharecad.org",
                    "type": "Free viewer (no conversion)"
                }
            ]
        }
    
    def suggest_alternative_workflow(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alternatif iş akışı öner
        """
        suggestions = []
        
        # File size check
        file_size_mb = file_info.get('file_size', 0) / (1024 * 1024)
        
        if file_size_mb < 10:
            suggestions.append({
                "method": "email_conversion",
                "description": "Küçük dosyalar için email ile dönüştürme servisi",
                "steps": [
                    "PRT dosyasını IT departmanına email ile gönderin",
                    "Konu: PRT to STEP Conversion Request",
                    "24 saat içinde dönüştürülmüş dosyayı alacaksınız"
                ]
            })
        
        suggestions.append({
            "method": "cloud_storage",
            "description": "Bulut depolama üzerinden paylaşım",
            "steps": [
                "PRT dosyasını şirket bulut depolamasına yükleyin",
                "CAD departmanına dönüştürme talebi oluşturun",
                "Dönüştürülmüş STEP dosyası aynı konuma yüklenecek"
            ]
        })
        
        suggestions.append({
            "method": "direct_analysis",
            "description": "Dönüştürme olmadan analiz",
            "steps": [
                "Teknik çizim PDF'ini yükleyin",
                "Malzeme ve boyut bilgilerini manuel girin",
                "Sistem maliyet hesaplamasını yapacak"
            ]
        })
        
        return {
            "file_info": file_info,
            "conversion_not_available": True,
            "alternative_workflows": suggestions,
            "recommended": suggestions[0] if suggestions else None
        }

# Global instance
nx_converter = NXConverterService()

def get_nx_conversion_help(filename: str, file_size: int) -> Dict[str, Any]:
    """
    NX dosyası için yardım bilgileri
    """
    file_info = {
        "filename": filename,
        "file_size": file_size,
        "format": "NX/Unigraphics PRT"
    }
    
    return {
        "format_info": {
            "name": "NX/Unigraphics Part File",
            "extension": ".prt",
            "vendor": "Siemens PLM Software",
            "proprietary": True,
            "conversion_difficulty": "High"
        },
        "conversion_options": nx_converter.get_conversion_instructions(),
        "alternative_workflow": nx_converter.suggest_alternative_workflow(file_info),
        "support_contact": {
            "email": "cad-support@company.com",
            "phone": "Extension 1234",
            "hours": "Mon-Fri 9:00-17:00"
        }
    }