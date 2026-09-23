"""Readable stderr progress; stdout is reserved for structured results."""
import sys

STAGES = {1: "确认账号", 2: "采集作品与评论", 3: "准备完整口播", 4: "分析与证据校验", 5: "生成报告"}
STATUS = {"info": "进行中", "done": "已完成", "reuse": "已复用", "warning": "需注意", "next": "下一步", "error": "未完成"}


def label(value, limit=48):
    text = ' '.join(str(value or '').split())
    return text[:limit] + ('…' if len(text) > limit else '')


def progress(message, *, status="info"):
    text = ' '.join(str(message).split())
    print(f"  [{STATUS[status]}] {text}", file=sys.stderr, flush=True)


def stage(number, detail=""):
    print(f"\n── {number}/5 {STAGES[number]} ──", file=sys.stderr, flush=True)
    if detail:
        progress(detail)


def changes(current, previous):
    old = {str(w.get('awemeId')) for w in previous}
    new = [w for w in current if str(w.get('awemeId')) not in old]
    return new, len(current) - len(new)
