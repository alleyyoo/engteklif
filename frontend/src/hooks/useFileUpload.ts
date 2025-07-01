import { useEffect, useState, useCallback, useRef } from "react";
import {
  apiService,
  FileUploadResponse,
  AnalysisResult,
  RenderStatusResponse,
  MultipleUploadResponse,
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
  isPartOfMatch?: boolean; // PDF-STEP eşleştirmesinin parçası mı?
  matchPairId?: string; // Hangi eşleştirmeye ait?
}

export interface MatchedPair {
  id: string;
  pdfFile: UploadedFile;
  stepFile: UploadedFile;
  matchScore: number;
  matchQuality: string;
  displayName: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  mergedResult?: AnalysisResult;
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
  totalFiles: number;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [matchedPairs, setMatchedPairs] = useState<MatchedPair[]>([]);
  const [fileGroups, setFileGroups] = useState<FileGroup[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [totalProcessingTime, setTotalProcessingTime] = useState(0);
  const [groupMode, setGroupMode] = useState(true);

  const [renderStatusMap, setRenderStatusMap] = useState<Map<string, string>>(
    new Map()
  );
  const [renderProgressMap, setRenderProgressMap] = useState<
    Map<string, number>
  >(new Map());

  const intervalsRef = useRef<Map<string, NodeJS.Timer>>(new Map());
  const lastCheckTimesRef = useRef<Map<string, number>>(new Map());
  const retryCountsRef = useRef<Map<string, number>>(new Map());

  const getFileType = useCallback((fileName: string): string => {
    const lowerName = fileName.toLowerCase();
    if (lowerName.endsWith(".pdf")) return "pdf";
    if (lowerName.endsWith(".step") || lowerName.endsWith(".stp"))
      return "step";
    if (lowerName.endsWith(".doc") || lowerName.endsWith(".docx")) return "doc";
    return "other";
  }, []);

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
                  pair.stepFile.analysisId === analysisId ||
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
      const stepResult = pair.stepFile.result;

      if (!pdfResult && !stepResult) return undefined;

      // Use the result that has step_analysis, preferring STEP file result
      const primaryResult = stepResult?.analysis?.step_analysis
        ? stepResult
        : pdfResult;
      const secondaryResult =
        primaryResult === stepResult ? pdfResult : stepResult;

      if (!primaryResult) return undefined;

      const mergedResult: AnalysisResult = {
        ...primaryResult,
        analysis: {
          ...primaryResult.analysis,
          // Merge step_analysis (prefer STEP file's analysis)
          step_analysis:
            stepResult?.analysis?.step_analysis ||
            pdfResult?.analysis?.step_analysis ||
            {},
          // Merge material matches (combine both)
          material_matches: [
            ...(pdfResult?.analysis?.material_matches || []),
            ...(stepResult?.analysis?.material_matches || []),
          ].filter((value, index, self) => self.indexOf(value) === index),
          // Use the best material calculations
          all_material_calculations:
            stepResult?.analysis?.all_material_calculations ||
            pdfResult?.analysis?.all_material_calculations ||
            [],
          // Use enhanced renders from STEP file
          enhanced_renders:
            stepResult?.analysis?.enhanced_renders ||
            pdfResult?.analysis?.enhanced_renders ||
            {},
          // Merge metadata
          original_filename: pair.displayName,
          matched_step_file: pair.stepFile.file.name,
          match_score: pair.matchScore,
          match_quality: pair.matchQuality,
          analysis_strategy: "pdf_with_matched_step",
          // Preserve other important fields
          render_status:
            stepResult?.analysis?.render_status ||
            pdfResult?.analysis?.render_status ||
            "none",
          stl_generated:
            stepResult?.analysis?.stl_generated ||
            pdfResult?.analysis?.stl_generated ||
            false,
          stl_path:
            stepResult?.analysis?.stl_path || pdfResult?.analysis?.stl_path,
        },
        processing_time: Math.max(
          primaryResult.processing_time || 0,
          secondaryResult?.processing_time || 0
        ),
        analysis_details: {
          ...primaryResult.analysis_details,
          matched_pair: true,
          pdf_file: pair.pdfFile.file.name,
          step_file: pair.stepFile.file.name,
          match_score: pair.matchScore,
          match_quality: pair.matchQuality,
        },
      };

      return mergedResult;
    },
    []
  );

  const calculatePairStatus = useCallback(
    (pair: MatchedPair): MatchedPair["status"] => {
      const statuses = [pair.pdfFile.status, pair.stepFile.status];

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
    const stepProgress = pair.stepFile.progress;
    return Math.round((pdfProgress + stepProgress) / 2);
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
        const stepFile = files.find(
          (f) =>
            f.matchPairId === pair.id && getFileType(f.file.name) === "step"
        );

        if (pdfFile) updatedPair.pdfFile = pdfFile;
        if (stepFile) updatedPair.stepFile = stepFile;

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

  const addFiles = useCallback((newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map((file) => ({
      file,
      status: "pending",
      progress: 0,
      renderStatus: "none",
      lastRenderCheck: 0,
      renderRetryCount: 0,
      isPartOfMatch: false,
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
        if (pair.stepFile.analysisId)
          clearRenderInterval(pair.stepFile.analysisId);

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

      // Process PDF-STEP matches
      uploadResponse.matching_results?.pdf_step_matches?.forEach((match) => {
        const pdfFile = pendingFiles.find(
          (f) => f.file.name === match.pdf_file
        );
        const stepFile = pendingFiles.find(
          (f) => f.file.name === match.step_file
        );

        if (pdfFile && stepFile) {
          const pairId = `pair_${Date.now()}_${Math.random()
            .toString(36)
            .substr(2, 9)}`;

          // Mark files as part of match
          pdfFile.isPartOfMatch = true;
          pdfFile.matchPairId = pairId;
          stepFile.isPartOfMatch = true;
          stepFile.matchPairId = pairId;

          const matchedPair: MatchedPair = {
            id: pairId,
            pdfFile,
            stepFile,
            matchScore: match.match_score,
            matchQuality: match.match_quality,
            displayName: pdfFile.file.name.replace(/\.[^/.]+$/, ""),
            status: "pending",
            progress: 0,
          };

          newMatchedPairs.push(matchedPair);
        }
      });

      return newMatchedPairs;
    },
    []
  );

  // Upload and analyze with multiple endpoint
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

      const uploadResponse: MultipleUploadResponse =
        await apiService.uploadMultipleFiles(filesToUpload);

      if (uploadResponse.success && uploadResponse.analyses) {
        console.log(
          "✅ Multiple upload başarılı:",
          uploadResponse.upload_summary
        );

        // Process matched pairs BEFORE updating file statuses
        const matchedFileNames = new Set<string>();
        const newMatchedPairs: MatchedPair[] = [];

        // Process PDF-STEP matches
        uploadResponse.matching_results?.pdf_step_matches?.forEach((match) => {
          const pdfFileIndex = pendingFiles.findIndex(
            (f) => f.file.name === match.pdf_file
          );
          const stepFileIndex = pendingFiles.findIndex(
            (f) => f.file.name === match.step_file
          );

          if (pdfFileIndex !== -1 && stepFileIndex !== -1) {
            const pairId = `pair_${Date.now()}_${Math.random()
              .toString(36)
              .substr(2, 9)}`;

            // Track matched file names
            matchedFileNames.add(match.pdf_file);
            matchedFileNames.add(match.step_file);

            // Update the pending files with match info
            pendingFiles[pdfFileIndex].isPartOfMatch = true;
            pendingFiles[pdfFileIndex].matchPairId = pairId;
            pendingFiles[stepFileIndex].isPartOfMatch = true;
            pendingFiles[stepFileIndex].matchPairId = pairId;

            const matchedPair: MatchedPair = {
              id: pairId,
              pdfFile: { ...pendingFiles[pdfFileIndex] },
              stepFile: { ...pendingFiles[stepFileIndex] },
              matchScore: match.match_score,
              matchQuality: match.match_quality,
              displayName: pendingFiles[pdfFileIndex].file.name.replace(
                /\.[^/.]+$/,
                ""
              ),
              status: "pending",
              progress: 0,
            };

            newMatchedPairs.push(matchedPair);
          }
        });

        if (newMatchedPairs.length > 0) {
          setMatchedPairs((prev) => [...prev, ...newMatchedPairs]);
          console.log(
            `🔗 ${newMatchedPairs.length} PDF-STEP eşleştirmesi oluşturuldu`
          );
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
                pair.stepFile.file.name === file.file.name
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
                        pair.stepFile.file.name === file.file.name
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
  }, [files, updateFileStatus, startRenderStatusMonitoring]);

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

    getFileType,
  };
};
