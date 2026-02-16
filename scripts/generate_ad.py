from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.ad_llm import generate_publishable_ads
from agent.hot_topics import collect_hot_topics


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

    raw = str(channels_value or "all").strip()
    if not raw:
        raw = "all"
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
    return resolved or ["wechat", "xiaohongshu", "douyin"]


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
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return output_dir


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
        hot_result = collect_hot_topics(category=category, city=city, seed=args.seed)
        hot_topics = hot_result.get("hot_topics") or []
        sources = hot_result.get("sources") or []

        warnings = list(hot_result.get("warnings") or [])
        channel_contents, channel_usage, gen_warnings = generate_publishable_ads(
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

        request_url = None
        for ch in channels:
            request_url = request_url or (channel_usage.get(ch) or {}).get("request_url")
        preview_text = channel_contents.get("wechat") or next(iter(channel_contents.values()))

        print(f"[ad_cli] hot_topics={len(hot_topics)} fallback={bool(hot_result.get('fallback_used'))}")
        print(f"[ad_cli] channels={','.join(channels)}")
        print(f"[ad_cli] request_url={request_url or 'N/A'}")
        print(f"[ad_cli] output_dir={output_dir}")
        print(f"[ad_cli] preview={_preview(preview_text, max_len=120)}")
        print(f"[ad_cli] elapsed={elapsed:.2f}s")
        return 0
    except Exception as exc:
        elapsed = time.perf_counter() - start
        print(f"[ad_cli] fatal_error={exc}", file=sys.stderr)
        print(f"[ad_cli] elapsed={elapsed:.2f}s", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
