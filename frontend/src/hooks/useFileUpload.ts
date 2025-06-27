import { useEffect, useState, useCallback, useRef } from "react";
import {
  apiService,
  FileUploadResponse,
  AnalysisResult,
  RenderStatusResponse,
} from "../services/api";

export interface UploadedFile {
  file: File;
  analysisId?: string;
  status:
    | "pending"
    | "uploading"
    | "uploaded"
    | "analyzing"
    | "completed"
    | "failed";
  progress: number;
  error?: string;
  result?: AnalysisResult;
  renderStatus?: "none" | "pending" | "processing" | "completed" | "failed";
  renderCheckInterval?: NodeJS.Timer;
}

// ✅ GÜNCELLENMIŞ - Dosya grubu interface'i
export interface FileGroup {
  groupId: string;
  groupName: string; // Ortak dosya ismi (uzantısız)
  groupType: string; // ✅ YENİ - Grup türü açıklaması
  files: UploadedFile[];
  mergedResult?: AnalysisResult; // Birleştirilmiş sonuç
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  primaryFile?: UploadedFile; // En detaylı veriye sahip dosya
  hasStep: boolean;
  hasPdf: boolean;
  hasDoc: boolean; // ✅ YENİ - DOC dosyası kontrolü
  totalFiles: number;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [fileGroups, setFileGroups] = useState<FileGroup[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [totalProcessingTime, setTotalProcessingTime] = useState(0);
  const [groupMode, setGroupMode] = useState(true);

  // Interval'leri takip etmek için ref kullan
  const intervalsRef = useRef<Map<string, NodeJS.Timer>>(new Map());

  // ✅ GÜNCELLENMIŞ - Dosya ismi normalize etme fonksiyonu
  const normalizeFileName = useCallback((fileName: string): string => {
    // Uzantıyı kaldır ve normalize et
    return fileName
      .replace(/\.[^/.]+$/, "") // Uzantıyı kaldır (.pdf, .step, .stp, .doc, .docx)
      .replace(/[_\-\s]+/g, "_") // Boşluk, tire ve alt çizgiyi normalize et
      .toLowerCase()
      .trim();
  }, []);

  // ✅ GÜNCELLENMIŞ - Dosya türü belirleme fonksiyonu
  const getFileType = useCallback((fileName: string): string => {
    const lowerName = fileName.toLowerCase();
    if (lowerName.endsWith(".pdf")) return "pdf";
    if (lowerName.endsWith(".step") || lowerName.endsWith(".stp"))
      return "step";
    if (lowerName.endsWith(".doc") || lowerName.endsWith(".docx")) return "doc";
    return "other";
  }, []);

  // ✅ TAMAMEN YENİDEN YAZILMIŞ - Gelişmiş gruplama fonksiyonu
  const groupFilesByName = useCallback(
    (fileList: UploadedFile[]): FileGroup[] => {
      if (!groupMode) return [];

      const groupMap = new Map<string, UploadedFile[]>();

      // Dosyaları normalize edilmiş isme göre grupla
      fileList.forEach((file) => {
        const normalizedName = normalizeFileName(file.file.name);
        if (!groupMap.has(normalizedName)) {
          groupMap.set(normalizedName, []);
        }
        groupMap.get(normalizedName)!.push(file);
      });

      // Grupları filtrele ve oluştur
      return Array.from(groupMap.entries())
        .filter(([_, files]) => {
          // Grup oluşturma kriterleri:
          // 1. Birden fazla dosya var
          // 2. VEYA tek dosya ama özel türlerden (step, pdf, doc)
          return (
            files.length > 1 ||
            files.some((f) => {
              const type = getFileType(f.file.name);
              return ["pdf", "step", "doc"].includes(type);
            })
          );
        })
        .map(([groupName, groupFiles]) => {
          // Dosya türlerini analiz et
          const fileTypes = groupFiles.map((f) => getFileType(f.file.name));
          const hasStep = fileTypes.includes("step");
          const hasPdf = fileTypes.includes("pdf");
          const hasDoc = fileTypes.includes("doc");

          // Grup türü belirleme
          let groupType = "";
          if (groupFiles.length === 1) {
            groupType = "Single File";
          } else if (hasStep && hasPdf && hasDoc) {
            groupType = "PDF + STEP + DOC";
          } else if (hasStep && hasPdf) {
            groupType = "PDF + STEP";
          } else if (hasStep && hasDoc) {
            groupType = "STEP + DOC";
          } else if (hasPdf && hasDoc) {
            groupType = "PDF + DOC";
          } else if (
            hasStep &&
            fileTypes.filter((t) => t === "step").length > 1
          ) {
            groupType = `Multiple STEP (${
              fileTypes.filter((t) => t === "step").length
            })`;
          } else if (
            hasPdf &&
            fileTypes.filter((t) => t === "pdf").length > 1
          ) {
            groupType = `Multiple PDF (${
              fileTypes.filter((t) => t === "pdf").length
            })`;
          } else if (
            hasDoc &&
            fileTypes.filter((t) => t === "doc").length > 1
          ) {
            groupType = `Multiple DOC (${
              fileTypes.filter((t) => t === "doc").length
            })`;
          } else {
            groupType = `Mixed Files (${groupFiles.length})`;
          }

          // Primary dosyayı belirle
          const primaryFile = determinePrimaryFile(groupFiles);

          // Grup durumunu hesapla
          const groupStatus = calculateGroupStatus(groupFiles);
          const groupProgress = calculateGroupProgress(groupFiles);

          return {
            groupId: `group_${groupName}_${Date.now()}_${Math.random()
              .toString(36)
              .substr(2, 9)}`,
            groupName,
            groupType,
            files: groupFiles,
            status: groupStatus,
            progress: groupProgress,
            primaryFile,
            hasStep,
            hasPdf,
            hasDoc,
            totalFiles: groupFiles.length,
          };
        });
    },
    [groupMode, normalizeFileName, getFileType]
  );

  // ✅ GÜNCELLENMIŞ - Primary dosya belirleme (daha akıllı)
  const determinePrimaryFile = (
    groupFiles: UploadedFile[]
  ): UploadedFile | undefined => {
    // 1. Öncelik: Tamamlanmış STEP dosyası (en detaylı geometri)
    const completedStep = groupFiles.find(
      (f) =>
        f.status === "completed" &&
        getFileType(f.file.name) === "step" &&
        f.result?.analysis?.step_analysis
    );
    if (completedStep) return completedStep;

    // 2. Öncelik: Tamamlanmış PDF (STEP çıkarılmış)
    const completedPdfWithStep = groupFiles.find(
      (f) =>
        f.status === "completed" &&
        getFileType(f.file.name) === "pdf" &&
        f.result?.analysis?.step_analysis &&
        f.result?.analysis?.pdf_step_extracted
    );
    if (completedPdfWithStep) return completedPdfWithStep;

    // 3. Öncelik: En çok malzeme eşleşmesi olan
    const fileWithMostMaterials = groupFiles
      .filter(
        (f) => f.status === "completed" && f.result?.analysis?.material_matches
      )
      .sort(
        (a, b) =>
          (b.result?.analysis?.material_matches?.length || 0) -
          (a.result?.analysis?.material_matches?.length || 0)
      )[0];
    if (fileWithMostMaterials) return fileWithMostMaterials;

    // 4. Öncelik: En büyük dosya boyutu (daha çok veri içerebilir)
    const largestFile = groupFiles
      .filter((f) => f.status === "completed")
      .sort((a, b) => b.file.size - a.file.size)[0];
    if (largestFile) return largestFile;

    // 5. Fallback: İlk tamamlanmış dosya
    const firstCompleted = groupFiles.find((f) => f.status === "completed");
    if (firstCompleted) return firstCompleted;

    // 6. Son fallback: Dosya türü önceliğine göre (STEP > PDF > DOC)
    const stepFile = groupFiles.find(
      (f) => getFileType(f.file.name) === "step"
    );
    if (stepFile) return stepFile;

    const pdfFile = groupFiles.find((f) => getFileType(f.file.name) === "pdf");
    if (pdfFile) return pdfFile;

    // 7. En son fallback: İlk dosya
    return groupFiles[0];
  };

  // Grup durumu hesaplama (değişiklik yok)
  const calculateGroupStatus = (
    groupFiles: UploadedFile[]
  ): FileGroup["status"] => {
    const statuses = groupFiles.map((f) => f.status);

    if (statuses.every((s) => s === "completed")) return "completed";
    if (statuses.some((s) => s === "failed")) return "failed";
    if (statuses.some((s) => s === "analyzing" || s === "uploading"))
      return "processing";
    return "pending";
  };

  // Grup progress hesaplama (değişiklik yok)
  const calculateGroupProgress = (groupFiles: UploadedFile[]): number => {
    if (groupFiles.length === 0) return 0;
    const totalProgress = groupFiles.reduce(
      (sum, file) => sum + file.progress,
      0
    );
    return Math.round(totalProgress / groupFiles.length);
  };

  // ✅ GÜNCELLENMIŞ - Grup sonuçlarını birleştirme
  const mergeGroupResults = useCallback(
    (group: FileGroup): AnalysisResult | undefined => {
      const completedFiles = group.files.filter(
        (f) => f.status === "completed" && f.result
      );
      if (completedFiles.length === 0) return undefined;

      const primaryResult = group.primaryFile?.result;
      if (!primaryResult) return completedFiles[0].result;

      // Birleştirilmiş sonuç oluştur
      const mergedResult: AnalysisResult = {
        ...primaryResult,
        // En iyi analizi kullan
        analysis: {
          ...primaryResult.analysis,
          // STEP analizi - en detaylısını kullan
          step_analysis: getBestStepAnalysis(completedFiles),
          // Malzeme eşleşmeleri - en kapsamlısını kullan
          material_matches: getBestMaterialMatches(completedFiles),
          // Malzeme hesaplamaları - en detaylısını kullan
          all_material_calculations:
            getBestMaterialCalculations(completedFiles),
          // Render - en kalitelisini kullan
          enhanced_renders: getBestRenders(completedFiles),
          // Grup bilgileri - detaylı
          group_info: {
            group_id: group.groupId,
            group_name: group.groupName,
            group_type: group.groupType,
            total_files: group.totalFiles,
            file_types: [
              ...new Set(group.files.map((f) => getFileType(f.file.name))),
            ],
            file_names: group.files.map((f) => f.file.name),
            has_step: group.hasStep,
            has_pdf: group.hasPdf,
            has_doc: group.hasDoc,
            primary_source: group.primaryFile?.file.name || "",
            analysis_sources: completedFiles.length,
          },
        },
        // Analysis details - grup bilgisi ekle
        analysis_details: {
          ...primaryResult.analysis_details,
          grouped_analysis: true,
          source_files: completedFiles.length,
          primary_source: group.primaryFile?.file.name || "",
          group_composition: group.groupType,
        },
      };

      return mergedResult;
    },
    [getFileType]
  );

  // ✅ GÜNCELLENMIŞ - Helper fonksiyonlar
  const getBestStepAnalysis = (files: UploadedFile[]) => {
    // 1. STEP dosyasından gelen analizi öncelikle kullan
    const stepFileResult = files.find(
      (f) =>
        getFileType(f.file.name) === "step" && f.result?.analysis?.step_analysis
    );
    if (stepFileResult) return stepFileResult.result!.analysis.step_analysis;

    // 2. PDF'den çıkarılan STEP analizi
    const pdfWithStepResult = files.find(
      (f) =>
        getFileType(f.file.name) === "pdf" &&
        f.result?.analysis?.step_analysis &&
        f.result?.analysis?.pdf_step_extracted
    );
    if (pdfWithStepResult)
      return pdfWithStepResult.result!.analysis.step_analysis;

    // 3. En detaylı step analizi
    const filesWithStep = files.filter(
      (f) => f.result?.analysis?.step_analysis
    );
    const mostDetailedStep = filesWithStep.sort((a, b) => {
      const aKeys = Object.keys(a.result?.analysis?.step_analysis || {}).length;
      const bKeys = Object.keys(b.result?.analysis?.step_analysis || {}).length;
      return bKeys - aKeys;
    })[0];

    return mostDetailedStep?.result?.analysis?.step_analysis || {};
  };

  const getBestMaterialMatches = (files: UploadedFile[]) => {
    // En çok eşleşmesi olan dosyayı kullan
    const sortedByMatches = files
      .filter((f) => f.result?.analysis?.material_matches)
      .sort(
        (a, b) =>
          (b.result?.analysis?.material_matches?.length || 0) -
          (a.result?.analysis?.material_matches?.length || 0)
      );

    if (sortedByMatches.length > 0) {
      return sortedByMatches[0].result!.analysis.material_matches;
    }

    return [];
  };

  // ✅ YENİ - En iyi malzeme hesaplamalarını getir
  const getBestMaterialCalculations = (files: UploadedFile[]) => {
    const sortedByCalculations = files
      .filter((f) => f.result?.analysis?.all_material_calculations)
      .sort(
        (a, b) =>
          (b.result?.analysis?.all_material_calculations?.length || 0) -
          (a.result?.analysis?.all_material_calculations?.length || 0)
      );

    if (sortedByCalculations.length > 0) {
      return sortedByCalculations[0].result!.analysis.all_material_calculations;
    }

    return [];
  };

  const getBestRenders = (files: UploadedFile[]) => {
    // 1. STEP dosyasından gelen render'ları öncelikle kullan
    const stepFileResult = files.find(
      (f) =>
        getFileType(f.file.name) === "step" &&
        f.result?.analysis?.enhanced_renders &&
        Object.keys(f.result.analysis.enhanced_renders).length > 0
    );
    if (stepFileResult) return stepFileResult.result!.analysis.enhanced_renders;

    // 2. En çok render'ı olan dosya
    const sortedByRenders = files
      .filter((f) => f.result?.analysis?.enhanced_renders)
      .sort((a, b) => {
        const aRenderCount = Object.keys(
          a.result?.analysis?.enhanced_renders || {}
        ).length;
        const bRenderCount = Object.keys(
          b.result?.analysis?.enhanced_renders || {}
        ).length;
        return bRenderCount - aRenderCount;
      });

    if (sortedByRenders.length > 0) {
      return sortedByRenders[0].result!.analysis.enhanced_renders;
    }

    return {};
  };

  // ✅ Dosyalar değiştiğinde grupları güncelle
  useEffect(() => {
    if (groupMode) {
      const groups = groupFilesByName(files);

      // Grup sonuçlarını güncelle
      const updatedGroups = groups.map((group) => ({
        ...group,
        mergedResult: mergeGroupResults(group),
      }));

      // Sadece gerçekten değişiklik varsa güncelle
      setFileGroups((prevGroups) => {
        // Grup sayısı değişti mi kontrol et
        if (prevGroups.length !== updatedGroups.length) {
          return updatedGroups;
        }

        // Her grup için değişiklik var mı kontrol et
        const hasChanges = updatedGroups.some((newGroup, index) => {
          const oldGroup = prevGroups[index];
          if (!oldGroup) return true;

          // Status veya progress değişti mi?
          if (
            oldGroup.status !== newGroup.status ||
            oldGroup.progress !== newGroup.progress
          ) {
            return true;
          }

          // Dosya durumları değişti mi?
          const filesChanged = newGroup.files.some((newFile, fileIndex) => {
            const oldFile = oldGroup.files[fileIndex];
            if (!oldFile) return true;
            return (
              oldFile.status !== newFile.status ||
              oldFile.progress !== newFile.progress ||
              oldFile.renderStatus !== newFile.renderStatus
            );
          });

          return filesChanged;
        });

        return hasChanges ? updatedGroups : prevGroups;
      });
    } else {
      setFileGroups([]);
    }
  }, [files, groupMode, groupFilesByName, mergeGroupResults]);

  // Interval temizleme fonksiyonu
  const clearRenderInterval = useCallback((analysisId: string) => {
    const interval = intervalsRef.current.get(analysisId);
    if (interval) {
      clearInterval(interval);
      intervalsRef.current.delete(analysisId);
      console.log(`🧹 Interval temizlendi: ${analysisId}`);
    }
  }, []);

  // Tüm interval'leri temizle
  const clearAllIntervals = useCallback(() => {
    intervalsRef.current.forEach((interval, analysisId) => {
      clearInterval(interval);
      console.log(`🧹 Interval temizlendi: ${analysisId}`);
    });
    intervalsRef.current.clear();
  }, []);

  const checkRenderStatus = useCallback(
    async (analysisId: string, fileIndex: number) => {
      try {
        const response: RenderStatusResponse = await apiService.getRenderStatus(
          analysisId
        );

        if (response.success) {
          setFiles((prev) => {
            const newFiles = [...prev];
            const file = newFiles[fileIndex];

            if (!file) {
              clearRenderInterval(analysisId);
              return prev;
            }

            if (response.render_status === "completed") {
              clearRenderInterval(analysisId);
              console.log(`✅ Render tamamlandı: ${analysisId}`);

              if (file.result && file.result.analysis) {
                if (response.stl_generated !== undefined) {
                  file.result.analysis.stl_generated = response.stl_generated;
                }

                if (response.stl_path) {
                  file.result.analysis.stl_path = response.stl_path;
                }

                file.result.analysis.render_status = "completed";

                if (response.renders && file.result) {
                  file.result.analysis.enhanced_renders = {};

                  Object.entries(response.renders).forEach(
                    ([viewType, renderData]) => {
                      if (
                        file.result &&
                        file.result.analysis.enhanced_renders
                      ) {
                        file.result.analysis.enhanced_renders[viewType] = {
                          success: true,
                          view_type: viewType,
                          file_path: renderData.file_path,
                          excel_path: renderData.excel_path || undefined,
                          svg_path: undefined,
                        };
                      }
                    }
                  );

                  console.log(
                    `✅ Enhanced renders güncellendi:`,
                    file.result.analysis.enhanced_renders
                  );
                }
              }

              newFiles[fileIndex] = {
                ...file,
                renderStatus: "completed",
                renderCheckInterval: undefined,
              };
            } else if (response.render_status === "failed") {
              clearRenderInterval(analysisId);
              console.log(`❌ Render başarısız: ${analysisId}`);

              if (file.result && file.result.analysis) {
                file.result.analysis.render_status = "failed";
              }

              newFiles[fileIndex] = {
                ...file,
                renderStatus: "failed",
                renderCheckInterval: undefined,
              };
            } else if (response.render_status === "processing") {
              newFiles[fileIndex] = {
                ...file,
                renderStatus: "processing",
              };
            }

            return newFiles;
          });
        }
      } catch (error) {
        console.error("Render status check failed:", error);
      }
    },
    [clearRenderInterval]
  );

  const addFiles = useCallback((newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map((file) => ({
      file,
      status: "pending",
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...uploadedFiles]);
  }, []);

  const removeFile = useCallback(
    (index: number) => {
      setFiles((prev) => {
        const fileToRemove = prev[index];
        if (fileToRemove?.analysisId) {
          clearRenderInterval(fileToRemove.analysisId);
        }
        return prev.filter((_, i) => i !== index);
      });
    },
    [clearRenderInterval]
  );

  // Grup silme fonksiyonu
  const removeGroup = useCallback(
    (groupId: string) => {
      const group = fileGroups.find((g) => g.groupId === groupId);
      if (group) {
        // Grup içindeki tüm dosyaları sil
        group.files.forEach((file) => {
          if (file.analysisId) {
            clearRenderInterval(file.analysisId);
          }
        });

        // Files listesinden grup dosyalarını kaldır
        setFiles((prev) => prev.filter((file) => !group.files.includes(file)));
      }
    },
    [fileGroups, clearRenderInterval]
  );

  const clearFiles = useCallback(() => {
    clearAllIntervals();
    setFiles([]);
    setFileGroups([]);
    setTotalProcessingTime(0);
  }, [clearAllIntervals]);

  const updateFileStatus = useCallback(
    (index: number, updates: Partial<UploadedFile>) => {
      setFiles((prev) =>
        prev.map((file, i) => (i === index ? { ...file, ...updates } : file))
      );
    },
    []
  );

  const startRenderStatusCheck = useCallback(
    (analysisId: string, fileIndex: number) => {
      clearRenderInterval(analysisId);

      console.log(`🎨 Render status kontrolü başlatılıyor: ${analysisId}`);

      const interval = setInterval(() => {
        setFiles((currentFiles) => {
          if (
            !currentFiles[fileIndex] ||
            currentFiles[fileIndex].analysisId !== analysisId
          ) {
            clearRenderInterval(analysisId);
            return currentFiles;
          }
          return currentFiles;
        });

        checkRenderStatus(analysisId, fileIndex);
      }, 3000);

      intervalsRef.current.set(analysisId, interval);

      setFiles((prev) =>
        prev.map((f, i) =>
          i === fileIndex ? { ...f, renderCheckInterval: interval } : f
        )
      );
    },
    [checkRenderStatus, clearRenderInterval]
  );

  const uploadAndAnalyze = useCallback(async () => {
    if (files.length === 0) return;

    const pendingFiles = files
      .map((file, index) => ({ file, index }))
      .filter(({ file }) => file.status === "pending");

    if (pendingFiles.length === 0) {
      console.log("Tüm dosyalar zaten işlenmiş veya işleniyor");
      return;
    }

    setIsUploading(true);
    const startTime = Date.now();

    try {
      for (const { file, index } of pendingFiles) {
        updateFileStatus(index, { status: "uploading", progress: 0 });

        try {
          const uploadResponse: FileUploadResponse =
            await apiService.uploadSingleFile(file.file);

          if (uploadResponse.success && uploadResponse.file_info) {
            const analysisId = uploadResponse.file_info.analysis_id;

            updateFileStatus(index, {
              status: "uploaded",
              progress: 50,
              analysisId: analysisId,
            });

            updateFileStatus(index, { status: "analyzing", progress: 60 });

            const analysisResponse = await apiService.analyzeFile(analysisId);

            if (analysisResponse.success) {
              updateFileStatus(index, {
                status: "completed",
                progress: 100,
                result: analysisResponse,
                renderStatus: analysisResponse.render_status || "none",
              });

              if (analysisResponse.render_status === "processing") {
                startRenderStatusCheck(analysisId, index);
              }
            } else {
              updateFileStatus(index, {
                status: "failed",
                progress: 0,
                error: analysisResponse.message || "Analiz başarısız",
              });
            }
          } else {
            updateFileStatus(index, {
              status: "failed",
              progress: 0,
              error: uploadResponse.message || "Upload başarısız",
            });
          }
        } catch (error) {
          updateFileStatus(index, {
            status: "failed",
            progress: 0,
            error: error instanceof Error ? error.message : "Bilinmeyen hata",
          });
        }
      }

      const endTime = Date.now();
      setTotalProcessingTime((endTime - startTime) / 1000);
    } finally {
      setIsUploading(false);
    }
  }, [files, updateFileStatus, startRenderStatusCheck]);

  const retryFile = useCallback(
    async (index: number) => {
      const file = files[index];
      if (!file || file.status === "uploading" || file.status === "analyzing")
        return;

      if (file.analysisId) {
        clearRenderInterval(file.analysisId);
      }

      updateFileStatus(index, {
        status: "uploading",
        progress: 0,
        error: undefined,
      });

      try {
        const uploadResponse = await apiService.uploadSingleFile(file.file);

        if (uploadResponse.success && uploadResponse.file_info) {
          const analysisId = uploadResponse.file_info.analysis_id;

          updateFileStatus(index, {
            status: "uploaded",
            progress: 50,
            analysisId: analysisId,
          });

          updateFileStatus(index, { status: "analyzing", progress: 60 });

          const analysisResponse = await apiService.analyzeFile(analysisId);

          if (analysisResponse.success) {
            updateFileStatus(index, {
              status: "completed",
              progress: 100,
              result: analysisResponse,
              renderStatus: analysisResponse.render_status || "none",
            });

            if (
              analysisResponse.render_status !== "completed" &&
              analysisResponse.render_status !== "failed"
            ) {
              startRenderStatusCheck(analysisId, index);
            }
          } else {
            updateFileStatus(index, {
              status: "failed",
              progress: 0,
              error: analysisResponse.message || "Analiz başarısız",
            });
          }
        } else {
          updateFileStatus(index, {
            status: "failed",
            progress: 0,
            error: uploadResponse.message || "Upload başarısız",
          });
        }
      } catch (error) {
        updateFileStatus(index, {
          status: "failed",
          progress: 0,
          error: error instanceof Error ? error.message : "Bilinmeyen hata",
        });
      }
    },
    [files, updateFileStatus, clearRenderInterval, startRenderStatusCheck]
  );

  // Grup export fonksiyonu
  const exportGroupToExcel = useCallback(async (group: FileGroup) => {
    if (!group.mergedResult) return;

    try {
      const blob = await apiService.exportAnalysisExcel(
        group.mergedResult.analysis.id
      );

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${group.groupName}_group_analysis.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Group Excel export failed:", error);
    }
  }, []);

  const exportToExcel = useCallback(
    async (analysisId: string, fileName: string) => {
      try {
        const blob = await apiService.exportAnalysisExcel(analysisId);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${fileName}_analysis.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error("Excel export failed:", error);
      }
    },
    []
  );

  const exportMultipleToExcel = useCallback(
    async (analysisIds: string[], customFileName?: string) => {
      try {
        console.log("📊 Çoklu Excel export başlıyor...", {
          analysisCount: analysisIds.length,
          analysisIds: analysisIds,
        });

        const result = await apiService.exportMultipleAnalysesExcel(
          analysisIds
        );

        if (result.success && result.blob) {
          const url = window.URL.createObjectURL(result.blob);
          const a = document.createElement("a");
          a.style.display = "none";
          a.href = url;
          a.download =
            customFileName ||
            result.filename ||
            `coklu_analiz_${analysisIds.length}_dosya.xlsx`;

          document.body.appendChild(a);
          a.click();

          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);

          console.log("✅ Çoklu Excel export başarılı:", {
            filename: a.download,
            blobSize: result.blob.size,
          });

          return { success: true, filename: a.download };
        } else {
          throw new Error(result.message || "Excel export başarısız");
        }
      } catch (error: any) {
        console.error("❌ Çoklu Excel export hatası:", error);
        return { success: false, error: error.message || "Bilinmeyen hata" };
      }
    },
    []
  );

  const exportAllCompletedToExcel = useCallback(async () => {
    if (groupMode) {
      // Grup modunda - grup sonuçlarını export et
      const completedGroups = fileGroups.filter(
        (g) => g.status === "completed" && g.mergedResult
      );
      if (completedGroups.length === 0) {
        return {
          success: false,
          error: "Export edilecek tamamlanmış grup bulunamadı",
        };
      }

      const analysisIds = completedGroups.map(
        (g) => g.mergedResult!.analysis.id
      );
      return await exportMultipleToExcel(
        analysisIds,
        `grup_analizleri_${Date.now()}.xlsx`
      );
    } else {
      // Normal mod - individual dosyaları export et
      const completedFiles = files.filter(
        (f) => f.status === "completed" && f.result?.analysis?.id
      );

      if (completedFiles.length === 0) {
        return { success: false, error: "Export edilecek analiz bulunamadı" };
      }

      const analysisIds = completedFiles.map((f) => f.result!.analysis.id);
      return await exportMultipleToExcel(
        analysisIds,
        `tum_analizler_${Date.now()}.xlsx`
      );
    }
  }, [files, fileGroups, groupMode, exportMultipleToExcel]);

  // Component unmount olduğunda tüm interval'leri temizle
  useEffect(() => {
    return () => {
      clearAllIntervals();
    };
  }, [clearAllIntervals]);

  return {
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
    exportToExcel,
    exportGroupToExcel,
    exportMultipleToExcel,
    exportAllCompletedToExcel,
    getFileType, // ✅ YENİ - Dışarıdan kullanım için export
  };
};
