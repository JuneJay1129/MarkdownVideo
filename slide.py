#!/usr/bin/env python3
"""
Slide Tool — Markdown → 单文件 HTML 幻灯片
用法: python slide.py input.md [-o output.html] [-t theme]

Markdown 语法:
  ---          分页符
  +++          同页逐步显示 (reveal)
  🎤 旁白台词   每行一个，供 TTS 使用（不显示在幻灯片上）
  <!-- bg: #颜色 -->    设置当前页背景色
  <!-- theme: dark -->  设置主题 (dark/light/ocean/sunset)
  <!-- layout: title --> 布局 (title/center/lyrics/two-col)
"""

import re
import sys
import argparse
import html
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 主题定义 ──────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg": "#1a1a2e",
        "fg": "#eee",
        "accent": "#e94560",
        "subtitle": "#aaa",
        "card_bg": "rgba(255,255,255,0.06)",
        "code_bg": "#16213e",
        "slide_bg": "#1a1a2e",
    },
    "light": {
        "bg": "#fafafa",
        "fg": "#2d2d2d",
        "accent": "#e94560",
        "subtitle": "#666",
        "card_bg": "rgba(0,0,0,0.04)",
        "code_bg": "#f0f0f0",
        "slide_bg": "#fafafa",
    },
    "ocean": {
        "bg": "#0f3460",
        "fg": "#e8e8e8",
        "accent": "#00b4d8",
        "subtitle": "#90b4ce",
        "card_bg": "rgba(255,255,255,0.08)",
        "code_bg": "#162447",
        "slide_bg": "#0f3460",
    },
    "sunset": {
        "bg": "#2d132c",
        "fg": "#f5e6cc",
        "accent": "#ee4540",
        "subtitle": "#c72c41",
        "card_bg": "rgba(255,255,255,0.06)",
        "code_bg": "#3d1f3c",
        "slide_bg": "#2d132c",
    },
    "green": {
        "bg": "#1b2a1b",
        "fg": "#d4e7d4",
        "accent": "#4caf50",
        "subtitle": "#81c784",
        "card_bg": "rgba(255,255,255,0.06)",
        "code_bg": "#233023",
        "slide_bg": "#1b2a1b",
    },
}

# ── Markdown → HTML 简易解析 ─────────────────────────────

def md_inline(text):
    """行内 Markdown: **bold**, *italic*, `code`, [link](url), ![img](url)"""
    # images
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" style="max-width:90%;max-height:60vh;border-radius:12px;margin:16px auto;display:block;">', text)
    # links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" style="color:var(--accent)">\1</a>', text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # inline code
    text = re.sub(r'`([^`]+)`', r'<code style="background:var(--code-bg);padding:2px 8px;border-radius:4px;font-size:0.9em">\1</code>', text)
    # ==highlight==
    text = re.sub(r'==(.+?)==', r'<mark style="background:var(--accent);color:#fff;padding:1px 6px;border-radius:3px">\1</mark>', text)
    return text


def md_block_to_html(block):
    """将一个 Markdown 块转换为 HTML"""
    lines = block.strip().split('\n')
    html_parts = []
    in_list = False
    in_code = False
    code_lines = []

    for line in lines:
        # code block
        if line.strip().startswith('```'):
            if in_code:
                html_parts.append(f'<pre style="background:var(--code-bg);padding:20px;border-radius:12px;overflow-x:auto;text-align:left;max-width:85%;margin:16px auto"><code>{html.escape(chr(10).join(code_lines))}</code></pre>')
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append('<br>')
            continue

        # heading
        m = re.match(r'^(#{1,6})\s+(.+)', stripped)
        if m:
            level = len(m.group(1))
            text = md_inline(m.group(2))
            sizes = {1: '2.2em', 2: '1.7em', 3: '1.3em', 4: '1.1em'}
            size = sizes.get(level, '1em')
            html_parts.append(f'<h{level} style="font-size:{size};margin:12px 0">{text}</h{level}>')
            continue

        # unordered list
        m = re.match(r'^[-*]\s+(.+)', stripped)
        if m:
            if not in_list:
                html_parts.append('<ul style="text-align:left;max-width:70%;margin:0 auto;padding-left:24px">')
                in_list = True
            html_parts.append(f'<li style="margin:8px 0;font-size:1.1em">{md_inline(m.group(1))}</li>')
            continue

        # ordered list
        m = re.match(r'^\d+\.\s+(.+)', stripped)
        if m:
            if not in_list:
                html_parts.append('<ul style="text-align:left;max-width:70%;margin:0 auto;padding-left:24px;list-style:decimal">')
                in_list = True
            html_parts.append(f'<li style="margin:8px 0;font-size:1.1em">{md_inline(m.group(1))}</li>')
            continue

        # separator line (---  or ***)
        if re.match(r'^[-*]{3,}$', stripped):
            html_parts.append('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.15);margin:24px auto;width:60%">')
            continue

        # quote
        if stripped.startswith('>'):
            text = md_inline(stripped.lstrip('> '))
            html_parts.append(f'<blockquote style="border-left:4px solid var(--accent);padding:12px 24px;margin:16px auto;max-width:70%;text-align:left;opacity:0.9;font-style:italic">{text}</blockquote>')
            continue

        # paragraph
        html_parts.append(f'<p style="font-size:1.2em;line-height:1.8;margin:8px 0">{md_inline(stripped)}</p>')

    if in_list:
        html_parts.append('</ul>')
    if in_code:
        html_parts.append(f'<pre style="background:var(--code-bg);padding:20px;border-radius:12px;overflow-x:auto;text-align:left;max-width:85%;margin:16px auto"><code>{html.escape(chr(10).join(code_lines))}</code></pre>')

    return '\n'.join(html_parts)


# ── 解析幻灯片 ────────────────────────────────────────────

def parse_slides(md_text):
    """
    解析 Markdown 文本为幻灯片列表
    返回: list of dict { content, bg, layout, theme, speaker_notes }

    支持 🎤 标记的旁白台词，每行一个：
      🎤 这是第一张幻灯片的旁白
      🎤 这是第二句旁白（同页）
    """
    slides_raw = re.split(r'\n---+\n', md_text)
    slides = []

    for raw in slides_raw:
        if not raw.strip():
            continue

        slide = {"content": raw, "bg": None, "layout": None, "theme": None, "speaker_notes": []}

        # 提取 🎤 旁白台词
        note_lines = []
        content_lines = []
        for line in raw.split('\n'):
            stripped = line.strip()
            if stripped.startswith('🎤'):
                note_text = stripped[1:].strip()  # 去掉 🎤 前缀
                if note_text:
                    note_lines.append(note_text)
                continue
            content_lines.append(line)

        slide["speaker_notes"] = note_lines
        raw = '\n'.join(content_lines)

        # 提取 HTML 注释指令
        bg_match = re.search(r'<!--\s*bg:\s*(.+?)\s*-->', raw)
        if bg_match:
            slide["bg"] = bg_match.group(1).strip()
            raw = raw.replace(bg_match.group(0), '')

        layout_match = re.search(r'<!--\s*layout:\s*(\w[\w-]*)\s*-->', raw)
        if layout_match:
            slide["layout"] = layout_match.group(1).strip()
            raw = raw.replace(layout_match.group(0), '')

        theme_match = re.search(r'<!--\s*theme:\s*(\w+)\s*-->', raw)
        if theme_match:
            slide["theme"] = theme_match.group(1).strip()
            raw = raw.replace(theme_match.group(0), '')

        slide["content"] = raw
        slides.append(slide)

    return slides


# ── 生成 HTML ──────────────────────────────────────────────

def build_html(slides, title="Presentation", default_theme="dark"):
    """生成完整单文件 HTML"""

    t = THEMES.get(default_theme, THEMES["dark"])

    slides_html_parts = []
    for i, s in enumerate(slides):
        content_html = md_block_to_html(s["content"])
        bg = s["bg"] or t["slide_bg"]
        layout = s["layout"] or ""
        theme_override = s["theme"]

        # layout class
        layout_class = ""
        layout_style = ""
        if layout == "title":
            layout_class = "layout-title"
        elif layout == "center":
            layout_class = "layout-center"
        elif layout == "lyrics":
            layout_class = "layout-lyrics"
        elif layout == "two-col":
            layout_class = "layout-two-col"

        # theme override per slide
        extra_vars = ""
        if theme_override and theme_override in THEMES:
            tt = THEMES[theme_override]
            extra_vars = f'--bg:{tt["bg"]};--fg:{tt["fg"]};--accent:{tt["accent"]};--subtitle:{tt["subtitle"]};--card-bg:{tt["card_bg"]};--code-bg:{tt["code_bg"]};'

        bg_style = f'background:{bg};' if bg else ''

        # Handle +++ reveal splitting
        chunks = re.split(r'\n\+{3,}\n', s["content"])
        if len(chunks) > 1:
            reveal_parts = []
            for ci, chunk in enumerate(chunks):
                chunk_html = md_block_to_html(chunk)
                if ci == 0:
                    reveal_parts.append(f'<div class="reveal-item reveal-visible">{chunk_html}</div>')
                else:
                    reveal_parts.append(f'<div class="reveal-item">{chunk_html}</div>')
            content_html = '\n'.join(reveal_parts)
        else:
            content_html = md_block_to_html(s["content"])

        slides_html_parts.append(f'''
<div class="slide {layout_class}" id="slide-{i}" style="{bg_style}{extra_vars}">
  <div class="slide-content">{content_html}</div>
  <div class="slide-number">{i+1} / {len(slides)}</div>
</div>''')

    slides_joined = '\n'.join(slides_html_parts)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;700&family=JetBrains+Mono:wght@400&display=swap');

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  :root {{
    --bg: {t["bg"]};
    --fg: {t["fg"]};
    --accent: {t["accent"]};
    --subtitle: {t["subtitle"]};
    --card-bg: {t["card_bg"]};
    --code-bg: {t["code_bg"]};
  }}

  html, body {{
    width:100%; height:100%;
    overflow:hidden;
    font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif;
    background:var(--bg);
    color:var(--fg);
  }}

  .slide {{
    position:absolute; top:0; left:0;
    width:100%; height:100%;
    display:none;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    padding:60px 80px;
    text-align:center;
    transition: opacity 0.4s ease;
  }}
  .slide.active {{ display:flex; }}

  .slide-content {{
    max-width:1000px;
    width:100%;
  }}

  .slide-number {{
    position:absolute;
    bottom:20px; right:30px;
    font-size:0.85em;
    opacity:0.4;
    font-family:'JetBrains Mono',monospace;
  }}

  /* ── 标题页布局 ── */
  .layout-title .slide-content {{
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
  }}
  .layout-title h1 {{
    font-size:3em !important;
    font-weight:700;
    margin-bottom:16px;
    background:linear-gradient(135deg, var(--accent), var(--fg));
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
  }}
  .layout-title h2, .layout-title p:first-child {{
    color:var(--subtitle);
    font-weight:300;
  }}

  /* ── 居中布局 ── */
  .layout-center {{
    justify-content:center;
    align-items:center;
  }}

  /* ── 歌词布局 ── */
  .layout-lyrics .slide-content {{
    font-size:1.8em;
    line-height:2;
    font-weight:300;
    letter-spacing:2px;
  }}
  .layout-lyrics p {{
    font-size:inherit !important;
    margin:12px 0 !important;
  }}

  /* ── 双栏布局 ── */
  .layout-two-col .slide-content {{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:40px;
    text-align:left;
  }}

  /* ── 导航提示 ── */
  .nav-hint {{
    position:fixed;
    bottom:20px; left:50%;
    transform:translateX(-50%);
    font-size:0.8em;
    opacity:0;
    transition:opacity 0.5s;
    pointer-events:none;
    color:var(--subtitle);
    font-family:'JetBrains Mono',monospace;
    z-index:100;
  }}
  .nav-hint.show {{ opacity:0.5; }}

  /* ── 进度条 ── */
  .progress {{
    position:fixed; top:0; left:0;
    height:3px;
    background:var(--accent);
    transition:width 0.3s ease;
    z-index:100;
  }}

  /* ── 列表动画 ── */
  .slide.active li {{
    animation:fadeInUp 0.4s ease forwards;
    opacity:0;
  }}
  .slide.active li:nth-child(1) {{ animation-delay:0.1s; }}
  .slide.active li:nth-child(2) {{ animation-delay:0.2s; }}
  .slide.active li:nth-child(3) {{ animation-delay:0.3s; }}
  .slide.active li:nth-child(4) {{ animation-delay:0.4s; }}
  .slide.active li:nth-child(5) {{ animation-delay:0.5s; }}
  .slide.active li:nth-child(6) {{ animation-delay:0.6s; }}

  @keyframes fadeInUp {{
    from {{ opacity:0; transform:translateY(12px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}

  /* ── 大图布局 ── */
  .slide img {{
    border-radius:12px;
    box-shadow:0 8px 32px rgba(0,0,0,0.3);
  }}

  /* ── 全屏按钮 ── */
  .fs-btn {{
    position:fixed;
    top:16px; right:16px;
    background:rgba(255,255,255,0.1);
    border:none;
    color:var(--fg);
    padding:8px 12px;
    border-radius:8px;
    cursor:pointer;
    font-size:1em;
    opacity:0.3;
    transition:opacity 0.3s;
    z-index:200;
  }}
  .fs-btn:hover {{ opacity:0.8; }}

  /* ── 逐步显示 (reveal) ── */
  .reveal-item {{
    opacity:0;
    transform:translateY(10px);
    transition:opacity 0.5s ease, transform 0.5s ease;
  }}
  .reveal-item.reveal-visible {{
    opacity:1;
    transform:translateY(0);
  }}
</style>
</head>
<body>

{slides_joined}

<div class="progress" id="progress"></div>
<div class="nav-hint" id="navHint">← → 翻页 &nbsp;|&nbsp; F 全屏 &nbsp;|&nbsp; G 跳页</div>
<button class="fs-btn" onclick="toggleFullscreen()" title="全屏 (F)">⛶</button>

<script>
(function() {{
  const slides = document.querySelectorAll('.slide');
  const total = slides.length;
  let current = 0;
  let revealIndex = -1;

  function getRevealItems(slideIdx) {{
    return slides[slideIdx].querySelectorAll('.reveal-item');
  }}

  function showReveal(slideIdx, idx) {{
    var items = getRevealItems(slideIdx);
    if (idx >= 0 && idx < items.length) {{
      requestAnimationFrame(function() {{ items[idx].classList.add('reveal-visible'); }});
    }}
  }}

  function hideAllReveals(slideIdx) {{
    var items = getRevealItems(slideIdx);
    items.forEach(function(item) {{ item.classList.remove('reveal-visible'); }});
    revealIndex = items.length > 0 ? 0 : -1;
    // immediately show the first (always-visible) item
    if (items.length > 0) {{ items[0].classList.add('reveal-visible'); revealIndex = 0; }}
  }}

  function showSlide(n) {{
    if (n < 0 || n >= total) return;
    slides[current].classList.remove('active');
    current = n;
    slides[current].classList.add('active');
    hideAllReveals(current);
    // progress bar
    document.getElementById('progress').style.width = ((current + 1) / total * 100) + '%';
    // update URL hash
    history.replaceState(null, '', '#' + (current + 1));
  }}

  function next() {{
    var items = getRevealItems(current);
    var hiddenCount = 0;
    items.forEach(function(it) {{ if (!it.classList.contains('reveal-visible')) hiddenCount++; }});
    if (hiddenCount > 0) {{
      // find next hidden item and reveal it
      for (var i = 0; i < items.length; i++) {{
        if (!items[i].classList.contains('reveal-visible')) {{
          showReveal(current, i);
          break;
        }}
      }}
    }} else {{
      showSlide(current + 1);
    }}
  }}

  function prev() {{
    // if current slide has reveal items, step back through them first
    var items = getRevealItems(current);
    if (items.length > 0) {{
      var lastRevealed = -1;
      for (var i = items.length - 1; i >= 0; i--) {{
        if (items[i].classList.contains('reveal-visible')) {{ lastRevealed = i; break; }}
      }}
      // hide the last revealed item (but keep the first one)
      if (lastRevealed > 0) {{
        items[lastRevealed].classList.remove('reveal-visible');
        return;
      }}
    }}
    showSlide(current - 1);
  }}

  // keyboard
  document.addEventListener('keydown', function(e) {{
    switch(e.key) {{
      case 'ArrowRight': case 'ArrowDown': case ' ': case 'PageDown':
        e.preventDefault(); next(); break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp':
        e.preventDefault(); prev(); break;
      case 'Home': e.preventDefault(); showSlide(0); break;
      case 'End': e.preventDefault(); showSlide(total - 1); break;
      case 'f': case 'F':
        if (!e.ctrlKey && !e.metaKey) {{ e.preventDefault(); toggleFullscreen(); }}
        break;
      case 'g': case 'G':
        e.preventDefault();
        var num = prompt('跳到第几页？ (1-' + total + ')');
        if (num && !isNaN(num)) showSlide(Math.max(0, Math.min(total - 1, parseInt(num) - 1)));
        break;
      case 'Escape':
        if (document.fullscreenElement) document.exitFullscreen();
        break;
    }}
  }});

  // click to advance (left 30% = prev, right 70% = next)
  document.addEventListener('click', function(e) {{
    if (e.target.closest('.fs-btn') || e.target.closest('a') || e.target.closest('button')) return;
    var x = e.clientX / window.innerWidth;
    if (x < 0.3) prev(); else next();
  }});

  // touch swipe
  let touchStartX = 0;
  document.addEventListener('touchstart', function(e) {{ touchStartX = e.touches[0].clientX; }});
  document.addEventListener('touchend', function(e) {{
    var dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {{ dx < 0 ? next() : prev(); }}
  }});

  // fullscreen
  window.toggleFullscreen = function() {{
    if (!document.fullscreenElement) {{
      document.documentElement.requestFullscreen().catch(function(){{}});
    }} else {{
      document.exitFullscreen();
    }}
  }};

  // show nav hint briefly
  var hint = document.getElementById('navHint');
  hint.classList.add('show');
  setTimeout(function() {{ hint.classList.remove('show'); }}, 3000);

  // init: check hash
  var hash = parseInt(location.hash.replace('#', ''));
  if (hash && hash >= 1 && hash <= total) {{
    showSlide(hash - 1);
  }} else {{
    showSlide(0);
  }}
}})();
</script>
</body>
</html>'''


# ── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Slide Tool — Markdown → 单文件 HTML 幻灯片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python slide.py demo.md                    # 生成 demo.html
  python slide.py demo.md -o slides.html     # 指定输出文件名
  python slide.py demo.md -t ocean           # 使用 ocean 主题

Markdown 语法:
  ---                     分页符
  +++                     同页逐步显示 (reveal)
  <!-- bg: #ff0000 -->    设置背景色
  <!-- layout: title -->  标题页布局
  <!-- layout: lyrics --> 歌词翻页布局
  <!-- theme: sunset -->  切换主题
        """
    )
    parser.add_argument("input", help="输入的 Markdown 文件")
    parser.add_argument("-o", "--output", help="输出 HTML 文件路径")
    parser.add_argument("-t", "--theme", default="dark",
                        choices=list(THEMES.keys()),
                        help="默认主题 (默认: dark)")
    parser.add_argument("--title", help="演示标题 (默认使用文件名)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在 — {input_path}")
        sys.exit(1)

    md_text = input_path.read_text(encoding="utf-8")
    slides = parse_slides(md_text)

    if not slides:
        print("错误: 没有找到幻灯片内容 (用 --- 分隔每页)")
        sys.exit(1)

    title = args.title or input_path.stem
    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")

    html_content = build_html(slides, title=title, default_theme=args.theme)
    output_path.write_text(html_content, encoding="utf-8")

    print(f"✅ 已生成 {len(slides)} 页幻灯片 → {output_path}")
    print(f"   主题: {args.theme}")
    print(f"   双击 HTML 文件即可演示")


if __name__ == "__main__":
    main()
