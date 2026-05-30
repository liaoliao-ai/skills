# 🎙️ Liaoliao Skills

Open agent skills collection.

## Skills

### liaoliao-tts — 豆包语音合成

火山引擎豆包 TTS 语音合成技能，将文字转为自然语音。100+ 音色可选。

```bash
npx skills add liaoliao-ai/liaoliao-skills --skill liaoliao-tts
```

[![skills.sh](https://skills.sh/b/liaoliao-ai/liaoliao-skills)](https://skills.sh/liaoliao-ai/liaoliao-skills)

## 快速开始

1. 安装技能后，配置火山引擎 API Key：
   ```bash
   python scripts/tts.py config --api-key "你的API Key"
   ```

2. 合成语音：
   ```bash
   python scripts/tts.py synthesize --text "你好世界" --speaker <发音人ID>
   ```

## 许可

MIT
