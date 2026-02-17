from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.ad_llm import generate_publishable_ads_with_meta
from agent.feishu_webhook import get_webhook_info, send_text_detailed
from agent.hot_topics import collect_hot_topics
from agent.llm_client import LLMClient


FORBIDDEN_FILENAME_CHARS = r'<>:"/\\|?*'
CHANNEL_ALIAS = {
    "wechat": "wechat",
    "公众号": "wechat",
    "xiaohongshu": "xiaohongshu",
    "小红书": "xiaohongshu",
    "douyin": "douyin",
    "抖音": "douyin",
    "all": "all",
}
CHANNEL_FILE_MAP = {
    "wechat": "wechat.md",
    "xiaohongshu": "xiaohongshu.md",
    "douyin": "douyin_script.md",
}


def _slugify(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "ad"

    text = re.sub(rf"[{re.escape(FORBIDDEN_FILENAME_CHARS)}]", "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-._")
    return text[:80] or "ad"


def _build_slug(category: str, brand: Optional[str]) -> str:
    parts = [str(brand or "").strip(), str(category or "").strip()]
    joined = "-".join([p for p in parts if p])
    return _slugify(joined or category)


def _preview(text: str, max_len: int = 120) -> str:
    flat = re.sub(r"\s+", " ", str(text or "").strip())
    if len(flat) <= max_len:
        return flat
    return flat[:max_len] + "..."


def _normalize_channel(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in CHANNEL_ALIAS:
        return CHANNEL_ALIAS[key]
    raise ValueError(f"Unsupported channel/channels value: {value}")


def _resolve_channels(channels_value: Optional[str], channel_value: Optional[str]) -> List[str]:
    if channel_value:
        normalized = _normalize_channel(channel_value)
        if normalized == "all":
            return ["wechat", "xiaohongshu", "douyin"]
        return [normalized]

    raw = str(channels_value or "wechat").strip()
    if not raw:
        raw = "wechat"
    pieces = [p.strip() for p in raw.split(",") if p.strip()]
    if not pieces:
        pieces = ["all"]

    resolved: List[str] = []
    for part in pieces:
        normalized = _normalize_channel(part)
        if normalized == "all":
            for item in ["wechat", "xiaohongshu", "douyin"]:
                if item not in resolved:
                    resolved.append(item)
            continue
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved or ["wechat"]


def _count_words(text: str) -> int:
    compact = re.sub(r"\s+", "", str(text or ""))
    return len(compact)


def _ensure_brand_mentions(text: str, brand: Optional[str], min_count: int = 2) -> str:
    content = str(text or "").strip()
    b = str(brand or "").strip()
    if not b:
        return content
    while content.count(b) < min_count:
        content += f"\n\n{b}"
    return content


def _write_outputs(
    *,
    channels: List[str],
    channel_contents: Dict[str, str],
    channel_usage: Dict[str, Dict[str, Any]],
    category: str,
    brand: Optional[str],
    city: Optional[str],
    channel: str,
    tone: str,
    extra: Optional[str],
    hot_topics: List[str],
    sources: List[Dict[str, str]],
    fallback_used: bool,
    warnings: List[str],
    seed: Optional[int],
    elapsed: float,
) -> Path:
    day = datetime.now().strftime("%Y-%m-%d")
    channels_tag = "-".join(channels)
    time_tag = datetime.now().strftime("%H%M%S")
    slug = f"{_build_slug(category=category, brand=brand)}-{channels_tag}-{time_tag}"
    output_dir = PROJECT_ROOT / "outputs" / "ads" / day / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    meta_path = output_dir / "meta.json"

    channel_word_count: Dict[str, int] = {}
    channel_files: Dict[str, str] = {}
    files: List[str] = []
    for channel in channels:
        file_name = CHANNEL_FILE_MAP[channel]
        content = channel_contents.get(channel, "")
        (output_dir / file_name).write_text(content, encoding="utf-8")
        channel_word_count[channel] = _count_words(content)
        channel_files[channel] = file_name
        files.append(file_name)

    # backward compatibility with old flow
    if "wechat" in channel_contents:
        (output_dir / "ad.md").write_text(channel_contents["wechat"], encoding="utf-8")
    elif channel_contents:
        first_channel = channels[0]
        (output_dir / "ad.md").write_text(channel_contents.get(first_channel, ""), encoding="utf-8")

    model_value = None
    request_url_value = None
    for channel in channels:
        usage_meta = channel_usage.get(channel) or {}
        model_value = model_value or usage_meta.get("model")
        request_url_value = request_url_value or usage_meta.get("request_url")

    meta = {
        "inputs": {
            "category": category,
            "brand": brand,
            "city": city,
            "channel": channel,
            "tone": tone,
            "extra": extra,
            "seed": seed,
            "channels": channels,
        },
        "category": category,
        "brand": brand,
        "city": city,
        "channel": channel,
        "tone": tone,
        "extra": extra,
        "seed": seed,
        "hot_topics": hot_topics,
        "sources": sources,
        "fallback_used": fallback_used,
        "warnings": warnings,
        "model": model_value,
        "request_url": request_url_value,
        "usage": {k: (v.get("usage") or {}) for k, v in channel_usage.items()},
        "word_count": channel_word_count,
        "channel_word_count": channel_word_count,
        "channel_files": channel_files,
        "channels_meta": {
            ch: {
                "file": channel_files.get(ch),
                "word_count": channel_word_count.get(ch, 0),
            }
            for ch in channels
        },
        "files": files,
        "elapsed": round(elapsed, 3),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "channels": channels,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return output_dir


def _truncate_for_push(text: str, limit: int = 3500) -> str:
    content = str(text or "")
    if len(content) <= limit:
        return content
    return content[:limit] + "\n\n(truncated)"


def _split_for_push(text: str, max_len: int = 3000) -> List[str]:
    content = str(text or "")
    if len(content) <= max_len:
        return [content]
    chunks: List[str] = []
    start = 0
    while start < len(content):
        end = min(start + max_len, len(content))
        chunks.append(content[start:end])
        start = end
    return chunks


def _update_meta_push_status(
    output_dir: Path,
    warnings: List[str],
    push_status: Dict[str, Any],
) -> None:
    meta_path = output_dir / "meta.json"
    if not meta_path.exists():
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return

    meta["warnings"] = list(warnings)
    meta["feishu_push"] = dict(push_status)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_feishu_push_log(output_dir: Path, records: List[Dict[str, Any]]) -> None:
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "records": records,
    }
    (output_dir / "feishu_push_log.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate universal publishable ad from category + hot topics")
    parser.add_argument("--category", required=True, help="产品品类（通用）")
    parser.add_argument("--brand", default="", help="品牌/店名")
    parser.add_argument("--city", default="", help="城市/服务范围")
    parser.add_argument("--channel", default="", help="兼容参数：单渠道（wechat/xiaohongshu/douyin 或 公众号/小红书/抖音）")
    parser.add_argument("--channels", default="all", help="all|wechat|xiaohongshu|douyin")
    parser.add_argument("--tone", default="专业但有感染力", help="文案语气")
    parser.add_argument("--seed", type=int, default=None, help="可复现随机种子")
    parser.add_argument("--extra", default="", help="补充信息（卖点/价格区间/活动/网址等）")
    parser.add_argument("--temperature", type=float, default=0.9, help="LLM temperature")
    parser.add_argument("--max-tokens", type=int, default=1200, help="LLM max tokens")
    parser.add_argument("--push", choices=["none", "feishu"], default="none", help="生成后可选推送")

    args = parser.parse_args(argv)
    start = time.perf_counter()

    category = args.category.strip()
    brand = args.brand.strip() or None
    city = args.city.strip() or None
    channel = args.channel.strip() or None
    channels = _resolve_channels(args.channels, channel)
    tone = args.tone.strip() or "专业但有感染力"
    extra = args.extra.strip() or None

    try:
        env_base_url = (os.getenv("LLM_BASE_URL") or "").strip()
        env_model = (os.getenv("LLM_MODEL") or "").strip()
        env_serper = "SET" if (os.getenv("SERPER_API_KEY") or "").strip() else "MISSING"
        webhook_info = get_webhook_info()
        webhook_set_text = "SET" if webhook_info.get("webhook_set") else "MISSING"
        print(
            f"[ad_cli] env: base_url={env_base_url or 'MISSING'} model={env_model or 'MISSING'} serper_key={env_serper}"
        )
        print(
            f"[ad_cli] feishu_env: webhook={webhook_set_text} host={webhook_info.get('webhook_host') or 'N/A'} hash={webhook_info.get('webhook_hash') or 'N/A'}"
        )
        if webhook_info.get("webhook_set") and webhook_info.get("looks_malformed"):
            print("[ad_cli] warning: FEISHU_WEBHOOK_URL looks malformed")

        llm_client = LLMClient()
        llm_request_url = f"{llm_client.base_url}/chat/completions"
        print(f"[ad_cli] request_url={llm_request_url}")

        hot_result = collect_hot_topics(category=category, city=city, seed=args.seed)
        hot_topics = hot_result.get("hot_topics") or []
        sources = hot_result.get("sources") or []
        print(f"[ad_cli] serper_ok={bool(hot_result.get('serper_ok'))} status={hot_result.get('serper_status')}")

        warnings = list(hot_result.get("warnings") or [])
        channel_contents, channel_usage, gen_warnings = generate_publishable_ads_with_meta(
            category=category,
            channels=channels,
            brand=brand,
            city=city,
            tone=tone,
            extra=extra,
            hot_topics=hot_topics,
            sources=sources,
            seed=args.seed,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            llm_client=llm_client,
        )
        warnings.extend(gen_warnings)

        for current_channel in channels:
            channel_contents[current_channel] = _ensure_brand_mentions(
                channel_contents.get(current_channel, ""),
                brand,
                min_count=2,
            )

        elapsed = time.perf_counter() - start
        output_dir = _write_outputs(
            channels=channels,
            channel_contents=channel_contents,
            channel_usage=channel_usage,
            category=category,
            brand=brand,
            city=city,
            channel="all" if len(channels) > 1 else channels[0],
            tone=tone,
            extra=extra,
            hot_topics=hot_topics,
            sources=sources,
            fallback_used=bool(hot_result.get("fallback_used")),
            warnings=warnings,
            seed=args.seed,
            elapsed=elapsed,
        )

        if args.push == "feishu":
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{hashlib.sha1(str(time.time()).encode()).hexdigest()[:4]}"
            webhook_set = bool(webhook_info.get("webhook_set"))
            push_errors: List[str] = []
            messages_sent = 0
            responses: List[Dict[str, Any]] = []

            word_count_map = {ch: _count_words(channel_contents.get(ch, "")) for ch in channels}
            receipt_text = (
                f"[Universal Ad CLI Receipt]\n"
                f"run_id={run_id}\n"
                f"brand={brand}\n"
                f"category={category}\n"
                f"city={city}\n"
                f"channels={','.join(channels)}\n"
                f"files=wechat.md,xiaohongshu.md,douyin_script.md,meta.json\n"
                f"output_dir={output_dir}"
            )
            receipt_resp = send_text_detailed(receipt_text, explicit_enable=True)
            receipt_resp["label"] = "receipt"
            responses.append(receipt_resp)
            if receipt_resp.get("ok"):
                messages_sent += 1
            else:
                push_errors.append(f"receipt:{receipt_resp.get('error')}")

            push_targets = [
                ("wechat", "wechat.md", "公众号内容"),
                ("xiaohongshu", "xiaohongshu.md", "小红书内容"),
                ("douyin", "douyin_script.md", "抖音脚本"),
            ]
            for channel_key, file_name, title in push_targets:
                file_path = output_dir / file_name
                if not file_path.exists():
                    push_errors.append(f"{channel_key}:missing_file")
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8")
                except Exception as exc:
                    push_errors.append(f"{channel_key}:read_failed:{exc}")
                    continue

                parts = _split_for_push(content, max_len=3000)
                if len(parts) > 3:
                    preview = _truncate_for_push(content, limit=800)
                    body = f"[{title}] run_id={run_id} preview\n{preview}\n\nlocal_file={file_path}"
                    resp = send_text_detailed(body, explicit_enable=True)
                    resp["label"] = f"{channel_key}-preview"
                    responses.append(resp)
                    if resp.get("ok"):
                        messages_sent += 1
                    else:
                        push_errors.append(f"{channel_key}:{resp.get('error')}")
                else:
                    total = len(parts)
                    for idx, chunk in enumerate(parts, start=1):
                        body = f"[{title}] run_id={run_id} part {idx}/{total}\n{chunk}"
                        resp = send_text_detailed(body, explicit_enable=True)
                        resp["label"] = f"{channel_key}-part-{idx}"
                        responses.append(resp)
                        if resp.get("ok"):
                            messages_sent += 1
                        else:
                            push_errors.append(f"{channel_key}:part{idx}:{resp.get('error')}")

            push_ok = webhook_set and not push_errors
            if push_errors:
                warnings.append("push_failed:" + " | ".join(push_errors))

            push_status = {
                "ok": bool(push_ok),
                "messages_sent": int(messages_sent),
                "errors": push_errors,
                "webhook_set": webhook_set,
                "run_id": run_id,
                "webhook_host": webhook_info.get("webhook_host"),
                "webhook_hash": webhook_info.get("webhook_hash"),
                "webhook_masked": webhook_info.get("webhook_masked"),
                "responses": responses,
            }
            _update_meta_push_status(output_dir, warnings, push_status)
            _write_feishu_push_log(output_dir, responses)

            summary_parts = []
            for item in responses:
                summary_parts.append(
                    f"{item.get('label')}=>code={item.get('response_code')} msg={item.get('response_msg')} message_id={item.get('message_id')}"
                )
            print(
                f"[ad_cli] feishu_push: run_id={run_id} webhook_hash={webhook_info.get('webhook_hash') or 'N/A'}"
            )
            print(f"[ad_cli] feishu_push_summary: {' | '.join(summary_parts)}")

        request_url = None
        for ch in channels:
            request_url = request_url or (channel_usage.get(ch) or {}).get("request_url")
        preview_text = channel_contents.get("wechat") or next(iter(channel_contents.values()))

        print(f"[ad_cli] hot_topics={len(hot_topics)} fallback={bool(hot_result.get('fallback_used'))}")
        print(f"[ad_cli] channels={','.join(channels)}")
        print(f"[ad_cli] request_url={request_url or llm_request_url}")
        print(f"[ad_cli] output_dir={output_dir}")
        print("[ad_cli] files=wechat.md,xiaohongshu.md,douyin_script.md,meta.json")
        print(f"[ad_cli] preview={_preview(preview_text, max_len=120)}")
        print(f"[ad_cli] elapsed={elapsed:.2f}s")
        return 0
    except Exception as exc:
        elapsed = time.perf_counter() - start
        if "Missing LLM_MODEL" in str(exc):
            print("[ad_cli] fatal_error=Missing LLM_MODEL (set $env:LLM_MODEL=...)", file=sys.stderr)
        else:
            print(f"[ad_cli] fatal_error={exc}", file=sys.stderr)
        print(f"[ad_cli] elapsed={elapsed:.2f}s", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
