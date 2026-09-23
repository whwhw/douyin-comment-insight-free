#!/usr/bin/env python3
"""Install one edition, preserving configuration and user data."""
from __future__ import annotations
import argparse,json,shutil,sys,tempfile,os
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent

def install(target,upgrade=False):
    meta=json.loads((ROOT/'edition.json').read_text(encoding='utf-8'));dest=Path(target).expanduser().resolve()/meta['name']
    if ROOT==dest:raise ValueError('请从解压后的交付包运行安装器，不要在已安装目录自我覆盖。')
    if dest.exists() and not upgrade:raise ValueError('已经安装；更新请使用 --upgrade。')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='insight-install-',dir=dest.parent) as tmp:
        stage=Path(tmp)/meta['name'];shutil.copytree(ROOT,stage,ignore=shutil.ignore_patterns('.env','workspace','.venv','__pycache__','*.pyc','*.zip'))
        preserve=dest if dest.exists() else None
        if preserve:
            if (preserve/'.env').exists():shutil.copy2(preserve/'.env',stage/'.env')
            if (preserve/'workspace').exists():shutil.copytree(preserve/'workspace',stage/'workspace')
            if dest.exists() and (dest/'.venv').exists():shutil.copytree(dest/'.venv',stage/'.venv',symlinks=True)
        if not (stage/'.env').exists():shutil.copy2(stage/'.env.example',stage/'.env')
        backup=None
        if dest.exists():
            backups=dest.parent/'.insight-backups';backups.mkdir(exist_ok=True)
            backup=backups/(dest.name+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));dest.rename(backup)
        try:shutil.move(str(stage),str(dest))
        except Exception:
            if backup and not dest.exists():backup.rename(dest)
            raise
    return {'installed':str(dest),'edition':meta['edition'],'backup':str(backup) if backup else None,'next':'在目标 .env 配置采集凭据及本地模型路径。'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--target',type=Path,default=Path.home()/'.codex/skills');ap.add_argument('--upgrade',action='store_true');a=ap.parse_args()
    if sys.version_info<(3,10):raise SystemExit('需要 Python 3.10 或更高版本')
    try:print(json.dumps(install(a.target,a.upgrade),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:raise SystemExit(str(e))
