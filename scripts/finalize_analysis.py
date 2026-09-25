#!/usr/bin/env python3
"""Merge Codex-authored findings into a model-ready analysis input."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from work_insight import validate_work_evidence
from pro_contract import validate
from progress import stage, progress


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--findings", required=True, type=Path)
    parser.add_argument("--work-findings", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    stage(4, "合并作品与评论分析，核对评论、口播和金句证据")

    analysis = json.loads(args.input.read_text(encoding="utf-8"))
    findings = json.loads(args.findings.read_text(encoding="utf-8"))
    work_findings = json.loads(args.work_findings.read_text(encoding="utf-8")) if args.work_findings else {}
    comment_ids = {str(comment.get("commentId", "")) for comment in analysis.get("comments", [])}
    work_ids = {str(work.get("awemeId", "")) for work in analysis.get("works", [])}
    invalid_evidence = []
    for collection in ("viewpoints",):
        for item in findings.get(collection, []):
            for comment_id in item.get("evidenceCommentIds", []):
                if str(comment_id) not in comment_ids:
                    invalid_evidence.append(f"{collection}:{item.get('id', '')}:{comment_id}")
    if invalid_evidence:
        raise SystemExit("发现不存在的证据评论 ID：" + ", ".join(invalid_evidence))
    invalid_comment_works = [str(comment.get("awemeId")) for comment in analysis.get("comments", []) if str(comment.get("awemeId", "")) not in work_ids]
    if invalid_comment_works:
        raise SystemExit("评论引用了不存在的作品 ID：" + ", ".join(sorted(set(invalid_comment_works))))
    protected={'accountId','profile','works','comments','source','selectedWorks','workWindow','updatedAt','followers','displayName'}
    if protected.intersection(findings) or protected.intersection(work_findings):
        raise SystemExit('分析输出不得覆盖原始账号、作品或评论证据')
    findings.pop("opportunities", None)
    work_findings.pop("opportunities", None)
    analysis.pop("opportunities", None)
    analysis.update(findings)
    analysis.update(work_findings)
    selected_count = len(analysis.get("selectedWorks", []))
    qualified_count = len(set(map(str, analysis.get("qualifiedWorkIds", []))))
    analysis["coverage"] = {
        **analysis.get("coverage", {}),
        "selected": selected_count,
        "transcriptQualified": qualified_count,
        "metadataOnly": max(selected_count - qualified_count, 0),
        "status": "complete" if selected_count and qualified_count == selected_count else "partial" if qualified_count else "awaiting_transcription" if selected_count else "no_works",
    }
    analysis["secUserId"] = analysis.get("profile", {}).get("secUserId", "")
    analysis["updatedAt"] = analysis.get("run", {}).get("completedAt") or analysis.get("updatedAt") or datetime.now(timezone.utc).isoformat()
    analysis.setdefault("metrics", {})["comments"] = len(analysis.get("comments", []))
    analysis["commentCount"] = len(analysis.get("comments", []))

    viewpoint_by_comment = {}
    for viewpoint in analysis.get("viewpoints", []):
        for comment_id in viewpoint.get("evidenceCommentIds", []):
            viewpoint_by_comment.setdefault(str(comment_id), viewpoint.get("id", ""))
    for comment in analysis.get("comments", []):
        comment_id = str(comment.get("commentId", ""))
        comment["viewpointId"] = viewpoint_by_comment.get(comment_id, "")

    evidence_errors = validate_work_evidence(analysis, args.input.parent) + validate(analysis, args.input.parent)
    if evidence_errors:
        raise SystemExit("作品证据校验失败：" + "; ".join(evidence_errors))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    progress(f"证据校验通过：{qualified_count}/{selected_count} 条合格口播，{len(analysis.get('comments', []))} 条评论；等待生成页面。", status="done")
    print(json.dumps({"output": str(args.output), "comments": len(analysis.get("comments", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
