"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  Sparkles,
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  Zap,
  PlayCircle,
  Video,
} from "lucide-react";

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup" | "forgot">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isDemoLoginEnabled = process.env.NEXT_PUBLIC_ENABLE_DEMO_LOGIN === "true";
  const demoEmail = process.env.NEXT_PUBLIC_DEMO_EMAIL || "";
  const demoPassword = process.env.NEXT_PUBLIC_DEMO_PASSWORD || "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("Please enter your email address");
      return;
    }
    if (mode !== "forgot" && !password.trim()) {
      setError("Please enter your password");
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else if (mode === "signup") {
        await signup(email.trim(), password, name.trim() || "Creator");
      } else {
        alert("Password reset instructions sent to " + email);
        setMode("login");
      }
    } catch (err: any) {
      setError(err?.message || "Authentication failed. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async () => {
    if (!demoEmail || !demoPassword) {
      setError("Demo credentials are not configured in environment.");
      return;
    }
    setError("");
    setIsSubmitting(true);
    try {
      await login(demoEmail, demoPassword);
    } catch {
      try {
        await signup(demoEmail, demoPassword, "Demo User");
      } catch (signupErr: any) {
        setError(signupErr?.message || "Demo login failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#06080e] flex items-center justify-center p-4 relative overflow-hidden select-none">
      {/* Background Neon Glowing Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/15 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/15 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-20 pointer-events-none"></div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-400 via-blue-600 to-purple-600 p-[2px] shadow-xl shadow-blue-500/25">
              <div className="w-full h-full bg-[#0b0f19] rounded-[14px] flex items-center justify-center">
                <div className="w-5 h-5 bg-gradient-to-tr from-cyan-400 to-purple-400 rounded-sm transform rotate-45 flex items-center justify-center">
                  <div className="w-2 h-2 bg-white rounded-full"></div>
                </div>
              </div>
            </div>
            <span className="text-2xl font-black text-white tracking-tight">VidoAI</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {mode === "login" && "Sign in to your Studio"}
            {mode === "signup" && "Create your VidoAI account"}
            {mode === "forgot" && "Reset your password"}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {mode === "login" && "Welcome back! Create viral AI videos in seconds"}
            {mode === "signup" && "Join thousands of creators making AI avatar videos"}
            {mode === "forgot" && "Enter your email to receive recovery instructions"}
          </p>
        </div>

        {/* Auth Glass Card */}
        <div className="bg-[#0c111f]/90 border border-[#1f2c49] rounded-3xl p-7 shadow-2xl backdrop-blur-xl">
          {/* Development-Only Demo Login Option (explicitly gated by NEXT_PUBLIC_ENABLE_DEMO_LOGIN) */}
          {isDemoLoginEnabled && (
            <>
              <div className="mb-5 p-3 rounded-2xl bg-[#12192c] border border-blue-500/30 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-xs">
                    D
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">Development Demo Access</p>
                    <p className="text-[10px] text-slate-400">Login with configured dev demo user</p>
                  </div>
                </div>
                <button
                  id="demo-login-btn"
                  data-testid="demo-login-btn"
                  type="button"
                  onClick={handleDemoLogin}
                  className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-md shadow-blue-600/30 flex items-center gap-1 transition-all cursor-pointer"
                >
                  <Zap size={12} /> Demo Login
                </button>
              </div>

              <div className="relative flex py-2 items-center mb-4">
                <div className="flex-grow border-t border-[#1a253d]"></div>
                <span className="flex-shrink mx-3 text-[11px] text-slate-500 uppercase tracking-wider font-semibold">
                  Or with credentials
                </span>
                <div className="flex-grow border-t border-[#1a253d]"></div>
              </div>
            </>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div
                id="auth-error-message"
                data-testid="auth-error-message"
                className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs"
              >
                {error}
              </div>
            )}

            {mode === "signup" && (
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-3 text-slate-500" />
                  <input
                    id="auth-name-input"
                    data-testid="auth-name-input"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Alex Morgan"
                    className="w-full bg-[#111728] border border-[#202c49] focus:border-blue-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-3 text-slate-500" />
                <input
                  id="auth-email-input"
                  data-testid="auth-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full bg-[#111728] border border-[#202c49] focus:border-blue-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            {mode !== "forgot" && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-slate-300">Password</label>
                  {mode === "login" && (
                    <button
                      id="auth-forgot-password-btn"
                      data-testid="auth-forgot-password-btn"
                      type="button"
                      onClick={() => setMode("forgot")}
                      className="text-[11px] text-blue-400 hover:underline"
                    >
                      Forgot?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-3 text-slate-500" />
                  <input
                    id="auth-password-input"
                    data-testid="auth-password-input"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#111728] border border-[#202c49] focus:border-blue-500 rounded-xl pl-10 pr-10 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none transition-colors"
                  />
                  <button
                    id="auth-toggle-password-btn"
                    data-testid="auth-toggle-password-btn"
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              id="auth-submit-btn"
              data-testid="auth-submit-btn"
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 transition-all mt-2 cursor-pointer"
            >
              <span>
                {isSubmitting
                  ? "Processing..."
                  : mode === "login"
                  ? "Sign In to VidoAI"
                  : mode === "signup"
                  ? "Create Account & Start Free"
                  : "Send Reset Link"}
              </span>
              <ArrowRight size={14} />
            </button>
          </form>

          {/* Switch Mode Footer */}
          <div className="mt-6 pt-4 border-t border-[#1a253d] text-center text-xs text-slate-400">
            {mode === "login" ? (
              <p>
                Don't have an account?{" "}
                <button
                  id="auth-switch-to-signup"
                  data-testid="auth-switch-to-signup"
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setError("");
                  }}
                  className="text-blue-400 hover:underline font-semibold"
                >
                  Sign up free
                </button>
              </p>
            ) : (
              <p>
                Already have an account?{" "}
                <button
                  id="auth-switch-to-login"
                  data-testid="auth-switch-to-login"
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setError("");
                  }}
                  className="text-blue-400 hover:underline font-semibold"
                >
                  Sign in
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Trust Badges */}
        <div className="mt-6 flex items-center justify-center gap-6 text-[11px] text-slate-500">
          <span className="flex items-center gap-1">
            <ShieldCheck size={13} className="text-emerald-400" /> SOC2 Compliant
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Zap size={13} className="text-amber-400" /> Instant Setup
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Video size={13} className="text-blue-400" /> 4K Ultra HD
          </span>
        </div>
      </div>
    </div>
  );
}
