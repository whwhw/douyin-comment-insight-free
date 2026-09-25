from __future__ import annotations
import argparse, json, shutil, os, sys, importlib.util
from pathlib import Path
from runtime import present, provider, EDITION

def executable(env,name):
    value=os.getenv(env) or name
    return bool(shutil.which(value))
def inspect(mode):
    results={'python':sys.version_info>=(3,10),'requests':importlib.util.find_spec('requests') is not None}
    if mode in ('collect','all'):results['TIKHUB_API_KEY']=present('TIKHUB_API_KEY')
    if mode in ('local','cloud','all'):
        choice=provider() if mode=='all' else provider(mode)
        results['ffmpeg']=executable('FFMPEG_PATH','ffmpeg');results['ffprobe']=executable('FFPROBE_PATH','ffprobe')
        if choice=='local':
            results['whisper-cli']=executable('WHISPER_CLI_PATH','whisper-cli')
            results['WHISPER_MODEL_PATH']=bool(os.getenv('WHISPER_MODEL_PATH')) and Path(os.getenv('WHISPER_MODEL_PATH','')).expanduser().is_file()
        else:results['cloud_credentials']=present('VOLCENGINE_SPEECH_API_KEY') or (present('VOLCENGINE_SPEECH_APP_ID') and present('VOLCENGINE_SPEECH_ACCESS_TOKEN'))
    return {'edition':EDITION,'ok':all(results.values()),'checks':results,'missing':[k for k,v in results.items() if not v]}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['collect','local','cloud','all'],default='all');args=ap.parse_args()
    try:result=inspect(args.mode)
    except ValueError as e:print(str(e),file=sys.stderr);sys.exit(2)
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ok'] else 2)
