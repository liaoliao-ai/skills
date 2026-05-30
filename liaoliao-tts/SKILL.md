---
name: doubao-tts
description: >
  豆包语音合成（火山引擎 TTS）—— 文本转语音。当用户需要将文字转成语音、合成配音、生成朗读音频时使用。
  触发场景：(1) 用户要求文字转语音/合成配音/TTS，(2) 用户提到"豆包语音合成"、"火山引擎 TTS"、"语音合成"，
  (3) 用户需要为视频生成配音/旁白，(4) 用户需要读取文本朗读。
---

# 豆包语音合成 TTS

使用火山引擎豆包语音合成大模型 API，将文字转为自然语音。

## 快速开始

```bash
python scripts/tts.py synthesize --text "要合成的文本" --speaker <发音人ID>
```

---

## 🚨 铁律：发音人必须让用户选择

**此规则优先级最高，违反即为重大失误。**

合成语音前，AI 必须判断用户意图，精确落入以下三档之一：

| 用户行为 | AI 应对 | 示例 |
|---------|--------|------|
| 用户**明确指定**了音色名称或 ID | 直接合成 | "用鸡汤女"、"voice_type: xxx" |
| 用户说**"自动选"/"随便"/"默认"**等 | 自动选一个，告知用户所选，直接合成 | "随便吧"、"默认的就行" |
| **以上两档都不满足** | **绝对禁止合成。必须停下，展示 10 个推荐音色，等用户选。** | "语音合成这段话"（没说用哪个音色） |

**严禁以下行为：**
- ❌ 用户没说用哪个音色，AI 自己挑一个已保存音色就合成了
- ❌ 用户没说"自动"，AI 以"已保存音色就一个，我帮你选了"为由直接合成
- ❌ 以任何理由跳过音色选择交互步骤

**处置：** 违规一次需向用户承认失误，并立即更新此技能将该条红线更醒目。

---

## 工作流程

### 1. 检查配置

首次使用时，运行以下命令检查状态：

```bash
python scripts/tts.py config
```

返回 JSON，含 `has_api_key`（是否已配置 API Key）和 `speakers`（已保存的发音人列表）。

### 2. 配置 API Key（仅在未配置时）

如果 `has_api_key` 为 false，向用户询问火山引擎 API Key。用户可从 https://console.volcengine.com/ 的 API Key 管理获取。

```bash
python scripts/tts.py config --api-key "用户提供的key"
```

API Key 保存在 `assets/config.json`，后续可随时用同样命令更新。

### 3. 管理发音人

#### 查看已保存的发音人

```bash
python scripts/tts.py config --speaker list
```

返回 `speakers` 数组，每项含 `id` 和 `name`。

#### 添加发音人

当用户提供发音人 ID 时，询问一个便于识别的显示名称（如"爽快思思-女声"），然后保存：

```bash
python scripts/tts.py config --speaker add --id "zh_female_shuangkuaisisi_moon_bigtts" --name "爽快思思"
```

#### 选择发音人

⚠️ **务必遵守顶部「🚨 铁律」—— 用户未指定音色且未说"自动"时，绝不可自行选择合成。**

内置音色库见 [references/speakers.md](references/speakers.md)，共 100+ 音色，按场景分类。

合成前判断用户意图：

1. **用户明确指定了发音人名称或 voice_type** → 直接使用合成
2. **用户明确说"自动选择"/"随便"/"默认"/"合适音色"** → 从已保存发音人中按文本风格自动选一个，告知用户所选音色，直接合成
3. **用户未指定、也未要求自动选择（最常见情况）** → **绝对禁止合成。** 必须停下，执行以下步骤：

   a. **分析文本场景**：判断内容属于"情感语录/深夜电台"、"视频配音"、"角色扮演/小说"、"搞笑/特色"等哪类场景
   
   b. **推荐 10 个音色**：从 [speakers.md](references/speakers.md) 中根据场景选取 10 个最适合的音色，带序号展示。同时附上用户已保存的音色（如有）。格式示例：
   ```
   根据文案风格（情感语录），推荐以下音色：
   
   【推荐音色 - 情感电台类】
   1. 鸡汤女 2.0
   2. 鸡汤妹妹/Hope 2.0
   3. 心灵鸡汤 2.0
   4. 温柔淑女 2.0
   5. 魅力苏菲 2.0
   6. 深夜播客 2.0
   7. 温柔妈妈 2.0
   8. 温柔小雅 2.0
   9. 知性灿灿 2.0
   10. 儒雅逸辰 2.0
   
   【已保存音色】
   11. 情感电台女主播
   
   输入序号快速选择，或直接说音色名称。
   ```
   
   c. **用户选择序号或名称后**，先通过 `python scripts/tts.py config --speaker list` 检查是否已保存。已保存则直接用；未保存则用 `python scripts/tts.py config --speaker add --id "<voice_type>" --name "<音色名称>"` 保存后再合成

如果用户选择一个未在内置库中的音色 ID，直接添加并合成

#### 删除发音人

```bash
python scripts/tts.py config --speaker remove --id "发音人ID"
```

### 4. 合成语音

```bash
python scripts/tts.py synthesize --text "要朗读的文本" --speaker <发音人ID>
```

可选参数：
- `--format mp3|ogg_opus|pcm`（默认 mp3）
- `--sample-rate 24000`（默认 24000，可选 8000/16000/22050/32000/44100/48000）
- `--mode chunked|sse`（默认 chunked，SSE 在长文本时更稳定）

**输出文件：** `workspace/doubao_tts_output.mp3`

脚本返回 JSON：
```json
{
  "status": "ok",
  "file": "path/to/output.mp3",
  "size_bytes": 12345,
  "format": "mp3",
  "sample_rate": 24000,
  "speaker": "zh_female_shuangkuaisisi_moon_bigtts"
}
```

合成成功后，用 `message` 工具将音频文件发送给用户。

### 5. 更新配置

**更新 API Key：** 同步骤 2 命令，新 key 会覆盖旧 key。

**更新 Resource ID：** 如果需要切换模型版本（如声音复刻），可更改：
```bash
python scripts/tts.py config --resource-id "seed-icl-2.0"
```

默认 Resource ID 为 `seed-tts-2.0`。

## 配置存储

- `assets/config.json` — API Key + Resource ID
- `assets/speakers.json` — 发音人列表 `[{"id": "...", "name": "..."}]`

两个文件均在 skill 的 `assets/` 目录下，无需手动编辑。

## 参考

- API 详细文档：[references/api_docs.md](references/api_docs.md)
- 发音人完整列表：https://www.volcengine.com/docs/6561/1327395
