#!/usr/bin/env python3
"""File protocol for a root agent bridging official task/notification tools.
No credentials, model API, scheduler, or network calls in this module.
"""
import argparse, json
from pathlib import Path
import loop

def request(state,output):
 s=loop.read(state); digest=loop.digest(s)
 packet=dict(version=1,request_id=digest,state_digest=digest,created=loop.now(),
  brief=loop.resume(state),state=s,questions=loop.QUESTIONS,
  contract={'response':'request_id, decision', 'decision':'action continue|revise|stop; diagnosis; alternative; expected_test; revise: task and replacement',
   'boundary':'Do not expand permission. Do not repeat unknown effects. Reply with JSON only. Public/private data boundaries remain unchanged.'})
 loop.save(output,packet); return packet

def accept(state,request_file,response_file):
 packet=loop.read(request_file); response=loop.read(response_file)
 if response.get('request_id')!=packet['request_id']: raise ValueError('wrong request id')
 d=response['decision']
 for k in ('diagnosis','alternative','expected_test'):
  if not isinstance(d.get(k),str) or not d[k].strip(): raise ValueError('missing reflection '+k)
 with loop.locked(state):
  s=loop.read(state)
  if any(e.get('request_id')==packet['request_id'] for e in s['events']): raise ValueError('already applied')
  if loop.digest(s)!=packet['state_digest']: raise ValueError('stale decision')
  if s.get('control',{}).get('stopped') and d['action']!='stop': raise ValueError('workflow stopped: explicit unpause required')
  if d['action']=='revise':
   key=d['task']; old=next(t for t in s['plan']['tasks'] if t['id']==key); new=d['replacement']
   if s['tasks'][key]['status']!='stalled' or not old.get('safe_retry'): raise ValueError('uncertain effects require reconciliation')
   if new['id']!=key or new.get('authorized')!=old.get('authorized') or new.get('safe_retry')!=old.get('safe_retry'): raise ValueError('cannot change authorization flags')
   if loop.digest(old)==loop.digest(new): raise ValueError('unchanged plan')
   if any(key in t.get('depends',[]) and s['tasks'][t['id']]['status']=='done' for t in s['plan']['tasks']): raise ValueError('completed dependents require new run')
   s['plan']['tasks']=[new if t['id']==key else t for t in s['plan']['tasks']]; loop.validate(s['plan']); s['tasks'][key]['status']='pending'
  elif d['action'] not in ('continue','stop'): raise ValueError('invalid decision')
  if d['action']=='stop': s['control']={'stopped':True,'reason':d['diagnosis'],'at':loop.now()}
  loop.event(s,'planner_decision',request_id=packet['request_id'],decision=d); loop.save(state,s)
 return d['action']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('op',choices=['request','accept']);p.add_argument('state');p.add_argument('request_file');p.add_argument('response_file',nargs='?');a=p.parse_args()
 if a.op=='request': print(json.dumps(request(a.state,a.request_file),ensure_ascii=False))
 else: print(accept(a.state,a.request_file,a.response_file))
