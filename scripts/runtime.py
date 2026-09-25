from __future__ import annotations
import json, os, re, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load_env():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                k,v=line.split('=',1);os.environ.setdefault(k.strip(),v.strip().strip('\"\''))
load_env()
EDITION=json.loads((ROOT/'edition.json').read_text(encoding='utf-8'))['edition']
WORKSPACE=Path(os.getenv('DOUYIN_INSIGHT_WORKSPACE') or ROOT/'workspace').expanduser().resolve()
def valid_account(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):raise ValueError('请输入真实抖音号；主页链接和昵称须先核验身份。')
    return value

def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');name=f.name
    Path(name).replace(path)

def present(key):
    v=os.getenv(key,'').strip()
    return bool(v and not v.startswith(('replace_','your_','<')))

def provider(requested=None):
    choice=requested or os.getenv('ASR_PROVIDER') or 'cloud'
    if choice not in ('local','cloud'):raise ValueError('ASR_PROVIDER 只能是 local 或 cloud')
    return choice
