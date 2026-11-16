import unittest, json
import test_loop,loop,bridge
class BridgeTest(unittest.TestCase):
 setUp=test_loop.HarnessTests.setUp
 tearDown=test_loop.HarnessTests.tearDown
 task=test_loop.HarnessTests.task
 initialize=test_loop.HarnessTests.initialize
 def test_apply_once_and_match_id(self):
  self.initialize([self.task('one')]); req=self.root/'req.json'; res=self.root/'res.json'
  p=bridge.request(self.state,req); d=dict(action='continue',diagnosis='ready',alternative='execute pending task',expected_test='verify artifact')
  loop.save(res,dict(request_id='wrong',decision=d))
  with self.assertRaisesRegex(ValueError,'wrong request'): bridge.accept(self.state,req,res)
  loop.save(res,dict(request_id=p['request_id'],decision=d)); self.assertEqual(bridge.accept(self.state,req,res),'continue')
  with self.assertRaisesRegex(ValueError,'already applied'): bridge.accept(self.state,req,res)
 def test_stale_refused(self):
  self.initialize([self.task('one')]);req=self.root/'req.json';res=self.root/'res.json';p=bridge.request(self.state,req)
  loop.save(res,dict(request_id=p['request_id'],decision=dict(action='continue',diagnosis='ready',alternative='run',expected_test='artifact')))
  loop.run(self.state)
  with self.assertRaisesRegex(ValueError,'stale'): bridge.accept(self.state,req,res)
if __name__=='__main__': unittest.main()
