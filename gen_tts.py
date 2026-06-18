"""
gen_tts.py — TTS + timing 生成
支持 edge-tts 和 MiMo TTS（默认 MiMo 东北话）
调用 generate_tts(narration_texts, output_dir) 返回结果 dict
"""
import base64
import json
import os
import re
import subprocess
import time

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(BASE, "..", "..", "AppData", "Local", "Programs",
                      "Python", "Python313", "Scripts", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

# MiMo TTS config
MIMO_KEY = "tp-ci8q121wuwc8f24qws2xhtbic208oav8t67okgnhsik74627"
MIMO_URL = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
MIMO_MODEL = "mimo-v2.5-tts"
MIMO_VOICE = "mimo_default"

# edge-tts config
EDGE_VOICE = "zh-CN-YunxiNeural"

# Timing constants (ms)
SLIDE_IN = 800
SLIDE_OUT = 1000
HOLD = 2000


def _get_duration(mp3_path: str) -> int:
    """Get audio duration in ms using ffmpeg."""
    r = subprocess.run([FFMPEG, "-i", mp3_path, "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', r.stderr)
    if m:
        return int(m[1])*3600000 + int(m[2])*60000 + int(m[3])*1000 + int(m[4])*10
    return 5000


def _mimo_tts(text: str, style: str, out_path: str) -> bool:
    """Call MiMo TTS API, save audio to out_path. Returns True on success."""
    headers = {
        "Authorization": f"Bearer {MIMO_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MIMO_MODEL,
        "messages": [
            {"role": "assistant", "content": f"<style>{style}</style>{text}"},
            {"role": "user", "content": f"用{style}风格朗读"},
        ],
        "audio": {
            "format": "mp3",
            "voice": MIMO_VOICE,
        },
    }
    try:
        r = requests.post(MIMO_URL, headers=headers, json=payload, timeout=30)
        if r.status_code != 200:
            print(f"    MiMo API error {r.status_code}: {r.text[:200]}")
            return False
        data = r.json()
        audio_data = data["choices"][0]["message"].get("audio", {}).get("data", "")
        if not audio_data:
            print("    MiMo returned empty audio")
            return False
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(audio_data))
        return True
    except Exception as e:
        print(f"    MiMo error: {e}")
        return False


def _edge_tts(text: str, out_path: str) -> bool:
    """Call edge-tts, save audio to out_path. Returns True on success."""
    import asyncio
    import edge_tts
    try:
        async def _gen():
            comm = edge_tts.Communicate(text, EDGE_VOICE)
            await comm.save(out_path)
        asyncio.run(_gen())
        return True
    except Exception as e:
        print(f"    edge-tts error: {e}")
        return False


def _generate_one(text: str, style: str, out_path: str, engine: str = "mimo") -> bool:
    """Generate TTS for one text, try MiMo first, fallback to edge-tts."""
    if engine == "mimo":
        ok = _mimo_tts(text, style, out_path)
        if ok:
            return True
        print("    Falling back to edge-tts...")
        return _edge_tts(text, out_path)
    else:
        return _edge_tts(text, out_path)


def generate_tts(texts: list[str], output_dir: str,
                 engine: str = "mimo", style: str = "东北话") -> dict:
    """
    Generate TTS for all texts, return result dict.
    
    engine: "mimo" or "edge"
    style: MiMo style prompt (e.g. "东北话", "开心", "粤语", "悄悄话")
    """
    os.makedirs(output_dir, exist_ok=True)
    audio_files = []
    durations = []

    for i, text in enumerate(texts):
        out_path = os.path.join(output_dir, f"slide_{i+1}.mp3")
        print(f"  Slide {i+1} ({engine}, style={style})...")
        ok = _generate_one(text, style, out_path, engine)
        if not ok:
            print(f"    Failed for slide {i+1}, skipping")
            continue
        dur_ms = _get_duration(out_path)
        durations.append(dur_ms)
        audio_files.append(out_path)
        print(f"    {dur_ms/1000:.1f}s")
        if engine == "mimo":
            time.sleep(0.5)  # rate limit

    if not audio_files:
        return {"audio": "", "segments": [], "timing": {}, "total_duration_ms": 0, "durations_ms": []}

    # Build segments with timing
    segments = []
    offset_ms = 0
    for i, text in enumerate(texts):
        if i >= len(durations):
            break
        # Split text into sentences for subtitle segments
        parts = re.split(r'(。|！|？|；|，|：)', text)
        chunks = []
        for j in range(0, len(parts) - 1, 2):
            s = (parts[j] + parts[j+1]).strip()
            if s:
                chunks.append(s)
        if len(parts) % 2 == 1 and parts[-1].strip():
            chunks.append(parts[-1].strip())
        # Merge short chunks
        merged = []
        for c in chunks:
            if merged and len(c) < 6:
                merged[-1] += c
            else:
                merged.append(c)
        merged = [re.sub(r'[，。！？；：、]$', '', c).strip() for c in merged]
        merged = [c for c in merged if c]

        # Distribute time proportionally
        total_chars = sum(len(c) for c in merged) or 1
        local_offset = 0
        for chunk in merged:
            ratio = len(chunk) / total_chars
            chunk_dur = int(durations[i] * ratio)
            segments.append({
                "text": chunk,
                "start_ms": offset_ms + local_offset,
                "end_ms": offset_ms + local_offset + chunk_dur,
            })
            local_offset += chunk_dur
        offset_ms += durations[i]

    # Concat audio
    list_path = os.path.join(output_dir, "audio_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")
    full_audio = os.path.join(output_dir, "full_narration.mp3")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
                    "-i", list_path, "-c", "copy", full_audio],
                   capture_output=True)

    # Build timing for animation
    slides_timing = []
    anim_offset = 0
    for i, dur in enumerate(durations):
        slides_timing.append({
            "enterStart": anim_offset,
            "childrenStart": anim_offset + SLIDE_IN,
            "exitStart": anim_offset + dur + HOLD,
            "exitEnd": anim_offset + dur + HOLD + SLIDE_OUT,
        })
        anim_offset += dur + HOLD + SLIDE_OUT

    timing = {
        "total_duration_ms": anim_offset,
        "slides": slides_timing,
        "durations_ms": durations,
    }
    timing_path = os.path.join(output_dir, "timing.json")
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing, f, indent=2, ensure_ascii=False)

    # Cleanup
    if os.path.exists(list_path):
        os.remove(list_path)

    return {
        "audio": full_audio,
        "segments": segments,
        "timing": timing,
        "total_duration_ms": anim_offset,
        "durations_ms": durations,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python gen_tts.py <output_dir> <text1> [text2] ...")
        print("Options: --engine mimo|edge --style 东北话|开心|粤语|悄悄话")
    else:
        engine = "mimo"
        style = "东北话"
        args = sys.argv[1:]
        if "--engine" in args:
            idx = args.index("--engine")
            engine = args[idx + 1]
            args = args[:idx] + args[idx+2:]
        if "--style" in args:
            idx = args.index("--style")
            style = args[idx + 1]
            args = args[:idx] + args[idx+2:]
        out_dir = args[0]
        texts = args[1:]
        result = generate_tts(texts, out_dir, engine=engine, style=style)
        print(f"\nAudio: {result['audio']}")
        print(f"Duration: {result['total_duration_ms']/1000:.1f}s")
