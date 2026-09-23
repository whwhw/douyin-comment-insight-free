from __future__ import annotations
import json, os, shutil, subprocess, tempfile, uuid
from pathlib import Path
from media import PipelineError

def transcribe(audio):
    cli=os.getenv('WHISPER_CLI_PATH') or shutil.which('whisper-cli')
    value=os.getenv('WHISPER_MODEL_PATH','');model=Path(value).expanduser()
    if not cli or not value or not model.is_file():raise PipelineError('请安装 whisper.cpp 并在 .env 配置 WHISPER_MODEL_PATH；见 references/setup.md。')
    ffmpeg=os.getenv('FFMPEG_PATH') or shutil.which('ffmpeg')
    if not ffmpeg:raise PipelineError('缺少 FFmpeg')
    with tempfile.TemporaryDirectory(prefix='insight-local-') as tmp:
        wav=Path(tmp)/'speech.wav';out=Path(tmp)/'result'
        r=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(audio),'-ar','16000','-ac','1','-c:a','pcm_s16le',str(wav)],capture_output=True,text=True,timeout=300)
        if r.returncode:raise PipelineError('本地音频标准化失败')
        r=subprocess.run([cli,'-m',str(model),'-f',str(wav),'-l',os.getenv('ASR_LANGUAGE','zh'),'-ojf','-of',str(out),'-np','-t',str(max(1,min(8,os.cpu_count() or 2)))],capture_output=True,text=True,timeout=1800)
        if r.returncode or not out.with_suffix('.json').exists():raise PipelineError('本地模型执行失败；检查模型与 whisper.cpp 版本')
        raw=json.loads(out.with_suffix('.json').read_text(encoding='utf-8'))
    utterances=[{'start_time':x.get('offsets',{}).get('from'),'end_time':x.get('offsets',{}).get('to'),'text':str(x.get('text','')).strip()} for x in raw.get('transcription',[])]
    text=''.join(x['text'] for x in utterances).strip()
    if not text:raise PipelineError('未识别到语音')
    return {'result':{'text':text,'utterances':utterances}}, {},str(uuid.uuid4())
