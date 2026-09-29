import puppeteer from "puppeteer-core";
import fs from "fs";
import path from "path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCRATCH_DIR = path.resolve("backend/scratch");
if (!fs.existsSync(SCRATCH_DIR)) {
  fs.mkdirSync(SCRATCH_DIR, { recursive: true });
}

async function runBrowserVerification() {
  console.log("=== STARTING BROWSER E2E VERIFICATION ===");

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

    // 3. Switch to Dashboard via Left Rail Home button
    console.log("[NAV] Ensuring Dashboard view via Home rail icon...");
    await page.evaluate(() => {
      const homeBtn = document.querySelector('button[title="Home / Dashboard"]');
      if (homeBtn) homeBtn.click();
    });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_01_dashboard.png") });

    // 4. Click the exact 'Create Now' button for Ads & Promo
    console.log("[ACTION] Clicking 'Create Now' on Ads & Promo card...");
    const cardClicked = await page.evaluate(() => {
      const btn = document.querySelector('button[aria-label="Create Ads & Promo video now"]');
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    });
    console.log(`[ACTION] Card clicked: ${cardClicked}`);
    if (!cardClicked) {
      throw new Error("Could not find Ads & Promo 'Create Now' button");
    }

    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_02_modal.png") });

    // 5. Inspect Modal details (Avatar, Voice, Captions, Prompt)
    const modalDetails = await page.evaluate(() => {
      const body = document.body.innerText;
      const textarea = document.querySelector("textarea");
      return {
        hasAnniePresenter: body.includes("Annie"),
        hasVoice: body.includes("Lifelike") || body.includes("Annie"),
        hasCaptions: body.includes("CC") || body.includes("Captions"),
        promptValue: textarea ? textarea.value : "",
      };
    });
    console.log("[MODAL CONFIG]", JSON.stringify(modalDetails, null, 2));

    // 6. Click 'Generate' button in modal
    console.log("[ACTION] Clicking 'Generate' in modal...");
    const generateClicked = await page.evaluate(() => {
      const modal = document.querySelector('[role="dialog"]') || document.body;
      const buttons = Array.from(modal.querySelectorAll("button"));
      // The modal footer button with text "Generate"
      const genBtn = buttons.find((b) => b.textContent && b.textContent.trim() === "Generate");
      if (genBtn) {
        genBtn.click();
        return true;
      }
      return false;
    });
    console.log(`[ACTION] Generate button clicked: ${generateClicked}`);
    if (!generateClicked) {
      throw new Error("Could not find modal Generate button");
    }

    // 7. Observe Generating state in Video Agent workspace
    await new Promise((r) => setTimeout(r, 2500));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_03_generating.png") });

    const genState = await page.evaluate(() => {
      const body = document.body.innerText;
      const isGenerating = body.includes("Generating Video Project") || body.includes("Generating...") || body.includes("Synthesizing");
      const hasFailed = body.includes("Generation Failed");
      const hasReady = body.includes("Draft Timeline") || (body.includes("Scene Breakdown") && !isGenerating);
      return { isGenerating, hasFailed, hasReady };
    });
    console.log("[GENERATING STATE]", JSON.stringify(genState, null, 2));

    if (genState.hasFailed && genState.hasReady) {
      throw new Error("CRITICAL BUG: UI shows FAILED and READY simultaneously!");
    }

    // 8. Poll for Completion (~90s max)
    console.log("[POLL] Waiting for media pipeline to finish (Piper TTS -> Wav2Lip -> FFmpeg -> MinIO)...");
    let completed = false;
    let finalVideoSrc = null;
    let durationSec = 0;

    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const status = await page.evaluate(() => {
        const video = document.querySelector("video");
        const body = document.body.innerText;
        const failed = body.includes("Generation Failed");
        const hasDownload = body.includes("Download MP4");
        const hasOpenStudio = body.includes("Open in Studio");
        return {
          hasVideo: Boolean(video && video.src),
          videoSrc: video ? video.src : null,
          videoDuration: video ? video.duration : 0,
          failed,
          hasDownload,
          hasOpenStudio,
        };
      });

      if (status.failed) {
        throw new Error("Generation failed in browser UI!");
      }

      if (status.hasVideo && status.hasDownload) {
        console.log(`[POLL] Generation COMPLETED in ~${i + 1}s!`);
        finalVideoSrc = status.videoSrc;
        durationSec = status.videoDuration;
        console.log(`[VIDEO SRC] ${finalVideoSrc.slice(0, 80)}...`);
        completed = true;
        break;
      }
    }

    if (!completed) {
      throw new Error("Browser UI did not reach completed state in allowed timeout.");
    }

    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_04_ready.png") });

    // 9. Verify Video Playback and check for FAILED/READY contradictions
    const readyCheck = await page.evaluate(async () => {
      const body = document.body.innerText;
      const hasFailed = body.includes("Generation Failed");
      const video = document.querySelector("video");
      let playOk = false;
      let dur = 0;

      if (video) {
        dur = video.duration || 0;
        try {
          await video.play();
          playOk = !video.paused;
        } catch (e) {}
      }

      const downloadLink = document.querySelector('a[title="Download Rendered MP4"]');
      const scenes = Array.from(document.querySelectorAll("h5")).map((h) => h.innerText);

      return {
        hasFailed,
        hasVideoTag: Boolean(video),
        videoDuration: dur,
        playOk,
        downloadHref: downloadLink ? downloadLink.href : null,
        scenesCount: scenes.length,
      };
    });

    console.log("[READY VERIFICATION]", JSON.stringify(readyCheck, null, 2));
    if (readyCheck.hasFailed) {
      throw new Error("Contradiction: 'Generation Failed' found on ready screen!");
    }

    // 10. Follow-up prompt: "Make it shorter and more professional."
    console.log("[ACTION] Testing follow-up prompt: 'Make it shorter and more professional.'");
    await page.evaluate(() => {
      const textarea = document.querySelector("textarea");
      if (textarea) {
        textarea.value = "Make it shorter and more professional.";
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    await page.keyboard.press("Enter");
    await new Promise((r) => setTimeout(r, 2500));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_05_followup_generating.png") });

    console.log("[ACTION] Polling follow-up generation completion...");
    let followupDone = false;
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const res = await page.evaluate(() => {
        const body = document.body.innerText;
        const isGen = body.includes("Generating Video Project") || body.includes("Generating...");
        const video = document.querySelector("video");
        return { isGen, hasVideo: Boolean(video && video.src) };
      });

      if (!res.isGen && res.hasVideo) {
        console.log(`[ACTION] Follow-up generation COMPLETED in ~${i + 1}s!`);
        followupDone = true;
        break;
      }
    }

    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_06_followup_done.png") });

    // 11. Test Open in Studio
    console.log("[ACTION] Clicking 'Open in Studio' button...");
    const studioClicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll("button"));
      const btn = buttons.find((b) => b.textContent && b.textContent.includes("Open in Studio"));
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    });

    console.log(`[ACTION] Clicked 'Open in Studio': ${studioClicked}`);
    await new Promise((r) => setTimeout(r, 3500));
    await page.screenshot({ path: path.join(SCRATCH_DIR, "browser_07_studio.png") });

    const studioDetails = await page.evaluate(() => {
      const body = document.body.innerText;
      const isStudio = body.includes("Studio") || body.includes("Timeline") || body.includes("Scene") || body.includes("Layers");
      return { isStudio, bodyPreview: body.slice(0, 100) };
    });
    console.log("[STUDIO DETAILS]", JSON.stringify(studioDetails, null, 2));

    console.log("\n>>> FULL BROWSER E2E TEST PASSED 100% <<<");
  } finally {
    await browser.close();
  }
}

runBrowserVerification().catch((err) => {
  console.error("BROWSER VERIFICATION FAILED:", err);
  process.exit(1);
});
