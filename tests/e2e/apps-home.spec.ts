import { test, expect, Page } from "@playwright/test";

async function ensureLoggedIn(page: Page) {
  await page.goto("http://localhost:3000/");

  const dashboardIndicator = page
    .locator("button[title*='Apps'], #rail-nav-tools, button:has-text('Apps')")
    .first();
  const emailInput = page.locator("#auth-email-input, input[type='email']").first();

  try {
    await expect(dashboardIndicator).toBeVisible({ timeout: 8000 });
    return;
  } catch {
    // Not yet logged in, proceed with login form
  }

  await emailInput.waitFor({ state: "visible", timeout: 15000 });
  await emailInput.fill("dev@heyzen.ai");

  const passwordInput = page.locator("#auth-password-input, input[type='password']").first();
  await passwordInput.fill("DevPassword123!");

  const submitBtn = page.locator("#auth-submit-btn, button[type='submit']").first();
  await submitBtn.click();

  await expect(dashboardIndicator).toBeVisible({ timeout: 15000 });
}

async function navigateToAppsHome(page: Page) {
  await ensureLoggedIn(page);

  // Click Apps on rail navigation
  const toolsRailBtn = page.locator("#rail-nav-tools, button[title*='Apps']").first();
  await expect(toolsRailBtn).toBeVisible({ timeout: 10000 });
  await toolsRailBtn.click();
  await page.waitForTimeout(400);

  // If on another apps sub-section, ensure Home is selected
  const homeBtn = page.locator("#apps-sidebar-nav-home").first();
  if (await homeBtn.isVisible()) {
    await homeBtn.click();
    await page.waitForTimeout(300);
  }

  // Verify page title
  const heading = page.locator("#apps-page-title").first();
  await expect(heading).toBeVisible({ timeout: 10000 });
}

test.describe("Apps → Home Tab Production E2E Suite", () => {
  test("Complete End-to-End Validation: Navigation, Registry, Search, Tabs, Recents, and Themes", async ({
    page,
  }) => {
    // 1. Login / session is restored and Apps → Home opens
    await navigateToAppsHome(page);

    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text();
        if (
          !text.includes("favicon") &&
          !text.includes("WebSocket") &&
          !text.includes("401") &&
          !text.includes("404") &&
          !text.includes("net::ERR")
        ) {
          consoleErrors.push(text);
        }
      }
    });

    // 2. Verify Page Title
    const title = page.locator("#apps-page-title").first();
    await expect(title).toBeVisible();
    await expect(title).toHaveText("App Library");

    // 3. Verify Featured Prompt to Video is visible
    const heroCard = page.locator("#apps-hero-card");
    await expect(heroCard).toBeVisible();
    await expect(heroCard).toContainText("Prompt to Video");
    await expect(heroCard).toContainText("Featured Creation Engine");

    // 4. Verify category tabs are visible and working
    const tabAll = page.locator("#apps-tab-all");
    const tabCreate = page.locator("#apps-tab-create");
    const tabEnhance = page.locator("#apps-tab-enhance");
    const tabEdit = page.locator("#apps-tab-edit");
    const tabInteractive = page.locator("#apps-tab-interactive");

    await expect(tabAll).toBeVisible();
    await expect(tabCreate).toBeVisible();
    await expect(tabEnhance).toBeVisible();
    await expect(tabEdit).toBeVisible();
    await expect(tabInteractive).toBeVisible();

    // Verify all apps rendered in All Apps tab
    const appsGrid = page.locator("#apps-grid");
    await expect(appsGrid).toBeVisible();
    const initialCardsCount = await page.locator('[data-testid^="app-card-"]').count();
    expect(initialCardsCount).toBeGreaterThanOrEqual(10);

    // 5. Test Create tab filters apps
    await tabCreate.click();
    await page.waitForTimeout(250);
    const createCards = page.locator('[data-testid^="app-card-"]');
    const createCount = await createCards.count();
    expect(createCount).toBeGreaterThan(0);
    expect(createCount).toBeLessThan(initialCardsCount);
    await expect(page.locator("#app-card-app_video_agent")).toBeVisible();
    await expect(page.locator("#app-card-app_translate")).toHaveCount(0);

    // 6. Test Enhance tab filters apps
    await tabEnhance.click();
    await page.waitForTimeout(250);
    const enhanceCards = page.locator('[data-testid^="app-card-"]');
    const enhanceCount = await enhanceCards.count();
    expect(enhanceCount).toBeGreaterThan(0);
    await expect(page.locator("#app-card-app_speech")).toBeVisible();
    await expect(page.locator("#app-card-app_video_agent")).toHaveCount(0);

    // 7. Test Edit tab filters apps
    await tabEdit.click();
    await page.waitForTimeout(250);
    const editCards = page.locator('[data-testid^="app-card-"]');
    const editCount = await editCards.count();
    expect(editCount).toBeGreaterThan(0);
    await expect(page.locator("#app-card-app_translate")).toBeVisible();
    await expect(page.locator("#app-card-app_speech")).toHaveCount(0);

    // 8. Test Interactive tab filters apps
    await tabInteractive.click();
    await page.waitForTimeout(250);
    const interactiveCards = page.locator('[data-testid^="app-card-"]');
    const interactiveCount = await interactiveCards.count();
    expect(interactiveCount).toBeGreaterThan(0);
    await expect(page.locator("#app-card-app_interactive")).toBeVisible();

    // Switch back to All Apps
    await tabAll.click();
    await page.waitForTimeout(250);
    expect(await page.locator('[data-testid^="app-card-"]').count()).toBe(initialCardsCount);

    // 9. Test Search functionality (instant filtering)
    const searchInput = page.locator("#apps-search-input");
    await expect(searchInput).toBeVisible();

    await searchInput.fill("Podcast");
    await page.waitForTimeout(300);
    await expect(page.locator("#app-card-app_podcast")).toBeVisible();
    expect(await page.locator('[data-testid^="app-card-"]').count()).toBe(1);

    // 10. Test Search empty state
    await searchInput.fill("NonExistentTermXYZ9999");
    await page.waitForTimeout(300);
    const emptyState = page.locator("#apps-search-empty-state");
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toContainText("No apps found");

    // 11. Test Clear search restores results
    const clearBtn = page.locator("#apps-empty-clear-btn, #apps-clear-search-btn").first();
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();
    await page.waitForTimeout(300);
    expect(await page.locator('[data-testid^="app-card-"]').count()).toBe(initialCardsCount);

    // 12. Verify Recents Sidebar
    const recentsSection = page.locator("#apps-sidebar-recents");
    await expect(recentsSection).toBeVisible();

    const hasRecents =
      (await page.locator('[data-testid^="recent-project-card-"]').count()) > 0 ||
      (await page.locator('[data-testid="apps-recents-empty"]').isVisible()) ||
      (await page.locator('[data-testid="apps-recents-loading"]').isVisible());
    expect(hasRecents).toBe(true);

    // 13. Test "See all ›" opens Projects
    const seeAllBtn = page.locator("#apps-recents-see-all-btn");
    await expect(seeAllBtn).toBeVisible();
    await seeAllBtn.click();
    await page.waitForTimeout(500);

    // Verify Projects view loaded
    const projectsView = page.getByText(/Projects/i).first();
    await expect(projectsView).toBeVisible({ timeout: 10000 });

    // Navigate back to Apps Home
    await navigateToAppsHome(page);

    // 14. Test "Try Video Agent" opens REAL Video Agent workspace
    const tryAgentBtn = page.locator("#try-video-agent-hero-btn");
    await expect(tryAgentBtn).toBeVisible();
    await tryAgentBtn.click();
    await page.waitForTimeout(800);

    // Verify Video Agent workspace is visible
    const agentIndicator = page.locator("text='Video Agent'").first();
    await expect(agentIndicator).toBeVisible({ timeout: 10000 });

    // Navigate back to Apps Home
    await navigateToAppsHome(page);

    // 15. Test Real App Card opens actual workflow (e.g. Translate Videos)
    const translateCard = page.locator("#featured-app-translate, #app-card-app_translate").first();
    await expect(translateCard).toBeVisible();
    await translateCard.click();
    await page.waitForTimeout(800);

    // Verify Translate Videos view opened
    const translateHeading = page.locator("h1").filter({ hasText: /Translate/i }).first();
    await expect(translateHeading).toBeVisible({ timeout: 10000 });

    // Navigate back to Apps Home
    await navigateToAppsHome(page);

    // 16. Verify No Horizontal Overflow
    const horizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 3;
    });
    expect(horizontalOverflow).toBe(false);

    // 17. Verify Dark and Light Theme Support
    const themeToggleBtn = page.locator("#global-theme-toggle-btn");
    if (await themeToggleBtn.isVisible()) {
      await themeToggleBtn.click();
      await page.waitForTimeout(300);
      await expect(title).toBeVisible();

      await themeToggleBtn.click();
      await page.waitForTimeout(300);
      await expect(title).toBeVisible();
    }

    // 18. Verify no fatal console errors occurred
    expect(consoleErrors.length).toBe(0);
  });
});
