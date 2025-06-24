// src/pages/dashboard/DashboardPage.tsx - Multiple Excel Export entegrasyonu
import React, { useState, useRef } from "react";
import { DashboardPageStyles } from "./DashboardPage.styles";
import { useFileUpload } from "../../hooks/useFileUpload";
import { Image } from "primereact/image";
import { apiService } from "../../services/api";

export const DashboardPage = () => {
  const classes = DashboardPageStyles();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  
  // Excel merge state
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [mergeProgress, setMergeProgress] = useState(0);
  
  // ✅ YENİ - Excel export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  
  const {
    files,
    isUploading,
    totalProcessingTime,
    addFiles,
    removeFile,
    clearFiles,
    uploadAndAnalyze,
    retryFile,
    exportMultipleToExcel, // ✅ YENİ - Çoklu export fonksiyonu
    exportAllCompletedToExcel, // ✅ YENİ - Otomatik tüm analizleri export
  } = useFileUpload();

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    // Reset input
    event.target.value = '';
  };

  // ✅ Excel dosya seçimi
  const handleExcelFileSelect = () => {
    excelInputRef.current?.click();
  };

  const handleExcelFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Excel dosya tipini kontrol et
      const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
        'application/vnd.ms-excel', // .xls
        'application/excel'
      ];
      
      if (validTypes.includes(file.type) || file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) {
        setSelectedExcelFile(file);
        console.log('✅ Excel dosyası seçildi:', file.name);
      } else {
        alert('Lütfen geçerli bir Excel dosyası (.xlsx, .xls) seçin.');
      }
    }
    // Reset input
    event.target.value = '';
  };

  // ✅ Excel merge işlemi
  const handleExcelMerge = async () => {
    if (!selectedExcelFile) {
      alert('Lütfen önce bir Excel dosyası seçin.');
      return;
    }

    // Tamamlanmış analizleri bul
    const completedAnalyses = files.filter(f => 
      f.status === 'completed' && 
      f.result?.analysis?.id
    );

    if (completedAnalyses.length === 0) {
      alert('Birleştirilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin.');
      return;
    }

    setIsMerging(true);
    setMergeProgress(10);

    try {
      console.log('📊 Excel merge başlıyor...', {
        excelFile: selectedExcelFile.name,
        analysisCount: completedAnalyses.length
      });

      // Analysis ID'lerini topla
      const analysisIds = completedAnalyses.map(f => f.result!.analysis.id);

      setMergeProgress(30);

      // API çağrısı
      const result = await apiService.mergeWithExcel(selectedExcelFile, analysisIds);

      setMergeProgress(80);

      if (result.success) {
        // Başarılı - dosyayı indir
        console.log('✅ Excel merge başarılı');
        
        // Blob olarak dönen dosyayı indir
        const url = window.URL.createObjectURL(result.blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = result.filename || `merged_excel_${Date.now()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        setMergeProgress(100);
        
        // Başarı mesajı
        setTimeout(() => {
          alert('✅ Excel dosyası başarıyla birleştirildi ve indirildi!');
          setSelectedExcelFile(null);
          setMergeProgress(0);
          setIsMerging(false);
        }, 500);

      } else {
        throw new Error(result.message || 'Excel birleştirme başarısız');
      }

    } catch (error: any) {
      console.error('❌ Excel merge hatası:', error);
      alert(`Excel birleştirme hatası: ${error.message || 'Bilinmeyen hata'}`);
      setMergeProgress(0);
      setIsMerging(false);
    }
  };

  // ✅ Excel dosyasını kaldır
  const removeExcelFile = () => {
    setSelectedExcelFile(null);
  };

  // ✅ YENİ - Multiple Excel Export işlemi
  const handleMultipleExcelExport = async () => {
    const completedFiles = files.filter(f => 
      f.status === 'completed' && 
      f.result?.analysis?.id
    );

    if (completedFiles.length === 0) {
      alert('Export edilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin.');
      return;
    }

    setIsExporting(true);
    setExportProgress(10);

    try {
      console.log('📊 Multiple Excel export başlıyor...', {
        analysisCount: completedFiles.length,
        fileNames: completedFiles.map(f => f.file.name)
      });

      setExportProgress(30);

      // Export fonksiyonunu çağır
      const result = await exportAllCompletedToExcel();

      setExportProgress(80);

      if (result.success) {
        console.log('✅ Multiple Excel export başarılı:', result.filename);
        
        setExportProgress(100);
        
        // Başarı mesajı
        setTimeout(() => {
          alert(`✅ ${completedFiles.length} analiz başarıyla Excel'e aktarıldı ve indirildi!\n\nDosya: ${result.filename}`);
          setExportProgress(0);
          setIsExporting(false);
        }, 500);

      } else {
        throw new Error(result.error || 'Excel export başarısız');
      }

    } catch (error: any) {
      console.error('❌ Multiple Excel export hatası:', error);
      alert(`Excel export hatası: ${error.message || 'Bilinmeyen hata'}`);
      setExportProgress(0);
      setIsExporting(false);
    }
  };

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedItems(newExpanded);
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      case 'analyzing':
      case 'uploading':
        return 'blue';
      default:
        return 'yellow';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Bekliyor';
      case 'uploading':
        return 'Yükleniyor...';
      case 'uploaded':
        return 'Yüklendi';
      case 'analyzing':
        return 'Analiz ediliyor...';
      case 'completed':
        return 'Tamamlandı';
      case 'failed':
        return 'Başarısız';
      default:
        return 'Bilinmiyor';
    }
  };

  const accessToken = localStorage.getItem('accessToken');

  // 3D Model görüntüleme - Backend'deki HTML dosyasını aç
  const open3DViewer = (analysisId: string, fileName: string) => {
    // Backend'deki 3D viewer HTML dosyasını yeni sekmede aç
    const viewerUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:5050'}/3d-viewer/${analysisId}/${accessToken}`;
    window.open(viewerUrl, '_blank', 'width=1600,height=1200,scrollbars=yes,resizable=yes');
  };

  // STL dosyasını direkt görüntüle
  const openSTLViewer = (analysisId: string, fileName: string) => {
    // Backend'deki STL viewer HTML dosyasını aç
    const stlViewerUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:5050'}/static/stepviews/${analysisId}/viewer.html`;
    window.open(stlViewerUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
  };

  const renderAnalysisResults = (file: any, index: number) => {
    if (!file.result?.analysis) return null;

    const analysis = file.result.analysis;
    const stepAnalysis = analysis.step_analysis;
    const materialOptions = analysis.material_options || [];
    const materialCalculations = analysis.all_material_calculations || [];

    return (
      <div className={classes.analyseItemInsideDiv}>
        <div className={classes.analyseFirstDiv}>
          <p className={classes.analyseAlias}>
            {analysis.material_matches?.[0] || '6061(alias:6061, %100)'}
          </p>
          <div className={classes.modelDiv}>
            <div className={classes.modelSection}>
              {analysis.enhanced_renders?.isometric ? (
                <Image
                  src={`${process.env.REACT_APP_API_URL || 'http://localhost:5050'}/${analysis.enhanced_renders.isometric.file_path}`}
                  zoomSrc={`${process.env.REACT_APP_API_URL || 'http://localhost:5050'}/${analysis.enhanced_renders.isometric.file_path}`}
                  className={classes.modelImage}
                  alt="3D Model"
                  width="200"
                  height="200"
                  preview 
                />
              ) : (
                <div style={{ color: '#999', textAlign: 'center' }}>
                  3D Model
                  <br />
                  Mevcut Değil
                </div>
              )}
            </div>
            
            {/* 3D Viewer Butonları */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <button 
                className={classes.modelShowButton}
                onClick={() => open3DViewer(analysis.id, file.file.name)}
                title="Gelişmiş 3D Viewer'da aç"
              >
                🎯 3D Model Viewer
              </button>
            </div>
          </div>
        </div>

        <div className={classes.line}></div>

        <p className={classes.titleSmall}>Step Dosyası Detaylı Analiz Tablosu</p>

        {/* Boyutlar */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>📐</span>
            <p className={classes.titleSmall}>Boyutlar</p>
          </div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>X(mm)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['X (mm)'] || '0.0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Y(mm)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Y (mm)'] || '0.0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Z(mm)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Z (mm)'] || '0.0'}</p>
          </div>
        </div>

        {/* Silindirik Özellikler */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>🌀</span>
            <p className={classes.titleSmall}>Silindirik Özellikler</p>
          </div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Silindirik Çap(mm)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Silindirik Çap (mm)'] || '0.0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Silindirik Yükseklik(mm)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Silindirik Yükseklik (mm)'] || '0.0'}</p>
          </div>
        </div>

        {/* Hacimsel Veriler */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>📦</span>
            <p className={classes.titleSmall}>Hacimsel Veriler</p>
          </div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Prizma Hacmi 10 mm Paylı(mm³)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Prizma Hacmi (mm³)'] || '0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Ürün Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Ürün Hacmi (mm³)'] || '0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Talaş Hacmi (mm³)'] || '0'}</p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Oranı(%)</p>
            <p className={classes.analyseItemExp}>{stepAnalysis?.['Talaş Oranı (%)'] || '0.0'}</p>
          </div>
        </div>

        {/* Step Dosyası Metadata */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>📋</span>
            <p className={classes.titleSmall}>Step Dosyası Metadata</p>
          </div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Malzeme Bilgisi</p>
            <p className={classes.analyseItemExp}>
              {analysis.material_matches?.length > 0 
                ? analysis.material_matches[0] 
                : 'Malzeme bilgisi step dosyasında bulunmuyor.'}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>
          
          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Not</p>
            <p className={classes.analyseItemExp}>
              Not bilgisi step dosyasında bulunmuyor.
            </p>
          </div>
        </div>

        {/* Hesaplaşmaya Esas Değerler */}
        {materialCalculations.length > 0 && (
          <div className={classes.analyseItemInsideDiv}>
            <div className={classes.analyseSubtitleDiv}>
              <span>⚙️</span>
              <p className={classes.titleSmall}>Hesaplaşmaya Esas Değerler</p>
            </div>
            
            {materialCalculations.map((calc: any, idx: any) => (
              
              <React.Fragment key={idx}>
                <div className={classes.analyseInsideItem} style={{backgroundColor: '#f8f9fa', paddingTop: '20px', paddingBottom: '20px'}}>
                  <p>{calc.category ? `Malzeme: ${calc.original_text}` : 'Malzeme bilgisi mevcut değil.'}</p>
                </div>
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Prizma Hacmi(mm³)</p>
                  <p className={classes.analyseItemExp}>{calc.volume_mm3}</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>
                
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Özkütle(g/cm³)({calc.material})</p>
                  <p className={classes.analyseItemExp}>{calc.density}</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>
                
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Kütle(kg)</p>
                  <p className={classes.analyseItemExp}>{calc.mass_kg}</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>
                
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Hammadde Maliyeti</p>
                  <p className={classes.analyseItemExp}>{calc.material_cost} USD</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>
                
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Toplam Yüzey Alanı</p>
                  <p className={classes.analyseItemExp}>
                    {stepAnalysis?.['Toplam Yüzey Alanı (mm²)'] || '0'} mm²
                  </p>
                </div>
                {idx < materialCalculations.length - 1 && <div className={classes.lineAnalyseItem}></div>}
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Tüm Malzemeler İçin Hesaplanan Değerler */}
        {materialOptions.length > 0 && (
          <>
            <p className={classes.titleSmall}>Tüm Malzemeler İçin Hesaplanan Değerler</p>
            
            <div className={classes.analyseItemInsideDiv}>
              <div className={classes.analyseMaterialDiv}>
                <p className={classes.materialTitle}>Malzeme</p>
                <p className={classes.materialTitle}>Özkütle(g/cm³)</p>
                <p className={classes.materialTitle}>Kütle(kg)</p>
                <p className={classes.materialTitle}>Maliyet(USD)</p>
              </div>
              
              {materialOptions.slice(0, 10).map((material: any, idx: any) => (
                <React.Fragment key={idx}>
                  <div className={classes.analyseMaterialExpDiv}>
                    <p className={classes.materialExp}>{material.name}</p>
                    <p className={classes.materialExp}>{material.density}</p>
                    <p className={classes.materialExp}>{material.mass_kg}</p>
                    <p className={classes.materialExp}>{material.material_cost}</p>
                  </div>
                  {idx < materialOptions.slice(0, 10).length - 1 && (
                    <div className={classes.lineAnalyseItem}></div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className={classes.container}>
      <div className={classes.firstSection}>
        <img
          src="/background-logo.png"
          alt="Background Logo"
          className={classes.backgroundLogo}
        />
        <p className={classes.title}>
          Yapay Zeka ile Teklif Parametrelerinin PDF ve STEP Dosyalarından Analizi
        </p>
        <p className={classes.exp}>
          İşlem sonucunda teklif verilecek ürüne ait tüm analizler tamamlanacak,
          değerler hesaplanacak, 3D modeli görüntülenebilir duruma gelecek ve
          sonuçlar excel olarak indirilebilecektir. <br />
          <span>
            Step dosyasını ayrıca yüklemenize gerek yok. Sistem PDF'in içinden
            dosyayı otomatik bulup işlem yapar.
          </span>
        </p>

        <div className={classes.uploadSection}>
          <div className={classes.fileSelection}>
            <button 
              className={classes.fileSelectionButton}
              onClick={handleFileSelect}
            >
              Choose Files
            </button>
            <span className={classes.fileIcon}>📁</span>
            <p className={classes.fileSelectionText}>
              {files.length === 0 
                ? 'No files selected' 
                : `${files.length} file${files.length > 1 ? 's' : ''} selected`
              }
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.step,.stp"
            onChange={handleFileChange}
            className={classes.hiddenFileInput}
          />

          <button 
            className={classes.uploadButton}
            onClick={uploadAndAnalyze}
            disabled={files.length === 0 || isUploading || !files.some(f => f.status === 'pending')}
          >
            {isUploading 
              ? 'Yükleniyor ve Analiz Ediliyor...' 
              : files.some(f => f.status === 'pending')
                ? `Yükle ve Tara (${files.filter(f => f.status === 'pending').length} dosya)`
                : 'Tüm Dosyalar İşlendi'
            }
          </button>

          {(isUploading || files.some(f => f.status === 'pending')) && (
            <p className={classes.processingInfo}>
              {isUploading 
                ? `${files.filter(f => f.status === 'uploading' || f.status === 'analyzing').length} dosya işleniyor, lütfen bekleyin...`
                : `${files.filter(f => f.status === 'pending').length} dosya işlenmeyi bekliyor`
              }
            </p>
          )}

          {/* Uploaded Files */}
          {files.map((file, index) => (
            <div key={index} className={classes.uploadedItem}>
              <div className={classes.uploadedItemFirstSection}>
                <p className={classes.exp}>{file.file.name}</p>
                <div className={`${classes.uploadedItemStatus} ${getStatusClass(file.status)}`}>
                  <p className={classes.uploadedItemStatusText}>
                    {getStatusText(file.status)}
                  </p>
                </div>
              </div>

              <div className={classes.progressContainer}>
                <div 
                  className={classes.progressBar}
                  style={{ width: `${file.progress}%` }}
                >
                  <span className={classes.progressText}>{file.progress}%</span>
                </div>
              </div>

              {file.error && (
                <div style={{ color: '#dc3545', fontSize: '12px', marginTop: '8px' }}>
                  Hata: {file.error}
                  <button 
                    className={classes.retryButton}
                    onClick={() => retryFile(index)}
                    style={{ marginLeft: '10px' }}
                    disabled={isUploading}
                  >
                    Tekrar Dene
                  </button>
                  <button 
                    onClick={() => removeFile(index)}
                    style={{ 
                      marginLeft: '8px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px'
                    }}
                  >
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === 'pending' && (
                <div style={{ fontSize: '12px', marginTop: '8px', color: '#6c757d' }}>
                  Dosya analiz için hazır. "Yükle ve Tara" butonuna tıklayın.
                  <button 
                    onClick={() => removeFile(index)}
                    style={{ 
                      marginLeft: '10px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px'
                    }}
                  >
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === 'completed' && (
                <div style={{ fontSize: '12px', marginTop: '8px', color: '#28a745' }}>
                  ✓ Analiz tamamlandı! İşleme süresi: {file.result?.processing_time?.toFixed(1) || '0'} saniye
                </div>
              )}
            </div>
          ))}

          {/* Analysis Results */}
          {files.some(f => f.status === 'completed') && (
            <>
              <div className={classes.line}></div>
              
              <div className={classes.analyseSection}>
                <div className={classes.iconTextDiv}>
                  <span>🕒</span>
                  <p className={classes.titleSmall}>
                    Toplam geçen süre: {totalProcessingTime.toFixed(1)} saniye
                  </p>
                </div>

                <div className={classes.iconTextDiv}>
                  <span>📊</span>
                  <p className={classes.title}>Analiz Sonuçları</p>
                </div>

                {files.map((file, index) => (
                  file.status === 'completed' && (
                    <div 
                      key={index} 
                      className={`${classes.analyseItem} ${expandedItems.has(index) ? 'active' : ''}`}
                    >
                      <div 
                        className={classes.analyseFirstSection}
                        onClick={() => toggleExpanded(index)}
                      >
                        <p className={classes.exp}>{file.file.name}</p>
                        <span style={{ transform: expandedItems.has(index) ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }}>
                          <i className="fa fa-arrow-down"></i>
                        </span>
                      </div>
                      
                      {expandedItems.has(index) && renderAnalysisResults(file, index)}
                    </div>
                  )
                ))}

                {/* ✅ YENİ - Multiple Excel Export Butonu */}
                <div style={{ position: 'relative', width: '100%' }}>
                  {/* Export progress */}
                  {isExporting && (
                    <div style={{ marginBottom: '10px' }}>
                      <div style={{ backgroundColor: '#f0f0f0', borderRadius: '4px', overflow: 'hidden' }}>
                        <div 
                          style={{ 
                            width: `${exportProgress}%`, 
                            height: '20px', 
                            backgroundColor: '#28a745', 
                            transition: 'width 0.3s ease',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: '12px'
                          }}
                        >
                          {exportProgress}%
                        </div>
                      </div>
                      <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                        Excel dosyası oluşturuluyor...
                      </p>
                    </div>
                  )}

                  <button 
                    className={classes.analyseButton}
                    onClick={handleMultipleExcelExport}
                    disabled={!files.some(f => f.status === 'completed') || isExporting}
                    style={{
                      backgroundColor: isExporting ? '#cccccc' : '#10b86b',
                      cursor: isExporting ? 'not-allowed' : 'pointer',
                      opacity: isExporting ? 0.7 : 1
                    }}
                  >
                    <img src="/download-icon.svg" alt="" />
                    {isExporting 
                      ? 'Excel Oluşturuluyor...' 
                      : `Excel İndir (${files.filter(f => f.status === 'completed').length} Analiz)`
                    }
                  </button>

                  {/* Bilgi mesajı */}
                  {files.some(f => f.status === 'completed') && !isExporting && (
                    <div style={{ 
                      fontSize: '12px', 
                      color: '#666', 
                      marginTop: '10px',
                      padding: '8px',
                      backgroundColor: '#e8f5e8',
                      borderRadius: '4px',
                      border: '1px solid #c3e6c3'
                    }}>
                      📊 <strong>Çoklu Excel Export:</strong> Tüm tamamlanmış analizler tek Excel dosyasında birleştirilecek. 
                      Her analiz için ayrı satır oluşturulacak ve 3D görseller dahil edilecek.
                      <br />
                      <strong>İndirilecek {files.filter(f => f.status === 'completed').length} analiz sonucu mevcut.</strong>
                    </div>
                  )}
                </div>

                <div className={classes.line}></div>

                {/* Excel Merge Bölümü */}
                <div className={classes.iconTextDiv}>
                  <span>📤</span>
                  <p className={classes.title}>Excel Yükle ve Analiz Sonuçlarıyla Birleştir</p>
                </div>

                {/* Excel dosya seçimi */}
                <div className={classes.fileSelection}>
                  <button 
                    className={classes.fileSelectionButton}
                    onClick={handleExcelFileSelect}
                    disabled={isMerging}
                  >
                    Choose File
                  </button>
                  <span className={classes.fileIcon}>📊</span>
                  <p className={classes.fileSelectionText}>
                    {selectedExcelFile ? selectedExcelFile.name : 'no file selected'}
                  </p>
                  {selectedExcelFile && (
                    <button 
                      onClick={removeExcelFile}
                      style={{ 
                        marginLeft: '10px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '11px'
                      }}
                      disabled={isMerging}
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Excel input (hidden) */}
                <input
                  ref={excelInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleExcelFileChange}
                  style={{ display: 'none' }}
                />

                {/* Excel merge progress */}
                {isMerging && (
                  <div style={{ marginTop: '10px', marginBottom: '10px' }}>
                    <div style={{ backgroundColor: '#f0f0f0', borderRadius: '4px', overflow: 'hidden' }}>
                      <div 
                        style={{ 
                          width: `${mergeProgress}%`, 
                          height: '20px', 
                          backgroundColor: '#28a745', 
                          transition: 'width 0.3s ease',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontSize: '12px'
                        }}
                      >
                        {mergeProgress}%
                      </div>
                    </div>
                    <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                      Excel dosyası birleştiriliyor...
                    </p>
                  </div>
                )}

                {/* Merge butonu */}
                <button 
                  className={classes.excelButton}
                  onClick={handleExcelMerge}
                  disabled={!selectedExcelFile || isMerging || !files.some(f => f.status === 'completed')}
                >
                  <img src="/upload.svg" alt="" />
                  {isMerging 
                    ? 'Birleştiriliyor...' 
                    : 'Excel Dosyasını Yükle ve Birleştir'
                  }
                </button>

                {/* Bilgi mesajı */}
                {files.some(f => f.status === 'completed') && (
                  <div style={{ 
                    fontSize: '12px', 
                    color: '#666', 
                    marginTop: '10px',
                    padding: '8px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    border: '1px solid #dee2e6'
                  }}>
                    💡 <strong>Nasıl çalışır:</strong> Excel dosyanızı seçin ve analiz sonuçlarıyla birleştirin. 
                    Sistem otomatik olarak ürün kodlarını eşleştirip malzeme bilgilerini, boyutları ve 3D görsellerini ekleyecek.
                    <br />
                    <strong>Birleştirilecek {files.filter(f => f.status === 'completed').length} analiz sonucu mevcut.</strong>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};