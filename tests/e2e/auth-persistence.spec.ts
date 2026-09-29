import { test, expect } from "@playwright/test";

test.describe("HeyZen Authentication & Token Persistence E2E", () => {
  test("Complete Auth Flow: Login -> Home -> Reload -> Authenticated -> Home -> Logout -> Login Page", async ({ page }) => {
    const timestamp = Date.now();
    const testEmail = `persistence.test_${timestamp}@vidoai.com`;
    const testPassword = `HeyZenSecurePass${timestamp}!`;
    const testName = `Persistence Tester ${timestamp.toString().slice(-4)}`;

    // 1. Visit root URL '/'
    await page.goto("/");

    // If previously authenticated, log out first to start with a clean state
    try {
      const existingUserBtn = page.locator("#user-menu-btn").first();
      if (await existingUserBtn.isVisible({ timeout: 2000 })) {
        await existingUserBtn.click({ force: true });
        const existingLogout = page.locator("#user-logout-btn").first();
        if (await existingLogout.isVisible({ timeout: 2000 })) {
          await existingLogout.click();
          await page.waitForTimeout(500);
        }
      }
    } catch {
      // already unauthenticated
    }

    // Ensure we are on the Login page
    const emailInput = page.locator("#auth-email-input");
    await expect(emailInput).toBeVisible({ timeout: 15000 });

    // Switch to Sign Up mode to create a clean genuine test account in PostgreSQL
    const switchToSignupBtn = page.locator("#auth-switch-to-signup");
    await expect(switchToSignupBtn).toBeVisible({ timeout: 5000 });
    await switchToSignupBtn.click();

    // Fill in genuine registration credentials
    const nameInput = page.locator("#auth-name-input");
    await expect(nameInput).toBeVisible({ timeout: 5000 });
    await nameInput.fill(testName);
    await emailInput.fill(testEmail);

    const passwordInput = page.locator("#auth-password-input");
    await expect(passwordInput).toBeVisible({ timeout: 5000 });
    await passwordInput.fill(testPassword);

    // Submit registration (authenticates and starts genuine session)
    const submitBtn = page.locator("#auth-submit-btn");
    await submitBtn.click();

    // 2. Verify Home / Dashboard
    // Dashboard sidebar (aside) and Open Studio button should appear
    const aside = page.locator("aside").first();
    await expect(aside).toBeVisible({ timeout: 15000 });

    // Verify URL is '/' and NOT '/projects'
    const homeUrl = new URL(page.url());
    expect(homeUrl.pathname).toBe("/");
    expect(homeUrl.pathname).not.toBe("/projects");

    // Verify Home content is rendered (Open Studio button or welcome message)
    const openStudioBtn = page.locator("#open-studio-header-btn");
    await expect(openStudioBtn).toBeVisible({ timeout: 10000 });

    const userMenuBtn = page.locator("#user-menu-btn");
    await expect(userMenuBtn).toBeVisible({ timeout: 10000 });

    // Verify access token is preserved in localStorage under canonical key 'vidoai_token'
    const savedToken = await page.evaluate(() => localStorage.getItem("vidoai_token"));
    expect(savedToken).toBeDefined();
    expect(typeof savedToken).toBe("string");
    expect(savedToken!.length).toBeGreaterThan(20);

    // Verify refresh token is NOT stored in localStorage
    const savedRefreshToken = await page.evaluate(() => localStorage.getItem("heyzen_refresh_token") || localStorage.getItem("refresh_token"));
    expect(savedRefreshToken).toBeNull();

    // 3. Reload browser (simulates user hitting F5 / refresh)
    await page.reload();

    // 4. Verify user remains authenticated
    await expect(aside).toBeVisible({ timeout: 15000 });
    await expect(userMenuBtn).toBeVisible({ timeout: 10000 });

    // 5. Verify URL remains '/'
    const reloadedUrl = new URL(page.url());
    expect(reloadedUrl.pathname).toBe("/");
    expect(reloadedUrl.pathname).not.toBe("/projects");

    // 6. Verify Login page is NOT displayed
    await expect(page.locator("#auth-submit-btn")).not.toBeVisible();
    await expect(page.locator("#auth-email-input")).not.toBeVisible();

    // Verify authenticated session survives and can fetch data
    await expect(openStudioBtn).toBeVisible({ timeout: 10000 });

    // 7. Logout
    const logoutBtn = page.locator("#user-logout-btn");
    await userMenuBtn.click();
    try {
      await expect(logoutBtn).toBeVisible({ timeout: 3000 });
    } catch {
      await userMenuBtn.click({ force: true });
      await expect(logoutBtn).toBeVisible({ timeout: 5000 });
    }
    await logoutBtn.click();

    // 8. Verify Login page appears
    await expect(page.locator("#auth-submit-btn")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#auth-email-input")).toBeVisible({ timeout: 15000 });
    await expect(aside).not.toBeVisible();
    await expect(userMenuBtn).not.toBeVisible();

    // Verify storage is purged on logout
    const clearedToken = await page.evaluate(() => localStorage.getItem("vidoai_token"));
    expect(clearedToken).toBeNull();
  });
});
