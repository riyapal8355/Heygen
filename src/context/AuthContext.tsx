"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  api,
  getStoredAccessToken,
  setStoredAccessToken,
  WorkspaceSummary,
  UserSummary,
  UserWithWorkspacesResponse,
  ApiError,
} from "@/lib/api";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarInitial: string;
  role: string;
  credits: number;
  maxCredits: number;
  plan: string;
}

export type { WorkspaceSummary };

interface AuthContextType {
  user: UserProfile | null;
  currentWorkspace: WorkspaceSummary | null;
  workspaces: WorkspaceSummary[];
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  switchWorkspace: (workspaceId: string) => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapUserToProfile(user: UserSummary, role: string = "Creator"): UserProfile {
  const name = user.display_name || user.email.split("@")[0] || "User";
  const avatarInitial = name.charAt(0).toUpperCase() || "U";
  return {
    id: user.id,
    name,
    email: user.email,
    avatarInitial,
    role: role === "owner" ? "Workspace Owner" : "Content Creator",
    credits: 1000,
    maxCredits: 1000,
    plan: "Pro Creator",
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<WorkspaceSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isInitializing, setIsInitializing] = useState(true);

  // Clean up legacy mock data from localStorage
  useEffect(() => {
    try {
      localStorage.removeItem("vidoai_user");
    } catch {
      // ignore
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const meData = await api.auth.getMe();
      const wsList = meData.workspaces || [];
      setWorkspaces(wsList);

      const activeWs =
        wsList.find((w) => w.id === currentWorkspace?.id) || wsList[0] || null;
      setCurrentWorkspace(activeWs);

      const profile = mapUserToProfile(meData.user, activeWs?.role || "Creator");
      setUser(profile);
    } catch (err) {
      setUser(null);
      setWorkspaces([]);
      setCurrentWorkspace(null);
      setStoredAccessToken(null);
    }
  }, [currentWorkspace?.id]);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      try {
        let token = getStoredAccessToken();
        let meData: UserWithWorkspacesResponse | null = null;
        let activeWsId: string | undefined = undefined;

        if (token) {
          try {
            meData = await api.auth.getMe();
          } catch (err: any) {
            // If access token is expired or unauthorized, attempt token refresh via HttpOnly cookie
            if (
              err?.status === 401 ||
              err?.code === "AUTH_TOKEN_EXPIRED" ||
              err?.code === "AUTH_UNAUTHORIZED" ||
              err?.code === "UNAUTHORIZED"
            ) {
              try {
                const authData = await api.auth.refresh();
                if (authData?.tokens?.access_token) {
                  token = authData.tokens.access_token;
                  setStoredAccessToken(token);
                  activeWsId = authData.workspace?.id;
                  meData = await api.auth.getMe();
                }
              } catch {
                // Both access and refresh tokens failed
                token = null;
                setStoredAccessToken(null);
              }
            } else {
              token = null;
              setStoredAccessToken(null);
            }
          }
        } else {
          // No access token in storage: attempt to restore from HttpOnly refresh cookie
          try {
            const authData = await api.auth.refresh();
            if (authData?.tokens?.access_token) {
              token = authData.tokens.access_token;
              setStoredAccessToken(token);
              activeWsId = authData.workspace?.id;
              meData = await api.auth.getMe();
            }
          } catch {
            token = null;
          }
        }

        if (!isMounted) return;

        if (token && meData) {
          const wsList = meData.workspaces || [];
          setWorkspaces(wsList);

          const initialWs =
            wsList.find((w: WorkspaceSummary) => w.id === activeWsId) || wsList[0] || null;
          setCurrentWorkspace(initialWs);

          const profile = mapUserToProfile(
            meData.user,
            initialWs?.role || "Creator"
          );
          setUser(profile);
        } else {
          setUser(null);
          setCurrentWorkspace(null);
          setStoredAccessToken(null);
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setCurrentWorkspace(null);
          setStoredAccessToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
          setIsInitializing(false);
        }
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    if (!password) {
      throw new Error("Password is required.");
    }
    setIsLoading(true);
    try {
      const authResp = await api.auth.login({
        email,
        password,
      });

      setStoredAccessToken(authResp.tokens.access_token);

      const meResp = await api.auth.getMe();
      const wsList = meResp.workspaces || [];
      setWorkspaces(wsList);

      const activeWs =
        wsList.find((w) => w.id === authResp.workspace?.id) || wsList[0] || null;
      setCurrentWorkspace(activeWs);

      const profile = mapUserToProfile(
        meResp.user,
        activeWs?.role || authResp.workspace?.role || "Creator"
      );
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (email: string, password: string, name?: string) => {
    if (!password) {
      throw new Error("Password is required.");
    }
    setIsLoading(true);
    try {
      const displayName = name || email.split("@")[0] || "Creator";
      const authResp = await api.auth.signup({
        email,
        password,
        display_name: displayName,
      });

      setStoredAccessToken(authResp.tokens.access_token);

      const meResp = await api.auth.getMe();
      const wsList = meResp.workspaces || [];
      setWorkspaces(wsList);

      const activeWs =
        wsList.find((w) => w.id === authResp.workspace?.id) || wsList[0] || null;
      setCurrentWorkspace(activeWs);

      const profile = mapUserToProfile(
        meResp.user,
        activeWs?.role || authResp.workspace?.role || "Creator"
      );
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.auth.logout();
    } catch {
      // ignore network errors during logout
    } finally {
      setStoredAccessToken(null);
      setUser(null);
      setCurrentWorkspace(null);
      setWorkspaces([]);
      setIsLoading(false);
    }
  };

  const switchWorkspace = (workspaceId: string) => {
    const target = workspaces.find((w) => w.id === workspaceId);
    if (target) {
      setCurrentWorkspace(target);
      if (user) {
        setUser({
          ...user,
          role: target.role === "owner" ? "Workspace Owner" : "Content Creator",
        });
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        currentWorkspace,
        workspaces,
        isAuthenticated: !!user,
        isLoading,
        isInitializing,
        login,
        logout,
        signup,
        switchWorkspace,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
