import json, os, signal, subprocess, sys, tempfile, time, unittest
from pathlib import Path
import loop

class HarnessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.state=self.root/'state.json'; self.plan=self.root/'plan.json'
 def tearDown(self): self.tmp.cleanup()
 def task(self,key,depends=()):
  return dict(id=key,owner='runner',next_action='create and verify '+key,authorized=True,depends=list(depends),command=[sys.executable,'-c',f"open('{key}','w').write('ok')"],verify=[sys.executable,'-c',f"assert open('{key}').read()=='ok'"])
 def initialize(self,tasks):
  self.plan.write_text(json.dumps(dict(goal='verified artifacts',done_when='all artifact contents verified',tasks=tasks))); loop.init(self.plan,self.state)
 def test_multicycle_resume(self):
  self.initialize([self.task('one'),self.task('two',['one']),self.task('three',['two'])])
  loop.run(self.state,1); self.assertEqual(loop.read(self.state)['tasks']['two']['status'],'pending')
  result=loop.run(self.state,10); self.assertTrue(all(x['status']=='done' for x in result['tasks'].values())); self.assertEqual(len([e for e in result['events'] if e['kind']=='done']),3)
  self.assertIn('sha256=',loop.resume(self.state))
 def test_stall_no_repeat_independent_continues(self):
  bad=self.task('bad'); bad['safe_retry']=True; bad['command']=[sys.executable,'-c','raise SystemExit(1)']
  self.initialize([bad,self.task('independent')]); loop.run(self.state); loop.run(self.state)
  s=loop.read(self.state); self.assertEqual(s['tasks']['bad']['attempts'],1); self.assertEqual(s['tasks']['independent']['status'],'done')
 def test_missing_authorization(self):
  t=self.task('one'); t['authorized']=False; self.initialize([t]); s=loop.run(self.state); self.assertEqual(s['tasks']['one']['status'],'blocked'); self.assertFalse((self.root/'one').exists())
 def test_real_crash_reconciliation(self):
  t=self.task('one'); t['command']=[sys.executable,'-c',"import time; open('one','w').write('ok'); time.sleep(30)"]
  self.initialize([t]); cli=Path(loop.__file__).resolve(); proc=subprocess.Popen([sys.executable,str(cli),'run',str(self.state)],start_new_session=True)
  try:
   deadline=time.monotonic()+5
   while not (self.root/'one').exists() and time.monotonic()<deadline: time.sleep(.02)
   self.assertTrue((self.root/'one').exists()); os.killpg(proc.pid,signal.SIGKILL); proc.wait()
   subprocess.run([sys.executable,str(cli),'unlock',str(self.state)],check=True)
   s=loop.run(self.state); self.assertEqual(s['tasks']['one']['status'],'unknown'); self.assertEqual(s['tasks']['one']['attempts'],1)
   subprocess.run([sys.executable,str(cli),'reconcile',str(self.state),'--task','one','--note','Action artifact inspected; verification only'],check=True)
   self.assertEqual(loop.read(self.state)['tasks']['one']['status'],'done')
  finally:
   if proc.poll() is None: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
 def test_no_overwrite(self):
  self.initialize([self.task('one')]); self.assertRaises(ValueError,loop.init,self.plan,self.state)
if __name__=='__main__': unittest.main()
