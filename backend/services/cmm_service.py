# backend/services/cmm_service.py
"""
CMM (Coordinate Measuring Machine) veri işleme servisi
RTF dosyalarından ölçüm verilerini parse eder ve Excel raporları oluşturur
"""

import os
import re
import json
import tempfile
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import traceback
import numpy as np

try:
    from striprtf.striprtf import rtf_to_text
    STRIPRTF_AVAILABLE = True
except ImportError:
    STRIPRTF_AVAILABLE = False
    print("⚠️ striprtf paketi yüklü değil. RTF desteği sınırlı olacak.")

@dataclass
class CMMOlcum:
    """CMM ölçüm verisi için data class"""
    operasyon: str
    sira_no: str  # String olarak sakla (10-18 formatı için)
    boyut_adi: str
    aciklama: str
    eksen: str
    nominal: float
    olculen: Any  # String veya float (min/max formatı için)
    pos_tolerans: Optional[float]
    neg_tolerans: Optional[float]
    sapma: float
    tolerans_disi: float
    bonus: Optional[float] = None
    durum: str = "✓"
    exclude_from_fai: bool = False  # FAI formunda gösterilmeyecek satırlar için

class CMMService:
    """CMM veri işleme servisi"""
    
    def __init__(self):
        self.parser = CMMParser()
        self.exporter = CMMExcelExporter()
    
    def process_files(self, file_paths: List[str], output_excel_path: str = None) -> Dict[str, Any]:
        """
        CMM dosyalarını işle ve Excel raporu oluştur
        
        Args:
            file_paths: İşlenecek RTF dosya yolları
            output_excel_path: Çıktı Excel dosya yolu (opsiyonel)
            
        Returns:
            İşlem sonucu dictionary
        """
        try:
            # Dosyaları parse et
            print(f"📄 CMM dosyaları işleniyor: {len(file_paths)} dosya")
            measurements = self.parser.parse_multiple_files(file_paths)
            
            if not measurements:
                return {
                    'success': False,
                    'error': 'Hiçbir ölçüm verisi bulunamadı',
                    'count': 0
                }
            
            # JSON'a dönüştür ve temizle
            cleaned_data = self._clean_and_prepare_data(measurements)
            
            # Operations listesini al
            operations = list(set(item['operasyon'] for item in cleaned_data))
            
            # Excel path oluştur
            if not output_excel_path:
                output_excel_path = self._generate_excel_filename(file_paths, operations)
            
            # Excel oluştur
            success = self.exporter.export_cleaned_data_to_excel(cleaned_data, output_excel_path)
            
            if success:
                return {
                    'success': True,
                    'count': len(cleaned_data),
                    'operations': operations,
                    'excel_path': output_excel_path,
                    'filename': os.path.basename(output_excel_path),
                    'summary': self._generate_summary(cleaned_data)
                }
            else:
                return {
                    'success': False,
                    'error': 'Excel dosyası oluşturulamadı',
                    'count': len(cleaned_data)
                }
                
        except Exception as e:
            print(f"❌ CMM işleme hatası: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    def _clean_and_prepare_data(self, measurements: List[CMMOlcum]) -> List[Dict]:
        """Ölçümleri temizle ve dictionary listesine dönüştür"""
        measurements_data = []
        
        for m in measurements:
            measurements_data.append({
                'operasyon': m.operasyon,
                'sira_no': m.sira_no,
                'boyut_adi': m.boyut_adi,
                'aciklama': m.aciklama,
                'eksen': m.eksen,
                'nominal': m.nominal,
                'olculen': m.olculen,
                'pos_tolerans': m.pos_tolerans,
                'neg_tolerans': m.neg_tolerans,
                'sapma': m.sapma,
                'tolerans_disi': m.tolerans_disi,
                'bonus': m.bonus,
                'durum': m.durum,
                'exclude_from_fai': m.exclude_from_fai
            })
        
        # Duplikatları kaldır
        seen = set()
        cleaned = []
        
        for item in measurements_data:
            key = (
                item['operasyon'],
                item['sira_no'], 
                item['boyut_adi'],
                item['aciklama'],
                item['eksen'],
                item['nominal'],
                str(item['olculen'])
            )
            
            if key not in seen:
                seen.add(key)
                cleaned.append(item)
        
        # Sırala
        def get_sort_key(item):
            sira_no_str = str(item['sira_no'])
            if '-' in sira_no_str:
                return int(sira_no_str.split('-')[0])
            else:
                return int(sira_no_str)
        
        cleaned.sort(key=get_sort_key)
        
        print(f"✅ Veri temizlendi: {len(measurements_data)} → {len(cleaned)} kayıt")
        
        return cleaned
    
    def _generate_excel_filename(self, file_paths: List[str], operations: List[str]) -> str:
        """Excel dosya adı oluştur"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_count = len(file_paths)
        ops_str = "_".join(sorted(operations)) if operations else "mixed"
        return f"cmm_raporu_{file_count}dosya_{ops_str}_{timestamp}.xlsx"
    
    def _generate_summary(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """Özet bilgileri oluştur"""
        # Operasyon bazlı istatistikler
        op_stats = {}
        for item in cleaned_data:
            op = item['operasyon']
            if op not in op_stats:
                op_stats[op] = 0
            op_stats[op] += 1
        
        # Durum istatistikleri
        successful = sum(1 for item in cleaned_data if item['durum'] == '✓')
        warnings = sum(1 for item in cleaned_data if item['durum'] == '⚠')
        
        # Benzersiz ölçüm numaraları
        unique_measurements = len(set(item['sira_no'] for item in cleaned_data))
        
        # FAI hariç tutulan sayısı
        fai_excluded = sum(1 for item in cleaned_data if item.get('exclude_from_fai', False))
        
        return {
            'total_measurements': len(cleaned_data),
            'successful_measurements': successful,
            'warning_measurements': warnings,
            'operation_breakdown': op_stats,
            'unique_measurement_numbers': unique_measurements,
            'fai_excluded_count': fai_excluded,
            'success_rate': round((successful / len(cleaned_data)) * 100, 2) if cleaned_data else 0
        }

class CMMParser:
    """CMM RTF dosyalarını parse eden sınıf"""
    
    def __init__(self):
        self.pattern_line = re.compile(
            r'\*+\s*(\d+)\s*\*+'  # Sıra numarası
        )
        self.pattern_dim = re.compile(
            r'DIM\s+(\w+)=\s*(.+?)\s+UNITS=MM'  # Boyut tanımı
        )
        self.pattern_data = re.compile(
            r'(\w+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
        )
    
    def extract_rtf_text(self, file_path: str) -> str:
        """RTF dosyasından metin çıkarır"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if STRIPRTF_AVAILABLE:
                return rtf_to_text(content)
            else:
                # Basit RTF temizleme (striprtf yoksa)
                # RTF kontrol kodlarını kaldır
                content = re.sub(r'\\[a-z]+\d*', '', content)
                content = re.sub(r'[{}]', '', content)
                return content
        except Exception as e:
            print(f"RTF okuma hatası: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Metni temizler ve normalize eder"""
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        # Özel karakterleri temizle
        text = text.replace('\x00', '').replace('\r', '\n')
        return text.strip()
    
    def parse_file(self, file_path: str) -> List[CMMOlcum]:
        """Tek bir CMM dosyasını parse eder"""
        measurements = []
        
        # Dosya adından operasyon belirle - daha esnek yaklaşım
        filename = Path(file_path).stem
        operasyon = self._detect_operation(filename)
        
        print(f"DEBUG: İşlenen dosya: {filename}, Operasyon: {operasyon}")
        
        # RTF text'i çıkar
        text = self.extract_rtf_text(file_path)
        if not text:
            return measurements
        
        # Sıra numaralarını bul - üç farklı pattern ile
        sira_matches = self._find_measurement_numbers(text)
        
        print(f"DEBUG: Toplam eşleşme sayısı: {len(sira_matches)}")
        
        # Her sıra numarası için bloğu çıkar
        for i, match in enumerate(sira_matches):
            sira_no_str = self._process_measurement_number(match.group(1).strip())
            
            print(f"DEBUG: Raw: '{match.group(1).strip()}' → Processed: '{sira_no_str}'")
            
            # Blok başlangıcı
            start_pos = match.end()
            
            # Blok bitişi (bir sonraki sıra numarası veya dosya sonu)
            if i + 1 < len(sira_matches):
                end_pos = sira_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            # Blok metnini çıkar
            block_text = text[start_pos:end_pos].strip()
            
            if block_text:
                print(f"DEBUG: ======== Sıra {sira_no_str} İŞLENİYOR ========")
                print(f"DEBUG: Blok uzunluğu: {len(block_text)} karakter")
                
                block_measurements = self.parse_measurement_block_simple(block_text, operasyon, sira_no_str)
                measurements.extend(block_measurements)
                
                print(f"DEBUG: ======== Sıra {sira_no_str} TAMAMLANDI ========")
                print(f"DEBUG: Bu bloktan {len(block_measurements)} ölçüm eklendi")
                print(f"DEBUG: Toplam ölçüm sayısı: {len(measurements)}")
                print()
        
        print(f"DEBUG: Toplam ölçüm sayısı: {len(measurements)}")
        return measurements
    
    def _detect_operation(self, filename: str) -> str:
        """Dosya adından operasyon tespit et"""
        filename_upper = filename.upper()
        
        # Önce standart formatları kontrol et
        if '1OP' in filename_upper:
            return '1OP'
        elif '2OP' in filename_upper:
            return '2OP'
        elif '3OP' in filename_upper:
            return '3OP'
        else:
            # Varsayılan olarak 1OP ata
            print(f"DEBUG: Dosya adında operasyon bulunamadı, varsayılan '1OP' atandı")
            return '1OP'
    
    def _find_measurement_numbers(self, text: str) -> List[re.Match]:
        """Metinde ölçüm numaralarını bul"""
        # Üç farklı regex pattern dene - TAM KAPSAMLI
        patterns = [
            r'\*+\s+([0-9]+(?:-[A-Za-z0-9\s]+)?)\s+\*+',  # Boşluklu format "**** 15 ****"
            r'\*+([0-9]+(?:-[A-Za-z0-9\s]+)?)\*+',        # Boşluksuz format "*****17-PART*****"
            r'\*+\s*([0-9]+)\s*\*+'                        # Tam esnek format
        ]
        
        all_matches = []
        seen_positions = set()
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.start() not in seen_positions:
                    all_matches.append(match)
                    seen_positions.add(match.start())
        
        # Pozisyona göre sırala
        return sorted(all_matches, key=lambda x: x.start())
    
    def _process_measurement_number(self, sira_no_raw: str) -> str:
        """Sıra numarasını işle"""
        # Sıra numarasını işle: sayı-metin ise sadece sayıyı al, sayı-sayı ise olduğu gibi bırak
        if '-' in sira_no_raw:
            parts = sira_no_raw.split('-', 1)  # Sadece ilk tire'de böl
            first_part = parts[0].strip()
            second_part = parts[1].strip()
            
            # İkinci kısım sayı mı kontrol et
            try:
                int(second_part)
                # İkinci kısım da sayı, aralık formatı (10-18)
                return sira_no_raw.replace(' ', '')  # Boşlukları kaldır
            except ValueError:
                # İkinci kısım metin, sadece ilk kısmı al (16-WEB SURFACE → 16)
                return first_part
        else:
            # Tire yok, normal sayı
            return sira_no_raw
    
    def parse_measurement_block_simple(self, block: str, operasyon: str, sira_no_str: str) -> List[CMMOlcum]:
        """Basitleştirilmiş blok parser - SURFACE profil birleştirme ile"""
        measurements = []
        lines = block.split('\n')
        
        current_dim = None
        current_desc = None
        surface_profiles = []  # SURFACE profil ölçümlerini topla
        has_surface = False  # Bu blokta SURFACE var mı kontrol et
        position_measurements = []  # POSITION ölçümlerini topla
        
        print(f"DEBUG: Blok işleniyor, sıra: {sira_no_str}")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # DIM tanımını yakala
            dim_match = re.search(r'DIM\s+(\w+)=\s*(.+?)\s+UNITS=MM', line)
            if dim_match:
                current_dim = dim_match.group(1)
                current_desc = dim_match.group(2).strip()
                print(f"DEBUG: DIM bulundu: {current_dim} - {current_desc}")
                
                # SURFACE profili mi kontrol et
                if 'SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper():
                    has_surface = True
                    print(f"DEBUG: SURFACE profili tespit edildi!")
                
                # POSITION ölçümü mü kontrol et
                if 'POSITION' in current_desc.upper():
                    # Yeni bir position grubu başlıyor, öncekini kaydet
                    if position_measurements:
                        self._process_position_group(position_measurements, measurements)
                        position_measurements = []
                
                continue
            
            # Veri satırları - Y, Z, X, A eksenlerini de dahil et
            if re.match(r'^[DRMTPZYXAF]+\s+', line):
                print(f"DEBUG: Veri satırı yakalandı: {line[:50]}...")
                
                # POSITION ölçümleri için özel işlem
                if current_desc and 'POSITION' in current_desc.upper():
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        position_measurements.append(measurement)
                        print(f"DEBUG: POSITION ölçümü toplandı: {measurement.eksen}")
                # SURFACE profil ölçümleri için özel işlem
                elif current_desc and ('SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper()):
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        surface_profiles.append(measurement)
                        print(f"DEBUG: SURFACE profil ölçümü toplandı: {measurement.boyut_adi}")
                else:
                    # Normal ölçümler
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        measurements.append(measurement)
                        print(f"DEBUG: Normal ölçüm eklendi: {measurement.boyut_adi}")
        
        # Son position grubunu işle
        if position_measurements:
            self._process_position_group(position_measurements, measurements)
        
        # SURFACE profil ölçümlerini birleştir - sadece gerçek SURFACE bloğunda
        if surface_profiles and has_surface:
            # Sadece M eksenli SURFACE profilleri birleştir
            m_surface_profiles = [p for p in surface_profiles if p.eksen == 'M']
            other_profiles = [p for p in surface_profiles if p.eksen != 'M']
            
            if m_surface_profiles:
                combined_measurement = self._combine_surface_profiles(m_surface_profiles, sira_no_str, operasyon)
                if combined_measurement:
                    measurements.append(combined_measurement)
                    print(f"DEBUG: {len(m_surface_profiles)} M eksenli SURFACE profil ölçümü birleştirildi - Sıra: {sira_no_str}")
            
            # M ekseni olmayan profilleri ayrı ekle
            if other_profiles:
                measurements.extend(other_profiles)
                print(f"DEBUG: {len(other_profiles)} non-M SURFACE profili ayrı eklendi")
        elif surface_profiles:
            # Eğer surface_profiles var ama has_surface False ise, normal olarak ekle
            measurements.extend(surface_profiles)
            print(f"DEBUG: SURFACE profilleri normal olarak eklendi")
        
        print(f"DEBUG: Blok tamamlandı, Sıra: {sira_no_str}, Toplam ölçüm: {len(measurements)}")
        return measurements
    
    def _process_position_group(self, position_measurements: List[CMMOlcum], measurements: List[CMMOlcum]):
        """POSITION ölçüm grubunu işle - sadece DF ve TP satırlarını ekle"""
        # X, Y, Z koordinat satırlarını FAI'dan hariç tut
        for m in position_measurements:
            if m.eksen in ['X', 'Y', 'Z']:
                m.exclude_from_fai = True
            measurements.append(m)
        
        print(f"DEBUG: POSITION grubu işlendi, {len(position_measurements)} ölçüm ({sum(1 for m in position_measurements if m.exclude_from_fai)} tanesi FAI'dan hariç)")
    
    def _combine_surface_profiles(self, profiles: List[CMMOlcum], sira_no_str: str, operasyon: str) -> Optional[CMMOlcum]:
        """Birden fazla SURFACE profil ölçümünü birleştirir"""
        if not profiles:
            return None
        
        # Tüm ölçülen değerleri topla
        measured_values = [float(p.olculen) for p in profiles]
        min_val = min(measured_values)
        max_val = max(measured_values)
        
        print(f"DEBUG: SURFACE profil değerleri: {measured_values}")
        print(f"DEBUG: Min: {min_val}, Max: {max_val}")
        
        # Min/Max formatında sonuç oluştur - YUVARLAMA YOK!
        if abs(min_val - max_val) < 0.001:  # Aynı değerler
            combined_result = str(min_val).rstrip('0').rstrip('.')
        else:
            min_str = str(min_val).rstrip('0').rstrip('.')
            max_str = str(max_val).rstrip('0').rstrip('.')
            combined_result = f"{min_str} / {max_str}"
        
        print(f"DEBUG: Birleştirilmiş sonuç: {combined_result}")
        
        # İlk profili temel alarak birleştirilmiş ölçüm oluştur
        base_profile = profiles[0]
        
        return CMMOlcum(
            operasyon=operasyon,
            sira_no=sira_no_str,
            boyut_adi="PROF_SURFACE",
            aciklama="PROFILE OF SURFACE (Combined)",
            eksen="M",
            nominal=base_profile.nominal,
            olculen=combined_result,  # Min/Max string formatında sakla
            pos_tolerans=base_profile.pos_tolerans,
            neg_tolerans=base_profile.neg_tolerans,
            sapma=base_profile.sapma,
            tolerans_disi=base_profile.tolerans_disi,
            bonus=base_profile.bonus,
            durum=base_profile.durum
        )
    
    def _parse_data_line(self, line: str, operasyon: str, sira_no_str: str, dim_name: str, description: str) -> Optional[CMMOlcum]:
        """Tek bir veri satırını parse eder - A ekseni desteği ile"""
        parts = line.split()
        if len(parts) < 3:
            return None
        
        try:
            eksen = parts[0]
            
            # Nominal
            nominal_str = parts[1]
            if nominal_str in ["RFS", "MMC", "LMC"]:
                nominal = 0.0
            else:
                nominal = float(nominal_str)
            
            # Ölçülen
            olculen = float(parts[2])
            
            # Toleranslar (varsa)
            pos_tol = None
            neg_tol = None
            bonus = None
            sapma = 0.0
            tolerans_disi = 0.0
            
            # TP satırı için özel parsing
            if eksen == "TP":
                print(f"DEBUG: TP satırı parse ediliyor: {line}")
                try:
                    # TP RFS 0.081 0.200 0.000 0.081 0.000
                    if len(parts) >= 6:
                        pos_tol = float(parts[3]) if parts[3] != '' else None  # Tolerans
                        bonus = float(parts[5]) if parts[5] != '' else None    # Bonus
                        sapma = float(parts[6]) if parts[6] != '' else 0.0     # Sapma (DEV)
                        tolerans_disi = float(parts[7]) if len(parts) >= 8 and parts[7] != '' else 0.0  # OUTTOL
                        print(f"DEBUG: TP parse - tol:{pos_tol}, bonus:{bonus}, sapma:{sapma}, outtol:{tolerans_disi}")
                except (ValueError, IndexError) as e:
                    print(f"DEBUG: TP parse hatası: {e}")
            else:
                # Normal satırlar için (D, R, M, DF, A) - X,Y,Z dahil
                if len(parts) >= 5:
                    try:
                        pos_tol = float(parts[3]) if parts[3] != '' else None
                        neg_tol = float(parts[4]) if parts[4] != '' else None
                    except ValueError:
                        pass
                
                # Sapma değerini bul (DEV sütunu - genelde sonlarda)
                for i, part in enumerate(parts):
                    try:
                        val = float(part)
                        # Sapma değeri (küçük pozitif/negatif değerler)
                        if i >= 5 and abs(val) < 1.0 and val != nominal and val != olculen:
                            sapma = val
                        # Tolerans dışı (genelde 0.000)
                        if i >= 6 and val == 0.0:
                            tolerans_disi = val
                            break
                    except ValueError:
                        continue
            
            # Durum
            durum = "✓" if tolerans_disi == 0.0 else "⚠"
            
            # Boyut adını oluştur
            if dim_name:
                if eksen in ['TP', 'DF']:
                    boyut_adi = f"{dim_name}_{eksen}"
                    aciklama = f"{description} ({eksen})"
                else:
                    boyut_adi = dim_name
                    aciklama = description
            else:
                boyut_adi = f"DIM{sira_no_str}"
                aciklama = "Bilinmeyen ölçüm"
            
            return CMMOlcum(
                operasyon=operasyon,
                sira_no=sira_no_str,
                boyut_adi=boyut_adi,
                aciklama=aciklama,
                eksen=eksen,
                nominal=nominal,
                olculen=olculen,
                pos_tolerans=pos_tol,
                neg_tolerans=neg_tol,
                sapma=sapma,
                tolerans_disi=tolerans_disi,
                bonus=bonus,
                durum=durum
            )
        
        except (ValueError, IndexError) as e:
            print(f"DEBUG: Veri satırı parse hatası: {e} - {line}")
            return None
    
    def parse_multiple_files(self, file_paths: List[str]) -> List[CMMOlcum]:
        """Birden fazla CMM dosyasını parse eder"""
        all_measurements = []
        
        for file_path in file_paths:
            try:
                print(f"\n🔄 İşleniyor: {file_path}")
                measurements = self.parse_file(file_path)
                all_measurements.extend(measurements)
                print(f"✅ {file_path}: {len(measurements)} ölçüm işlendi")
                
                # Her dosya için ölçüm detaylarını göster
                for m in measurements:
                    print(f"   📊 Ölçüm No: {m.sira_no}, Boyut: {m.boyut_adi}, Eksen: {m.eksen}")
                    
            except Exception as e:
                print(f"❌ {file_path}: Hata - {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n📈 TOPLAM: {len(all_measurements)} ölçüm")
        return all_measurements

class CMMExcelExporter:
    """CMM verilerini Excel'e dönüştüren sınıf"""
    
    def __init__(self):
        pass
    
    def to_dataframe(self, measurements: List[CMMOlcum]) -> pd.DataFrame:
        """CMMOlcum listesini DataFrame'e dönüştürür"""
        data = []
        for m in measurements:
            data.append({
                'Operasyon': m.operasyon,
                'Ölçüm No': m.sira_no,
                'Boyut Adı': m.boyut_adi,
                'Açıklama': m.aciklama,
                'Eksen': m.eksen,
                'Nominal': m.nominal,
                'Ölçülen': m.olculen,
                '+Tolerans': m.pos_tolerans,
                '-Tolerans': m.neg_tolerans,
                'Sapma': m.sapma,
                'Tolerans Dışı': m.tolerans_disi,
                'Bonus': m.bonus,
                'Durum': m.durum,
                'FAI Hariç': m.exclude_from_fai  # FAI hariç tutma bilgisi
            })
        
        df = pd.DataFrame(data)
        
        # Duplicate satırları kaldır
        df = df.drop_duplicates()
        
        # Operasyon ve ölçüm numarasına göre sırala
        # 1OP -> 1, 2OP -> 2 şeklinde sıralama
        op_mapping = {'1OP': 1, '2OP': 2, 'UNKNOWN': 3}
        df['op_order'] = df['Operasyon'].map(op_mapping)
        
        # Sıralama fonksiyonu - 10-18 formatı için
        def get_sort_key(sira_no_str):
            if '-' in str(sira_no_str):
                return int(str(sira_no_str).split('-')[0])
            else:
                return int(sira_no_str)
        
        df['sort_key'] = df['Ölçüm No'].apply(get_sort_key)
        
        # Sıralama: Operasyon önce, sonra ölçüm no
        df = df.sort_values(['op_order', 'sort_key', 'Boyut Adı'], ascending=[True, True, True])
        
        # Geçici sütunları kaldır ve index sıfırla
        df = df.drop(['op_order', 'sort_key'], axis=1).reset_index(drop=True)
        
        print(f"DEBUG: DataFrame oluşturuldu, {len(df)} satır")
        print(f"DEBUG: Operasyonlar: {df['Operasyon'].unique()}")
        print(f"DEBUG: Ölçüm numaraları: {sorted(df['Ölçüm No'].unique(), key=get_sort_key)}")
        
        return df
    
    def export_cleaned_data_to_excel(self, cleaned_data: List[Dict], output_path: str) -> bool:
        """Temizlenmiş JSON verisini Excel'e dönüştürür"""
        
        try:
            # Dict'ten DataFrame oluştur
            df = pd.DataFrame(cleaned_data)
            
            # NaN ve problematik değerleri temizle
            def clean_value(val):
                if pd.isna(val) or val is None:
                    return ''
                elif isinstance(val, float) and (not np.isfinite(val)):
                    return ''
                else:
                    return val
            
            # Tüm değerleri temizle
            for col in df.columns:
                df[col] = df[col].apply(clean_value)
            
            # Sütun isimlerini düzenle
            df = df.rename(columns={
                'operasyon': 'Operasyon',
                'sira_no': 'Ölçüm No',
                'boyut_adi': 'Boyut Adı',
                'aciklama': 'Açıklama',
                'eksen': 'Eksen',
                'nominal': 'Nominal',
                'olculen': 'Ölçülen',
                'pos_tolerans': '+Tolerans',
                'neg_tolerans': '-Tolerans',
                'sapma': 'Sapma',
                'tolerans_disi': 'Tolerans Dışı',
                'bonus': 'Bonus',
                'durum': 'Durum',
                'exclude_from_fai': 'FAI Hariç'
            })
            
            print(f"📋 Excel DataFrame hazırlandı:")
            print(f"   Satır sayısı: {len(df)}")
            print(f"   Operasyonlar: {df['Operasyon'].unique()}")
            print(f"   Ölçüm numaraları: {sorted(df['Ölçüm No'].unique())}")
            
            # Excel yazıcı oluştur
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                # Ana veri sayfası
                df.to_excel(writer, sheet_name='CMM_Verileri', index=False)
                
                # Workbook ve worksheet objelerini al
                workbook = writer.book
                worksheet = writer.sheets['CMM_Verileri']
                
                # Formatları tanımla
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                good_format = workbook.add_format({
                    'bg_color': '#C6EFCE',
                    'font_color': '#006100'
                })
                
                warning_format = workbook.add_format({
                    'bg_color': '#FFC7CE',
                    'font_color': '#9C0006'
                })
                
                # TP satırları için özel format
                tp_format = workbook.add_format({
                    'bg_color': '#E1D5E7',
                    'font_color': '#5B2C6F'
                })
                
                # Sütun genişliklerini ayarla
                worksheet.set_column('A:A', 12)  # Operasyon
                worksheet.set_column('B:B', 10)  # Ölçüm No
                worksheet.set_column('C:C', 15)  # Boyut Adı
                worksheet.set_column('D:D', 35)  # Açıklama
                worksheet.set_column('E:E', 8)   # Eksen
                worksheet.set_column('F:N', 12)  # Sayısal değerler
                
                # Header formatını uygula
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Sadece TP satırlarını renklendir
                for row_num in range(1, len(df) + 1):
                    eksen = df.iloc[row_num-1]['Eksen']
                    
                    # Sadece TP satırları için özel renk
                    if eksen == 'TP':
                        for col_num in range(len(df.columns)):
                            cell_value = df.iloc[row_num-1, col_num]
                            # Güvenli yazma
                            try:
                                worksheet.write(row_num, col_num, cell_value, tp_format)
                            except:
                                # Hata varsa boş string yaz
                                worksheet.write(row_num, col_num, '', tp_format)
                
                # Özet sayfa ekle
                self._add_summary_sheet_from_dict(writer, df, workbook)
                
                # FAI Form 3 sayfası ekle
                self._add_fai_form3_sheet(writer, df, workbook)
            
            print(f"💾 Excel dosyası oluşturuldu: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel export hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_fai_form3_sheet(self, writer, df: pd.DataFrame, workbook):
        """FAI Form 3 sayfası ekler - Position ve Min/Max desteği ile"""
        
        # FAI'dan hariç tutulan satırları filtrele
        df_fai = df[df['FAI Hariç'] != True].copy()
        
        # Yeni sayfa oluştur
        fai_ws = workbook.add_worksheet('FAI_Form3')
        
        # Format tanımları
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        doc_format = workbook.add_format({
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        section_header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'fg_color': '#E7E6E6',
            'border': 1
        })
        
        part_header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
        
        part_data_format = workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        column_header_format = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'fg_color': '#D9E1F2',
            'border': 1
        })
        
        data_format = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Sütun genişlikleri (ek bilgi sütunu ile)
        fai_ws.set_column('A:A', 6)   # Krk No
        fai_ws.set_column('B:B', 10)  # Ek Bilgi (LOC3, CIR6 vs)
        fai_ws.set_column('C:C', 12)  # Ref Bölge
        fai_ws.set_column('D:D', 18)  # Karakter Özelliği
        fai_ws.set_column('E:E', 12)  # Gerek/Ölçü
        fai_ws.set_column('F:F', 10)  # Requirement
        fai_ws.set_column('G:G', 15)  # Sonuç
        fai_ws.set_column('H:H', 2)   # Boş
        fai_ws.set_column('I:I', 2)   # Boş
        fai_ws.set_column('J:J', 15)  # Aletler
        fai_ws.set_column('K:K', 12)  # Uygunsuzluk
        fai_ws.set_column('L:L', 2)   # Boş
        fai_ws.set_column('M:M', 15)  # Ek Veriler
        fai_ws.set_column('N:N', 15)  # Ek Veriler devam
        
        # Satır yükseklikleri
        fai_ws.set_row(0, 25)
        fai_ws.set_row(2, 30)
        fai_ws.set_row(3, 25)
        fai_ws.set_row(5, 20)
        fai_ws.set_row(6, 30)
        
        # Başlık - 1. satır
        fai_ws.merge_range('D1:N1', 'İLK ÜRÜN MUAYENESİ\nFIRST ARTICLE INSPECTION (FAI)', title_format)
        fai_ws.write('N1', 'Doküman No:ENG-KT-FR-44\nİlk Yayın Tarihi: 26.06.2024\nRevizyon No: 01\nRevizyon Tarihi:06.09.2024', doc_format)
        
        # Alt başlık - 3. satır
        fai_ws.merge_range('A3:N3', 'Karakteristik Nitelikler, Doğrulama ve Uygunluk Değerlendirmesi Formu\nCharacteristic Accountability, Verification and Compatibility Evaluation\nSAE AS9102 Revision C', section_header_format)
        
        # Parça bilgileri başlıkları - 4. satır
        fai_ws.merge_range('A4:C4', '1. Parça Numarası\n     Part Number', part_header_format)
        fai_ws.merge_range('D4:J4', '2. Parça Tanımı\n     Part Name', part_header_format)
        fai_ws.merge_range('K4:L4', '3. Seri No.\n     Serial Number', part_header_format)
        fai_ws.merge_range('M4:N4', '4. FAI Rapor No.\n     FAIR Identifier', part_header_format)
        
        # Parça bilgileri verileri - 5. satır
        fai_ws.merge_range('A5:C5', 'MM-7570-1828', part_data_format)
        fai_ws.merge_range('D5:J5', 'KILAVUZ CL/KFY ORTA MAYON CIKIS ESB SOL', part_data_format)
        fai_ws.merge_range('K5:L5', 'FAI', part_data_format)
        fai_ws.merge_range('M5:N5', 'MM-7570-1828;241122', part_data_format)
        
        # Ana bölüm başlıkları - 6. satır
        fai_ws.merge_range('A6:F6', 'Karakteristik Nitelikler\nCharacteristic Accountability', section_header_format)
        fai_ws.merge_range('G6:L6', 'Muayene / Test Sonuçları\nInspection / Test Results', section_header_format)
        fai_ws.merge_range('M6:N6', '12. Ek Veriler / Yorumlar\n Additional Data / Comments', section_header_format)
        
        # Sütun başlıkları - 7. satır (ek bilgi sütunu ile)
        fai_ws.write('A7', '5. Krk. No.\n    Char No.', column_header_format)
        fai_ws.write('B7', '6. Ek Bilgi\nExtra Info', column_header_format)
        fai_ws.write('C7', '7.Dokümandaki Ref.Bölge\nReference Location', column_header_format)
        fai_ws.write('D7', '8. Karakter Özelliği\nCharacteristic Designator', column_header_format)
        fai_ws.merge_range('E7:F7', '9. Gerek/Ölçü\n     Requirement', column_header_format)
        fai_ws.merge_range('G7:I7', '10. Sonuç\n     Results', column_header_format)
        fai_ws.write('J7', '11.  Tasarlanmış / Nitelikli Aletler\nDesigned / Qualified Tooling', column_header_format)
        fai_ws.merge_range('K7:L7', '12. Uygunsuzluk Bildirim No.\nNon-Conformance Number', column_header_format)
        fai_ws.merge_range('M7:N7', '13. Ek Veriler / Yorumlar\n Additional Data / Comments', column_header_format)
        
        # Boş satır - 8
        for col in range(15):
            fai_ws.write(7, col, '', data_format)
        
        # Veri satırları - Alt numaralama ile
        start_row = 8
        
        # Aynı ölçüm numarası için sub-numbering hesapla
        measurement_counts = {}
        for idx, row in df_fai.iterrows():
            olcum_no = row['Ölçüm No']
            if olcum_no in measurement_counts:
                measurement_counts[olcum_no] += 1
            else:
                measurement_counts[olcum_no] = 1
        
        # Her ölçüm numarası için sayaç
        current_counts = {}
        
        # Position ölçümleri için min/max değerleri topla
        position_values = {}  # {(olcum_no, loc_name, measurement_type): [values]}
        
        for idx, row in df_fai.iterrows():
            olcum_no = row['Ölçüm No']
            boyut_adi = row['Boyut Adı']
            eksen = row['Eksen']
            
            # Position ölçümü için DF ve TP değerlerini topla
            if 'LOC' in str(boyut_adi) and eksen in ['DF', 'TP']:
                loc_name = str(boyut_adi).split('_')[0] if '_' in str(boyut_adi) else str(boyut_adi)
                key = (olcum_no, loc_name, eksen)
                if key not in position_values:
                    position_values[key] = []
                position_values[key].append(float(row['Ölçülen']))
        
        # FAI satırlarını yaz
        fai_row_index = 0
        for idx, row in df_fai.iterrows():
            current_row = start_row + fai_row_index
            olcum_no = row['Ölçüm No']
            
            # Sub-numbering hesapla
            if olcum_no in current_counts:
                current_counts[olcum_no] += 1
            else:
                current_counts[olcum_no] = 1
            
            # Krk No formatını belirle
            if measurement_counts[olcum_no] > 1:
                # Birden fazla ölçüm varsa alt numara ekle
                krk_no_formatted = f"{olcum_no}.{current_counts[olcum_no]}"
            else:
                # Tek ölçüm varsa sadece numara
                krk_no_formatted = str(olcum_no)
            
            # Ek bilgi çıkar (LOC3, CIR6 vs)
            boyut_adi = row['Boyut Adı']
            ek_bilgi = ""
            if '_' in str(boyut_adi):
                # DIM3_TP -> DIM3 ve TP ayrımı
                boyut_parts = str(boyut_adi).split('_')
                if len(boyut_parts) >= 2:
                    base_dim = boyut_parts[0]  # DIM3, LOC3 vs
                    # LOC3, CIR6, ANGL1 gibi bilgileri çıkar
                    if base_dim.startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL')):
                        ek_bilgi = base_dim
            elif str(boyut_adi).startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL')):
                ek_bilgi = str(boyut_adi)
            
            # Karakter özelliği belirle (Türkçe terimler)
            eksen = row['Eksen']
            aciklama = str(row['Açıklama'])
            
            if 'SURFACE' in aciklama.upper() or 'PROFILE' in aciklama.upper():
                ozellik = 'PROFİL'
            elif 'POSITION' in aciklama.upper() or eksen == 'TP':
                ozellik = 'KONUM'
            elif 'FLATNESS' in aciklama.upper():
                ozellik = 'DÜZLEMSELLİK'
            elif 'PARALLELISM' in aciklama.upper():
                ozellik = 'PARALELLİK'
            elif 'PERPENDICULARITY' in aciklama.upper():
                ozellik = 'DİKLİK'
            elif 'DISTANCE' in aciklama.upper():
                ozellik = 'MESAFE'
            elif 'ANGLE' in aciklama.upper() or eksen == 'A':
                ozellik = 'AÇI'
            elif 'LOCATION' in aciklama.upper():
                if eksen == 'D':
                    ozellik = 'ÇAP'
                elif eksen == 'R':
                    ozellik = 'YARIÇAP'
                else:
                    ozellik = 'KONUM'
            else:
                ozellik = str(boyut_adi)
            
            # Gerek/Ölçü formatı - TAM DEĞER, YUVARLAMA YOK
            nominal = row['Nominal']
            if nominal != 0 and eksen != 'TP':  # nominal > 0 yerine nominal != 0 kullan
                if eksen == 'R':
                    # R96, R61 formatı - tam sayıya yuvarla sadece R için
                    gerek_olcu = f"R{int(abs(nominal))}"  # Mutlak değer al
                elif eksen == 'A':
                    # Açı değerleri için - negatif değerleri mutlak değer olarak yaz
                    gerek_olcu = str(abs(nominal)).rstrip('0').rstrip('.')
                elif 'M6' in str(nominal):
                    gerek_olcu = "M6"
                else:
                    # TAM DEĞERİ KULLAN - YUVARLAMA YOK - NEGATİF DEĞERLERİ MUTLAK DEĞER OLARAK YAZ
                    gerek_olcu = str(abs(nominal)).rstrip('0').rstrip('.')
            elif eksen == 'TP':
                gerek_olcu = "KONUM"
            elif ozellik in ['DÜZLEMSELLİK', 'PARALELLİK', 'DİKLİK', 'PROFİL']:
                gerek_olcu = ozellik
            else:
                gerek_olcu = str(abs(nominal)).rstrip('0').rstrip('.') if nominal != 0 else ""
            
            # Requirement (tolerans) - Geometrik toleranslar için artı işareti kaldır - YUVARLAMA YOK!
            pos_tol = row['+Tolerans']
            neg_tol = row['-Tolerans']
            if pos_tol and neg_tol and pos_tol == neg_tol:
                if ozellik in ['KONUM', 'DÜZLEMSELLİK', 'PARALELLİK', 'DİKLİK', 'PROFİL']:
                    # Geometrik toleranslar için artı işareti yok - TAM DEĞER
                    requirement = str(pos_tol).replace('.', ',')
                else:
                    # Normal ölçüler için ± formatı - TAM DEĞER
                    requirement = f"±{str(pos_tol)}".replace('.', ',')
            elif pos_tol and neg_tol:
                requirement = f"+{str(pos_tol)}/-{str(neg_tol)}".replace('.', ',')
            elif pos_tol:
                if ozellik in ['KONUM', 'DÜZLEMSELLİK', 'PARALELLİK', 'DİKLİK', 'PROFİL']:
                    # Geometrik toleranslar için artı işareti yok - TAM DEĞER
                    requirement = str(pos_tol).replace('.', ',')
                else:
                    # Normal ölçüler için + formatı - TAM DEĞER
                    requirement = f"+{str(pos_tol)}".replace('.', ',')
            elif eksen == 'TP':
                requirement = str(row['Ölçülen']).replace('.', ',')
            else:
                requirement = ""
            
            # Sonuç formatı - Position ölçümleri için min/max format
            sonuc = row['Ölçülen']
            
            # Position ölçümleri için min/max kontrolü
            if 'LOC' in str(boyut_adi) and eksen in ['DF', 'TP']:
                loc_name = str(boyut_adi).split('_')[0] if '_' in str(boyut_adi) else str(boyut_adi)
                key = (olcum_no, loc_name, eksen)
                if key in position_values and len(position_values[key]) > 1:
                    # Min/max formatı kullan
                    values = position_values[key]
                    min_val = min(values)
                    max_val = max(values)
                    if abs(min_val - max_val) < 0.001:
                        sonuc_str = str(min_val).replace('.', ',')
                    else:
                        sonuc_str = f"{str(min_val).replace('.', ',')} - {str(max_val).replace('.', ',')}"
                else:
                    sonuc_str = str(sonuc).replace('.', ',')
            elif isinstance(sonuc, (int, float)):
                if 'M6' in str(gerek_olcu):
                    sonuc_str = "OK"
                else:
                    # TAM DEĞERİ YAZ - YUVARLAMA YOK!
                    sonuc_str = str(sonuc).replace('.', ',')
            else:
                sonuc_str = str(sonuc).replace('.', ',')
            
            # Veriyi yaz (ek bilgi sütunu ile güncellenmiş sütun düzeni)
            fai_ws.write(current_row, 0, krk_no_formatted, data_format)  # A: Krk No (alt numaralama)
            fai_ws.write(current_row, 1, ek_bilgi, data_format)  # B: Ek Bilgi (LOC3, CIR6 vs)
            fai_ws.write(current_row, 2, 'N/A', data_format)  # C: Ref Bölge  
            fai_ws.write(current_row, 3, ozellik, data_format)  # D: Karakter Özelliği
            fai_ws.write(current_row, 4, gerek_olcu, data_format)  # E: Gerek/Ölçü
            fai_ws.write(current_row, 5, requirement, data_format)  # F: Requirement
            fai_ws.write(current_row, 6, sonuc_str, data_format)  # G: Sonuç
            fai_ws.write(current_row, 7, '', data_format)  # H: Boş
            fai_ws.write(current_row, 8, '', data_format)  # I: Boş
            fai_ws.write(current_row, 9, 'CMM-001', data_format)  # J: Aletler
            fai_ws.write(current_row, 10, '', data_format)  # K: Uygunsuzluk No - BOŞ
            fai_ws.write(current_row, 11, '', data_format)  # L: Boş
            fai_ws.write(current_row, 12, '', data_format)  # M: Ek Veriler - BOŞ
            fai_ws.write(current_row, 13, '', data_format)  # N: Ek Veriler - BOŞ
            fai_ws.write(current_row, 14, '', data_format)  # O: Boş
            
            fai_row_index += 1
        
        print(f"📋 FAI Form 3 sayfası eklendi: {fai_row_index} karakteristik")
        
        # Alt numaralama debug bilgisi
        duplicate_measurements = {k: v for k, v in measurement_counts.items() if v > 1}
        if duplicate_measurements:
            print(f"🔢 Alt numaralama yapılan ölçümler: {duplicate_measurements}")
        else:
            print(f"ℹ️ Tüm ölçümler tekil, alt numaralama yapılmadı")
    
    def _add_summary_sheet_from_dict(self, writer, df: pd.DataFrame, workbook):
        """Dict verisinden özet sayfası ekler"""
        summary_data = {
            'Metrik': [
                'Toplam Ölçüm',
                'Başarılı Ölçüm',
                'Uyarı Gerekli',
                'Operasyon 1OP',
                'Operasyon 2OP',
                'Farklı Ölçüm Numarası',
                'FAI Hariç Tutulan'
            ],
            'Değer': [
                len(df),
                len(df[df['Durum'] == '✓']),
                len(df[df['Durum'] == '⚠']),
                len(df[df['Operasyon'] == '1OP']),
                len(df[df['Operasyon'] == '2OP']),
                len(df['Ölçüm No'].unique()),
                len(df[df['FAI Hariç'] == True])
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Özet', index=False)
        
        # Özet sayfası formatlaması
        summary_ws = writer.sheets['Özet']
        summary_ws.set_column('A:A', 20)
        summary_ws.set_column('B:B', 15)

# Legacy functions for backward compatibility
def process_cmm_files(file_paths: List[str], output_excel_path: str = None) -> Dict[str, Any]:
    """Ana işleme fonksiyonu - backward compatibility için"""
    service = CMMService()
    return service.process_files(file_paths, output_excel_path)

def clean_and_sort_data(json_path: str) -> List[Dict]:
    """JSON dosyasından veriyi temizle ve ölçüm numarasına göre sırala"""
    import json
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Ham veri analizi:")
    print(f"   Toplam kayıt: {len(data)}")
    
    # Operasyonlara göre grupla (sadece debug için)
    op_groups = {}
    for item in data:
        op = item['operasyon']
        if op not in op_groups:
            op_groups[op] = []
        op_groups[op].append(item)
    
    for op, items in op_groups.items():
        sira_nos = [item['sira_no'] for item in items]
        print(f"   {op}: {len(items)} kayıt, sıra no: {sorted(set(sira_nos))}")
    
    # Duplikatları kaldır (tamamen aynı satırlar)
    seen = set()
    cleaned = []
    duplicates_removed = 0
    
    for item in data:
        # Unique key oluştur - tüm alanları dahil et
        key = (
            item['operasyon'],
            item['sira_no'], 
            item['boyut_adi'],
            item['aciklama'],
            item['eksen'],
            item['nominal'],
            str(item['olculen'])  # String'e çevir (min/max formatı için)
        )
        
        if key not in seen:
            seen.add(key)
            cleaned.append(item)
        else:
            duplicates_removed += 1
    
    print(f"🗑️ {duplicates_removed} duplikat kayıt kaldırıldı")
    
    # Sıralama fonksiyonu - 10-18 formatı için
    def get_sort_key(item):
        sira_no_str = str(item['sira_no'])
        # 10-18 formatında ise "-" öncesini al
        if '-' in sira_no_str:
            return int(sira_no_str.split('-')[0])
        else:
            return int(sira_no_str)
    
    # Ölçüm numarasına göre sırala (10-18 → 10 olarak değerlendir)
    cleaned.sort(key=get_sort_key)
    
    print(f"✅ Sıralama tamamlandı: {len(cleaned)} kayıt")
    print(f"   Ölçüm numaraları sırası: {[item['sira_no'] for item in cleaned]}")
    
    return cleaned

# Test fonksiyonu
def test_parser():
    """Parser'ı test etmek için"""
    test_files = [
        "uploads/cmm_0001-1OP.RTF",
        "uploads/cmm_0001-2OP.RTF"
    ]
    
    output_path = "static/cmm_test_output.xlsx"
    result = process_cmm_files(test_files, output_path)
    print("Test sonucu:", result)

if __name__ == "__main__":
    test_parser()