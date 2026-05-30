# 豆包语音合成 API 参考

> 来源: https://www.volcengine.com/docs/6561/1598757

## 概述

火山引擎豆包语音合成大模型，支持多语种、多方言的文本转语音（TTS）。

### 可用接口

| 接口 | 协议 | 场景 |
|------|------|------|
| `/api/v3/tts/unidirectional` | HTTP Chunked | 一次性输入文本，流式输出音频 |
| `/api/v3/tts/unidirectional/sse` | HTTP SSE | 一次性输入文本，SSE 流式输出 |

## 鉴权（新版控制台）

| Header | 说明 | 必填 |
|--------|------|------|
| `X-Api-Key` | 火山引擎控制台获取的 API Key | ✅ |
| `X-Api-Resource-Id` | 资源 ID，决定模型版本和计费 | ✅ |
| `X-Api-Request-Id` | 请求 ID（UUID），可选 | ❌ |

### Resource ID 取值

**语音合成：**
- `seed-tts-2.0` — 模型 2.0（推荐）
- `seed-tts-1.0` — 模型 1.0（字符版）
- `seed-tts-1.0-concurr` — 模型 1.0（并发版）

**声音复刻：**
- `seed-icl-2.0` — 复刻 2.0
- `seed-icl-1.0` — 复刻 1.0（字符版）
- `seed-icl-1.0-concurr` — 复刻 1.0（并发版）

## 请求 Body

```json
{
    "user": {"uid": "任意用户标识"},
    "req_params": {
        "text": "合成文本",
        "speaker": "发音人 ID",
        "audio_params": {
            "format": "mp3",
            "sample_rate": 24000
        }
    }
}
```

### 核心参数

| 字段 | 说明 | 必填 |
|------|------|------|
| `req_params.text` | 合成文本 | ✅ |
| `req_params.speaker` | 发音人 ID（见发音人列表） | ✅ |
| `req_params.audio_params.format` | `mp3` / `ogg_opus` / `pcm` | ❌ (默认 mp3) |
| `req_params.audio_params.sample_rate` | 8000/16000/22050/24000/32000/44100/48000 | ❌ (默认 24000) |

### 可选参数

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `req_params.audio_params.emotion` | 情感（仅部分音色支持） | — |
| `req_params.audio_params.emotion_scale` | 情绪值 1~5 | 4 |
| `req_params.audio_params.speech_rate` | 语速 [-50,100] | 0 |
| `req_params.audio_params.loudness_rate` | 音量 [-50,100] | 0 |
| `req_params.additions.silence_duration` | 句尾静音 0~30000ms | 0 |
| `req_params.additions.disable_markdown_filter` | 关闭 Markdown 过滤 | false |
| `req_params.additions.post_process.pitch` | 音调 [-12,12] | 0 |

## 响应格式

### HTTP Chunked

每行一个 JSON，最后以 `code: 20000000` 结束：

```json
{"code":0,"message":"","data":"<base64 音频>"}
{"code":20000000,"message":"ok","data":null}
```

### SSE

```text
event: 352
data: {"code":0,"message":"","data":"<base64 音频>"}

event: 152
data: {"code":20000000,"message":"OK","data":null}
```

## 错误码

| Code | 说明 |
|------|------|
| 20000000 | 合成完成 |
| 40402003 | 文本超长 |
| 45000000 | 音色鉴权失败 |
| 55000000 | 服务端错误 |

## 发音人列表参考

完整列表见: https://www.volcengine.com/docs/6561/1327395

常用音色示例：
- `zh_female_shuangkuaisisi_moon_bigtts` — 爽快思思（女声）
- `zh_male_bvlazysheep` — 懒羊羊（男声）
- `BV120_streaming` — 通用女声
- `zh_female_vv_uranus_bigtts` — VV（女声，支持方言）
- `zh_male_ahu_conversation_wvae_bigtts` — 阿虎（男声）
