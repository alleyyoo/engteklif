// src/pages/dashboard/DashboardPage.tsx - Collapsible stability düzeltildi
import React, { useState, useRef, useCallback, useMemo } from "react";
import { DashboardPageStyles } from "./DashboardPage.styles";
import { useFileUpload, FileGroup } from "../../hooks/useFileUpload";
import { Image } from "primereact/image";
import { apiService } from "../../services/api";

export const DashboardPage = () => {
  const classes = DashboardPageStyles();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const excelInputRef = useRef<HTMLInputElement>(null);

  // ✅ DÜZELTME - Stable ID'ler için benzersiz key'ler kullan
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

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
    groupMode,
    setGroupMode,
    isUploading,
    totalProcessingTime,
    addFiles,
    removeFile,
    removeGroup,
    clearFiles,
    uploadAndAnalyze,
    retryFile,
    exportGroupToExcel,
    exportAllCompletedToExcel,
  } = useFileUpload();

  // ✅ DÜZELTME - Stable ID oluşturma (render'dan bağımsız)
  const getStableFileId = useCallback((file: any, index: number) => {
    // Dosya adı + boyut + lastModified (değişmez özellikler)
    return `file_${file.file.name.replace(/[^a-zA-Z0-9]/g, "_")}_${
      file.file.size
    }_${file.file.lastModified || index}`;
  }, []);

  const getStableGroupId = useCallback((group: FileGroup) => {
    // Grup adı + toplam dosya sayısı (değişmez özellikler)
    return `group_${group.groupName.replace(/[^a-zA-Z0-9]/g, "_")}_${
      group.totalFiles
    }`;
  }, []);

  // ✅ DÜZELTME - Memoized toggle fonksiyonu
  const toggleExpanded = useCallback((itemId: string) => {
    setExpandedItems((prev) => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(itemId)) {
        newExpanded.delete(itemId);
      } else {
        newExpanded.add(itemId);
      }
      return newExpanded;
    });
  }, []);

  const accessToken = localStorage.getItem("accessToken");

  const open3DViewer = (analysisId: string, fileName: string) => {
    const viewerUrl = `${
      process.env.REACT_APP_API_URL || "http://localhost:5050"
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

  // ✅ Grup analiz sonuçlarını render etme (değişiklik yok)
  const renderGroupAnalysisResults = (group: FileGroup) => {
    if (!group.mergedResult?.analysis) return null;

    const analysis = group.mergedResult.analysis;
    const stepAnalysis = analysis.step_analysis;
    const materialOptions = analysis.material_options || [];
    const materialCalculations = analysis.all_material_calculations || [];

    const isRenderProcessing =
      group.primaryFile?.renderStatus === "processing" ||
      group.primaryFile?.renderStatus === "pending";
    const isRenderCompleted =
      group.primaryFile?.renderStatus === "completed" ||
      analysis.render_status === "completed";
    const hasEnhancedRenders =
      analysis.enhanced_renders &&
      Object.keys(analysis.enhanced_renders).length > 0;

    return (
      <div className={classes.analyseItemInsideDiv}>
        {/* Grup Bilgileri */}
        <div
          style={{
            backgroundColor: "#e3f2fd",
            padding: "12px",
            borderRadius: "8px",
            marginBottom: "16px",
            border: "1px solid #2196f3",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginBottom: "8px",
            }}
          >
            <span style={{ fontSize: "20px" }}>📁</span>
            <h4 style={{ margin: 0, color: "#1976d2" }}>
              Grup Analizi: {group.groupName}
            </h4>
          </div>
          <div style={{ fontSize: "12px", color: "#666" }}>
            <div>
              <strong>Grup Türü:</strong> {group.groupType || "Bilinmiyor"}
            </div>
            <div>
              <strong>Toplam Dosya:</strong> {group.totalFiles}
            </div>
            <div>
              <strong>Dosya Türleri:</strong>{" "}
              {analysis.group_info?.file_types?.join(", ") || "Bilinmiyor"}
            </div>
            <div>
              <strong>STEP Dosyası:</strong>{" "}
              {group.hasStep ? "✅ Var" : "❌ Yok"}
            </div>
            <div>
              <strong>PDF Dosyası:</strong> {group.hasPdf ? "✅ Var" : "❌ Yok"}
            </div>
            {group.hasDoc && (
              <div>
                <strong>DOC Dosyası:</strong> ✅ Var
              </div>
            )}
            <div>
              <strong>Birincil Kaynak:</strong>{" "}
              {group.primaryFile?.file.name || "Bilinmiyor"}
            </div>
          </div>
        </div>

        <div className={classes.analyseFirstDiv}>
          <p className={classes.analyseAlias}>
            {(() => {
              const match = analysis.material_matches?.[0];
              return match && !match.includes("default")
                ? match
                : "Malzeme Eşleşmesi Yok";
            })()}
          </p>
          <div className={classes.modelDiv}>
            <div className={classes.modelSection}>
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
                  <div style={{ fontSize: "12px" }}>Lütfen bekleyin...</div>
                </div>
              ) : hasEnhancedRenders && analysis.enhanced_renders?.isometric ? (
                <Image
                  src={`${
                    process.env.REACT_APP_API_URL || "http://localhost:5050"
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  zoomSrc={`${
                    process.env.REACT_APP_API_URL || "http://localhost:5050"
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
                onClick={() => open3DViewer(analysis.id, group.groupName)}
                title="Gelişmiş 3D Görüntüleyici'de aç"
              >
                🎯 3D Modeli Görüntüle
              </button>
            </div>
          </div>
        </div>

        <div className={classes.line}></div>

        <p className={classes.titleSmall}>Grup Detaylı Analiz Tablosu</p>

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
              {stepAnalysis?.["Prizma Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Ürün Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Ürün Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Talaş Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Oranı(%)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Talaş Oranı (%)"] || "0.0"}
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

            {materialCalculations.slice(0, 1).map((calc: any, idx: any) => (
              <React.Fragment key={idx}>
                <div
                  className={classes.analyseInsideItem}
                  style={{
                    backgroundColor: "#f8f9fa",
                    paddingTop: "20px",
                    paddingBottom: "20px",
                  }}
                >
                  <p>
                    {calc.category
                      ? `Malzeme: ${calc.original_text}`
                      : "Malzeme bilgisi mevcut değil."}
                  </p>
                </div>
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Prizma Hacmi(mm³)</p>
                  <p className={classes.analyseItemExp}>{calc.volume_mm3}</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>
                    Özkütle(g/cm³)({calc.material})
                  </p>
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
                  <p className={classes.analyseItemExp}>
                    {calc.material_cost} USD
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Toplam Yüzey Alanı</p>
                  <p className={classes.analyseItemExp}>
                    {stepAnalysis?.["Toplam Yüzey Alanı (mm²)"] || "0"} mm²
                  </p>
                </div>
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Grup Excel Export Butonu */}
        <div
          style={{
            marginTop: "20px",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <button
            className={classes.excelButton}
            onClick={() => exportGroupToExcel(group)}
            style={{ width: "300px" }}
          >
            <img src="/download-icon.svg" alt="" />
            Bu Grup için Excel İndir
          </button>
        </div>
      </div>
    );
  };

  // Normal dosya analiz sonuçlarını render etme (değişiklik yok)
  const renderAnalysisResults = (file: any, fileUniqueId: string) => {
    if (!file.result?.analysis) return null;

    const analysis = file.result.analysis;
    const stepAnalysis = analysis.step_analysis;
    const materialOptions = analysis.material_options || [];
    const materialCalculations = analysis.all_material_calculations || [];

    const isRenderProcessing =
      file.renderStatus === "processing" || file.renderStatus === "pending";
    const isRenderCompleted =
      file.renderStatus === "completed" ||
      analysis.render_status === "completed";
    const hasEnhancedRenders =
      analysis.enhanced_renders &&
      Object.keys(analysis.enhanced_renders).length > 0;

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
          <div className={classes.modelDiv}>
            <div className={classes.modelSection}>
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
                  <div style={{ fontSize: "12px" }}>Lütfen bekleyin...</div>
                </div>
              ) : hasEnhancedRenders && analysis.enhanced_renders?.isometric ? (
                <Image
                  src={`${
                    process.env.REACT_APP_API_URL || "http://localhost:5050"
                  }${fixImagePath(
                    analysis.enhanced_renders.isometric.file_path
                  )}`}
                  zoomSrc={`${
                    process.env.REACT_APP_API_URL || "http://localhost:5050"
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
                onClick={() => open3DViewer(analysis.id, file.file.name)}
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

        {/* Silindirik Özellikler */}
        <div className={classes.analyseItemInsideDiv}>
          <div className={classes.analyseSubtitleDiv}>
            <span>🌀</span>
            <p className={classes.titleSmall}>Silindirik Özellikler</p>
          </div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Silindirik Çap(mm)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Silindirik Çap (mm)"] || "0.0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Silindirik Yükseklik(mm)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Silindirik Yükseklik (mm)"] || "0.0"}
            </p>
          </div>
        </div>

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
              {stepAnalysis?.["Prizma Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Ürün Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Ürün Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Hacmi(mm³)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Talaş Hacmi (mm³)"] || "0"}
            </p>
          </div>
          <div className={classes.lineAnalyseItem}></div>

          <div className={classes.analyseInsideItem}>
            <p className={classes.analyseItemTitle}>Talaş Oranı(%)</p>
            <p className={classes.analyseItemExp}>
              {stepAnalysis?.["Talaş Oranı (%)"] || "0.0"}
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

            {materialCalculations.map((calc: any, idx: any) => (
              <React.Fragment key={idx}>
                <div
                  className={classes.analyseInsideItem}
                  style={{
                    backgroundColor: "#f8f9fa",
                    paddingTop: "20px",
                    paddingBottom: "20px",
                  }}
                >
                  <p>
                    {calc.category
                      ? `Malzeme: ${calc.original_text}`
                      : "Malzeme bilgisi mevcut değil."}
                  </p>
                </div>
                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Prizma Hacmi(mm³)</p>
                  <p className={classes.analyseItemExp}>{calc.volume_mm3}</p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>
                    Özkütle(g/cm³)({calc.material})
                  </p>
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
                  <p className={classes.analyseItemExp}>
                    {calc.material_cost} USD
                  </p>
                </div>
                <div className={classes.lineAnalyseItem}></div>

                <div className={classes.analyseInsideItem}>
                  <p className={classes.analyseItemTitle}>Toplam Yüzey Alanı</p>
                  <p className={classes.analyseItemExp}>
                    {stepAnalysis?.["Toplam Yüzey Alanı (mm²)"] || "0"} mm²
                  </p>
                </div>
                {idx < materialCalculations.length - 1 && (
                  <div className={classes.lineAnalyseItem}></div>
                )}
              </React.Fragment>
            ))}
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

  // ✅ DÜZELTME - Stable key'ler ile memoized components
  const MemoizedGroupAnalysisItem = React.memo(
    ({
      group,
      stableId,
      isExpanded,
      onToggle,
    }: {
      group: FileGroup;
      stableId: string;
      isExpanded: boolean;
      onToggle: () => void;
    }) => {
      if (group.status !== "completed") return null;

      return (
        <div className={`${classes.analyseItem} ${isExpanded ? "active" : ""}`}>
          <div className={classes.analyseFirstSection} onClick={onToggle}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontSize: "18px" }}>📁</span>
              <div>
                <p className={classes.exp} style={{ fontWeight: "bold" }}>
                  {group.groupName}
                </p>
                <p
                  style={{
                    fontSize: "11px",
                    color: "#666",
                    margin: 0,
                  }}
                >
                  {group.groupType} - {group.totalFiles} dosya
                </p>
              </div>
            </div>
            <span
              style={{
                transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.3s",
              }}
            >
              <i className="fa fa-arrow-down"></i>
            </span>
          </div>

          {isExpanded && renderGroupAnalysisResults(group)}
        </div>
      );
    },
    // ✅ DÜZELTME - Custom comparison function
    (prevProps, nextProps) => {
      return (
        prevProps.stableId === nextProps.stableId &&
        prevProps.isExpanded === nextProps.isExpanded &&
        prevProps.group.status === nextProps.group.status &&
        prevProps.group.progress === nextProps.group.progress &&
        // Render durumu karşılaştırması
        prevProps.group.primaryFile?.renderStatus ===
          nextProps.group.primaryFile?.renderStatus
      );
    }
  );

  const MemoizedIndividualAnalysisItem = React.memo(
    ({
      file,
      stableId,
      isExpanded,
      onToggle,
    }: {
      file: any;
      stableId: string;
      isExpanded: boolean;
      onToggle: () => void;
    }) => {
      if (file.status !== "completed") return null;

      return (
        <div className={`${classes.analyseItem} ${isExpanded ? "active" : ""}`}>
          <div className={classes.analyseFirstSection} onClick={onToggle}>
            <p className={classes.exp}>{file.file.name}</p>
            <span
              style={{
                transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.3s",
              }}
            >
              <i className="fa fa-arrow-down"></i>
            </span>
          </div>

          {isExpanded && renderAnalysisResults(file, stableId)}
        </div>
      );
    },
    // ✅ DÜZELTME - Custom comparison function
    (prevProps, nextProps) => {
      return (
        prevProps.stableId === nextProps.stableId &&
        prevProps.isExpanded === nextProps.isExpanded &&
        prevProps.file.status === nextProps.file.status &&
        prevProps.file.progress === nextProps.file.progress &&
        prevProps.file.renderStatus === nextProps.file.renderStatus
      );
    }
  );

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

    let analysisIds: string[] = [];

    if (groupMode) {
      const completedGroups = fileGroups.filter(
        (g) => g.status === "completed" && g.mergedResult
      );
      if (completedGroups.length === 0) {
        alert(
          "Birleştirilecek grup analizi bulunamadı. Önce dosyalarınızı analiz edin."
        );
        return;
      }
      analysisIds = completedGroups.map((g) => g.mergedResult!.analysis.id);
    } else {
      const completedAnalyses = files.filter(
        (f) => f.status === "completed" && f.result?.analysis?.id
      );
      if (completedAnalyses.length === 0) {
        alert(
          "Birleştirilecek analiz sonucu bulunamadı. Önce dosyalarınızı analiz edin."
        );
        return;
      }
      analysisIds = completedAnalyses.map((f) => f.result!.analysis.id);
    }

    setIsMerging(true);
    setMergeProgress(10);

    try {
      console.log("📊 Excel merge başlıyor...", {
        excelFile: selectedExcelFile.name,
        analysisCount: analysisIds.length,
        mode: groupMode ? "group" : "individual",
      });

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
    let completedCount = 0;

    if (groupMode) {
      completedCount = fileGroups.filter(
        (g) => g.status === "completed" && g.mergedResult
      ).length;
    } else {
      completedCount = files.filter(
        (f) => f.status === "completed" && f.result?.analysis?.id
      ).length;
    }

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
        mode: groupMode ? "group" : "individual",
      });

      setExportProgress(30);

      const result = await exportAllCompletedToExcel();

      setExportProgress(80);

      if (result.success) {
        console.log("✅ Multiple Excel export başarılı:", result.filename);

        setExportProgress(100);

        setTimeout(() => {
          alert(
            `✅ ${completedCount} ${
              groupMode ? "grup" : "dosya"
            } analizi başarıyla Excel'e aktarıldı ve indirildi!\n\nDosya: ${
              result.filename
            }`
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

  return (
    <div className={classes.container}>
      <div className={classes.firstSection}>
        <img
          src="/background-logo.png"
          alt="Background Logo"
          className={classes.backgroundLogo}
        />
        <p className={classes.title}>
          Yapay Zeka ile Teklif Parametrelerinin PDF ve STEP Dosyalarından
          Analizi
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
          {/* Grup Modu Toggle */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "16px",
              padding: "12px",
              backgroundColor: "#f8f9fa",
              borderRadius: "8px",
              border: "1px solid #dee2e6",
            }}
          >
            <span style={{ fontSize: "16px" }}>📁</span>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "500",
                color: "#495057",
              }}
            >
              <input
                type="checkbox"
                checked={groupMode}
                onChange={(e) => setGroupMode(e.target.checked)}
                style={{ transform: "scale(1.2)" }}
              />
              Aynı isimli dosyaları grup halinde analiz et
            </label>
            {groupMode && (
              <span
                style={{
                  fontSize: "12px",
                  color: "#6c757d",
                  fontStyle: "italic",
                  marginLeft: "8px",
                }}
              >
                (Aynı projeye ait dosyalar otomatik gruplandırılır)
              </span>
            )}
          </div>

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
                : groupMode
                ? `${files.length} file${
                    files.length > 1 ? "s" : ""
                  } selected (${fileGroups.length} group${
                    fileGroups.length !== 1 ? "s" : ""
                  })`
                : `${files.length} file${files.length > 1 ? "s" : ""} selected`}
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
            disabled={
              files.length === 0 ||
              isUploading ||
              !files.some((f) => f.status === "pending")
            }
          >
            {isUploading
              ? "Yükleniyor ve Analiz Ediliyor..."
              : files.some((f) => f.status === "pending")
              ? `Yükle ve Tara (${
                  files.filter((f) => f.status === "pending").length
                } dosya)`
              : "Tüm Dosyalar İşlendi"}
          </button>

          {(isUploading || files.some((f) => f.status === "pending")) && (
            <p className={classes.processingInfo}>
              {isUploading
                ? `${
                    files.filter(
                      (f) =>
                        f.status === "uploading" || f.status === "analyzing"
                    ).length
                  } dosya işleniyor, lütfen bekleyin...`
                : `${
                    files.filter((f) => f.status === "pending").length
                  } dosya işlenmeyi bekliyor`}
            </p>
          )}

          {/* Grup Modu: Grup Kartları */}
          {groupMode &&
            fileGroups.map((group) => (
              <div key={group.groupId} className={classes.uploadedItem}>
                <div className={classes.uploadedItemFirstSection}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <span style={{ fontSize: "18px" }}>📁</span>
                    <div>
                      <p className={classes.exp} style={{ fontWeight: "bold" }}>
                        {group.groupName} ({group.totalFiles} dosya)
                      </p>
                      <p style={{ fontSize: "11px", color: "#666", margin: 0 }}>
                        {group.groupType} -{" "}
                        {group.files.map((f) => f.file.name).join(", ")}
                      </p>
                    </div>
                  </div>
                  <div
                    className={`${classes.uploadedItemStatus} ${getStatusClass(
                      group.status
                    )}`}
                  >
                    <p className={classes.uploadedItemStatusText}>
                      {getStatusText(group.status)}
                    </p>
                  </div>
                </div>

                <div className={classes.progressContainer}>
                  <div
                    className={classes.progressBar}
                    style={{ width: `${group.progress}%` }}
                  >
                    <span className={classes.progressText}>
                      {group.progress}%
                    </span>
                  </div>
                </div>

                <div
                  style={{ fontSize: "12px", marginTop: "8px", width: "100%" }}
                >
                  {group.files.map((file, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        width: "100%",
                        padding: "4px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      <span>{file.file.name}</span>
                      <span
                        className={`${
                          classes.uploadedItemStatus
                        } ${getStatusClass(file.status)}`}
                        style={{ fontSize: "10px", padding: "2px 6px" }}
                      >
                        {getStatusText(file.status)}
                      </span>
                    </div>
                  ))}
                </div>

                {group.status === "completed" && (
                  <div
                    style={{
                      fontSize: "12px",
                      marginTop: "8px",
                      color: "#28a745",
                    }}
                  >
                    ✓ Grup analizi tamamlandı! Birincil kaynak:{" "}
                    {group.primaryFile?.file.name}
                  </div>
                )}

                {group.status === "failed" && (
                  <div
                    style={{
                      fontSize: "12px",
                      marginTop: "8px",
                      color: "#dc3545",
                    }}
                  >
                    ❌ Grup analizi başarısız oldu.
                    <button
                      onClick={() => removeGroup(group.groupId)}
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
                      Grubu Kaldır
                    </button>
                  </div>
                )}
              </div>
            ))}

          {/* Normal Mod: Individual Dosyalar */}
          {(!groupMode
            ? files
            : files.filter(
                (file) =>
                  !fileGroups.some((group) => group.files.includes(file))
              )
          ).map((file, index) => (
            <div key={index} className={classes.uploadedItem}>
              <div className={classes.uploadedItemFirstSection}>
                <p className={classes.exp}>{file.file.name}</p>
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
                    onClick={() => retryFile(index)}
                    style={{ marginLeft: "10px" }}
                    disabled={isUploading}
                  >
                    Tekrar Dene
                  </button>
                  <button
                    onClick={() => removeFile(index)}
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
                    onClick={() => removeFile(index)}
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

          {/* Analysis Results */}
          {((!groupMode && files.some((f) => f.status === "completed")) ||
            (groupMode &&
              fileGroups.some((g) => g.status === "completed"))) && (
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
                    {groupMode ? "Grup Analiz Sonuçları" : "Analiz Sonuçları"}
                  </p>
                </div>

                {/* ✅ DÜZELTME - Stable key'ler ile Group Sonuçları */}
                {groupMode &&
                  fileGroups.map((group) => {
                    const stableId = getStableGroupId(group);
                    return (
                      <MemoizedGroupAnalysisItem
                        key={stableId}
                        group={group}
                        stableId={stableId}
                        isExpanded={expandedItems.has(stableId)}
                        onToggle={() => toggleExpanded(stableId)}
                      />
                    );
                  })}

                {/* ✅ DÜZELTME - Stable key'ler ile Individual Sonuçlar */}
                {!groupMode &&
                  files.map((file, index) => {
                    const stableId = getStableFileId(file, index);
                    return (
                      <MemoizedIndividualAnalysisItem
                        key={stableId}
                        file={file}
                        stableId={stableId}
                        isExpanded={expandedItems.has(stableId)}
                        onToggle={() => toggleExpanded(stableId)}
                      />
                    );
                  })}

                {/* Multiple Excel Export Butonu */}
                <div style={{ position: "relative", width: "100%" }}>
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
                    disabled={
                      (!groupMode &&
                        !files.some((f) => f.status === "completed")) ||
                      (groupMode &&
                        !fileGroups.some((g) => g.status === "completed")) ||
                      isExporting
                    }
                    style={{
                      backgroundColor: isExporting ? "#cccccc" : "#10b86b",
                      cursor: isExporting ? "not-allowed" : "pointer",
                      opacity: isExporting ? 0.7 : 1,
                    }}
                  >
                    <img src="/download-icon.svg" alt="" />
                    {isExporting
                      ? "Excel Oluşturuluyor..."
                      : groupMode
                      ? `Excel İndir (${
                          fileGroups.filter((g) => g.status === "completed")
                            .length
                        } Grup)`
                      : `Excel İndir (${
                          files.filter((f) => f.status === "completed").length
                        } Analiz)`}
                  </button>

                  {((groupMode &&
                    fileGroups.some((g) => g.status === "completed")) ||
                    (!groupMode &&
                      files.some((f) => f.status === "completed"))) &&
                    !isExporting && (
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
                        📊{" "}
                        <strong>
                          {groupMode ? "Grup" : "Çoklu"} Excel Export:
                        </strong>
                        {groupMode
                          ? ` Tüm tamamlanmış grup analizleri tek Excel dosyasında birleştirilecek. Her grup için en iyi veri kullanılacak.`
                          : ` Tüm tamamlanmış analizler tek Excel dosyasında birleştirilecek. Her analiz için ayrı satır oluşturulacak ve 3D görseller dahil edilecek.`}
                        <br />
                        <strong>
                          İndirilecek{" "}
                          {groupMode
                            ? `${
                                fileGroups.filter(
                                  (g) => g.status === "completed"
                                ).length
                              } grup analizi`
                            : `${
                                files.filter((f) => f.status === "completed")
                                  .length
                              } analiz sonucu`}{" "}
                          mevcut.
                        </strong>
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

                <input
                  ref={excelInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleExcelFileChange}
                  style={{ display: "none" }}
                />

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

                <button
                  className={classes.excelButton}
                  onClick={handleExcelMerge}
                  disabled={
                    !selectedExcelFile ||
                    isMerging ||
                    (!groupMode &&
                      !files.some((f) => f.status === "completed")) ||
                    (groupMode &&
                      !fileGroups.some((g) => g.status === "completed"))
                  }
                >
                  <img src="/upload.svg" alt="" />
                  {isMerging
                    ? "Birleştiriliyor..."
                    : "Excel Dosyasını Yükle ve Birleştir"}
                </button>

                {/* Bilgi mesajı */}
                {((groupMode &&
                  fileGroups.some((g) => g.status === "completed")) ||
                  (!groupMode &&
                    files.some((f) => f.status === "completed"))) && (
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
                    görsellerini ekleyecek.
                    <br />
                    <strong>
                      Birleştirilecek{" "}
                      {groupMode
                        ? `${
                            fileGroups.filter((g) => g.status === "completed")
                              .length
                          } grup analizi`
                        : `${
                            files.filter((f) => f.status === "completed").length
                          } analiz sonucu`}{" "}
                      mevcut.
                    </strong>
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
