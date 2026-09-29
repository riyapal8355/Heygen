"use client";

import React, { useState } from "react";
import { X, Shield, Lock, CheckCircle2 } from "lucide-react";

interface ImportVoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function ImportVoiceModal({
  isOpen,
  onClose,
  onSuccess,
}: ImportVoiceModalProps) {
  const [provider, setProvider] = useState<"elevenlabs" | "lmnt">("elevenlabs");
  const [apiKey, setApiKey] = useState("");
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (!apiKey.trim()) return;
    setInfoMessage(
      `Third-party cloud voice import (${provider === "elevenlabs" ? "ElevenLabs" : "LMNT"}) is not yet supported on this backend (BACKEND MISSING). Please use OpenVoice local cloning.`
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-in fade-in duration-200 select-none">
      <div className="w-full max-w-2xl bg-white dark:bg-[#0e1322] text-slate-900 dark:text-white rounded-3xl p-7 shadow-2xl border border-slate-200 dark:border-[#22304f] relative overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-[#1c2742]">
          <h2 className="text-xl font-bold tracking-tight">Import voice</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-[#19243d] transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Security Alert Banner (Matches Screenshot 3) */}
        <div className="mt-5 p-4 rounded-2xl bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800/40 flex items-start gap-3 text-cyan-900 dark:text-cyan-200">
          <div className="w-6 h-6 rounded-lg bg-cyan-900/10 dark:bg-cyan-400/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Shield size={16} className="text-cyan-600 dark:text-cyan-400" />
          </div>
          <p className="text-xs leading-relaxed">
            Rest assured that VidoAI will only use your resources when your current API key is valid. If you refresh your API key with the 3rd party service provider, the current operation will become invalid.
          </p>
        </div>

        {/* Service Provider Selection */}
        <div className="mt-6">
          <label className="text-xs font-bold text-slate-800 dark:text-slate-200 block mb-2.5">
            Service provider
          </label>
          <div className="grid grid-cols-3 gap-3">
            {/* ElevenLabs */}
            <div
              onClick={() => setProvider("elevenlabs")}
              className={`p-4 rounded-2xl border flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                provider === "elevenlabs"
                  ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/20 shadow-md ring-1 ring-blue-500"
                  : "border-slate-200 dark:border-[#1e2942] hover:border-slate-400 dark:hover:border-slate-600 bg-slate-50/50 dark:bg-[#111728]"
              }`}
            >
              <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white">
                IIElevenLabs
              </span>
            </div>

            {/* LMNT */}
            <div
              onClick={() => setProvider("lmnt")}
              className={`p-4 rounded-2xl border flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                provider === "lmnt"
                  ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/20 shadow-md ring-1 ring-blue-500"
                  : "border-slate-200 dark:border-[#1e2942] hover:border-slate-400 dark:hover:border-slate-600 bg-slate-50/50 dark:bg-[#111728]"
              }`}
            >
              <span className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white flex items-center gap-1">
                <span className="text-cyan-500">◌</span> LMNT
              </span>
            </div>

            {/* Coming Soon */}
            <div className="p-4 rounded-2xl border border-dashed border-slate-200 dark:border-[#1e2942] flex flex-col items-center justify-center text-center opacity-60">
              <span className="text-xs font-medium text-slate-400">Coming soon</span>
            </div>
          </div>
        </div>

        {/* API Key Input */}
        <div className="mt-6">
          <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 mb-2">
            API key <Lock size={12} className="text-purple-400" />
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste your API key here"
            className="w-full bg-slate-50 dark:bg-[#111728] border border-slate-200 dark:border-[#22304d] rounded-2xl px-4 py-3 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 transition-colors shadow-inner"
          />
        </div>

        {infoMessage && (
          <div className="mt-4 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs leading-relaxed">
            {infoMessage}
          </div>
        )}

        {/* Actions */}
        <div className="mt-8 flex items-center gap-3">
          <button
            onClick={handleConfirm}
            disabled={!apiKey.trim()}
            className={`px-7 py-2.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
              apiKey.trim()
                ? "bg-slate-900 hover:bg-slate-800 dark:bg-blue-600 dark:hover:bg-blue-500 text-white shadow-md"
                : "bg-slate-200 dark:bg-[#18233a] text-slate-400 cursor-not-allowed"
            }`}
          >
            Confirm
          </button>

          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-full border border-slate-200 dark:border-[#22304d] text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-[#18233a] transition-all cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
