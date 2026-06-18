# Slide Tool

> Markdown → 带动画的幻灯片视频，一条命令搞定

把 Markdown 写的幻灯片变成带 TTS 旁白、字幕、片头片尾的竖屏短视频。适合技术分享、知识科普、AI 工具介绍等内容的快速视频化。

## 效果

- **输入**: 一个 `.md` 文件（含 `🎤` 旁白标记）
- **输出**: 1080×1920 竖屏 MP4，含动画过渡 + 语音旁白 + 底部字幕
- **耗时**: 约 2 分钟（8 页幻灯片）

## 一句话流程

```
Markdown ──→ HTML 幻灯片 ──→ Playwright 录屏 ──→ TTS 语音 ──→ 字幕烧录 ──→ 最终视频
             (动画过渡)        (逐帧渲染)       (MiMo/edge)    (SRT→ASS)    (片头+内容+片尾)
```

## 快速开始

### 安装依赖

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

```markdown
# 标题

正文内容

---

## 第二页

新的一页内容
```

- `---` 分页符
- `+++` 同页逐步显示（渐进动画）
- `🎤 文字` 旁白台词（不显示在幻灯片上，供 TTS 使用）

### 布局控制

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
slide-tool/
├── generate.py        # 🚀 一键入口（读取 Markdown → 输出视频）
├── slide.py           # Markdown 解析器（语法 → 幻灯片数据）
├── baoyu.py           # HTML 生成器（幻灯片数据 → 带动画的 HTML）
├── gen_tts.py         # TTS 生成（MiMo / edge-tts + 时长计算）
├── burn_subs.py       # SRT 字幕生成
├── pw_pipeline.py     # Playwright 录屏 + 音频合并 + 字幕烧录
├── record_clips.py    # 片头片尾录制
├── concat_final.py    # 三段视频拼接（片头+内容+片尾）
├── demo.md            # 示例幻灯片
├── demo_anim.html     # 生成的动画 HTML（中间产物）
├── intro.html         # 片头模板
├── outro.html         # 片尾模板
├── mascot_logo.png    # 品牌 Logo
└── output/            # 输出目录（每次生成一个时间戳子目录）
    └── 2026-06-18 14-37-58/
        ├── final.mp4          # 最终视频
        ├── content_final.mp4  # 内容视频（无片头片尾）
        ├── tts/               # TTS 音频 + 字幕 + timing
        └── clips/             # 片头片尾
```

## 各模块详解

### slide.py — Markdown 解析器

将 Markdown 文本解析为结构化的幻灯片数据：

```python
from slide import parse_slides
slides = parse_slides(open("demo.md").read())
# → [{"title": "...", "content": [...], "layout": "title", "narration": "...", "bg": "#0f3460"}, ...]
```

支持的 content 类型：
- **heading**: 标题行
- **text**: 普通段落
- **bullet**: 列表项
- **quote**: 引用块
- **table**: 表格（自动解析 Markdown 表格语法）
- **code**: 代码块
- **image**: 图片

### baoyu.py — HTML 生成器

使用 baoyu-design 设计系统生成专业级 HTML 幻灯片：

```python
from baoyu import generate_baoyu_html
html = generate_baoyu_html(slides, title="My Deck")
```

特性：
- 内嵌 deck-stage.js 引擎（键盘导航、缩放适配、fade 过渡）
- 纯 JS 动画引擎（兼容 CDP 时间偏移录制）
- 每页：0.8s 进入动画 → 内容逐项显示 → 0.8s 退出
- CSS 自定义属性驱动主题色彩

### gen_tts.py — TTS 语音生成

双引擎 TTS，自动 fallback：

```python
from gen_tts import generate_tts
result = generate_tts(["旁白文本1", "旁白文本2"], "output/tts",
                       engine="mimo", style="东北话")
# → {"audio": "full_narration.mp3", "segments": [...], "timing": {...}, "total_duration_ms": 52000}
```

| 引擎 | 优势 | 劣势 |
|------|------|------|
| MiMo TTS | 免费、支持风格（东北话/粤语/开心等） | 偶尔超时 |
| edge-tts | 极其稳定、速度快 | 无风格控制 |

### pw_pipeline.py — 录屏 + 后期

- Playwright 录制 HTML 动画 → WebM
- ffmpeg 转 MP4 + 合并 TTS 音频
- SRT 字幕烧录（黑底白字，底部显示）

### record_clips.py / concat_final.py — 片头片尾

- 片头：品牌 Logo + "每天认识一个AI工具" + 账号名（2.5s）
- 片尾：Logo + "感谢观看" + 关注提示（2.5s）
- 分辨率自动适配：片头片尾 1080×1920，内容 1080×1970（含字幕区）

## 技术细节

### 动画时序

每页幻灯片的动画时间线：

```
|← 0.8s →|← 内容逐项显示(0.5s间隔) →|← 持续显示 →|← 0.8s →|
  进入动画                            旁白播放       退出动画
```

总时长 = Σ(旁白时长 + 2s 缓冲 + 0.8s 退出)

### CSS → JS 动画迁移

HTML 中所有动画使用纯 JS 引擎（`requestAnimationFrame` + `performance.now()`），不用 CSS `@keyframes`。原因：CSS 动画由浏览器合成器线程管理，与 CDP `setTimeOffset` 不同步，导致录屏时动画瞬间完成。

### 字幕处理

- 旁白文本按标点分割为短句（5-15 字）
- 按字数比例分配时间
- SRT 格式，12px 字体，无背景色
- Windows 路径冒号需转义（`C\:/Users/...`）

### 品牌信息

- **品牌名**: 每天认识一个AI工具
- **账号**: 一个句号的科技清单
- **Logo**: `mascot_logo.png`
- **主色调**: 紫蓝渐变 `#667eea → #764ba2`

## 输出规格

| 属性 | 值 |
|------|----|
| 分辨率 | 1080×1920（竖屏） |
| 编码 | H.264 + AAC |
| 帧率 | Playwright 默认（~30fps） |
| 文件大小 | ~5 MB（8 页，~2 分钟） |
| 输出格式 | MP4 |

## 自定义

### 修改片头片尾

编辑 `intro.html` 和 `outro.html`，替换 Logo 和文字即可。

### 修改品牌色

`intro.html` / `outro.html` 中的渐变色：
```css
background: linear-gradient(90deg, #667eea, #764ba2);
```

### 修改字幕样式

`pw_pipeline.py` 中 `burn_subtitles()` 的 `force_style` 参数：
```
FontName=SimHei, FontSize=12, PrimaryColour=&H00E8E0D0
```

### 单独使用各模块

```bash
# 只生成 HTML（不录视频）
python slide.py demo.md -o slides.html

# 只生成 TTS
python gen_tts.py tts_output "第一段旁白" "第二段旁白" --style 开心

# 只生成字幕（从 stdin 读取 JSON）
echo '[{"text":"你好","start_ms":0,"end_ms":2000}]' | python burn_subs.py output.srt

# 只录制片头片尾
python record_clips.py clips_output
```

## 已知限制

- 竖屏固定 1080×1920，不支持横屏
- MiMo TTS 偶尔超时（自动 fallback 到 edge-tts）
- 字幕样式通过 ffmpeg `force_style` 控制，修改需了解 ASS 格式
- Playwright 录屏为实时等待，长旁白会增加总耗时
- 片头片尾 CSS 动画在最终视频中可能与内容页帧率略有差异

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 运行环境 |
| playwright | latest | HTML 录屏 |
| edge-tts | 7.x | 备用 TTS |
| requests | latest | MiMo API 调用 |
| ffmpeg | 7.1+ | 音视频处理 |
