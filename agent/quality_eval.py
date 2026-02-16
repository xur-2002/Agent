"""Lightweight quality evaluation for generated ad text (rule-based only)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

STRONG_VERBS = ["提升", "降低", "节省", "拉满", "拿下", "解决", "搞定", "翻倍", "压缩"]
STRONG_OUTCOMES = ["效率", "结果", "收益", "省钱", "省时", "稳", "不踩坑", "可落地"]
CTA_TERMS = ["私信", "评论", "领取", "下单", "链接", "咨询", "马上", "立即"]
RISK_TERMS = ["外围", "地陪", "博彩", "彩票", "成人", "空降", "客服微信"]

PLATFORM_HINTS = {
    "wechat": ["公众号", "导语", "小标题", "免责声明", "CTA", "正文"],
    "xiaohongshu": ["小红书", "评论区", "私信", "#", "避坑", "预算"],
    "douyin": ["抖音", "镜头", "旁白", "字幕", "转场", "脚本"],
}


def _count_matches(text: str, patterns: List[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(re.escape(pattern), text))
    return total


def _clip_score(value: float, scale: float = 1.0) -> int:
    score = int(round(value * scale))
    if score < 0:
        return 0
    if score > 100:
        return 100
    return score


def _safe_brand_count(text: str, brand: Optional[str]) -> int:
    b = str(brand or "").strip()
    if not b:
        return 0
    return text.count(b)


def eval_text(channel: str, text: str, brand: Optional[str], category: Optional[str]) -> Dict[str, Any]:
    """Evaluate generated text with cheap deterministic rules."""
    content = str(text or "")
    content_len = len(content)
    front = content[:120]

    has_number = bool(re.search(r"\d+", front))
    verb_hits = _count_matches(front, STRONG_VERBS)
    outcome_hits = _count_matches(front, STRONG_OUTCOMES)
    hook_score = _clip_score((20 if has_number else 0) + verb_hits * 20 + outcome_hits * 15)

    heading_count = len(re.findall(r"^#{1,6}\s", content, flags=re.MULTILINE))
    subheading_count = len(re.findall(r"^##\s", content, flags=re.MULTILINE))
    list_count = len(re.findall(r"^\s*[-*]\s", content, flags=re.MULTILINE))
    structure_raw = heading_count * 18 + subheading_count * 14 + list_count * 6
    structure_score = _clip_score(structure_raw)

    number_count = len(re.findall(r"\d+", content))
    step_terms = ["第一步", "第二步", "如果", "对比", "清单"]
    step_hits = _count_matches(content, step_terms)
    specificity_score = _clip_score(number_count * 6 + step_hits * 12)

    tail_start = int(content_len * 0.8)
    tail = content[tail_start:] if content else ""
    cta_hits = _count_matches(tail, CTA_TERMS)
    cta_score = _clip_score(cta_hits * 28)

    risk_flags: List[str] = []
    for risk in RISK_TERMS:
        if risk in content:
            risk_flags.append(risk)

    channel_norm = str(channel or "").strip().lower()
    hints = PLATFORM_HINTS.get(channel_norm, [])
    hint_hits = _count_matches(content, hints)
    platform_fit = _clip_score((hint_hits / max(len(hints), 1)) * 100)

    brand_mentions = _safe_brand_count(content, brand)
    category_mentions = _safe_brand_count(content, category)

    total_score = _clip_score((hook_score + structure_score + specificity_score + cta_score + platform_fit) / 5)

    return {
        "channel": channel_norm,
        "hook_score": hook_score,
        "structure_score": structure_score,
        "specificity_score": specificity_score,
        "cta_score": cta_score,
        "platform_fit": platform_fit,
        "total_score": total_score,
        "risk_flags": risk_flags,
        "metrics": {
            "length": content_len,
            "heading_count": heading_count,
            "subheading_count": subheading_count,
            "list_count": list_count,
            "number_count": number_count,
            "step_hits": step_hits,
            "cta_hits_tail": cta_hits,
            "brand_mentions": brand_mentions,
            "category_mentions": category_mentions,
            "platform_hint_hits": hint_hits,
        },
    }
