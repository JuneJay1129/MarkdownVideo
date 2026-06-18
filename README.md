# MarkdownVideo

> Markdown 转视频 — 写好 Markdown，一条命令生成带旁白、字幕、动画的短视频

把 Markdown 写的幻灯片变成 1080×1920 竖屏 MP4，自带 TTS 语音旁白、动画过渡、字幕和片头片尾。适合技术分享、知识科普、AI 工具介绍等内容的快速视频化。

## 效果

- **输入**: 一个 `.md` 文件（用 `🎤` 标记旁白台词）
- **输出**: 1080×1920 竖屏 MP4，含动画 + 语音 + 字幕
- **耗时**: 约 2 分钟（8 页幻灯片）

## 流程

```
Markdown → HTML 幻灯片 → Playwright 录屏 → TTS 语音 → 字幕烧录 → 最终视频
           (动画过渡)      (逐帧渲染)      (MiMo/edge)  (SRT→ASS)   (片头+内容+片尾)
```

## 快速开始

### 安装

```bash
pip install playwright edge-tts requests
playwright install chromium
```

还需要 ffmpeg（Python 包 `imageio-ffmpeg` 自带，或系统安装）。

### 生成视频

```bash
python generate.py demo.md
```

输出在 `output/<timestamp>/final.mp4`。

### 命令行参数

```bash
python generate.py demo.md                        # 默认 MiMo TTS 东北话
python generate.py demo.md --engine edge           # 用 edge-tts
python generate.py demo.md --style 开心            # MiMo 开心风格
python generate.py demo.md --engine edge --voice zh-CN-XiaoxiaoNeural
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--engine` | `mimo` | TTS 引擎：`mimo`（免费，支持风格）或 `edge`（稳定） |
| `--style` | `东北话` | MiMo 风格：`东北话`、`开心`、`粤语`、`悄悄话` 等 |
| `--voice` | `zh-CN-YunxiNeural` | edge-tts 语音（仅 edge 引擎生效） |

## Markdown 语法

### 基本结构

- `---` 分页符
- `+++` 同页逐步显示（渐进动画）
- `🎤 文字` 旁白台词（不显示在幻灯片上，供 TTS 使用）

### 布局

```markdown
<!-- layout: title -->    大标题居中（首页）
<!-- layout: center -->   内容居中
<!-- layout: two-col -->  左右两栏
<!-- layout: lyrics -->   大字歌词风
```

### 主题与背景

```markdown
<!-- theme: dark -->      深色主题（dark / light / ocean / sunset）
<!-- bg: #0f3460 -->      当前页背景色（覆盖主题默认）
```

### 完整示例

```markdown
<!-- layout: title -->
<!-- bg: #0f3460 -->

# AI 时代的效率革命

## 从工具使用者到 AI 协作者

🎤 大家好！今天咱唠唠 AI 时代咋整才能效率翻倍！

---

## 🤔 核心观点

> 把 AI 当作**副驾驶**，而不是替代品

+++

- 🎯 人负责**决策**，AI 负责**执行**

+++

- ⚡ 效率提升 10 倍不是梦

🎤 核心就一句话：把AI当副驾驶，别当替代品！
```

## 项目结构

```
├── generate.py        # 一键入口（Markdown → 视频）
├── slide.py           # Markdown 解析器
├── baoyu.py           # HTML 幻灯片生成器
├── gen_tts.py         # TTS 语音生成（MiMo / edge-tts）
├── burn_subs.py       # SRT 字幕生成
├── pw_pipeline.py     # Playwright 录屏 + 音频合并 + 字幕烧录
├── record_clips.py    # 片头片尾录制
├── concat_final.py    # 视频拼接
├── demo.md            # 示例幻灯片
├── intro.html         # 片头模板
├── outro.html         # 片尾模板
├── mascot_logo.png    # 品牌 Logo
└── output/            # 输出目录
```

## 各模块

### slide.py — Markdown 解析器

```python
from slide import parse_slides
slides = parse_slides(open("demo.md").read())
# → [{"title": "...", "content": [...], "layout": "title", "narration": "...", "bg": "#0f3460"}, ...]
```

支持 content 类型：heading、text、bullet、quote、table、code、image

### baoyu.py — HTML 生成器

```python
from baoyu import generate_baoyu_html
html = generate_baoyu_html(slides, title="My Deck")
```

- 内嵌 deck-stage.js 引擎（键盘导航、缩放适配、fade 过渡）
- 纯 JS 动画引擎（兼容 CDP 时间偏移录制）
- 每页：0.8s 进入 → 内容逐项显示 → 0.8s 退出

### gen_tts.py — TTS 语音

```python
from gen_tts import generate_tts
result = generate_tts(["旁白1", "旁白2"], "output/tts", engine="mimo", style="东北话")
```

| 引擎 | 优势 | 劣势 |
|------|------|------|
| MiMo TTS | 免费、支持风格（东北话/粤语/开心等） | 偶尔超时 |
| edge-tts | 极其稳定、速度快 | 无风格控制 |

### pw_pipeline.py — 录屏 + 后期

- Playwright 录制 HTML 动画 → WebM
- ffmpeg 转 MP4 + 合并 TTS 音频
- SRT 字幕烧录

### record_clips.py / concat_final.py — 片头片尾

- 片头：品牌 Logo + "每天认识一个AI工具" + 账号名（2.5s）
- 片尾：Logo + "感谢观看" + 关注提示（2.5s）
- 片头片尾 1080×1920，内容 1080×1970（含字幕区）

## 技术细节

### 动画时序

```
|← 0.8s →|← 内容逐项显示(0.5s间隔) →|← 持续显示 →|← 0.8s →|
  进入动画                            旁白播放       退出动画
```

### CSS → JS 动画

HTML 中所有动画使用纯 JS 引擎（`requestAnimationFrame` + `performance.now()`），不用 CSS `@keyframes`。原因：CSS 动画由浏览器合成器线程管理，与 CDP `setTimeOffset` 不同步，录屏时动画会瞬间完成。

### 字幕处理

- 旁白按标点分割为短句（5-15 字），按字数比例分配时间
- SRT 格式，12px 字体

## 输出规格

| 属性 | 值 |
|------|----|
| 分辨率 | 1080×1920（竖屏） |
| 编码 | H.264 + AAC |
| 文件大小 | ~5 MB（8 页，~2 分钟） |
| 输出格式 | MP4 |

## 自定义

### 片头片尾

编辑 `intro.html` 和 `outro.html`，替换 Logo 和文字。

### 品牌色

`intro.html` / `outro.html` 中的渐变色：
```css
background: linear-gradient(90deg, #667eea, #764ba2);
```

### 字幕样式

`pw_pipeline.py` 中 `burn_subtitles()` 的 `force_style` 参数：
```
FontName=SimHei, FontSize=12, PrimaryColour=&H00E8E0D0
```

### 单独使用各模块

```bash
python slide.py demo.md -o slides.html                          # 只生成 HTML
python gen_tts.py tts_output "旁白1" "旁白2" --style 开心       # 只生成 TTS
python record_clips.py clips_output                              # 只录制片头片尾
```

## 已知限制

- 竖屏固定 1080×1920，不支持横屏
- MiMo TTS 偶尔超时（自动 fallback 到 edge-tts）
- Playwright 录屏为实时等待，长旁白会增加总耗时

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 运行环境 |
| playwright | latest | HTML 录屏 |
| edge-tts | 7.x | 备用 TTS |
| requests | latest | MiMo API 调用 |
| ffmpeg | 7.1+ | 音视频处理 |
