#!/usr/bin/env python3
"""Bounded evidence-producing workflow runner, Python 3 stdlib only."""
import contextlib
import argparse, datetime, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

QUESTIONS = [
 '本人が必要とする成果と観測可能な完了条件は何か。質問への返答だけで終えていないか。',
 '事実・仮説・不明を分離したか。次の行動でどの不確実性を減らすか。',
 '同じ観測を繰り返すだけになっていないか。失敗仮説と代替案は何か。',
 '既存許可で独立して進められる工程は何か。本人しか決められないことは何か。',
 '完了を証明する成果物・同一版の検証・保存先は何か。担当終了を完了扱いしていないか。',
 '次の担当がコマンド1つで文脈と未完工程を復元できるか。'
]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def save(path,data):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.state-')
 try:
  with os.fdopen(fd,'w') as f:
   json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
def read(path): return json.loads(Path(path).read_text())
def validate(plan):
 if not plan.get('goal') or not plan.get('done_when'): raise ValueError('goal and done_when required')
 tasks=plan['tasks']; ids=[t['id'] for t in tasks]
 if not tasks or len(set(ids))!=len(ids): raise ValueError('unique nonempty tasks required')
 for t in tasks:
  if not re.fullmatch(r'[A-Za-z0-9_-]+',t['id']): raise ValueError('unsafe task id')
  if not isinstance(t.get('timeout',60),(int,float)) or t.get('timeout',60)<=0: raise ValueError('positive timeout required')
  if not t.get('owner') or not t.get('next_action'): raise ValueError('owner and next_action required')
  for key in ('command','verify'):
   if not isinstance(t.get(key),list) or not t[key] or not all(isinstance(x,str) for x in t[key]): raise ValueError(key+' must be nonempty argv')
  if any(d not in ids or d==t['id'] for d in t.get('depends',[])): raise ValueError('bad dependency')
 visited=set()
 while len(visited)<len(ids):
  ready={t['id'] for t in tasks if set(t.get('depends',[]))<=visited}-visited
  if not ready: raise ValueError('dependency cycle')
  visited |= ready
 return plan

def init(plan_path,state):
 if Path(state).exists(): raise ValueError('state exists; refusing overwrite')
 plan=validate(read(plan_path)); root=str(Path(plan_path).resolve().parent)
 save(state,dict(version=1,goal=plan['goal'],done_when=plan['done_when'],root=root,plan=plan,
                 tasks={t['id']:{'status':'pending','attempts':0} for t in plan['tasks']},events=[],lessons=[],created=now()))
def event(s,kind,**data): s['events'].append(dict(at=now(),kind=kind,**data))
def execute(argv,cwd,timeout,log):
 # No shell interpretation. Commands must already be within operator authorization.
 try:
  with open(log,'w') as output:
   p=subprocess.run(argv,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,timeout=timeout,check=False)
  rc=p.returncode
 except subprocess.TimeoutExpired: rc=124
 except OSError as e: Path(log).write_text(str(e)); rc=127
 return dict(argv=argv,returncode=rc,log=str(log),sha256=hashlib.sha256(Path(log).read_bytes()).hexdigest(),at=now())
@contextlib.contextmanager
def locked(state):
 lock=Path(state).resolve().with_suffix('.lock')
 try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError: raise ValueError('lock exists: inspect process before using unlock')
 os.write(fd,str(os.getpid()).encode()); os.close(fd)
 try: yield
 finally: lock.unlink(missing_ok=True)
def run(state,max_steps=20):
 state=Path(state).resolve()
 with locked(state):
  s=read(state); validate(s['plan'])
  if s.get('control',{}).get('stopped'): return s
  logs=state.parent/(state.stem+'-logs'); logs.mkdir(exist_ok=True)
  # A crashed action may have taken effect. Never repeat it blindly.
  for k,v in s['tasks'].items():
   if v['status']=='running': v['status']='unknown'; event(s,'reconcile_required',task=k)
  save(state,s)
  for _ in range(max_steps):
   ready=[t for t in s['plan']['tasks'] if s['tasks'][t['id']]['status']=='pending' and all(s['tasks'][d]['status']=='done' for d in t.get('depends',[]))]
   if not ready: break
   t=ready[0]; v=s['tasks'][t['id']]
   if not t.get('authorized',False):
    v['status']='blocked'; v['reason']='No recorded authorization'; event(s,'blocked',task=t['id']); save(state,s); continue
   v.update(status='running',attempts=v['attempts']+1,started=now()); event(s,'started',task=t['id'],spec=t); save(state,s)
   prefix=logs/(t['id'].replace('/','_')+'-'+str(v['attempts']))
   result=execute(t['command'],s['root'],t.get('timeout',60),str(prefix)+'.action.log'); v['action']=result
   # Save action result before verifier, so an interruption remains reconcilable.
   save(state,s)
   if result['returncode']==0:
    v['verification']=execute(t['verify'],s['root'],t.get('timeout',60),str(prefix)+'.verify.log')
    v['status']='done' if v['verification']['returncode']==0 else ('stalled' if t.get('safe_retry',False) else 'unknown')
   else: v['status']='stalled' if t.get('safe_retry',False) else 'unknown'
   v['reason']='' if v['status']=='done' else 'Action or verification failed: inspect evidence, revise hypothesis/plan; no automatic identical retry'
   event(s,v['status'],task=t['id'],evidence=dict(v)); save(state,s)
  event(s,'checkpoint',complete=all(v['status']=='done' for v in s['tasks'].values())); save(state,s)
 return s

def resume(state):
 s=read(state)
 lines=['# 再開ブリーフ', '実行制御: '+('STOPPED (explicit unpause required)' if s.get('control',{}).get('stopped') else 'active'), '目的: '+s['goal'],'完了条件: '+s['done_when']]
 for t in s['plan']['tasks']:
  v=s['tasks'][t['id']]; lines.append(f"- {t['id']}: {v['status']} / 担当 {t['owner']} / 次 {t['next_action']}")
  if v.get('reason'): lines.append('  障害: '+v['reason'])
  for k in ('action','verification'):
   if v.get(k): lines.append(f"  {k}: exit={v[k]['returncode']} log={v[k]['log']} sha256={v[k]['sha256']}")
 lines+=['## 自問・計画更新']+['- '+q for q in QUESTIONS]+['## 学習済み']+['- '+x for x in s['lessons']]
 if all(v['status']=='done' for v in s['tasks'].values()): lines.append('登録済み全工程の検証成功。計画外の実機性能等を証明したものではありません。')
 return '\n'.join(lines)
def main():
 p=argparse.ArgumentParser(); p.add_argument('op',choices=['init','run','resume','revise','reconcile','learn','unlock','stop','unpause']); p.add_argument('state'); p.add_argument('--plan'); p.add_argument('--task'); p.add_argument('--note'); p.add_argument('--steps',type=int,default=20); a=p.parse_args()
 try:
  if a.op=='init':
   with locked(a.state): init(a.plan,a.state)
  elif a.op=='run':
   if a.steps<1: raise ValueError('steps must be positive')
   run(a.state,a.steps)
  elif a.op=='resume': print(resume(a.state))
  elif a.op=='unlock':
   lock=Path(a.state).resolve().with_suffix('.lock'); pid=int(lock.read_text())
   try: os.kill(pid,0)
   except ProcessLookupError: lock.unlink()
   else: raise ValueError('process still alive; refusing unlock')
  else:
   with locked(a.state):
    s=read(a.state)
    if not a.note: raise ValueError('a reason/lesson is required with --note')
    if s.get('control',{}).get('stopped') and a.op not in ('learn','unpause','stop'): raise ValueError('workflow stopped: explicit unpause required')
    if a.op=='stop': s['control']={'stopped':True,'reason':a.note,'at':now()}
    elif a.op=='unpause': s['control']={'stopped':False,'reason':a.note,'at':now()}
    elif a.op=='learn': s['lessons'].append(a.note)
    elif a.op=='revise':
     plan=validate(read(a.plan)); old=next(t for t in s['plan']['tasks'] if t['id']==a.task); new=next(t for t in plan['tasks'] if t['id']==a.task)
     if s['tasks'][a.task]['status'] in ('running','unknown'): raise ValueError('reconcile uncertain action first')
     if digest(old)==digest(new): raise ValueError('unchanged plan: identical retry refused')
     if any(a.task in t.get('depends',[]) and s['tasks'][t['id']]['status']=='done' for t in s['plan']['tasks']): raise ValueError('completed dependents: create a new plan/run')
     s['plan']['tasks']=[new if t['id']==a.task else t for t in s['plan']['tasks']]; validate(s['plan']); s['tasks'][a.task]['status']='pending'
    else:
     t=next(t for t in s['plan']['tasks'] if t['id']==a.task); v=s['tasks'][a.task]
     if v['status']!='unknown': raise ValueError('reconcile only unknown actions')
     log=Path(a.state).resolve().parent/(a.task.replace('/','_')+'-reconcile.log')
     v['verification']=execute(t['verify'],s['root'],t.get('timeout',60),log)
     v['status']='done' if v['verification']['returncode']==0 else 'unknown'
    event(s,a.op,task=a.task,note=a.note); save(a.state,s)
 except (ValueError,KeyError,TypeError,OSError) as e: print(str(e),file=sys.stderr); return 2
 return 0
if __name__=='__main__': sys.exit(main())
