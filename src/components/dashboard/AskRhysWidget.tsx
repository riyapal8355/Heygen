"use client";

import React, { useState } from "react";
import { Sparkles, X, Send, Bot, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

interface AskRhysWidgetProps {
  variant?: "compact" | "banner";
  initialBanner?: boolean;
  onCloseBanner?: () => void;
  theme?: "light" | "dark";
  projectId?: string | null;
}

export default function AskRhysWidget({
  variant,
  initialBanner,
  onCloseBanner,
  theme: propTheme,
  projectId,
}: AskRhysWidgetProps = {}) {
  const { currentWorkspace } = useAuth();
  const { theme: contextTheme } = useTheme();
  const theme = propTheme || contextTheme;
  const effectiveVariant = variant || (initialBanner ? "banner" : "compact");
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; text: string }[]>([
    {
      role: "assistant",
      text: "Hi! I'm Rhys, your AI Video Copilot. How can I help you refine your script or video project today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([
    "Generate TikTok Script",
    "Suggest Avatars",
    "Translate video",
  ]);

  const handleSend = async (overrideText?: string) => {
    const textToSend = (overrideText || input).trim();
    if (!textToSend || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", text: textToSend }]);
    setInput("");
    setIsLoading(true);

    try {
      if (!currentWorkspace?.id) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "Please select or activate a workspace to consult with Rhys Copilot.",
          },
        ]);
        return;
      }

      const historyPayload = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6)
        .map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.text,
        }));

      const resp = await api.askRhys(currentWorkspace.id, {
        message: textToSend,
        project_id: projectId || null,
        conversation_id: conversationId || undefined,
        context_mode: projectId ? "project" : "general",
        history: historyPayload,
      });

      if (resp.conversation_id) {
        setConversationId(resp.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: resp.response,
        },
      ]);

      if (resp.suggestions && resp.suggestions.length > 0) {
        setSuggestions(resp.suggestions);
      }
    } catch (err: any) {
      const errMsg = err?.message || "Rhys encountered an unexpected issue. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Rhys Error: ${errMsg}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Top Right Header Pill */}
      {effectiveVariant === "banner" ? (
        <div
          className={`flex items-center gap-2.5 px-3.5 py-1.5 rounded-full transition-all duration-200 group ${
            theme === "light"
              ? "bg-white hover:bg-slate-50 border border-slate-200/90 shadow-sm"
              : "bg-[#121828] hover:bg-[#18233c] border border-[#1b2940] shadow-sm"
          }`}
        >
          <div
            className="relative cursor-pointer"
            onClick={() => setIsOpen(true)}
            title="Open Rhys Copilot"
          >
            <div
              className={`w-6 h-6 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-white text-xs font-bold ring-2 ${
                theme === "light" ? "ring-slate-100" : "ring-[#0c1220]"
              }`}
            >
              👨‍💻
            </div>
            <span
              className={`absolute bottom-0 right-0 w-2 h-2 bg-emerald-500 rounded-full ring-1.5 ${
                theme === "light" ? "ring-white" : "ring-[#0c1220]"
              }`}
            ></span>
          </div>

          <button
            onClick={() => setIsOpen(true)}
            className={`text-xs font-medium cursor-pointer flex items-center gap-1 text-left ${
              theme === "light"
                ? "text-slate-700 group-hover:text-slate-900"
                : "text-slate-300 group-hover:text-white"
            }`}
          >
            <span>Not sure about something?</span>
            <span className={theme === "light" ? "font-semibold text-slate-950" : "font-semibold text-cyan-400"}>
              Ask Rhys.
            </span>
          </button>

          {onCloseBanner && (
            <button
              onClick={onCloseBanner}
              className={`p-0.5 ml-1 rounded-full transition-colors cursor-pointer ${
                theme === "light"
                  ? "text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                  : "text-slate-400 hover:text-white hover:bg-[#18233c]"
              }`}
              title="Dismiss"
            >
              <X size={14} />
            </button>
          )}
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className={`flex items-center gap-2.5 px-3.5 py-1.5 rounded-full transition-all duration-200 group cursor-pointer ${
            theme === "light"
              ? "bg-white hover:bg-slate-100 border border-slate-200 text-slate-800 shadow-sm"
              : "bg-[#121829] hover:bg-[#182138] border border-[#222f4c] hover:border-[#32456e] text-slate-200 shadow-md"
          }`}
        >
          <div className="relative">
            <div className={`w-7 h-7 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-white text-xs font-bold ring-2 ${
              theme === "light" ? "ring-slate-100" : "ring-[#0c1220]"
            }`}>
              👨‍💻
            </div>
            <span className={`absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-2 ${
              theme === "light" ? "ring-white" : "ring-[#0c1220]"
            }`}></span>
          </div>
          <span className={`text-xs font-medium ${
            theme === "light" ? "text-slate-800 group-hover:text-slate-950" : "text-slate-200 group-hover:text-white"
          }`}>
            Ask Rhys
          </span>
        </button>
      )}

      {/* AI Copilot Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className={`w-full max-w-md h-[600px] rounded-2xl shadow-2xl flex flex-col overflow-hidden ${
            theme === "light"
              ? "bg-white border border-slate-200 text-slate-900"
              : "bg-[#0c111e] border border-[#222f4d] text-white"
          }`}>
            {/* Header */}
            <div className={`p-4 flex items-center justify-between border-b ${
              theme === "light" ? "bg-slate-50 border-slate-200" : "bg-[#121829] border-[#202c49]"
            }`}>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-white text-sm font-bold">
                    👨‍💻
                  </div>
                  <span className={`absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-2 ${
                    theme === "light" ? "ring-white" : "ring-[#0c111e]"
                  }`}></span>
                </div>
                <div>
                  <h3 className={`text-sm font-semibold flex items-center gap-1.5 ${
                    theme === "light" ? "text-slate-900" : "text-white"
                  }`}>
                    Rhys AI Copilot <Sparkles size={14} className="text-cyan-500" />
                  </h3>
                  <p className={`text-[11px] ${theme === "light" ? "text-slate-500" : "text-slate-400"}`}>
                    Your AI Video & Script Assistant
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className={`p-1.5 rounded-lg transition-colors ${
                  theme === "light"
                    ? "text-slate-500 hover:text-slate-900 hover:bg-slate-200"
                    : "text-slate-400 hover:text-white hover:bg-[#1a233a]"
                }`}
              >
                <X size={18} />
              </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-blue-500 flex-shrink-0 text-xs">
                      <Bot size={14} />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                      m.role === "user"
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-none"
                        : theme === "light"
                        ? "bg-slate-100 border border-slate-200 text-slate-800 rounded-bl-none shadow-xs"
                        : "bg-[#141b2e] border border-[#233152] text-slate-200 rounded-bl-none shadow-sm"
                    }`}
                  >
                    {m.text}
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-2.5 justify-start">
                  <div className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-blue-500 flex-shrink-0 text-xs">
                    <Bot size={14} />
                  </div>
                  <div className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed rounded-bl-none shadow-sm flex items-center gap-2 ${
                    theme === "light"
                      ? "bg-slate-100 border border-slate-200 text-slate-600"
                      : "bg-[#141b2e] border border-[#233152] text-slate-400"
                  }`}>
                    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                    <span>Rhys is thinking...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Suggestions */}
            <div className={`px-4 py-2 border-t flex gap-1.5 overflow-x-auto ${
              theme === "light" ? "border-slate-200 bg-slate-50" : "border-[#1a243d] bg-[#0c111e]"
            }`}>
              {suggestions.map((chip) => (
                <button
                  key={chip}
                  disabled={isLoading}
                  onClick={() => {
                    setInput(chip);
                  }}
                  className={`text-[10px] px-2.5 py-1 rounded-full whitespace-nowrap transition-colors disabled:opacity-50 cursor-pointer ${
                    theme === "light"
                      ? "bg-white hover:bg-slate-100 text-blue-700 border border-blue-200 shadow-xs"
                      : "bg-[#141d31] hover:bg-[#1f2c4a] text-blue-300 border border-blue-900/40"
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <div className={`p-3 border-t flex items-center gap-2 ${
              theme === "light" ? "bg-slate-50 border-slate-200" : "bg-[#101625] border-[#1a243d]"
            }`}>
              <input
                type="text"
                value={input}
                disabled={isLoading}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={isLoading ? "Rhys is thinking..." : "Ask Rhys to write a script or build a video..."}
                className={`flex-1 rounded-xl px-3.5 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60 transition-all ${
                  theme === "light"
                    ? "bg-white border border-slate-300 text-slate-900 placeholder-slate-400 focus:border-blue-500"
                    : "bg-[#151c2e] border border-[#23304e] text-white placeholder-slate-500 focus:border-blue-500"
                }`}
              />
              <button
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim()}
                className="bg-blue-600 hover:bg-blue-500 text-white p-2 rounded-xl transition-colors shadow-md shadow-blue-600/20 disabled:opacity-50 cursor-pointer"
              >
                <Send size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
