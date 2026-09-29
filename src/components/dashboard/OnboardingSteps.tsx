"use client";

import React, { useState, useEffect, useCallback } from "react";
import { User, Mic2, Sparkles, Video, CheckCircle2, Circle, Lock, AlertCircle } from "lucide-react";
import RecordingModal from "./RecordingModal";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api, OnboardingStatusResponse } from "@/lib/api";

interface OnboardingStepsProps {
  workspaceId?: string;
  onNavigate?: (view: string) => void;
  onOpenStudio?: () => void;
}

export default function OnboardingSteps({
  workspaceId: propWorkspaceId,
  onNavigate,
  onOpenStudio,
}: OnboardingStepsProps) {
  const { currentWorkspace } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const effectiveWorkspaceId = propWorkspaceId || currentWorkspace?.id;

  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecordingOpen, setIsRecordingOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!effectiveWorkspaceId) return;
    try {
      setIsLoading(true);
      const res = await api.onboarding.getStatus(effectiveWorkspaceId);
      setStatus(res);
    } catch (err) {
      console.error("Failed to fetch onboarding status:", err);
    } finally {
      setIsLoading(false);
    }
  }, [effectiveWorkspaceId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const isStep1Done = Boolean(status?.step_1_digital_twin);
  const isStep2Done = Boolean(status?.step_2_voice);
  const isStep3Done = Boolean(status?.step_3_look);
  const isStep4Done = Boolean(status?.step_4_video);

  // Dependency graph:
  // Step 1: always available
  // Step 2: locked until Step 1 complete
  // Step 3: locked until Step 1 complete
  // Step 4: locked until Step 2 OR Step 3 complete
  const isStep2Unlocked = status?.is_step_2_unlocked ?? isStep1Done;
  const isStep3Unlocked = status?.is_step_3_unlocked ?? isStep1Done;
  const isStep4Unlocked = status?.is_step_4_unlocked ?? (isStep2Done || isStep3Done);

  const completedCount = status
    ? status.completed_count
    : [isStep1Done, isStep2Done, isStep3Done, isStep4Done].filter(Boolean).length;

  const handleStep2Click = () => {
    if (!isStep2Unlocked) {
      setNotice("Step 2 is locked. Please complete Step 1 (Create Digital Twin) first.");
      return;
    }
    setNotice(null);
    onNavigate?.("voices");
  };

  const handleStep3Click = () => {
    if (!isStep3Unlocked) {
      setNotice("Step 3 is locked. Please complete Step 1 (Create Digital Twin) first.");
      return;
    }
    setNotice(null);
    onNavigate?.("design_look");
  };

  const handleStep4Click = () => {
    if (!isStep4Unlocked) {
      setNotice("Step 4 is locked. Please complete Step 2 (Polish Voice) or Step 3 (Create Look) first.");
      return;
    }
    setNotice(null);
    if (onNavigate) {
      onNavigate("video_agent");
    } else if (onOpenStudio) {
      onOpenStudio();
    }
  };

  return (
    <div className="w-full">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-4">
        <div className={`flex items-center gap-2 font-medium text-xs ${isLight ? "text-slate-600" : "text-slate-300"}`}>
          <User size={15} className={isLight ? "text-slate-500" : "text-slate-400"} />
          <span>Finish your account setup - {completedCount}/4</span>
        </div>

        {notice && (
          <div className="flex items-center gap-1.5 text-xs text-amber-500 bg-amber-500/10 border border-amber-500/30 px-3 py-1 rounded-xl animate-in fade-in">
            <AlertCircle size={13} />
            <span>{notice}</span>
          </div>
        )}
      </div>

      {/* Steps 4-Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Step 1: Create Digital Twin */}
        <div
          className={`relative rounded-2xl p-4.5 flex flex-col justify-between transition-all duration-300 ${
            !isStep1Done
              ? isLight
                ? "bg-white border-2 border-blue-500 shadow-md shadow-blue-100 hover:border-blue-600"
                : "bg-[#0f1424] border border-blue-500/70 shadow-[0_0_20px_rgba(59,130,246,0.12)] hover:border-blue-400"
              : isLight
              ? "bg-emerald-50/70 border border-emerald-300 shadow-xs"
              : "bg-[#0d1220] border border-emerald-500/40"
          }`}
        >
          <div>
            {/* Top row */}
            <div className="flex items-center justify-between mb-3.5">
              {isStep1Done ? (
                <CheckCircle2 size={18} className="text-emerald-500" />
              ) : (
                <div className="w-4.5 h-4.5 rounded-full border-2 border-blue-500 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-blue-600"></div>
                </div>
              )}
              <span className="text-[11px] font-bold tracking-wider text-blue-600 dark:text-blue-400">
                STEP 1
              </span>
            </div>

            {/* Title & Icon */}
            <div className="flex items-center gap-2 mb-2">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${
                isLight ? "bg-blue-50 border-blue-200 text-blue-600" : "bg-blue-500/15 border-blue-500/30 text-blue-400"
              }`}>
                <User size={13} />
              </div>
              <h4 className={`font-semibold text-xs tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>
                Create Digital Twin
              </h4>
            </div>

            {/* Description */}
            <p className={`text-[11px] leading-relaxed mb-4 font-normal ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              Just 15 seconds, and don&apos;t worry about the background or outfit. This step captures how you move; everything else can be changed later.
            </p>
          </div>

          {/* Action Button */}
          {!isStep1Done ? (
            <button
              type="button"
              onClick={() => {
                setNotice(null);
                setIsRecordingOpen(true);
              }}
              className="w-full py-2 px-3 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-500 hover:from-blue-500 hover:to-indigo-500 shadow-md shadow-blue-500/25 transition-all duration-200 flex items-center justify-center gap-1.5 cursor-pointer"
            >
              Start Recording
            </button>
          ) : (
            <div className="flex items-center justify-between py-1">
              <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 size={13} /> Digital Twin ready
              </span>
              <button
                type="button"
                onClick={() => setIsRecordingOpen(true)}
                className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium cursor-pointer"
              >
                Record again
              </button>
            </div>
          )}
        </div>

        {/* Step 2: Polish your Voice */}
        <div
          role="button"
          tabIndex={0}
          aria-disabled={!isStep2Unlocked}
          onClick={handleStep2Click}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleStep2Click();
            }
          }}
          className={`relative rounded-2xl p-4.5 flex flex-col justify-between transition-all duration-300 ${
            isStep2Unlocked
              ? isStep2Done
                ? isLight
                  ? "bg-emerald-50/70 border border-emerald-300 cursor-pointer shadow-xs hover:border-emerald-400"
                  : "bg-[#0d1220] border border-emerald-500/40 cursor-pointer hover:border-emerald-400"
                : isLight
                ? "bg-white border border-blue-300 hover:border-blue-500 cursor-pointer shadow-xs"
                : "bg-[#0f1424] border border-blue-500/50 hover:border-blue-400 cursor-pointer shadow-[0_0_15px_rgba(59,130,246,0.1)]"
              : isLight
              ? "bg-slate-100/70 border border-slate-200 opacity-60 cursor-not-allowed"
              : "bg-[#0b0f1a] border border-[#182238] opacity-60 cursor-not-allowed"
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-3.5">
              {isStep2Done ? (
                <CheckCircle2 size={18} className="text-emerald-500" />
              ) : isStep2Unlocked ? (
                <Circle size={17} className="text-blue-500" />
              ) : (
                <Lock size={15} className={isLight ? "text-slate-400" : "text-slate-600"} />
              )}
              <span className={`text-[11px] font-bold tracking-wider ${isStep2Unlocked ? "text-blue-600 dark:text-blue-400" : "text-slate-400"}`}>
                STEP 2
              </span>
            </div>

            <div className="flex items-center gap-2 mb-2">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${
                isStep2Unlocked
                  ? isLight
                    ? "bg-blue-50 border-blue-200 text-blue-600"
                    : "bg-blue-500/15 border-blue-500/30 text-blue-400"
                  : isLight
                  ? "bg-slate-200 border-slate-300 text-slate-500"
                  : "bg-slate-800 border-slate-700 text-slate-400"
              }`}>
                <Mic2 size={13} />
              </div>
              <h4 className={`font-semibold text-xs tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>
                Polish your Voice
              </h4>
            </div>

            <p className={`text-[11px] leading-relaxed mb-4 font-normal ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              Hear the clone we made from your footage, or record a cleaner sample and re-clone.
            </p>
          </div>

          <div className="text-[11px] font-medium py-1">
            {isStep2Done ? (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={13} /> Voice Cloned
              </span>
            ) : isStep2Unlocked ? (
              <span className="text-blue-600 dark:text-blue-400 flex items-center gap-1 font-semibold">
                Click to customize voice →
              </span>
            ) : (
              <span className="text-slate-400 flex items-center gap-1">
                <Lock size={11} /> Unlocks after step 1
              </span>
            )}
          </div>
        </div>

        {/* Step 3: Create a Look */}
        <div
          role="button"
          tabIndex={0}
          aria-disabled={!isStep3Unlocked}
          onClick={handleStep3Click}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleStep3Click();
            }
          }}
          className={`relative rounded-2xl p-4.5 flex flex-col justify-between transition-all duration-300 ${
            isStep3Unlocked
              ? isStep3Done
                ? isLight
                  ? "bg-emerald-50/70 border border-emerald-300 cursor-pointer shadow-xs hover:border-emerald-400"
                  : "bg-[#0d1220] border border-emerald-500/40 cursor-pointer hover:border-emerald-400"
                : isLight
                ? "bg-white border border-emerald-300 hover:border-emerald-500 cursor-pointer shadow-xs"
                : "bg-[#0f1424] border border-emerald-500/50 hover:border-emerald-400 cursor-pointer shadow-[0_0_15px_rgba(16,185,129,0.1)]"
              : isLight
              ? "bg-slate-100/70 border border-slate-200 opacity-60 cursor-not-allowed"
              : "bg-[#0b0f1a] border border-[#182238] opacity-60 cursor-not-allowed"
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-3.5">
              {isStep3Done ? (
                <CheckCircle2 size={18} className="text-emerald-500" />
              ) : isStep3Unlocked ? (
                <Circle size={17} className="text-emerald-500" />
              ) : (
                <Lock size={15} className={isLight ? "text-slate-400" : "text-slate-600"} />
              )}
              <span className={`text-[11px] font-bold tracking-wider ${isStep3Unlocked ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>
                STEP 3
              </span>
            </div>

            <div className="flex items-center gap-2 mb-2">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${
                isStep3Unlocked
                  ? isLight
                    ? "bg-emerald-50 border-emerald-200 text-emerald-600"
                    : "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                  : isLight
                  ? "bg-slate-200 border-slate-300 text-slate-500"
                  : "bg-slate-800 border-slate-700 text-slate-400"
              }`}>
                <Sparkles size={13} />
              </div>
              <h4 className={`font-semibold text-xs tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>
                Create a Look
              </h4>
            </div>

            <p className={`text-[11px] leading-relaxed mb-4 font-normal ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              New outfits and scenes from one prompt, and your face stays locked.
            </p>
          </div>

          <div className="text-[11px] font-medium py-1">
            {isStep3Done ? (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={13} /> Custom Looks generated
              </span>
            ) : isStep3Unlocked ? (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-semibold">
                Click to design look →
              </span>
            ) : (
              <span className="text-slate-400 flex items-center gap-1">
                <Lock size={11} /> Unlocks after step 1
              </span>
            )}
          </div>
        </div>

        {/* Step 4: Make your first video */}
        <div
          role="button"
          tabIndex={0}
          aria-disabled={!isStep4Unlocked}
          onClick={handleStep4Click}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleStep4Click();
            }
          }}
          className={`relative rounded-2xl p-4.5 flex flex-col justify-between transition-all duration-300 ${
            isStep4Unlocked
              ? isStep4Done
                ? isLight
                  ? "bg-emerald-50/70 border border-emerald-300 cursor-pointer shadow-xs hover:border-emerald-400"
                  : "bg-[#0d1220] border border-emerald-500/40 cursor-pointer hover:border-emerald-400"
                : isLight
                ? "bg-white border border-purple-300 hover:border-purple-500 cursor-pointer shadow-xs"
                : "bg-[#0f1424] border border-purple-500/50 hover:border-purple-400 cursor-pointer shadow-[0_0_15px_rgba(168,85,247,0.1)]"
              : isLight
              ? "bg-slate-100/70 border border-slate-200 opacity-60 cursor-not-allowed"
              : "bg-[#0b0f1a] border border-[#182238] opacity-60 cursor-not-allowed"
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-3.5">
              {isStep4Done ? (
                <CheckCircle2 size={18} className="text-emerald-500" />
              ) : isStep4Unlocked ? (
                <Circle size={17} className="text-purple-500" />
              ) : (
                <Lock size={15} className={isLight ? "text-slate-400" : "text-slate-600"} />
              )}
              <span className={`text-[11px] font-bold tracking-wider ${isStep4Unlocked ? "text-purple-600 dark:text-purple-400" : "text-slate-400"}`}>
                STEP 4
              </span>
            </div>

            <div className="flex items-center gap-2 mb-2">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${
                isStep4Unlocked
                  ? isLight
                    ? "bg-purple-50 border-purple-200 text-purple-600"
                    : "bg-purple-500/15 border-purple-500/30 text-purple-400"
                  : isLight
                  ? "bg-slate-200 border-slate-300 text-slate-500"
                  : "bg-slate-800 border-slate-700 text-slate-400"
              }`}>
                <Video size={13} />
              </div>
              <h4 className={`font-semibold text-xs tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>
                Make your first video
              </h4>
            </div>

            <p className={`text-[11px] leading-relaxed mb-4 font-normal ${isLight ? "text-slate-600" : "text-slate-400"}`}>
              Start from a script, a prompt, or scene by scene in AI Studio.
            </p>
          </div>

          <div className="text-[11px] font-medium py-1">
            {isStep4Done ? (
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={13} /> Video Created!
              </span>
            ) : isStep4Unlocked ? (
              <span className="text-purple-600 dark:text-purple-400 flex items-center gap-1 font-semibold">
                Click to create video →
              </span>
            ) : (
              <span className="text-slate-400 flex items-center gap-1">
                <Lock size={11} /> Unlocks after step 2 or 3
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Recording Modal Component */}
      <RecordingModal
        isOpen={isRecordingOpen}
        workspaceId={effectiveWorkspaceId}
        onClose={() => setIsRecordingOpen(false)}
        onSuccess={() => {
          fetchStatus();
        }}
      />
    </div>
  );
}
