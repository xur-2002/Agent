from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
import random
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlsplit

import requests


def _truncate(text: str, limit: int = 300) -> str:
    raw = str(text or "")
    if len(raw) <= limit:
        return raw
    return raw[:limit]


def get_webhook_info() -> Dict[str, Any]:
    webhook_url = (os.getenv("FEISHU_WEBHOOK_URL") or "").strip()
    if not webhook_url:
        return {
            "webhook_set": False,
            "webhook_host": None,
            "webhook_hash": None,
            "webhook_masked": None,
            "looks_malformed": True,
        }

    parts = urlsplit(webhook_url)
    host = parts.netloc or None
    digest = hashlib.sha256(webhook_url.encode("utf-8")).hexdigest()[:8]
    masked_path = parts.path or ""
    if "/hook/" in masked_path:
        masked_path = masked_path.split("/hook/")[0] + "/hook/***"
    masked = f"{parts.scheme}://{host}{masked_path}" if host else "***"
    looks_malformed = not (
        webhook_url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/")
        and bool(host)
    )
    return {
        "webhook_set": True,
        "webhook_host": host,
        "webhook_hash": digest,
        "webhook_masked": masked,
        "looks_malformed": looks_malformed,
    }


def _extract_code_msg(response_json: Any) -> Tuple[Optional[int], Optional[str], Optional[str], Any]:
    if not isinstance(response_json, dict):
        return None, None, None, None
    code = response_json.get("code")
    if code is None:
        code = response_json.get("StatusCode")
    msg = response_json.get("msg")
    if msg is None:
        msg = response_json.get("StatusMessage")

    data = response_json.get("data")
    message_id = None
    if isinstance(data, dict):
        message_id = data.get("message_id") or data.get("open_message_id")
    if not message_id:
        message_id = response_json.get("message_id") or response_json.get("open_message_id")

    try:
        code_int = int(code) if code is not None else None
    except Exception:
        code_int = None
    return code_int, (str(msg) if msg is not None else None), (str(message_id) if message_id else None), data


def _mask_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    masked = dict(headers or {})
    if "Authorization" in masked:
        masked["Authorization"] = "Bearer ***"
    if "X-API-KEY" in masked:
        masked["X-API-KEY"] = "***"
    return masked


def _payload_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = json.loads(json.dumps(payload or {}, ensure_ascii=False))
    try:
        text = (((out.get("content") or {}).get("text")) if isinstance(out, dict) else None)
        if isinstance(text, str) and len(text) > 500:
            out["content"]["text"] = text[:500] + "...(truncated)"
    except Exception:
        pass
    return out


def _post_with_retry(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    detail = send_payload_detailed(payload=payload)
    return bool(detail.get("ok")), detail.get("error")


def send_payload_detailed(payload: Dict[str, Any]) -> Dict[str, Any]:
    webhook = get_webhook_info()
    result: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "http_status": None,
        "response_json": None,
        "response_code": None,
        "response_msg": None,
        "message_id": None,
        "data": None,
        "attempts": 0,
        "request_headers": _mask_headers({"Content-Type": "application/json"}),
        "request_payload": _payload_preview(payload),
        "webhook_host": webhook.get("webhook_host"),
        "webhook_hash": webhook.get("webhook_hash"),
        "webhook_masked": webhook.get("webhook_masked"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    if not webhook.get("webhook_set"):
        result["error"] = "Missing FEISHU_WEBHOOK_URL"
        return result

    webhook_url = (os.getenv("FEISHU_WEBHOOK_URL") or "").strip()
    max_retries = 3
    timeout = 12

    for attempt in range(max_retries + 1):
        result["attempts"] = attempt + 1
        try:
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            result["error"] = f"network_error:{exc}"
            if attempt < max_retries:
                sleep_s = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.35)
                time.sleep(sleep_s)
                continue
            return result

        status = int(response.status_code)
        result["http_status"] = status
        body = _truncate(response.text or "")

        response_json = None
        try:
            response_json = response.json()
        except Exception:
            response_json = {"raw": body}
        result["response_json"] = response_json

        response_code, response_msg, message_id, data = _extract_code_msg(response_json)
        result["response_code"] = response_code
        result["response_msg"] = response_msg
        result["message_id"] = message_id
        result["data"] = data

        if status == 200 and (response_code in (0, None)):
            result["ok"] = True
            result["error"] = None
            return result

        if status in {429, 500, 502, 503, 504} and attempt < max_retries:
            sleep_s = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.35)
            time.sleep(sleep_s)
            continue

        if status != 200:
            result["error"] = f"http_{status}: body={body}"
        else:
            result["error"] = f"feishu_status_error:{response_code}:{response_msg}".strip(":")
        return result

    if not result.get("error"):
        result["error"] = "unknown_error"
    return result


def send_text(text: str) -> Tuple[bool, Optional[str]]:
    payload = {
        "msg_type": "text",
        "content": {
            "text": str(text or "").strip(),
        },
    }
    return _post_with_retry(payload)


def send_text_detailed(text: str) -> Dict[str, Any]:
    payload = {
        "msg_type": "text",
        "content": {
            "text": str(text or "").strip(),
        },
    }
    return send_payload_detailed(payload)


def send_rich_summary(summary: dict) -> Tuple[bool, Optional[str]]:
    data = dict(summary or {})
    lines = [
        "[Universal Ad CLI] 生成完成",
        f"brand={data.get('brand')}",
        f"category={data.get('category')}",
        f"city={data.get('city')}",
        f"tone={data.get('tone')}",
        f"channels={','.join(data.get('channels') or [])}",
        f"seed={data.get('seed')}",
        f"hot_topics_top3={json.dumps(data.get('hot_topics_top3') or [], ensure_ascii=False)}",
        f"output_dir={data.get('output_dir')}",
        f"word_count={json.dumps(data.get('word_count') or {}, ensure_ascii=False)}",
    ]
    return send_text("\n".join(lines))


def send_rich_summary_detailed(summary: dict) -> Dict[str, Any]:
    data = dict(summary or {})
    lines = [
        "[Universal Ad CLI] 生成完成",
        f"brand={data.get('brand')}",
        f"category={data.get('category')}",
        f"city={data.get('city')}",
        f"tone={data.get('tone')}",
        f"channels={','.join(data.get('channels') or [])}",
        f"seed={data.get('seed')}",
        f"hot_topics_top3={json.dumps(data.get('hot_topics_top3') or [], ensure_ascii=False)}",
        f"output_dir={data.get('output_dir')}",
        f"word_count={json.dumps(data.get('word_count') or {}, ensure_ascii=False)}",
    ]
    return send_text_detailed("\n".join(lines))
