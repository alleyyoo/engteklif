import React, { useState, useRef, useEffect } from 'react';
import { DashboardPageStyles } from './DashboardPage.styles';
import { useFileUpload } from '../../hooks/useFileUpload';
import { Image } from 'primereact/image';
import { apiService } from '../../services/api';

export const DashboardPage = () => {
  const classes = DashboardPageStyles();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [isDragging, setIsDragging] = useState(false);

  // Excel merge state
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [mergeProgress, setMergeProgress] = useState(0);

  // Excel export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);

  const {
    files,
    fileGroups,
    matchedPairs,
    groupMode,
    setGroupMode,
    isUploading,
    totalProcessingTime,
    renderStatusMap,
    renderProgressMap,
    addFiles,
    removeFile,
    removeGroup,
    clearFiles,
    uploadAndAnalyze,
    retryFile,
    exportMultipleToExcel,
    exportAllCompletedToExcel,
    exportGroupToExcel,
    refreshRenderStatus,
    getFileType
  } = useFileUpload();

  // Grup modunu başlangıçta aktif yap
  useEffect(() => {
    setGroupMode(true);
  }, [setGroupMode]);

  // Drag & Drop handlers
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    const validFiles = droppedFiles.filter((file) => {
      const ext = file.name.toLowerCase();
      return (
        ext.endsWith('.pdf') ||
        ext.endsWith('.doc') ||
        ext.endsWith('.docx') ||
        ext.endsWith('.step') ||
        ext.endsWith('.stp')
      );
    });

    if (validFiles.length > 0) {
      addFiles(validFiles);
    } else if (droppedFiles.length > 0) {
      alert('Lütfen sadece PDF, DOC, DOCX, STEP veya STP dosyaları yükleyin.');
    }
  };

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    event.target.value = '';
  };

  const handleExcelFileSelect = () => {
    excelInputRef.current?.click();
  };

  const handleExcelFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/excel'
      ];

      if (
        validTypes.includes(file.type) ||
        file.name.toLowerCase().endsWith('.xlsx') ||
        file.name.toLowerCase().endsWith('.xls')
      ) {
        setSelectedExcelFile(file);
        console.log('✅ Excel dosyası seçildi:', file.name);
      } else {
        alert('Lütfen geçerli bir Excel dosyası (.xlsx, .xls) seçin.');
      }
    }
    event.target.value = '';
  };

  const handleExcelMerge = async () => {
    if (!selectedExcelFile) {
      alert('Lütfen önce bir Excel dosyası seçin.');
      return;
    }

    let completedAnalyses = [];

    // Tüm tamamlanmış analizleri topla (matchedPairs dahil)
    matchedPairs.forEach((pair) => {
      if (pair.status === 'completed' && pair.mergedResult?.analysis?.id) {
        completedAnalyses.push({
          result: pair.mergedResult
        });
      }
    });

    // Eşleşmeyen dosyaları da ekle
    files.forEach((file) => {
      if (
        file.status === 'completed' &&
        file.result?.analysis?.id &&
        !file.isPartOfMatch
      ) {
        completedAnalyses.push({
          result: file.result
        });
      }
    });

    if (completedAnalyses.length === 0) {
      alert(
        'Birleştirilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin.'
      );
      return;
    }

    setIsMerging(true);
    setMergeProgress(10);

    try {
      console.log('📊 Excel merge başlıyor...', {
        excelFile: selectedExcelFile.name,
        analysisCount: completedAnalyses.length
      });

      const analysisIds = completedAnalyses.map(
        (item) => item.result!.analysis.id
      );

      setMergeProgress(30);

      const result = await apiService.mergeWithExcel(
        selectedExcelFile,
        analysisIds
      );

      setMergeProgress(80);

      if (result.success) {
        console.log('✅ Excel merge başarılı');

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

  const removeExcelFile = () => {
    setSelectedExcelFile(null);
  };

  const handleMultipleExcelExport = async () => {
    const completedCount =
      matchedPairs.filter((p) => p.status === 'completed').length +
      files.filter((f) => f.status === 'completed' && !f.isPartOfMatch).length;

    if (completedCount === 0) {
      alert(
        'Export edilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin.'
      );
      return;
    }

    setIsExporting(true);
    setExportProgress(10);

    try {
      console.log('📊 Multiple Excel export başlıyor...', {
        analysisCount: completedCount
      });

      setExportProgress(30);

      const result = await exportAllCompletedToExcel();

      setExportProgress(80);

      if (result.success) {
        console.log('✅ Multiple Excel export başarılı:', result.filename);

        setExportProgress(100);

        setTimeout(() => {
          alert(
            `✅ ${completedCount} analiz başarıyla Excel'e aktarıldı ve indirildi!\n\nDosya: ${result.filename}`
          );
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

  const handlePairExport = async (pair: any) => {
    if (!pair.mergedResult) {
      alert('Bu eşleştirme için export edilecek veri bulunamadı.');
      return;
    }

    try {
      await exportGroupToExcel(pair);
      alert(
        `✅ "${pair.displayName}" eşleştirmesi başarıyla Excel'e aktarıldı!`
      );
    } catch (error: any) {
      console.error('❌ Eşleştirme Excel export hatası:', error);
      alert(`Excel export hatası: ${error.message || 'Bilinmeyen hata'}`);
    }
  };

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
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
      case 'processing':
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
      case 'processing':
        return 'İşleniyor...';
      case 'completed':
        return 'Tamamlandı';
      case 'failed':
        return 'Başarısız';
      default:
        return 'Bilinmiyor';
    }
  };

  const getFileTypeIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return '📄';
      case 'step':
        return '📐';
      case 'doc':
        return '📝';
      default:
        return '📎';
    }
  };

  const getMatchQualityColor = (quality: string) => {
    switch (quality?.toLowerCase()) {
      case 'excellent':
        return '#28a745';
      case 'good':
        return '#17a2b8';
      case 'fair':
        return '#ffc107';
      case 'poor':
        return '#dc3545';
      default:
        return '#6c757d';
    }
  };

  const accessToken = localStorage.getItem('accessToken');

  const open3DViewer = (analysisId: string, fileName: string) => {
    const viewerUrl = `${
      process.env.REACT_APP_API_URL || 'http://188.132.220.35:5051'
    }/3d-viewer/${analysisId}/${accessToken}`;
    window.open(
      viewerUrl,
      '_blank',
      'width=1600,height=1200,scrollbars=yes,resizable=yes'
    );
  };

  const fixImagePath = (path: string) => {
    if (path.startsWith('../static/')) {
      return path.replace('../static/', '/static/');
    }
    if (!path.startsWith('/static/') && !path.startsWith('http')) {
      return `/static/${path}`;
    }
    return path;
  };

  const renderAnalysisDetails = (result: any, id: string) => {
    if (!result?.analysis) return null;

    const analysis = result.analysis;
    const stepAnalysis = analysis.step_analysis;
    const materialOptions = analysis.material_options || [];
    const materialCalculations = analysis.all_material_calculations || [];

    // Render durumunu kontrol et
    const analysisId = analysis.id;
    const renderStatus =
      renderStatusMap.get(analysisId) || analysis.render_status || 'none';
    const renderProgress = renderProgressMap.get(analysisId) || 0;

    const isRenderProcessing =
      renderStatus === 'processing' || renderStatus === 'pending';
    const isRenderCompleted = renderStatus === 'completed';
    const hasEnhancedRenders =
      analysis.enhanced_renders &&
      Object.keys(analysis.enhanced_renders).length > 0;

    const pendingCount = files.filter((f) => f.status === 'pending').length;

    return (
      <div className={classes.analyseItemInsideDiv}>
        <div className={classes.analyseFirstDiv}>
          <p className={classes.analyseAlias}>
            {(() => {
              const match = analysis.material_matches?.[0];
              return match && !match.includes('default')
                ? match
                : 'Malzeme Eşleşmesi Yok';
            })()}
          </p>
          <div className={classes.modelDiv}>
            <div className={classes.modelSection}>
              {/* Render işleniyor durumu */}
              {isRenderProcessing ? (
                <div
                  style={{
                    color: '#007bff',
                    textAlign: 'center',
                    padding: '20px',
                    backgroundColor: '#f0f8ff',
                    borderRadius: '8px'
                  }}>
                  <div style={{ fontSize: '24px', marginBottom: '10px' }}>
                    ⏳
                  </div>
                  <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                    3D Model İşleniyor
                  </div>
                  <div style={{ fontSize: '12px' }}>
                    {renderProgress > 0 && `İlerleme: ${renderProgress}% - `}
                    Lütfen bekleyin...
                  </div>
                  <button
                    onClick={() => refreshRenderStatus(analysisId)}
                    style={{
                      marginTop: '8px',
                      fontSize: '11px',
                      padding: '4px 8px',
                      border: '1px solid #007bff',
                      borderRadius: '4px',
                      backgroundColor: 'white',
                      color: '#007bff',
                      cursor: 'pointer'
                    }}>
                    🔄 Durumu Kontrol Et
                  </button>
                </div>
              ) : hasEnhancedRenders && analysis.enhanced_renders?.isometric ? (
                <Image
                  src={`${
                    process.env.REACT_APP_API_URL ||
                    'http://188.132.220.35:5051'
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  zoomSrc={`${
                    process.env.REACT_APP_API_URL ||
                    'http://188.132.220.35:5051'
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  className={classes.modelImage}
                  alt='3D Model'
                  width='200'
                  height='200'
                  preview
                />
              ) : isRenderCompleted && !hasEnhancedRenders ? (
                <div
                  style={{
                    color: '#dc3545',
                    textAlign: 'center',
                    padding: '20px',
                    backgroundColor: '#fff5f5',
                    borderRadius: '8px'
                  }}>
                  <div style={{ fontSize: '24px', marginBottom: '10px' }}>
                    ⚠️
                  </div>
                  <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                    3D Model Güncel Değil
                  </div>
                  <div style={{ fontSize: '12px' }}>
                    Render tamamlandı ancak
                    <br />
                    görüntü yüklenemedi
                  </div>
                </div>
              ) : (
                <div style={{ color: '#999', textAlign: 'center' }}>
                  3D Model
                  <br />
                  Mevcut Değil
                </div>
              )}
            </div>

            {/* 3D Viewer Butonları */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                marginTop: '12px'
              }}>
              <button
                className={classes.modelShowButton}
                onClick={() =>
                  open3DViewer(analysis.id, analysis.original_filename || '')
                }
                title="Gelişmiş 3D Görüntüleyici'de aç">
                🎯 3D Modeli Görüntüle
              </button>
            </div>
          </div>
        </div>

        <div className={classes.line}></div>

        <p className={classes.titleSmall}>
          Step Dosyası Detaylı Analiz Tablosu
        </p>

        {/* Boyutlar */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>📐</span>
            <p className={classes.titleSmall}>Boyutlar</p>
          </div>

          <div className={classes.dimensionTable}>
            <div className={classes.tableHeader}>
              <div className={classes.tableCell}>Eksen</div>
              <div className={classes.tableCell}>Boyut (mm)</div>
              <div className={classes.tableCell}>Paylı Boyut (mm)</div>
            </div>

            <div className={classes.tableRow}>
              <div className={classes.tableCell}>X</div>
              <div className={classes.tableCell}>
                {Math.ceil(parseFloat(stepAnalysis?.['X (mm)']) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.['X (mm)']) || 0) + 10)}
              </div>
            </div>

            <div className={classes.tableRow}>
              <div className={classes.tableCell}>Y</div>
              <div className={classes.tableCell}>
                {Math.ceil(parseFloat(stepAnalysis?.['Y (mm)']) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.['Y (mm)']) || 0) + 10)}
              </div>
            </div>

            <div className={classes.tableRow}>
              <div className={classes.tableCell}>Z</div>
              <div className={classes.tableCell}>
                {Math.ceil(parseFloat(stepAnalysis?.['Z (mm)']) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.['Z (mm)']) || 0) + 10)}
              </div>
            </div>
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
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Silindirik Çap (mm)'] || '0.0'}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Silindirik Yükseklik(mm)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Silindirik Yükseklik (mm)'] || '0.0'}
            </p>
          </div>
        </div>

        {/* Hacimsel Veriler */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>📦</span>
            <p className={classes.titleSmall}>Hacimsel Veriler</p>
          </div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>
              Prizma Hacmi 10 mm Paylı(mm³)
            </p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Prizma Hacmi (mm³)'] || '0'}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Ürün Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Ürün Hacmi (mm³)'] || '0'}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Talaş Hacmi (mm³)'] || '0'}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Oranı(%)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.['Talaş Oranı (%)'] || '0.0'}
            </p>
          </div>
        </div>

        {/* Hesaplaşmaya Esas Değerler */}
        {materialCalculations.length > 0 && (
          <div className={classes.analyseItemInsideDiv}>
            <div className={classes.analyseSubtitleDiv}>
              <span>⚙️</span>
              <p className={classes.titleSmall}>Esas Değerler</p>
            </div>

            {materialCalculations.length > 0 && (
              <>
                <div
                  className={classes.analyseInsideItem}
                  style={{
                    backgroundColor: '#f8f9fa',
                    paddingTop: '20px',
                    paddingBottom: '20px'
                  }}>
                  <p>
                    {materialCalculations[0].original_text
                      ? `Malzeme: ${materialCalculations[0].original_text}`
                      : 'Malzeme bilgisi mevcut değil.'}
                  </p>
                </div>
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Prizma Hacmi(mm³)</p>
                  <p className={classes.analyseItemExp}>
                    {materialCalculations[0].volume_mm3}
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>
                    Özkütle(g/cm³)({materialCalculations[0].material})
                  </p>
                  <p className={classes.analyseItemExp}>
                    {materialCalculations[0].density}
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Kütle(kg)</p>
                  <p className={classes.analyseItemExp}>
                    {materialCalculations[0].mass_kg}
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Hammadde Maliyeti</p>
                  <p className={classes.analyseItemExp}>
                    {materialCalculations[0].material_cost} USD
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Toplam Yüzey Alanı</p>
                  <p className={classes.analyseItemExp}>
                    {stepAnalysis?.['Toplam Yüzey Alanı (mm²)'] || '0'} mm²
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tüm Malzemeler İçin Hesaplanan Değerler */}
        {materialOptions.length > 0 && (
          <>
            <p className={classes.titleSmall}>
              Tüm Malzemeler İçin Hesaplanan Değerler
            </p>

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
                    <p className={classes.materialExp}>
                      {material.material_cost}
                    </p>
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

  // Render file list - Eşleşmeleri ve tek dosyaları göster
  const renderFileList = () => {
    return (
      <>
        {/* Eşleşmiş PDF-STEP çiftleri */}
        {matchedPairs.map((pair) => (
          <div
            key={pair.id}
            style={{ marginBottom: '16px' }}>
            <div
              className={classes.uploadedItem}
              style={{ backgroundColor: '#f0f8ff' }}>
              <div className={classes.uploadedItemFirstSection}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}>
                  <span style={{ fontSize: '18px' }}>🔗</span>
                  <div>
                    <p
                      className={classes.exp}
                      style={{ fontWeight: 'bold' }}>
                      {pair.displayName}
                    </p>
                    <p
                      style={{
                        fontSize: '12px',
                        color: '#666',
                        marginTop: '4px'
                      }}>
                      PDF + STEP Eşleştirmesi
                    </p>
                  </div>
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  }}>
                  {/* Match score badge */}
                  <div
                    style={{
                      padding: '4px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      backgroundColor: '#d4edda',
                      color: getMatchQualityColor(pair.matchQuality)
                    }}>
                    🎯 {pair.matchScore}% - {pair.matchQuality}
                  </div>
                  <div
                    className={`${classes.uploadedItemStatus} ${getStatusClass(
                      pair.status
                    )}`}>
                    <p className={classes.uploadedItemStatusText}>
                      {getStatusText(pair.status)}
                    </p>
                  </div>
                </div>
              </div>

              <div className={classes.progressContainer}>
                <div
                  className={classes.progressBar}
                  style={{ width: `${pair.progress}%` }}>
                  <span className={classes.progressText}>{pair.progress}%</span>
                </div>
              </div>

              {/* Eşleşen dosyalar */}
              <div style={{ marginTop: '12px', paddingLeft: '20px' }}>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#666',
                    marginBottom: '8px'
                  }}>
                  <div style={{ marginBottom: '4px' }}>
                    📄 PDF: {pair.pdfFile.file.name}
                    <span
                      style={{
                        marginLeft: '8px',
                        fontSize: '11px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: '#e8f5e8',
                        color: '#2e7d32'
                      }}>
                      {getStatusText(pair.pdfFile.status)}
                    </span>
                  </div>
                  <div>
                    📐 STEP: {pair.stepFile.file.name}
                    <span
                      style={{
                        marginLeft: '8px',
                        fontSize: '11px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: '#e8f5e8',
                        color: '#2e7d32'
                      }}>
                      {getStatusText(pair.stepFile.status)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Kontroller */}
              {pair.status === 'pending' && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => removeGroup(pair.id)}
                    style={{
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '4px 12px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}>
                    Eşleştirmeyi Kaldır
                  </button>
                </div>
              )}

              {pair.status === 'failed' && (
                <div
                  style={{
                    marginTop: '8px',
                    color: '#dc3545',
                    fontSize: '12px'
                  }}>
                  ⚠️ Eşleştirme analizi başarısız.
                </div>
              )}

              {pair.status === 'completed' && pair.mergedResult && (
                <div
                  style={{
                    marginTop: '8px',
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center'
                  }}>
                  <span style={{ fontSize: '12px', color: '#28a745' }}>
                    ✓ Eşleştirme analizi tamamlandı!
                  </span>
                  <button
                    onClick={() => handlePairExport(pair)}
                    style={{
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      padding: '4px 12px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}>
                    📊 Excel İndir
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Eşleşmeyen dosyalar */}
        {files
          .filter((file) => !file.isPartOfMatch)
          .map((file, index) => (
            <div
              key={`file-${index}`}
              className={classes.uploadedItem}>
              <div className={classes.uploadedItemFirstSection}>
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{getFileTypeIcon(getFileType(file.file.name))}</span>
                  <p className={classes.exp}>{file.file.name}</p>
                </div>
                <div
                  className={`${classes.uploadedItemStatus} ${getStatusClass(
                    file.status
                  )}`}>
                  <p className={classes.uploadedItemStatusText}>
                    {getStatusText(file.status)}
                  </p>
                </div>
              </div>

              <div className={classes.progressContainer}>
                <div
                  className={classes.progressBar}
                  style={{ width: `${file.progress}%` }}>
                  <span className={classes.progressText}>{file.progress}%</span>
                </div>
              </div>

              {file.status === 'completed' &&
                (file.renderStatus === 'processing' ||
                  file.renderStatus === 'pending') && (
                  <div
                    style={{
                      fontSize: '12px',
                      marginTop: '8px',
                      color: '#007bff'
                    }}>
                    🎨 3D render işleniyor, lütfen bekleyin...
                  </div>
                )}

              {file.error && (
                <div
                  style={{
                    color: '#dc3545',
                    fontSize: '12px',
                    marginTop: '8px'
                  }}>
                  Hata: {file.error}
                  <button
                    className={classes.retryButton}
                    onClick={() => retryFile(files.indexOf(file))}
                    style={{ marginLeft: '10px' }}
                    disabled={isUploading}>
                    Tekrar Dene
                  </button>
                  <button
                    onClick={() => removeFile(files.indexOf(file))}
                    style={{
                      marginLeft: '8px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px'
                    }}>
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === 'pending' && (
                <div
                  style={{
                    fontSize: '12px',
                    marginTop: '8px',
                    color: '#6c757d'
                  }}>
                  Dosya analiz için hazır. "Yükle ve Tara" butonuna tıklayın.
                  <button
                    onClick={() => removeFile(files.indexOf(file))}
                    style={{
                      marginLeft: '10px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px'
                    }}>
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === 'completed' && (
                <div
                  style={{
                    fontSize: '12px',
                    marginTop: '8px',
                    color: '#28a745'
                  }}>
                  ✓ Analiz tamamlandı! İşleme süresi:{' '}
                  {file.result?.processing_time?.toFixed(1) || '0'} saniye
                </div>
              )}
            </div>
          ))}
      </>
    );
  };

  // Render analysis results
  const renderAnalysisResults = () => {
    const processedPairIds = new Set<string>();

    return (
      <>
        {/* Önce eşleşmiş çiftlerin sonuçlarını göster */}
        {matchedPairs
          .filter((pair) => pair.status === 'completed' && pair.mergedResult)
          .map((pair) => {
            processedPairIds.add(pair.id);
            return (
              <div
                key={`pair-result-${pair.id}`}
                className={`${classes.analyseItem} ${
                  expandedItems.has(pair.id) ? 'active' : ''
                }`}>
                <div
                  className={classes.analyseFirstSection}
                  onClick={() => toggleExpanded(pair.id)}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px'
                    }}>
                    <span style={{ fontSize: '18px' }}>🔗</span>
                    <div>
                      <p
                        className={classes.exp}
                        style={{ fontWeight: 'bold' }}>
                        {pair.pdfFile.file.name}
                      </p>
                      <p
                        style={{
                          fontSize: '12px',
                          color: '#666',
                          marginTop: '4px'
                        }}>
                        PDF + STEP Eşleştirmesi
                        <span
                          style={{
                            marginLeft: '8px',
                            padding: '2px 6px',
                            borderRadius: '8px',
                            backgroundColor: '#d4edda',
                            color: getMatchQualityColor(pair.matchQuality),
                            fontSize: '10px',
                            fontWeight: 'bold'
                          }}>
                          🎯 {pair.matchScore}% - {pair.matchQuality}
                        </span>
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      transform: expandedItems.has(pair.id)
                        ? 'rotate(180deg)'
                        : 'rotate(0deg)',
                      transition: 'transform 0.3s'
                    }}>
                    <i className='fa fa-arrow-down'></i>
                  </span>
                </div>

                {expandedItems.has(pair.id) &&
                  renderAnalysisDetails(pair.mergedResult, pair.id)}
              </div>
            );
          })}

        {/* Sonra eşleşmeyen dosyaların sonuçlarını göster */}
        {files
          .filter((file) => {
            // Sadece eşleşme parçası olmayan VE tamamlanmış dosyaları göster
            if (file.isPartOfMatch) return false;
            if (file.status !== 'completed') return false;

            // Eğer bu dosya bir eşleşmenin parçasıysa gösterme
            const isPartOfProcessedPair = matchedPairs.some(
              (pair) =>
                (pair.pdfFile.file.name === file.file.name ||
                  pair.stepFile.file.name === file.file.name) &&
                pair.status === 'completed'
            );

            return !isPartOfProcessedPair;
          })
          .map((file, index) => (
            <div
              key={`file-result-${index}`}
              className={`${classes.analyseItem} ${
                expandedItems.has(`file-${index}`) ? 'active' : ''
              }`}>
              <div
                className={classes.analyseFirstSection}
                onClick={() => toggleExpanded(`file-${index}`)}>
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{getFileTypeIcon(getFileType(file.file.name))}</span>
                  <p className={classes.exp}>{file.file.name}</p>
                </div>
                <span
                  style={{
                    transform: expandedItems.has(`file-${index}`)
                      ? 'rotate(180deg)'
                      : 'rotate(0deg)',
                    transition: 'transform 0.3s'
                  }}>
                  <i className='fa fa-arrow-down'></i>
                </span>
              </div>

              {expandedItems.has(`file-${index}`) &&
                renderAnalysisDetails(file.result, `file-${index}`)}
            </div>
          ))}
      </>
    );
  };

  const hasCompletedResults =
    matchedPairs.some((p) => p.status === 'completed') ||
    files.some((f) => f.status === 'completed' && !f.isPartOfMatch);

  const completedMatchCount = matchedPairs.filter(
    (p) => p.status === 'completed'
  ).length;

  const completedSingleFileCount = files.filter((f) => {
    // Dosya tamamlanmış mı?
    if (f.status !== 'completed') return false;

    // Dosya bir eşleştirmenin parçası mı?
    if (f.isPartOfMatch) return false;

    // Bu dosya için tamamlanmış bir eşleştirme var mı?
    const hasCompletedMatch = matchedPairs.some(
      (pair) =>
        pair.status === 'completed' &&
        (pair.pdfFile.file.name === f.file.name ||
          pair.stepFile.file.name === f.file.name)
    );

    return !hasCompletedMatch;
  }).length;

  const pendingCount = files.filter((f) => f.status === 'pending').length;

  return (
    <div className={classes.container}>
      {/* Main Content - Split Layout */}
      <div className={classes.mainContent}>
        {/* Left Panel - File Upload and Management */}
        <div className={classes.leftPanel}>
          <div className={classes.panelHeader}>
            <h3>📁 Dosya Yönetimi</h3>
            <p>Dosyalarınızı buraya sürükleyin veya seçin</p>
          </div>

          {/* Dropzone */}
          <div
            className={`${classes.dropzone} ${
              isDragging ? classes.dropzoneActive : ''
            }`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={handleFileSelect}>
            <div className={classes.dropzoneContent}>
              <span className={classes.dropzoneIcon}>📤</span>
              <p className={classes.dropzoneText}>
                {isDragging
                  ? 'Dosyaları buraya bırakın'
                  : 'Dosyaları sürükleyin veya tıklayın'}
              </p>
              <p className={classes.dropzoneSubtext}>
                PDF, DOC, DOCX, STEP, STP
              </p>
              {files.length > 0 && (
                <p className={classes.dropzoneFileCount}>
                  {files.length} dosya seçildi
                </p>
              )}
            </div>
          </div>

          <input
            ref={fileInputRef}
            type='file'
            multiple
            accept='.pdf,.doc,.docx,.step,.stp'
            onChange={handleFileChange}
            className={classes.hiddenFileInput}
          />

          {/* Eşleştirme bilgisi */}
          {files.length > 0 && matchedPairs.length > 0 && (
            <div className={classes.matchInfo}>
              <div className={classes.matchInfoContent}>
                🎯 <strong>{matchedPairs.length} eşleştirme bulundu!</strong>
                <ul>
                  {matchedPairs.map((pair) => (
                    <li key={pair.id}>
                      {pair.pdfFile.file.name} ↔ {pair.stepFile.file.name} (
                      <strong>{pair.matchScore}%</strong> - {pair.matchQuality})
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Upload Button */}
          <button
            className={classes.uploadButton}
            onClick={uploadAndAnalyze}
            disabled={files.length === 0 || isUploading || pendingCount === 0}>
            {isUploading
              ? 'Yükleniyor ve Analiz Ediliyor...'
              : pendingCount > 0
              ? `Yükle ve Tara (${pendingCount} dosya)`
              : 'Tüm Dosyalar İşlendi'}
          </button>

          {(isUploading || pendingCount > 0) && (
            <p className={classes.processingInfo}>
              {isUploading
                ? `${
                    files.filter(
                      (f) =>
                        f.status === 'uploading' || f.status === 'analyzing'
                    ).length
                  } dosya işleniyor, lütfen bekleyin...`
                : `${pendingCount} dosya işlenmeyi bekliyor`}
            </p>
          )}

          {/* File List */}
          <div className={classes.fileListSection}>{renderFileList()}</div>

          {/* Excel Operations */}
          {hasCompletedResults && (
            <div className={classes.excelOperations}>
              {/* Multiple Excel Export */}
              <div className={classes.exportSection}>
                <h4>📊 Toplu Excel İndirme</h4>
                {isExporting && (
                  <div className={classes.exportProgress}>
                    <div
                      className={classes.exportProgressBar}
                      style={{ width: `${exportProgress}%` }}>
                      {exportProgress}%
                    </div>
                  </div>
                )}
                <button
                  className={classes.exportButton}
                  onClick={handleMultipleExcelExport}
                  disabled={!hasCompletedResults || isExporting}>
                  <img
                    src='/download-icon.svg'
                    alt=''
                  />
                  {isExporting
                    ? 'Excel Oluşturuluyor...'
                    : `Excel İndir (${
                        completedMatchCount + completedSingleFileCount
                      } Analiz)`}
                </button>
              </div>

              {/* Excel Merge */}
              <div className={classes.mergeSection}>
                <h4>📤 Excel Birleştirme</h4>
                <div className={classes.excelFileSelection}>
                  <button
                    className={classes.excelSelectButton}
                    onClick={handleExcelFileSelect}
                    disabled={isMerging}>
                    Excel Seç
                  </button>
                  <span className={classes.excelFileName}>
                    {selectedExcelFile
                      ? selectedExcelFile.name
                      : 'Dosya seçilmedi'}
                  </span>
                  {selectedExcelFile && (
                    <button
                      onClick={removeExcelFile}
                      className={classes.removeExcelButton}
                      disabled={isMerging}>
                      ✕
                    </button>
                  )}
                </div>
                <input
                  ref={excelInputRef}
                  type='file'
                  accept='.xlsx,.xls'
                  onChange={handleExcelFileChange}
                  style={{ display: 'none' }}
                />
                {isMerging && (
                  <div className={classes.mergeProgress}>
                    <div
                      className={classes.mergeProgressBar}
                      style={{ width: `${mergeProgress}%` }}>
                      {mergeProgress}%
                    </div>
                  </div>
                )}
                <button
                  className={classes.mergeButton}
                  onClick={handleExcelMerge}
                  disabled={
                    !selectedExcelFile || isMerging || !hasCompletedResults
                  }>
                  <img
                    src='/upload.svg'
                    alt=''
                  />
                  {isMerging ? 'Birleştiriliyor...' : 'Excel Birleştir'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - Analysis Results */}
        <div className={classes.rightPanel}>
          <div className={classes.panelHeader}>
            <h3>📊 Analiz Sonuçları</h3>
            {hasCompletedResults && (
              <p>
                {completedMatchCount} eşleştirme, {completedSingleFileCount}{' '}
                tekil dosya
                {totalProcessingTime > 0 &&
                  ` • ⏱️ ${totalProcessingTime.toFixed(1)}s`}
              </p>
            )}
          </div>

          <div className={classes.resultsSection}>
            {hasCompletedResults ? (
              renderAnalysisResults()
            ) : (
              <div className={classes.emptyResults}>
                <span className={classes.emptyIcon}>📋</span>
                <p style={{ marginTop: 16 }}>Henüz analiz sonucu yok</p>
                <p className={classes.emptySubtext}>
                  Dosyalarınızı yükleyip analiz ettikten sonra sonuçlar burada
                  görünecek
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
