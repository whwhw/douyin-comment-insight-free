#!/usr/bin/env python3
"""Fetch one Douyin account, its recent works, and first-level comments."""
from __future__ import annotations
import argparse, json, os, re, time, hashlib
from runtime import atomic_json
import requests
from datetime import datetime, timezone
from pathlib import Path
from work_insight import normalize_work

from runtime import load_env as load_project_env

load_project_env()

BASE='https://api.tikhub.io'
SEARCH='/api/v1/douyin/search/fetch_user_search'
PROFILE='/api/v1/douyin/app/v3/handler_user_profile'
POSTS='/api/v1/douyin/app/v3/fetch_user_post_videos'
COMMENTS='/api/v1/douyin/app/v3/fetch_video_comments'
MIN_REQUEST_INTERVAL=1.0
_last_request=0.0
CACHE_DIR=None

def request(path, token, *, method='GET', params=None, body=None):
    global _last_request
    cache_key=hashlib.sha256(json.dumps([BASE,path,method,params,body],sort_keys=True).encode()).hexdigest()
    cache_path=CACHE_DIR/(cache_key+'.json') if CACHE_DIR else None
    if cache_path and cache_path.exists():return json.loads(cache_path.read_text(encoding='utf-8'))
    url=BASE+path
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','User-Agent':'curl/8.0'}
    err=None
    for attempt in range(3):
        wait=MIN_REQUEST_INTERVAL-(time.monotonic()-_last_request)
        if wait>0: time.sleep(wait)
        try:
            _last_request=time.monotonic()
            response=requests.request(method,url,params=params,json=body,headers=headers,timeout=60)
            if response.status_code >= 400:
                response.raise_for_status()
            result=response.json()
            if result.get('code') not in (None,0,200):raise ValueError('API returned a non-success payload')
            if cache_path:atomic_json(cache_path,result)
            return result
        except requests.HTTPError as e:
            err=e
            # Do not immediately hammer a throttled or unstable endpoint.
            if e.response is not None and e.response.status_code in (429, 500, 502, 503, 504):
                if attempt<2: time.sleep((30,60,120)[attempt])
            else: break
        except (requests.RequestException, ValueError) as e:
            err=e
            if attempt<2: time.sleep((30,60,120)[attempt])
    raise RuntimeError(f'{path}: {type(err).__name__}; 检查网络、凭据、额度及请求参数，可续跑')

def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values(): yield from walk(x)
    elif isinstance(v,list):
        for x in v: yield from walk(x)

def first_user(payload, account):
    candidates=[]
    for x in walk(payload):
        raw_data=x.get('raw_data')
        if isinstance(raw_data,str):
            try:
                decoded=json.loads(raw_data).get('user_info',{})
                if decoded: candidates.append((str(decoded.get('unique_id') or '').strip(),decoded))
            except (ValueError,TypeError):
                pass
        uid=str(x.get('unique_id') or x.get('short_id') or '').strip()
        nickname=x.get('nickname') or x.get('nick_name')
        if nickname: candidates.append((uid,x))
    exact=[x for uid,x in candidates if uid==account]
    # Never assume the first search result is the requested account.
    unique={str(x.get('sec_uid') or x.get('sec_user_id') or x.get('user_id') or x.get('uid')):x for x in exact}
    if len(unique)==1:return next(iter(unique.values()))
    raise RuntimeError(f'无法唯一核验抖音号：{account}；请提供真实抖音号或可核验主页信息')

def user_value(u,*keys):
    for k in keys:
        if u.get(k) not in (None,''): return u[k]
    return ''

def avatar_value(user):
    """Read both legacy flat avatar URLs and TikHub's nested url_list fields."""
    direct=user_value(user,'avatar_url')
    if isinstance(direct,str) and direct.startswith(('http://','https://')): return direct
    for key in ('avatar_300x300','avatar_medium','avatar_thumb','avatar_larger','avatar_168x168'):
        value=user.get(key)
        if isinstance(value,dict):
            urls=value.get('url_list') or []
            if isinstance(urls,list):
                # Prefer broadly supported JPEG/WebP-like URLs over HEIC variants.
                candidates=[url for url in urls if isinstance(url,str) and url.startswith(('http://','https://'))]
                compatible=next((url for url in candidates if '.heic' not in url.lower()),None)
                if compatible or candidates: return compatible or candidates[0]
    return ''

def post_items(payload):
    """Return unique post objects without mistaking nested statistic objects for works."""
    rows=[]; seen=set()
    for x in walk(payload):
        aid=str(user_value(x,'aweme_id','item_id','group_id'))
        if aid and aid not in seen and isinstance(x.get('statistics'),dict) and (x.get('desc') is not None or x.get('video') is not None):
            seen.add(aid); rows.append(x)
    return rows

def next_cursor(payload):
    for x in walk(payload):
        if x.get('has_more') in (1,True,'1'):
            cursor=x.get('max_cursor') or x.get('cursor')
            if cursor not in (None,''): return cursor
    return None

def main():
    global BASE, CACHE_DIR
    ap=argparse.ArgumentParser(); ap.add_argument('account'); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--works',type=int,default=30); ap.add_argument('--comments',type=int,default=100); ap.add_argument('--api-key-env',default='TIKHUB_API_KEY'); ap.add_argument('--base-url',default=os.getenv('TIKHUB_BASE_URL','https://api.tikhub.dev')); args=ap.parse_args()
    BASE=args.base_url.rstrip('/')
    token=os.getenv(args.api_key_env,'').strip()
    if not token: raise SystemExit('TIKHUB_API_KEY 未配置')
    args.out.mkdir(parents=True,exist_ok=True)
    CACHE_DIR=args.out/'request-cache';CACHE_DIR.mkdir(exist_ok=True)
    started=datetime.now(timezone.utc).isoformat(); result={'accountId':args.account,'startedAt':started,'source':{'provider':'TikHub','commentLevel':'一级评论'},'warnings':[],'errors':[]}
    search=request(SEARCH,token,method='POST',body={'keyword':args.account,'cursor':0,'douyin_user_fans':'','douyin_user_type':'','search_id':''}); (args.out/'search.json').write_text(json.dumps(search,ensure_ascii=False,indent=2))
    user=first_user(search,args.account); sec=user_value(user,'sec_uid','sec_user_id','user_id');
    if not sec: raise RuntimeError(f'账号缺少 sec_user_id：{args.account}')
    prof=request(PROFILE,token,params={'sec_user_id':sec}); (args.out/'profile.json').write_text(json.dumps(prof,ensure_ascii=False,indent=2))
    p=next((x for x in walk(prof) if x.get('nickname') or x.get('nick_name')),user)
    profile_account=str(p.get('unique_id') or p.get('short_id') or '')
    if profile_account and profile_account!=args.account:raise RuntimeError('主页抖音号与请求不一致，停止采集')
    result['profile']={'displayName':user_value(p,'nickname','nick_name') or user_value(user,'nick_name','nickname'),'secUserId':sec,'avatar':avatar_value(p) or avatar_value(user),'followers':user_value(p,'follower_count','fans_count','fans_cnt') or user_value(user,'fans_cnt'),'works':user_value(p,'aweme_count','publish_count','publish_cnt') or user_value(user,'publish_cnt'),'bio':user_value(p,'signature','desc')}
    from progress import progress, label
    progress(f"已确认账号：{label(result['profile']['displayName'])}；正在获取作品列表……")
    pages=[]; raw_works=[]; seen=set(); cursor=0
    for _ in range(2):
        posts=request(POSTS,token,params={'sec_user_id':sec,'max_cursor':cursor,'count':min(20,max(1,args.works-len(raw_works))),'sort_type':0})
        pages.append(posts)
        for item in post_items(posts):
            aid=str(user_value(item,'aweme_id','item_id','group_id'))
            if aid not in seen: seen.add(aid); raw_works.append(item)
        if len(raw_works)>=args.works: break
        cursor=next_cursor(posts)
        if cursor is None: break
    (args.out/'posts.json').write_text(json.dumps({'pages':pages},ensure_ascii=False,indent=2))
    works=[normalize_work(item) for item in raw_works[:args.works]]
    comments=[];seen_comments=set()
    for index,w in enumerate(works,1):
        progress(f"[{index}/{len(works)}] 正在获取评论：{label(w.get('title'))}")
        try:
            payload=request(COMMENTS,token,params={'aweme_id':w['awemeId'],'cursor':0,'count':args.comments});
            work_comments=[]
            for x in walk(payload):
                text=x.get('text'); cid=x.get('cid') or x.get('comment_id')
                if text and cid and str(cid) not in seen_comments:
                    seen_comments.add(str(cid));work_comments.append({'commentId':str(cid),'awemeId':w['awemeId'],'text':str(text),'createTime':x.get('create_time',0),'diggCount':x.get('digg_count',0)})
            comments.extend(work_comments[:args.comments])
        except Exception as e:
            result['warnings'].append(f"作品 {w['awemeId']} 评论采集失败：{e}")
            progress(f"评论获取失败（{type(e).__name__}）；跳过此作品的评论，继续采集其余作品。", status="warning")
    result.update({'works':works,'comments':comments[:args.comments*args.works],'source':{'provider':'TikHub','worksFetched':len(works),'commentsFetched':len(comments[:args.comments*args.works]),'commentLevel':'一级评论'}})
    (args.out/'collected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)); print(json.dumps({'account':args.account,'works':len(works),'comments':len(result['comments']),'out':str(args.out)},ensure_ascii=False))
if __name__=='__main__': main()
