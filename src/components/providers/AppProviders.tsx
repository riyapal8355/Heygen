"use client";

import React from "react";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import ThemeToggle from "@/components/common/ThemeToggle";

export default function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        {children}
        <ThemeToggle variant="floating" />
      </AuthProvider>
    </ThemeProvider>
  );
}
