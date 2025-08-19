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
        
        # Sırala - Geliştirilmiş sıralama
        def get_sort_key(item):
            sira_no_str = str(item['sira_no'])
            if '-' in sira_no_str:
                parts = sira_no_str.split('-', 1)
                try:
                    return int(parts[0])
                except ValueError:
                    return 999
            else:
                try:
                    return int(sira_no_str)
                except ValueError:
                    return 999
        
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
                content = re.sub(r'\\[a-z]+\d*', '', content)
                content = re.sub(r'[{}]', '', content)
                return content
        except Exception as e:
            print(f"RTF okuma hatası: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Metni temizler ve normalize eder"""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\x00', '').replace('\r', '\n')
        return text.strip()
    
    def parse_file(self, file_path: str) -> List[CMMOlcum]:
        """Tek bir CMM dosyasını parse eder"""
        measurements = []
        
        # Dosya adından operasyon belirle
        filename = Path(file_path).stem
        operasyon = self._detect_operation(filename)
        
        print(f"DEBUG: İşlenen dosya: {filename}, Operasyon: {operasyon}")
        
        # RTF text'i çıkar
        text = self.extract_rtf_text(file_path)
        if not text:
            return measurements
        
        # Sıra numaralarını bul - Geliştirilmiş pattern'ler
        sira_matches = self._find_measurement_numbers(text)
        
        print(f"DEBUG: Toplam eşleşme sayısı: {len(sira_matches)}")
        
        # Her sıra numarası için bloğu çıkar
        for i, match in enumerate(sira_matches):
            sira_no_str = self._process_measurement_number(match.group(1).strip())
            
            # Blok başlangıcı ve bitişi
            start_pos = match.end()
            if i + 1 < len(sira_matches):
                end_pos = sira_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            # Blok metnini çıkar
            block_text = text[start_pos:end_pos].strip()
            
            if block_text:
                block_measurements = self.parse_measurement_block_simple(block_text, operasyon, sira_no_str)
                measurements.extend(block_measurements)
                print(f"DEBUG: Sıra {sira_no_str}: {len(block_measurements)} ölçüm eklendi")
        
        print(f"DEBUG: Toplam ölçüm sayısı: {len(measurements)}")
        return measurements
    
    def _detect_operation(self, filename: str) -> str:
        """Dosya adından operasyon tespit et"""
        filename_upper = filename.upper()
        
        if '1OP' in filename_upper:
            return '1OP'
        elif '2OP' in filename_upper:
            return '2OP'
        elif '3OP' in filename_upper:
            return '3OP'
        else:
            print(f"DEBUG: Dosya adında operasyon bulunamadı, varsayılan '1OP' atandı")
            return '1OP'
    
    def _find_measurement_numbers(self, text: str) -> List[re.Match]:
        """Metinde ölçüm numaralarını bul - Geliştirilmiş"""
        # Dört farklı pattern dene
        pattern1 = r'\*+\s+([0-9]+(?:-[A-Za-z0-9\s]+)?)\s+\*+'
        pattern2 = r'\*+([0-9]+(?:-[A-Za-z0-9\s]+)?)\*+'
        pattern3 = r'\*{3,}\s*([0-9]+)\s*\*{3,}'
        pattern4 = r'\*{3,}\s*([0-9]+\s*-\s*[0-9]+)\s*\*{3,}'  # 10-18 formatı için
        
        # Pattern4'ü önce uygula (en spesifik)
        matches4 = list(re.finditer(pattern4, text, re.IGNORECASE))
        
        excluded_positions = set()
        for match in matches4:
            for pos in range(match.start(), match.end()):
                excluded_positions.add(pos)
        
        # Diğer pattern'leri uygula
        matches1 = []
        matches2 = []
        matches3 = []
        
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            if match.start() not in excluded_positions:
                matches1.append(match)
        
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            if match.start() not in excluded_positions:
                matches2.append(match)
                
        for match in re.finditer(pattern3, text, re.IGNORECASE):
            if match.start() not in excluded_positions:
                matches3.append(match)
        
        # Tüm match'leri birleştir
        all_matches = []
        seen_positions = set()
        
        for match in matches4 + matches1 + matches2 + matches3:
            if match.start() not in seen_positions:
                all_matches.append(match)
                seen_positions.add(match.start())
        
        # Pozisyona göre sırala
        return sorted(all_matches, key=lambda x: x.start())
    
    def _process_measurement_number(self, sira_no_raw: str) -> str:
        """Sıra numarasını işle"""
        if '-' in sira_no_raw:
            parts = sira_no_raw.split('-', 1)
            first_part = parts[0].strip()
            
            if len(parts) > 1:
                second_part = parts[1].strip()
                try:
                    int(second_part)
                    # İkinci kısım da sayı, aralık formatı (10-18)
                    return sira_no_raw.replace(' ', '')
                except ValueError:
                    # İkinci kısım metin, sadece ilk kısmı al
                    return first_part
            else:
                return first_part
        else:
            return sira_no_raw
    
    def parse_measurement_block_simple(self, block: str, operasyon: str, sira_no_str: str) -> List[CMMOlcum]:
        """Basitleştirilmiş blok parser"""
        measurements = []
        lines = block.split('\n')
        
        current_dim = None
        current_desc = None
        surface_profiles = []
        has_surface = False
        position_measurements = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # DIM tanımını yakala
            dim_match = re.search(r'DIM\s+(\w+)=\s*(.+?)\s+UNITS=MM', line)
            if dim_match:
                current_dim = dim_match.group(1)
                current_desc = dim_match.group(2).strip()
                
                if 'SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper():
                    has_surface = True
                
                if 'POSITION' in current_desc.upper():
                    if position_measurements:
                        self._process_position_group(position_measurements, measurements)
                        position_measurements = []
                continue
            
            # Veri satırları
            if re.match(r'^[DRMTPZYXAFP]+\s+', line):
                if current_desc and 'POSITION' in current_desc.upper():
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        position_measurements.append(measurement)
                elif current_desc and ('SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper()):
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        surface_profiles.append(measurement)
                else:
                    measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                    if measurement:
                        measurements.append(measurement)
        
        # Son position grubunu işle
        if position_measurements:
            self._process_position_group(position_measurements, measurements)
        
        # SURFACE profil ölçümlerini birleştir
        if surface_profiles and has_surface:
            m_surface_profiles = [p for p in surface_profiles if p.eksen == 'M']
            other_profiles = [p for p in surface_profiles if p.eksen != 'M']
            
            if m_surface_profiles:
                combined_measurement = self._combine_surface_profiles(m_surface_profiles, sira_no_str, operasyon)
                if combined_measurement:
                    measurements.append(combined_measurement)
            
            if other_profiles:
                measurements.extend(other_profiles)
        elif surface_profiles:
            measurements.extend(surface_profiles)
        
        return measurements
    
    def _process_position_group(self, position_measurements: List[CMMOlcum], measurements: List[CMMOlcum]):
        """POSITION ölçüm grubunu işle"""
        for m in position_measurements:
            if m.eksen in ['X', 'Y', 'Z', 'PR', 'PA']:
                m.exclude_from_fai = True
            elif m.eksen in ['TP', 'DF']:
                m.exclude_from_fai = False
            measurements.append(m)
    
    def _combine_surface_profiles(self, profiles: List[CMMOlcum], sira_no_str: str, operasyon: str) -> Optional[CMMOlcum]:
        """Birden fazla SURFACE profil ölçümünü birleştirir"""
        if not profiles:
            return None
        
        measured_values = [float(p.olculen) for p in profiles]
        min_val = min(measured_values)
        max_val = max(measured_values)
        
        if abs(min_val - max_val) < 0.001:
            combined_result = str(min_val).rstrip('0').rstrip('.')
        else:
            min_str = str(min_val).rstrip('0').rstrip('.')
            max_str = str(max_val).rstrip('0').rstrip('.')
            combined_result = f"{min_str} / {max_str}"
        
        base_profile = profiles[0]
        
        return CMMOlcum(
            operasyon=operasyon,
            sira_no=sira_no_str,
            boyut_adi="SURFACE",  # PROF_SURFACE yerine SURFACE
            aciklama="PROFILE OF SURFACE (Combined)",
            eksen="M",
            nominal=0.0,  # SURFACE için nominal her zaman 0
            olculen=combined_result,
            pos_tolerans=base_profile.pos_tolerans,
            neg_tolerans=base_profile.neg_tolerans,
            sapma=base_profile.sapma,
            tolerans_disi=base_profile.tolerans_disi,
            bonus=base_profile.bonus,
            durum=base_profile.durum
        )
    
    def _parse_data_line(self, line: str, operasyon: str, sira_no_str: str, dim_name: str, description: str) -> Optional[CMMOlcum]:
        """Tek bir veri satırını parse eder"""
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
            
            # Toleranslar
            pos_tol = None
            neg_tol = None
            bonus = None
            sapma = 0.0
            tolerans_disi = 0.0
            
            # TP satırı için özel parsing
            if eksen == "TP":
                if len(parts) >= 4:
                    try:
                        pos_tol = float(parts[3]) if parts[3] != '' else 0.0
                    except ValueError:
                        pos_tol = 0.100
                    neg_tol = 0
                    
                    # Bonus
                    bonus = None
                    for i in range(4, min(len(parts), 7)):
                        try:
                            val = float(parts[i])
                            if i == 4 and val > 0:
                                bonus = val
                                break
                        except ValueError:
                            continue
                    
                    sapma = olculen
                    
                    # Tolerans dışı kontrolü
                    tolerans_disi = 0.0
                    for i in range(5, len(parts)):
                        try:
                            val = float(parts[i])
                            if val == 0.0 and i >= 6:
                                tolerans_disi = val
                                break
                        except ValueError:
                            continue
            else:
                # Normal satırlar
                if len(parts) >= 5:
                    try:
                        pos_tol = float(parts[3]) if parts[3] != '' else None
                        neg_tol = float(parts[4]) if parts[4] != '' else None
                    except ValueError:
                        pass
                
                # Sapma değerini bul
                for i, part in enumerate(parts):
                    try:
                        val = float(part)
                        if i >= 5 and abs(val) < 1.0 and val != nominal and val != olculen:
                            sapma = val
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
            print(f"DEBUG: Veri satırı parse hatası: {e}")
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
                
                for m in measurements:
                    print(f"   📊 Ölçüm No: {m.sira_no}, Boyut: {m.boyut_adi}, Eksen: {m.eksen}")
                    
            except Exception as e:
                print(f"❌ {file_path}: Hata - {e}")
                traceback.print_exc()
        
        print(f"\n📈 TOPLAM: {len(all_measurements)} ölçüm")
        return all_measurements


class CMMExcelExporter:
    """CMM verilerini Excel'e dönüştüren sınıf"""
    
    def __init__(self):
        pass
    
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
                
                # TP satırlarını renklendir
                for row_num in range(1, len(df) + 1):
                    eksen = df.iloc[row_num-1]['Eksen']
                    if eksen == 'TP':
                        for col_num in range(len(df.columns)):
                            cell_value = df.iloc[row_num-1, col_num]
                            try:
                                worksheet.write(row_num, col_num, cell_value, tp_format)
                            except:
                                worksheet.write(row_num, col_num, '', tp_format)
                
                # Özet sayfa ekle
                self._add_summary_sheet_from_dict(writer, df, workbook)
                
                # FAI Form 3 sayfası ekle - DÜZELTİLMİŞ VERSİYON
                self._add_fai_form3_sheet(writer, df, workbook)
            
            print(f"💾 Excel dosyası oluşturuldu: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel export hatası: {e}")
            traceback.print_exc()
            return False
    
    def _add_fai_form3_sheet(self, writer, df: pd.DataFrame, workbook):
        """FAI Form 3 sayfası ekler - SURFACE ve FLATNESS düzeltmesi ile"""
        
        # FAI'dan hariç tutulan satırları filtrele
        df_fai = df.copy()
        
        # Debug: Başlangıçtaki TP satırlarını kontrol et
        all_tp_before = df_fai[df_fai['Eksen'] == 'TP']
        print(f"📊 FAI öncesi toplam TP satırı: {len(all_tp_before)}")
        
        # 1. Önce normal FAI filtrelemesi yap
        df_fai = df_fai[df_fai['FAI Hariç'] != True].copy()
        
        # 2. X, Y, Z, PR, PA koordinat satırlarını çıkar (POSITION olanlar)
        df_fai = df_fai[~((df_fai['Boyut Adı'].str.contains('LOC', na=False)) & 
                         (df_fai['Eksen'].isin(['X', 'Y', 'Z', 'PR', 'PA'])) & 
                         (df_fai['Açıklama'].str.contains('POSITION', na=False)))].copy()
        
        # 3. LOC1_DF HARİÇ diğer POSITION DF satırlarını çıkar
        df_fai = df_fai[~((df_fai['Boyut Adı'].str.contains('LOC', na=False)) & 
                         (df_fai['Eksen'] == 'DF') & 
                         (df_fai['Boyut Adı'] != 'LOC1_DF'))].copy()
        
        # 4. TÜM TP satırlarını tekrar ekle
        all_tp_rows = df[df['Eksen'] == 'TP'].copy()
        
        # 5. TÜM LOC+DF satırlarını ekle
        all_loc_df_rows = df[(df['Boyut Adı'].str.contains('LOC', na=False)) & 
                             (df['Eksen'] == 'DF')].copy()
        
        # Eksik TP satırlarını ekle
        for idx, tp_row in all_tp_rows.iterrows():
            boyut_adi = tp_row['Boyut Adı']
            olcum_no = tp_row['Ölçüm No']
            
            existing = df_fai[(df_fai['Boyut Adı'] == boyut_adi) & 
                             (df_fai['Ölçüm No'] == olcum_no) &
                             (df_fai['Eksen'] == 'TP')]
            
            if existing.empty:
                print(f"  ➕ TP satırı ekleniyor: {boyut_adi} (Ölçüm {olcum_no})")
                df_fai = pd.concat([df_fai, pd.DataFrame([tp_row])], ignore_index=True)
        
        # LOC+DF satırlarını ekle
        for idx, df_row in all_loc_df_rows.iterrows():
            boyut_adi = df_row['Boyut Adı']
            olcum_no = df_row['Ölçüm No']
            
            existing = df_fai[(df_fai['Boyut Adı'] == boyut_adi) & 
                             (df_fai['Ölçüm No'] == olcum_no)]
            
            if existing.empty:
                print(f"  ➕ LOC+DF satırı ekleniyor: {boyut_adi} (Ölçüm {olcum_no})")
                df_fai = pd.concat([df_fai, pd.DataFrame([df_row])], ignore_index=True)
        
        # SIRALAMA DÜZELTMESİ - Sayısal sıralama için özel fonksiyon
        def get_numeric_sort_key(olcum_no):
            """Ölçüm numarasını sayısal değere çevir (sıralama için)"""
            olcum_no_str = str(olcum_no)
            # Eğer tire varsa ilk kısmı al (10-18 -> 10)
            if '-' in olcum_no_str:
                olcum_no_str = olcum_no_str.split('-')[0]
            try:
                return int(olcum_no_str)
            except ValueError:
                return 9999  # Sayısal olmayan değerler en sona
        
        # Sıralama için geçici sütun ekle
        df_fai['sort_key'] = df_fai['Ölçüm No'].apply(get_numeric_sort_key)
        df_fai['boyut_sort'] = df_fai['Boyut Adı'].apply(lambda x: (x.split('_')[0] if '_' in str(x) else str(x), x))
        
        # Önce ölçüm numarasına göre sayısal sıralama, sonra boyut adına göre alfabetik
        df_fai = df_fai.sort_values(by=['sort_key', 'boyut_sort']).reset_index(drop=True)
        
        # Geçici sütunları kaldır
        df_fai = df_fai.drop(['sort_key', 'boyut_sort'], axis=1)
        
        # Debug: Filtreleme sonrası TP satırlarını kontrol et
        tp_in_fai = df_fai[df_fai['Eksen'] == 'TP']
        print(f"📋 FAI'daki TP satır sayısı (filtreleme sonrası): {len(tp_in_fai)}")
        
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
        
        # Sütun genişlikleri
        fai_ws.set_column('A:A', 6)   # Krk No
        fai_ws.set_column('B:B', 10)  # Ek Bilgi
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
        
        # FAI Form başlıkları
        fai_ws.merge_range('D1:N1', 'İLK ÜRÜN MUAYENESİ\nFIRST ARTICLE INSPECTION (FAI)', title_format)
        fai_ws.write('N1', 'Doküman No:ENG-KT-FR-44\nİlk Yayın Tarihi: 26.06.2024\nRevizyon No: 01\nRevizyon Tarihi:06.09.2024', doc_format)
        
        fai_ws.merge_range('A3:N3', 'Karakteristik Nitelikler, Doğrulama ve Uygunluk Değerlendirmesi Formu\nCharacteristic Accountability, Verification and Compatibility Evaluation\nSAE AS9102 Revision C', section_header_format)
        
        fai_ws.merge_range('A4:C4', '1. Parça Numarası\n     Part Number', part_header_format)
        fai_ws.merge_range('D4:J4', '2. Parça Tanımı\n     Part Name', part_header_format)
        fai_ws.merge_range('K4:L4', '3. Seri No.\n     Serial Number', part_header_format)
        fai_ws.merge_range('M4:N4', '4. FAI Rapor No.\n     FAIR Identifier', part_header_format)
        
        fai_ws.merge_range('A5:C5', 'MM-7570-1828', part_data_format)
        fai_ws.merge_range('D5:J5', 'KILAVUZ CL/KFY ORTA MAYON CIKIS ESB SOL', part_data_format)
        fai_ws.merge_range('K5:L5', 'FAI', part_data_format)
        fai_ws.merge_range('M5:N5', 'MM-7570-1828;241122', part_data_format)
        
        fai_ws.merge_range('A6:F6', 'Karakteristik Nitelikler\nCharacteristic Accountability', section_header_format)
        fai_ws.merge_range('G6:L6', 'Muayene / Test Sonuçları\nInspection / Test Results', section_header_format)
        fai_ws.merge_range('M6:N6', '12. Ek Veriler / Yorumlar\n Additional Data / Comments', section_header_format)
        
        # Sütun başlıkları
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
        
        # Veri satırları
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
                krk_no_formatted = f"{olcum_no}.{current_counts[olcum_no]}"
            else:
                krk_no_formatted = str(olcum_no)
            
            # Ek bilgi çıkar
            boyut_adi = row['Boyut Adı']
            ek_bilgi = ""
            if '_' in str(boyut_adi):
                boyut_parts = str(boyut_adi).split('_')
                if len(boyut_parts) >= 2:
                    base_dim = boyut_parts[0]
                    if base_dim.startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL', 'CYLY', 'DIST', 'PERP')):
                        ek_bilgi = base_dim
            elif str(boyut_adi).startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL', 'CYLY', 'DIST', 'PERP')):
                ek_bilgi = str(boyut_adi)
            
            # Karakter özelliği belirle
            eksen = row['Eksen']
            aciklama = str(row['Açıklama'])
            
            if 'POSITION' in aciklama.upper() or eksen == 'TP':
                ozellik = 'KONUM'
            elif 'DISTANCE' in aciklama.upper() or 'DIST' in str(boyut_adi).upper():
                ozellik = 'MESAFE'
            elif 'PERPENDICULARITY' in aciklama.upper() or 'PERP' in str(boyut_adi).upper():
                ozellik = 'DİKLİK'
            elif 'FLATNESS' in aciklama.upper() or 'FLAT' in str(boyut_adi).upper():
                ozellik = 'FLATNESS'  # FLAT1 yerine FLATNESS
            elif 'SURFACE' in aciklama.upper() or 'PROFILE' in aciklama.upper() or 'PROF' in str(boyut_adi).upper():
                ozellik = 'SURFACE'  # Profil yerine SURFACE
            elif 'LOCATION' in aciklama.upper() and eksen == 'D':
                ozellik = 'ÇAP'
            else:
                # Eğer hiçbiri değilse boyut adına bak
                if 'PROF' in str(boyut_adi).upper():
                    ozellik = 'SURFACE'
                elif 'FLAT' in str(boyut_adi).upper():
                    ozellik = 'FLATNESS'
                else:
                    ozellik = str(boyut_adi)
            
            # Gerek/Ölçü formatı - BU KISIM DEĞİŞTİ!
            nominal = row['Nominal']
            
            # SURFACE ve FLATNESS için özel durum
            if ozellik == 'SURFACE':
                gerek_olcu = "SURFACE"  # 0 yerine SURFACE
            elif ozellik == 'FLATNESS':
                gerek_olcu = "FLATNESS"  # 0 yerine FLATNESS
            elif eksen == 'TP':
                gerek_olcu = "KONUM"
            elif eksen == 'DF':
                gerek_olcu = str(abs(nominal)).rstrip('0').rstrip('.')
            elif ozellik in ['DİKLİK', 'MESAFE'] and nominal in [0, 1.0]:
                gerek_olcu = ozellik
            else:
                gerek_olcu = str(abs(nominal)).rstrip('0').rstrip('.')
            
            # TOLERANS FORMATLAMA
            pos_tol = row['+Tolerans']
            neg_tol = row['-Tolerans']
            
            # None veya NaN değerleri 0 olarak ele al
            if pos_tol is None or pd.isna(pos_tol):
                pos_tol = 0
            if neg_tol is None or pd.isna(neg_tol):
                neg_tol = 0
            
            # Requirement formatı
            requirement = ""
            
            # TP için özel durum
            if eksen == 'TP':
                if pos_tol > 0:
                    # TP için de eşit toleranslarda ± kullan
                    if neg_tol > 0 and pos_tol == neg_tol:
                        requirement = f"±{str(pos_tol).replace('.', ',')}"
                    else:
                        requirement = f"⌖{str(pos_tol).replace('.', ',')}"
                else:
                    requirement = "⌖0,3"
            
            # DF için özel durum
            elif eksen == 'DF':
                # TÜM DF'ler için: eşit toleranslarda ± kullan
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}"
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol > 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # DİKLİK için
            elif ozellik == 'DİKLİK':
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                elif pos_tol > 0:
                    requirement = f"⊥{str(pos_tol).replace('.', ',')}"
                else:
                    requirement = "⊥0,1"
            
            # KONUM için
            elif ozellik == 'KONUM' and eksen != 'TP':
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}"
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol > 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # MESAFE için
            elif ozellik == 'MESAFE':
                # Eğer pozitif ve negatif toleranslar eşitse ± kullan
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                # Sadece pozitif tolerans varsa
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/0"
                # Sadece negatif tolerans varsa
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                # Farklı toleranslar varsa
                elif pos_tol > 0 and neg_tol > 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # ÇAP için
            elif ozellik == 'ÇAP':
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/0"
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol > 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # FLATNESS ve SURFACE için
            elif ozellik in ['FLATNESS', 'SURFACE']:
                if pos_tol > 0 and neg_tol > 0 and pos_tol == neg_tol:
                    requirement = f"±{str(pos_tol).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}"
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol > 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # Genel durumlar
            else:
                if pos_tol > 0 and neg_tol > 0:
                    if pos_tol == neg_tol:
                        requirement = f"±{str(pos_tol).replace('.', ',')}"
                    else:
                        requirement = f"+{str(pos_tol).replace('.', ',')}/-{str(abs(neg_tol)).replace('.', ',')}"
                elif pos_tol > 0 and neg_tol == 0:
                    requirement = f"+{str(pos_tol).replace('.', ',')}"
                elif pos_tol == 0 and neg_tol > 0:
                    requirement = f"-{str(abs(neg_tol)).replace('.', ',')}"
                else:
                    requirement = ""
            
            # Sonuç formatı
            sonuc = row['Ölçülen']
            if isinstance(sonuc, (int, float)):
                sonuc_str = str(sonuc).replace('.', ',')
            else:
                sonuc_str = str(sonuc).replace('.', ',')
            
            # Veriyi yaz
            fai_ws.write(current_row, 0, krk_no_formatted, data_format)
            fai_ws.write(current_row, 1, ek_bilgi, data_format)
            fai_ws.write(current_row, 2, 'N/A', data_format)
            fai_ws.write(current_row, 3, ozellik, data_format)
            fai_ws.write(current_row, 4, gerek_olcu, data_format)
            fai_ws.write(current_row, 5, requirement, data_format)
            fai_ws.write(current_row, 6, sonuc_str, data_format)
            fai_ws.write(current_row, 7, '', data_format)
            fai_ws.write(current_row, 8, '', data_format)
            fai_ws.write(current_row, 9, 'CMM-001', data_format)
            fai_ws.write(current_row, 10, '', data_format)
            fai_ws.write(current_row, 11, '', data_format)
            fai_ws.write(current_row, 12, '', data_format)
            fai_ws.write(current_row, 13, '', data_format)
            fai_ws.write(current_row, 14, '', data_format)
            
            fai_row_index += 1
        
        print(f"📋 FAI Form 3 sayfası eklendi: {fai_row_index} karakteristik")
        
        duplicate_measurements = {k: v for k, v in measurement_counts.items() if v > 1}
        if duplicate_measurements:
            print(f"🔢 Alt numaralama yapılan ölçümler: {duplicate_measurements}")
    
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
    
    # Operasyonlara göre grupla
    op_groups = {}
    for item in data:
        op = item['operasyon']
        if op not in op_groups:
            op_groups[op] = []
        op_groups[op].append(item)
    
    for op, items in op_groups.items():
        sira_nos = [item['sira_no'] for item in items]
        print(f"   {op}: {len(items)} kayıt, sıra no: {sorted(set(sira_nos))}")
    
    # Duplikatları kaldır
    seen = set()
    cleaned = []
    duplicates_removed = 0
    
    for item in data:
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
        else:
            duplicates_removed += 1
    
    print(f"🗑️ {duplicates_removed} duplikat kayıt kaldırıldı")
    
    # Sıralama fonksiyonu
    def get_sort_key(item):
        sira_no_str = str(item['sira_no'])
        if '-' in sira_no_str:
            first_part = sira_no_str.split('-')[0].strip()
            try:
                return float(first_part)
            except ValueError:
                return 999
        else:
            try:
                return float(sira_no_str)
            except ValueError:
                return 999
    
    cleaned.sort(key=get_sort_key)
    
    print(f"✅ Sıralama tamamlandı: {len(cleaned)} kayıt")
    
    return cleaned


# Test fonksiyonu
def test_parser():
    """Parser'ı test etmek için"""
    test_files = [
        "uploads/CMM_10140783_FAI.RTF"
    ]
    
    output_path = "static/cmm_test_output.xlsx"
    result = process_cmm_files(test_files, output_path)
    print("Test sonucu:", result)


if __name__ == "__main__":
    test_parser()