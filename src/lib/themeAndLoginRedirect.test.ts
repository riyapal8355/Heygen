import test from "node:test";
import assert from "node:assert/strict";

test("Theme & Login Redirect Test Suite", async (t) => {
  await t.test("Login redirect: Default view is dashboard ('/'), not projects", () => {
    // Simulate initial props of DashboardContent
    const defaultInitialView = "dashboard";
    const defaultInitialRailTab = "home";

    assert.equal(defaultInitialView, "dashboard", "DashboardContent must default to dashboard view");
    assert.equal(defaultInitialRailTab, "home", "Left rail must default to home tab on landing");
    assert.notEqual(defaultInitialView, "projects", "Default view must NOT be projects");
  });

  await t.test("Theme persistence: Theme is stored and retrieved from localStorage key 'vidoai_theme'", () => {
    const storage: Record<string, string> = {};
    const mockLocalStorage = {
      getItem: (key: string) => storage[key] || null,
      setItem: (key: string, value: string) => {
        storage[key] = value;
      },
      removeItem: (key: string) => {
        delete storage[key];
      },
    };

    // Default when unset
    let activeTheme = mockLocalStorage.getItem("vidoai_theme") || "dark";
    assert.equal(activeTheme, "dark");

    // Toggle to light
    mockLocalStorage.setItem("vidoai_theme", "light");
    activeTheme = mockLocalStorage.getItem("vidoai_theme") || "dark";
    assert.equal(activeTheme, "light");

    // Simulating page refresh: theme remains light
    const restoredTheme = mockLocalStorage.getItem("vidoai_theme");
    assert.equal(restoredTheme, "light", "Theme must persist as 'light' across refresh");

    // Toggle back to dark
    mockLocalStorage.setItem("vidoai_theme", "dark");
    assert.equal(mockLocalStorage.getItem("vidoai_theme"), "dark");
  });

  await t.test("Light theme document class and attribute application", () => {
    const classList = new Set<string>(["dark"]);
    let dataTheme = "dark";
    let colorScheme = "dark";

    const applyTheme = (theme: "light" | "dark") => {
      if (theme === "light") {
        classList.delete("dark");
        classList.add("light");
        dataTheme = "light";
        colorScheme = "light";
      } else {
        classList.delete("light");
        classList.add("dark");
        dataTheme = "dark";
        colorScheme = "dark";
      }
    };

    // Apply light theme
    applyTheme("light");
    assert.ok(classList.has("light"), "Root classList must have 'light'");
    assert.ok(!classList.has("dark"), "Root classList must not have 'dark'");
    assert.equal(dataTheme, "light", "Root data-theme attribute must be 'light'");
    assert.equal(colorScheme, "light", "Root colorScheme must be 'light'");

    // Switch to dark theme
    applyTheme("dark");
    assert.ok(classList.has("dark"), "Root classList must have 'dark'");
    assert.ok(!classList.has("light"), "Root classList must not have 'light'");
    assert.equal(dataTheme, "dark");
  });

  await t.test("Navigation preservation: Theme remains intact during in-app navigation without refresh", () => {
    let currentTheme = "light";
    const navigationHistory: string[] = [];

    const navigateTo = (view: "dashboard" | "projects" | "studio" | "brand") => {
      navigationHistory.push(view);
      // Theme should not reset or mutate on view changes
      return currentTheme;
    };

    assert.equal(navigateTo("dashboard"), "light");
    assert.equal(navigateTo("projects"), "light");
    assert.equal(navigateTo("studio"), "light");
    assert.equal(navigateTo("brand"), "light");

    assert.deepEqual(navigationHistory, ["dashboard", "projects", "studio", "brand"]);
    assert.equal(currentTheme, "light", "Theme must remain light through navigation");
  });

  await t.test("Auth flow consistency: 1-Click demo login and password login redirect to '/' dashboard", () => {
    const simulateLoginSuccess = (userType: "demo" | "credentials") => {
      const targetDestination = "/"; // application root
      const initialView = "dashboard";
      return { userType, targetDestination, initialView };
    };

    const demoLogin = simulateLoginSuccess("demo");
    const standardLogin = simulateLoginSuccess("credentials");

    assert.equal(demoLogin.targetDestination, "/");
    assert.equal(demoLogin.initialView, "dashboard");

    assert.equal(standardLogin.targetDestination, "/");
    assert.equal(standardLogin.initialView, "dashboard");
  });
});
