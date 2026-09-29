"use client";

import React, { useState } from "react";
import { X, Camera, Mic, RotateCw, CheckCircle2, Lock, ArrowRight } from "lucide-react";

interface EnablePermissionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPermissionsGranted?: () => void;
}

export default function EnablePermissionsModal({
  isOpen,
  onClose,
  onPermissionsGranted,
}: EnablePermissionsModalProps) {
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const handleToggleCamera = () => {
    const newState = !cameraEnabled;
    setCameraEnabled(newState);
    if (newState && micEnabled) {
      triggerSuccess();
    }
  };

  const handleToggleMic = () => {
    const newState = !micEnabled;
    setMicEnabled(newState);
    if (newState && cameraEnabled) {
      triggerSuccess();
    }
  };

  const triggerSuccess = () => {
    setIsSuccess(true);
    setTimeout(() => {
      if (onPermissionsGranted) onPermissionsGranted();
      onClose();
    }, 1200);
  };

  const handleEnableBoth = () => {
    setCameraEnabled(true);
    setMicEnabled(true);
    triggerSuccess();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-2xl bg-[#0e1322] text-white rounded-3xl p-7 shadow-2xl border border-[#22304f] relative overflow-hidden">
        {/* Header (Matches Screenshot) */}
        <div className="flex items-center justify-between pb-3 border-b border-[#1c2742]">
          <h2 className="text-lg font-bold tracking-tight text-white">
            Enable Camera & Microphone
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-full hover:bg-[#18233b] transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Main Mockup Container (Matches Screenshot) */}
        <div className="mt-5 bg-[#0a0e19] border border-[#1d273f] rounded-2xl p-5 relative overflow-hidden">
          {/* Browser Tab Header */}
          <div className="flex items-center gap-2 mb-3">
            <div className="bg-[#121828] border border-[#22304d] rounded-t-xl px-4 py-1.5 flex items-center gap-2 text-xs font-semibold shadow-sm text-slate-200">
              <div className="w-3 h-3 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600"></div>
              <span>VidoAI — Create Avatar</span>
            </div>
          </div>

          {/* Browser Address Bar with Permission Trigger */}
          <div className="bg-[#121828] border border-[#22304d] rounded-2xl p-2 px-3.5 flex items-center gap-3 shadow-inner mb-6 text-xs font-mono text-slate-300">
            <div className="flex items-center gap-1 text-slate-400">
              <span>&lt;</span>
              <span>&gt;</span>
              <RotateCw size={13} className="ml-1" />
            </div>

            <div className="flex-1 bg-[#0a0e19] border border-[#1e2a44] rounded-xl py-1 px-3 flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-[#1c2742] flex items-center justify-center text-[10px]">
                🔒
              </div>
              <span className="font-semibold text-slate-200">app.vidoai.com</span>
            </div>
          </div>

          {/* Center Simulated Permission Dialog (Matches Screenshot) */}
          <div className="min-h-[220px] flex flex-col items-center justify-center relative py-4">
            {/* Background Red Warning Pill */}
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold px-4 py-1.5 rounded-full mb-4 shadow-sm">
              Camera & Microphone are blocked
            </div>

            {/* Permission Floating Card */}
            <div className="w-72 bg-[#141d31] border border-[#2c3d64] rounded-2xl p-4 shadow-2xl z-10 space-y-3.5 animate-in zoom-in-95 duration-150">
              {/* Camera Row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-200">
                  <Camera size={16} className={cameraEnabled ? "text-cyan-400" : "text-slate-400"} />
                  <span>Camera</span>
                </div>

                {/* Toggle Switch */}
                <div
                  onClick={handleToggleCamera}
                  className={`w-10 h-5.5 rounded-full p-0.5 flex items-center transition-colors cursor-pointer ${
                    cameraEnabled
                      ? "bg-cyan-500 justify-end"
                      : "bg-[#25324e] justify-start"
                  }`}
                >
                  <div className="w-4.5 h-4.5 bg-white rounded-full shadow-md"></div>
                </div>
              </div>

              <div className="h-[1px] bg-[#1f2c4a]"></div>

              {/* Microphone Row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-200">
                  <Mic size={16} className={micEnabled ? "text-cyan-400" : "text-slate-400"} />
                  <span>Microphone</span>
                </div>

                {/* Toggle Switch */}
                <div
                  onClick={handleToggleMic}
                  className={`w-10 h-5.5 rounded-full p-0.5 flex items-center transition-colors cursor-pointer ${
                    micEnabled
                      ? "bg-cyan-500 justify-end"
                      : "bg-[#25324e] justify-start"
                  }`}
                >
                  <div className="w-4.5 h-4.5 bg-white rounded-full shadow-md"></div>
                </div>
              </div>
            </div>

            {/* Success Toast */}
            {isSuccess && (
              <div className="mt-3 flex items-center gap-1.5 text-xs font-bold text-emerald-400 animate-bounce">
                <CheckCircle2 size={16} /> Permissions granted! Starting camera...
              </div>
            )}
          </div>
        </div>

        {/* Footer Text (Matches Screenshot) */}
        <div className="mt-5 text-center">
          <p className="text-xs text-slate-400 mb-4">
            Please allow access in your browser settings and refresh the page.
          </p>

          <button
            onClick={handleEnableBoth}
            className="px-7 py-2.5 bg-white hover:bg-slate-200 text-slate-900 text-xs font-bold rounded-full shadow-md transition-all cursor-pointer"
          >
            Allow Both & Continue
          </button>
        </div>
      </div>
    </div>
  );
}
