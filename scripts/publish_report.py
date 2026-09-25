#!/usr/bin/env python3
"""Publish one report and atomically refresh the static report index."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import requests
from transcript_reading import enrich
from progress import stage, progress


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "assets" / "templates"
ICON_ASSETS = ROOT / "assets" / "icons"
UI_ASSETS = ROOT / "assets" / "ui"
ACCOUNT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()
DEFAULT_WORKSPACE = Path(os.getenv("DOUYIN_INSIGHT_WORKSPACE") or ROOT / "workspace").expanduser().resolve()
DEFAULT_SITE = DEFAULT_WORKSPACE / "site"


def date_only(value: object) -> str:
    return str(value or "")[:10].replace(".", "-")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def localize_avatar(payload: dict, output_dir: Path, account: str) -> None:
    """Download remote avatars so generated reports do not depend on hotlinks."""
    avatar = str(payload.get("avatar") or payload.get("profile", {}).get("avatar") or "").strip()
    if not avatar.startswith(("https://", "http://")):
        payload["avatar"] = avatar
        return
    try:
        response = requests.get(
            avatar,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"},
            timeout=20,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        suffix = {"image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(content_type, ".jpg")
        if not content_type.startswith("image/") or len(response.content) > 5 * 1024 * 1024:
            raise ValueError("头像响应不是有效的小型图片")
        assets = output_dir / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        target = assets / f"{account}-avatar{suffix}"
        with tempfile.NamedTemporaryFile("wb", dir=assets, delete=False) as handle:
            handle.write(response.content)
            temporary = Path(handle.name)
        temporary.replace(target)
        payload["avatar"] = f"assets/{target.name}"
    except (requests.RequestException, OSError, ValueError) as error:
        payload["avatar"] = ""
        payload.setdefault("warnings", []).append(f"头像本地化失败，页面将使用文字占位：{error}")


def embed_transcripts(payload: dict, data_dir: Path) -> None:
    """Embed qualified spoken text so file:// reports can show it without fetch/CORS."""
    for analysis in payload.get("workAnalyses", []):
        value = str(analysis.get("spokenScriptPath") or "")
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = (data_dir / path).resolve()
        if path.is_file():
            analysis["spokenScript"] = path.read_text(encoding="utf-8", errors="ignore").strip()


def localize_work_covers(payload: dict, output_dir: Path, account: str) -> None:
    """Cache covers for qualified analyses; keep graceful visual fallbacks on failure."""
    qualified = set(map(str, payload.get("qualifiedWorkIds", [])))
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for work in payload.get("works", []):
        aweme_id = str(work.get("awemeId") or "")
        cover = str(work.get("cover") or "")
        if aweme_id not in qualified or not cover.startswith(("https://", "http://")):
            continue
        try:
            response = requests.get(cover, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"}, timeout=25)
            response.raise_for_status()
            if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                raise ValueError("作品封面响应不是图片")
            target = assets / f"{account}-{aweme_id}-cover.jpg"
            with tempfile.NamedTemporaryFile("wb", dir=assets, delete=False) as handle:
                handle.write(response.content)
                temporary = Path(handle.name)
            temporary.replace(target)
            work["cover"] = f"assets/{target.name}"
        except (requests.RequestException, OSError, ValueError):
            pass


def creator_homepage(payload: dict) -> str:
    sec_id = str(payload.get("secUserId") or payload.get("profile", {}).get("secUserId") or "")
    return f"https://www.douyin.com/user/{sec_id}" if re.fullmatch(r"[A-Za-z0-9_-]+", sec_id) else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SITE)
    parser.add_argument("--preserve-layout", action="store_true", help="Keep this account's existing custom HTML shell while replacing its complete data payload")
    args = parser.parse_args()
    args.preserve_layout = False
    stage(5, f"为 {args.account} 更新详情页、首页索引和共用样式")
    if not ACCOUNT_PATTERN.fullmatch(args.account):
        raise SystemExit("账号只能包含字母、数字、下划线和连字符，长度不超过 64")
    payload = json.loads(args.data.read_text(encoding="utf-8"))
    payload.pop("opportunities", None)
    for comment in payload.get("comments", []):
        comment.pop("opportunityId", None)
    payload["accountId"] = args.account
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if ICON_ASSETS.exists():
        shutil.copytree(ICON_ASSETS, output_dir / "assets" / "icons", dirs_exist_ok=True)
    if UI_ASSETS.exists():
        shutil.copytree(UI_ASSETS, output_dir / "assets" / "ui", dirs_exist_ok=True)
    localize_avatar(payload, output_dir, args.account)
    embed_transcripts(payload, args.data.resolve().parent)
    enrich(payload)
    localize_work_covers(payload, output_dir, args.account)

    index_html = output_dir / "comment-insight-index.html"
    atomic_write(index_html, (TEMPLATES / "index.html").read_text(encoding="utf-8"))

    existing_detail = output_dir / f"{args.account}.html"
    source = (existing_detail if args.preserve_layout and existing_detail.exists() else TEMPLATES / "report.html").read_text(encoding="utf-8")
    if args.preserve_layout and existing_detail.exists():
        match = re.search(r'const pageData=(.*?);\s*/\* INSIGHT_DATA_END', source, re.S)
        if not match or str(json.loads(match.group(1)).get('accountId')) != args.account:
            raise SystemExit("不能复用其他账号或无法核验账号的页面")
    start, end = "/* INSIGHT_DATA_START */", "/* INSIGHT_DATA_END */"
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit("详情页模板缺少唯一的数据注入标记")
    before, rest = source.split(start, 1)
    _, after = rest.split(end, 1)
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    detail = output_dir / f"{args.account}.html"
    atomic_write(detail, before + start + f"\nconst pageData={embedded};\n" + end + after)

    index_path = output_dir / "comment-insight-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"updatedAt": "", "reports": []}
    previous = next((row for row in index.get("reports", []) if str(row.get("accountId")) == args.account), {})
    reports = [row for row in index.get("reports", []) if str(row.get("accountId")) != args.account]
    comment_count = len(payload.get("comments", []))
    updated_at = payload.get("updatedAt") or payload.get("run", {}).get("completedAt") or ""
    reports.append({
        "accountId": args.account,
        "displayName": payload.get("displayName") or previous.get("displayName") or args.account,
        "file": detail.name,
        "homepageUrl": creator_homepage(payload) or previous.get("homepageUrl", ""),
        "avatar": payload.get("avatar") or previous.get("avatar") or "",
        "followers": payload.get("followers", previous.get("followers", 0)),
        "works": payload.get("worksCount", len(payload.get("works", []))) if isinstance(payload.get("works"), list) else payload.get("works", previous.get("works", 0)),
        "lane": payload.get("lane") or previous.get("lane") or "未分类",
        "summary": payload.get("summary") or payload.get("bio") or previous.get("summary") or "评论分析报告",
        "commentCount": comment_count,
        "viralCount": len(payload.get("viralWorks", [])),
        "qualifiedWorkCount": len(payload.get("qualifiedWorkIds", [])),
        "collectionAt": payload.get("workWindow", {}).get("observedAt") or updated_at,
        "coverageStatus": payload.get("coverage", {}).get("status", "legacy"),
        "status": "completed" if comment_count > 0 else "pending",
        "executionAt": updated_at,
        "updatedAt": date_only(updated_at),
    })
    index["reports"] = sorted(reports, key=lambda row: str(row.get("executionAt", "")), reverse=True)
    index["updatedAt"] = date_only(updated_at) or index.get("updatedAt", "")
    readable = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    bundle = "window.COMMENT_INSIGHT_INDEX=" + json.dumps(index, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";\n"
    atomic_write(index_path, readable)
    atomic_write(output_dir / "comment-insight-index-data.js", bundle)
    progress("详情页与首页索引已写入", status="done")
    progress("检查页面显示、报告跳转和资源加载后完成交付", status="next")
    print(json.dumps({"accountId": args.account, "detailPage": str(detail), "indexPage": str(index_html), "status": "updated" if previous else "created"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
