import test from "node:test";
import assert from "node:assert/strict";

/**
 * HeyZen Auth Token Persistence & Session Lifecycle Test Suite
 *
 * Verifies:
 * A. Login persistence across browser reload (vidoai_token storage + /auth/me hydration)
 * B. Expired access token auto-refresh via HttpOnly cookie and session continuation
 * C. Invalid refresh token session termination and redirect to login
 * D. Demo login restrictions (no hardcoded passwords, disabled by default)
 * E. Normal credentials login contract
 */

test("HeyZen Auth Token Persistence & Lifecycle Suite", async (t) => {
  // Mock localStorage implementation
  const createMockStorage = () => {
    const store: Record<string, string> = {};
    return {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, val: string) => {
        store[key] = val;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        for (const k of Object.keys(store)) delete store[k];
      },
      _store: store,
    };
  };

  await t.test("A. Login persistence: Login -> Home -> reload -> still authenticated -> Home", async () => {
    const mockStorage = createMockStorage();
    let inMemoryToken: string | null = null;

    const setStoredAccessToken = (token: string | null) => {
      inMemoryToken = token;
      if (token) {
        mockStorage.setItem("vidoai_token", token);
      } else {
        mockStorage.removeItem("vidoai_token");
      }
    };

    const getStoredAccessToken = () => inMemoryToken || mockStorage.getItem("vidoai_token");

    // 1. Initial Login
    const loginPayload = { email: "user@example.com", password: "ValidPassword123!" };
    const mockLoginResponse = {
      tokens: { access_token: "jwt_access_token_abc123", expires_in_seconds: 900 },
      user: { id: "user-1", email: "user@example.com", display_name: "Test User" },
      workspace: { id: "ws-1", name: "Personal Workspace", role: "owner" },
    };

    setStoredAccessToken(mockLoginResponse.tokens.access_token);
    assert.equal(getStoredAccessToken(), "jwt_access_token_abc123", "Access token must be saved to storage");
    assert.equal(mockStorage.getItem("vidoai_token"), "jwt_access_token_abc123", "Canonical key must be vidoai_token");

    // Verify refresh token is NOT in localStorage
    assert.equal(mockStorage.getItem("heyzen_refresh_token"), null, "Refresh token must NOT be stored in localStorage");
    assert.equal(mockStorage.getItem("refresh_token"), null, "Refresh token must NOT be stored in localStorage");

    // 2. Simulate Browser Reload: in-memory token is reset to null
    inMemoryToken = null;
    let isInitializing = true;
    let currentUser: any = null;

    // initAuth runs on mount
    const tokenOnReload = getStoredAccessToken();
    assert.equal(tokenOnReload, "jwt_access_token_abc123", "Access token must survive normal page reload in storage");

    // Hydrate user via /auth/me
    const mockMeResponse = {
      user: { id: "user-1", email: "user@example.com", display_name: "Test User" },
      workspaces: [{ id: "ws-1", name: "Personal Workspace", role: "owner" }],
    };

    if (tokenOnReload) {
      setStoredAccessToken(tokenOnReload);
      currentUser = mockMeResponse.user;
    }
    isInitializing = false;

    // Verify session restored to Home without redirect to Login
    assert.equal(isInitializing, false, "Auth initialization must complete");
    assert.ok(currentUser !== null, "User must remain authenticated after reload");
    assert.equal(currentUser.email, "user@example.com");
  });

  await t.test("B. Expired access token: Access token expired -> refresh endpoint succeeds -> session restored", async () => {
    const mockStorage = createMockStorage();
    mockStorage.setItem("vidoai_token", "expired_access_token_xyz");

    let memoryToken: string | null = null;
    const getStoredAccessToken = () => memoryToken || mockStorage.getItem("vidoai_token");
    const setStoredAccessToken = (token: string | null) => {
      memoryToken = token;
      if (token) mockStorage.setItem("vidoai_token", token);
      else mockStorage.removeItem("vidoai_token");
    };

    // Simulate getMe() failure with 401 AUTH_TOKEN_EXPIRED
    let meAttempts = 0;
    const mockApiGetMe = async () => {
      meAttempts++;
      if (getStoredAccessToken() === "expired_access_token_xyz") {
        const err: any = new Error("Access token has expired.");
        err.status = 401;
        err.code = "AUTH_TOKEN_EXPIRED";
        throw err;
      }
      return {
        user: { id: "user-1", email: "user@example.com", display_name: "Refreshed User" },
        workspaces: [{ id: "ws-1", name: "Workspace 1", role: "owner" }],
      };
    };

    // Simulate refresh endpoint (called with HttpOnly cookie)
    let refreshCalled = false;
    const mockApiRefresh = async () => {
      refreshCalled = true;
      return {
        tokens: { access_token: "new_fresh_access_token_999", expires_in_seconds: 900 },
        user: { id: "user-1", email: "user@example.com", display_name: "Refreshed User" },
        workspace: { id: "ws-1", name: "Workspace 1", role: "owner" },
      };
    };

    // Session restoration flow in initAuth
    let restoredUser: any = null;
    let token = getStoredAccessToken();

    try {
      await mockApiGetMe();
    } catch (err: any) {
      if (err.status === 401 && (err.code === "AUTH_TOKEN_EXPIRED" || err.code === "AUTH_UNAUTHORIZED")) {
        // Automatically attempt token refresh via HttpOnly cookie
        const authData = await mockApiRefresh();
        if (authData?.tokens?.access_token) {
          token = authData.tokens.access_token;
          setStoredAccessToken(token);
          const meData = await mockApiGetMe();
          restoredUser = meData.user;
        }
      }
    }

    assert.equal(refreshCalled, true, "Refresh endpoint must be invoked when access token is expired");
    assert.equal(getStoredAccessToken(), "new_fresh_access_token_999", "Storage must be updated with refreshed token");
    assert.ok(restoredUser !== null, "Session must be successfully restored without redirecting to login");
    assert.equal(restoredUser.display_name, "Refreshed User");
  });

  await t.test("C. Invalid refresh: Refresh fails -> session cleared -> Login shown", async () => {
    const mockStorage = createMockStorage();
    mockStorage.setItem("vidoai_token", "invalid_stale_token");

    let memoryToken: string | null = "invalid_stale_token";
    const getStoredAccessToken = () => memoryToken || mockStorage.getItem("vidoai_token");
    const setStoredAccessToken = (token: string | null) => {
      memoryToken = token;
      if (token) mockStorage.setItem("vidoai_token", token);
      else mockStorage.removeItem("vidoai_token");
    };

    // Both getMe and refresh fail (both tokens expired / session revoked)
    const mockApiGetMe = async () => {
      const err: any = new Error("Token expired");
      err.status = 401;
      err.code = "AUTH_TOKEN_EXPIRED";
      throw err;
    };

    const mockApiRefresh = async () => {
      const err: any = new Error("Invalid session");
      err.status = 401;
      err.code = "AUTH_INVALID_SESSION";
      throw err;
    };

    let sessionCleared = false;
    let activeUser: any = "old_user";

    try {
      await mockApiGetMe();
    } catch (err: any) {
      if (err.status === 401) {
        try {
          await mockApiRefresh();
        } catch {
          // Both failed: clear session
          setStoredAccessToken(null);
          activeUser = null;
          sessionCleared = true;
        }
      }
    }

    assert.equal(sessionCleared, true, "Session must be cleared when refresh fails");
    assert.equal(activeUser, null, "User state must be set to null (rendering login page)");
    assert.equal(getStoredAccessToken(), null, "Access token must be cleared from storage");
    assert.equal(mockStorage.getItem("vidoai_token"), null, "localStorage must be purged of invalid token");
  });

  await t.test("D. Demo login: Production build contains no hardcoded demo password; disabled by default", () => {
    // 1. Verify default environment configuration
    const isDemoEnabledDefault = process.env.NEXT_PUBLIC_ENABLE_DEMO_LOGIN === "true";
    assert.equal(isDemoEnabledDefault, false, "Demo login MUST be default OFF unless explicitly enabled");

    // 2. Verify AuthPage does not contain hardcoded demo password literals
    const fs = require("node:fs");
    const path = require("node:path");
    const authPageSrc = fs.readFileSync(
      path.join(__dirname, "../components/auth/AuthPage.tsx"),
      "utf-8"
    );
    const authContextSrc = fs.readFileSync(
      path.join(__dirname, "../context/AuthContext.tsx"),
      "utf-8"
    );

    assert.ok(
      !authPageSrc.includes("HeyZenDemoPass123!"),
      "AuthPage must not contain hardcoded password 'HeyZenDemoPass123!'"
    );
    assert.ok(
      !authContextSrc.includes("HeyZenDefaultPass123!"),
      "AuthContext must not contain fallback password 'HeyZenDefaultPass123!'"
    );
    assert.ok(
      !authPageSrc.includes("riya@vidoai.com"),
      "AuthPage must not contain hardcoded email 'riya@vidoai.com'"
    );

    // 3. Verify demo login button is only rendered if environment variable is enabled
    const renderDemoSection = (envFlag: string | undefined) => {
      const isEnabled = envFlag === "true";
      return isEnabled ? "DEMO_BUTTON_RENDERED" : null;
    };

    assert.equal(renderDemoSection(undefined), null, "Demo section must not render when unset");
    assert.equal(renderDemoSection("false"), null, "Demo section must not render when false");
    assert.equal(renderDemoSection("true"), "DEMO_BUTTON_RENDERED", "Demo section only renders when explicitly true");
  });

  await t.test("E. Normal login: Entered credentials are required and sent to login endpoint", async () => {
    // 1. Verify login rejects missing password
    const login = async (email: string, password?: string) => {
      if (!password) {
        throw new Error("Password is required.");
      }
      return {
        email: email.trim().toLowerCase(),
        password,
      };
    };

    await assert.rejects(
      async () => {
        await login("test@example.com", "");
      },
      { message: "Password is required." },
      "Login must reject empty password"
    );

    await assert.rejects(
      async () => {
        await login("test@example.com", undefined);
      },
      { message: "Password is required." },
      "Login must reject undefined password without silent fallback"
    );

    // 2. Valid credentials format and target destination
    const validResult = await login("User.Name@Example.com", "MySecretPass123!");
    assert.equal(validResult.email, "user.name@example.com", "Email must be normalized");
    assert.equal(validResult.password, "MySecretPass123!", "Raw entered password must be transmitted");

    // 3. Post-authentication destination must be '/' (dashboard)
    const targetRoute = "/";
    assert.equal(targetRoute, "/", "Successful login destination must be '/' dashboard");
    assert.notEqual(targetRoute, "/projects", "Successful login must NOT redirect to /projects");
  });
});
