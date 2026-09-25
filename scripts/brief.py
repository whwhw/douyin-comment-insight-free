"""Validate model-authored basic findings; emit a plain-text account brief."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from runtime import atomic_json

def build(data,findings):
    allowed={'summary','lane','viewpoints','limitations'}
    if set(findings)-allowed:raise ValueError('基础简评只接收 summary/lane/viewpoints/limitations')
    original=data.get('comments',[]);ids={str(c['commentId']) for c in original}
    if not isinstance(findings.get('summary'),str) or not findings['summary'].strip():raise ValueError('缺少简评结论')
    if len(findings.get('viewpoints',[]))>3:raise ValueError('账号体检最多归纳 3 个主要讨论点')
    for v in findings.get('viewpoints',[]):
        evidence=v.get('evidenceCommentIds',[])
        if not evidence or any(str(i) not in ids for i in evidence):raise ValueError('讨论点必须引用本次真实评论')
    out={**data,**findings,'edition':'free','status':'completed' if original else 'pending'}
    return out

def render(data):
    rows=[data.get('displayName',data['accountId'])+' · 账号体检',
          '观察时间：'+str(data.get('updatedAt') or '未提供'),
          f"本次样本：{len(data.get('works',[]))} 条作品，{len(data.get('comments',[]))} 条评论",
          '内容方向：'+str(data.get('lane') or '样本不足，暂未判断'),data['summary'],'','作品表现（仅为本次样本内排名）：']
    for w in data.get('works',[])[:3]:rows.append(f"- {w.get('title','')}：赞 {w.get('diggCount',0)}，藏 {w.get('collectCount',0)}，分享 {w.get('shareCount',0)}")
    by_id={c['commentId']:c for c in data.get('comments',[])}
    for v in data.get('viewpoints',[]):
        rows+=['',v['title'],v['summary']]+['  原文：'+by_id[i]['text'] for i in v['evidenceCommentIds']]
    rows+=['','高赞评论：']+[f"- {c['text']}（赞 {c.get('diggCount',0)}）" for c in sorted(data.get('comments',[]),key=lambda c:-c.get('diggCount',0))[:5]]
    rows+=['','样本限制：评论记录不等于独立人数；排名不等于平台级爆款；转写未经逐字精校。']+list(data.get('limitations',[]))
    return '\n'.join(rows)+'\n'
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--findings',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    data=build(json.loads(args.input.read_text(encoding='utf-8')),json.loads(args.findings.read_text(encoding='utf-8')))
    atomic_json(args.output,data)
    text=render(data)
    args.output.with_name('account-brief.md').write_text(text,encoding='utf-8')
    print(text)
