import { test, expect, Page } from "@playwright/test";

async function ensureLoggedIn(page: Page) {
  await page.goto("http://localhost:3000/");
  const aside = page.locator("aside").first();
  try {
    if (await aside.isVisible({ timeout: 3000 })) return;
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

test.describe("Manage Avatars → Design a look E2E Tests", () => {
  test("Loads Design a look, renders look cards with images, tests search, tabs, themes, and ensures no overflow", async ({
    page,
  }) => {
    // 1. Ensure logged in and on Home
    await ensureLoggedIn(page);

    // 2. Navigate to Avatars via left rail navigation
    const avatarRailBtn = page.locator("#rail-nav-avatar, button[title*='Avatar']").first();
    await expect(avatarRailBtn).toBeVisible({ timeout: 10000 });
    await avatarRailBtn.click();
    await page.waitForTimeout(500);

    // 3. Click 'Design a look' in Manage Avatars sidebar
    const designLookBtn = page
      .locator("#manage-avatars-nav-design_look, button:has-text('Design a look')")
      .first();
    await expect(designLookBtn).toBeVisible({ timeout: 10000 });
    await designLookBtn.click();

    // 4. Verify Page Heading loads
    const heading = page.locator("#design-look-heading, h1:has-text('What new look are you imagining?')").first();
    await expect(heading).toBeVisible({ timeout: 10000 });
    await expect(heading).toContainText("What new look are you imagining?");

    // 5. Verify All Looks tab is active and renders cards
    const allLooksTab = page.locator("#tab-all-looks").first();
    await expect(allLooksTab).toBeVisible({ timeout: 5000 });

    const cardsGrid = page.locator("#looks-cards-grid");
    await expect(cardsGrid).toBeVisible({ timeout: 15000 });

    const lookCards = cardsGrid.locator('[data-testid^="look-card-"]');
    const cardsCount = await lookCards.count();
    expect(cardsCount).toBeGreaterThan(0);

    // 6. Verify cards have images with valid sources and no external Unsplash URLs
    const firstCard = lookCards.first();
    const cardImg = firstCard.locator("img").first();
    await expect(cardImg).toBeVisible({ timeout: 5000 });
    const imgSrc = await cardImg.getAttribute("src");
    expect(imgSrc).toBeTruthy();
    expect(imgSrc).not.toContain("unsplash.com");

    // Verify card aspect ratio container is square (equal height and width)
    const mediaContainer = firstCard.locator(".aspect-square").first();
    await expect(mediaContainer).toBeVisible();
    const box = await mediaContainer.boundingBox();
    expect(box).toBeTruthy();
    if (box) {
      // In 1:1 aspect ratio, width and height must be approximately equal (within 2px)
      expect(Math.abs(box.width - box.height)).toBeLessThanOrEqual(3);
    }

    // 7. Verify search functionality
    const searchInput = page.locator("#search-looks-input").first();
    await expect(searchInput).toBeVisible();

    // Search for a specific look or avatar (e.g., 'Annie' or 'Blazer')
    await searchInput.fill("Annie");
    await page.waitForTimeout(300);
    const searchFilteredCount = await lookCards.count();
    expect(searchFilteredCount).toBeGreaterThan(0);
    expect(searchFilteredCount).toBeLessThanOrEqual(cardsCount);

    // Search for non-existent item
    await searchInput.fill("xyzNonExistentLookQuery999");
    await page.waitForTimeout(300);
    const emptyState = page.locator("#looks-empty-state");
    await expect(emptyState).toBeVisible({ timeout: 5000 });
    await expect(emptyState).toContainText("No looks match");

    // Clear search using clear button
    const clearBtn = page.locator("#search-looks-clear-btn, button:has-text('Clear search')").first();
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();
    await page.waitForTimeout(300);

    // Verify cards restored
    await expect(cardsGrid).toBeVisible();
    const restoredCount = await lookCards.count();
    expect(restoredCount).toBe(cardsCount);

    // 8. Verify tabs switching
    // Click Recently Used tab
    const recentTab = page.locator("#tab-recently-used").first();
    await expect(recentTab).toBeVisible();
    await recentTab.click();
    await page.waitForTimeout(300);

    // If no recent looks yet, empty state should be displayed explicitly
    const recentContentVisible = (await cardsGrid.isVisible()) || (await emptyState.isVisible());
    expect(recentContentVisible).toBe(true);

    // Click Templates tab
    const templatesTab = page.locator("#tab-templates").first();
    await expect(templatesTab).toBeVisible();
    await templatesTab.click();
    await page.waitForTimeout(300);
    const templatesVisible = (await cardsGrid.isVisible()) || (await emptyState.isVisible());
    expect(templatesVisible).toBe(true);

    // Switch back to All Looks
    await allLooksTab.click();
    await page.waitForTimeout(300);
    await expect(cardsGrid).toBeVisible();

    // 9. Verify no horizontal overflow
    const horizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 3;
    });
    expect(horizontalOverflow).toBe(false);

    // 10. Verify Light and Dark theme support
    const themeToggleBtn = page.locator("#global-theme-toggle-btn");
    await expect(themeToggleBtn).toBeVisible({ timeout: 10000 });

    const html = page.locator("html");

    // Switch to Light mode if currently dark
    const classAttr1 = await html.getAttribute("class");
    if (!classAttr1?.includes("light")) {
      await themeToggleBtn.click();
      await page.waitForTimeout(500);
    }
    await expect(html).toHaveAttribute("data-theme", "light");
    await expect(heading).toBeVisible();
    await expect(cardsGrid).toBeVisible();

    // Switch back to Dark mode
    await themeToggleBtn.click();
    await page.waitForTimeout(500);
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(heading).toBeVisible();
    await expect(cardsGrid).toBeVisible();
  });
});
