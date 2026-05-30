#!/usr/bin/env python3
"""
火山引擎大模型录音文件极速版识别 → SRT 字幕生成

用法:
  python generate_subtitles.py <音频文件路径> [--config assets/config.json] [--output output.srt]
"""

import sys
import os
import json
import uuid
import base64
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SCRIPT_DIR / "assets" / "config.json"


def load_config(config_path):
    """加载配置文件"""
    cfg = Path(config_path)
    if not cfg.exists():
        print(f"[ERROR] 配置文件不存在: {config_path}")
        print(f"        请先配置 API Key。参考: {SCRIPT_DIR / 'assets' / 'config.example.json'}")
        sys.exit(1)
    with open(cfg, "r", encoding="utf-8") as f:
        config = json.load(f)

    version = config.get("version", "new")
    if version == "new":
        if not config.get("api_key"):
            print("[ERROR] 请在 config.json 中填写 api_key（新版本控制台）")
            sys.exit(1)
    else:
        if not config.get("app_key") or not config.get("access_key"):
            print("[ERROR] 请在 config.json 中填写 app_key 和 access_key（旧版本控制台）")
            sys.exit(1)

    return config


def build_curl_headers(config):
    """构建 curl 请求头列表"""
    task_id = str(uuid.uuid4())
    headers = [
        "X-Api-Resource-Id", config.get("resource_id", "volc.bigasr.auc_turbo"),
        "X-Api-Request-Id", task_id,
        "X-Api-Sequence", "-1",
        "Content-Type", "application/json",
    ]
    version = config.get("version", "new")
    if version == "new":
        headers += ["X-Api-Key", config["api_key"]]
    else:
        headers += ["X-Api-App-Key", config["app_key"], "X-Api-Access-Key", config["access_key"]]
    return headers


def recognize_curl(config, audio_path):
    """通过 curl 调用火山引擎 ASR 接口（解决部分环境 Python SSL 兼容性问题）"""
    api_url = config.get("api_url", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash")
    app_key = config.get("app_key") or config.get("api_key")

    print(f"[UPLOAD] {audio_path}")
    base64_data = base64.b64encode(Path(audio_path).read_bytes()).decode("utf-8")

    payload = json.dumps({
        "user": {"uid": app_key},
        "audio": {"data": base64_data},
        "request": {"model_name": config.get("model_name", "bigmodel")},
    }, ensure_ascii=False)

    # 写入临时请求文件（无 BOM）
    req_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    req_file.write(payload)
    req_file.close()

    # 临时响应文件
    resp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    resp_file.close()

    # curl = shutil.which("curl") or shutil.which("curl.exe") or "curl"
    curl_bin = "curl.exe"

    header_args = []
    h = build_curl_headers(config)
    for i in range(0, len(h), 2):
        header_args += ["-H", f"{h[i]}: {h[i+1]}"]

    cmd = [curl_bin, "-s", "-k", "-X", "POST", api_url,
           "-d", f"@{req_file.name}",
           "-o", resp_file.name,
           "--connect-timeout", "30", "--max-time", "300",
           "-D", "-"] + header_args

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=310)
    os.unlink(req_file.name)

    if result.returncode != 0:
        print(f"[ERROR] curl 调用失败: {result.stderr}")
        sys.exit(1)

    # 解析响应头获取状态
    header_lines = result.stdout.strip().split("\n")
    status_code = ""
    logid = ""
    for line in header_lines:
        line_lower = line.lower()
        if line_lower.startswith("x-api-status-code:"):
            status_code = line.split(":", 1)[1].strip()
        elif line_lower.startswith("x-tt-logid:"):
            logid = line.split(":", 1)[1].strip()

    with open(resp_file.name, "r", encoding="utf-8") as f:
        resp_text = f.read()
    os.unlink(resp_file.name)

    if status_code == "20000000":
        print(f"[OK] 识别成功 (logid: {logid})")
        return json.loads(resp_text)
    elif status_code == "20000003":
        print("[WARN] 静音音频，无内容可识别")
        return None
    elif status_code == "45000002":
        print("[WARN] 空音频")
        return None
    else:
        try:
            err = json.loads(resp_text)
            print(f"[ERROR] 识别失败: code={status_code}, msg={err.get('header',{}).get('message','N/A')}")
        except Exception:
            print(f"[ERROR] 识别失败: code={status_code}")
        sys.exit(1)


def ms_to_srt_time(ms):
    """毫秒 → SRT 时间格式 HH:MM:SS,mmm"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    ms_remain = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_remain:03d}"


def extract_texts(result):
    """从识别结果提取所有文本片段"""
    utterances = result.get("result", {}).get("utterances", [])
    texts = []
    for u in utterances:
        t = u.get("text", "").strip()
        if t:
            texts.append(t)
    return texts


def generate_srt(result, output_path):
    """生成 SRT 格式字幕"""
    utterances = result.get("result", {}).get("utterances", [])
    if not utterances:
        print("[WARN] 识别结果中无语音片段，无法生成字幕")
        return

    lines = []
    index = 1
    for utterance in utterances:
        text = utterance.get("text", "").strip()
        if not text:
            continue
        start = ms_to_srt_time(utterance["start_time"])
        end = ms_to_srt_time(utterance["end_time"])
        lines.append(f"{index}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
        index += 1

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"[DONE] SRT 字幕: {output_path} ({index - 1} 条)")


def generate_txt(result, output_path):
    """生成纯文本字幕（逐行文本，无时间戳）"""
    texts = extract_texts(result)
    if not texts:
        print("[WARN] 识别结果中无语音片段，无法生成字幕")
        return

    Path(output_path).write_text("\n\n".join(texts), encoding="utf-8")
    print(f"[DONE] TXT 字幕: {output_path} ({len(texts)} 段)")


def copy_srt_as_txt(srt_path):
    """生成 SRT 后自动复制一份 .txt（内容一致，方便直接查看）"""
    txt_path = Path(srt_path).with_suffix(".txt")
    shutil.copy2(srt_path, txt_path)
    print(f"[DONE] TXT 副本: {txt_path} (与 SRT 内容相同)")


def main():
    parser = argparse.ArgumentParser(description="火山引擎 ASR -> 字幕生成 (TXT/SRT)")
    parser.add_argument("audio", help="音频文件路径 (WAV/MP3/OGG OPUS, <=2h, <=100MB)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help=f"配置文件路径 (默认: {DEFAULT_CONFIG})")
    parser.add_argument("--output", "-o", help="输出路径 (默认: 与音频同名 .txt)")
    parser.add_argument("--format", "-f", choices=["srt", "txt"], default="srt",
                        help="输出格式: srt=带时间轴字幕 txt=纯文本无时间戳 (默认: srt)")
    parser.add_argument("--keep-json", action="store_true", help="保留识别的 JSON 原始结果")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"[ERROR] 文件不存在: {args.audio}")
        sys.exit(1)

    config = load_config(args.config)

    # 通过 curl 调用 API（兼容性好）
    result = recognize_curl(config, str(audio_path))
    if result is None:
        sys.exit(0)

    output_path = args.output or str(audio_path.with_suffix(".txt"))
    if args.format == "txt":
        generate_txt(result, output_path)
    else:
        generate_srt(result, output_path)
        # SRT 模式自动多输出一份 .txt 副本（内容相同，方便用户直接查看）
        copy_srt_as_txt(output_path)

    # 可选：保存原始 JSON
    if args.keep_json:
        json_path = str(audio_path.with_suffix(".json"))
        Path(json_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SAVE] JSON: {json_path}")


if __name__ == "__main__":
    main()
