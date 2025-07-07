# backend/utils/cmm_parser.py
# CMM Parser dosyasını bu konuma kopyalayın

import re
import os
import pandas as pd
try:
    from striprtf.striprtf import rtf_to_text
    STRIPRTF_AVAILABLE = True
except ImportError:
    STRIPRTF_AVAILABLE = False
    print("⚠️ striprtf paketi yüklü değil. RTF desteği sınırlı olacak.")
    
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CMMOlcum:
    """CMM ölçüm verisi için data class"""
    operasyon: str
    sira_no: int
    boyut_adi: str
    aciklama: str
    eksen: str
    nominal: float
    olculen: float
    pos_tolerans: Optional[float]
    neg_tolerans: Optional[float]
    sapma: float
    tolerans_disi: float
    bonus: Optional[float] = None
    durum: str = "✓"

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
    
    def parse_measurement_block(self, block: str, operasyon: str) -> List[CMMOlcum]:
        """Tek bir ölçüm bloğunu parse eder"""
        measurements = []
        lines = block.split('\n')
        
        sira_no = None
        boyut_adi = None
        aciklama = None
        
        # Sıra numarası bul - düzeltilmiş regex
        for line in lines:
            # *******   1    ******* veya **********   3       ********** formatını yakala
            match = re.search(r'\*+\s*(\d+)\s*\*+', line)
            if match:
                sira_no = int(match.group(1))
                print(f"DEBUG: Sıra numarası bulundu: {sira_no} - Line: {line.strip()}")
                break
        
        # Eğer bulunamazsa varsayılan değer
        if sira_no is None:
            sira_no = 0
            print(f"DEBUG: Sıra numarası bulunamadı, varsayılan 0 atandı")
        
        # Boyut tanımını bul
        for line in lines:
            match = self.pattern_dim.search(line)
            if match:
                boyut_adi = match.group(1)
                aciklama = match.group(2).strip()
                print(f"DEBUG: Boyut bulundu: {boyut_adi} - {aciklama}")
                break
        
        # Veri satırlarını parse et - ESKİ YÖNTEMİ KORU
        for line in lines:
            # Position ölçümü için özel durum (X, Y, TP gibi)
            if any(keyword in line for keyword in ['POSITION', 'TRUE POSITION', 'TP']):
                position_measurements = self._parse_position_measurement(line, operasyon, sira_no, boyut_adi, aciklama)
                measurements.extend(position_measurements)
            else:
                # Normal ölçüm
                measurement = self._parse_single_measurement(line, operasyon, sira_no, boyut_adi, aciklama)
                if measurement:
                    measurements.append(measurement)
        
        print(f"DEBUG: Blok tamamlandı, toplam ölçüm: {len(measurements)}")
        return measurements
    
    def _parse_single_measurement(self, line: str, operasyon: str, sira_no: int, 
                                 boyut_adi: str, aciklama: str) -> Optional[CMMOlcum]:
        """Tek bir ölçüm satırını parse eder"""
        # Veri satırı pattern'i
        pattern = r'(\w+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
        match = re.search(pattern, line)
        
        if not match:
            return None
        
        try:
            eksen = match.group(1)
            nominal = float(match.group(2))
            olculen = float(match.group(3))
            pos_tol = float(match.group(4))
            neg_tol = float(match.group(5))
            sapma = float(match.group(6))
            tolerans_disi = float(match.group(7))
            
            # Durum belirleme
            durum = "✓" if tolerans_disi == 0.0 else "⚠"
            
            return CMMOlcum(
                operasyon=operasyon,
                sira_no=sira_no,
                boyut_adi=boyut_adi,
                aciklama=aciklama,
                eksen=eksen,
                nominal=nominal,
                olculen=olculen,
                pos_tolerans=pos_tol,
                neg_tolerans=neg_tol,
                sapma=sapma,
                tolerans_disi=tolerans_disi,
                durum=durum
            )
        except (ValueError, IndexError) as e:
            print(f"Veri parse hatası: {e}")
            return None
    
    def _parse_position_measurement(self, line: str, operasyon: str, sira_no: int, 
                                   boyut_adi: str, aciklama: str) -> List[CMMOlcum]:
        """Position ölçümlerini parse eder (X, Y, TP ayrı ayrı)"""
        measurements = []
        
        # Position parsing - DF satırını da ekle
        if line.strip().startswith(('X ', 'Y ', 'TP ', 'DF ')):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    eksen = parts[0]
                    
                    # Nominal değer
                    nominal_str = parts[1]
                    if nominal_str == "RFS":
                        nominal = 0.0
                    else:
                        nominal = float(nominal_str)
                    
                    olculen = float(parts[2])
                    
                    # Sapma değerini bul (DEV sütunu genelde sona doğru)
                    pos_tol = None
                    neg_tol = None
                    sapma = 0.0
                    tolerans_disi = 0.0
                    
                    # Tolerans değerleri varsa al
                    if len(parts) >= 5:
                        try:
                            pos_tol = float(parts[3]) if parts[3] != '' else None
                            neg_tol = float(parts[4]) if parts[4] != '' else None
                        except (ValueError, IndexError):
                            pass
                    
                    # Sapma değerini bul (negatif sayılar da olabilir)
                    for i in range(3, len(parts)):
                        try:
                            val = float(parts[i])
                            # Sapma genelde küçük değer (-0.034, 0.023 gibi)
                            if abs(val) < 10 and val != nominal and val != olculen:
                                sapma = val
                                break
                        except ValueError:
                            continue
                    
                    durum = "✓"  # Position ölçümleri genelde başarılı
                    
                    # Boyut adını eksen ile birleştir
                    boyut_tam_adi = f"{boyut_adi}_{eksen}" if boyut_adi else f"POS_{eksen}"
                    aciklama_detay = f"{aciklama} ({eksen})" if aciklama else f"Position {eksen}"
                    
                    measurement = CMMOlcum(
                        operasyon=operasyon,
                        sira_no=sira_no,
                        boyut_adi=boyut_tam_adi,
                        aciklama=aciklama_detay,
                        eksen=eksen,
                        nominal=nominal,
                        olculen=olculen,
                        pos_tolerans=pos_tol,
                        neg_tolerans=neg_tol,
                        sapma=sapma,
                        tolerans_disi=tolerans_disi,
                        durum=durum
                    )
                    measurements.append(measurement)
                    
                except (ValueError, IndexError) as e:
                    print(f"Position parse hatası (atlanıyor): {e}")
        
        return measurements
    
    def parse_file(self, file_path: str) -> List[CMMOlcum]:
        """Tek bir CMM dosyasını parse eder"""
        measurements = []
        
        # Dosya adından operasyon belirle
        filename = Path(file_path).stem
        if '1OP' in filename:
            operasyon = '1OP'
        elif '2OP' in filename:
            operasyon = '2OP'
        else:
            operasyon = 'UNKNOWN'
        
        print(f"DEBUG: İşlenen dosya: {filename}, Operasyon: {operasyon}")
        
        # RTF text'i çıkar
        text = self.extract_rtf_text(file_path)
        if not text:
            return measurements
        
        # Sıra numarası pattern'leri bul
        sira_pattern = r'\*+\s*(\d+)\s*\*+'
        sira_matches = list(re.finditer(sira_pattern, text))
        
        print(f"DEBUG: Bulunan sıra numaraları: {[int(m.group(1)) for m in sira_matches]}")
        
        # Her sıra numarası için bloğu çıkar
        for i, match in enumerate(sira_matches):
            sira_no = int(match.group(1))
            
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
                print(f"DEBUG: Sıra {sira_no} işleniyor, blok uzunluğu: {len(block_text)}")
                block_measurements = self.parse_measurement_block_simple(block_text, operasyon, sira_no)
                measurements.extend(block_measurements)
                print(f"DEBUG: Sıra {sira_no} tamamlandı, ölçüm sayısı: {len(block_measurements)}")
        
        print(f"DEBUG: Toplam ölçüm sayısı: {len(measurements)}")
        return measurements
    
    def parse_measurement_block_simple(self, block: str, operasyon: str, sira_no: int) -> List[CMMOlcum]:
        """Basitleştirilmiş blok parser"""
        measurements = []
        lines = block.split('\n')
        
        current_dim = None
        current_desc = None
        
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
                continue
            
            # Veri satırları (D, R, M, X, Y, TP, DF ile başlayanlar)
            if re.match(r'^[DRMXYTP]F?\s+', line):
                measurement = self._parse_data_line(line, operasyon, sira_no, current_dim, current_desc)
                if measurement:
                    measurements.append(measurement)
                    print(f"DEBUG: Ölçüm eklendi: {measurement.boyut_adi}_{measurement.eksen}")
        
        return measurements
    
    def _parse_data_line(self, line: str, operasyon: str, sira_no: int, dim_name: str, description: str) -> Optional[CMMOlcum]:
        """Tek bir veri satırını parse eder"""
        parts = line.split()
        if len(parts) < 3:
            return None
        
        try:
            eksen = parts[0]
            
            # Nominal
            nominal_str = parts[1]
            if nominal_str == "RFS":
                nominal = 0.0
            else:
                nominal = float(nominal_str)
            
            # Ölçülen
            olculen = float(parts[2])
            
            # Toleranslar (varsa)
            pos_tol = None
            neg_tol = None
            if len(parts) >= 5:
                try:
                    pos_tol = float(parts[3]) if parts[3] != '' else None
                    neg_tol = float(parts[4]) if parts[4] != '' else None
                except ValueError:
                    pass
            
            # Sapma (DEV sütunu - genelde sonlarda)
            sapma = 0.0
            tolerans_disi = 0.0
            
            # DEV ve OUTTOL değerlerini bul
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
                if eksen in ['X', 'Y', 'TP', 'DF']:
                    boyut_adi = f"{dim_name}_{eksen}"
                    aciklama = f"{description} ({eksen})"
                else:
                    boyut_adi = dim_name
                    aciklama = description
            else:
                boyut_adi = f"DIM{sira_no}"
                aciklama = "Bilinmeyen ölçüm"
            
            return CMMOlcum(
                operasyon=operasyon,
                sira_no=sira_no,
                boyut_adi=boyut_adi,
                aciklama=aciklama,
                eksen=eksen,
                nominal=nominal,
                olculen=olculen,
                pos_tolerans=pos_tol,
                neg_tolerans=neg_tol,
                sapma=sapma,
                tolerans_disi=tolerans_disi,
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
                'Durum': m.durum
            })
        
        df = pd.DataFrame(data)
        
        # Duplicate satırları kaldır
        df = df.drop_duplicates()
        
        # Operasyon ve ölçüm numarasına göre sırala
        # 1OP -> 1, 2OP -> 2 şeklinde sıralama
        op_mapping = {'1OP': 1, '2OP': 2, 'UNKNOWN': 3}
        df['op_order'] = df['Operasyon'].map(op_mapping)
        
        # Sıralama: Operasyon önce, sonra ölçüm no
        df = df.sort_values(['op_order', 'Ölçüm No', 'Boyut Adı'], ascending=[True, True, True])
        
        # Geçici sütunu kaldır ve index sıfırla
        df = df.drop('op_order', axis=1).reset_index(drop=True)
        
        print(f"DEBUG: DataFrame oluşturuldu, {len(df)} satır")
        print(f"DEBUG: Operasyonlar: {df['Operasyon'].unique()}")
        print(f"DEBUG: Ölçüm numaraları: {sorted(df['Ölçüm No'].unique())}")
        
        return df
    
    def export_to_excel(self, measurements: List[CMMOlcum], output_path: str) -> bool:
        """Excel dosyası oluşturur"""
        try:
            df = self.to_dataframe(measurements)
            
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
                
                # Sütun genişliklerini ayarla
                worksheet.set_column('A:A', 12)  # Operasyon
                worksheet.set_column('B:B', 10)  # Ölçüm No
                worksheet.set_column('C:C', 15)  # Boyut Adı
                worksheet.set_column('D:D', 35)  # Açıklama (genişletildi)
                worksheet.set_column('E:E', 8)   # Eksen
                worksheet.set_column('F:N', 12)  # Sayısal değerler
                
                # Header formatını uygula
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Durum sütununa göre renklendirme
                for row_num in range(1, len(df) + 1):
                    durum = df.iloc[row_num-1]['Durum']
                    format_to_use = good_format if durum == '✓' else warning_format
                    worksheet.write(row_num, len(df.columns)-1, durum, format_to_use)
                
                # Özet sayfa ekle
                self._add_summary_sheet(writer, df, workbook)
            
            return True
            
        except Exception as e:
            print(f"Excel export hatası: {e}")
            return False
    
    def export_cleaned_data_to_excel(self, cleaned_data: List[Dict], output_path: str) -> bool:
        """Temizlenmiş JSON verisini Excel'e dönüştürür"""
        try:
            # Dict'ten DataFrame oluştur
            df = pd.DataFrame(cleaned_data)
            
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
                'durum': 'Durum'
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
                
                # Durum sütununa göre renklendirme
                durum_col = df.columns.get_loc('Durum')
                for row_num in range(1, len(df) + 1):
                    durum = df.iloc[row_num-1]['Durum']
                    format_to_use = good_format if durum == '✓' else warning_format
                    worksheet.write(row_num, durum_col, durum, format_to_use)
                
                # Özet sayfa ekle
                self._add_summary_sheet_from_dict(writer, df, workbook)
            
            print(f"💾 Excel dosyası oluşturuldu: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel export hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_summary_sheet_from_dict(self, writer, df: pd.DataFrame, workbook):
        """Dict verisinden özet sayfası ekler"""
        summary_data = {
            'Metrik': [
                'Toplam Ölçüm',
                'Başarılı Ölçüm',
                'Uyarı Gerekli',
                'Operasyon 1OP',
                'Operasyon 2OP',
                'Farklı Ölçüm Numarası'
            ],
            'Değer': [
                len(df),
                len(df[df['Durum'] == '✓']),
                len(df[df['Durum'] == '⚠']),
                len(df[df['Operasyon'] == '1OP']),
                len(df[df['Operasyon'] == '2OP']),
                len(df['Ölçüm No'].unique())
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Özet', index=False)
        
        # Özet sayfası formatlaması
        summary_ws = writer.sheets['Özet']
        summary_ws.set_column('A:A', 20)
        summary_ws.set_column('B:B', 15)

def process_cmm_files(file_paths: List[str], output_excel_path: str = None) -> Dict[str, Any]:
    """Ana işleme fonksiyonu - JSON ile veri temizleme"""
    import json
    import tempfile
    
    try:
        # Parser ve exporter oluştur
        parser = CMMParser()
        exporter = CMMExcelExporter()
        
        # Dosyaları parse et
        print("📄 CMM dosyaları işleniyor...")
        measurements = parser.parse_multiple_files(file_paths)
        
        if not measurements:
            return {
                'success': False,
                'error': 'Hiçbir ölçüm verisi bulunamadı',
                'count': 0
            }
        
        # JSON'a dönüştür ve geçici dosyaya kaydet
        temp_json = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_json_path = temp_json.name
        
        # Measurement'ları dict'e dönüştür
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
                'durum': m.durum
            })
        
        # JSON'a kaydet
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(measurements_data, f, indent=2, ensure_ascii=False)
        
        print(f"📋 JSON oluşturuldu: {len(measurements_data)} ham ölçüm")
        
        # JSON'dan temiz veri oluştur
        cleaned_data = clean_and_sort_data(temp_json_path)
        print(f"🧹 Veri temizlendi: {len(cleaned_data)} temiz ölçüm")
        
        # Operations listesini cleaned_data'dan al
        operations = list(set(item['operasyon'] for item in cleaned_data))
        
        # Eğer output_excel_path verilmemişse otomatik oluştur
        if not output_excel_path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_count = len(file_paths)
            ops_str = "_".join(sorted(operations)) if operations else "mixed"
            output_excel_path = f"cmm_raporu_{file_count}dosya_{ops_str}_{timestamp}.xlsx"
        
        # Temiz verileri kullanarak Excel oluştur
        success = exporter.export_cleaned_data_to_excel(cleaned_data, output_excel_path)
        
        # Operations listesini cleaned_data'dan al
        operations = list(set(item['operasyon'] for item in cleaned_data))
        
        # Geçici JSON dosyasını sil
        try:
            os.unlink(temp_json_path)
            print(f"🗑️ Geçici JSON silindi: {temp_json_path}")
        except Exception as e:
            print(f"⚠️ Geçici JSON silinemedi: {e}")
        
        if success:
            return {
                'success': True,
                'count': len(cleaned_data),
                'operations': operations,
                'excel_path': output_excel_path,
                'filename': os.path.basename(output_excel_path)
            }
        else:
            return {
                'success': False,
                'error': 'Excel dosyası oluşturulamadı',
                'count': len(cleaned_data)
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'count': 0
        }

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
            item['olculen']
        )
        
        if key not in seen:
            seen.add(key)
            cleaned.append(item)
        else:
            duplicates_removed += 1
    
    print(f"🗑️ {duplicates_removed} duplikat kayıt kaldırıldı")
    
    # SADECE ölçüm numarasına göre sırala (operasyon fark etmez)
    cleaned.sort(key=lambda x: x['sira_no'])
    
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