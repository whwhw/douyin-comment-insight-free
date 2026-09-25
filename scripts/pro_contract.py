"""Validate model-authored output without changing primary evidence."""
import json
from pathlib import Path
from transcript_reading import words

def validate(analysis,base):
    errors=[];qualified=set(analysis.get('qualifiedWorkIds',[]));comments={c['commentId'] for c in analysis.get('comments',[])}
    for item in analysis.get('viewpoints',[]):
        ids=item.get('evidenceCommentIds',[])
        if not ids or any(i not in comments for i in ids):errors.append('观点缺少真实评论证据')
    for angle in analysis.get('recreationAngles',[]):
        if any(i not in comments for i in angle.get('evidenceCommentIds',[])):errors.append('二创引用未知评论')
    for a in analysis.get('workAnalyses',[]):
        wid=a.get('referenceId')
        if wid not in qualified:continue
        path=Path(a.get('asrMetadataPath',''));path=path if path.is_absolute() else base/path
        try:meta=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):errors.append('缺少可读ASR记录');continue
        if meta.get('qualityIssues') or meta.get('status')!='completed':errors.append('未经复核的转写不得进入深度拆解')
        utterances=meta.get('utterances',[])
        sections=analysis.get('transcriptSections',{}).get(wid,[])
        if not sections:errors.append('合格作品缺少分段原文和点评')
        for s in sections:
            r=s.get('review',{})
            if any(not r.get(k) for k in ('strength','risk','improvement')):errors.append('分段点评不完整')
            if words(s.get('readingText',''))!=words(s.get('text','')):errors.append('阅读版改动了原词')
        if words(''.join(s.get('text','') for s in sections))!=words(''.join(u.get('text','') for u in utterances)):errors.append('结构分段未完整覆盖ASR原文')
        for item in sections+a.get('goldenQuotes',[]):
            start=item.get('startMs');end=item.get('endMs')
            if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or end<=start:
                errors.append('分段或金句缺少有效时间');continue
            chunks=[u for u in utterances if u.get('start_time',-1)>=start and u.get('end_time',10**12)<=end]
            if not chunks or chunks[0]['start_time']!=start or chunks[-1]['end_time']!=end or words(''.join(u.get('text','') for u in chunks))!=words(item.get('text','')):errors.append('时间范围与引用原文不匹配')
        for beat in a.get('structureBeats',[]):
            if not isinstance(beat,(str,dict)) or (isinstance(beat,dict) and not isinstance(beat.get('label'),str)):errors.append('结构节点格式错误')
    return errors
