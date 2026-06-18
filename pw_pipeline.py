"""Record main content video (Playwright) + merge with TTS audio + burn subtitles"""
import json
import subprocess
import os
import shutil
import asyncio
from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(BASE, "..", "..", "AppData", "Local", "Programs",
                      "Python", "Python313", "Scripts", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"


def record_content(html_path: str, timing_json: str, output_dir: str) -> str:
    """Record HTML animation → webm, return webm path."""
    with open(timing_json, "r", encoding="utf-8") as f:
        timing = json.load(f)

    total_s = timing["total_duration_ms"] / 1000 + 2
    rec_dir = os.path.join(output_dir, "_rec_content")
    os.makedirs(rec_dir, exist_ok=True)

    print(f"  Recording content ({total_s:.0f}s)...")

    async def _rec():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1080, "height": 1920},
                device_scale_factor=1,
                record_video_dir=rec_dir,
                record_video_size={"width": 1080, "height": 1920},
            )
            page = await ctx.new_page()
            await page.goto(f"file:///{html_path.replace(os.sep, '/')}")
            await page.wait_for_timeout(int(total_s * 1000))
            await ctx.close()
            await browser.close()

    asyncio.run(_rec())

    for f in os.listdir(rec_dir):
        if f.endswith(".webm"):
            dst = os.path.join(output_dir, "content.webm")
            os.replace(os.path.join(rec_dir, f), dst)
            shutil.rmtree(rec_dir, ignore_errors=True)
            return dst

    shutil.rmtree(rec_dir, ignore_errors=True)
    return ""


def merge_audio(webm: str, audio: str, output: str, duration_ms: int):
    """Convert webm→mp4, merge with audio, burn subtitles."""
    base = os.path.dirname(output)
    mp4_tmp = os.path.join(base, "_content_tmp.mp4")

    # webm → mp4
    print("  Converting to mp4...")
    subprocess.run([
        FFMPEG, "-y", "-i", webm,
        "-t", str(duration_ms / 1000),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an",
        mp4_tmp,
    ], capture_output=True)

    # Merge with audio
    print("  Merging audio...")
    subprocess.run([
        FFMPEG, "-y", "-i", mp4_tmp, "-i", audio,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
        output,
    ], capture_output=True)

    if os.path.exists(mp4_tmp):
        os.remove(mp4_tmp)

    size = os.path.getsize(output) / (1024 * 1024)
    print(f"  → {output} ({size:.1f} MB)")


def burn_subtitles(video: str, srt: str, output: str):
    """Burn SRT subtitles into video."""
    srt_escaped = srt.replace("\\", "/").replace(":", "\\:")
    sub_filter = (
        f"[0:v]pad=iw:ih+50:0:0:black,"
        f"subtitles='{srt_escaped}'"
        f":force_style='FontName=SimHei,FontSize=12,"
        f"PrimaryColour=&H00E8E0D0,"
        f"OutlineColour=&H40000000,"
        f"Outline=1,Shadow=0,"
        f"MarginV=12,MarginL=30,MarginR=30'[v]"
    )
    print("  Burning subtitles...")
    r = subprocess.run([
        FFMPEG, "-y", "-i", video,
        "-filter_complex", sub_filter,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output,
    ], capture_output=True, text=True)

    if r.returncode != 0:
        print(f"  Subtitle burn failed: {r.stderr[-200:]}")
    else:
        size = os.path.getsize(output) / (1024 * 1024)
        print(f"  → {output} ({size:.1f} MB)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 5:
        print("Usage: python pw_pipeline.py <html> <timing.json> <audio> <srt> <output_dir>")
    else:
        html, timing, audio, srt, out_dir = sys.argv[1:6]
        webm = record_content(html, timing, out_dir)
        if webm:
            merged = os.path.join(out_dir, "content_merged.mp4")
            final = os.path.join(out_dir, "content_final.mp4")
            merge_audio(webm, audio, merged, json.load(open(timing))["total_duration_ms"])
            burn_subtitles(merged, srt, final)
