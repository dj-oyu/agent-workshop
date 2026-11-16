import json, sys, unittest
import test_loop
import adaptive,loop
class AdaptiveTest(unittest.TestCase):
 setUp=test_loop.HarnessTests.setUp
 tearDown=test_loop.HarnessTests.tearDown
 task=test_loop.HarnessTests.task
 initialize=test_loop.HarnessTests.initialize
 def test_failure_reflection_revision_execution(self):
  t=self.task('one'); t['safe_retry']=True; t['command']=[sys.executable,'-c','raise SystemExit(1)']; self.initialize([t])
  planner=self.root/'planner.py'
  planner.write_text("import json,sys\np=json.load(sys.stdin)\nt=p['state']['plan']['tasks'][0]\nt['command']=[sys.executable,'-c',\"open('one','w').write('ok')\"]\nprint(json.dumps(dict(action='revise',task='one',replacement=t,diagnosis='exit 1; no output was produced',alternative='produce the required artifact instead of failing',expected_test='read exact artifact content')))\n")
  self.assertEqual(adaptive.cycle(self.state,[sys.executable,str(planner)],3),'complete')
  s=loop.read(self.state); self.assertEqual(s['tasks']['one']['attempts'],2); self.assertTrue(any(e['kind']=='reflection' for e in s['events']))
 def test_stale_planner_rejected(self):
  t=self.task('one'); t['safe_retry']=True; t['command']=[sys.executable,'-c','raise SystemExit(1)']; self.initialize([t])
  planner=self.root/'stale.py'
  planner.write_text("import json,sys\nfrom pathlib import Path\np=json.load(sys.stdin)\nf=Path("+repr(str(self.state))+")\ns=json.loads(f.read_text());s['lessons'].append('concurrent update');f.write_text(json.dumps(s))\nprint(json.dumps(dict(action='stop',diagnosis='x',alternative='y',expected_test='z')))\n")
  with self.assertRaisesRegex(ValueError,'stale planner'):
   adaptive.cycle(self.state,[sys.executable,str(planner)],2)
if __name__=='__main__': unittest.main()
