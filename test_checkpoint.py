import json, pathlib, tempfile, unittest, zipfile, subprocess, sys
import checkpoint, loop
class CheckpointTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.base=pathlib.Path(self.t.name);self.old=self.base/'old';self.old.mkdir();self.state=self.old/'state.json';self.archive=self.base/'case.zip'
  plan={'goal':'resume','done_when':'two artifacts','tasks':[{'id':n,'owner':'test','next_action':'write','authorized':True,'depends':([] if n=='one' else ['one']),'command':['python3','-c',f"from pathlib import Path; Path('{n}').write_text('ok')"],'verify':['python3','-c',f"from pathlib import Path; assert Path('{n}').read_text()=='ok'"]} for n in ['one','two']]}
  (self.old/'plan.json').write_text(json.dumps(plan));loop.init(self.old/'plan.json',self.state);loop.run(self.state,1)
 def tearDown(self): self.t.cleanup()
 def test_empty_directory_restore_pending_only(self):
  checkpoint.export(self.state,self.archive,['one']);new=self.base/'new';s=checkpoint.restore(self.archive,new);out=loop.run(s);self.assertEqual(out['tasks']['one']['status'],'unknown');self.assertEqual(out['tasks']['two']['status'],'pending');subprocess.run([sys.executable,str(pathlib.Path(loop.__file__).resolve()),'reconcile',str(s),'--task','one','--note','Inspect portable artifact using trusted read-only verifier'],check=True);out=loop.run(s);self.assertEqual(out['tasks']['one']['attempts'],1);self.assertEqual(out['tasks']['two']['attempts'],1);self.assertTrue(all(v['status']=='done' for v in out['tasks'].values()));self.assertTrue((new/'two').exists());self.assertFalse((self.old/'two').exists())
 def test_missing_artifact_never_done(self):
  checkpoint.export(self.state,self.archive,[]);new=self.base/'new';state=checkpoint.restore(self.archive,new);out=loop.run(state);self.assertEqual(out['tasks']['one']['status'],'unknown');self.assertEqual(out['tasks']['two']['status'],'pending');subprocess.run([sys.executable,str(pathlib.Path(loop.__file__).resolve()),'reconcile',str(state),'--task','one','--note','Read-only verification of missing artifact'],check=True);out=loop.read(state);self.assertEqual(out['tasks']['one']['status'],'unknown');self.assertEqual(out['tasks']['one']['attempts'],1);self.assertFalse((new/'one').exists())
 def test_no_overwrite(self):
  checkpoint.export(self.state,self.archive,['one']);self.assertRaises(ValueError,checkpoint.restore,self.archive,self.old)
 def test_tamper(self):
  checkpoint.export(self.state,self.archive,['one']);bad=self.base/'bad.zip'
  with zipfile.ZipFile(self.archive) as src,zipfile.ZipFile(bad,'w') as dst:
   for n in src.namelist(): dst.writestr(n,b'bad' if n=='one' else src.read(n))
  self.assertRaises(ValueError,checkpoint.restore,bad,self.base/'new')
 def test_traversal(self):
  self.assertRaises(ValueError,checkpoint.export,self.state,self.archive,['../outside'])
if __name__=='__main__':unittest.main()
