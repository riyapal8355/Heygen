"use client";

import React, { useState, useRef, useEffect } from "react";
import { Search, BookOpen, FileText } from "lucide-react";

interface KnowledgeHubModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDocument?: (docTitle: string) => void;
}

export default function KnowledgeHubModal({
  isOpen,
  onClose,
  onSelectDocument,
}: KnowledgeHubModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const modalRef = useRef<HTMLDivElement>(null);

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
        className="w-full max-w-xl md:max-w-2xl bg-[#0A0F1A] rounded-3xl p-6 sm:p-8 shadow-2xl border border-[#1B2940] min-h-[460px] flex flex-col text-slate-100 animate-in zoom-in-95 duration-150 relative"
      >
        {/* 1. Header Title */}
        <div className="pb-1">
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Knowledge Hub
          </h2>
        </div>

        {/* 2. Full-Width Search Input with Focus Ring */}
        <div className="mt-4 mb-2">
          <div className="relative w-full">
            <Search
              size={17}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              autoFocus
              className="w-full bg-[#07090e] border border-[#1B2940] rounded-2xl pl-11 pr-4 py-3 text-xs sm:text-sm text-white placeholder:text-slate-500 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all shadow-sm"
            />
          </div>
        </div>

        {/* 3. Centered Empty State */}
        <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
          <div className="w-16 h-16 rounded-full bg-[#101827] flex items-center justify-center text-cyan-400 mb-4 ring-1 ring-[#1B2940]">
            <BookOpen size={30} strokeWidth={1.7} className="text-cyan-400" />
          </div>

          <h3 className="text-base font-bold text-white tracking-tight">
            No documents found
          </h3>

          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Upload documents in Knowledge Hub
          </p>
        </div>
      </div>
    </div>
  );
}
