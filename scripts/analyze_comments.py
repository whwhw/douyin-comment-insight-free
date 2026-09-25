#!/usr/bin/env python3
"""Create a truthful, model-ready comment analysis input from collected data."""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path
from work_insight import build_work_payload

STOP=set('的了我你他她是有在也就都要和一个什么怎么可以吗啊吧呢这那不很还'.split())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    d=json.loads(args.input.read_text()); comments=d.get('comments',[])
    words=Counter()
    for c in comments:
        for w in re.findall(r'[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_-]{1,20}',c.get('text','')):
            if w not in STOP: words[w]+=1
    high=[]; layers=Counter()
    for c in comments:
        t=c['text']; layer='常规互动'; intent='表达态度'
        if any(x in t for x in ('怎么','如何','能不能','可以吗','多少钱','哪里','不会','求')): layer='高价值提问'; intent='寻求解决方案'
        elif any(x in t for x in ('想要','我也要','我也需要','求一个','链接','安装','领取')): layer='明确需求'; intent='表达获得或使用意愿'
        elif any(x in t for x in ('骗','垃圾','无语','假的')): layer='负面风险'; intent='负面反馈'
        c['layer']=layer; c['intent']=intent; layers[layer]+=1
        if layer in ('高价值提问','明确需求'): high.append(c)
    strategy_prompt='基于真实评论归纳主要讨论点，每条绑定证据ID；无评论则明确无证据。'
    work_payload=build_work_payload(d.get('works',[]),d.get('startedAt',''))
    out={'accountId':d.get('accountId'),'displayName':d.get('profile',{}).get('displayName',d.get('accountId')),'avatar':d.get('profile',{}).get('avatar',''),'followers':d.get('profile',{}).get('followers',0),'worksCount':len(d.get('works',[])),'updatedAt':d.get('startedAt',''),'bio':d.get('profile',{}).get('bio',''),'commentCount':len(comments),'profile':d.get('profile',{}),'source':d.get('source',{}),'commentLayers':[{'name':k,'count':v} for k,v in layers.items()],'keywords':[[k,v] for k,v in words.most_common(20)],'highValueComments':high[:50],'comments':comments,'qualifiedWorkIds':[],'workAnalyses':[],'recreationAngles':[],'coverage':{'selected':len(work_payload['selectedWorks']),'transcriptQualified':0,'metadataOnly':len(work_payload['selectedWorks']),'status':'awaiting_transcription' if work_payload['selectedWorks'] else 'no_works'},'codexPrompt':strategy_prompt,'warnings':d.get('warnings',[]),**work_payload}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)); print(json.dumps({'accountId':d.get('accountId'),'comments':len(comments),'keywords':len(out['keywords']),'output':str(args.output)},ensure_ascii=False))
if __name__=='__main__': main()
