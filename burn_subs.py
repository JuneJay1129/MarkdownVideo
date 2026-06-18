"""
burn_subs.py — SRT 字幕生成
调用 generate_srt(segments, srt_path) 生成 SRT 文件
segments: [{"text": str, "start_ms": int, "end_ms": int}, ...]
"""
import os


def _ms_to_srt(ms: int) -> str:
    h, r = divmod(ms, 3600000)
    m, r = divmod(r, 60000)
    s, ms_r = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_r:03d}"


def generate_srt(segments: list[dict], srt_path: str) -> str:
    """Write SRT file from segments, return path."""
    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{_ms_to_srt(seg['start_ms'])} --> {_ms_to_srt(seg['end_ms'])}\n")
            f.write(f"{seg['text']}\n\n")
    return srt_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python burn_subs.py <srt_path> (reads segments from stdin JSON)")
    else:
        import json
        segments = json.load(sys.stdin)
        generate_srt(segments, sys.argv[1])
        print(f"Written {len(segments)} entries to {sys.argv[1]}")
