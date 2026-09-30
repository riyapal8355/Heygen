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
  // If in VideoAgentWorkspace, click return home
  const vaHomeBtn = page.locator("#video-agent-home-btn, button[title='Return to Dashboard']").first();
  if (await vaHomeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await vaHomeBtn.click();
    await page.waitForTimeout(400);
  }

  // If in Studio, click back to dashboard
  const backToDashBtn = page.locator("#back-to-dashboard-btn, button[title='Return to Home']").first();
  if (await backToDashBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await backToDashBtn.click();
    await page.waitForTimeout(400);
  }

  // Click Apps on rail navigation
  const toolsRailBtn = page.locator("#rail-nav-tools, button[title*='Apps']").first();
  await expect(toolsRailBtn).toBeVisible({ timeout: 10000 });
  await toolsRailBtn.click();
  await page.waitForTimeout(400);

  // If on another apps sub-section, ensure Home is selected
  const homeBtn = page.locator("#apps-sidebar-nav-home").first();
  if (await homeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await homeBtn.click();
    await page.waitForTimeout(300);
  }

  // Verify Apps Home page title
  const heading = page.locator("#apps-page-title").first();
  await expect(heading).toBeVisible({ timeout: 10000 });
}

test.describe("Apps Home Workflow Routing Audit & Validation", () => {
  test.setTimeout(90000);

  test.beforeEach(async ({ page }) => {
    await ensureLoggedIn(page);
    await navigateToAppsHome(page);
  });

  test("1. Dedicated Page View Apps open their respective workflows, NOT Studio", async ({
    page,
  }) => {
    // 1A. Video Agent -> VideoAgentWorkspace
    const videoAgentCard = page.locator("#app-card-app_video_agent");
    await expect(videoAgentCard).toBeVisible();
    await videoAgentCard.click();
    await page.waitForTimeout(500);

    // Verify Video Agent workspace rendered and Studio did NOT open
    await expect(page.locator("#video-agent-workspace")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();
    // Normal Video Agent session must NOT have specialized workflow context
    await expect(page.locator("#video-agent-workflow-context")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1B. Design a Look -> DesignLookStudio
    const designLookCard = page.locator("#app-card-app_design_look");
    await expect(designLookCard).toBeVisible();
    await designLookCard.click();
    await page.waitForTimeout(500);

    // Verify Design Look Studio root is visible
    await expect(page.locator("#design-look-studio-root")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1C. Translate Videos -> TranslateVideos
    const translateCard = page.locator("#app-card-app_translate");
    await expect(translateCard).toBeVisible();
    await translateCard.click();
    await page.waitForTimeout(500);

    // Verify Translate Videos view is visible
    await expect(page.locator("#translate-videos-view")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1D. Single Scene Video -> SingleScene
    const singleSceneCard = page.locator("#app-card-app_single_scene");
    await expect(singleSceneCard).toBeVisible();
    await singleSceneCard.click();
    await page.waitForTimeout(500);

    // Verify Single Scene view is visible
    await expect(page.locator("#single-scene-view")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1E. Scene by Scene -> SceneByScene
    const sceneBySceneCard = page.locator("#app-card-app_scene_by_scene");
    await expect(sceneBySceneCard).toBeVisible();
    await sceneBySceneCard.click();
    await page.waitForTimeout(500);

    // Verify Scene by Scene view is visible
    await expect(page.locator("#scene-by-scene-view")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1F. Brand Systems -> BrandSystems
    const brandCard = page.locator("#app-card-app_brand_kit");
    await expect(brandCard).toBeVisible();
    await brandCard.click();
    await page.waitForTimeout(500);

    // Verify Brand Systems view is visible
    await expect(page.locator("#brand-systems-view")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 1G. AI Studio -> Fundamental Studio destination
    const studioCard = page.locator("#app-card-app_studio");
    await expect(studioCard).toBeVisible();
    await studioCard.click();
    await page.waitForTimeout(500);

    // Verify Studio container is visible
    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 10000 });
  });

  test("2. AI Video Generator modal opens with truthful GPU limitation notice", async ({
    page,
  }) => {
    const generatorCard = page.locator("#app-card-app_generator");
    await expect(generatorCard).toBeVisible();
    await generatorCard.click();

    // Verify dedicated generator modal
    const submitBtn = page.locator("#modal-generator-submit-btn");
    await expect(submitBtn).toBeVisible({ timeout: 5000 });

    // Click generate button
    await submitBtn.click();

    // Verify truthful GPU_REQUIRED notice appears (no fake generation, no fake mp4)
    const gpuNotice = page.locator("#generator-gpu-required-notice");
    await expect(gpuNotice).toBeVisible({ timeout: 5000 });
    await expect(gpuNotice).toContainText("GPU_REQUIRED");

    // Close modal
    const closeBtn = page.locator("button[aria-label='Close modal']").first();
    await closeBtn.click();
    await expect(gpuNotice).not.toBeVisible();
  });

  test("3A. Dedicated Workflow Modals: Podcast, Speech, PPT/PDF, Shots project assembly and Studio handoff", async ({
    page,
  }) => {
    // 3A1. Video Podcast Modal -> Creates Project -> Studio
    const podcastCard = page.locator("#app-card-app_podcast");
    await expect(podcastCard).toBeVisible();
    await podcastCard.click();

    const podcastSubmit = page.locator("#modal-podcast-submit-btn");
    await expect(podcastSubmit).toBeVisible({ timeout: 5000 });
    await podcastSubmit.click();

    // Verify Studio opened with generated podcast project
    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);

    // 3A2. Speech Cleanup Modal -> Creates Project -> Studio
    const speechCard = page.locator("#app-card-app_speech");
    await expect(speechCard).toBeVisible();
    await speechCard.click();

    const speechSubmit = page.locator("#modal-speech-submit-btn");
    await expect(speechSubmit).toBeVisible({ timeout: 5000 });
    await speechSubmit.click();

    // Verify Studio opened with cleaned speech project
    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);

    // 3A3. PPT/PDF to Video Modal -> Video Agent with Preserved Context -> Orchestration
    const pdfCard = page.locator("#app-card-app_pdf");
    await expect(pdfCard).toBeVisible();
    await pdfCard.click();

    // Verify PPT/PDF modal opened with controls intact
    const pdfModal = page.locator("#modal-pdf");
    await expect(pdfModal).toBeVisible({ timeout: 5000 });
    const pdfPromptInput = page.locator("#modal-pdf-prompt-input");
    await expect(pdfPromptInput).toBeVisible();
    await pdfPromptInput.fill("Create a product launch presentation for our new laptop.");

    const pdfSubmit = page.locator("#modal-pdf-submit-btn");
    await expect(pdfSubmit).toBeVisible({ timeout: 5000 });
    await pdfSubmit.click();

    // Verify Studio did NOT open directly from the modal
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Verify Video Agent workspace opened with workflow context
    const vaWorkspace = page.locator("#video-agent-workspace");
    await expect(vaWorkspace).toBeVisible({ timeout: 10000 });

    const workflowContext = page.locator("#video-agent-workflow-context");
    await expect(workflowContext).toBeVisible({ timeout: 10000 });
    await expect(workflowContext).toContainText("PPT/PDF to Video");
    await expect(page.locator("#workflow-context-config")).toContainText("Q3_Product_Roadmap.pdf");

    // Verify prompt is editable in composer
    const composerInput = page.locator("#video-agent-composer-input");
    await expect(composerInput).toBeVisible();
    await expect(composerInput).toHaveValue("Create a product launch presentation for our new laptop.");

    // Submit prompt in Video Agent to trigger orchestration
    const generateBtn = page.locator("#video-agent-generate-btn");
    await expect(generateBtn).toBeVisible();
    await generateBtn.click({ force: true });
    await page.waitForTimeout(600);

    // Return to Apps Home
    await navigateToAppsHome(page);

    // 3A4. Cinematic Shots Modal -> Video Agent with Preserved Context -> Orchestration
    const shotsCard = page.locator("#app-card-app_shots");
    await expect(shotsCard).toBeVisible();
    await shotsCard.click();

    // Verify Cinematic Shots modal opened with controls intact
    const shotsModal = page.locator("#modal-shots");
    await expect(shotsModal).toBeVisible({ timeout: 5000 });
    const shotsPromptInput = page.locator("#modal-shots-prompt-input");
    await expect(shotsPromptInput).toBeVisible();
    await shotsPromptInput.fill("Epic cinematic hero shot in golden hour 35mm atmosphere.");

    const shotsSubmit = page.locator("#modal-shots-submit-btn");
    await expect(shotsSubmit).toBeVisible({ timeout: 5000 });
    await shotsSubmit.click();

    // Verify Studio did NOT open directly from the modal
    await expect(page.locator("#vido-studio-container")).not.toBeVisible();

    // Verify Video Agent workspace opened with cinematic workflow context
    await expect(vaWorkspace).toBeVisible({ timeout: 10000 });
    await expect(workflowContext).toBeVisible({ timeout: 10000 });
    await expect(workflowContext).toContainText("Cinematic Shots");
    await expect(page.locator("#workflow-context-config")).toContainText("Over-the-Shoulder Dialogue Cut");

    // Verify prompt is editable in composer
    await expect(composerInput).toBeVisible();
    await expect(composerInput).toHaveValue("Epic cinematic hero shot in golden hour 35mm atmosphere.");

    // Submit prompt in Video Agent to trigger orchestration
    await generateBtn.click({ force: true });
    await page.waitForTimeout(600);

    // Return to Apps Home
    await navigateToAppsHome(page);
  });

  test("3B. Dedicated Workflow Modals: Upscale, Clipping, Face Swap, Interactive project assembly and Studio handoff", async ({
    page,
  }) => {
    // 3B1. AI Video Upscaler Modal -> Creates Project -> Studio
    const upscaleCard = page.locator("#app-card-app_upscale");
    await expect(upscaleCard).toBeVisible();
    await upscaleCard.click();

    const upscaleSubmit = page.locator("#modal-upscale-submit-btn");
    await expect(upscaleSubmit).toBeVisible({ timeout: 5000 });
    await upscaleSubmit.click();

    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);

    // 3B2. AI Clipping Modal -> Creates Project -> Studio
    const clippingCard = page.locator("#app-card-app_clipping");
    await expect(clippingCard).toBeVisible();
    await clippingCard.click();

    const clippingSubmit = page.locator("#modal-clipping-submit-btn");
    await expect(clippingSubmit).toBeVisible({ timeout: 5000 });
    await clippingSubmit.click();

    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);

    // 3B3. Face Swap Modal -> Creates Project -> Studio
    const faceswapCard = page.locator("#app-card-app_faceswap");
    await expect(faceswapCard).toBeVisible();
    await faceswapCard.click();

    const faceswapSubmit = page.locator("#modal-faceswap-submit-btn");
    await expect(faceswapSubmit).toBeVisible({ timeout: 5000 });
    await faceswapSubmit.click();

    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);

    // 3B4. Interactive Video Modal -> Creates Project -> Studio
    const interactiveCard = page.locator("#app-card-app_interactive");
    await expect(interactiveCard).toBeVisible();
    await interactiveCard.click();

    const interactiveSubmit = page.locator("#modal-interactive-submit-btn");
    await expect(interactiveSubmit).toBeVisible({ timeout: 5000 });
    await interactiveSubmit.click();

    await expect(page.locator("#vido-studio-container")).toBeVisible({ timeout: 15000 });
    await navigateToAppsHome(page);
  });

  test("4. Featured Cards 2 & 3 open dedicated modals directly without generic popup", async ({
    page,
  }) => {
    // Featured Card 2: PPT/PDF to Video
    const featuredPdf = page.locator("#featured-app-pdf");
    await expect(featuredPdf).toBeVisible();
    await featuredPdf.click();

    const pdfSubmit = page.locator("#modal-pdf-submit-btn");
    await expect(pdfSubmit).toBeVisible({ timeout: 5000 });

    const closeBtn = page.locator("button[aria-label='Close modal']").first();
    await closeBtn.click();
    await expect(pdfSubmit).not.toBeVisible();

    // Featured Card 3: Cinematic Shots
    const featuredShots = page.locator("#featured-app-shots");
    await expect(featuredShots).toBeVisible();
    await featuredShots.click();

    const shotsSubmit = page.locator("#modal-shots-submit-btn");
    await expect(shotsSubmit).toBeVisible({ timeout: 5000 });

    const closeBtn2 = page.locator("button[aria-label='Close modal']").first();
    await closeBtn2.click();
    await expect(shotsSubmit).not.toBeVisible();
  });
});
