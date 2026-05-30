#!/usr/bin/env python3
"""
Doubao TTS (豆包语音合成) — 火山引擎 HTTP Chunked / SSE 单向流式 API.
Usage:
  python tts.py --text "你好世界" --speaker <id> [--format mp3] [--sample-rate 24000]
  python tts.py --text "你好世界" --speaker <id> --mode sse
  python tts.py config --api-key <key>
  python tts.py config --speaker add --id <speaker_id> --name <display_name>
  python tts.py config --speaker list
  python tts.py config --speaker remove --id <speaker_id>
"""

import argparse
import base64
import json
import os
import sys
import uuid

# ---- Paths ----
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SKILL_DIR, "..", "assets", "config.json")
SPEAKER_FILE = os.path.join(SKILL_DIR, "..", "assets", "speakers.json")
DEFAULT_OUTPUT = os.path.join(SKILL_DIR, "..", "..", "..", "workspace", "doubao_tts_output.mp3")

# ---- API Constants ----
API_URL_CHUNKED = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
API_URL_SSE = "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse"
RESOURCE_ID_DEFAULT = "seed-tts-2.0"


def _ensure_assets_dir():
    d = os.path.dirname(CONFIG_FILE)
    os.makedirs(d, exist_ok=True)


def load_config():
    _ensure_assets_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    _ensure_assets_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_speakers():
    _ensure_assets_dir()
    if os.path.exists(SPEAKER_FILE):
        with open(SPEAKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_speakers(speakers):
    _ensure_assets_dir()
    with open(SPEAKER_FILE, "w", encoding="utf-8") as f:
        json.dump(speakers, f, ensure_ascii=False, indent=2)


def tts_synthesize_chunked(api_key, resource_id, text, speaker, audio_format, sample_rate):
    """HTTP Chunked transfer-encoding TTS. Returns output file path."""
    import requests

    headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    body = {
        "user": {"uid": "openclaw-doubao-tts"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
            },
        },
    }

    audio_bytes = bytearray()
    session = requests.Session()
    with session.post(API_URL_CHUNKED, headers=headers, json=body, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            code = chunk.get("code")
            if code == 20000000:  # session finished
                break
            elif code != 0:
                raise RuntimeError(f"API error: code={code}, message={chunk.get('message', '')}")
            data = chunk.get("data")
            if data:
                audio_bytes.extend(base64.b64decode(data))

    output = DEFAULT_OUTPUT
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "wb") as f:
        f.write(audio_bytes)
    return output, len(audio_bytes)


def tts_synthesize_sse(api_key, resource_id, text, speaker, audio_format, sample_rate):
    """SSE streaming TTS. Returns output file path."""
    import requests

    headers = {
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    body = {
        "user": {"uid": "openclaw-doubao-tts"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": audio_format,
                "sample_rate": sample_rate,
            },
        },
    }

    audio_bytes = bytearray()
    session = requests.Session()
    with session.post(API_URL_SSE, headers=headers, json=body, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            json_str = line[5:].strip()
            try:
                chunk = json.loads(json_str)
            except json.JSONDecodeError:
                continue
            code = chunk.get("code")
            if code == 20000000:
                break
            elif code != 0:
                raise RuntimeError(f"API error: code={code}, message={chunk.get('message', '')}")
            data = chunk.get("data")
            if data:
                audio_bytes.extend(base64.b64decode(data))

    output = DEFAULT_OUTPUT
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "wb") as f:
        f.write(audio_bytes)
    return output, len(audio_bytes)


# ---- CLI ----
def cmd_synthesize(args):
    cfg = load_config()
    api_key = cfg.get("api_key", "")
    resource_id = cfg.get("resource_id", RESOURCE_ID_DEFAULT)

    if not api_key:
        print(json.dumps({
            "status": "no_api_key",
            "message": "尚未配置 API Key。请先运行: python tts.py config --api-key <your-key>"
        }, ensure_ascii=False))
        return

    speaker = args.speaker
    if not speaker:
        speakers = load_speakers()
        print(json.dumps({
            "status": "no_speaker",
            "message": "请指定发音人 (--speaker)，或查看已保存的发音人: python tts.py config --speaker list",
            "speakers": speakers
        }, ensure_ascii=False))
        return

    mode = args.mode or "chunked"
    audio_format = args.format or "mp3"
    sample_rate = args.sample_rate or 24000

    try:
        if mode == "sse":
            output, size = tts_synthesize_sse(api_key, resource_id, args.text, speaker, audio_format, sample_rate)
        else:
            output, size = tts_synthesize_chunked(api_key, resource_id, args.text, speaker, audio_format, sample_rate)
        print(json.dumps({
            "status": "ok",
            "file": output,
            "size_bytes": size,
            "format": audio_format,
            "sample_rate": sample_rate,
            "speaker": speaker
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


def cmd_config(args):
    cfg = load_config()

    if args.api_key:
        cfg["api_key"] = args.api_key
        save_config(cfg)
        print(json.dumps({"status": "ok", "message": "API Key 已保存"}, ensure_ascii=False))
        return

    if args.resource_id:
        cfg["resource_id"] = args.resource_id
        save_config(cfg)
        print(json.dumps({"status": "ok", "message": f"Resource ID 已更新为 {args.resource_id}"}, ensure_ascii=False))
        return

    if args.speaker:
        speakers = load_speakers()
        action = args.speaker

        if action == "list":
            print(json.dumps({"status": "ok", "speakers": speakers}, ensure_ascii=False))
            return

        elif action == "add":
            if not args.id or not args.name:
                print(json.dumps({"status": "error", "message": "添加发音人需要 --id 和 --name"}, ensure_ascii=False))
                return
            # check duplicate
            for s in speakers:
                if s["id"] == args.id:
                    s["name"] = args.name
                    save_speakers(speakers)
                    print(json.dumps({"status": "ok", "message": f"发音人 {args.id} ({args.name}) 已更新"}, ensure_ascii=False))
                    return
            speakers.append({"id": args.id, "name": args.name})
            save_speakers(speakers)
            print(json.dumps({"status": "ok", "message": f"发音人 {args.id} ({args.name}) 已添加"}, ensure_ascii=False))
            return

        elif action == "remove":
            if not args.id:
                print(json.dumps({"status": "error", "message": "删除发音人需要 --id"}, ensure_ascii=False))
                return
            before = len(speakers)
            speakers = [s for s in speakers if s["id"] != args.id]
            save_speakers(speakers)
            if len(speakers) < before:
                print(json.dumps({"status": "ok", "message": f"发音人 {args.id} 已删除"}, ensure_ascii=False))
            else:
                print(json.dumps({"status": "error", "message": f"发音人 {args.id} 不存在"}, ensure_ascii=False))
            return

    # show current config (minus api_key)
    safe = {k: v for k, v in cfg.items() if k != "api_key"}
    safe["has_api_key"] = bool(cfg.get("api_key"))
    safe["speakers"] = load_speakers()
    print(json.dumps({"status": "ok", "config": safe}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Doubao TTS CLI")
    sp = parser.add_subparsers(dest="command")

    # synthesize
    syn = sp.add_parser("synthesize", help="合成语音")
    syn.add_argument("--text", required=True, help="合成文本")
    syn.add_argument("--speaker", help="发音人 ID")
    syn.add_argument("--format", default="mp3", choices=["mp3", "ogg_opus", "pcm"], help="音频格式")
    syn.add_argument("--sample-rate", type=int, default=24000, help="采样率")
    syn.add_argument("--mode", default="chunked", choices=["chunked", "sse"], help="传输协议")

    # config
    cfg_p = sp.add_parser("config", help="管理配置")
    cfg_p.add_argument("--api-key", help="设置 API Key")
    cfg_p.add_argument("--resource-id", help="设置 Resource ID (默认 seed-tts-2.0)")
    cfg_p.add_argument("--speaker", choices=["add", "remove", "list"], help="发音人管理")
    cfg_p.add_argument("--id", help="发音人 ID")
    cfg_p.add_argument("--name", help="发音人显示名称")

    args = parser.parse_args()

    if args.command == "synthesize":
        cmd_synthesize(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
