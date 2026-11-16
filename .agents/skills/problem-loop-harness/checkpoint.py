#!/usr/bin/env python3
"""Explicit-file portable checkpoints. Trusted plans only; restore never executes."""
import argparse, hashlib, json, os, tempfile, zipfile
from pathlib import Path, PurePosixPath
import loop

def safe(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts: raise ValueError('unsafe archive path')
 return p

def export(state, archive, includes):
 state=Path(state).resolve(); archive=Path(archive)
 if archive.exists(): raise ValueError('archive exists')
 with loop.locked(state):
  s=loop.read(state); root=Path(s['root']).resolve()
  if state.parent!=root: raise ValueError('state must reside in workspace root')
  if any(v['status']=='running' for v in s['tasks'].values()): raise ValueError('reconcile running work before export')
  # Do not silently rewrite commands or operational permission records.
  for t in s['plan']['tasks']:
   if any(str(root) in a for k in ('command','verify') for a in t[k]): raise ValueError('workspace absolute command path is not portable')
  files={}
  def add(path):
   if path.is_symlink(): raise ValueError('symlink input')
   real=path.resolve(); rel=real.relative_to(root).as_posix(); safe(rel)
   if not real.is_file(): raise ValueError('explicit regular files required')
   if rel.endswith('.lock') or rel in {state.name,'state.json','manifest.json'}: raise ValueError('reserved file')
   files[rel]=real.read_bytes()
  for name in includes:
   safe(name); add(root/name)
  def logs(v):
   if isinstance(v,dict):
    for k,x in list(v.items()):
     if k=='log' and isinstance(x,str):
      p=Path(x).resolve(); add(p); v[k]={'checkpoint_log':p.relative_to(root).as_posix()}
     else: logs(x)
   elif isinstance(v,list):
    for x in v: logs(x)
  logs(s); s['root']='CHECKPOINT_ROOT'
  files['state.json']=json.dumps(s,ensure_ascii=False,indent=2).encode()
  manifest={'version':1,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()},'warning':'Trusted plan only. Integrity hashes do not grant permission. Review operational data before sharing.'}
  with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
   for n,b in files.items(): z.writestr(n,b)
   z.writestr('manifest.json',json.dumps(manifest,indent=2))
 return manifest

def restore(archive,destination):
 dest=Path(destination).absolute()
 if dest.exists(): raise ValueError('destination must not exist')
 with zipfile.ZipFile(archive) as z:
  names=z.namelist()
  if len(names)!=len(set(names)): raise ValueError('duplicate entries')
  for n in names: safe(n)
  if sum(i.file_size for i in z.infolist())>64*1024*1024: raise ValueError('checkpoint too large')
  m=json.loads(z.read('manifest.json'))
  if m['version']!=1 or set(names)!=set(m['files'])|{'manifest.json'}: raise ValueError('manifest mismatch')
  data={n:z.read(n) for n in m['files']}
  if any(hashlib.sha256(b).hexdigest()!=m['files'][n] for n,b in data.items()): raise ValueError('hash mismatch')
 s=json.loads(data['state.json']); loop.validate(s['plan'])
 if s['root']!='CHECKPOINT_ROOT': raise ValueError('unexpected root')
 def paths(v):
  if isinstance(v,dict):
   for k,x in list(v.items()):
    if k=='log' and isinstance(x,dict) and set(x)=={'checkpoint_log'}:
     n=x['checkpoint_log']; safe(n)
     if n not in data: raise ValueError('missing evidence')
     v[k]=str(dest/n)
    else: paths(x)
  elif isinstance(v,list):
   for x in v: paths(x)
 paths(s); s['root']=str(dest)
 for v in s['tasks'].values():
  if v['status'] in ('running','done'):
   v['status']='unknown'
   v['reason']='Restored into a new environment: explicitly reconcile with a trusted read-only verifier before accepting prior completion; do not replay the action.'
 loop.event(s,'checkpoint_restored',source_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest())
 data['state.json']=json.dumps(s,ensure_ascii=False,indent=2).encode()
 dest.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=dest.parent,prefix='.restore-') as tmp:
  staging=Path(tmp)/'workspace'; staging.mkdir()
  for n,b in data.items():
   p=staging/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
  os.rename(staging,dest)
 return dest/'state.json'

if __name__=='__main__':
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='op',required=True)
 e=sub.add_parser('export'); e.add_argument('state'); e.add_argument('archive'); e.add_argument('--include',action='append',default=[])
 r=sub.add_parser('restore'); r.add_argument('archive'); r.add_argument('destination')
 a=p.parse_args()
 if a.op=='export': print(json.dumps(export(a.state,a.archive,a.include),indent=2))
 else: print(restore(a.archive,a.destination))
