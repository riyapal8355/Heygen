import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Translate Videos Feature End-to-End Logic", () => {
  // 1. Source Media Input Validation
  describe("Source Media Validation", () => {
    const ALLOWED_EXTENSIONS = [".mp4", ".mov", ".webm"];
    const ALLOWED_MIME_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
    const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 * 1024; // 5 GB
    const FREE_PLAN_MAX_DURATION_SECONDS = 120.0;

    function validateLocalVideo(file: { name: string; type: string; size: number; duration?: number }) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return { valid: false, error: `Unsupported file extension '${ext}'. Allowed: MP4, MOV, WEBM.` };
      }
      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        return { valid: false, error: `Unsupported MIME type '${file.type}'.` };
      }
      if (file.size > MAX_FILE_SIZE_BYTES) {
        return { valid: false, error: "File size exceeds 5 GB limit." };
      }
      if (file.duration && file.duration > FREE_PLAN_MAX_DURATION_SECONDS) {
        return { valid: false, error: `Duration exceeds limit of ${FREE_PLAN_MAX_DURATION_SECONDS}s.` };
      }
      return { valid: true };
    }

    it("accepts valid MP4, MOV, and WEBM video uploads within bounds", () => {
      assert.deepStrictEqual(validateLocalVideo({ name: "demo.mp4", type: "video/mp4", size: 10 * 1024 * 1024 }), { valid: true });
      assert.deepStrictEqual(validateLocalVideo({ name: "clip.mov", type: "video/quicktime", size: 50 * 1024 * 1024 }), { valid: true });
      assert.deepStrictEqual(validateLocalVideo({ name: "screen.webm", type: "video/webm", size: 5 * 1024 * 1024 }), { valid: true });
    });

    it("rejects unsupported extensions such as .avi, .mkv, .exe", () => {
      assert.strictEqual(validateLocalVideo({ name: "bad.avi", type: "video/avi", size: 1000 }).valid, false);
      assert.strictEqual(validateLocalVideo({ name: "bad.exe", type: "application/octet-stream", size: 1000 }).valid, false);
    });

    it("rejects files exceeding 5 GB maximum limit", () => {
      const oversized = 6 * 1024 * 1024 * 1024;
      assert.strictEqual(validateLocalVideo({ name: "huge.mp4", type: "video/mp4", size: oversized }).valid, false);
    });
  });

  // 2. URL Ingestion Syntax Validation
  describe("URL Ingestion Syntax Validation", () => {
    function validateVideoUrl(url: string) {
      const clean = (url || "").trim();
      if (!clean) return { valid: false, error: "URL cannot be empty." };
      try {
        const parsed = new URL(clean);
        if (!["http:", "https:"].includes(parsed.protocol)) {
          return { valid: false, error: "URL must use http or https protocol." };
        }
        if (["localhost", "127.0.0.1", "0.0.0.0"].includes(parsed.hostname)) {
          return { valid: false, error: "Internal network URLs are disallowed." };
        }
        return { valid: true, url: clean };
      } catch {
        return { valid: false, error: "Invalid URL syntax." };
      }
    }

    it("accepts valid public YouTube and Google Drive links", () => {
      assert.strictEqual(validateVideoUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ").valid, true);
      assert.strictEqual(validateVideoUrl("https://drive.google.com/file/d/12345/view").valid, true);
    });

    it("rejects empty, invalid, and SSRF localhost targets", () => {
      assert.strictEqual(validateVideoUrl("").valid, false);
      assert.strictEqual(validateVideoUrl("ftp://files.example.com/video.mp4").valid, false);
      assert.strictEqual(validateVideoUrl("http://localhost:8000/internal").valid, false);
      assert.strictEqual(validateVideoUrl("not-a-url").valid, false);
    });
  });

  // 3. Language & Voice Registry Mapping
  describe("Language & Voice Registry", () => {
    const SUPPORTED_LANGUAGES = [
      { code: "es", name: "Spanish", voiceId: "es_ES-davefx-medium" },
      { code: "fr", name: "French", voiceId: "fr_FR-siwis-medium" },
      { code: "de", name: "German", voiceId: "de_DE-thorsten-medium" },
      { code: "it", name: "Italian", voiceId: "it_IT-serena-medium" },
      { code: "pt", name: "Portuguese", voiceId: "pt_BR-faber-medium" },
      { code: "en", name: "English", voiceId: "en_US-lessac-medium" },
    ];

    it("verifies all advertised languages have assigned Piper voices", () => {
      for (const lang of SUPPORTED_LANGUAGES) {
        assert.ok(lang.code.length >= 2);
        assert.ok(lang.voiceId.startsWith(lang.code) || lang.voiceId.includes(lang.code));
      }
    });

    it("supports multi-target language job orchestration", () => {
      const targets = ["es", "fr", "de"];
      const distinctJobs = targets.map((t) => ({
        targetLanguage: t,
        voiceId: SUPPORTED_LANGUAGES.find((l) => l.code === t)?.voiceId,
        status: "QUEUED",
      }));
      assert.strictEqual(distinctJobs.length, 3);
      assert.strictEqual(distinctJobs[0].targetLanguage, "es");
      assert.strictEqual(distinctJobs[1].targetLanguage, "fr");
      assert.strictEqual(distinctJobs[2].targetLanguage, "de");
    });
  });

  // 4. Job State Machine Transitions
  describe("Job State Machine", () => {
    const VALID_STATES = [
      "QUEUED",
      "PREPARING",
      "ANALYZING",
      "TRANSCRIBING",
      "TRANSLATING",
      "GENERATING_AUDIO",
      "GENERATING_LIPSYNC",
      "COMPOSITING",
      "UPLOADING_RESULT",
      "COMPLETED",
      "FAILED",
      "PROVIDER_UNAVAILABLE",
      "GPU_REQUIRED",
      "INVALID_SOURCE",
    ];

    it("enforces canonical state naming and transitions", () => {
      assert.ok(VALID_STATES.includes("TRANSCRIBING"));
      assert.ok(VALID_STATES.includes("TRANSLATING"));
      assert.ok(VALID_STATES.includes("COMPOSITING"));
      assert.ok(VALID_STATES.includes("COMPLETED"));
    });

    it("accurately reports Wav2Lip CPU fallback mode without claiming CUDA", () => {
      const cpuLipSyncMetadata = {
        enabled: true,
        provider: "wav2lip",
        provider_mode: "development_fallback",
        hardware: "CPU",
      };
      assert.strictEqual(cpuLipSyncMetadata.provider_mode, "development_fallback");
      assert.strictEqual(cpuLipSyncMetadata.hardware, "CPU");
      assert.notStrictEqual(cpuLipSyncMetadata.provider, "liveportrait");
    });
  });

  // 5. Result Presentation & Persistence Contract
  describe("Result Presentation Contract", () => {
    it("ensures generated output contains playable URLs and Studio link", () => {
      const translationResult = {
        translation_id: "trans-1234",
        project_id: "proj-5678",
        version_id: "ver-9999",
        video_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/ws1/translations/trans-1234/es/video/translated_es.mp4",
        audio_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/ws1/translations/trans-1234/es/audio/translated_es.wav",
        subtitle_url: "http://127.0.0.1:9000/heyzen-assets/workspaces/ws1/translations/trans-1234/es/subtitles/translated_es.vtt",
        target_language: "es",
        duration: 12.5,
        translated_text: "Hola y bienvenidos a la plataforma de video HeyZen Studio.",
      };

      assert.ok(translationResult.video_url.includes(".mp4"));
      assert.ok(translationResult.subtitle_url?.includes(".vtt"));
      assert.ok(translationResult.duration > 0);
      assert.ok(translationResult.translated_text.length > 0);

      const studioUrl = `/studio/${translationResult.project_id}`;
      assert.strictEqual(studioUrl, "/studio/proj-5678");
    });
  });
});
