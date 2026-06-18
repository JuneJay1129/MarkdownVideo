"""Record intro and outro clips (2.5s each) into output_dir"""
import asyncio
import os
import shutil
from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
INTRO_HTML = os.path.join(BASE, "intro.html")
OUTRO_HTML = os.path.join(BASE, "outro.html")

DURATION_S = 2.5
DURATION_MS = int(DURATION_S * 1000)


async def _record(html_path: str, name: str, output_dir: str) -> str:
    """Record one clip, returns path to .mp4"""
    rec_dir = os.path.join(output_dir, f"_rec_{name}")
    os.makedirs(rec_dir, exist_ok=True)

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
        await page.wait_for_timeout(DURATION_MS)
        await ctx.close()
        await browser.close()

    # Find webm → move & convert
    for f in os.listdir(rec_dir):
        if f.endswith(".webm"):
            webm = os.path.join(rec_dir, f)
            mp4 = os.path.join(output_dir, f"{name}.mp4")
            _convert(webm, mp4)
            shutil.rmtree(rec_dir, ignore_errors=True)
            return mp4

    shutil.rmtree(rec_dir, ignore_errors=True)
    return ""


def _convert(src: str, dst: str):
    import subprocess
    ffmpeg = os.path.join(os.path.dirname(BASE), "..", "AppData", "Local",
                          "Programs", "Python", "Python313", "Scripts", "ffmpeg.exe")
    # Try system ffmpeg first
    try:
        subprocess.run(["ffmpeg", "-y", "-i", src, "-c:v", "libx264",
                        "-preset", "fast", "-crf", "23", "-an", dst],
                       capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run([ffmpeg, "-y", "-i", src, "-c:v", "libx264",
                        "-preset", "fast", "-crf", "23", "-an", dst],
                       capture_output=True)


def record_clips(output_dir: str) -> tuple[str, str]:
    """Record intro & outro, return (intro_mp4, outro_mp4) paths."""
    os.makedirs(output_dir, exist_ok=True)

    print("Recording intro...")
    intro = asyncio.run(_record(INTRO_HTML, "intro", output_dir))
    print(f"  → {intro}")

    print("Recording outro...")
    outro = asyncio.run(_record(OUTRO_HTML, "outro", output_dir))
    print(f"  → {outro}")

    return intro, outro


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "clips")
    record_clips(out)
