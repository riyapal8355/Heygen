import { test, expect, Page } from "@playwright/test";

async function ensureLoggedIn(page: Page) {
  await page.goto("/");
  const aside = page.locator("aside").first();
  try {
    if (await aside.isVisible({ timeout: 2000 })) return;
  } catch {
    // continue to login
  }

  const emailInput = page.locator("#auth-email-input, input[type='email']").first();
  await emailInput.waitFor({ state: "visible", timeout: 15000 });
  await emailInput.fill("dev@heyzen.ai");

  const passwordInput = page.locator("#auth-password-input, input[type='password']").first();
  await passwordInput.fill("DevPassword123!");

  const submitBtn = page.locator("#auth-submit-btn, button[type='submit']").first();
  await submitBtn.click();

  await aside.waitFor({ state: "visible", timeout: 15000 });
}

test.describe("HeyZen Frontend Smoke Tests", () => {
  test("1. Frontend loads successfully", async ({ page }) => {
    // Open http://127.0.0.1:3000 as required by smoke specification
    await page.goto("http://127.0.0.1:3000");
    const title = await page.title();
    expect(title).toBeDefined();
    expect(title.length).toBeGreaterThan(0);

    const body = page.locator("body");
    await expect(body).toBeVisible();
  });

  test("2. Brand Systems opens", async ({ page }) => {
    await ensureLoggedIn(page);

    // Click Brand Systems in rail nav
    const brandButton = page.locator('button[title="Brand Systems"]');
    await expect(brandButton).toBeVisible({ timeout: 10000 });
    await brandButton.click();

    // Verify Brand Systems content appears
    const brandHeading = page.getByRole("heading", { name: /Brand Systems/i }).first();
    await expect(brandHeading).toBeVisible({ timeout: 10000 });
  });

  test("3. Projects opens", async ({ page }) => {
    await ensureLoggedIn(page);

    // Click Projects in rail nav
    const projectsButton = page.locator('button[title="Projects"]');
    await expect(projectsButton).toBeVisible({ timeout: 10000 });
    await projectsButton.click();

    // Verify Projects view appears
    const projectsView = page.getByText(/Projects/i).first();
    await expect(projectsView).toBeVisible({ timeout: 10000 });
  });

  test("4. AI Agent opens with flexible duration selector", async ({ page }) => {
    await ensureLoggedIn(page);

    // Navigate to Home / Video Agent
    const homeButton = page.locator('button[title="Home / Dashboard"]');
    if (await homeButton.isVisible()) {
      await homeButton.click();
    }

    // Click Video Agent in sidebar
    const videoAgentButton = page.getByRole("button", { name: /Video agent/i }).first();
    await expect(videoAgentButton).toBeVisible({ timeout: 10000 });
    await videoAgentButton.click();

    // Verify AI Agent composer and duration selector button are visible
    const composer = page.locator("#video-agent-prompt-composer");
    await expect(composer).toBeVisible({ timeout: 15000 });

    const durationBtn = page.locator("#duration-selector-btn");
    await expect(durationBtn).toBeVisible({ timeout: 10000 });

    // Open duration dropdown menu
    await durationBtn.click();
    const dropdown = page.locator("#duration-dropdown-menu");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Verify required preset buttons are rendered
    await expect(page.locator("#duration-preset-15")).toBeVisible();
    await expect(page.locator("#duration-preset-30")).toBeVisible();
    await expect(page.locator("#duration-preset-60")).toBeVisible();
    await expect(page.locator("#duration-preset-90")).toBeVisible();
    await expect(page.locator("#duration-preset-120")).toBeVisible();
    await expect(page.locator("#duration-preset-300")).toBeVisible();
    await expect(page.locator("#duration-preset-600")).toBeVisible();
    await expect(page.locator("#duration-preset-custom")).toBeVisible();
  });

  test("5. Studio opens, Generate button is actionable, and sections resize dynamically", async ({ page }) => {
    await ensureLoggedIn(page);

    // If not already on Home, switch to Home via Left Rail
    const homeRailBtn = page.locator('button[title="Home / Dashboard"]');
    if (await homeRailBtn.isVisible()) {
      await homeRailBtn.click();
    }

    // Open Studio via the header button or direct project navigation
    const openStudioBtn = page.locator("#open-studio-header-btn");
    await expect(openStudioBtn).toBeVisible({ timeout: 10000 });
    await openStudioBtn.click();

    // Verify Studio is opened
    const studioSidebar = page.locator("#studio-left-sidebar");
    await expect(studioSidebar).toBeVisible({ timeout: 15000 });

    const studioTitle = page.getByText(/HeyZen Studio/i).first();
    await expect(studioTitle).toBeVisible({ timeout: 10000 });

    // b. Finds Generate
    const generateBtn = page.locator("#studio-generate-btn");
    await expect(generateBtn).toBeVisible({ timeout: 10000 });

    // c. Verifies it is actionable
    await expect(generateBtn).toBeEnabled();

    // d. Exercises the resize handle
    const initialBox = await studioSidebar.boundingBox();
    expect(initialBox).not.toBeNull();
    const initialWidth = initialBox!.width;

    const leftHandle = page.locator("#resize-handle-left-sidebar");
    await expect(leftHandle).toBeVisible();

    const handleBox = await leftHandle.boundingBox();
    expect(handleBox).not.toBeNull();

    // Drag handle to the right
    await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2);
    await page.mouse.down();
    await page.mouse.move(handleBox!.x + handleBox!.width / 2 + 60, handleBox!.y + handleBox!.height / 2, { steps: 5 });
    await page.mouse.up();

    // e. Verifies the section dimensions actually change
    const newBox = await studioSidebar.boundingBox();
    expect(newBox).not.toBeNull();
    expect(newBox!.width).toBeGreaterThan(initialWidth + 15);

    // Also verify bottom timeline resize handle
    const timeline = page.locator("#studio-bottom-timeline");
    await expect(timeline).toBeVisible();
    const initialTimelineBox = await timeline.boundingBox();
    expect(initialTimelineBox).not.toBeNull();

    const timelineHandle = page.locator("#resize-handle-timeline");
    await expect(timelineHandle).toBeVisible();
    const timelineHandleBox = await timelineHandle.boundingBox();
    expect(timelineHandleBox).not.toBeNull();

    // Drag timeline handle upwards
    await page.mouse.move(timelineHandleBox!.x + timelineHandleBox!.width / 2, timelineHandleBox!.y + timelineHandleBox!.height / 2);
    await page.mouse.down();
    await page.mouse.move(timelineHandleBox!.x + timelineHandleBox!.width / 2, timelineHandleBox!.y + timelineHandleBox!.height / 2 - 50, { steps: 5 });
    await page.mouse.up();

    const newTimelineBox = await timeline.boundingBox();
    expect(newTimelineBox).not.toBeNull();
    expect(newTimelineBox!.height).toBeGreaterThan(initialTimelineBox!.height + 15);

    // Also verify right inspector resize handle
    const inspector = page.locator("#studio-right-inspector");
    await expect(inspector).toBeVisible();
    const initialInspectorBox = await inspector.boundingBox();
    expect(initialInspectorBox).not.toBeNull();

    const rightHandle = page.locator("#resize-handle-right-inspector");
    await expect(rightHandle).toBeVisible();
    const rightHandleBox = await rightHandle.boundingBox();
    expect(rightHandleBox).not.toBeNull();

    // Drag right handle to the left to expand inspector
    await page.mouse.move(rightHandleBox!.x + rightHandleBox!.width / 2, rightHandleBox!.y + rightHandleBox!.height / 2);
    await page.mouse.down();
    await page.mouse.move(rightHandleBox!.x + rightHandleBox!.width / 2 - 50, rightHandleBox!.y + rightHandleBox!.height / 2, { steps: 5 });
    await page.mouse.up();

    const newInspectorBox = await inspector.boundingBox();
    expect(newInspectorBox).not.toBeNull();
    expect(newInspectorBox!.width).toBeGreaterThan(initialInspectorBox!.width + 15);

    // Verify Generate button interaction reaches the real render pipeline without producing revision conflict
    await generateBtn.click();
    await page.waitForTimeout(1000);

    // Verify Generate does NOT produce a revision conflict error
    await expect(page.locator("text=/Revision conflict/i")).not.toBeVisible();

    const generateBtnText = await page.locator("#studio-generate-btn").first().innerText();
    expect(generateBtnText).toBeDefined();

    // f. Studio Fullscreen API integration: enter fullscreen, exit on Esc, re-enter, exit on second click
    const fullscreenBtn = page.locator("#studio-fullscreen-btn");
    await expect(fullscreenBtn).toBeVisible({ timeout: 10000 });
    await expect(fullscreenBtn).toHaveAttribute("title", "Enter Fullscreen");

    // Click to enter fullscreen
    await fullscreenBtn.click();
    await page.waitForTimeout(300);

    const isFullscreenActive = await page.evaluate(() => {
      const el = document.fullscreenElement || (document as any).webkitFullscreenElement;
      return Boolean(el && (el.id === "vido-studio-container" || el.contains(document.getElementById("studio-fullscreen-btn"))));
    });
    expect(isFullscreenActive).toBe(true);
    await expect(fullscreenBtn).toHaveAttribute("title", "Exit Fullscreen");

    // Exit on browser Esc
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);

    const isFullscreenAfterEsc = await page.evaluate(() => {
      return Boolean(document.fullscreenElement || (document as any).webkitFullscreenElement);
    });
    expect(isFullscreenAfterEsc).toBe(false);
    await expect(fullscreenBtn).toHaveAttribute("title", "Enter Fullscreen");

    // Click again to re-enter
    await fullscreenBtn.click();
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => Boolean(document.fullscreenElement || (document as any).webkitFullscreenElement))).toBe(true);

    // Second click exits fullscreen
    await fullscreenBtn.click();
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => Boolean(document.fullscreenElement || (document as any).webkitFullscreenElement))).toBe(false);
    await expect(fullscreenBtn).toHaveAttribute("title", "Enter Fullscreen");
  });

  test("6. Login redirects to '/', light theme applies across all views, and persists after refresh", async ({ page }) => {
    // 1. Visit root page
    await page.goto("/");

    // Wait for either the dashboard (if session persisted) or the login page
    const loginOrDashboard = page.locator("#auth-email-input, aside").first();
    await loginOrDashboard.waitFor({ state: "visible", timeout: 15000 });

    // If currently logged in, log out first to verify fresh login flow
    const aside = page.locator("aside").first();
    if (await aside.isVisible()) {
      const userMenuBtn = page.locator("#user-menu-btn").first();
      await userMenuBtn.click();
      const logoutBtn = page.locator("#user-logout-btn, button:has-text('Sign Out'), button:has-text('Log Out')").first();
      await expect(logoutBtn).toBeVisible({ timeout: 5000 });
      await logoutBtn.click();
      await page.waitForTimeout(500);
    }

    // Perform Login with valid test credentials
    const emailInput = page.locator("#auth-email-input, input[type='email']").first();
    await emailInput.waitFor({ state: "visible", timeout: 15000 });
    await emailInput.fill("dev@heyzen.ai");

    const passwordInput = page.locator("#auth-password-input, input[type='password']").first();
    await passwordInput.fill("DevPassword123!");

    const submitBtn = page.locator("#auth-submit-btn, button[type='submit']").first();
    await submitBtn.click();

    // 1. Login -> URL is '/' and not '/projects'
    await page.waitForSelector("aside", { timeout: 15000 });
    const currentUrl = new URL(page.url());
    expect(currentUrl.pathname).toBe("/");
    expect(currentUrl.pathname).not.toBe("/projects");

    // Confirm Dashboard view is active by default (not projects)
    const openStudioBtn = page.locator("#open-studio-header-btn");
    await expect(openStudioBtn).toBeVisible({ timeout: 10000 });

    // 2. Toggle light mode
    const themeToggleBtn = page.locator("#global-theme-toggle-btn");
    await expect(themeToggleBtn).toBeVisible({ timeout: 10000 });

    const html = page.locator("html");
    const classAttr = await html.getAttribute("class");
    if (!classAttr?.includes("light")) {
      await themeToggleBtn.click();
    }

    // Confirm light theme class on html tag
    await expect(html).toHaveClass(/light/);
    await expect(html).toHaveAttribute("data-theme", "light");

    // 3. Navigate Dashboard -> Projects
    const projectsNav = page.locator("#rail-nav-projects");
    await expect(projectsNav).toBeVisible({ timeout: 10000 });
    await projectsNav.click();
    await page.waitForTimeout(500);

    // 4. Confirm light theme remains applied in Projects
    await expect(html).toHaveClass(/light/);
    await expect(page.getByText(/Projects/i).first()).toBeVisible({ timeout: 10000 });

    // Navigate Projects -> Studio
    const homeNav = page.locator("#rail-nav-home");
    await expect(homeNav).toBeVisible({ timeout: 10000 });
    await homeNav.click();
    await page.waitForTimeout(500);
    await expect(openStudioBtn).toBeVisible({ timeout: 10000 });
    await openStudioBtn.click();

    // Confirm light theme remains applied in Studio
    const studioSidebar = page.locator("#studio-left-sidebar");
    await expect(studioSidebar).toBeVisible({ timeout: 15000 });
    await expect(html).toHaveClass(/light/);

    // Navigate Studio -> Return to Dashboard -> Brand Systems
    const backBtn = page.locator("#back-to-dashboard-btn, button:has-text('Dashboard')").first();
    await expect(backBtn).toBeVisible({ timeout: 10000 });
    await backBtn.click();
    await page.waitForTimeout(500);

    const brandNav = page.locator("#rail-nav-brand");
    await expect(brandNav).toBeVisible({ timeout: 10000 });
    await brandNav.click();
    await page.waitForTimeout(500);

    // Confirm light theme remains applied in Brand Systems
    const brandHeading = page.getByRole("heading", { name: /Brand Systems/i }).first();
    await expect(brandHeading).toBeVisible({ timeout: 10000 });
    await expect(html).toHaveClass(/light/);

    // 5. Refresh and confirm light theme persists
    await page.reload();
    await page.waitForSelector("aside", { timeout: 15000 });
    await expect(html).toHaveClass(/light/);
    await expect(html).toHaveAttribute("data-theme", "light");

    const savedTheme = await page.evaluate(() => localStorage.getItem("vidoai_theme"));
    expect(savedTheme).toBe("light");
  });
});

