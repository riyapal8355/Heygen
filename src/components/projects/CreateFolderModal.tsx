"use client";

import React, { useState, useRef } from "react";
import {
  X,
  Lock,
  Users,
  Globe,
  ChevronDown,
  Check,
  ChevronUp,
} from "lucide-react";

interface CreateFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateFolder: (folderData: { name: string; accessLevel: "Private" | "Workspace" | "Public" }) => void;
}

export default function CreateFolderModal({
  isOpen,
  onClose,
  onCreateFolder,
}: CreateFolderModalProps) {
  const [folderName, setFolderName] = useState("");
  const [accessLevel, setAccessLevel] = useState<"Private" | "Workspace" | "Public">("Private");
  const [isAccessDropdownOpen, setIsAccessDropdownOpen] = useState(false);
  const [touched, setTouched] = useState(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  if (!isOpen) return null;

  const handleScrollUp = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ top: -60, behavior: "smooth" });
    }
  };

  const handleScrollDown = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ top: 60, behavior: "smooth" });
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setTouched(true);
    if (!folderName.trim()) return;

    onCreateFolder({
      name: folderName.trim(),
      accessLevel,
    });
    setFolderName("");
    setTouched(false);
    onClose();
  };

  const isNameEmpty = touched && !folderName.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 sm:p-6 animate-in fade-in duration-200">
      {/* Modal Card */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-[#0c111e] text-slate-100 rounded-3xl shadow-2xl border border-[#22304f] p-7 sm:p-8 animate-in zoom-in-95 duration-200 font-sans relative flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5 px-1">
          <h2 className="text-xl font-bold text-white tracking-tight">
            Create a folder
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-full hover:bg-[#162035] transition-colors cursor-pointer"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Form Body with Side Scroller Track & Buttons */}
        <div className="relative flex-1 flex gap-2 overflow-hidden my-1">
          {/* Main Form Fields Container */}
          <div
            ref={scrollContainerRef}
            className="flex-1 overflow-y-auto pr-2 space-y-5 scroll-smooth custom-scrollbar"
            style={{ maxHeight: "360px" }}
          >
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Folder Name Input */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  Folder name
                </label>
                <input
                  type="text"
                  value={folderName}
                  onChange={(e) => {
                    setFolderName(e.target.value);
                    if (touched) setTouched(false);
                  }}
                  onBlur={() => setTouched(true)}
                  placeholder="Enter folder name"
                  autoFocus
                  className={`w-full bg-[#121828] border ${
                    isNameEmpty
                      ? "border-rose-500 ring-2 ring-rose-500/20"
                      : "border-[#22304d] hover:border-slate-500 focus:border-cyan-500"
                  } rounded-2xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all`}
                />
                {/* Red Validation Warning */}
                <p className="text-[11px] font-medium text-rose-400 pl-0.5">
                  Folder Name *
                </p>
              </div>

              {/* Access Level Dropdown */}
              <div className="relative space-y-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  Access level
                </label>

                <div
                  onClick={() => setIsAccessDropdownOpen(!isAccessDropdownOpen)}
                  className="w-full bg-[#121828] border border-[#22304d] hover:border-slate-500 rounded-2xl px-4 py-3 flex items-center justify-between cursor-pointer transition-all shadow-xs"
                >
                  <div className="flex items-center gap-3">
                    {/* Cyan Rounded Lock Icon */}
                    <div className="w-8 h-8 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 flex items-center justify-center shrink-0">
                      {accessLevel === "Private" && <Lock size={15} strokeWidth={2.5} />}
                      {accessLevel === "Workspace" && <Users size={15} strokeWidth={2.5} />}
                      {accessLevel === "Public" && <Globe size={15} strokeWidth={2.5} />}
                    </div>
                    <span className="text-sm font-semibold text-slate-100">
                      {accessLevel}
                    </span>
                  </div>
                  <ChevronDown
                    size={18}
                    className={`text-slate-400 transition-transform duration-200 ${
                      isAccessDropdownOpen ? "rotate-180" : ""
                    }`}
                  />
                </div>

                {/* Dropdown Menu */}
                {isAccessDropdownOpen && (
                  <div
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-full left-0 right-0 mt-1.5 bg-[#0d1222] border border-[#22304f] rounded-2xl shadow-2xl p-2 z-20 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl"
                  >
                    {[
                      {
                        id: "Private",
                        label: "Private",
                        desc: "Only you can view and edit",
                        icon: Lock,
                      },
                      {
                        id: "Workspace",
                        label: "Workspace",
                        desc: "Anyone in your team can view and edit",
                        icon: Users,
                      },
                      {
                        id: "Public",
                        label: "Public",
                        desc: "Anyone with the link can view",
                        icon: Globe,
                      },
                    ].map((item) => {
                      const Icon = item.icon;
                      const isSelected = accessLevel === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            setAccessLevel(item.id as any);
                            setIsAccessDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-colors cursor-pointer ${
                            isSelected
                              ? "bg-[#162035] text-white"
                              : "hover:bg-[#141b2c] text-slate-300 hover:text-white"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-7 h-7 rounded-full bg-[#162035] text-cyan-400 flex items-center justify-center">
                              <Icon size={14} />
                            </div>
                            <div>
                              <div className="text-xs font-bold text-white">{item.label}</div>
                              <div className="text-[10px] text-slate-400">{item.desc}</div>
                            </div>
                          </div>
                          {isSelected && <Check size={16} className="text-cyan-400" strokeWidth={2.5} />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </form>
          </div>

          {/* Right Scrollbar Bar with Up & Down Arrow Buttons (Exact Screenshot Match) */}
          <div className="flex flex-col items-center justify-between w-4 bg-[#111728] border border-[#1e2a44] rounded-full py-1 shrink-0 select-none shadow-inner">
            <button
              onClick={handleScrollUp}
              className="text-slate-400 hover:text-cyan-400 p-0.5 rounded transition-colors cursor-pointer"
              title="Scroll Up"
            >
              <ChevronUp size={12} strokeWidth={3} />
            </button>

            {/* Scroll Thumb Indicator */}
            <div className="w-1.5 h-16 bg-[#253554] hover:bg-cyan-500 rounded-full my-1 transition-colors" />

            <button
              onClick={handleScrollDown}
              className="text-slate-400 hover:text-cyan-400 p-0.5 rounded transition-colors cursor-pointer"
              title="Scroll Down"
            >
              <ChevronDown size={12} strokeWidth={3} />
            </button>
          </div>
        </div>

        {/* Save Button */}
        <div className="pt-4 px-1">
          <button
            onClick={handleSubmit}
            disabled={!folderName.trim()}
            className={`w-full py-3.5 rounded-full text-sm font-bold transition-all duration-200 cursor-pointer ${
              folderName.trim()
                ? "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 shadow-lg shadow-cyan-500/25 hover:scale-[1.01]"
                : "bg-[#141c2e] text-slate-500 border border-[#22304d]/40 cursor-not-allowed"
            }`}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
