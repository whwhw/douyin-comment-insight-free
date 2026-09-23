from __future__ import annotations
import argparse,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from runtime import ROOT,WORKSPACE,EDITION,atomic_json,valid_account

def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)
def inspect(account):
    matches=sorted((WORKSPACE/'runs').glob(f'*/{account}/analysis-input.json'),reverse=True)
    return {'accountId':account,'edition':EDITION,'analysisInput':str(matches[0]) if matches else None}
def prepare(account,resume=None,works=30,comments=100,offline=None):
    if not 1<=works<=30 or not 1<=comments<=100:raise ValueError('作品数须为1–30，单作品评论上限须为1–100')
    directory=Path(resume).resolve() if resume else WORKSPACE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')/account
    directory.mkdir(parents=True,exist_ok=True);manifest=directory/'run-manifest.json'
    if resume:
        prior=json.loads(manifest.read_text(encoding='utf-8'))
        if prior['accountId']!=account:raise ValueError('续跑目录不属于该账号')
        works=prior['works'];comments=prior['comments']
    state={'accountId':account,'edition':EDITION,'works':works,'comments':comments,'status':'collecting','startedAt':datetime.now(timezone.utc).isoformat()}
    atomic_json(manifest,state)
    try:
        if offline:
            data=json.loads(Path(offline).read_text(encoding='utf-8'))
            if data['accountId']!=account:raise ValueError('导入数据账号与参数不匹配')
            atomic_json(directory/'collected.json',data)
        else:run(ROOT/'scripts/fetch_account_data.py',account,'--out',directory,'--works',works,'--comments',comments)
        run(ROOT/'scripts/analyze_comments.py','--input',directory/'collected.json','--output',directory/'analysis-input.json')
        state['status']='awaiting_analysis'
    except Exception:
        state['status']='collection_failed';atomic_json(manifest,state)
        print(f'采集未完成，已有结果保留。续跑：python scripts/workflow.py prepare --account {account} --resume "{directory}"',file=sys.stderr);raise
    atomic_json(manifest,state)
    return {'accountId':account,'runDir':str(directory),'analysisInput':str(directory/'analysis-input.json'),'findings':str(directory/'findings.json'),'finalAnalysis':str(directory/'analysis.json')}
if __name__=='__main__':
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    i=sp.add_parser('inspect');i.add_argument('--account',required=True)
    p=sp.add_parser('prepare');p.add_argument('--account',required=True);p.add_argument('--resume',type=Path);p.add_argument('--works',type=int,default=30);p.add_argument('--comments',type=int,default=100);p.add_argument('--offline-input',type=Path)
    args=ap.parse_args()
    try:
        account=valid_account(args.account)
        result=inspect(account) if args.cmd=='inspect' else prepare(account,args.resume,args.works,args.comments,args.offline_input)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print('操作未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(2)
