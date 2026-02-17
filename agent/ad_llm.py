"""LLM orchestration for one-shot publishable ad generation."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Tuple

from agent.llm_client import LLMClient

FORBIDDEN_TEMPLATE_TERMS = ["Hook", "卖什么", "给谁", "为什么现在", "场景", "CTA"]
SUPPORTED_CHANNELS = {"wechat", "xiaohongshu", "douyin"}
CHANNEL_ALIAS = {
    "wechat": "wechat",
    "公众号": "wechat",
    "xiaohongshu": "xiaohongshu",
    "小红书": "xiaohongshu",
    "douyin": "douyin",
    "抖音": "douyin",
    "all": "all",
}


def _shuffle_topics_by_seed(hot_topics: List[str], seed: Optional[int]) -> List[str]:
    topics = [str(t).strip() for t in hot_topics if str(t).strip()]
    if seed is None:
        return topics
    rng = random.Random(seed)
    rng.shuffle(topics)
    return topics


def _seed_randomness_hint(seed: Optional[int]) -> str:
    if seed is None:
        return ""
    palette = [
        "优先选择反常识切入，段落节奏快慢交替。",
        "优先选择故事化开头，后段给出明确行动指令。",
        "优先使用极短句与转折句，避免中性平铺。",
        "优先用争议观点开头，再快速落回产品价值。",
    ]
    return palette[seed % len(palette)]


def _strip_code_fence(text: str) -> str:
    body = str(text or "").strip()
    body = re.sub(r"^```(?:markdown|md)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    return body.strip()


def _sanitize_forbidden_template_terms(text: str) -> str:
    sanitized = str(text or "")
    for token in FORBIDDEN_TEMPLATE_TERMS:
        sanitized = sanitized.replace(token, "")
    return re.sub(r"\n{3,}", "\n\n", sanitized).strip()


def _normalize_channel(value: str) -> str:
    key = str(value or "").strip().lower()
    if key in CHANNEL_ALIAS:
        return CHANNEL_ALIAS[key]
    raise ValueError(f"Unsupported channel: {value}")


def _normalize_channels(channels: Optional[List[str]]) -> List[str]:
    raw = list(channels or ["wechat", "xiaohongshu", "douyin"])
    normalized: List[str] = []
    for item in raw:
        channel = _normalize_channel(item)
        if channel == "all":
            for each in ["wechat", "xiaohongshu", "douyin"]:
                if each not in normalized:
                    normalized.append(each)
            continue
        if channel not in normalized:
            normalized.append(channel)
    if not normalized:
        return ["wechat", "xiaohongshu", "douyin"]
    return normalized


def _build_fallback_content(channel: str, category: str, brand: Optional[str], city: Optional[str], tone: str) -> str:
    brand_text = brand or "该品牌"
    city_text = city or "本地"
    if channel == "wechat":
        return (
            f"# {brand_text} {category} 选购建议\n\n"
            f"在{city_text}做{category}决策时，先看真实需求，再看预算和耐用性。{brand_text}给到的方案更重视长期使用体验。\n\n"
            f"## 为什么现在就该做\n"
            f"需求在变化，拖延会放大试错成本。{brand_text}建议先做小范围试配，再逐步升级。\n\n"
            f"## 行动建议\n"
            f"留言或私信“{category}”获取清单与预算建议。\n\n"
            f"_声明：以上内容基于常见用户痛点与公开讨论整理，不构成绝对承诺。_"
        )
    if channel == "xiaohongshu":
        return (
            f"# {brand_text} 的{category}到底怎么选？\n\n"
            f"最近很多人问我{category}怎么配不踩坑。\n"
            f"一句话：先明确用途，再看预算，再看耐用。\n\n"
            f"我自己会优先看：\n"
            f"- 是否真的匹配日常场景\n"
            f"- 是否能控制后续维护成本\n"
            f"- 是否有清晰的升级路径\n\n"
            f"{brand_text}这边给到的建议是先做轻量方案，再按体验逐步加配。\n\n"
            f"评论区扣“{category}”，我把避坑清单发你。\n\n"
            f"#{category} #选购 #避坑 #预算 #推荐 #经验分享 #清单 #指南"
        )
    return (
        "| 镜头编号 | 画面 | 旁白 | 字幕 | 音效/转场 |\n"
        "|---|---|---|---|---|\n"
        f"| 1 | 近景开场 | 3秒讲清{category}最常见误区 | 别再乱配了 | 强节奏鼓点 |\n"
        f"| 2 | 使用场景切换 | {brand_text}建议先按用途分层选择 | 先用途再预算 | 转场闪切 |\n"
        f"| 3 | 细节展示 | 在{city_text}也能按需求做渐进升级 | 逐步升级更稳 | 拉近镜头 |\n"
        f"| 4 | 结尾CTA | 私信关键词“{category}”拿清单 | 现在就来问 | 收尾上扬 |"
    )


def _build_system_message(channel: str, brand: Optional[str], has_sources: bool, seed: Optional[int]) -> str:
    seed_hint = _seed_randomness_hint(seed)
    source_rule = (
        "如果 evidence/sources 为空：只能写“基于近期讨论热度/常见痛点”，不能假装引用数据"
        if not has_sources
        else "如果 sources 较少，引用时只引用已给出的 title/url/snippet，不要扩展为不可验证事实"
    )

    base = [
        "你是顶级增长文案/广告创意总监。",
        "不能编造具体不可验证的事实（例如全网第一/销量第一/官方认证），除非用户 extra 提供。",
        "禁止使用固定模板章节词：为什么现在、卖什么给谁解决什么、场景痛点等套路化小标题。",
        source_rule,
        f"文中自然出现品牌名（若提供）至少 2 次，但不要像硬广堆砌{'（本次品牌为空则无需强制）' if not brand else ''}。",
    ]

    if channel == "wechat":
        channel_rules = [
            "目标渠道：微信公众号。",
            "必须输出：标题 + Hook + 正文（分小标题）+ 明确 CTA + 免责声明。",
            "文风：公众号可直接发布，信息密度高，表达自然。",
            "输出为 Markdown，长度 600-1200 中文字。",
        ]
    elif channel == "xiaohongshu":
        channel_rules = [
            "目标渠道：小红书笔记。",
            "标题要像小红书爆款；前 3 行强种草/强情绪。",
            "大量口语短句，节奏快。",
            "必须包含 #标签 8-15 个。",
            "必须覆盖“我怎么选/避坑清单/预算分档/适合人群”中的任意 2 项。",
            "CTA 更像“评论/私信关键词”。",
            "输出为 Markdown，长度 500-1000 中文字。",
        ]
    else:
        channel_rules = [
            "目标渠道：抖音短视频脚本。",
            "总时长 30-45 秒。",
            "必须输出分镜表，包含列：镜头编号、画面、旁白、字幕、音效/转场。",
            "开头 3 秒强钩子，结尾强 CTA。",
            "避免虚构可核验事实。",
            "输出为 Markdown，长度 400-900 中文字。",
        ]

    lines = ["你是顶级增长文案/广告创意总监"] + base + channel_rules
    if seed_hint:
        lines.append(f"随机性提示：{seed_hint}")
    return "\n".join(lines)


def _build_user_message(
    channel: str,
    category: str,
    brand: Optional[str],
    city: Optional[str],
    tone: str,
    extra: Optional[str],
    hot_topics: List[str],
    sources: List[Dict[str, str]],
) -> str:
    brand_text = brand or "（未提供）"
    city_text = city or "（未提供）"
    extra_text = extra or "（无）"

    topics_block = "\n".join([f"- {topic}" for topic in hot_topics]) if hot_topics else "- （无）"

    if sources:
        source_lines = []
        for idx, item in enumerate(sources, start=1):
            title = str(item.get("title") or "").strip() or "（无标题）"
            url = str(item.get("url") or "").strip() or "（无链接）"
            snippet = str(item.get("snippet") or "").strip() or "（无摘要）"
            source_lines.append(f"{idx}. title: {title}\n   url: {url}\n   snippet: {snippet}")
        sources_block = "\n".join(source_lines)
    else:
        sources_block = "（无）"

    return (
        f"category: {category}\n"
        f"brand: {brand_text}\n"
        f"city: {city_text}\n"
        f"channel: {channel}\n"
        f"tone: {tone}\n"
        f"extra: {extra_text}\n\n"
        f"hot_topics:\n{topics_block}\n\n"
        f"sources:\n{sources_block}\n\n"
        f"target_channel: {channel}\n\n"
        "请基于以上热点与产品信息，生成对应渠道可直接发布的最终内容。只输出最终 Markdown 正文，不要输出分析过程。"
    )


def generate_publishable_ad(
    *,
    category: str,
    brand: Optional[str] = None,
    city: Optional[str] = None,
    channel: str = "公众号",
    tone: str = "专业但有感染力",
    extra: Optional[str] = None,
    hot_topics: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, str]]] = None,
    seed: Optional[int] = None,
    temperature: float = 0.9,
    max_tokens: int = 1200,
    llm_client: Optional[LLMClient] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Generate one publishable ad markdown from hotspots and product info."""
    channel_norm = _normalize_channel(channel or "wechat")
    if channel_norm == "all" or channel_norm not in SUPPORTED_CHANNELS:
        raise ValueError(f"Unsupported channel: {channel}")

    topics = _shuffle_topics_by_seed(hot_topics or [], seed)
    src = list(sources or [])

    client = llm_client or LLMClient()

    system_message = _build_system_message(channel=channel_norm, brand=brand, has_sources=bool(src), seed=seed)
    user_message = _build_user_message(
        channel=channel_norm,
        category=category,
        brand=brand,
        city=city,
        tone=tone,
        extra=extra,
        hot_topics=topics,
        sources=src,
    )

    result = client.chat(
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
    )

    ad_markdown = _strip_code_fence(result.get("content") or "")
    if channel_norm == "wechat":
        ad_markdown = _sanitize_forbidden_template_terms(ad_markdown)

    if not ad_markdown:
        raise RuntimeError("LLM returned empty ad content")

    usage_meta = {
        "channel": channel_norm,
        "model": result.get("model"),
        "usage": result.get("usage") or {},
        "request_url": result.get("request_url"),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
        "hot_topics_used": topics,
        "source_count": len(src),
    }
    return ad_markdown, usage_meta


def generate_publishable_ads_with_meta(
    *,
    category: str,
    channels: Optional[List[str]] = None,
    brand: Optional[str] = None,
    city: Optional[str] = None,
    tone: str = "专业但有感染力",
    extra: Optional[str] = None,
    hot_topics: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, str]]] = None,
    seed: Optional[int] = None,
    temperature: float = 0.9,
    max_tokens: int = 1200,
    llm_client: Optional[LLMClient] = None,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]], List[str]]:
    """Generate publishable content for all requested channels.

    Returns:
        channel_contents: canonical channel -> markdown content
        channel_usage: canonical channel -> usage metadata
        warnings: generation warnings
    """
    normalized_channels = _normalize_channels(channels)
    contents: Dict[str, str] = {}
    usage_map: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []

    def _is_fatal_llm_config_error(exc: Exception) -> bool:
        msg = str(exc or "")
        return isinstance(exc, ValueError) and (
            "Missing LLM_MODEL" in msg
            or "Missing LLM_API_KEY" in msg
            or "Missing LLM_BASE_URL" in msg
        )

    for channel in normalized_channels:
        try:
            content, usage = generate_publishable_ad(
                category=category,
                brand=brand,
                city=city,
                channel=channel,
                tone=tone,
                extra=extra,
                hot_topics=hot_topics,
                sources=sources,
                seed=seed,
                temperature=temperature,
                max_tokens=max_tokens,
                llm_client=llm_client,
            )
            contents[channel] = content
            usage_map[channel] = usage
        except Exception as exc:
            if _is_fatal_llm_config_error(exc):
                raise
            warnings.append(f"channel_generate_failed:{channel}:{exc}")
            contents[channel] = _build_fallback_content(
                channel=channel,
                category=category,
                brand=brand,
                city=city,
                tone=tone,
            )
            usage_map[channel] = {
                "channel": channel,
                "model": None,
                "usage": {},
                "request_url": None,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "seed": seed,
                "hot_topics_used": hot_topics or [],
                "source_count": len(sources or []),
                "fallback": True,
                "error": str(exc),
            }

    return contents, usage_map, warnings


def generate_publishable_ads(
    inputs: Dict[str, Any],
    hot_topics_result: Dict[str, Any],
    llm_client: Optional[LLMClient] = None,
    channels: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Unified multi-channel entry point.

    Args:
        inputs: input dict including category/brand/city/tone/extra/seed/temperature/max_tokens
        hot_topics_result: dict from collect_hot_topics including hot_topics/sources
        llm_client: optional preconfigured LLM client
        channels: requested channels list (wechat/xiaohongshu/douyin)

    Returns:
        Dict[channel, markdown_content]
    """
    payload = dict(inputs or {})
    category = str(payload.get("category") or "").strip()
    if not category:
        raise ValueError("category is required")

    resolved_channels = channels or payload.get("channels") or ["wechat"]

    contents, _usage, _warnings = generate_publishable_ads_with_meta(
        category=category,
        channels=list(resolved_channels),
        brand=(str(payload.get("brand") or "").strip() or None),
        city=(str(payload.get("city") or "").strip() or None),
        tone=str(payload.get("tone") or "专业但有感染力").strip() or "专业但有感染力",
        extra=(str(payload.get("extra") or "").strip() or None),
        hot_topics=list((hot_topics_result or {}).get("hot_topics") or []),
        sources=list((hot_topics_result or {}).get("sources") or []),
        seed=payload.get("seed"),
        temperature=float(payload.get("temperature") or 0.9),
        max_tokens=int(payload.get("max_tokens") or 1200),
        llm_client=llm_client,
    )
    return contents
