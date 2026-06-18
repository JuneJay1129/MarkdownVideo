"""
Pipeline v2: per-slide timecut + merge
"""
import json
import os
import subprocess
import re
import tempfile
import shutil

BASE = r"C:\Users\123\.nanobot\workspace\slide-tool"
FFMPEG = r"C:\Users\123\AppData\Local\Programs\Python\Python313\Scripts\ffmpeg.exe"
TTS_DIR = os.path.join(BASE, "tts_output")
HTML_TEMPLATE = os.path.join(BASE, "demo_anim.html")
TIMING_JSON = os.path.join(TTS_DIR, "timing.json")
AUDIO_FILE = os.path.join(TTS_DIR, "full_narration.mp3")
SRT_FILE = os.path.join(TTS_DIR, "subtitles.srt")
VIDEO_FINAL = os.path.join(BASE, "demo_final.mp4")
SLIDE_VIDEOS_DIR = os.path.join(BASE, "slide_videos")

os.makedirs(SLIDE_VIDEOS_DIR, exist_ok=True)


def generate_single_slide_html(slide_index, timing):
    """Generate a standalone HTML for one slide with correct timing."""
    with open(HTML_TEMPLATE, 'r', encoding='utf-8') as f:
        html = f.read()

    # Replace TTS_TIMING with just this slide's timing, adjusted to start at 0
    st = timing["slides"][slide_index]
    adjusted = {
        "enterStart": 0,
        "childrenStart": st["childrenStart"] - st["enterStart"],
        "exitStart": st["exitStart"] - st["enterStart"],
        "exitEnd": st["exitEnd"] - st["enterStart"],
    }
    duration_ms = adjusted["exitEnd"]

    # Keep only the current slide visible, hide others
    slide_els = [
        ('<div class="slide cover" data-slide="0">', 'cover'),
        ('<div class="slide summary" data-slide="1">', 'summary'),
        ('<div class="slide features" data-slide="2">', 'features'),
        ('<div class="slide architecture" data-slide="3">', 'architecture'),
        ('<div class="slide usage" data-slide="4">', 'usage'),
    ]

    for i, (tag, cls) in enumerate(slide_els):
        if i != slide_index:
            # Hide non-active slides by adding display:none
            html = html.replace(tag, tag.replace(
                f'class="slide {cls}"',
                f'class="slide {cls}" style="display:none"'
            ))

    # Replace TTS_TIMING
    html = html.replace(
        "const TTS_TIMING = null;",
        f"const TTS_TIMING = [{json.dumps(adjusted)}];"
    ).replace(
        re.search(r'const TTS_TIMING = \[.*?\];', html, re.DOTALL).group() if 'enterStart' in html else "NO_MATCH",
        f"const TTS_TIMING = [{json.dumps(adjusted)}];"
    )

    # Write to temp file
    tmp_path = os.path.join(SLIDE_VIDEOS_DIR, f"slide_{slide_index + 1}.html")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return tmp_path, duration_ms


def capture_slide(slide_index, html_path, duration_ms):
    """Use timecut to capture a single slide."""
    out_path = os.path.join(SLIDE_VIDEOS_DIR, f"slide_{slide_index + 1}.mp4")
    duration_s = duration_ms / 1000 + 1  # +1s buffer

    cmd = [
        "npx", "timecut",
        f"file:///{html_path.replace(os.sep, '/')}",
        f"--duration={duration_s:.0f}",
        "--fps=30",
        "--viewport=1080,1920",
        f"--ffmpeg-path={FFMPEG}",
        f"-O={out_path}",
        "--quiet",
    ]

    print(f"  Capturing slide {slide_index + 1} ({duration_s:.0f}s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=True)

    if not os.path.exists(out_path):
        print(f"    FAILED: {result.stderr[-200:]}")
        return None

    size = os.path.getsize(out_path) / 1024
    print(f"    OK: {size:.0f} KB")
    return out_path


def concat_slide_videos(video_paths, output_path):
    """Concatenate slide videos."""
    list_path = os.path.join(SLIDE_VIDEOS_DIR, "video_list.txt")
    with open(list_path, 'w', encoding='utf-8') as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")

    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
           "-i", list_path, "-c", "copy", output_path]
    subprocess.run(cmd, capture_output=True)
    print(f"  Concatenated: {output_path}")


def merge_audio_subtitles(video_path, timing):
    """Merge video + audio + subtitles."""
    total_s = timing["total_duration_ms"] / 1000

    # Pad video to match audio length (video might be shorter due to per-slide buffering)
    video_padded = os.path.join(SLIDE_VIDEOS_DIR, "concat_padded.mp4")
    cmd_pad = [
        FFMPEG, "-y",
        "-i", video_path,
        "-t", str(total_s),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an", video_padded,
    ]
    subprocess.run(cmd_pad, capture_output=True)
    print(f"  Padded video to {total_s:.1f}s")

    # Merge with audio
    cmd = [
        FFMPEG, "-y",
        "-i", video_padded,
        "-i", AUDIO_FILE,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        VIDEO_FINAL,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Merge error: {result.stderr[-200:]}")
        return False

    size = os.path.getsize(VIDEO_FINAL) / (1024 * 1024)
    print(f"  Final: {VIDEO_FINAL} ({size:.1f} MB)")
    return True


def restore_html():
    """Restore HTML template."""
    with open(HTML_TEMPLATE, 'r', encoding='utf-8') as f:
        html = f.read()
    match = re.search(r'const TTS_TIMING = \[.*?\];', html, re.DOTALL)
    if match:
        html = html.replace(match.group(), "const TTS_TIMING = null;")
    # Also remove display:none from slides
    html = html.replace('style="display:none"', '')
    with open(HTML_TEMPLATE, 'w', encoding='utf-8') as f:
        f.write(html)
    print("  Restored HTML template")


def main():
    with open(TIMING_JSON, 'r', encoding='utf-8') as f:
        timing = json.load(f)

    print("=== 1. Generate per-slide HTML + capture ===")
    slide_videos = []
    for i in range(5):
        html_path, dur_ms = generate_single_slide_html(i, timing)
        video_path = capture_slide(i, html_path, dur_ms)
        if video_path:
            slide_videos.append(video_path)
        else:
            print(f"  Slide {i+1} failed!")
            return

    print("\n=== 2. Concatenate slide videos ===")
    concat_path = os.path.join(SLIDE_VIDEOS_DIR, "concat.mp4")
    concat_slide_videos(slide_videos, concat_path)

    print("\n=== 3. Merge with audio ===")
    merge_audio_subtitles(concat_path, timing)

    print("\n=== 4. Restore HTML ===")
    restore_html()

    print(f"\n=== Done! ===")
    print(f"  Video: {VIDEO_FINAL}")
    print(f"  SRT:   {SRT_FILE}")
    print(f"  Total: {timing['total_duration_ms']/1000:.1f}s")


if __name__ == "__main__":
    main()
