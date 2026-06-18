# Slide Tool 🎬

Markdown → HTML slides → TTS → 字幕 → 视频 一键生成工具

## 项目结构

```
slide-tool/
├── generate.py        # 🚀 主入口：一键生成完整视频
├── baoyu.py           # 幻灯片 HTML 生成（baoyu-design 风格）
├── slide.py           # Markdown → HTML slides（通用主题）
├── gen_tts.py         # TTS 语音生成（edge-tts）+ timing
├── burn_subs.py       # SRT 字幕生成
├── pw_pipeline.py     # Playwright 录制 + 音频合并 + 字幕烧录
├── record_clips.py    # 片头/片尾录制
├── concat_final.py    # 片头 + 内容 + 片尾拼接
├── pipeline.py        # 旧版管线（待清理）
├── demo.md            # 示例 Markdown 源文件
├── demo_anim.html     # 示例幻灯片 HTML
├── intro.html         # 固定片头模板
├── outro.html         # 固定片尾模板
├── mascot_logo.png    # 品牌 Logo
└── examples/          # 示例文件
```

## 使用方式

### 一键生成

```bash
python generate.py demo.md
```

输出到 `output/<时间戳>/` 目录：
```
output/2026-06-18 14-30-00/
├── tts/                  TTS 音频 + timing
├── clips/                片头/片尾 mp4
├── content_merged.mp4    合并音频后的视频
├── content_final.mp4     烧录字幕后的视频
└── final.mp4             最终完整视频
```

### Markdown 格式

```markdown
# 第一页标题
🎤 这里是第一页的旁白文本，会生成 TTS 语音

正文内容...

---
# 第二页标题
🎤 第二页的旁白文本

正文内容...
```

- `🎤` 标记的行提取为 TTS 旁白
- `---` 分隔不同页面

## 依赖

- Python 3.13+
- edge-tts (`pip install edge-tts`)
- playwright (`pip install playwright && playwright install chromium`)
- ffmpeg (系统 PATH 或指定路径)

## 固定片头片尾

`intro.html` 和 `outro.html` 是固定模板，不需要根据内容修改：
- 品牌：每天认识一个AI工具
- 账号：一个句号的科技清单
- Logo：mascot_logo.png
