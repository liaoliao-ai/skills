---
name: subtitle-generator
description: 使用火山引擎大模型录音文件极速版识别 API，将音频/视频文件转为 SRT 字幕。当用户需要生成字幕、语音转文字转字幕、给视频加字幕、音视频转 SRT 时使用。支持 WAV/MP3/OGG OPUS 格式，最长 2 小时。触发词：字幕生成、语音识别转字幕、ASR 字幕、生成 SRT、音频转字幕。
---

# 字幕生成 (Subtitle Generator)

基于火山引擎大模型录音文件极速版识别 API，一键将音频转为 SRT 字幕文件。

## 前置条件

### 1. 获取 API Key

前往 [火山引擎控制台](https://console.volcengine.com/speech) 开通语音识别服务（需开通 `volc.bigasr.auc_turbo` 权限），获取 API Key。

### 2. 配置

将 `assets/config.example.json` 复制为 `assets/config.json`，填入密钥：

```json
{
  "version": "new",
  "api_key": "你的API Key",
  "api_url": "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
  "resource_id": "volc.bigasr.auc_turbo",
  "model_name": "bigmodel"
}
```

> 旧版控制台需填 `version: "old"`、`app_key`、`access_key`。

### 用户没有 API Key 时

引导用户前往火山引擎控制台开通语音识别服务获取 Key，然后帮用户写入 `assets/config.json`。

## 使用方式

### 命令行

```bash
python scripts/generate_subtitles.py <音频路径> [-o 输出.srt] [--keep-json]
```

`--keep-json` 可同时保留原始识别结果 JSON 文件。

### AI Agent 使用流程

1. 确认 `assets/config.json` 存在且 API Key 已配置
2. 确认音频文件路径
3. 运行 `python scripts/generate_subtitles.py <音频路径> --keep-json`
4. 返回 SRT 和 JSON 文件路径

## 技术说明

- 脚本使用 **curl** 调用 API（而非 Python requests），解决部分环境 Python SSL 库与字节跳动服务器不兼容导致 `SSLEOFError` 的问题
- 请求体写入临时文件时使用 **UTF-8 无 BOM** 编码，避免 BOM 头导致 API 返回 `45000000` 错误
- 音频文件先 Base64 编码后通过 `audio.data` 字段直传

## API 限制

| 项目 | 限制 |
|------|------|
| 音频时长 | ≤ 2 小时 |
| 音频大小 | ≤ 100MB |
| 支持格式 | WAV / MP3 / OGG OPUS |
| 请求方式 | 一次请求即返回结果（无需轮询） |

## 输出行为

- **默认 SRT 模式**：生成 `.srt` 字幕文件，同时自动生成一份内容相同的 `.txt` 副本（方便用户直接查看）
- **TXT 模式**（`-f txt`）：生成纯文本无时间戳字幕
- `--keep-json`：同时保留原始识别结果 JSON

## 识别结果 → SRT 规则

- 每条 `utterance` → 一条 SRT 条目
- `start_time` / `end_time`（毫秒）→ `HH:MM:SS,mmm`
- 空文本片段自动跳过
- 序号从 1 递增
