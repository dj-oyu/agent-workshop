#!/usr/bin/env python3
"""Agent decision adapter. Planner command is explicitly supplied by operator."""
import argparse, json, subprocess, sys
from pathlib import Path
import loop

def cycle(state,planner,max_rounds=5):
 for _ in range(max_rounds):
  s=loop.read(state)
  if s.get('control',{}).get('stopped'): return 'stopped'
  if all(v['status']=='done' for v in s['tasks'].values()): return 'complete'
  before=len(s['events']); loop.run(state,1); s=loop.read(state)
  if s.get('control',{}).get('stopped'): return 'stopped'
  if all(v['status']=='done' for v in s['tasks'].values()): return 'complete'
  packet={'brief':loop.resume(state),'state':s,'new_events':s['events'][before:],'questions':loop.QUESTIONS,
          'contract':'Return JSON: action continue|revise|stop, diagnosis, alternative, expected_test; revise includes task and replacement task object.'}
  # No implicit network access/model. The caller supplies a trusted local adapter.
  p=subprocess.run(planner,input=json.dumps(packet,ensure_ascii=False),text=True,capture_output=True,timeout=60,check=True)
  d=json.loads(p.stdout)
  for field in ('diagnosis','alternative','expected_test'):
   if not isinstance(d.get(field),str) or not d[field].strip(): raise ValueError('missing reflection: '+field)
  observed=loop.digest(s)
  with loop.locked(state):
   s=loop.read(state)
   if loop.digest(s)!=observed: raise ValueError('stale planner decision: state changed; observe again')
   loop.event(s,'reflection',decision=d)
   if d['action']=='revise':
    key=d['task']; old=next(t for t in s['plan']['tasks'] if t['id']==key); new=d['replacement']
    if s['tasks'][key]['status']!='stalled' or not old.get('safe_retry',False): raise ValueError('only safe stalled actions may be revised automatically')
    if new['id']!=key or new.get('authorized')!=old.get('authorized') or new.get('safe_retry')!=old.get('safe_retry'): raise ValueError('authorization flags cannot be changed; command authorization requires trusted adapter checks')
    if any(key in t.get('depends',[]) and s['tasks'][t['id']]['status']=='done' for t in s['plan']['tasks']): raise ValueError('completed dependents require a new run')
    if loop.digest(old)==loop.digest(new): raise ValueError('unchanged plan')
    s['plan']['tasks']=[new if t['id']==key else t for t in s['plan']['tasks']]; loop.validate(s['plan']); s['tasks'][key]['status']='pending'
   elif d['action'] not in ('continue','stop'): raise ValueError('invalid action')
   if d['action']=='stop': s['control']={'stopped':True,'reason':d['diagnosis'],'at':loop.now()}
   loop.save(state,s)
  if d['action']=='stop': return 'stopped'
  if d['action']=='continue' and not any(v['status']=='pending' for v in s['tasks'].values()): return 'blocked'
 return 'checkpoint'
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('state'); p.add_argument('--rounds',type=int,default=5); p.add_argument('planner',nargs=argparse.REMAINDER); a=p.parse_args()
 if a.planner and a.planner[0]=='--': a.planner=a.planner[1:]
 if not a.planner: p.error('trusted local planner argv is required')
 print(cycle(a.state,a.planner,a.rounds))
