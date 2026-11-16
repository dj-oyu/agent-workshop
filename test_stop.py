import json, pathlib, subprocess, sys, unittest
import loop,bridge,adaptive,test_loop,checkpoint
class StopTests(unittest.TestCase):
 setUp=test_loop.HarnessTests.setUp
 tearDown=test_loop.HarnessTests.tearDown
 task=test_loop.HarnessTests.task
 initialize=test_loop.HarnessTests.initialize
 def cli(self,op):
  subprocess.run([sys.executable,str(pathlib.Path(loop.__file__).resolve()),op,str(self.state),'--note','explicit test operator decision'],check=True)
 def test_bridge_stop_survives_new_process_and_continue(self):
  self.initialize([self.task('one')]);req=self.root/'req.json';res=self.root/'res.json';p=bridge.request(self.state,req);d=dict(action='stop',diagnosis='stop condition',alternative='remain stopped',expected_test='no output')
  loop.save(res,dict(request_id=p['request_id'],decision=d));bridge.accept(self.state,req,res)
  subprocess.run([sys.executable,str(pathlib.Path(loop.__file__).resolve()),'run',str(self.state)],check=True)
  self.assertFalse((self.root/'one').exists());self.assertEqual(loop.read(self.state)['tasks']['one']['attempts'],0)
  p=bridge.request(self.state,req);d['action']='continue';loop.save(res,dict(request_id=p['request_id'],decision=d))
  with self.assertRaisesRegex(ValueError,'stopped'):bridge.accept(self.state,req,res)
  self.cli('unpause');loop.run(self.state);self.assertTrue((self.root/'one').exists())
 def test_adaptive_stop_is_persistent(self):
  self.initialize([self.task('one'),self.task('two')]);planner=[sys.executable,'-c',"import json;print(json.dumps(dict(action='stop',diagnosis='stop now',alternative='wait',expected_test='no second artifact')))"]
  self.assertEqual(adaptive.cycle(self.state,planner),'stopped');loop.run(self.state);self.assertFalse((self.root/'two').exists());self.assertEqual(adaptive.cycle(self.state,['nonexistent-command']),'stopped')
 def test_checkpoint_preserves_stop(self):
  self.initialize([self.task('one')]);self.cli('stop');archive=self.root/'case.zip';checkpoint.export(self.state,archive,[]);s=checkpoint.restore(archive,self.root/'restored');loop.run(s);self.assertTrue(loop.read(s)['control']['stopped']);self.assertEqual(loop.read(s)['tasks']['one']['attempts'],0)
if __name__=='__main__':unittest.main()
