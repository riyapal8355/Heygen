"use client";

import React, { useState } from "react";
import { Sun, Moon, Sparkles } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

interface ThemeToggleProps {
  variant?: "floating" | "inline";
}

export default function ThemeToggle({ variant = "floating" }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const [isHovered, setIsHovered] = useState(false);

  const isDark = theme === "dark";

  if (variant === "inline") {
    return (
      <button
        onClick={toggleTheme}
        title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#121828] hover:bg-[#1c2740] border border-[#22304d] text-slate-300 hover:text-white transition-all text-xs font-semibold cursor-pointer shadow-sm"
      >
        {isDark ? (
          <>
            <Sun size={14} className="text-amber-400 animate-spin-slow" />
            <span>Light</span>
          </>
        ) : (
          <>
            <Moon size={14} className="text-indigo-400" />
            <span>Dark</span>
          </>
        )}
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2 select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Tooltip on Hover */}
      {isHovered && (
        <div className="bg-[#0c111e]/95 backdrop-blur-md text-white text-xs font-semibold px-3 py-1.5 rounded-full border border-[#22304f] shadow-2xl animate-in fade-in zoom-in-95 duration-150 flex items-center gap-1.5">
          <Sparkles size={12} className="text-cyan-400" />
          <span>{isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}</span>
        </div>
      )}

      {/* Main Corner Toggle Button */}
      <button
        id="global-theme-toggle-btn"
        data-testid="global-theme-toggle-btn"
        onClick={toggleTheme}
        aria-label="Toggle light and dark theme"
        className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl cursor-pointer group hover:scale-110 active:scale-95 border ${
          isDark
            ? "bg-[#0f1523]/90 hover:bg-[#162035] text-amber-400 border-[#26375c] shadow-cyan-900/30 shadow-lg backdrop-blur-xl"
            : "bg-white/95 hover:bg-slate-50 text-indigo-600 border-slate-200 shadow-xl backdrop-blur-xl"
        }`}
      >
        <div className="relative w-6 h-6 flex items-center justify-center">
          {/* Sun Icon */}
          <Sun
            size={20}
            className={`absolute transition-all duration-500 transform ${
              isDark
                ? "opacity-100 rotate-0 scale-100 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.5)]"
                : "opacity-0 -rotate-90 scale-0 text-amber-500"
            }`}
          />

          {/* Moon Icon */}
          <Moon
            size={20}
            className={`absolute transition-all duration-500 transform ${
              isDark
                ? "opacity-0 rotate-90 scale-0 text-slate-400"
                : "opacity-100 rotate-0 scale-100 text-indigo-600 drop-shadow-[0_0_8px_rgba(99,102,241,0.4)]"
            }`}
          />
        </div>
      </button>
    </div>
  );
}
