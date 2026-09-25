"""Export one account only, with shared assets and no machine-specific evidence paths."""
from __future__ import annotations
import argparse,json,re,zipfile
from pathlib import Path
from runtime import WORKSPACE,valid_account

def export(account,output,site):
    account=valid_account(account);site=Path(site).resolve();output=Path(output).resolve()
    index=json.loads((site/'comment-insight-index.json').read_text(encoding='utf-8'));row=next((r for r in index['reports'] if r['accountId']==account),None)
    if not row:raise ValueError('该账号尚未发布报告')
    page=(site/f'{account}.html').read_text(encoding='utf-8');match=re.search(r'const pageData=(.*?);\s*/\* INSIGHT_DATA_END',page,re.S)
    if not match:raise ValueError('报告数据格式无效')
    data=json.loads(match.group(1))
    def clean(v):
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ('spokenScriptPath','asrMetadataPath','subtitlePath','sourceAnalysis')}
        if isinstance(v,list):return [clean(x) for x in v]
        return v
    data=clean(data);blob=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    page=page[:match.start(1)]+blob+page[match.end(1):]
    paths=set()
    for v in [data.get('avatar'),*(w.get('cover') for w in data.get('works',[]))]:
        if isinstance(v,str) and v.startswith('assets/'):
            p=(site/v).resolve()
            if not p.is_relative_to(site):raise ValueError('资源路径越界')
            if p.is_file():paths.add(p)
    for folder in ('assets/ui','assets/icons'):
        paths.update(p for p in (site/folder).rglob('*') if p.is_file())
    index['reports']=[row]
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix(output.suffix+'.tmp')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'{account}.html',page)
        homepage=(site/'comment-insight-index.html').read_text(encoding='utf-8')
        z.writestr('index.html',homepage);z.writestr('comment-insight-index.html',homepage)
        z.writestr('comment-insight-index-data.js','window.COMMENT_INSIGHT_INDEX='+json.dumps(index,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n')
        z.writestr('comment-insight-index.json',json.dumps(index,ensure_ascii=False,indent=2))
        for p in sorted(paths):z.write(p,p.relative_to(site))
    temp.replace(output);return {'accountId':account,'archive':str(output),'entrypoint':'index.html','note':'包含本账号原始评论与分析；分享前自行核对。远程封面和CDN动效受网络影响，主体内容已嵌入。'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--account',required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--site',type=Path,default=WORKSPACE/'site');a=ap.parse_args()
    print(json.dumps(export(a.account,a.output,a.site),ensure_ascii=False,indent=2))
