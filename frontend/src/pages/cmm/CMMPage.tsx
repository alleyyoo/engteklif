// frontend/src/pages/cmm/CMMPage.tsx
import React, { useState, useRef, useEffect } from "react";
import { Button } from "primereact/button";
import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import { Toast } from "primereact/toast";
import { Card } from "primereact/card";
import { Badge } from "primereact/badge";
import { ConfirmDialog, confirmDialog } from "primereact/confirmdialog";
import { ProgressBar } from "primereact/progressbar";
import { Divider } from "primereact/divider";
import { Panel } from "primereact/panel";
import { Chip } from "primereact/chip";
import { CMMPageStyles } from "./CMMPage.styles";
import { cmmService, CMMAnalysis } from "../../services/cmmService";

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
        showError("CMM analizleri yüklenemedi");
      }
    } catch (error: any) {
      console.error("❌ CMM analiz yükleme hatası:", error);
      showError(error.message || "CMM analizleri yüklenirken hata oluştu");
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
      console.error("❌ CMM istatistik hatası:", error);
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
      const invalidMessages = invalid.map(item => 
        `${item.file.name}: ${item.reason}`
      ).join('\n');
      
      showError(`Geçersiz dosyalar:\n${invalidMessages}`);
    }

    if (valid.length > 0) {
      setSelectedFiles(valid);
      showSuccess(`${valid.length} RTF dosyası seçildi`);
    }

    // Input'u temizle
    event.target.value = "";
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
      showError("Lütfen en az bir RTF dosyası seçin");
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(10);

      console.log("📄 CMM dosyaları işleniyor...", {
        fileCount: selectedFiles.length,
        files: selectedFiles.map(f => f.name)
      });

      setUploadProgress(30);

      // CMM dosyalarını yükle ve parse et
      const result = await cmmService.uploadCMMFiles(selectedFiles);

      setUploadProgress(80);

      if (result.success) {
        console.log("✅ CMM işleme başarılı:", {
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
          const filename = await cmmService.downloadAndSaveCMMExcel(result.analysis_id);
          showSuccess(`📁 Excel raporu indirildi: ${filename}`);
        } catch (downloadError) {
          console.error("❌ Otomatik Excel indirme hatası:", downloadError);
          showError("Excel indirme başarısız. Manuel olarak indirin.");
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
        throw new Error(result.message || "CMM işleme başarısız");
      }

    } catch (error: any) {
      console.error("❌ CMM upload hatası:", error);
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
      header: "CMM Analizi Sil",
      icon: "pi pi-exclamation-triangle",
      accept: async () => {
        try {
          await cmmService.deleteCMMAnalysis(analysis._id);
          showSuccess("CMM analizi silindi");
          await loadCMMAnalyses();
          await loadStats();
        } catch (error: any) {
          showError(`Silme hatası: ${error.message}`);
        }
      },
    });
  };

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  const showSuccess = (message: string) => {
    toast.current?.show({
      severity: "success",
      summary: "Başarılı",
      detail: message,
      life: 4000,
    });
  };

  const showError = (message: string) => {
    toast.current?.show({
      severity: "error",
      summary: "Hata",
      detail: message,
      life: 5000,
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
      return <Badge value="Operasyon Yok" severity="secondary" />;
    }

    return (
      <div className={classes.badgeContainer}>
        {operations.map((op, index) => (
          <Badge 
            key={index} 
            value={op} 
            severity={op === '1OP' ? 'success' : op === '2OP' ? 'info' : 'secondary'} 
          />
        ))}
      </div>
    );
  };

  const renderAnalysisActions = (analysis: CMMAnalysis) => {
    return (
      <div className={classes.actionButtons}>
        <Button
          icon="pi pi-download"
          size="small"
          severity="success"
          outlined
          onClick={() => handleDownloadExcel(analysis)}
          tooltip="Excel İndir"
          disabled={!analysis.excel_available}
          className={classes.responsiveButton}
        />
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          onClick={() => handleDeleteAnalysis(analysis)}
          tooltip="Sil"
          className={classes.responsiveButton}
        />
      </div>
    );
  };

  const renderFileList = () => {
    if (selectedFiles.length === 0) {
      return (
        <div className={classes.emptyState}>
          📄 Seçilen RTF dosyası yok
        </div>
      );
    }

    return (
      <div className={classes.fileList}>
        {selectedFiles.map((file, index) => (
          <div key={index} className={classes.fileItem}>
            <div className={classes.fileInfo}>
              <span className={classes.fileName}>📄 {file.name}</span>
              <span className={classes.fileSize}>{formatFileSize(file.size)}</span>
            </div>
            <Button
              icon="pi pi-times"
              size="small"
              severity="danger"
              text
              onClick={() => removeFile(index)}
              tooltip="Kaldır"
            />
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

      <h1 className={classes.pageTitle}>📏 CMM Ölçüm Raporu Analizi</h1>

      {/* Stats Cards */}
      {stats && (
        <div className={classes.statsContainer}>
          <Card className={classes.statsCard}>
            <div className={classes.statItem}>
              <span className={classes.statNumber}>{stats.total_analyses}</span>
              <span className={classes.statLabel}>Toplam Analiz</span>
            </div>
          </Card>
          <Card className={classes.statsCard}>
            <div className={classes.statItem}>
              <span className={classes.statNumber}>{stats.total_measurements}</span>
              <span className={classes.statLabel}>Toplam Ölçüm</span>
            </div>
          </Card>
          <Card className={classes.statsCard}>
            <div className={classes.statItem}>
              <span className={classes.statNumber}>{stats.this_month_analyses}</span>
              <span className={classes.statLabel}>Bu Ay</span>
            </div>
          </Card>
          <Card className={classes.statsCard}>
            <div className={classes.statItem}>
              <span className={classes.statNumber}>{stats.avg_measurements_per_analysis}</span>
              <span className={classes.statLabel}>Ort. Ölçüm/Analiz</span>
            </div>
          </Card>
        </div>
      )}

      {/* File Upload Section */}
      <div className={classes.cardContainer}>
        <Card title="📤 CMM RTF Dosyası Yükleme">
          <div className={classes.uploadSection}>
            <div className={classes.fileSelection}>
              <Button
                label="RTF Dosyaları Seç"
                icon="pi pi-upload"
                onClick={handleFileSelect}
                className={classes.responsiveButton}
              />
              <span className={classes.fileCount}>
                {selectedFiles.length === 0 
                  ? "Dosya seçilmedi" 
                  : `${selectedFiles.length} RTF dosyası seçildi`}
              </span>
              {selectedFiles.length > 0 && (
                <Button
                  label="Temizle"
                  icon="pi pi-times"
                  severity="secondary"
                  outlined
                  size="small"
                  onClick={clearFiles}
                  className={classes.responsiveButton}
                />
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".rtf,.RTF"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            {/* Selected Files List */}
            {renderFileList()}

            {/* Processing Info */}
            <div className={classes.processingInfo}>
              <Panel header="📋 CMM İşleme Özellikleri" toggleable collapsed>
                <ul className={classes.featureList}>
                  <li>✅ 1OP ve 2OP operasyon otomatik tanıma</li>
                  <li>✅ Ölçüm numarası bazlı sıralama</li>
                  <li>✅ Position ölçümü desteği (X, Y, TP, DF)</li>
                  <li>✅ Duplikat veri temizleme</li>
                  <li>✅ Tolerans dışı değer analizi</li>
                  <li>✅ Excel raporu otomatik oluşturma</li>
                  <li>✅ Boyut, tolerans ve sapma analizi</li>
                </ul>
              </Panel>
            </div>

            {/* Upload Progress */}
            {isUploading && (
              <div className={classes.progressSection}>
                <ProgressBar 
                  value={uploadProgress} 
                  displayValueTemplate={() => `${uploadProgress}%`}
                />
                <p className={classes.progressText}>
                  CMM dosyaları işleniyor, lütfen bekleyin...
                </p>
              </div>
            )}

            {/* Upload Button */}
            <Button
              label={isUploading ? "İşleniyor..." : "RTF Dosyalarını İşle"}
              icon={isUploading ? "pi pi-spin pi-spinner" : "pi pi-cog"}
              onClick={handleUploadAndProcess}
              disabled={selectedFiles.length === 0 || isUploading}
              severity="success"
              className={classes.uploadButton}
            />
          </div>
        </Card>
      </div>

      <Divider />

      {/* CMM Analyses List */}
      <div className={classes.cardContainer}>
        <Card title="📊 CMM Analiz Geçmişi">
          <div className={classes.tableWrapper}>
            <DataTable
              value={analyses}
              loading={loading}
              paginator
              rows={pageSize}
              totalRecords={totalRecords}
              lazy
              first={(currentPage - 1) * pageSize}
              onPage={(e) => setCurrentPage((e.first / pageSize) + 1)}
              emptyMessage="Henüz CMM analizi yapılmamış."
              responsiveLayout="scroll"
            >
              <Column 
                field="analysis_id" 
                header="Analiz ID" 
                style={{ minWidth: '150px' }}
                className={classes.hideOnMobile}
              />
              
              <Column 
                field="file_count" 
                header="Dosya Sayısı" 
                style={{ width: '100px' }}
                body={(rowData: CMMAnalysis) => (
                  <Chip label={rowData.file_count.toString()} />
                )}
              />
              
              <Column 
                field="measurement_count" 
                header="Ölçüm Sayısı" 
                style={{ width: '120px' }}
                body={(rowData: CMMAnalysis) => (
                  <Badge 
                    value={rowData.measurement_count.toString()} 
                    severity="success" 
                  />
                )}
              />
              
              <Column 
                field="operations" 
                header="Operasyonlar" 
                style={{ minWidth: '150px' }}
                body={(rowData: CMMAnalysis) => renderOperationsBadges(rowData.operations)}
                className={classes.hideOnMobile}
              />
              
              <Column 
                field="created_at" 
                header="Oluşturma Tarihi" 
                style={{ minWidth: '180px' }}
                body={(rowData: CMMAnalysis) => formatDate(rowData.created_at)}
                className={classes.hideOnMobile}
              />
              
              <Column 
                field="excel_available" 
                header="Excel" 
                style={{ width: '80px' }}
                body={(rowData: CMMAnalysis) => (
                  rowData.excel_available ? 
                    <Badge value="✓" severity="success" /> : 
                    <Badge value="✗" severity="danger" />
                )}
              />
              
              <Column 
                body={renderAnalysisActions} 
                header="İşlemler" 
                style={{ width: '120px' }}
              />
            </DataTable>
            
            <div className={classes.scrollHint}>
              💡 Tabloda kaydırarak tüm sütunları görebilirsiniz
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};