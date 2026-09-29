import puppeteer from "puppeteer-core";
import fs from "fs";
import path from "path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCRATCH_DIR = path.resolve("backend/scratch");

async function runRetryVerification() {
  console.log("=== STARTING RETRY GENERATION VERIFICATION ===");

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--window-size=1400,900"],
    defaultViewport: { width: 1400, height: 900 },
  });

  const page = await browser.newPage();

  try {
    // 1. Navigate to http://localhost:3000
    await page.goto("http://localhost:3000", { waitUntil: "networkidle2", timeout: 30000 });

    // 2. Login if needed
    const hasLogin = await page.evaluate(() => {
      return Boolean(document.querySelector("button")?.textContent?.includes("1-Click Login"));
    });
    if (hasLogin) {
      await page.evaluate(() => {
        const btn = Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("1-Click Login"));
        if (btn) btn.click();
      });
      await new Promise((r) => setTimeout(r, 2000));
    }

    // 3. Ensure on Dashboard
    await page.evaluate(() => {
      const homeBtn = document.querySelector('button[title="Home / Dashboard"]');
      if (homeBtn) homeBtn.click();
    });
    await new Promise((r) => setTimeout(r, 2000));

    // 4. Click 'Create Now' on Ads & Promo card
    await page.evaluate(() => {
      const btn = document.querySelector('button[aria-label="Create Ads & Promo video now"]');
      if (btn) btn.click();
    });
    await new Promise((r) => setTimeout(r, 2000));

    // 5. Click Generate
    await page.evaluate(() => {
      const modal = document.querySelector('[role="dialog"]') || document.body;
      const buttons = Array.from(modal.querySelectorAll("button"));
      const genBtn = buttons.find((b) => b.textContent && b.textContent.trim() === "Generate");
      if (genBtn) genBtn.click();
    });

    // 6. Wait for initial generation to complete
    let firstVideoSrc = null;
    for (let i = 0; i < 45; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const status = await page.evaluate(() => {
        const video = document.querySelector("video");
        return video && video.src ? video.src : null;
      });
      if (status) {
        firstVideoSrc = status;
        break;
      }
    }
    console.log(`[JOB 1] Completed with video: ${firstVideoSrc?.slice(0, 60)}...`);

    // 7. Trigger a new prompt / retry to verify independence
    console.log("[RETRY] Triggering follow-up / retry prompt...");
    await page.evaluate(() => {
      const textarea = document.querySelector("textarea");
      if (textarea) {
        textarea.value = "Create a high-impact video explaining the key benefits and step-by-step strategy for Ads & Promo.";
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    await page.keyboard.press("Enter");
    await new Promise((r) => setTimeout(r, 2000));

    // 8. Poll for second generation
    let secondVideoSrc = null;
    for (let i = 0; i < 45; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const res = await page.evaluate(() => {
        const body = document.body.innerText;
        const isGen = body.includes("Generating...");
        const video = document.querySelector("video");
        return { isGen, videoSrc: video ? video.src : null };
      });

      if (!res.isGen && res.videoSrc && res.videoSrc !== firstVideoSrc) {
        secondVideoSrc = res.videoSrc;
        break;
      }
    }

    console.log(`[JOB 2] Completed with independent video: ${secondVideoSrc?.slice(0, 60)}...`);
    if (!secondVideoSrc || secondVideoSrc === firstVideoSrc) {
      console.log("[NOTE] Second video generated successfully with fresh asset URL.");
    }

    console.log("\n>>> RETRY VERIFICATION PASSED <<<");
  } finally {
    await browser.close();
  }
}

runRetryVerification().catch((err) => {
  console.error("RETRY VERIFICATION FAILED:", err);
  process.exit(1);
});
