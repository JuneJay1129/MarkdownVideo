"""Concat intro + main + outro into final video"""
import subprocess
import os

FFMPEG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "AppData", "Local", "Programs", "Python",
                      "Python313", "Scripts", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"  # fallback to system ffmpeg


def concat_video(intro: str, main: str, outro: str, output: str,
                 target_h: int = 1970) -> str:
    """Concat 3 clips with unified resolution, return output path."""
    base = os.path.dirname(output)
    tmp = []

    for name, src in [("intro", intro), ("main", main), ("outro", outro)]:
        out = os.path.join(base, f"_norm_{name}.mp4")
        tmp.append(out)
        print(f"  Normalizing {name}...")

        if name == "main":
            subprocess.run([
                FFMPEG, "-y", "-i", src,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                out,
            ], capture_output=True)
        else:
            subprocess.run([
                FFMPEG, "-y", "-i", src,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-vf", f"pad=1080:{target_h}:0:0:black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-shortest",
                out,
            ], capture_output=True)

    # Concat
    concat_list = os.path.join(base, "_concat.txt")
    with open(concat_list, "w") as f:
        for p in tmp:
            f.write(f"file '{p}'\n")

    print("  Concatenating...")
    r = subprocess.run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output,
    ], capture_output=True, text=True)

    # Cleanup temp
    for f in tmp:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(concat_list):
        os.remove(concat_list)

    if r.returncode != 0:
        print(f"  Error: {r.stderr[-300:]}")
        return ""

    size = os.path.getsize(output) / (1024 * 1024)
    print(f"  → {output} ({size:.1f} MB)")
    return output


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 5:
        print("Usage: python concat_final.py <intro> <main> <outro> <output>")
    else:
        concat_video(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
