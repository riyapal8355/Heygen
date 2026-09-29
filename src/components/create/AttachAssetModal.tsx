"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  X,
  UploadCloud,
  File,
  Image as ImageIcon,
  Film,
  Check,
  Trash2,
  Search,
  FolderPlus,
  Folder,
  ArrowLeft,
  ArrowRight,
  Plus,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface WorkspaceAsset {
  id: string;
  name: string;
  type: "image" | "video" | "doc";
  size: string;
  date: string;
  folder?: string;
  thumbnail?: string;
}


interface AttachAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAttachFile?: (fileName: string) => void;
  onAttachAsset?: (asset: {
    id: string;
    name: string;
    type: "image" | "video" | "audio" | "doc";
    size?: string;
  }) => void;
  initialTab?: "upload" | "assets";
}

export default function AttachAssetModal({
  isOpen,
  onClose,
  onAttachFile,
  onAttachAsset,
  initialTab = "upload",
}: AttachAssetModalProps) {
  const [activeTab, setActiveTab] = useState<"upload" | "assets">(initialTab);
  const [selectedFile, setSelectedFile] = useState<{
    name: string;
    size: string;
    type: string;
  } | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Assets Tab state
  const [searchQuery, setSearchQuery] = useState("");
  const [folders, setFolders] = useState<string[]>([
    "Brand Assets",
    "Product Videos",
    "Presentations",
  ]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [assetsList, setAssetsList] = useState<WorkspaceAsset[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const compactFileInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Backend workspace & MinIO upload state
  const { currentWorkspace } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentWorkspace?.id || !isOpen) return;
    api.assets
      .list(currentWorkspace.id)
      .then((res) => {
        if (res) {
          setAssetsList(
            res.map((a) => ({
              id: a.id,
              name: a.original_filename,
              type:
                a.asset_type === "video"
                  ? "video"
                  : a.asset_type === "image"
                  ? "image"
                  : "doc",
              size: `${(a.size_bytes / (1024 * 1024)).toFixed(1)} MB`,
              date: new Date(a.created_at).toLocaleDateString(),
              folder: "Workspace Assets",
            }))
          );
        }
      })
      .catch(() => {});
  }, [currentWorkspace?.id, isOpen]);

  const uploadFileToMinIO = async (file: File) => {
    const sizeStr = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
    const newFile = {
      name: file.name,
      size: sizeStr,
      type: file.type,
    };
    setSelectedFile(newFile);

    if (currentWorkspace?.id) {
      setIsUploading(true);
      setUploadError(null);
      try {
        let assetType = "doc";
        if (file.type.startsWith("video")) assetType = "video";
        else if (file.type.startsWith("image")) assetType = "image";
        else if (file.type.startsWith("audio")) assetType = "audio";

        const intent = await api.assets.createUploadIntent(currentWorkspace.id, {
          original_filename: file.name,
          mime_type: file.type || "application/octet-stream",
          size_bytes: file.size,
          asset_type: assetType,
        });

        await api.assets.uploadBinaryDirect(
          intent.signed_upload_url,
          file,
          file.type || "application/octet-stream"
        );

        const confirmed = await api.assets.confirmUpload(
          currentWorkspace.id,
          intent.asset_id
        );

        const createdAsset: WorkspaceAsset = {
          id: confirmed.asset_id,
          name: file.name,
          type: assetType as any,
          size: sizeStr,
          date: "Just now",
          folder: selectedFolder || "Workspace Assets",
        };
        setAssetsList((prev) => [createdAsset, ...prev]);
        setSelectedAssetId(createdAsset.id);
        return;
      } catch (err: any) {
        setUploadError(err?.message || "MinIO direct upload failed");
      } finally {
        setIsUploading(false);
      }
    }

    const fallbackAsset: WorkspaceAsset = {
      id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "uploaded_asset",
      name: file.name,
      type: file.type.startsWith("video")
        ? "video"
        : file.type.startsWith("image")
        ? "image"
        : "doc",
      size: sizeStr,
      date: "Just now",
      folder: selectedFolder || undefined,
    };
    setAssetsList((prev) => [fallbackAsset, ...prev]);
    setSelectedAssetId(fallbackAsset.id);
  };

  // Sync tab on open
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFileToMinIO(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFileToMinIO(e.dataTransfer.files[0]);
    }
  };

  const handleCreateFolder = () => {
    if (newFolderName.trim()) {
      const trimmed = newFolderName.trim();
      if (!folders.includes(trimmed)) {
        setFolders((prev) => [...prev, trimmed]);
      }
      setSelectedFolder(trimmed);
      setNewFolderName("");
      setIsCreatingFolder(false);
    }
  };

  const handleContinue = () => {
    const asset = assetsList.find((a) => a.id === selectedAssetId);
    if (asset) {
      if (onAttachAsset) onAttachAsset(asset);
      if (onAttachFile) onAttachFile(asset.name);
    } else if (selectedFile) {
      if (onAttachAsset && selectedAssetId) {
        onAttachAsset({
          id: selectedAssetId,
          name: selectedFile.name,
          type: (selectedFile.type.startsWith("video")
            ? "video"
            : selectedFile.type.startsWith("image")
            ? "image"
            : selectedFile.type.startsWith("audio")
            ? "audio"
            : "doc") as any,
          size: selectedFile.size,
        });
      }
      if (onAttachFile) onAttachFile(selectedFile.name);
    }
    onClose();
  };

  const filteredAssets = assetsList.filter((asset) => {
    const matchesSearch = asset.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesFolder = !selectedFolder || asset.folder === selectedFolder;
    return matchesSearch && matchesFolder;
  });

  return (
    <div
      onClick={(e) => {
        if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
          onClose();
        }
      }}
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200 select-none"
    >
      <div
        ref={modalRef}
        className="w-full max-w-xl md:max-w-2xl bg-[#0A0F1A] rounded-3xl p-6 sm:p-7 shadow-2xl border border-[#1B2940] text-slate-100 max-h-[90vh] flex flex-col animate-in zoom-in-95 duration-150 relative"
      >
        {/* 1. Header: Title & Close Button */}
        <div className="flex items-center justify-between pb-1 flex-shrink-0">
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Attach an Asset
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-[#101827] flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* 2. Segmented Tab Control (Upload | Assets) */}
        <div className="w-full bg-[#0B1220] p-1 rounded-2xl flex items-center gap-1 my-4 flex-shrink-0 border border-[#1B2940]">
          <button
            type="button"
            onClick={() => setActiveTab("upload")}
            className={`flex-1 py-2 text-center text-xs sm:text-sm font-bold rounded-xl transition-all cursor-pointer ${
              activeTab === "upload"
                ? "bg-[#101827] text-white shadow-xs ring-1 ring-cyan-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Upload
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("assets")}
            className={`flex-1 py-2 text-center text-xs sm:text-sm font-bold rounded-xl transition-all cursor-pointer ${
              activeTab === "assets"
                ? "bg-[#101827] text-white shadow-xs ring-1 ring-cyan-500/30"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Assets
          </button>
        </div>

        {/* 3. Main Body Content (Screen A vs Screen B) */}
        <div className="flex-1 overflow-y-auto pr-1 scrollbar-thin">
          {activeTab === "upload" ? (
            /* SCREEN A: Upload Tab */
            <div className="space-y-4">
              {/* Large Dashed Drag & Drop Box */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-12 sm:p-16 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
                  isDragging
                    ? "border-cyan-500 bg-cyan-500/10 scale-[0.99]"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] hover:bg-[#101827]"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,video/*,.pdf,.doc,.docx,.ppt,.pptx,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />

                <div className="w-12 h-12 rounded-full bg-[#101827] border border-[#1B2940] flex items-center justify-center text-cyan-400 mb-3.5 shadow-2xs">
                  <UploadCloud size={26} strokeWidth={2} />
                </div>

                <div className="text-sm sm:text-base font-bold text-white leading-snug">
                  Upload file or drag and drop here
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Supports images, videos, and documents
                </div>
              </div>

              {/* Selected File Badge / Preview */}
              {selectedFile && (
                <div className="flex items-center justify-between p-3 bg-[#0B111E] border border-[#1B2940] rounded-2xl text-xs animate-in fade-in duration-150">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-400 flex items-center justify-center flex-shrink-0">
                      <File size={15} />
                    </div>
                    <div className="min-w-0">
                      <div className="font-bold text-white truncate">
                        {selectedFile.name}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {selectedFile.size} • Ready to attach
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    className="text-slate-400 hover:text-red-400 p-1 rounded-md transition-colors"
                    title="Remove"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* SCREEN B: Assets Tab */
            <div className="space-y-4">
              {/* Assets Search Bar */}
              <div className="relative w-full">
                <Search
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
                />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search"
                  className="w-full bg-[#07090e] border border-[#1B2940] rounded-2xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-white placeholder:text-slate-500 outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 transition-all shadow-2xs"
                />
              </div>

              {/* Compact Drag & Drop Area */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => compactFileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl py-4 px-4 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
                  isDragging
                    ? "border-cyan-500 bg-cyan-500/10"
                    : "border-[#1B2940] hover:border-cyan-500/50 bg-[#0B111E] hover:bg-[#101827]"
                }`}
              >
                <input
                  ref={compactFileInputRef}
                  type="file"
                  accept="image/*,video/*,.pdf,.doc,.docx,.ppt,.pptx,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <UploadCloud size={20} className="text-cyan-400 mb-1" />
                <span className="text-xs font-semibold text-slate-300">
                  or drag and drop here
                </span>
              </div>

              {/* Folders Section */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-bold text-white">
                    Folders
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsCreatingFolder(true)}
                    className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-[#101827] transition-colors cursor-pointer flex items-center gap-1 text-[11px] font-semibold"
                    title="New folder"
                  >
                    <FolderPlus size={14} />
                    <span>New folder</span>
                  </button>
                </div>

                {/* Inline Folder Creation Popover */}
                {isCreatingFolder && (
                  <div className="mb-3 p-3 bg-[#0B111E] border border-[#1B2940] rounded-2xl shadow-sm animate-in fade-in duration-150">
                    <div className="text-[11px] font-bold text-slate-300 mb-1.5">
                      New Folder Name
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={newFolderName}
                        onChange={(e) => setNewFolderName(e.target.value)}
                        placeholder="e.g. Campaign 2026"
                        autoFocus
                        onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                        className="flex-1 bg-[#07090e] border border-[#1B2940] rounded-xl px-2.5 py-1.5 text-xs text-white outline-none focus:border-cyan-500 placeholder:text-slate-600"
                      />
                      <button
                        type="button"
                        onClick={handleCreateFolder}
                        className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold px-3 py-1.5 rounded-xl cursor-pointer transition-colors"
                      >
                        Create
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreatingFolder(false);
                          setNewFolderName("");
                        }}
                        className="text-slate-400 hover:text-white text-xs px-2 py-1.5 cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Folder Pills List */}
                <div className="flex flex-wrap items-center gap-1.5 pb-1">
                  <button
                    type="button"
                    onClick={() => setSelectedFolder(null)}
                    className={`px-3 py-1 rounded-full text-[11px] font-semibold transition-colors cursor-pointer border ${
                      selectedFolder === null
                        ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                        : "bg-[#0B1220] border-[#1B2940] text-slate-400 hover:bg-[#101827] hover:text-white"
                    }`}
                  >
                    All Assets
                  </button>
                  {folders.map((fld) => (
                    <button
                      key={fld}
                      type="button"
                      onClick={() =>
                        setSelectedFolder(selectedFolder === fld ? null : fld)
                      }
                      className={`px-3 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer border ${
                        selectedFolder === fld
                          ? "bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold"
                          : "bg-[#0B1220] border-[#1B2940] text-slate-400 hover:bg-[#101827] hover:text-white"
                      }`}
                    >
                      <Folder size={11} />
                      <span>{fld}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Asset Library Cards */}
              <div className="space-y-2 pt-1">
                {filteredAssets.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-xs">
                    No matching assets found.
                  </div>
                ) : (
                  filteredAssets.map((asset) => {
                    const isSelected = selectedAssetId === asset.id;
                    return (
                      <div
                        key={asset.id}
                        onClick={() =>
                          setSelectedAssetId(isSelected ? null : asset.id)
                        }
                        className={`flex items-center justify-between p-3 rounded-2xl border transition-all duration-200 cursor-pointer ${
                          isSelected
                            ? "bg-cyan-500/15 border-cyan-500 shadow-sm"
                            : "bg-[#0B111E] hover:bg-[#101827] border-[#1B2940]"
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                              isSelected
                                ? "bg-cyan-500 text-slate-950 font-bold"
                                : "bg-[#101827] border border-[#1B2940] text-slate-400"
                            }`}
                          >
                            {asset.type === "video" ? (
                              <Film size={18} />
                            ) : asset.type === "image" ? (
                              <ImageIcon size={18} />
                            ) : (
                              <File size={18} />
                            )}
                          </div>
                          <div className="min-w-0">
                            <div className="text-xs font-bold text-white truncate">
                              {asset.name}
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1.5">
                              <span>{asset.size}</span>
                              <span>•</span>
                              <span>{asset.date}</span>
                              {asset.folder && (
                                <>
                                  <span>•</span>
                                  <span className="text-slate-400 font-medium">
                                    {asset.folder}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Selection Checkmark */}
                        <div
                          className={`w-5 h-5 rounded-full flex items-center justify-center border transition-all ${
                            isSelected
                              ? "bg-cyan-500 border-cyan-500 text-slate-950 font-bold"
                              : "border-[#1B2940] bg-[#101827]"
                          }`}
                        >
                          {isSelected && <Check size={12} strokeWidth={3} />}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* 4. Modal Footer Actions (Back on left, Continue on right) */}
        <div className="pt-4 mt-3 border-t border-[#1B2940] flex items-center justify-between flex-shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white font-bold text-xs flex items-center gap-1.5 px-3 py-2 rounded-xl hover:bg-[#101827] transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>

          <button
            type="button"
            onClick={handleContinue}
            className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-full shadow-lg hover:shadow-cyan-500/25 transition-all duration-200 cursor-pointer flex items-center gap-1.5 active:scale-95"
          >
            <span>Continue</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
