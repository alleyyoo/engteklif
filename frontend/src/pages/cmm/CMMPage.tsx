// frontend/src/pages/cmm/CMMPage.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Button } from 'primereact/button';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Toast } from 'primereact/toast';
import { Card } from 'primereact/card';
import { Badge } from 'primereact/badge';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { ProgressBar } from 'primereact/progressbar';
import { Divider } from 'primereact/divider';
import { Panel } from 'primereact/panel';
import { Chip } from 'primereact/chip';
import { CMMPageStyles } from './CMMPage.styles';
import { cmmService, CMMAnalysis } from '../../services/cmmService';

export const CMMPage = () => {
  const classes = CMMPageStyles();
  const toast = useRef<Toast>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State management
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analyses, setAnalyses] = useState<CMMAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const pageSize = 10;

  useEffect(() => {
    loadCMMAnalyses();
    loadStats();
  }, [currentPage]);

  // ============================================================================
  // DATA LOADING
  // ============================================================================

  const loadCMMAnalyses = async () => {
    try {
      setLoading(true);
      const result = await cmmService.getMyCMMAnalyses(currentPage, pageSize);

      if (result.success) {
        setAnalyses(result.analyses);
        setTotalRecords(result.pagination.total);
      } else {
        showError('CMM analizleri yüklenemedi');
      }
    } catch (error: any) {
      console.error('❌ CMM analiz yükleme hatası:', error);
      showError(error.message || 'CMM analizleri yüklenirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const result = await cmmService.getCMMStats();
      if (result.success) {
        setStats(result.stats);
      }
    } catch (error) {
      console.error('❌ CMM istatistik hatası:', error);
    }
  };

  // ============================================================================
  // DRAG & DROP HANDLERS
  // ============================================================================

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
    const { valid, invalid } = cmmService.validateCMMFiles(droppedFiles);

    if (invalid.length > 0) {
      const invalidMessages = invalid
        .map((item) => `${item.file.name}: ${item.reason}`)
        .join('\n');

      showError(`Geçersiz dosyalar:\n${invalidMessages}`);
    }

    if (valid.length > 0) {
      setSelectedFiles(valid);
      showSuccess(`${valid.length} RTF dosyası seçildi`);
    }
  };

  // ============================================================================
  // FILE HANDLING
  // ============================================================================

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);

    if (files.length === 0) return;

    // Dosya validasyonu
    const { valid, invalid } = cmmService.validateCMMFiles(files);

    if (invalid.length > 0) {
      const invalidMessages = invalid
        .map((item) => `${item.file.name}: ${item.reason}`)
        .join('\n');

      showError(`Geçersiz dosyalar:\n${invalidMessages}`);
    }

    if (valid.length > 0) {
      setSelectedFiles(valid);
      showSuccess(`${valid.length} RTF dosyası seçildi`);
    }

    // Input'u temizle
    event.target.value = '';
  };

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
  };

  const clearFiles = () => {
    setSelectedFiles([]);
  };

  // ============================================================================
  // CMM PROCESSING
  // ============================================================================

  const handleUploadAndProcess = async () => {
    if (selectedFiles.length === 0) {
      showError('Lütfen en az bir RTF dosyası seçin');
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(10);

      console.log('📄 CMM dosyaları işleniyor...', {
        fileCount: selectedFiles.length,
        files: selectedFiles.map((f) => f.name)
      });

      setUploadProgress(30);

      // CMM dosyalarını yükle ve parse et
      const result = await cmmService.uploadCMMFiles(selectedFiles);

      setUploadProgress(80);

      if (result.success) {
        console.log('✅ CMM işleme başarılı:', {
          analysisId: result.analysis_id,
          measurementCount: result.data.measurement_count,
          operations: result.data.operations
        });

        setUploadProgress(100);

        // Başarı mesajı
        showSuccess(
          `✅ ${result.data.file_count} RTF dosyası başarıyla işlendi!\n` +
            `📊 ${result.data.measurement_count} ölçüm verisi çıkarıldı\n` +
            `🏭 Operasyonlar: ${result.data.operations.join(', ')}\n` +
            `📋 Excel raporu hazır`
        );

        // Otomatik Excel indirme
        try {
          const filename = await cmmService.downloadAndSaveCMMExcel(
            result.analysis_id
          );
          showSuccess(`📁 Excel raporu indirildi: ${filename}`);
        } catch (downloadError) {
          console.error('❌ Otomatik Excel indirme hatası:', downloadError);
          showError('Excel indirme başarısız. Manuel olarak indirin.');
        }

        // Dosyaları temizle ve listeyi yenile
        setSelectedFiles([]);
        await loadCMMAnalyses();
        await loadStats();

        setTimeout(() => {
          setUploadProgress(0);
          setIsUploading(false);
        }, 1000);
      } else {
        throw new Error(result.message || 'CMM işleme başarısız');
      }
    } catch (error: any) {
      console.error('❌ CMM upload hatası:', error);
      showError(`CMM işleme hatası: ${error.message}`);
      setUploadProgress(0);
      setIsUploading(false);
    }
  };

  // ============================================================================
  // ANALYSIS MANAGEMENT
  // ============================================================================

  const handleDownloadExcel = async (analysis: CMMAnalysis) => {
    try {
      const filename = await cmmService.downloadAndSaveCMMExcel(analysis._id);
      showSuccess(`Excel indirildi: ${filename}`);
    } catch (error: any) {
      showError(`İndirme hatası: ${error.message}`);
    }
  };

  const handleDeleteAnalysis = (analysis: CMMAnalysis) => {
    confirmDialog({
      message: `"${analysis.analysis_id}" CMM analizini silmek istediğinize emin misiniz?`,
      header: 'CMM Analizi Sil',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await cmmService.deleteCMMAnalysis(analysis._id);
          showSuccess('CMM analizi silindi');
          await loadCMMAnalyses();
          await loadStats();
        } catch (error: any) {
          showError(`Silme hatası: ${error.message}`);
        }
      }
    });
  };

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  const showSuccess = (message: string) => {
    toast.current?.show({
      severity: 'success',
      summary: 'Başarılı',
      detail: message,
      life: 4000
    });
  };

  const showError = (message: string) => {
    toast.current?.show({
      severity: 'error',
      summary: 'Hata',
      detail: message,
      life: 5000
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('tr-TR');
  };

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  const renderOperationsBadges = (operations: string[]) => {
    if (!operations || operations.length === 0) {
      return (
        <Badge
          value='Operasyon Yok'
          severity='secondary'
        />
      );
    }

    return (
      <div className={classes.badgeContainer}>
        {operations.map((op, index) => (
          <Badge
            key={index}
            value={op}
            severity={
              op === '1OP' ? 'success' : op === '2OP' ? 'info' : 'secondary'
            }
          />
        ))}
      </div>
    );
  };

  const renderAnalysisActions = (analysis: CMMAnalysis) => {
    return (
      <div className={classes.actionButtons}>
        <Button
          icon='pi pi-download'
          size='small'
          severity='success'
          outlined
          onClick={() => handleDownloadExcel(analysis)}
          tooltip='Excel İndir'
          disabled={!analysis.excel_available}
          className={classes.responsiveButton}
        />
        <Button
          icon='pi pi-trash'
          size='small'
          severity='danger'
          outlined
          onClick={() => handleDeleteAnalysis(analysis)}
          tooltip='Sil'
          className={classes.responsiveButton}
        />
      </div>
    );
  };

  const renderFileList = () => {
    if (selectedFiles.length === 0) return null;

    return (
      <div className={classes.fileList}>
        {selectedFiles.map((file, index) => (
          <div
            key={index}
            className={classes.fileItem}>
            <div className={classes.fileInfo}>
              <span className={classes.fileIcon}>📄</span>
              <div className={classes.fileDetails}>
                <span className={classes.fileName}>{file.name}</span>
                <span className={classes.fileSize}>
                  {formatFileSize(file.size)}
                </span>
              </div>
            </div>
            <button
              className={classes.removeFileButton}
              onClick={() => removeFile(index)}
              title='Kaldır'>
              ✕
            </button>
          </div>
        ))}
      </div>
    );
  };

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  return (
    <div className={classes.container}>
      <Toast ref={toast} />
      <ConfirmDialog />

      {/* Header Section */}
      <div className={classes.headerSection}>
        <h1 className={classes.pageTitle}>📏 CMM Ölçüm Raporu Analizi</h1>
        <p className={classes.pageDescription}>
          RTF formatındaki CMM ölçüm raporlarınızı yükleyin, otomatik olarak
          analiz edin ve Excel raporları oluşturun.
        </p>

        {/* Stats Cards */}
        {stats && (
          <div className={classes.statsContainer}>
            <div className={classes.statsCard}>
              <div className={classes.statNumber}>{stats.total_analyses}</div>
              <div className={classes.statLabel}>Toplam Analiz</div>
            </div>
            <div className={classes.statsCard}>
              <div className={classes.statNumber}>
                {stats.total_measurements}
              </div>
              <div className={classes.statLabel}>Toplam Ölçüm</div>
            </div>
            <div className={classes.statsCard}>
              <div className={classes.statNumber}>
                {stats.this_month_analyses}
              </div>
              <div className={classes.statLabel}>Bu Ay</div>
            </div>
            <div className={classes.statsCard}>
              <div className={classes.statNumber}>
                {stats.avg_measurements_per_analysis}
              </div>
              <div className={classes.statLabel}>Ort. Ölçüm/Analiz</div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content - Split Layout */}
      <div className={classes.mainContent}>
        {/* Left Panel - File Upload */}
        <div className={classes.leftPanel}>
          <div className={classes.panelHeader}>
            <h3>📤 Dosya Yükleme</h3>
            <p>RTF dosyalarınızı buraya sürükleyin veya seçin</p>
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
              <span className={classes.dropzoneIcon}>📁</span>
              <p className={classes.dropzoneText}>
                {isDragging
                  ? 'Dosyaları buraya bırakın'
                  : 'RTF dosyalarını sürükleyin veya tıklayın'}
              </p>
              <p className={classes.dropzoneSubtext}>
                Sadece .RTF formatı desteklenir
              </p>
              {selectedFiles.length > 0 && (
                <p className={classes.dropzoneFileCount}>
                  {selectedFiles.length} dosya seçildi
                </p>
              )}
            </div>
          </div>

          <input
            ref={fileInputRef}
            type='file'
            multiple
            accept='.rtf,.RTF'
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />

          {/* Selected Files List */}
          {renderFileList()}

          {/* Clear All Button */}
          {selectedFiles.length > 0 && (
            <button
              className={classes.clearButton}
              onClick={clearFiles}>
              <i className='pi pi-times'></i> Tümünü Temizle
            </button>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <div className={classes.progressSection}>
              <div className={classes.progressBar}>
                <div
                  className={classes.progressFill}
                  style={{ width: `${uploadProgress}%` }}>
                  {uploadProgress}%
                </div>
              </div>
              <p className={classes.progressText}>
                CMM dosyaları işleniyor, lütfen bekleyin...
              </p>
            </div>
          )}

          {/* Upload Button */}
          <button
            className={classes.uploadButton}
            onClick={handleUploadAndProcess}
            disabled={selectedFiles.length === 0 || isUploading}>
            {isUploading ? (
              <>
                <i className='pi pi-spin pi-spinner'></i>
                İşleniyor...
              </>
            ) : (
              <>
                <i className='pi pi-cog'></i>
                RTF Dosyalarını İşle
              </>
            )}
          </button>

          {/* Features Panel */}
          <div className={classes.featuresPanel}>
            <h4>📋 CMM İşleme Özellikleri</h4>
            <ul className={classes.featureList}>
              <li>✅ 1OP ve 2OP operasyon otomatik tanıma</li>
              <li>✅ Ölçüm numarası bazlı sıralama</li>
              <li>✅ Position ölçümü desteği (X, Y, TP, DF)</li>
              <li>✅ Duplikat veri temizleme</li>
              <li>✅ Tolerans dışı değer analizi</li>
              <li>✅ Excel raporu otomatik oluşturma</li>
              <li>✅ Boyut, tolerans ve sapma analizi</li>
            </ul>
          </div>
        </div>

        {/* Right Panel - Analysis History */}
        <div className={classes.rightPanel}>
          <div className={classes.panelHeader}>
            <h3>📊 Analiz Geçmişi</h3>
            <p>Tamamlanan CMM analizleriniz</p>
          </div>

          <div className={classes.analysisSection}>
            {loading ? (
              <div className={classes.loadingState}>
                <i
                  className='pi pi-spin pi-spinner'
                  style={{ fontSize: '2rem' }}></i>
                <p>Yükleniyor...</p>
              </div>
            ) : analyses.length === 0 ? (
              <div className={classes.emptyState}>
                <span className={classes.emptyIcon}>📋</span>
                <p style={{ marginTop: 16 }}>Henüz CMM analizi yok</p>
                <p className={classes.emptySubtext}>
                  RTF dosyalarınızı yükleyerek ilk analizinizi başlatın
                </p>
              </div>
            ) : (
              <div className={classes.analysisGrid}>
                {analyses.map((analysis) => (
                  <div
                    key={analysis._id}
                    className={classes.analysisCard}>
                    <div className={classes.analysisHeader}>
                      <span className={classes.analysisId}>
                        {analysis.analysis_id}
                      </span>
                      <div className={classes.analysisStats}>
                        <Badge value={`${analysis.file_count} Dosya`} />
                        <Badge
                          value={`${analysis.measurement_count} Ölçüm`}
                          severity='success'
                        />
                      </div>
                    </div>

                    <div className={classes.analysisBody}>
                      <div className={classes.analysisInfo}>
                        <div className={classes.infoItem}>
                          <span className={classes.infoLabel}>
                            Operasyonlar:
                          </span>
                          <div className={classes.operationBadges}>
                            {renderOperationsBadges(analysis.operations)}
                          </div>
                        </div>
                        <div className={classes.infoItem}>
                          <span className={classes.infoLabel}>Tarih:</span>
                          <span className={classes.infoValue}>
                            {formatDate(analysis.created_at)}
                          </span>
                        </div>
                      </div>

                      <div className={classes.analysisActions}>
                        <button
                          className={`${classes.actionButton} ${classes.downloadButton}`}
                          onClick={() => handleDownloadExcel(analysis)}
                          disabled={!analysis.excel_available}
                          title='Excel İndir'>
                          <i className='pi pi-download'></i>
                          Excel
                        </button>
                        <button
                          className={`${classes.actionButton} ${classes.deleteButton}`}
                          onClick={() => handleDeleteAnalysis(analysis)}
                          title='Sil'>
                          <i className='pi pi-trash'></i>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalRecords > pageSize && (
              <div className={classes.pagination}>
                <button
                  className={classes.pageButton}
                  onClick={() =>
                    setCurrentPage((prev) => Math.max(1, prev - 1))
                  }
                  disabled={currentPage === 1}>
                  <i className='pi pi-chevron-left'></i>
                </button>
                <span className={classes.pageInfo}>
                  Sayfa {currentPage} / {Math.ceil(totalRecords / pageSize)}
                </span>
                <button
                  className={classes.pageButton}
                  onClick={() =>
                    setCurrentPage((prev) =>
                      Math.min(Math.ceil(totalRecords / pageSize), prev + 1)
                    )
                  }
                  disabled={currentPage === Math.ceil(totalRecords / pageSize)}>
                  <i className='pi pi-chevron-right'></i>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
