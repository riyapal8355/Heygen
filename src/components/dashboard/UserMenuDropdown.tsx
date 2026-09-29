"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import {
  LogOut,
  User,
  Settings,
  CreditCard,
  Key,
  Shield,
  Sparkles,
  ChevronRight,
  Gem,
  Sun,
  Moon,
} from "lucide-react";

interface UserMenuDropdownProps {
  placement?: "left-rail" | "top-bar";
  onSelectTab?: (tab: string) => void;
}

export default function UserMenuDropdown({
  placement = "left-rail",
  onSelectTab,
}: UserMenuDropdownProps) {
  const { user, logout, currentWorkspace, workspaces, switchWorkspace } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [activeModal, setActiveModal] = useState<"profile" | "billing" | "workspace" | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const path = event.composedPath ? event.composedPath() : [];
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !path.includes(dropdownRef.current)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isLight = theme === "light";

  if (!user) return null;

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        {/* Trigger Button */}
        <button
          id="user-menu-btn"
          data-testid="user-menu-btn"
          onClick={() => setIsOpen(!isOpen)}
          className={`w-10 h-10 rounded-full bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-600 flex items-center justify-center font-bold text-white text-base shadow-md border-2 hover:border-purple-400 hover:scale-105 transition-all cursor-pointer ${
            isLight ? "border-slate-300" : "border-[#1e2a44]"
          }`}
          title={`${user.name} (${user.email})`}
        >
          {user.avatarInitial}
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div
            className={`absolute ${
              placement === "left-rail"
                ? "left-14 bottom-0"
                : "right-0 top-12"
            } w-72 rounded-2xl shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl border ${
              isLight
                ? "bg-white border-slate-200 text-slate-900"
                : "bg-[#0d1222] border-[#22304f] text-white"
            }`}
          >
            {/* User Header */}
            <div className={`p-3 rounded-xl border mb-2 ${
              isLight ? "bg-slate-50 border-slate-200" : "bg-[#131b2e] border-[#1f2c49]"
            }`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-500 flex items-center justify-center text-white font-bold text-base ring-2 ring-purple-400/30">
                  {user.avatarInitial}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className={`text-xs font-bold truncate flex items-center gap-1.5 ${
                    isLight ? "text-slate-900" : "text-white"
                  }`}>
                    {user.name}
                    <span className="text-[9px] bg-blue-500/20 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded border border-blue-500/30 font-medium">
                      {user.plan}
                    </span>
                  </h4>
                  <p className={`text-[11px] truncate ${isLight ? "text-slate-500" : "text-slate-400"}`}>{user.email}</p>
                </div>
              </div>

              {/* Credits bar */}
              <div className={`mt-3 pt-2.5 border-t ${isLight ? "border-slate-200" : "border-[#1c2843]"}`}>
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className={`flex items-center gap-1 font-medium ${isLight ? "text-amber-600" : "text-amber-300"}`}>
                    <Gem size={12} /> AI Credits
                  </span>
                  <span className={`font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                    {user.credits} / {user.maxCredits}
                  </span>
                </div>
                <div className={`w-full h-1.5 rounded-full overflow-hidden ${isLight ? "bg-slate-200" : "bg-[#1a253c]"}`}>
                  <div
                    className="h-full bg-gradient-to-r from-amber-400 to-purple-500"
                    style={{ width: `${(user.credits / user.maxCredits) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Links */}
            <div className={`space-y-0.5 text-xs ${isLight ? "text-slate-700" : "text-slate-300"}`}>
              <button
                onClick={() => {
                  setIsOpen(false);
                  setActiveModal("profile");
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                  isLight ? "hover:bg-slate-100 hover:text-slate-900" : "hover:bg-[#162035] hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <User size={15} className={isLight ? "text-slate-500" : "text-slate-400"} /> Account Profile
                </span>
                <ChevronRight size={13} className="text-slate-400" />
              </button>

              <button
                onClick={() => {
                  setIsOpen(false);
                  setActiveModal("billing");
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                  isLight ? "hover:bg-slate-100 hover:text-slate-900" : "hover:bg-[#162035] hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <CreditCard size={15} className={isLight ? "text-slate-500" : "text-slate-400"} /> Subscription & Billing
                </span>
                <ChevronRight size={13} className="text-slate-400" />
              </button>

              <button
                onClick={() => {
                  setIsOpen(false);
                  if (onSelectTab) onSelectTab("developer");
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                  isLight ? "hover:bg-slate-100 hover:text-slate-900" : "hover:bg-[#162035] hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Key size={15} className={isLight ? "text-slate-500" : "text-slate-400"} /> API Keys & Webhooks
                </span>
                <ChevronRight size={13} className="text-slate-400" />
              </button>

              <button
                onClick={() => {
                  setIsOpen(false);
                  setActiveModal("workspace");
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                  isLight ? "hover:bg-slate-100 hover:text-slate-900" : "hover:bg-[#162035] hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Settings size={15} className={isLight ? "text-slate-500" : "text-slate-400"} /> Workspace Settings
                </span>
                <ChevronRight size={13} className="text-slate-400" />
              </button>

              {/* Theme Toggle in Menu */}
              <button
                id="user-menu-theme-toggle-btn"
                data-testid="user-menu-theme-toggle-btn"
                onClick={() => toggleTheme()}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-colors cursor-pointer ${
                  isLight ? "hover:bg-slate-100 hover:text-slate-900" : "hover:bg-[#162035] hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2.5">
                  {theme === "dark" ? (
                    <Sun size={15} className="text-amber-400" />
                  ) : (
                    <Moon size={15} className="text-indigo-600" />
                  )}
                  <span>Theme: {theme === "dark" ? "Dark Mode" : "Light Mode"}</span>
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  isLight
                    ? "bg-slate-100 text-blue-700 border-slate-200"
                    : "bg-[#121828] text-cyan-400 border-[#22304d]"
                }`}>
                  {theme === "dark" ? "Light ☀" : "Dark ☾"}
                </span>
              </button>
            </div>

            <div className={`my-1.5 h-[1px] ${isLight ? "bg-slate-200" : "bg-[#1a253c]"}`}></div>

            {/* Logout Action */}
            <button
              id="user-logout-btn"
              data-testid="user-logout-btn"
              onClick={async () => {
                setIsOpen(false);
                await logout();
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-rose-500 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors text-xs font-semibold cursor-pointer"
            >
              <LogOut size={15} />
              <span>Sign Out / Log Out</span>
            </button>
          </div>
        )}
      </div>

      {/* Account Profile Modal */}
      {activeModal === "profile" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl p-6 border ${
            isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#0e1322] border-[#22304f] text-white"
          }`}>
            <div className={`flex items-center justify-between pb-3 border-b ${
              isLight ? "border-slate-200" : "border-[#1b2640]"
            }`}>
              <div className="flex items-center gap-2">
                <User size={18} className="text-blue-500" />
                <h3 className="text-sm font-bold">Account Profile</h3>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                className={`text-xs px-2 py-1 rounded transition-colors cursor-pointer ${
                  isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-700" : "bg-[#162035] text-slate-400 hover:text-white"
                }`}
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Display Name</span>
                <div className={`p-2.5 rounded-xl border font-medium ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-900" : "bg-[#121827] border-[#1e2a44] text-slate-200"
                }`}>
                  {user.name}
                </div>
              </div>
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Email Address</span>
                <div className={`p-2.5 rounded-xl border font-medium ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-900" : "bg-[#121827] border-[#1e2a44] text-slate-200"
                }`}>
                  {user.email}
                </div>
              </div>
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>User ID</span>
                <div className={`p-2.5 rounded-xl border font-mono text-[10px] select-all ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-600" : "bg-[#121827] border-[#1e2a44] text-slate-400"
                }`}>
                  {user.id}
                </div>
              </div>
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Workspace Role</span>
                <div className={`p-2.5 rounded-xl border font-medium ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-900" : "bg-[#121827] border-[#1e2a44] text-slate-200"
                }`}>
                  {user.role}
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Subscription & Billing Modal */}
      {activeModal === "billing" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl p-6 border ${
            isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#0e1322] border-[#22304f] text-white"
          }`}>
            <div className={`flex items-center justify-between pb-3 border-b ${
              isLight ? "border-slate-200" : "border-[#1b2640]"
            }`}>
              <div className="flex items-center gap-2">
                <CreditCard size={18} className="text-amber-500" />
                <h3 className="text-sm font-bold">Subscription & Billing</h3>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                className={`text-xs px-2 py-1 rounded transition-colors cursor-pointer ${
                  isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-700" : "bg-[#162035] text-slate-400 hover:text-white"
                }`}
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className={`p-3.5 rounded-xl border ${
                isLight ? "bg-slate-50 border-slate-200" : "bg-gradient-to-r from-[#141d33] to-[#121827] border-[#243456]"
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-bold ${isLight ? "text-slate-900" : "text-white"}`}>{user.plan}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/30">
                    Active
                  </span>
                </div>
                <p className={`text-[11px] ${isLight ? "text-slate-500" : "text-slate-400"}`}>Self-hosted HeyZen production tier.</p>
              </div>

              <div className={`p-3.5 rounded-xl border ${
                isLight ? "bg-slate-50 border-slate-200" : "bg-[#121827] border-[#1e2a44]"
              }`}>
                <div className="flex items-center justify-between text-[11px] mb-1.5">
                  <span className={`flex items-center gap-1.5 font-medium ${isLight ? "text-amber-700" : "text-amber-300"}`}>
                    <Gem size={13} /> Monthly AI Synthesis Quota
                  </span>
                  <span className={`font-bold ${isLight ? "text-slate-900" : "text-white"}`}>
                    {user.credits} / {user.maxCredits}
                  </span>
                </div>
                <div className={`w-full h-2 rounded-full overflow-hidden mb-1 ${isLight ? "bg-slate-200" : "bg-[#1a253c]"}`}>
                  <div
                    className="h-full bg-gradient-to-r from-amber-400 to-purple-500"
                    style={{ width: `${(user.credits / user.maxCredits) * 100}%` }}
                  ></div>
                </div>
                <span className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-500"}`}>Includes GPU synthesis, voice cloning, and rendering.</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Workspace Settings Modal */}
      {activeModal === "workspace" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl p-6 border ${
            isLight ? "bg-white border-slate-200 text-slate-900" : "bg-[#0e1322] border-[#22304f] text-white"
          }`}>
            <div className={`flex items-center justify-between pb-3 border-b ${
              isLight ? "border-slate-200" : "border-[#1b2640]"
            }`}>
              <div className="flex items-center gap-2">
                <Settings size={18} className="text-blue-500" />
                <h3 className="text-sm font-bold">Workspace Settings</h3>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                className={`text-xs px-2 py-1 rounded transition-colors cursor-pointer ${
                  isLight ? "bg-slate-100 hover:bg-slate-200 text-slate-700" : "bg-[#162035] text-slate-400 hover:text-white"
                }`}
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Active Workspace</span>
                <div className={`p-2.5 rounded-xl border font-medium ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-900" : "bg-[#121827] border-[#1e2a44] text-slate-200"
                }`}>
                  {currentWorkspace?.name || "Personal Workspace"}
                </div>
              </div>
              <div>
                <span className={`block text-[11px] mb-0.5 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Workspace ID</span>
                <div className={`p-2.5 rounded-xl border font-mono text-[10px] select-all ${
                  isLight ? "bg-slate-50 border-slate-200 text-slate-600" : "bg-[#121827] border-[#1e2a44] text-slate-400"
                }`}>
                  {currentWorkspace?.id || "N/A"}
                </div>
              </div>

              {workspaces.length > 1 && (
                <div>
                  <span className={`block text-[11px] mb-1 ${isLight ? "text-slate-500" : "text-slate-400"}`}>Switch Workspace</span>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto">
                    {workspaces.map((ws) => (
                      <button
                        key={ws.id}
                        onClick={() => switchWorkspace(ws.id)}
                        className={`w-full flex items-center justify-between p-2 rounded-xl text-left transition-colors cursor-pointer ${
                          ws.id === currentWorkspace?.id
                            ? isLight
                              ? "bg-blue-50 border border-blue-300 text-blue-700 font-semibold"
                              : "bg-blue-600/20 border border-blue-500/40 text-white"
                            : isLight
                            ? "bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700"
                            : "bg-[#121827] hover:bg-[#162035] border border-[#1e2a44] text-slate-300"
                        }`}
                      >
                        <span className="truncate">{ws.name}</span>
                        {ws.id === currentWorkspace?.id && (
                          <span className="text-[10px] text-blue-600 dark:text-cyan-400 font-semibold">Active</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-between items-center">
              <button
                onClick={() => {
                  setActiveModal(null);
                  if (onSelectTab) onSelectTab("developer");
                }}
                className="text-xs text-blue-600 dark:text-cyan-400 hover:underline font-medium cursor-pointer"
              >
                Manage API Keys & Webhooks →
              </button>
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
