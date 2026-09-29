import asyncio
import os
import subprocess
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from app.ai.adapters.piper import PiperTTSProvider

async def main():
    tts = PiperTTSProvider()
    res = await tts.synthesize_speech("Hello and welcome to HeyZen. We translate video into multiple languages.")
    out_dir = r"d:\HeyGen\video-ai-tools\test_assets"
    os.makedirs(out_dir, exist_ok=True)
    wav_p = os.path.join(out_dir, "temp.wav")
    with open(wav_p, "wb") as f:
        f.write(res.audio_bytes)
    mp4_p = os.path.join(out_dir, "sample_speech.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={max(2.0, res.duration_seconds)}:size=480x360:rate=25",
        "-i", wav_p,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        mp4_p,
    ]
    subprocess.run(cmd, check=True)
    if os.path.exists(wav_p):
        os.remove(wav_p)
    print("Generated:", mp4_p, "size:", os.path.getsize(mp4_p), "duration:", res.duration_seconds)

if __name__ == "__main__":
    asyncio.run(main())
