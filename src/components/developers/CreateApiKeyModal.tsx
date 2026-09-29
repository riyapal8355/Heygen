"use client";

import React, { useState } from "react";
import { X, Key, Copy, Check, ShieldCheck, AlertCircle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

interface CreateApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateKey?: (keyData: { name: string; env: "production" | "sandbox"; permissions: "full" | "read_only" }) => void;
  onKeyCreated?: () => void;
}

export default function CreateApiKeyModal({
  isOpen,
  onClose,
  onCreateKey,
  onKeyCreated,
}: CreateApiKeyModalProps) {
  const { currentWorkspace } = useAuth();
  const [keyName, setKeyName] = useState("");
  const [env, setEnv] = useState<"production" | "sandbox">("production");
  const [permissions, setPermissions] = useState<"full" | "read_only">("full");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim() || isSubmitting) return;

    if (!currentWorkspace?.id) {
      setErrorMessage("No active workspace found.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const res = await api.developer.createApiKey(currentWorkspace.id, {
        name: keyName.trim(),
        environment: env,
        permissions,
      });

      setCreatedKey(res.secret_key);
      onCreateKey?.({
        name: keyName.trim(),
        env,
        permissions,
      });
      onKeyCreated?.();
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to create API key");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (createdKey) {
      navigator.clipboard?.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDone = () => {
    setKeyName("");
    setCreatedKey(null);
    setCopied(false);
    setErrorMessage(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-[#0c111e] text-slate-100 rounded-3xl shadow-2xl border border-[#22304f] p-7 sm:p-8 animate-in zoom-in-95 duration-200 font-sans"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 flex items-center justify-center">
              <Key size={17} />
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              {createdKey ? "Save your API Key" : "Create API Key"}
            </h2>
          </div>
          <button
            onClick={handleDone}
            className="text-slate-400 hover:text-white p-1.5 rounded-full hover:bg-[#162035] transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {createdKey ? (
          /* Secret Key Display State */
          <div className="space-y-5 animate-in fade-in duration-200">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3">
              <AlertCircle size={18} className="text-amber-400 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-200/90 leading-relaxed">
                Please copy this key and store it in a secure location. You will not be able to view this secret key again.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Secret API Key
              </label>
              <div className="flex items-center gap-2 bg-[#121828] border border-[#22304d] rounded-2xl p-2.5 pl-4">
                <code className="flex-1 font-mono text-xs text-cyan-300 select-all truncate">
                  {createdKey}
                </code>
                <button
                  onClick={handleCopy}
                  className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-3 py-1.5 rounded-xl text-xs flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 shadow-sm"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  <span>{copied ? "Copied!" : "Copy"}</span>
                </button>
              </div>
            </div>

            <button
              onClick={handleDone}
              className="w-full py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold rounded-full text-sm transition-all shadow-lg shadow-cyan-500/25 cursor-pointer"
            >
              Done & Close
            </button>
          </div>
        ) : (
          /* Input Form State */
          <form onSubmit={handleGenerate} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Key Name
              </label>
              <input
                type="text"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g. Next.js Production Backend, Discord Bot"
                autoFocus
                className="w-full bg-[#121828] border border-[#22304d] hover:border-slate-500 focus:border-cyan-500 rounded-2xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Environment
                </label>
                <select
                  value={env}
                  onChange={(e) => setEnv(e.target.value as any)}
                  className="w-full bg-[#121828] border border-[#22304d] rounded-2xl px-3.5 py-3 text-xs text-white focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="production">Production (Live)</option>
                  <option value="sandbox">Sandbox (Test)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Permissions
                </label>
                <select
                  value={permissions}
                  onChange={(e) => setPermissions(e.target.value as any)}
                  className="w-full bg-[#121828] border border-[#22304d] rounded-2xl px-3.5 py-3 text-xs text-white focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="full">Full Access (Read & Write)</option>
                  <option value="read_only">Read Only</option>
                </select>
              </div>
            </div>

            {errorMessage && (
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-3 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle size={15} className="shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={!keyName.trim() || isSubmitting}
                className={`w-full py-3.5 rounded-full text-sm font-bold transition-all duration-200 cursor-pointer ${
                  keyName.trim() && !isSubmitting
                    ? "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 shadow-lg shadow-cyan-500/25"
                    : "bg-[#141c2e] text-slate-500 border border-[#22304d]/40 cursor-not-allowed"
                }`}
              >
                {isSubmitting ? "Creating..." : "Create API Key"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
