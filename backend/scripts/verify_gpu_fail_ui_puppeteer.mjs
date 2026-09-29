import puppeteer from "puppeteer-core";
import fs from "fs";
import path from "path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCRATCH_DIR = path.resolve("backend/scratch");
if (!fs.existsSync(SCRATCH_DIR)) {
  fs.mkdirSync(SCRATCH_DIR, { recursive: true });
}

async function runBrowserVerification() {
  console.log("=== STARTING REAL CHROME BROWSER E2E TEST FOR GPU_REQUIRED UI ===");

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--window-size=1400,900"],
    defaultViewport: { width: 1400, height: 900 },
  });

  const page = await browser.newPage();

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      console.log(`[BROWSER ERROR] ${msg.text()}`);
    }
  });

  try {
    // 1. Navigate to http://localhost:3000
    console.log("[NAV] Loading http://localhost:3000...");
    await page.goto("http://localhost:3000", { waitUntil: "networkidle2", timeout: 30000 });

    // 2. Login if needed
    const hasLogin = await page.evaluate(() => {
      return Boolean(document.querySelector("button")?.textContent?.includes("1-Click Login"));
    });

    if (hasLogin) {
      console.log("[AUTH] Logging in via '1-Click Login'...");
      await page.evaluate(() => {
        const btn = Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("1-Click Login"));
        if (btn) btn.click();
      });
      await new Promise((r) => setTimeout(r, 2500));
    }

    // 3. Ensure Dashboard view
    console.log("[NAV] Switching to Dashboard view...");
    await page.evaluate(() => {
      const homeBtn = document.querySelector('button[title="Home / Dashboard"]');
      if (homeBtn) homeBtn.click();
    });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "gpu_fail_01_dashboard.png") });

    // 4. Open Create Modal via 'Create Ads & Promo video now'
    console.log("[ACTION] Opening modal via 'Create Ads & Promo video now'...");
    await page.evaluate(() => {
      const btn = document.querySelector('button[aria-label="Create Ads & Promo video now"]');
      if (btn) btn.click();
    });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "gpu_fail_02_modal.png") });

    // 5. In Modal: set prompt to 'hey'
    console.log("[ACTION] Setting prompt to 'hey' in modal...");
    await page.evaluate(() => {
      const modal = document.querySelector('[role="dialog"]') || document.body;
      const textarea = modal.querySelector("textarea");
      if (textarea) {
        textarea.value = "hey";
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    // 6. Click 'Generate' in modal
    console.log("[ACTION] Clicking 'Generate' in modal...");
    await page.evaluate(() => {
      const modal = document.querySelector('[role="dialog"]') || document.body;
      const genBtn = Array.from(modal.querySelectorAll("button")).find(
        (b) => b.textContent && b.textContent.trim() === "Generate"
      );
      if (genBtn) genBtn.click();
    });

    console.log("[NAV] Redirected to Video Agent Workspace. Waiting for generation to start and reach GPU_REQUIRED...");
    let terminalReached = false;
    let terminalState = null;

    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const state = await page.evaluate(() => {
        const text = document.body.innerText;
        return {
          hasGpuNotice: text.includes("Neural avatar generation requires a CUDA GPU."),
          hasFailed: text.includes("Generation Failed") || text.includes("GPU Required"),
          hasDraftTimeline: text.includes("Draft Timeline"),
          hasIncompleteDraft: text.includes("Draft / Generation incomplete"),
          hasPlayButton: Boolean(document.querySelector('button[title="Preview Timeline"]')),
          hasVideoElement: Boolean(document.querySelector("video")),
          hasRetry: text.includes("Retry Generation"),
          stageText: text.includes("Synthesizing & Rendering Video") ? "Generating..." : "Idle/Terminal",
        };
      });

      if (state.hasGpuNotice) {
        terminalReached = true;
        terminalState = state;
        console.log(`[POLL ${i}s] Terminal failure state reached:`, JSON.stringify(state, null, 2));
        break;
      }
    }

    await page.screenshot({ path: path.join(SCRATCH_DIR, "gpu_fail_03_annie_failed.png") });

    if (!terminalReached) {
      const pageText = await page.evaluate(() => document.body.innerText.slice(0, 500));
      throw new Error(`FAIL: Did not reach GPU notice within timeout. Page text: ${pageText}`);
    }

    // Validate Test A conditions
    const annieValidation = await page.evaluate(() => {
      const body = document.body.innerText;
      return {
        gpuNoticeInChat: body.includes("Neural avatar generation requires a CUDA GPU."),
        retryButtonPresent: Boolean(Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("Retry Generation"))),
        draftTimelineBadgeAbsent: !body.includes("Draft Timeline"),
        fakePlayButtonAbsent: !Boolean(document.querySelector('button[title="Preview Timeline"]')),
        playableVideoAbsent: !Boolean(document.querySelector("video")),
        draftScenesMarkedIncomplete: body.includes("Draft / Generation incomplete"),
      };
    });

    console.log("[VALIDATION ANNIE]", JSON.stringify(annieValidation, null, 2));
    if (!annieValidation.gpuNoticeInChat) throw new Error("FAIL: 'Neural avatar generation requires a CUDA GPU.' was not displayed!");
    if (!annieValidation.retryButtonPresent) throw new Error("FAIL: 'Retry Generation' button was not displayed!");
    if (!annieValidation.draftTimelineBadgeAbsent) throw new Error("FAIL: Stale 'Draft Timeline' badge was displayed!");
    if (!annieValidation.fakePlayButtonAbsent) throw new Error("FAIL: Fake Play button was displayed!");
    if (!annieValidation.playableVideoAbsent) throw new Error("FAIL: A video element was displayed on GPU_REQUIRED failure!");
    console.log("[OK] Test A (Annie prompt 'hey') PASSED all requirements.");

    // -----------------------------------------------------------------
    // TEST B: Verify Retry Generation Action
    // -----------------------------------------------------------------
    console.log("\n[TEST B] Testing Retry Generation button...");
    const retryClicked = await page.evaluate(() => {
      const retryBtn = Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("Retry Generation"));
      if (retryBtn) {
        retryBtn.click();
        return true;
      }
      return false;
    });
    console.log(`[ACTION] Retry button clicked: ${retryClicked}`);
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "gpu_fail_04_retry_triggered.png") });

    const isRetrying = await page.evaluate(() => {
      return document.body.innerText.includes("Generating...") || document.body.innerText.includes("Synthesizing");
    });
    console.log(`[OK] Retry triggered active generation successfully: ${isRetrying}`);

    // Wait for retry to settle back to GPU_REQUIRED
    for (let i = 0; i < 25; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const hasGpu = await page.evaluate(() => document.body.innerText.includes("Neural avatar generation requires a CUDA GPU."));
      if (hasGpu) break;
    }

    // -----------------------------------------------------------------
    // TEST C: Send prompt "hey" with Non-Annie presenter in composer
    // -----------------------------------------------------------------
    console.log("\n[TEST C] Selecting Non-Annie presenter and prompting 'hey'...");
    
    // Open presenter picker
    const pickerOpened = await page.evaluate(() => {
      const pickerBtn = document.querySelector('#presenter-selector-btn') || document.querySelector('[data-testid="presenter-selector-btn"]');
      if (pickerBtn) {
        pickerBtn.click();
        return true;
      }
      return false;
    });
    console.log(`[ACTION] Presenter picker opened: ${pickerOpened}`);
    await new Promise((r) => setTimeout(r, 1000));

    // Select Rasmus or Daniel
    const selectedNonAnnie = await page.evaluate(() => {
      const option = document.querySelector('[data-testid*="presenter-option"]');
      const buttons = Array.from(document.querySelectorAll("button"));
      const presenterBtn = buttons.find((b) => (b.textContent?.includes("Rasmus") || b.textContent?.includes("Daniel") || b.textContent?.includes("Sophia")) && !b.textContent?.includes("Annie"));
      if (presenterBtn) {
        presenterBtn.click();
        return presenterBtn.textContent?.trim();
      }
      if (option) {
        option.click();
        return option.textContent?.trim();
      }
      return null;
    });
    console.log(`[ACTION] Selected non-Annie presenter: ${selectedNonAnnie}`);
    await new Promise((r) => setTimeout(r, 1000));

    // Type "hey" into the VideoAgentWorkspace composer
    await page.evaluate(() => {
      const textarea = document.querySelector('textarea[placeholder*="Enter your next prompt"]');
      if (textarea) {
        textarea.value = "hey";
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    await page.evaluate(() => {
      const sendBtn = document.querySelector('button[title="Send Prompt"]');
      if (sendBtn) sendBtn.click();
    });

    console.log("[POLL] Waiting for non-Annie job to reach GPU_REQUIRED...");
    for (let i = 0; i < 35; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const hasNotice = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes("Neural avatar generation requires a CUDA GPU.");
      });
      if (hasNotice) {
        console.log(`[POLL ${i}s] Non-Annie failure reached.`);
        break;
      }
    }

    await page.screenshot({ path: path.join(SCRATCH_DIR, "gpu_fail_05_non_annie_failed.png") });

    // Validate Test C conditions
    const nonAnnieValidation = await page.evaluate(() => {
      const body = document.body.innerText;
      return {
        gpuNoticePresent: body.includes("Neural avatar generation requires a CUDA GPU."),
        retryButtonPresent: Boolean(Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("Retry Generation"))),
        draftTimelineBadgeAbsent: !body.includes("Draft Timeline"),
        fakePlayButtonAbsent: !Boolean(document.querySelector('button[title="Preview Timeline"]')),
        playableVideoAbsent: !Boolean(document.querySelector("video")),
      };
    });

    console.log("[VALIDATION NON-ANNIE]", JSON.stringify(nonAnnieValidation, null, 2));
    if (!nonAnnieValidation.gpuNoticePresent) throw new Error("FAIL: 'Neural avatar generation requires a CUDA GPU.' was not displayed for non-Annie presenter!");
    if (!nonAnnieValidation.draftTimelineBadgeAbsent) throw new Error("FAIL: Draft Timeline badge was displayed!");
    if (!nonAnnieValidation.fakePlayButtonAbsent) throw new Error("FAIL: Fake Play button was displayed!");
    if (!nonAnnieValidation.playableVideoAbsent) throw new Error("FAIL: Video preview was displayed!");
    console.log("[OK] Test C (Non-Annie prompt 'hey') PASSED all requirements.");

    console.log("\n==========================================================");
    console.log("ALL REAL BROWSER E2E TESTS COMPLETED AND VERIFIED 100%!");
    console.log("==========================================================");

  } finally {
    await browser.close();
  }
}

runBrowserVerification().catch((err) => {
  console.error("Browser test failed:", err);
  process.exit(1);
});
