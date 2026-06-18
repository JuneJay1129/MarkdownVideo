"""
generate.py — 一键生成视频
用法: python generate.py <markdown文件路径>

输出: output/<timestamp>/ 下的所有文件
  ├── slides/          幻灯片截图
  ├── tts/             TTS 音频 + 字幕
  ├── clips/           片头/片尾 mp4
  ├── content.webm     录制的原始视频
  ├── content_merged.mp4  合并音频后的视频
  ├── content_final.mp4   烧录字幕后的视频
  └── final.mp4          最终完整视频（含片头片尾）
"""
import json
import os
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


def get_output_dir() -> str:
    """Create timestamped output directory."""
    ts = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    out = os.path.join(BASE, "output", ts)
    os.makedirs(out, exist_ok=True)
    return out


def run_pipeline(md_path: str):
    from gen_tts import generate_tts
    from burn_subs import generate_srt
    from pw_pipeline import record_content, merge_audio, burn_subtitles
    from record_clips import record_clips
    from concat_final import concat_video

    output_dir = get_output_dir()
    tts_dir = os.path.join(output_dir, "tts")
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(tts_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    html_path = os.path.join(BASE, "demo_anim.html")
    timing_json = os.path.join(tts_dir, "timing.json")
    audio_file = os.path.join(tts_dir, "full_narration.mp3")
    srt_file = os.path.join(tts_dir, "subtitles.srt")
    content_webm = os.path.join(output_dir, "content.webm")
    content_mp4 = os.path.join(output_dir, "content_merged.mp4")
    content_sub = os.path.join(output_dir, "content_final.mp4")
    final_mp4 = os.path.join(output_dir, "final.mp4")

    print(f"输出目录: {output_dir}\n")

    # Step 1: TTS
    print("=== 1. 生成 TTS ===")
    with open(md_path, "r", encoding="utf-8") as f:
        narration = [line.strip().lstrip("🎤 ").strip()
                     for line in f if line.strip().startswith("🎤")]
    if not narration:
        print("  错误: 没有找到 🎤 标记的旁白文本")
        return

    tts_result = generate_tts(narration, tts_dir)
    print(f"  音频: {tts_result['audio']}")
    print(f"  时长: {tts_result['total_duration_ms']/1000:.1f}s")

    # Step 2: SRT
    print("\n=== 2. 生成字幕 ===")
    generate_srt(tts_result["segments"], srt_file)
    print(f"  → {srt_file}")

    # Step 3: Record content
    print("\n=== 3. 录制内容 ===")
    webm = record_content(html_path, timing_json, output_dir)
    if not webm:
        print("  录制失败")
        return

    # Step 4: Merge audio + burn subtitles
    print("\n=== 4. 合并音频 + 字幕 ===")
    merge_audio(webm, audio_file, content_mp4, tts_result["total_duration_ms"])
    burn_subtitles(content_mp4, srt_file, content_sub)

    # Step 5: Record intro & outro
    print("\n=== 5. 录制片头片尾 ===")
    intro, outro = record_clips(clips_dir)

    # Step 6: Concat final
    print("\n=== 6. 拼接最终视频 ===")
    concat_video(intro, content_sub, outro, final_mp4)

    # Cleanup intermediate files
    for f in [content_webm, content_mp4]:
        if os.path.exists(f):
            os.remove(f)

    print(f"\n{'='*40}")
    print(f"✅ 完成!")
    print(f"  最终视频: {final_mp4}")
    print(f"  字幕:    {srt_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate.py <markdown文件>")
        print("示例: python generate.py demo.md")
        sys.exit(1)

    md = sys.argv[1]
    if not os.path.isabs(md):
        md = os.path.join(BASE, md)

    if not os.path.exists(md):
        print(f"文件不存在: {md}")
        sys.exit(1)

    run_pipeline(md)
