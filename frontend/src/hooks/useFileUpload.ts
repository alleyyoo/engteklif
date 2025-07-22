import { useEffect, useState, useCallback, useRef } from "react";
import {
  apiService,
  FileUploadResponse,
  AnalysisResult,
  RenderStatusResponse,
  MultipleUploadResponse,
  getFileTypeFromName,  // ✅ ENHANCED
  isCADFile,            // ✅ NEW
  needsConversion,      // ✅ NEW
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
  lastRenderCheck?: number;
  renderRetryCount?: number;
  isPartOfMatch?: boolean; // PDF-CAD eşleştirmesinin parçası mı?
  matchPairId?: string; // Hangi eşleştirmeye ait?
  
  // ✅ NEW - CAD conversion information
  conversionInfo?: {
    needsConversion: boolean;
    originalFormat?: string;
    converted?: boolean;
    conversionTime?: number;
    conversionError?: string;
  };
}

export interface MatchedPair {
  id: string;
  pdfFile: UploadedFile;
  cadFile: UploadedFile;  // ✅ ENHANCED - CAD instead of STEP (backward compatible with stepFile)
  stepFile?: UploadedFile; // ✅ BACKWARD COMPATIBILITY - deprecated, use cadFile
  matchScore: number;
  matchQuality: string;
  displayName: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  mergedResult?: AnalysisResult;
  
  // ✅ NEW - CAD format information
  cadFormat?: string;  // PRT, CATPART, STEP
  cadConverted?: boolean;
  cadConversionTime?: number;
}

export interface FileGroup {
  groupId: string;
  groupName: string;
  groupType: string;
  files: UploadedFile[];
  mergedResult?: AnalysisResult;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  primaryFile?: UploadedFile;
  hasStep: boolean;
  hasPdf: boolean;
  hasDoc: boolean;
  hasCad?: boolean; // ✅ NEW
  totalFiles: number;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [matchedPairs, setMatchedPairs] = useState<MatchedPair[]>([]);
  const [fileGroups, setFileGroups] = useState<FileGroup[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [totalProcessingTime, setTotalProcessingTime] = useState(0);
  const [groupMode, setGroupMode] = useState(true);

  // ✅ NEW - CAD conversion statistics
  const [conversionStats, setConversionStats] = useState({
    totalAttempted: 0,
    successful: 0,
    failed: 0,
    averageTime: 0,
  });

  const [renderStatusMap, setRenderStatusMap] = useState<Map<string, string>>(
    new Map()
  );
  const [renderProgressMap, setRenderProgressMap] = useState<
    Map<string, number>
  >(new Map());

  const intervalsRef = useRef<Map<string, NodeJS.Timer>>(new Map());
  const lastCheckTimesRef = useRef<Map<string, number>>(new Map());
  const retryCountsRef = useRef<Map<string, number>>(new Map());

  // ✅ ENHANCED - getFileType with CAD support
  const getFileType = useCallback((fileName: string): string => {
    return getFileTypeFromName(fileName);
  }, []);

  // ✅ NEW - CAD file detection methods
  const isCADFileType = useCallback((fileName: string): boolean => {
    return isCADFile(fileName);
  }, []);

  const needsCADConversion = useCallback((fileName: string): boolean => {
    return needsConversion(fileName);
  }, []);

  // ✅ ENHANCED - Enhanced file type icon
  const getFileTypeIcon = useCallback((fileName: string) => {
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
  }, [getFileType]);

  const checkRenderStatus = useCallback(
    async (analysisId: string, fileIndex?: number) => {
      const now = Date.now();
      const lastCheck = lastCheckTimesRef.current.get(analysisId) || 0;
      const minInterval = 2000;

      if (now - lastCheck < minInterval) {
        console.log(`⏭️ Render check skipped (too soon): ${analysisId}`);
        return;
      }

      lastCheckTimesRef.current.set(analysisId, now);

      try {
        console.log(`🎨 Render status kontrol ediliyor: ${analysisId}`);

        const response: RenderStatusResponse = await apiService.getRenderStatus(
          analysisId
        );

        if (response.success) {
          const currentStatus = renderStatusMap.get(analysisId);
          const newStatus = response.render_status;
          const renderProgress = response.progress || 0;

          setRenderProgressMap(
            (prev) => new Map(prev.set(analysisId, renderProgress))
          );

          if (currentStatus !== newStatus) {
            console.log(
              `🔄 Render status güncellemesi: ${analysisId} -> ${newStatus} (${renderProgress}%)`
            );

            setRenderStatusMap(
              (prev) => new Map(prev.set(analysisId, newStatus))
            );

            // Update files
            setFiles((prevFiles) =>
              prevFiles.map((file) => {
                if (
                  file.analysisId === analysisId ||
                  file.result?.analysis?.id === analysisId
                ) {
                  const updatedFile = {
                    ...file,
                    renderStatus: newStatus as any,
                    lastRenderCheck: now,
                  };

                  if (
                    newStatus === "completed" &&
                    response.renders &&
                    file.result?.analysis
                  ) {
                    const enhancedRenders: any = {};

                    Object.entries(response.renders).forEach(
                      ([viewType, renderData]: [string, any]) => {
                        enhancedRenders[viewType] = {
                          success: true,
                          view_type: viewType,
                          file_path: renderData.file_path,
                          excel_path: renderData.excel_path || undefined,
                        };
                      }
                    );

                    file.result.analysis.enhanced_renders = enhancedRenders;
                    file.result.analysis.render_status = "completed";

                    if (response.stl_generated !== undefined) {
                      file.result.analysis.stl_generated =
                        response.stl_generated;
                    }
                    if (response.stl_path) {
                      file.result.analysis.stl_path = response.stl_path;
                    }
                  }

                  return updatedFile;
                }
                return file;
              })
            );

            // Update matched pairs
            setMatchedPairs((prevPairs) =>
              prevPairs.map((pair) => {
                if (
                  pair.pdfFile.analysisId === analysisId ||
                  pair.cadFile?.analysisId === analysisId ||
                  pair.stepFile?.analysisId === analysisId || // ✅ BACKWARD COMPATIBILITY
                  pair.mergedResult?.analysis?.id === analysisId
                ) {
                  return {
                    ...pair,
                    mergedResult: pair.mergedResult
                      ? {
                          ...pair.mergedResult,
                          analysis: {
                            ...pair.mergedResult.analysis,
                            render_status: newStatus as any,
                            enhanced_renders:
                              response.renders && newStatus === "completed"
                                ? Object.entries(response.renders).reduce(
                                    (
                                      acc,
                                      [viewType, renderData]: [string, any]
                                    ) => {
                                      acc[viewType] = {
                                        success: true,
                                        view_type: viewType,
                                        file_path: renderData.file_path,
                                        excel_path:
                                          renderData.excel_path || undefined,
                                      };
                                      return acc;
                                    },
                                    {} as any
                                  )
                                : pair.mergedResult.analysis.enhanced_renders,
                          },
                        }
                      : undefined,
                  };
                }
                return pair;
              })
            );
          }

          if (newStatus === "completed" || newStatus === "failed") {
            clearRenderInterval(analysisId);
            retryCountsRef.current.delete(analysisId);

            if (newStatus === "completed" && response.renders) {
              console.log(`🎉 3D Model başarıyla oluşturuldu: ${analysisId}`, {
                renderCount: Object.keys(response.renders).length,
                views: Object.keys(response.renders),
                stlGenerated: response.stl_generated,
              });
            }
          }
        } else {
          console.warn(
            `⚠️ Render status kontrolü başarısız: ${analysisId}`,
            response
          );

          const retryCount = retryCountsRef.current.get(analysisId) || 0;
          if (retryCount < 3) {
            retryCountsRef.current.set(analysisId, retryCount + 1);
            console.log(
              `🔄 Render status retry: ${analysisId} (${retryCount + 1}/3)`
            );

            setTimeout(
              () => checkRenderStatus(analysisId, fileIndex),
              Math.pow(2, retryCount) * 1000
            );
          } else {
            console.error(
              `❌ Render status retry limit exceeded: ${analysisId}`
            );
            clearRenderInterval(analysisId);
          }
        }
      } catch (error: any) {
        console.error(`❌ Render status kontrol hatası: ${analysisId}`, error);

        const retryCount = retryCountsRef.current.get(analysisId) || 0;
        if (
          retryCount < 3 &&
          (error.name === "NetworkError" || error.code === "NETWORK_ERROR")
        ) {
          retryCountsRef.current.set(analysisId, retryCount + 1);
          console.log(
            `🔄 Network error retry: ${analysisId} (${retryCount + 1}/3)`
          );

          setTimeout(() => checkRenderStatus(analysisId, fileIndex), 5000);
        } else {
          clearRenderInterval(analysisId);
          setRenderStatusMap((prev) => new Map(prev.set(analysisId, "failed")));
        }
      }
    },
    [renderStatusMap]
  );

  const clearRenderInterval = useCallback((analysisId: string) => {
    const interval = intervalsRef.current.get(analysisId);
    if (interval) {
      clearInterval(interval);
      intervalsRef.current.delete(analysisId);
      lastCheckTimesRef.current.delete(analysisId);
      console.log(`🧹 Render interval temizlendi: ${analysisId}`);
    }
  }, []);

  const clearAllIntervals = useCallback(() => {
    console.log(
      `🧹 Tüm render interval'ları temizleniyor (${intervalsRef.current.size} adet)`
    );

    intervalsRef.current.forEach((interval, analysisId) => {
      clearInterval(interval);
      console.log(`🧹 Temizlendi: ${analysisId}`);
    });

    intervalsRef.current.clear();
    lastCheckTimesRef.current.clear();
    retryCountsRef.current.clear();

    setRenderStatusMap(new Map());
    setRenderProgressMap(new Map());
  }, []);

  const startRenderStatusMonitoring = useCallback(
    (analysisId: string, fileIndex?: number) => {
      clearRenderInterval(analysisId);

      console.log(`🎨 Render monitoring başlatılıyor: ${analysisId}`);

      checkRenderStatus(analysisId, fileIndex);

      let checkCount = 0;
      const maxChecks = 100;

      const adaptiveCheck = () => {
        checkCount++;

        const baseInterval = 3000;
        const intervalMultiplier = Math.min(Math.floor(checkCount / 10) + 1, 4);
        const currentInterval = baseInterval * intervalMultiplier;

        console.log(
          `🎨 Adaptive render check #${checkCount}: ${analysisId} (interval: ${currentInterval}ms)`
        );

        checkRenderStatus(analysisId, fileIndex);

        const currentStatus = renderStatusMap.get(analysisId);
        if (
          currentStatus === "completed" ||
          currentStatus === "failed" ||
          checkCount >= maxChecks
        ) {
          console.log(
            `🛑 Render monitoring durduruluyor: ${analysisId} (${
              currentStatus || "timeout"
            })`
          );
          clearRenderInterval(analysisId);
          return;
        }

        const nextInterval = setTimeout(adaptiveCheck, currentInterval);
        intervalsRef.current.set(analysisId, nextInterval as any);
      };

      const initialInterval = setTimeout(adaptiveCheck, 3000);
      intervalsRef.current.set(analysisId, initialInterval as any);

      setTimeout(() => {
        const currentInterval = intervalsRef.current.get(analysisId);
        if (
          currentInterval === initialInterval ||
          intervalsRef.current.has(analysisId)
        ) {
          console.log(`⏰ Render monitoring max timeout: ${analysisId}`);
          clearRenderInterval(analysisId);
          setRenderStatusMap((prev) => new Map(prev.set(analysisId, "failed")));
        }
      }, 15 * 60 * 1000);
    },
    [checkRenderStatus, renderStatusMap, clearRenderInterval]
  );

  const mergeMatchedPairResults = useCallback(
    (pair: MatchedPair): AnalysisResult | undefined => {
      const pdfResult = pair.pdfFile.result;
      const cadResult = pair.cadFile?.result || pair.stepFile?.result; // ✅ BACKWARD COMPATIBILITY

      if (!pdfResult && !cadResult) return undefined;

      // Use the result that has step_analysis, preferring CAD file result
      const primaryResult = cadResult?.analysis?.step_analysis
        ? cadResult
        : pdfResult;
      const secondaryResult =
        primaryResult === cadResult ? pdfResult : cadResult;

      if (!primaryResult) return undefined;

      const mergedResult: AnalysisResult = {
        ...primaryResult,
        analysis: {
          ...primaryResult.analysis,
          // Merge step_analysis (prefer CAD file's analysis)
          step_analysis:
            cadResult?.analysis?.step_analysis ||
            pdfResult?.analysis?.step_analysis ||
            {},
          // Merge material matches (combine both)
          material_matches: [
            ...(pdfResult?.analysis?.material_matches || []),
            ...(cadResult?.analysis?.material_matches || []),
          ].filter((value, index, self) => self.indexOf(value) === index),
          // Use the best material calculations
          all_material_calculations:
            cadResult?.analysis?.all_material_calculations ||
            pdfResult?.analysis?.all_material_calculations ||
            [],
          // Use enhanced renders from CAD file
          enhanced_renders:
            cadResult?.analysis?.enhanced_renders ||
            pdfResult?.analysis?.enhanced_renders ||
            {},
          // Merge metadata
          original_filename: pair.displayName,
          matched_cad_file: pair.cadFile?.file.name || pair.stepFile?.file.name, // ✅ ENHANCED
          matched_step_file: pair.stepFile?.file.name, // ✅ BACKWARD COMPATIBILITY
          match_score: pair.matchScore,
          match_quality: pair.matchQuality,
          analysis_strategy: "pdf_with_matched_cad", // ✅ ENHANCED
          cad_format: pair.cadFormat, // ✅ NEW
          cad_converted: pair.cadConverted, // ✅ NEW
          // Preserve other important fields
          render_status:
            cadResult?.analysis?.render_status ||
            pdfResult?.analysis?.render_status ||
            "none",
          stl_generated:
            cadResult?.analysis?.stl_generated ||
            pdfResult?.analysis?.stl_generated ||
            false,
          stl_path:
            cadResult?.analysis?.stl_path || pdfResult?.analysis?.stl_path,
        },
        processing_time: Math.max(
          primaryResult.processing_time || 0,
          secondaryResult?.processing_time || 0
        ),
        analysis_details: {
          ...primaryResult.analysis_details,
          matched_pair: true,
          pdf_file: pair.pdfFile.file.name,
          cad_file: pair.cadFile?.file.name || pair.stepFile?.file.name, // ✅ ENHANCED
          step_file: pair.stepFile?.file.name, // ✅ BACKWARD COMPATIBILITY
          match_score: pair.matchScore,
          match_quality: pair.matchQuality,
          cad_format: pair.cadFormat, // ✅ NEW
          cad_converted: pair.cadConverted, // ✅ NEW
        },
      };

      return mergedResult;
    },
    []
  );

  const calculatePairStatus = useCallback(
    (pair: MatchedPair): MatchedPair["status"] => {
      const cadFile = pair.cadFile || pair.stepFile; // ✅ BACKWARD COMPATIBILITY
      const statuses = [pair.pdfFile.status, cadFile?.status].filter(Boolean);

      if (statuses.every((s) => s === "completed")) return "completed";
      if (statuses.some((s) => s === "failed")) return "failed";
      if (statuses.some((s) => s === "analyzing" || s === "uploading"))
        return "processing";
      return "pending";
    },
    []
  );

  const calculatePairProgress = useCallback((pair: MatchedPair): number => {
    const pdfProgress = pair.pdfFile.progress;
    const cadFile = pair.cadFile || pair.stepFile; // ✅ BACKWARD COMPATIBILITY
    const cadProgress = cadFile?.progress || 0;
    return Math.round((pdfProgress + cadProgress) / 2);
  }, []);

  // Update matched pairs when files change
  useEffect(() => {
    setMatchedPairs((prevPairs) =>
      prevPairs.map((pair) => {
        const updatedPair = { ...pair };

        // Update file references - use matchPairId to find correct files
        const pdfFile = files.find(
          (f) => f.matchPairId === pair.id && getFileType(f.file.name) === "pdf"
        );
        const cadFile = files.find(
          (f) =>
            f.matchPairId === pair.id && 
            (getFileType(f.file.name) === "step" || getFileType(f.file.name) === "cad_part")
        );

        if (pdfFile) updatedPair.pdfFile = pdfFile;
        if (cadFile) {
          updatedPair.cadFile = cadFile;
          // ✅ BACKWARD COMPATIBILITY
          if (getFileType(cadFile.file.name) === "step") {
            updatedPair.stepFile = cadFile;
          }
        }

        // Update status and progress
        updatedPair.status = calculatePairStatus(updatedPair);
        updatedPair.progress = calculatePairProgress(updatedPair);

        // Merge results if both completed
        if (updatedPair.status === "completed") {
          updatedPair.mergedResult = mergeMatchedPairResults(updatedPair);
        }

        return updatedPair;
      })
    );
  }, [
    files,
    calculatePairStatus,
    calculatePairProgress,
    mergeMatchedPairResults,
    getFileType,
  ]);

  // ✅ ENHANCED - Add files with CAD conversion info
  const addFiles = useCallback((newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map((file) => {
      const fileType = getFileType(file.name);
      const needsConv = needsCADConversion(file.name);
      
      return {
        file,
        status: "pending",
        progress: 0,
        renderStatus: "none",
        lastRenderCheck: 0,
        renderRetryCount: 0,
        isPartOfMatch: false,
        // ✅ NEW - CAD conversion info
        conversionInfo: {
          needsConversion: needsConv,
          originalFormat: needsConv ? 
            (file.name.toLowerCase().endsWith('.prt') ? 'PRT' : 
             file.name.toLowerCase().endsWith('.catpart') ? 'CATPART' : 'UNKNOWN') 
            : undefined,
          converted: false,
        }
      };
    });
    
    setFiles((prev) => [...prev, ...uploadedFiles]);
    
    // ✅ NEW - Update conversion stats
    const conversionCount = uploadedFiles.filter(f => f.conversionInfo?.needsConversion).length;
    if (conversionCount > 0) {
      setConversionStats(prev => ({
        ...prev,
        totalAttempted: prev.totalAttempted + conversionCount
      }));
    }
  }, [getFileType, needsCADConversion]);

  const removeFile = useCallback(
    (index: number) => {
      setFiles((prev) => {
        const fileToRemove = prev[index];
        if (fileToRemove?.analysisId) {
          clearRenderInterval(fileToRemove.analysisId);
        }

        // Remove from matched pairs if part of match
        if (fileToRemove?.isPartOfMatch && fileToRemove.matchPairId) {
          setMatchedPairs((prevPairs) =>
            prevPairs.filter((pair) => pair.id !== fileToRemove.matchPairId)
          );
        }

        return prev.filter((_, i) => i !== index);
      });
    },
    [clearRenderInterval]
  );

  const removeGroup = useCallback(
    (groupId: string) => {
      const pair = matchedPairs.find((p) => p.id === groupId);
      if (pair) {
        // Clear render intervals
        if (pair.pdfFile.analysisId)
          clearRenderInterval(pair.pdfFile.analysisId);
        const cadFile = pair.cadFile || pair.stepFile; // ✅ BACKWARD COMPATIBILITY
        if (cadFile?.analysisId)
          clearRenderInterval(cadFile.analysisId);

        // Remove files
        setFiles((prev) =>
          prev.filter(
            (file) => !(file.isPartOfMatch && file.matchPairId === groupId)
          )
        );

        // Remove pair
        setMatchedPairs((prev) => prev.filter((p) => p.id !== groupId));
      }
    },
    [matchedPairs, clearRenderInterval]
  );

  const clearFiles = useCallback(() => {
    clearAllIntervals();
    setFiles([]);
    setMatchedPairs([]);
    setFileGroups([]);
    setTotalProcessingTime(0);
    // ✅ NEW - Reset conversion stats
    setConversionStats({
      totalAttempted: 0,
      successful: 0,
      failed: 0,
      averageTime: 0,
    });
  }, [clearAllIntervals]);

  const updateFileStatus = useCallback(
    (index: number, updates: Partial<UploadedFile>) => {
      setFiles((prev) =>
        prev.map((file, i) => (i === index ? { ...file, ...updates } : file))
      );
    },
    []
  );

  // Process upload response and create matched pairs
  const processUploadResponse = useCallback(
    (uploadResponse: MultipleUploadResponse, pendingFiles: UploadedFile[]) => {
      const newMatchedPairs: MatchedPair[] = [];

      // ✅ ENHANCED - Process PDF-CAD matches (supports both old and new formats)
      const cadMatches = uploadResponse.matching_results?.pdf_cad_matches || 
                        uploadResponse.matching_results?.pdf_step_matches || [];

      cadMatches.forEach((match: any) => {
        const pdfFile = pendingFiles.find(
          (f) => f.file.name === match.pdf_file
        );
        const cadFile = pendingFiles.find(
          (f) => f.file.name === (match.cad_file || match.step_file)
        );

        if (pdfFile && cadFile) {
          const pairId = `pair_${Date.now()}_${Math.random()
            .toString(36)
            .substr(2, 9)}`;

          // Mark files as part of match
          pdfFile.isPartOfMatch = true;
          pdfFile.matchPairId = pairId;
          cadFile.isPartOfMatch = true;
          cadFile.matchPairId = pairId;

          const matchedPair: MatchedPair = {
            id: pairId,
            pdfFile,
            cadFile,
            matchScore: match.match_score,
            matchQuality: match.match_quality,
            displayName: pdfFile.file.name.replace(/\.[^/.]+$/, ""),
            status: "pending",
            progress: 0,
            // ✅ NEW - CAD format information
            cadFormat: match.cad_format || (match.step_file ? 'STEP' : 'UNKNOWN'),
            cadConverted: match.cad_format !== 'STEP',
          };

          // ✅ BACKWARD COMPATIBILITY
          if (getFileType(cadFile.file.name) === "step") {
            matchedPair.stepFile = cadFile;
          }

          newMatchedPairs.push(matchedPair);
        }
      });

      // ✅ NEW - Update conversion statistics from response
      if (uploadResponse.upload_summary?.cad_conversions) {
        const cadConversions = uploadResponse.upload_summary.cad_conversions;
        setConversionStats(prev => ({
          totalAttempted: prev.totalAttempted + cadConversions.total_attempted,
          successful: prev.successful + cadConversions.successful,
          failed: prev.failed + cadConversions.failed,
          averageTime: prev.averageTime, // Will be updated when individual results come
        }));
      }

      return newMatchedPairs;
    },
    [getFileType]
  );

  // ✅ ENHANCED - Upload and analyze with CAD conversion support
  const uploadAndAnalyze = useCallback(async () => {
    if (files.length === 0) return;

    const pendingFiles = files.filter((file) => file.status === "pending");

    if (pendingFiles.length === 0) {
      console.log("Tüm dosyalar zaten işlenmiş veya işleniyor");
      return;
    }

    setIsUploading(true);
    const startTime = Date.now();

    try {
      // Mark all pending files as uploading
      pendingFiles.forEach((file) => {
        const index = files.indexOf(file);
        updateFileStatus(index, {
          status: "uploading",
          progress: 20,
        });
      });

      // Upload multiple files
      const filesToUpload = pendingFiles.map((f) => f.file);
      console.log(`📤 Multiple upload başlıyor: ${filesToUpload.length} dosya`);
      
      // ✅ NEW - Log CAD files being uploaded
      const cadFiles = filesToUpload.filter(f => isCADFileType(f.name));
      const conversionFiles = filesToUpload.filter(f => needsCADConversion(f.name));
      
      if (cadFiles.length > 0) {
        console.log(`🔧 CAD dosyaları: ${cadFiles.length} adet`);
      }
      if (conversionFiles.length > 0) {
        console.log(`🔄 Conversion gerekli: ${conversionFiles.length} adet (${conversionFiles.map(f => f.name).join(', ')})`);
      }

      const uploadResponse: MultipleUploadResponse =
        await apiService.uploadMultipleFiles(filesToUpload);

      if (uploadResponse.success && uploadResponse.analyses) {
        console.log(
          "✅ Multiple upload başarılı:",
          uploadResponse.upload_summary
        );

        // ✅ NEW - Log conversion results
        if (uploadResponse.conversion_results && uploadResponse.conversion_results.length > 0) {
          console.log("🔄 CAD Conversion sonuçları:");
          uploadResponse.conversion_results.forEach((result: any) => {
            const status = result.conversion_successful ? "✅" : "❌";
            console.log(`  ${status} ${result.original_file}: ${result.message} (${result.processing_time}s)`);
          });
        }

        // Process matched pairs BEFORE updating file statuses
        const matchedFileNames = new Set<string>();
        const newMatchedPairs: MatchedPair[] = [];

        // ✅ ENHANCED - Process PDF-CAD matches (supports both formats)
        const cadMatches = uploadResponse.matching_results?.pdf_cad_matches || 
                          uploadResponse.matching_results?.pdf_step_matches || [];

        cadMatches.forEach((match: any) => {
          const pdfFileIndex = pendingFiles.findIndex(
            (f) => f.file.name === match.pdf_file
          );
          const cadFileIndex = pendingFiles.findIndex(
            (f) => f.file.name === (match.cad_file || match.step_file)
          );

          if (pdfFileIndex !== -1 && cadFileIndex !== -1) {
            const pairId = `pair_${Date.now()}_${Math.random()
              .toString(36)
              .substr(2, 9)}`;

            // Track matched file names
            matchedFileNames.add(match.pdf_file);
            matchedFileNames.add(match.cad_file || match.step_file);

            // Update the pending files with match info
            pendingFiles[pdfFileIndex].isPartOfMatch = true;
            pendingFiles[pdfFileIndex].matchPairId = pairId;
            pendingFiles[cadFileIndex].isPartOfMatch = true;
            pendingFiles[cadFileIndex].matchPairId = pairId;

            const matchedPair: MatchedPair = {
              id: pairId,
              pdfFile: { ...pendingFiles[pdfFileIndex] },
              cadFile: { ...pendingFiles[cadFileIndex] },
              matchScore: match.match_score,
              matchQuality: match.match_quality,
              displayName: pendingFiles[pdfFileIndex].file.name.replace(
                /\.[^/.]+$/,
                ""
              ),
              status: "pending",
              progress: 0,
              // ✅ NEW - CAD format information
              cadFormat: match.cad_format || (match.step_file ? 'STEP' : 'UNKNOWN'),
              cadConverted: (match.cad_format || 'STEP') !== 'STEP',
            };

            // ✅ BACKWARD COMPATIBILITY
            if (getFileType(pendingFiles[cadFileIndex].file.name) === "step") {
              matchedPair.stepFile = { ...pendingFiles[cadFileIndex] };
            }

            newMatchedPairs.push(matchedPair);
          }
        });

        if (newMatchedPairs.length > 0) {
          setMatchedPairs((prev) => [...prev, ...newMatchedPairs]);
          console.log(
            `🔗 ${newMatchedPairs.length} PDF-CAD eşleştirmesi oluşturuldu`
          );
          
          // ✅ NEW - Log CAD format distribution
          const formatCounts = newMatchedPairs.reduce((acc, pair) => {
            const format = pair.cadFormat || 'UNKNOWN';
            acc[format] = (acc[format] || 0) + 1;
            return acc;
          }, {} as Record<string, number>);
          
          console.log(`📊 CAD format dağılımı:`, formatCounts);
        }

        // Create analysis map
        const analysisMap = new Map<string, any>();
        uploadResponse.analyses.forEach((analysis: any) => {
          analysisMap.set(analysis.primary_file, analysis);
          if (analysis.secondary_file) {
            analysisMap.set(analysis.secondary_file, analysis);
          }
        });

        // Update file statuses with match information
        setFiles((prevFiles) => {
          return prevFiles.map((file) => {
            const pendingFile = pendingFiles.find(
              (pf) => pf.file.name === file.file.name
            );
            if (!pendingFile) return file;

            const analysis = analysisMap.get(file.file.name);
            const isMatched = matchedFileNames.has(file.file.name);
            const matchedPair = newMatchedPairs.find(
              (pair) =>
                pair.pdfFile.file.name === file.file.name ||
                pair.cadFile?.file.name === file.file.name ||
                pair.stepFile?.file.name === file.file.name // ✅ BACKWARD COMPATIBILITY
            );

            if (analysis) {
              return {
                ...file,
                status: "uploaded",
                progress: 50,
                analysisId: analysis.analysis_id,
                isPartOfMatch: isMatched,
                matchPairId: matchedPair?.id,
              };
            } else {
              const failedUpload = uploadResponse.failed_uploads?.find(
                (f) => f.filename === file.file.name
              );

              return {
                ...file,
                status: "failed",
                progress: 0,
                error: failedUpload?.error || "Dosya yüklenemedi",
              };
            }
          });
        });

        // Analyze each file
        for (const analysisData of uploadResponse.analyses) {
          const analysisId = analysisData.analysis_id;

          // Find related files
          const relatedFiles = files.filter(
            (f) =>
              f.file.name === analysisData.primary_file ||
              f.file.name === analysisData.secondary_file
          );

          relatedFiles.forEach((file) => {
            const fileIndex = files.indexOf(file);
            updateFileStatus(fileIndex, {
              status: "analyzing",
              progress: 70,
            });
          });

          try {
            const analysisResponse = await apiService.analyzeFile(analysisId);

            if (analysisResponse.success) {
              const renderStatus =
                analysisResponse.analysis?.render_status || "none";

              // Update all related files - preserve match info
              setFiles((prevFiles) => {
                return prevFiles.map((file) => {
                  if (
                    file.file.name === analysisData.primary_file ||
                    file.file.name === analysisData.secondary_file
                  ) {
                    const matchedPair = newMatchedPairs.find(
                      (pair) =>
                        pair.pdfFile.file.name === file.file.name ||
                        pair.cadFile?.file.name === file.file.name ||
                        pair.stepFile?.file.name === file.file.name // ✅ BACKWARD COMPATIBILITY
                    );

                    return {
                      ...file,
                      status: "completed",
                      progress: 100,
                      result: analysisResponse,
                      renderStatus: renderStatus as any,
                      lastRenderCheck: Date.now(),
                      // Make sure match info is preserved
                      isPartOfMatch:
                        file.isPartOfMatch ||
                        !!matchedPair ||
                        matchedFileNames.has(file.file.name),
                      matchPairId: file.matchPairId || matchedPair?.id,
                    };
                  }
                  return file;
                });
              });

              // Start render monitoring if needed
              if (renderStatus === "processing" || renderStatus === "pending") {
                console.log(`🎨 Render monitoring başlatılıyor: ${analysisId}`);
                setRenderStatusMap(
                  (prev) => new Map(prev.set(analysisId, renderStatus))
                );
                startRenderStatusMonitoring(analysisId);
              }
            } else {
              // Update failed files
              setFiles((prevFiles) => {
                return prevFiles.map((file) => {
                  if (
                    file.file.name === analysisData.primary_file ||
                    file.file.name === analysisData.secondary_file
                  ) {
                    return {
                      ...file,
                      status: "failed",
                      progress: 0,
                      error: analysisResponse.message || "Analiz başarısız",
                    };
                  }
                  return file;
                });
              });
            }
          } catch (error) {
            relatedFiles.forEach((file) => {
              const fileIndex = files.indexOf(file);
              updateFileStatus(fileIndex, {
                status: "failed",
                progress: 0,
                error: error instanceof Error ? error.message : "Analiz hatası",
              });
            });
          }
        }
      } else {
        // Upload failed
        pendingFiles.forEach((file) => {
          const fileIndex = files.indexOf(file);
          updateFileStatus(fileIndex, {
            status: "failed",
            progress: 0,
            error: uploadResponse.message || "Upload başarısız",
          });
        });
      }

      const endTime = Date.now();
      setTotalProcessingTime((endTime - startTime) / 1000);
    } catch (error) {
      console.error("❌ Upload/Analyze hatası:", error);

      pendingFiles.forEach((file) => {
        const fileIndex = files.indexOf(file);
        updateFileStatus(fileIndex, {
          status: "failed",
          progress: 0,
          error: error instanceof Error ? error.message : "Bilinmeyen hata",
        });
      });
    } finally {
      setIsUploading(false);
    }
  }, [files, updateFileStatus, startRenderStatusMonitoring, getFileType, isCADFileType, needsCADConversion]);

  const retryFile = useCallback(
    async (index: number) => {
      const file = files[index];
      if (!file || file.status === "uploading" || file.status === "analyzing")
        return;

      if (file.analysisId) {
        clearRenderInterval(file.analysisId);
      }

      // Reset file status
      updateFileStatus(index, {
        status: "pending",
        progress: 0,
        error: undefined,
        renderStatus: "none",
        renderRetryCount: 0,
        analysisId: undefined,
        result: undefined,
        isPartOfMatch: false,
        matchPairId: undefined,
        // ✅ NEW - Reset conversion info
        conversionInfo: {
          ...file.conversionInfo,
          converted: false,
          conversionTime: undefined,
          conversionError: undefined,
        }
      });

      // Remove from matched pairs if it was part of one
      if (file.isPartOfMatch && file.matchPairId) {
        setMatchedPairs((prev) =>
          prev.filter((pair) => pair.id !== file.matchPairId)
        );
      }

      // Retry upload
      setTimeout(() => {
        uploadAndAnalyze();
      }, 100);
    },
    [files, updateFileStatus, clearRenderInterval, uploadAndAnalyze]
  );

  const refreshRenderStatus = useCallback(
    (analysisId: string, fileIndex?: number) => {
      console.log(`🔄 Manual render status refresh: ${analysisId}`);

      retryCountsRef.current.delete(analysisId);
      lastCheckTimesRef.current.delete(analysisId);
      checkRenderStatus(analysisId, fileIndex);

      if (!intervalsRef.current.has(analysisId)) {
        startRenderStatusMonitoring(analysisId, fileIndex);
      }
    },
    [checkRenderStatus, startRenderStatusMonitoring]
  );

  const exportGroupToExcel = useCallback(
    async (group: MatchedPair | FileGroup) => {
      const result = "mergedResult" in group ? group.mergedResult : undefined;
      if (!result) return;

      try {
        const blob = await apiService.exportAnalysisExcel(result.analysis.id);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${group.displayName || group.groupName}_analysis.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error("Group Excel export failed:", error);
      }
    },
    []
  );

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
    const analysisIds: string[] = [];

    // Add completed matched pairs
    matchedPairs.forEach((pair) => {
      if (pair.status === "completed" && pair.mergedResult?.analysis?.id) {
        analysisIds.push(pair.mergedResult.analysis.id);
      }
    });

    // Add completed individual files
    files.forEach((file) => {
      if (
        file.status === "completed" &&
        file.result?.analysis?.id &&
        !file.isPartOfMatch
      ) {
        analysisIds.push(file.result.analysis.id);
      }
    });

    if (analysisIds.length === 0) {
      return { success: false, error: "Export edilecek analiz bulunamadı" };
    }

    return await exportMultipleToExcel(
      analysisIds,
      `tum_analizler_${Date.now()}.xlsx`
    );
  }, [files, matchedPairs, exportMultipleToExcel]);

  const getRenderStatistics = useCallback(() => {
    const stats = {
      total: renderStatusMap.size,
      processing: Array.from(renderStatusMap.values()).filter(
        (s) => s === "processing"
      ).length,
      completed: Array.from(renderStatusMap.values()).filter(
        (s) => s === "completed"
      ).length,
      failed: Array.from(renderStatusMap.values()).filter((s) => s === "failed")
        .length,
      pending: Array.from(renderStatusMap.values()).filter(
        (s) => s === "pending"
      ).length,
    };

    return stats;
  }, [renderStatusMap]);

  // ✅ NEW - Get CAD conversion statistics
  const getConversionStatistics = useCallback(() => {
    return {
      ...conversionStats,
      successRate: conversionStats.totalAttempted > 0 
        ? (conversionStats.successful / conversionStats.totalAttempted) * 100 
        : 0,
    };
  }, [conversionStats]);

  // ✅ NEW - Get file type statistics
  const getFileTypeStatistics = useCallback(() => {
    const stats = files.reduce((acc, file) => {
      const type = getFileType(file.file.name);
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      ...stats,
      total: files.length,
      cadFiles: (stats.step || 0) + (stats.cad_part || 0),
      needsConversion: files.filter(f => f.conversionInfo?.needsConversion).length,
    };
  }, [files, getFileType]);

  useEffect(() => {
    return () => {
      console.log(
        "🧹 useFileUpload cleanup - tüm render interval'ları temizleniyor"
      );
      clearAllIntervals();
    };
  }, [clearAllIntervals]);

  return {
    files,
    fileGroups,
    matchedPairs,
    groupMode,
    setGroupMode,
    isUploading,
    totalProcessingTime,

    renderStatusMap,
    renderProgressMap,
    getRenderStatistics,

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

    startRenderStatusMonitoring,
    clearRenderInterval,
    refreshRenderStatus,

    exportToExcel,
    exportGroupToExcel,
    exportMultipleToExcel,
    exportAllCompletedToExcel,

    // ✅ ENHANCED - File type detection with CAD support
    getFileType,
    getFileTypeIcon,
    isCADFile: isCADFileType,
    needsConversion: needsCADConversion,
  };
};