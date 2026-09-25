#!/usr/bin/env python3
"""Normalize works, rank account-relative hits, select samples and validate evidence."""
from __future__ import annotations

import math
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


METRICS = ("diggCount", "commentCount", "collectCount", "shareCount")


def first_url(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    urls = value.get("url_list") or []
    if not isinstance(urls, list):
        return ""
    candidates = [str(url) for url in urls if str(url).startswith(("https://", "http://"))]
    compatible = next((url for url in candidates if ".heic" not in url.lower()), "")
    return compatible or (candidates[0] if candidates else "")


def normalize_work(raw: dict[str, Any]) -> dict[str, Any]:
    stats = raw.get("statistics") if isinstance(raw.get("statistics"), dict) else {}
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    play = video.get("play_addr") if isinstance(video.get("play_addr"), dict) else {}
    if not play:
        bit_rates = video.get("bit_rate") if isinstance(video.get("bit_rate"), list) else []
        play = next((item.get("play_addr") for item in bit_rates if isinstance(item, dict) and isinstance(item.get("play_addr"), dict)), {})
    cover = raw.get("cover") if isinstance(raw.get("cover"), dict) else {}
    if not cover and isinstance(video.get("cover"), dict):
        cover = video.get("cover")
    aweme_id = str(raw.get("aweme_id") or raw.get("item_id") or raw.get("group_id") or raw.get("awemeId") or "")
    created = int(raw.get("create_time") or raw.get("createTime") or 0)
    duration_ms = int(raw.get("duration") or raw.get("durationMs") or 0)
    return {
        "awemeId": aweme_id,
        "title": str(raw.get("desc") or raw.get("title") or raw.get("description") or ""),
        "createTime": created,
        "publishedAt": datetime.fromtimestamp(created, timezone.utc).isoformat() if created else "",
        "durationMs": duration_ms,
        "durationSeconds": round(duration_ms / 1000, 3) if duration_ms else 0,
        "cover": first_url(cover) if cover else str(raw.get("cover") or ""),
        "videoUrl": first_url(play) or str(raw.get("videoUrl") or ""),
        "sourceUrl": str(raw.get("share_url") or raw.get("sourceUrl") or (f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "")),
        "diggCount": int(stats.get("digg_count") or raw.get("diggCount") or 0),
        "commentCount": int(stats.get("comment_count") or raw.get("commentCount") or 0),
        "collectCount": int(stats.get("collect_count") or raw.get("collectCount") or 0),
        "shareCount": int(stats.get("share_count") or raw.get("shareCount") or 0),
        "playCount": int(stats.get("play_count") or raw.get("playCount") or 0),
    }


def score_works(works: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(work) for work in works if work.get("awemeId")]
    metric_values: dict[str, list[float]] = {
        metric: [math.log1p(max(0, int(row.get(metric) or 0))) for row in rows]
        for metric in METRICS
    }
    for row_index, row in enumerate(rows):
        z_scores = []
        for metric in METRICS:
            values = metric_values[metric]
            deviation = pstdev(values) if len(values) > 1 else 0
            z_scores.append((values[row_index] - mean(values)) / deviation if deviation else 0.0)
        row["viralScore"] = round(mean(z_scores), 4)
        row["playDataAvailable"] = bool(int(row.get("playCount") or 0) > 0)
    rows.sort(key=lambda row: (-float(row["viralScore"]), -int(row.get("diggCount") or 0), str(row["awemeId"])))
    viral_count = max(1, math.ceil(len(rows) * 0.2)) if rows else 0
    for rank, row in enumerate(rows, 1):
        row["viralRank"] = rank
        row["isAccountViral"] = rank <= viral_count
    return rows


def topic_tokens(work: dict[str, Any]) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z][A-Za-z0-9_-]{1,20}", str(work.get("title") or "").lower()))


def select_samples(scored: list[dict[str, Any]], limit: int = 5) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(rows: list[dict[str, Any]], role: str, count: int) -> None:
        for row in rows:
            aweme_id = str(row.get("awemeId") or "")
            if not aweme_id or aweme_id in seen:
                continue
            selected.append({"awemeId": aweme_id, "selectionRole": role})
            seen.add(aweme_id)
            if sum(1 for item in selected if item["selectionRole"] == role) >= count:
                break

    add(scored, "viral", 2)
    latest = sorted(scored, key=lambda row: (-int(row.get("createTime") or 0), str(row.get("awemeId") or "")))
    add(latest, "latest", 2)
    if len(selected) < limit:
        base = set().union(*(topic_tokens(row) for row in scored if str(row.get("awemeId")) in seen))
        outliers = sorted(
            (row for row in scored if str(row.get("awemeId")) not in seen),
            key=lambda row: (len(topic_tokens(row) & base) / max(len(topic_tokens(row) | base), 1), -int(row.get("createTime") or 0)),
        )
        add(outliers, "outlier", 1)
    if len(selected) < limit:
        add(latest, "fallback", limit - len(selected))
    return selected[:limit]


def build_work_payload(raw_works: list[dict[str, Any]], observed_at: str) -> dict[str, Any]:
    normalized = []
    seen = set()
    for raw in raw_works:
        work = normalize_work(raw)
        if work["awemeId"] and work["awemeId"] not in seen:
            normalized.append(work)
            seen.add(work["awemeId"])
    scored = score_works(normalized)
    latest = sorted(scored, key=lambda row: (-int(row.get("createTime") or 0), str(row.get("awemeId") or "")))
    times = [int(row.get("createTime") or 0) for row in scored if row.get("createTime")]
    return {
        "workWindow": {
            "requested": 30,
            "observed": len(scored),
            "observedAt": observed_at,
            "from": datetime.fromtimestamp(min(times), timezone.utc).isoformat() if times else "",
            "to": datetime.fromtimestamp(max(times), timezone.utc).isoformat() if times else "",
            "viralDefinition": "account_relative_log1p_zscore_equal_weight_top_20_percent",
        },
        "works": scored,
        "viralWorks": [row for row in scored if row["isAccountViral"]][:5],
        "latestWorks": latest[:5],
        "selectedWorks": select_samples(scored, limit=1),
    }
