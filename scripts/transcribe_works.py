from __future__ import annotations
import argparse, hashlib, json, re, sys, tempfile, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
from runtime import WORKSPACE, atomic_json, provider, valid_account
from media import PipelineError, prepare_audio, audio_from_video
from doctor import inspect

def quality(text,utterances,duration):
    reasons=[]
    if not text.strip():reasons.append('没有识别文本')
    if not utterances:reasons.append('缺少时间戳')
    last=0
    for u in utterances:
        start=u.get('start_time');end=u.get('end_time')
        if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or start<last or end<=start:
            reasons.append('时间戳无效或倒序');break
        last=end
    if duration and last<duration*1000-max(10000,duration*50):reasons.append('口播结束过早，需核对静音片尾或缺失')
    if duration and last>duration*1000+3000:reasons.append('时间戳超出媒体长度')
    norm=lambda s:re.sub(r'[^\w\u4e00-\u9fff]','',s)
    counts=Counter(norm(u.get('text','')) for u in utterances)
    if any(len(t)>=5 and n>=4 for t,n in counts.items()):reasons.append('检测到重复识别，需人工核对')
    if len(norm(text))<20:reasons.append('有效语音过少，需人工复核')
    return reasons

def stamp(ms):
    n=max(0,int(ms));return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'

def save_result(dest,wid,text,meta):
    dest.mkdir(parents=True,exist_ok=True)
    spoken=dest/'spoken'/f'{wid}.txt';asr=dest/'asr'/f'{wid}.json';srt=dest/'subtitles'/f'{wid}.srt'
    for p in (spoken,asr,srt):p.parent.mkdir(parents=True,exist_ok=True)
    spoken.write_text(text+'\n',encoding='utf-8');atomic_json(asr,meta)
    valid=[u for u in meta['utterances'] if isinstance(u.get('start_time'),(int,float)) and isinstance(u.get('end_time'),(int,float)) and u['end_time']>u['start_time']>=0]
    srt.write_text('\n\n'.join(f"{i}\n{stamp(u['start_time'])} --> {stamp(u['end_time'])}\n{u['text']}" for i,u in enumerate(valid,1))+'\n',encoding='utf-8')
    return {'spokenScriptPath':str(spoken.resolve()),'asrMetadataPath':str(asr.resolve()),'subtitlePath':str(srt.resolve())}

def cached(input_path,account,work,choice,output_dir=None):
    # Reuse manifests even when report generation was interrupted.
    paths=[Path(output_dir)/'transcription-manifest.json'] if output_dir else []
    paths.append(input_path.parent/'evidence/transcription-manifest.json')
    paths+=sorted((WORKSPACE/'runs').glob(f'*/{account}/evidence/transcription-manifest.json'),reverse=True)
    for path in dict.fromkeys(paths):
        try:
            m=json.loads(path.read_text(encoding='utf-8'))
            if m.get('accountId')!=account:continue
            for row in m.get('works',[]):
                if row.get('referenceId')!=work['awemeId'] or row.get('provider')!=choice or not row.get('transcriptComplete'):continue
                meta=json.loads(Path(row['asrMetadataPath']).read_text(encoding='utf-8'));text=Path(row['spokenScriptPath']).read_text(encoding='utf-8').strip()
                old=float(meta.get('expectedDurationSeconds') or 0);new=float(work.get('durationSeconds') or 0)
                if abs(old-new)>max(3,new*.01) or quality(text,meta['utterances'],new):continue
                if not Path(row['subtitlePath']).is_file():continue
                return {**row,'reused':True}
        except (OSError,ValueError,KeyError,TypeError):continue
    return None

def extract_one(work,dest,choice):
    wid=valid_account(str(work['awemeId']))
    with tempfile.TemporaryDirectory(prefix='insight-audio-') as tmp:
        video=Path(tmp)/'video.mp4';audio=Path(tmp)/'audio.wav'
        if work.get('localMedia'):audio_from_video(Path(work['localMedia']),audio)
        else:prepare_audio(work,wid,video,audio)
        from local_asr import transcribe
        response,headers,request=transcribe(audio)
    result=response.get('result',{});text=result.get('text','').strip();utterances=result.get('utterances',[])
    reasons=quality(text,utterances,float(work.get('durationSeconds') or 0));now=datetime.now(timezone.utc).isoformat()
    meta={'provider':choice,'status':'needs_review' if reasons else 'completed','completedAt':now,'requestId':request,'expectedDurationSeconds':work.get('durationSeconds',0),'utterances':utterances,'qualityIssues':reasons,'accuracyNote':'完整性校验不等于逐字准确；原文保留识别误差。'}
    return {'referenceId':wid,'provider':choice,'status':meta['status'],'transcriptComplete':not reasons,'sourceKind':'full_asr' if not reasons else 'metadata_only','qualityIssues':reasons,'completedAt':now,**save_result(dest,wid,text,meta)}

def main():
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--input',type=Path);g.add_argument('--media',type=Path)
    ap.add_argument('--output-dir',type=Path);ap.add_argument('--provider',choices=['local']);ap.add_argument('--force-transcribe',action='store_true');args=ap.parse_args()
    choice=provider(args.provider);check=inspect(choice)
    if not check['ok']:raise PipelineError('环境未就绪：'+', '.join(check['missing'])+'；参阅 references/setup.md')
    if args.media:
        media=args.media.expanduser().resolve()
        if not media.is_file():raise PipelineError('媒体文件不存在')
        digest=hashlib.sha256(media.read_bytes()).hexdigest()[:16]
        probe=subprocess.run([os.getenv('FFPROBE_PATH') or 'ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(media)],capture_output=True,text=True,timeout=20)
        if probe.returncode:raise PipelineError('无法读取媒体时长')
        duration=float(probe.stdout.strip())
        works=[{'awemeId':digest,'localMedia':str(media),'durationSeconds':duration}];account='local';inp=WORKSPACE/'local'/digest/'analysis-input.json'
    else:
        inp=args.input.resolve();data=json.loads(inp.read_text(encoding='utf-8'));account=valid_account(data['accountId']);selected={str(x['awemeId']) for x in data['selectedWorks']};works=[w for w in data['works'] if str(w['awemeId']) in selected]
    dest=(args.output_dir or inp.parent/'evidence').resolve();dest.mkdir(parents=True,exist_ok=True)
    # Gather all reusable rows before replacing the manifest.
    reuse={w['awemeId']:cached(inp,account,w,choice,dest) for w in works} if not args.force_transcribe else {}
    rows=[]
    for i,w in enumerate(works,1):
        print(f"[{i}/{len(works)}] 本地文案提取：{w.get('title') or w['awemeId']}",file=sys.stderr)
        try:row=reuse.get(w['awemeId']) or extract_one(w,dest,choice)
        except Exception as e:
            # Never persist remote responses, credentials, or signed URLs in diagnostic text.
            row={'referenceId':w['awemeId'],'provider':choice,'status':'failed','transcriptComplete':False,'sourceKind':'metadata_only','error':type(e).__name__,'nextAction':'检查本地模型、音频工具或媒体文件；修复后重跑本命令。'}
        row['selectionRole']=next((s.get('selectionRole') for s in data.get('selectedWorks',[]) if s['awemeId']==w['awemeId']),None) if args.input else 'local'
        rows.append(row);atomic_json(dest/'transcription-manifest.json',{'accountId':account,'works':rows})
    print(json.dumps({'manifest':str(dest/'transcription-manifest.json'),'completed':sum(r['status']=='completed' for r in rows),'needsReview':sum(r['status']=='needs_review' for r in rows),'failed':sum(r['status']=='failed' for r in rows),'reused':sum(bool(r.get('reused')) for r in rows)},ensure_ascii=False))
    return 0 if rows and all(r['status']=='completed' for r in rows) else 2
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,PipelineError) as e:print(str(e),file=sys.stderr);sys.exit(2)
