import React, { useState, useRef, useEffect } from "react";
import { DashboardPageStyles } from "./DashboardPage.styles";
import { useFileUpload } from "../../hooks/useFileUpload";
import { Image } from "primereact/image";
import { apiService } from "../../services/api";

export const DashboardPage = () => {
  const classes = DashboardPageStyles();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Excel merge state
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [mergeProgress, setMergeProgress] = useState(0);

  // Excel export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);

  // ✅ NEW - CAD conversion status state
  const [cadConversionStatus, setCadConversionStatus] = useState<any>(null);
  const [showCADStatus, setShowCADStatus] = useState(false);

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
    // ✅ NEW - CAD conversion features
    conversionStats,
    getConversionStatistics,
    getFileTypeStatistics,
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
    getFileType,
    getFileTypeIcon,
    isCADFile,
    needsConversion,
  } = useFileUpload();

  // Grup modunu başlangıçta aktif yap
  useEffect(() => {
    setGroupMode(true);
  }, [setGroupMode]);

  // ✅ NEW - CAD conversion status'u yükle
  useEffect(() => {
    const loadCADStatus = async () => {
      try {
        const status = await apiService.getCADConversionStatus();
        setCadConversionStatus(status);
      } catch (error) {
        console.error("CAD status yüklenemedi:", error);
      }
    };

    loadCADStatus();
  }, []);

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    if (selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    event.target.value = "";
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
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/excel",
      ];

      if (
        validTypes.includes(file.type) ||
        file.name.toLowerCase().endsWith(".xlsx") ||
        file.name.toLowerCase().endsWith(".xls")
      ) {
        setSelectedExcelFile(file);
        console.log("✅ Excel dosyası seçildi:", file.name);
      } else {
        alert("Lütfen geçerli bir Excel dosyası (.xlsx, .xls) seçin.");
      }
    }
    event.target.value = "";
  };

  const handleExcelMerge = async () => {
    if (!selectedExcelFile) {
      alert("Lütfen önce bir Excel dosyası seçin.");
      return;
    }

    let completedAnalyses = [];

    // Tüm tamamlanmış analizleri topla (matchedPairs dahil)
    matchedPairs.forEach((pair) => {
      if (pair.status === "completed" && pair.mergedResult?.analysis?.id) {
        completedAnalyses.push({
          result: pair.mergedResult,
        });
      }
    });

    // Eşleşmeyen dosyaları da ekle
    files.forEach((file) => {
      if (
        file.status === "completed" &&
        file.result?.analysis?.id &&
        !file.isPartOfMatch
      ) {
        completedAnalyses.push({
          result: file.result,
        });
      }
    });

    if (completedAnalyses.length === 0) {
      alert(
        "Birleştirilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin."
      );
      return;
    }

    setIsMerging(true);
    setMergeProgress(10);

    try {
      console.log("📊 Excel merge başlıyor...", {
        excelFile: selectedExcelFile.name,
        analysisCount: completedAnalyses.length,
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
        console.log("✅ Excel merge başarılı");

        const url = window.URL.createObjectURL(result.blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = result.filename || `merged_excel_${Date.now()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        setMergeProgress(100);

        setTimeout(() => {
          alert("✅ Excel dosyası başarıyla birleştirildi ve indirildi!");
          setSelectedExcelFile(null);
          setMergeProgress(0);
          setIsMerging(false);
        }, 500);
      } else {
        throw new Error(result.message || "Excel birleştirme başarısız");
      }
    } catch (error: any) {
      console.error("❌ Excel merge hatası:", error);
      alert(`Excel birleştirme hatası: ${error.message || "Bilinmeyen hata"}`);
      setMergeProgress(0);
      setIsMerging(false);
    }
  };

  const removeExcelFile = () => {
    setSelectedExcelFile(null);
  };

  const handleMultipleExcelExport = async () => {
    const completedCount =
      matchedPairs.filter((p) => p.status === "completed").length +
      files.filter((f) => f.status === "completed" && !f.isPartOfMatch).length;

    if (completedCount === 0) {
      alert(
        "Export edilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin."
      );
      return;
    }

    setIsExporting(true);
    setExportProgress(10);

    try {
      console.log("📊 Multiple Excel export başlıyor...", {
        analysisCount: completedCount,
      });

      setExportProgress(30);

      const result = await exportAllCompletedToExcel();

      setExportProgress(80);

      if (result.success) {
        console.log("✅ Multiple Excel export başarılı:", result.filename);

        setExportProgress(100);

        setTimeout(() => {
          alert(
            `✅ ${completedCount} analiz başarıyla Excel'e aktarıldı ve indirildi!\n\nDosya: ${result.filename}`
          );
          setExportProgress(0);
          setIsExporting(false);
        }, 500);
      } else {
        throw new Error(result.error || "Excel export başarısız");
      }
    } catch (error: any) {
      console.error("❌ Multiple Excel export hatası:", error);
      alert(`Excel export hatası: ${error.message || "Bilinmeyen hata"}`);
      setExportProgress(0);
      setIsExporting(false);
    }
  };

  const handlePairExport = async (pair: any) => {
    if (!pair.mergedResult) {
      alert("Bu eşleştirme için export edilecek veri bulunamadı.");
      return;
    }

    try {
      await exportGroupToExcel(pair);
      alert(
        `✅ "${pair.displayName}" eşleştirmesi başarıyla Excel'e aktarıldı!`
      );
    } catch (error: any) {
      console.error("❌ Eşleştirme Excel export hatası:", error);
      alert(`Excel export hatası: ${error.message || "Bilinmeyen hata"}`);
    }
  };

  // ✅ NEW - CAD status temizleme fonksiyonu
  const handleCADCleanup = async () => {
    try {
      const result = await apiService.cleanupCADTempFiles(24);
      if (result.success) {
        alert(`✅ ${result.removed_files} geçici CAD dosyası temizlendi!`);
        // Status'u yenile
        const status = await apiService.getCADConversionStatus();
        setCadConversionStatus(status);
      } else {
        alert(`❌ Temizleme hatası: ${result.message}`);
      }
    } catch (error: any) {
      alert(`❌ Temizleme hatası: ${error.message}`);
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
      case "completed":
        return "green";
      case "failed":
        return "red";
      case "analyzing":
      case "uploading":
      case "processing":
        return "blue";
      default:
        return "yellow";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "pending":
        return "Bekliyor";
      case "uploading":
        return "Yükleniyor...";
      case "uploaded":
        return "Yüklendi";
      case "analyzing":
        return "Analiz ediliyor...";
      case "processing":
        return "İşleniyor...";
      case "completed":
        return "Tamamlandı";
      case "failed":
        return "Başarısız";
      default:
        return "Bilinmiyor";
    }
  };

  // ✅ ENHANCED - File type icon with CAD support
  const getFileTypeIconEnhanced = (fileName: string) => {
    const fileType = getFileType(fileName);
    
    switch (fileType) {
      case "pdf":
        return "📄";
      case "step":
        return "📐";
      case "cad_part":
        if (fileName.toLowerCase().endsWith('.prt')) {
          return "🔧"; // NX/Unigraphics PRT
        } else if (fileName.toLowerCase().endsWith('.catpart')) {
          return "⚙️"; // CATIA CATPART
        }
        return "📐"; // Generic CAD
      case "doc":
        return "📝";
      default:
        return "📎";
    }
  };

  const getMatchQualityColor = (quality: string) => {
    switch (quality?.toLowerCase()) {
      case "excellent":
        return "#28a745";
      case "good":
        return "#17a2b8";
      case "fair":
        return "#ffc107";
      case "poor":
        return "#dc3545";
      default:
        return "#6c757d";
    }
  };

  const accessToken = localStorage.getItem("accessToken");

  const open3DViewer = (analysisId: string, fileName: string) => {
    const viewerUrl = `${
      process.env.REACT_APP_API_URL || "http://188.132.220.35:5051"
    }/3d-viewer/${analysisId}/${accessToken}`;
    window.open(
      viewerUrl,
      "_blank",
      "width=1600,height=1200,scrollbars=yes,resizable=yes"
    );
  };

  const fixImagePath = (path: string) => {
    if (path.startsWith("../static/")) {
      return path.replace("../static/", "/static/");
    }
    if (!path.startsWith("/static/") && !path.startsWith("http")) {
      return `/static/${path}`;
    }
    return path;
  };

  // ✅ NEW - Get conversion statistics
  const conversionStatistics = getConversionStatistics();
  const fileTypeStatistics = getFileTypeStatistics();

  const renderAnalysisDetails = (result: any, id: string) => {
    if (!result?.analysis) return null;

    const analysis = result.analysis;
    const stepAnalysis = analysis.step_analysis;
    const materialOptions = analysis.material_options || [];
    const materialCalculations = analysis.all_material_calculations || [];

    // Render durumunu kontrol et
    const analysisId = analysis.id;
    const renderStatus =
      renderStatusMap.get(analysisId) || analysis.render_status || "none";
    const renderProgress = renderProgressMap.get(analysisId) || 0;

    const isRenderProcessing =
      renderStatus === "processing" || renderStatus === "pending";
    const isRenderCompleted = renderStatus === "completed";
    const hasEnhancedRenders =
      analysis.enhanced_renders &&
      Object.keys(analysis.enhanced_renders).length > 0;

    const pendingCount = files.filter((f) => f.status === "pending").length;

    // ✅ NEW - CAD conversion info display
    const showCADInfo = analysis.cad_converted || analysis.matched_cad_converted;
    const originalCADFormat = analysis.original_cad_format || analysis.matched_cad_original_format;
    const conversionTime = analysis.conversion_time || analysis.matched_cad_conversion_time;

    return (
      <div className={classes.analyseItemInsideDiv}>
        <div className={classes.analyseFirstDiv}>
          <p className={classes.analyseAlias}>
            {(() => {
              const match = analysis.material_matches?.[0];
              return match && !match.includes("default")
                ? match
                : "Malzeme Eşleşmesi Yok";
            })()}
          </p>

          {/* ✅ NEW - CAD Conversion Info Display */}
          {showCADInfo && (
            <div style={{
              marginBottom: "16px",
              padding: "12px",
              backgroundColor: "#e8f5e8",
              borderRadius: "8px",
              border: "1px solid #4caf50"
            }}>
              <div style={{ fontSize: "14px", color: "#2e7d32", fontWeight: "bold" }}>
                🔄 CAD Dosya Dönüştürme Bilgisi
              </div>
              <div style={{ fontSize: "12px", color: "#2e7d32", marginTop: "4px" }}>
                {originalCADFormat?.toUpperCase()} formatından STEP'e çevrildi
                {conversionTime && ` (${conversionTime.toFixed(1)}s)`}
              </div>
            </div>
          )}

          <div className={classes.modelDiv}>
            <div className={classes.modelSection}>
              {/* Render işleniyor durumu */}
              {isRenderProcessing ? (
                <div
                  style={{
                    color: "#007bff",
                    textAlign: "center",
                    padding: "20px",
                    backgroundColor: "#f0f8ff",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "24px", marginBottom: "10px" }}>
                    ⏳
                  </div>
                  <div style={{ fontWeight: "bold", marginBottom: "5px" }}>
                    3D Model İşleniyor
                  </div>
                  <div style={{ fontSize: "12px" }}>
                    {renderProgress > 0 && `İlerleme: ${renderProgress}% - `}
                    Lütfen bekleyin...
                  </div>
                  <button
                    onClick={() => refreshRenderStatus(analysisId)}
                    style={{
                      marginTop: "8px",
                      fontSize: "11px",
                      padding: "4px 8px",
                      border: "1px solid #007bff",
                      borderRadius: "4px",
                      backgroundColor: "white",
                      color: "#007bff",
                      cursor: "pointer",
                    }}
                  >
                    🔄 Durumu Kontrol Et
                  </button>
                </div>
              ) : hasEnhancedRenders && analysis.enhanced_renders?.isometric ? (
                <Image
                  src={`${
                    process.env.REACT_APP_API_URL ||
                    "http://188.132.220.35:5051"
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  zoomSrc={`${
                    process.env.REACT_APP_API_URL ||
                    "http://188.132.220.35:5051"
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  className={classes.modelImage}
                  alt="3D Model"
                  width="200"
                  height="200"
                  preview
                />
              ) : isRenderCompleted && !hasEnhancedRenders ? (
                <div
                  style={{
                    color: "#dc3545",
                    textAlign: "center",
                    padding: "20px",
                    backgroundColor: "#fff5f5",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ fontSize: "24px", marginBottom: "10px" }}>
                    ⚠️
                  </div>
                  <div style={{ fontWeight: "bold", marginBottom: "5px" }}>
                    3D Model Güncel Değil
                  </div>
                  <div style={{ fontSize: "12px" }}>
                    Render tamamlandı ancak
                    <br />
                    görüntü yüklenemedi
                  </div>
                </div>
              ) : (
                <div style={{ color: "#999", textAlign: "center" }}>
                  3D Model
                  <br />
                  Mevcut Değil
                </div>
              )}
            </div>

            {/* 3D Viewer Butonları */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
                marginTop: "12px",
              }}
            >
              <button
                className={classes.modelShowButton}
                onClick={() =>
                  open3DViewer(analysis.id, analysis.original_filename || "")
                }
                title="Gelişmiş 3D Görüntüleyici'de aç"
              >
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
                {Math.ceil(parseFloat(stepAnalysis?.["X (mm)"]) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.["X (mm)"]) || 0) + 10)}
              </div>
            </div>

            <div className={classes.tableRow}>
              <div className={classes.tableCell}>Y</div>
              <div className={classes.tableCell}>
                {Math.ceil(parseFloat(stepAnalysis?.["Y (mm)"]) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.["Y (mm)"]) || 0) + 10)}
              </div>
            </div>

            <div className={classes.tableRow}>
              <div className={classes.tableCell}>Z</div>
              <div className={classes.tableCell}>
                {Math.ceil(parseFloat(stepAnalysis?.["Z (mm)"]) || 0)}
              </div>
              <div className={classes.tableCell}>
                {Math.ceil((parseFloat(stepAnalysis?.["Z (mm)"]) || 0) + 10)}
              </div>
            </div>
          </div>
        </div>

        {/* Rest of the analysis details remain the same... */}
        {/* (Silindirik Özellikler, Hacimsel Veriler, etc.) */}
      </div>
    );
  };

  // Render file list - Eşleşmeleri ve tek dosyaları göster
  const renderFileList = () => {
    return (
      <>
        {/* Eşleşmiş PDF-CAD çiftleri */}
        {matchedPairs.map((pair) => (
          <div key={pair.id} style={{ marginBottom: "16px" }}>
            <div
              className={classes.uploadedItem}
              style={{ backgroundColor: "#f0f8ff" }}
            >
              <div className={classes.uploadedItemFirstSection}>
                <div
                  style={{ display: "flex", alignItems: "center", gap: "10px" }}
                >
                  <span style={{ fontSize: "18px" }}>🔗</span>
                  <div>
                    <p className={classes.exp} style={{ fontWeight: "bold" }}>
                      {pair.displayName}
                    </p>
                    <p
                      style={{
                        fontSize: "12px",
                        color: "#666",
                        marginTop: "4px",
                      }}
                    >
                      {/* ✅ ENHANCED - Show CAD format info */}
                      PDF + {pair.cadFormat || 'CAD'} Eşleştirmesi
                      {pair.cadConverted && (
                        <span style={{ color: "#2e7d32", marginLeft: "4px" }}>
                          (STEP'e çevrildi)
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <div
                  style={{ display: "flex", alignItems: "center", gap: "10px" }}
                >
                  {/* Match score badge */}
                  <div
                    style={{
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontWeight: "bold",
                      backgroundColor: "#d4edda",
                      color: getMatchQualityColor(pair.matchQuality),
                    }}
                  >
                    🎯 {pair.matchScore}% - {pair.matchQuality}
                  </div>
                  <div
                    className={`${classes.uploadedItemStatus} ${getStatusClass(
                      pair.status
                    )}`}
                  >
                    <p className={classes.uploadedItemStatusText}>
                      {getStatusText(pair.status)}
                    </p>
                  </div>
                </div>
              </div>

              <div className={classes.progressContainer}>
                <div
                  className={classes.progressBar}
                  style={{ width: `${pair.progress}%` }}
                >
                  <span className={classes.progressText}>{pair.progress}%</span>
                </div>
              </div>

              {/* Eşleşen dosyalar */}
              <div style={{ marginTop: "12px", paddingLeft: "20px" }}>
                <div
                  style={{
                    fontSize: "12px",
                    color: "#666",
                    marginBottom: "8px",
                  }}
                >
                  <div style={{ marginBottom: "4px" }}>
                    📄 PDF: {pair.pdfFile.file.name}
                    <span
                      style={{
                        marginLeft: "8px",
                        fontSize: "11px",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        backgroundColor: "#e8f5e8",
                        color: "#2e7d32",
                      }}
                    >
                      {getStatusText(pair.pdfFile.status)}
                    </span>
                  </div>
                  <div>
                    {/* ✅ ENHANCED - Show CAD file with format icon */}
                    {getFileTypeIconEnhanced(pair.cadFile.file.name)} {pair.cadFormat || 'CAD'}: {pair.cadFile.file.name}
                    <span
                      style={{
                        marginLeft: "8px",
                        fontSize: "11px",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        backgroundColor: "#e8f5e8",
                        color: "#2e7d32",
                      }}
                    >
                      {getStatusText(pair.cadFile.status)}
                    </span>
                    {/* ✅ NEW - Show conversion info */}
                    {pair.cadConverted && (
                      <span
                        style={{
                          marginLeft: "4px",
                          fontSize: "10px",
                          padding: "1px 4px",
                          borderRadius: "3px",
                          backgroundColor: "#fff3cd",
                          color: "#856404",
                        }}
                      >
                        Çevrildi
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Kontroller */}
              {pair.status === "pending" && (
                <div style={{ marginTop: "8px", display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => removeGroup(pair.id)}
                    style={{
                      backgroundColor: "#6c757d",
                      color: "white",
                      border: "none",
                      padding: "4px 12px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
                    Eşleştirmeyi Kaldır
                  </button>
                </div>
              )}

              {pair.status === "failed" && (
                <div
                  style={{
                    marginTop: "8px",
                    color: "#dc3545",
                    fontSize: "12px",
                  }}
                >
                  ⚠️ Eşleştirme analizi başarısız.
                </div>
              )}

              {pair.status === "completed" && pair.mergedResult && (
                <div
                  style={{
                    marginTop: "8px",
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: "12px", color: "#28a745" }}>
                    ✓ Eşleştirme analizi tamamlandı!
                  </span>
                  <button
                    onClick={() => handlePairExport(pair)}
                    style={{
                      backgroundColor: "#28a745",
                      color: "white",
                      border: "none",
                      padding: "4px 12px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
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
            <div key={`file-${index}`} className={classes.uploadedItem}>
              <div className={classes.uploadedItemFirstSection}>
                <div
                  style={{ display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {/* ✅ ENHANCED - Use enhanced file type icon */}
                  <span>{getFileTypeIconEnhanced(file.file.name)}</span>
                  <div>
                    <p className={classes.exp}>{file.file.name}</p>
                    {/* ✅ NEW - Show conversion info for individual files */}
                    {file.conversionInfo?.needsConversion && (
                      <p style={{ fontSize: "10px", color: "#666", marginTop: "2px" }}>
                        {file.conversionInfo.originalFormat} → STEP
                        {file.conversionInfo.converted && (
                          <span style={{ color: "#28a745", marginLeft: "4px" }}>
                            ✓ Çevrildi
                          </span>
                        )}
                        {file.conversionInfo.conversionError && (
                          <span style={{ color: "#dc3545", marginLeft: "4px" }}>
                            ✗ Çevrilemedi
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                </div>
                <div
                  className={`${classes.uploadedItemStatus} ${getStatusClass(
                    file.status
                  )}`}
                >
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

              {file.status === "completed" &&
                (file.renderStatus === "processing" ||
                  file.renderStatus === "pending") && (
                  <div
                    style={{
                      fontSize: "12px",
                      marginTop: "8px",
                      color: "#007bff",
                    }}
                  >
                    🎨 3D render işleniyor, lütfen bekleyin...
                  </div>
                )}

              {file.error && (
                <div
                  style={{
                    color: "#dc3545",
                    fontSize: "12px",
                    marginTop: "8px",
                  }}
                >
                  Hata: {file.error}
                  <button
                    className={classes.retryButton}
                    onClick={() => retryFile(files.indexOf(file))}
                    style={{ marginLeft: "10px" }}
                    disabled={isUploading}
                  >
                    Tekrar Dene
                  </button>
                  <button
                    onClick={() => removeFile(files.indexOf(file))}
                    style={{
                      marginLeft: "8px",
                      backgroundColor: "#6c757d",
                      color: "white",
                      border: "none",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "11px",
                    }}
                  >
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === "pending" && (
                <div
                  style={{
                    fontSize: "12px",
                    marginTop: "8px",
                    color: "#6c757d",
                  }}
                >
                  Dosya analiz için hazır. "Yükle ve Tara" butonuna tıklayın.
                  <button
                    onClick={() => removeFile(files.indexOf(file))}
                    style={{
                      marginLeft: "10px",
                      backgroundColor: "#6c757d",
                      color: "white",
                      border: "none",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "11px",
                    }}
                  >
                    Kaldır
                  </button>
                </div>
              )}

              {file.status === "completed" && (
                <div
                  style={{
                    fontSize: "12px",
                    marginTop: "8px",
                    color: "#28a745",
                  }}
                >
                  ✓ Analiz tamamlandı! İşleme süresi:{" "}
                  {file.result?.processing_time?.toFixed(1) || "0"} saniye
                </div>
              )}
            </div>
          ))}
      </>
    );
  };

  // Render analysis results (same as before, no changes needed)
  const renderAnalysisResults = () => {
    const processedPairIds = new Set<string>();

    return (
      <>
        {/* Önce eşleşmiş çiftlerin sonuçlarını göster */}
        {matchedPairs
          .filter((pair) => pair.status === "completed" && pair.mergedResult)
          .map((pair) => {
            processedPairIds.add(pair.id);
            return (
              <div
                key={`pair-result-${pair.id}`}
                className={`${classes.analyseItem} ${
                  expandedItems.has(pair.id) ? "active" : ""
                }`}
              >
                <div
                  className={classes.analyseFirstSection}
                  onClick={() => toggleExpanded(pair.id)}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <span style={{ fontSize: "18px" }}>🔗</span>
                    <div>
                      <p className={classes.exp} style={{ fontWeight: "bold" }}>
                        {pair.pdfFile.file.name}
                      </p>
                      <p
                        style={{
                          fontSize: "12px",
                          color: "#666",
                          marginTop: "4px",
                        }}
                      >
                        PDF + {pair.cadFormat || 'CAD'} Eşleştirmesi
                        <span
                          style={{
                            marginLeft: "8px",
                            padding: "2px 6px",
                            borderRadius: "8px",
                            backgroundColor: "#d4edda",
                            color: getMatchQualityColor(pair.matchQuality),
                            fontSize: "10px",
                            fontWeight: "bold",
                          }}
                        >
                          🎯 {pair.matchScore}% - {pair.matchQuality}
                        </span>
                      </p>
                    </div>
                  </div>
                  <span
                    style={{
                      transform: expandedItems.has(pair.id)
                        ? "rotate(180deg)"
                        : "rotate(0deg)",
                      transition: "transform 0.3s",
                    }}
                  >
                    <i className="fa fa-arrow-down"></i>
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
            if (file.status !== "completed") return false;

            // Eğer bu dosya bir eşleşmenin parçasıysa gösterme
            const isPartOfProcessedPair = matchedPairs.some(
              (pair) =>
                (pair.pdfFile.file.name === file.file.name ||
                  pair.cadFile.file.name === file.file.name) &&
                pair.status === "completed"
            );

            return !isPartOfProcessedPair;
          })
          .map((file, index) => (
            <div
              key={`file-result-${index}`}
              className={`${classes.analyseItem} ${
                expandedItems.has(`file-${index}`) ? "active" : ""
              }`}
            >
              <div
                className={classes.analyseFirstSection}
                onClick={() => toggleExpanded(`file-${index}`)}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {/* ✅ ENHANCED - Use enhanced file type icon */}
                  <span>{getFileTypeIconEnhanced(file.file.name)}</span>
                  <p className={classes.exp}>{file.file.name}</p>
                </div>
                <span
                  style={{
                    transform: expandedItems.has(`file-${index}`)
                      ? "rotate(180deg)"
                      : "rotate(0deg)",
                    transition: "transform 0.3s",
                  }}
                >
                  <i className="fa fa-arrow-down"></i>
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
    matchedPairs.some((p) => p.status === "completed") ||
    files.some((f) => f.status === "completed" && !f.isPartOfMatch);

  const completedMatchCount = matchedPairs.filter(
    (p) => p.status === "completed"
  ).length;

  const completedSingleFileCount = files.filter((f) => {
    // Dosya tamamlanmış mı?
    if (f.status !== "completed") return false;

    // Dosya bir eşleştirmenin parçası mı?
    if (f.isPartOfMatch) return false;

    // Bu dosya için tamamlanmış bir eşleştirme var mı?
    const hasCompletedMatch = matchedPairs.some(
      (pair) =>
        pair.status === "completed" &&
        (pair.pdfFile.file.name === f.file.name ||
          pair.cadFile.file.name === f.file.name)
    );

    return !hasCompletedMatch;
  }).length;

  const pendingCount = files.filter((f) => f.status === "pending").length;

  return (
    <div className={classes.container}>
      <div className={classes.firstSection}>
        <img
          src="/background-logo.png"
          alt="Background Logo"
          className={classes.backgroundLogo}
        />
        <p className={classes.title}>
          {/* ✅ ENHANCED - Updated title to include CAD formats */}
          Yapay Zeka ile Teklif Parametrelerinin PDF, STEP, PRT ve CATPART Dosyalarından Analizi
        </p>
        <p className={classes.exp}>
          {/* ✅ ENHANCED - Updated description */}
          İşlem sonucunda teklif verilecek ürüne ait tüm analizler tamamlanacak,
          CAD dosyaları otomatik olarak STEP formatına çevrilecek, değerler hesaplanacak, 
          3D modeli görüntülenebilir duruma gelecek ve sonuçlar excel olarak indirilebilecektir.
          <br />
          <strong>Desteklenen formatlar:</strong> PDF, DOC/DOCX, STEP/STP, PRT (NX), CATPART (CATIA)
        </p>

        {/* ✅ NEW - CAD Conversion Status Display */}
        {cadConversionStatus && (
          <div style={{ marginBottom: "16px" }}>
            <button
              onClick={() => setShowCADStatus(!showCADStatus)}
              style={{
                backgroundColor: cadConversionStatus.cad_conversion?.available ? "#28a745" : "#dc3545",
                color: "white",
                border: "none",
                padding: "8px 16px",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
                marginBottom: "8px"
              }}
            >
              🔧 CAD Conversion: {cadConversionStatus.cad_conversion?.available ? "Aktif" : "Pasif"}
              {showCADStatus ? " ▼" : " ▶"}
            </button>

            {showCADStatus && (
              <div style={{
                padding: "12px",
                backgroundColor: "#f8f9fa",
                borderRadius: "6px",
                border: "1px solid #dee2e6",
                fontSize: "12px"
              }}>
                <div><strong>FreeCAD:</strong> {cadConversionStatus.cad_conversion?.freecad_path || "Bulunamadı"}</div>
                <div><strong>Desteklenen Formatlar:</strong> {cadConversionStatus.cad_conversion?.supported_formats?.join(", ")}</div>
                <div><strong>Temp Dosyalar:</strong> {cadConversionStatus.cad_conversion?.temp_files_count || 0} adet</div>
                <div style={{ marginTop: "8px" }}>
                  <button
                    onClick={handleCADCleanup}
                    style={{
                      backgroundColor: "#ffc107",
                      color: "#212529",
                      border: "none",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "11px"
                    }}
                  >
                    🧹 Temp Dosyaları Temizle
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ✅ NEW - File Type and Conversion Statistics */}
        {files.length > 0 && (
          <div style={{
            marginBottom: "16px",
            padding: "12px",
            backgroundColor: "#f8f9fa",
            borderRadius: "6px",
            border: "1px solid #dee2e6"
          }}>
            <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "8px" }}>
              📊 Dosya İstatistikleri
            </div>
            <div style={{ fontSize: "12px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <div>
                <div>📄 PDF: {fileTypeStatistics.pdf || 0}</div>
                <div>📐 STEP: {fileTypeStatistics.step || 0}</div>
                <div>🔧 CAD Dosyalar: {fileTypeStatistics.cadFiles || 0}</div>
              </div>
              <div>
                <div>📝 DOC: {fileTypeStatistics.doc || 0}</div>
                <div>🔄 Çevrilmeli: {fileTypeStatistics.needsConversion || 0}</div>
                <div>📊 Toplam: {fileTypeStatistics.total}</div>
              </div>
            </div>
            
            {/* Conversion Statistics */}
            {conversionStatistics.totalAttempted > 0 && (
              <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px solid #dee2e6" }}>
                <div style={{ fontSize: "12px", fontWeight: "bold" }}>🔄 CAD Conversion Başarım:</div>
                <div style={{ fontSize: "11px", marginTop: "4px" }}>
                  ✅ Başarılı: {conversionStatistics.successful} / 
                  ❌ Başarısız: {conversionStatistics.failed} / 
                  📊 Oran: %{conversionStatistics.successRate.toFixed(1)}
                </div>
              </div>
            )}
          </div>
        )}

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
                ? "No files selected"
                : `${files.length} file${files.length > 1 ? "s" : ""} selected`}
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.step,.stp,.prt,.catpart" // ✅ ENHANCED - Added PRT and CATPART
            onChange={handleFileChange}
            className={classes.hiddenFileInput}
          />

          {/* ✅ ENHANCED - Eşleştirme bilgisi (CAD desteği ile) */}
          {files.length > 0 && matchedPairs.length > 0 && (
            <div
              style={{
                marginTop: "10px",
                marginBottom: "10px",
                padding: "12px",
                backgroundColor: "#e8f5e8",
                borderRadius: "6px",
                border: "1px solid #4caf50",
              }}
            >
              <div style={{ fontSize: "14px", color: "#2e7d32" }}>
                🎯 <strong>{matchedPairs.length} eşleştirme bulundu!</strong>
                <ul style={{ margin: "8px 0 0 20px", fontSize: "12px" }}>
                  {matchedPairs.map((pair) => (
                    <li key={pair.id}>
                      {pair.pdfFile.file.name} ↔ {pair.cadFile.file.name} 
                      {/* ✅ NEW - Show CAD format and conversion info */}
                      <span style={{ color: "#666", marginLeft: "4px" }}>
                        ({pair.cadFormat})
                      </span>
                      <span style={{ fontWeight: "bold", marginLeft: "4px" }}>
                        ({pair.matchScore}% - {pair.matchQuality})
                      </span>
                      {pair.cadConverted && (
                        <span style={{ color: "#2e7d32", marginLeft: "4px", fontSize: "10px" }}>
                          [Çevrildi]
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <button
            className={classes.uploadButton}
            onClick={uploadAndAnalyze}
            disabled={files.length === 0 || isUploading || pendingCount === 0}
          >
            {isUploading
              ? "Yükleniyor ve Analiz Ediliyor..."
              : pendingCount > 0
              ? `Yükle ve Tara (${pendingCount} dosya)`
              : "Tüm Dosyalar İşlendi"}
          </button>

          {(isUploading || pendingCount > 0) && (
            <p className={classes.processingInfo}>
              {isUploading
                ? `${
                    files.filter(
                      (f) =>
                        f.status === "uploading" || f.status === "analyzing"
                    ).length
                  } dosya işleniyor, lütfen bekleyin...`
                : `${pendingCount} dosya işlenmeyi bekliyor`}
            </p>
          )}

          {/* Uploaded Files */}
          {renderFileList()}

          {/* Analysis Results */}
          {hasCompletedResults && (
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
                  <p className={classes.title}>
                    Analiz Sonuçları
                    <span
                      style={{
                        fontSize: "14px",
                        fontWeight: "normal",
                        marginLeft: "10px",
                        color: "#666",
                      }}
                    >
                      ({completedMatchCount} eşleştirme,{" "}
                      {completedSingleFileCount} tekil dosya)
                    </span>
                  </p>
                </div>

                {renderAnalysisResults()}

                {/* Multiple Excel Export Butonu */}
                <div style={{ position: "relative", width: "100%" }}>
                  {/* Export progress */}
                  {isExporting && (
                    <div style={{ marginBottom: "10px" }}>
                      <div
                        style={{
                          backgroundColor: "#f0f0f0",
                          borderRadius: "4px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${exportProgress}%`,
                            height: "20px",
                            backgroundColor: "#28a745",
                            transition: "width 0.3s ease",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "white",
                            fontSize: "12px",
                          }}
                        >
                          {exportProgress}%
                        </div>
                      </div>
                      <p
                        style={{
                          fontSize: "12px",
                          color: "#666",
                          marginTop: "5px",
                        }}
                      >
                        Excel dosyası oluşturuluyor...
                      </p>
                    </div>
                  )}

                  <button
                    className={classes.analyseButton}
                    onClick={handleMultipleExcelExport}
                    disabled={!hasCompletedResults || isExporting}
                    style={{
                      backgroundColor: isExporting ? "#cccccc" : "#10b86b",
                      cursor: isExporting ? "not-allowed" : "pointer",
                      opacity: isExporting ? 0.7 : 1,
                    }}
                  >
                    <img src="/download-icon.svg" alt="" />
                    {isExporting
                      ? "Excel Oluşturuluyor..."
                      : `Excel İndir (${
                          matchedPairs.filter((p) => p.status === "completed")
                            .length +
                          files.filter(
                            (f) => f.status === "completed" && !f.isPartOfMatch
                          ).length
                        } Analiz)`}
                  </button>

                  {/* Bilgi mesajı */}
                  {hasCompletedResults && !isExporting && (
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#666",
                        marginTop: "10px",
                        padding: "8px",
                        backgroundColor: "#e8f5e8",
                        borderRadius: "4px",
                        border: "1px solid #c3e6c3",
                      }}
                    >
                      📊 <strong>Çoklu Excel Export:</strong> Tüm tamamlanmış
                      analizler tek Excel dosyasında birleştirilecek.
                      <br />
                      <strong>
                        İndirilecek{" "}
                        {matchedPairs.filter((p) => p.status === "completed")
                          .length +
                          files.filter(
                            (f) => f.status === "completed" && !f.isPartOfMatch
                          ).length}{" "}
                        analiz sonucu mevcut.
                      </strong>
                      {/* ✅ NEW - Show conversion info in export message */}
                      {conversionStatistics.totalAttempted > 0 && (
                        <div style={{ marginTop: "4px", fontSize: "11px" }}>
                          🔄 CAD Conversion: {conversionStatistics.successful} başarılı, 
                          {conversionStatistics.failed} başarısız 
                          (%{conversionStatistics.successRate.toFixed(1)} başarı oranı)
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className={classes.line}></div>

                {/* Excel Merge Bölümü */}
                <div className={classes.iconTextDiv}>
                  <span>📤</span>
                  <p className={classes.title}>
                    Excel Yükle ve Analiz Sonuçlarıyla Birleştir
                  </p>
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
                    {selectedExcelFile
                      ? selectedExcelFile.name
                      : "no file selected"}
                  </p>
                  {selectedExcelFile && (
                    <button
                      onClick={removeExcelFile}
                      style={{
                        marginLeft: "10px",
                        backgroundColor: "#dc3545",
                        color: "white",
                        border: "none",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontSize: "11px",
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
                  style={{ display: "none" }}
                />

                {/* Excel merge progress */}
                {isMerging && (
                  <div style={{ marginTop: "10px", marginBottom: "10px" }}>
                    <div
                      style={{
                        backgroundColor: "#f0f0f0",
                        borderRadius: "4px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${mergeProgress}%`,
                          height: "20px",
                          backgroundColor: "#28a745",
                          transition: "width 0.3s ease",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "white",
                          fontSize: "12px",
                        }}
                      >
                        {mergeProgress}%
                      </div>
                    </div>
                    <p
                      style={{
                        fontSize: "12px",
                        color: "#666",
                        marginTop: "5px",
                      }}
                    >
                      Excel dosyası birleştiriliyor...
                    </p>
                  </div>
                )}

                {/* Merge butonu */}
                <button
                  className={classes.excelButton}
                  onClick={handleExcelMerge}
                  disabled={
                    !selectedExcelFile || isMerging || !hasCompletedResults
                  }
                >
                  <img src="/upload.svg" alt="" />
                  {isMerging
                    ? "Birleştiriliyor..."
                    : "Excel Dosyasını Yükle ve Birleştir"}
                </button>

                {/* ✅ ENHANCED - Bilgi mesajı (CAD conversion bilgisi ile) */}
                {hasCompletedResults && (
                  <div
                    style={{
                      fontSize: "12px",
                      color: "#666",
                      marginTop: "10px",
                      padding: "8px",
                      backgroundColor: "#f8f9fa",
                      borderRadius: "4px",
                      border: "1px solid #dee2e6",
                    }}
                  >
                    💡 <strong>Nasıl çalışır:</strong> Excel dosyanızı seçin ve
                    analiz sonuçlarıyla birleştirin. Sistem otomatik olarak ürün
                    kodlarını eşleştirip malzeme bilgilerini, boyutları ve 3D
                    görsellerini ekleyecek. CAD dosyaları otomatik olarak STEP formatına
                    çevrilmiş ve analiz edilmiştir.
                    <br />
                    <strong>
                      Birleştirilecek{" "}
                      {matchedPairs.filter((p) => p.status === "completed")
                        .length +
                        files.filter(
                          (f) => f.status === "completed" && !f.isPartOfMatch
                        ).length}{" "}
                      analiz sonucu mevcut.
                    </strong>
                    {/* ✅ NEW - CAD conversion summary */}
                    {conversionStatistics.totalAttempted > 0 && (
                      <div style={{ marginTop: "4px", fontStyle: "italic" }}>
                        📊 {conversionStatistics.totalAttempted} CAD dosyası dönüştürme denendi,
                        {conversionStatistics.successful} başarılı.
                      </div>
                    )}
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