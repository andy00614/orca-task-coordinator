"""Offline packaging checks: subprocess is mocked; no Orca/Git execution."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import launch_task as launcher
import startup_bench as bench

class PackagingTests(unittest.TestCase):
    def args(self, root, *extra):
        return ['launch_task.py','--name','fixture-task','--repo-id','fixture-repo',
                '--fetch-worktree',str(root),'--prompt-text','请检查测试文案','--collect-seconds','0',*extra]

    def test_import_has_no_subprocess_side_effect(self):
        with patch('subprocess.run',side_effect=AssertionError('unexpected process')) as run:
            importlib.reload(bench);importlib.reload(launcher)
        run.assert_not_called()

    def test_missing_repo_rejected_before_side_effect(self):
        with patch.object(sys,'argv',['launch_task.py','--name','x','--fetch-worktree','/fixture','--prompt-text','x']), patch('subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):launcher.main()
        run.assert_not_called()

    def test_bad_timestamp_rejected_before_side_effect(self):
        with patch.object(sys,'argv',self.args('/fixture','--user-start-utc','2026-10-01')), patch('subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):launcher.main()
        run.assert_not_called()

    def test_existing_log_dir_is_not_reused(self):
        with tempfile.TemporaryDirectory() as root, patch('subprocess.run') as run:
            with patch.object(sys,'argv',self.args(root,'--log-dir',root)):
                with self.assertRaises(FileExistsError):launcher.main()
            run.assert_not_called()

    def test_logs_cannot_enter_skill(self):
        dest=Path(launcher.__file__).resolve().parent/'fixture-logs'
        with patch.object(sys,'argv',self.args('/fixture','--log-dir',str(dest))), patch('subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):launcher.main()
        run.assert_not_called();self.assertFalse(dest.exists())

    def test_unknown_create_never_recreates(self):
        p=bench.Probe(1,'fixture',repo='id:fixture');p.name='fixture-task'
        row={'displayName':p.name,'path':'/fixture/'+p.name,'id':'fixture-id'}
        with patch.object(p,'trees',side_effect=[[],[row]]),patch.object(p,'terminals',return_value=[]),patch.object(p,'command',side_effect=RuntimeError('unknown transport')) as command:
            with self.assertRaises(RuntimeError):p.create()
        self.assertEqual(command.call_count,1)
        self.assertEqual(p.data['unknown_create_matches'][0]['id'],'fixture-id')

    def test_expired_collection_leaves_agent(self):
        with tempfile.TemporaryDirectory() as root:
            p=bench.Probe(1,'fixture',repo='id:fixture')
            with patch.object(p,'command') as command:
                self.assertEqual(launcher.collect(p,Path(root),0,1),'unknown')
            command.assert_not_called()
            self.assertIn('left untouched',json.loads((Path(root)/'collection-end.json').read_text())['reason'])

    def test_probe_requires_explicit_repo(self):
        with self.assertRaises(ValueError):bench.Probe(1,'fixture')

    def test_exact_prompt_and_timing_with_mock_runtime(self, base_branch='main'):
        class FakeProbe:
            def __init__(self,*args):
                self.agent='claude';self.started=launcher.time.monotonic();self.handle='fixture-handle'
                self.data={'steps':[],'resources':{},'started_utc':launcher.utc()}
            def remaining(self):return 30
            def create(self):self.data['resources']={'head':'fixture-sha'}
            def command(self,label,args):
                self_calls.append((label,args))
                if label=='send_exact_prompt_once':return {'result':{'send':{'accepted':True,'prompt':{'requestId':'fixture-request'}}}}
                return {'result':{'mutation':{'requestId':'fixture-request','replayed':True}}}
            def poll(self,label,predicate):return '⏺ 已开始检查'
        self_calls=[]
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/'logs'
            response=type('Result',(),{'returncode':0,'stdout':'fixture-sha\n','stderr':''})()
            with patch.object(sys,'argv',self.args(root,'--log-dir',str(out),'--user-start-utc','2026-10-01T00:00:00+00:00','--base-branch',base_branch)),patch.object(launcher,'Probe',FakeProbe),patch.object(launcher,'configure'),patch.object(launcher.subprocess,'run',return_value=response) as run,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.main(),0)
            data=json.loads((out/'startup.json').read_text())
            self.assertTrue(data['launch_confirmed']);self.assertIn('actual_start_observed_utc',data)
            self.assertIn('user_start_to_observed_start_seconds',data)
            self.assertEqual(data['base_branch'],'origin/'+base_branch)
            git_calls=[c.args[0] for c in run.call_args_list]
            self.assertIn(['git','-C',root,'fetch','origin',base_branch],git_calls)
            self.assertIn(['git','-C',root,'rev-parse','origin/'+base_branch],git_calls)
            self.assertEqual(len(self_calls),2)
            first=self_calls[0][1];self.assertEqual(first[first.index('--text')+1],'请检查测试文案')
            self.assertIn('--retry-request',self_calls[1][1])

    def test_non_main_branch_launch(self):
        self.test_exact_prompt_and_timing_with_mock_runtime('release/staging')

    def test_invalid_base_branch_has_no_side_effects(self):
        for branch in ('--help','../main','main//other'):
            with self.subTest(branch=branch), patch.object(sys,'argv',self.args('/fixture','--base-branch='+branch)), patch('subprocess.run') as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):launcher.main()
                run.assert_not_called()

if __name__=='__main__':unittest.main()
