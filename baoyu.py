#!/usr/bin/env python3
"""
Baoyu Design Slide Generator
使用 baoyu-design 设计系统生成专业幻灯片 HTML
生成的 HTML 包含内嵌 deck-stage.js 引擎（键盘导航、缩放、fade 过渡、Speaker Notes）

用法:
  from slide import parse_slides
  from baoyu import generate_baoyu_html
  
  slides = parse_slides(open("demo.md").read())
  html = generate_baoyu_html(slides, title="My Deck")
  open("out.html", "w").write(html)
"""

import html as _html
import re
import json


def _md_inline(text):
    """Markdown 行内元素 → HTML"""
    t = _html.escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    return t


def _parse_features(content):
    """解析特性/要点列表"""
    items = []
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 去掉列表前缀
        line = re.sub(r'^[-*]\s+', '', line)
        line = re.sub(r'^\d+\.\s+', '', line)
        if not line:
            continue
        # 提取 emoji 图标
        emoji_match = re.match(r'^([\U0001F300-\U0001FAFF\u2600-\u27BF]+)\s*(.+)', line)
        if emoji_match:
            icon = emoji_match.group(1)
            text = emoji_match.group(2)
            # 尝试拆分 "标题 — 描述" 或 "标题: 描述"
            parts = re.split(r'\s*[—:：]\s*', text, maxsplit=1)
            title = parts[0]
            desc = parts[1] if len(parts) > 1 else ''
        else:
            icon = '•'
            parts = re.split(r'\s*[—:：]\s*', line, maxsplit=1)
            title = parts[0]
            desc = parts[1] if len(parts) > 1 else ''
        items.append((icon, title, desc))
    return items


def _slide_title(content):
    """提取标题"""
    for line in content.strip().split('\n'):
        line = line.strip()
        m = re.match(r'^#{1,3}\s+(.+)', line)
        if m:
            return _md_inline(m.group(1))
    # 没有标题则取第一行非空文本
    for line in content.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('-') and not line.startswith('*'):
            return _md_inline(line)
    return ''


def _slide_body(content):
    """提取标题之后的正文"""
    lines = content.strip().split('\n')
    body_lines = []
    found_title = False
    for line in lines:
        stripped = line.strip()
        if not found_title and re.match(r'^#{1,3}\s+', stripped):
            found_title = True
            continue
        if found_title or not re.match(r'^#{1,3}\s+', stripped):
            if stripped:
                body_lines.append(stripped)
    return '\n'.join(body_lines)


def _slide_subtitle(content):
    """提取副标题（第二个非空行）"""
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    for line in lines[1:]:
        if not line.startswith('#') and not line.startswith('-') and not line.startswith('*') and not line.startswith('<!--'):
            return _md_inline(line)
    return ''


def _render_slide_html(slide, index, total):
    """渲染单张幻灯片的 HTML"""
    content = slide['content']
    layout = slide.get('layout')
    bg = slide.get('bg')
    title = _slide_title(content)
    body = _slide_body(content)
    subtitle = _slide_subtitle(content)
    features = _parse_features(body)
    
    # 自动推断布局
    if not layout:
        if index == 0:
            layout = 'title'
        elif index == total - 1:
            layout = 'closing'
        elif len(features) >= 3:
            layout = 'features'
        elif len(features) >= 2 and all(f[2] for f in features):
            layout = 'comparison'
        else:
            layout = 'content'
    
    # 自定义背景
    bg_style = f'style="background: {bg}"' if bg else f'style="background: var(--slide-bg-{layout})"'
    
    if layout == 'title':
        return f'''
        <section class="slide" {bg_style}>
          <div class="slide-content title-layout">
            <div class="title-emoji" data-anim="0">{features[0][0] if features and features[0][0] != '•' else '🚀'}</div>
            <h1 data-anim="1">{title}</h1>
            <p class="subtitle" data-anim="2">{subtitle}</p>
            {"".join(f'<span class="tag" data-anim="{i+3}">{_md_inline(f[1])}</span>' for i, f in enumerate(features[:4]))}
          </div>
        </section>'''
    
    elif layout == 'features':
        cards_html = ''.join(
            f'''<div class="card" data-anim="{i+2}">
                  <span class="card-emoji">{icon}</span>
                  <h3>{_md_inline(title)}</h3>
                  <p>{_md_inline(desc)}</p>
                </div>'''
            for i, (icon, title, desc) in enumerate(features[:6])
        )
        return f'''
        <section class="slide" {bg_style}>
          <div class="slide-content features-layout">
            <h2 data-anim="0">{title}</h2>
            {f'<p class="lead" data-anim="1">{_md_inline(subtitle)}</p>' if subtitle else ''}
            <div class="features-grid">{cards_html}</div>
          </div>
        </section>'''
    
    elif layout == 'comparison':
        items_html = ''.join(
            f'''<div class="card" data-anim="{i+2}">
                  <span class="card-emoji">{icon}</span>
                  <h3>{_md_inline(title)}</h3>
                  <p>{_md_inline(desc)}</p>
                </div>'''
            for i, (icon, title, desc) in enumerate(features[:4])
        )
        return f'''
        <section class="slide" {bg_style}>
          <div class="slide-content features-layout">
            <h2 data-anim="0">{title}</h2>
            {f'<p class="lead" data-anim="1">{_md_inline(subtitle)}</p>' if subtitle else ''}
            <div class="features-grid">{items_html}</div>
          </div>
        </section>'''
    
    elif layout == 'closing':
        return f'''
        <section class="slide" {bg_style}>
          <div class="slide-content closing-layout">
            <h1 data-anim="0">{title}</h1>
            <p class="lead" data-anim="1">{subtitle}</p>
            <div class="cta" data-anim="2">了解更多 →</div>
          </div>
        </section>'''
    
    else:  # content / default
        # 渲染正文段落
        body_html = ''
        for line in body.split('\n'):
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'^[-*]\s+', '', line)
            line = re.sub(r'^\d+\.\s+', '', line)
            if line:
                emoji_match = re.match(r'^([\U0001F300-\U0001FAFF\u2600-\u27BF]+)\s*(.+)', line)
                if emoji_match:
                    body_html += f'<p><span class="emoji-bullet">{emoji_match.group(1)}</span> {_md_inline(emoji_match.group(2))}</p>'
                else:
                    body_html += f'<p>{_md_inline(line)}</p>'
        
        return f'''
        <section class="slide" {bg_style}>
          <div class="slide-content content-layout">
            <h2 data-anim="0">{title}</h2>
            {f'<p class="lead" data-anim="1">{_md_inline(subtitle)}</p>' if subtitle else ''}
            <div class="body-content" data-anim="2">
              {body_html}
            </div>
          </div>
        </section>'''


def generate_baoyu_html(slides, title="Presentation"):
    """
    生成 baoyu-design 风格的 HTML 幻灯片
    
    Args:
        slides: list of dict (来自 parse_slides)
        title: 幻灯片标题
    
    Returns:
        str: 完整的 HTML 字符串
    """
    total = len(slides)
    slides_html = '\n'.join(_render_slide_html(s, i, total) for i, s in enumerate(slides))
    
    # Speaker Notes JSON
    notes = []
    for s in slides:
        s_notes = s.get('speaker_notes', [])
        notes.append(' '.join(s_notes) if s_notes else '')
    notes_json = json.dumps(notes, ensure_ascii=False)
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{_html.escape(title)}</title>
<style>
/* ── Reset ── */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

/* ── baoyu-design Color Palette ── */
:root {{
  --bg-primary: #0f0f23;
  --bg-secondary: #1a1a3e;
  --bg-card: rgba(255, 255, 255, 0.08);
  --text-primary: #ffffff;
  --text-secondary: #a0a0c0;
  --accent: #00d4ff;
  --accent-warm: #ff6b6b;
  --accent-green: #4ecdc4;
  --accent-yellow: #ffd93d;
  --accent-purple: #a855f7;
  --radius: 16px;
  --radius-sm: 10px;
  
  /* Slide backgrounds per type */
  --slide-bg-title: linear-gradient(135deg, #1e3a5f 0%, #0f0f23 50%, #1a0a2e 100%);
  --slide-bg-features: linear-gradient(180deg, #0f0f23 0%, #16213e 100%);
  --slide-bg-comparison: linear-gradient(180deg, #0f0f23 0%, #1a0a2e 100%);
  --slide-bg-content: linear-gradient(180deg, #0f0f23 0%, #16213e 100%);
  --slide-bg-closing: linear-gradient(135deg, #0f0f23 0%, #1e3a5f 50%, #0f0f23 100%);
}}

html, body {{
  width: 100%;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #000;
  color: var(--text-primary);
}}

/* ── Deck Stage (baoyu-design deck-stage simplified) ── */
.deck-stage {{
  --design-w: 1920;
  --design-h: 1080;
  --s: 1;
  position: absolute;
  top: 50%;
  left: 50%;
  width: calc(var(--design-w) * 1px);
  height: calc(var(--design-h) * 1px);
  transform-origin: top left;
  transform: translate(-50%, -50%) scale(var(--s));
}}

/* ── Slide Base ── */
.slide {{
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: none;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}}

.slide.active {{
  display: flex;
}}

.slide-content {{
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 120px;
  text-align: center;
}}

/* ── Title Layout ── */
.title-layout .title-emoji {{
  font-size: 80px;
  margin-bottom: 32px;
}}

.title-layout h1 {{
  font-size: 72px;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: -1px;
}}

.title-layout .subtitle {{
  font-size: 32px;
  color: var(--text-secondary);
  margin-bottom: 40px;
}}

.title-layout .tag {{
  display: inline-block;
  background: var(--bg-card);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 999px;
  padding: 10px 24px;
  margin: 6px;
  font-size: 20px;
}}

/* ── Features / Comparison Layout ── */
.features-layout {{
  justify-content: flex-start;
  padding-top: 80px;
}}

.features-layout h2 {{
  font-size: 56px;
  font-weight: 700;
  margin-bottom: 16px;
}}

.features-layout .lead {{
  font-size: 24px;
  color: var(--text-secondary);
  margin-bottom: 48px;
}}

.features-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 28px;
  width: 100%;
  max-width: 1600px;
}}

.features-grid .card {{
  background: var(--bg-card);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius);
  padding: 36px 32px;
  text-align: left;
  transition: transform 0.2s, background 0.2s;
}}

.features-grid .card:hover {{
  transform: translateY(-4px);
  background: rgba(255,255,255,0.12);
}}

.card-emoji {{
  font-size: 40px;
  display: block;
  margin-bottom: 16px;
}}

.features-grid .card h3 {{
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 12px;
}}

.features-grid .card p {{
  font-size: 20px;
  color: var(--text-secondary);
  line-height: 1.6;
}}

/* ── Content Layout ── */
.content-layout {{
  justify-content: flex-start;
  padding-top: 80px;
}}

.content-layout h2 {{
  font-size: 56px;
  font-weight: 700;
  margin-bottom: 16px;
}}

.content-layout .lead {{
  font-size: 24px;
  color: var(--text-secondary);
  margin-bottom: 48px;
}}

.body-content {{
  text-align: left;
  max-width: 1400px;
  width: 100%;
}}

.body-content p {{
  font-size: 26px;
  line-height: 1.8;
  margin-bottom: 16px;
  color: var(--text-secondary);
}}

.body-content .emoji-bullet {{
  margin-right: 12px;
  font-size: 28px;
}}

/* ── Closing Layout ── */
.closing-layout h1 {{
  font-size: 72px;
  font-weight: 700;
  margin-bottom: 24px;
}}

.closing-layout .lead {{
  font-size: 32px;
  color: var(--text-secondary);
  margin-bottom: 48px;
}}

.closing-layout .cta {{
  display: inline-block;
  background: var(--accent);
  color: #0f0f23;
  font-weight: 600;
  font-size: 28px;
  padding: 18px 48px;
  border-radius: 999px;
  transition: transform 0.2s;
}}

.closing-layout .cta:hover {{
  transform: scale(1.05);
}}

/* ── Slide Number ── */
.slide-number {{
  position: absolute;
  bottom: 28px;
  right: 40px;
  font-size: 16px;
  color: var(--text-secondary);
  opacity: 0.6;
  font-family: 'SF Mono', 'Fira Code', monospace;
  z-index: 10;
}}

/* ── Progress Bar ── */
.progress-bar {{
  position: fixed;
  bottom: 0;
  left: 0;
  height: 4px;
  background: var(--accent);
  transition: width 0.3s ease;
  z-index: 100;
}}

/* ── Keyboard Hint ── */
.kbd-hint {{
  position: fixed;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 13px;
  color: var(--text-secondary);
  opacity: 0.4;
  z-index: 100;
  font-family: 'SF Mono', 'Fira Code', monospace;
  pointer-events: none;
}}

/* ── Animations ── */
@keyframes fadeInUp {{
  from {{ opacity: 0; transform: translateY(30px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Animation Scrub System (controlled by JS for video capture) ── */
[data-anim] {{
  opacity: 0;
  transform: translateY(30px);
}}

.slide.active [data-anim] {{
  animation: fadeInUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-play-state: paused;
}}

.slide.active [data-anim="0"] {{ animation-delay: 0s; }}
.slide.active [data-anim="1"] {{ animation-delay: 0.15s; }}
.slide.active [data-anim="2"] {{ animation-delay: 0.3s; }}
.slide.active [data-anim="3"] {{ animation-delay: 0.45s; }}
.slide.active [data-anim="4"] {{ animation-delay: 0.6s; }}
.slide.active [data-anim="5"] {{ animation-delay: 0.75s; }}
.slide.active [data-anim="6"] {{ animation-delay: 0.9s; }}
.slide.active [data-anim="7"] {{ animation-delay: 1.05s; }}

/* ── Print / Capture ── */
@media print {{
  .slide {{ display: flex !important; page-break-after: always; position: relative; }}
  .slide-number, .progress-bar, .kbd-hint {{ display: none; }}
}}
</style>
</head>
<body>

<div class="deck-stage" id="deck">
  {slides_html}
</div>

<div class="progress-bar" id="progress"></div>
<div class="kbd-hint">← → 翻页 · Space 下一页 · Home/End 首尾页</div>

<script type="application/json" id="speaker-notes">
{notes_json}
</script>

<script>
(function() {{
  const stage = document.getElementById('deck');
  const slides = stage.querySelectorAll('.slide');
  const total = slides.length;
  const progress = document.getElementById('progress');
  let current = 0;

  // Speaker Notes
  let notes = [];
  try {{
    notes = JSON.parse(document.getElementById('speaker-notes').textContent);
  }} catch(e) {{}}

  // Scaling (baoyu-design deck-stage pattern)
  function rescale() {{
    const vw = window.innerWidth, vh = window.innerHeight;
    const dw = 1920, dh = 1080;
    const s = Math.min(vw / dw, vh / dh);
    stage.style.setProperty('--s', s);
    stage.style.top = (vh - dh * s) / 2 + 'px';
    stage.style.left = (vw - dw * s) / 2 + 'px';
    stage.style.transform = 'scale(' + s + ')';
    stage.style.transformOrigin = 'top left';
  }}

  function showSlide(i) {{
    slides.forEach(function(s) {{ s.classList.remove('active'); }});
    slides[i].classList.add('active');
    // 更新 slide number
    slides[i].querySelectorAll('.slide-number').forEach(function(el) {{ el.remove(); }});
    var num = document.createElement('div');
    num.className = 'slide-number';
    num.textContent = (i + 1) + ' / ' + total;
    slides[i].appendChild(num);
    // 更新进度条
    progress.style.width = ((i + 1) / total * 100) + '%';
    current = i;
  }}

  function goNext() {{
    if (current < total - 1) showSlide(current + 1);
  }}

  function goPrev() {{
    if (current > 0) showSlide(current - 1);
  }}

  // Keyboard navigation
  document.addEventListener('keydown', function(e) {{
    switch(e.key) {{
      case 'ArrowRight':
      case 'ArrowDown':
      case ' ':
        e.preventDefault(); goNext(); break;
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault(); goPrev(); break;
      case 'Home':
        e.preventDefault(); showSlide(0); break;
      case 'End':
        e.preventDefault(); showSlide(total - 1); break;
    }}
  }});

  // Public API (Playwright can call these)
  window.deckApi = {{
    goTo: function(i) {{ if (i >= 0 && i < total) showSlide(i); }},
    next: goNext,
    prev: goPrev,
    reset: function() {{ showSlide(0); }},
    getIndex: function() {{ return current; }},
    getLength: function() {{ return total; }},
    getNotes: function() {{ return notes; }},
    getNote: function(i) {{ return (notes[i] || '').trim(); }},
    // Animation scrub: set all [data-anim] elements to a specific time point
    scrubTo: function(slideIndex, timeMs) {{
      if (slideIndex >= 0 && slideIndex < total) {{
        showSlide(slideIndex);
        var slide = slides[slideIndex];
        var elems = slide.querySelectorAll('[data-anim]');
        elems.forEach(function(el) {{
          el.style.animationPlayState = 'paused';
          el.style.animationDelay = (-timeMs / 1000) + 's';
        }});
      }}
    }},
    // Reset animations to default state
    resetAnims: function() {{
      var slide = slides[current];
      var elems = slide.querySelectorAll('[data-anim]');
      elems.forEach(function(el) {{
        el.style.animationPlayState = '';
        el.style.animationDelay = '';
      }});
    }}
  }};

  // Init
  rescale();
  window.addEventListener('resize', rescale);
  showSlide(0);
}})();
</script>
</body>
</html>'''


if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # 简单的命令行入口：python baoyu.py input.md [-o output.html]
    if len(sys.argv) < 2:
        print("用法: python baoyu.py input.md [-o output.html]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = None
    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not output_file:
        output_file = str(Path(input_file).with_suffix('.html'))
    
    # 导入 slide.py 的解析器
    sys.path.insert(0, str(Path(__file__).parent))
    from slide import parse_slides
    
    md_text = Path(input_file).read_text(encoding='utf-8')
    slides = parse_slides(md_text)
    html = generate_baoyu_html(slides, title=Path(input_file).stem)
    
    Path(output_file).write_text(html, encoding='utf-8')
    print(f"✅ 生成: {output_file} ({len(slides)} 页)")
