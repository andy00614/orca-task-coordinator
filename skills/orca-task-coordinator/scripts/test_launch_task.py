import json
import unittest
from pathlib import Path
from launch_task import classify, official_state

class CompletionReplayTests(unittest.TestCase):
    def test_saved_finished_screen_requires_stability(self):
        finished=['⏺ Review prepared\n✻ Baked for 1m · done\n❯\n']*2
        self.assertGreaterEqual(len(finished),2)
        self.assertEqual(classify(finished[0],True,1),'unknown')
        self.assertEqual(finished[0],finished[1])
        self.assertEqual(classify(finished[1],True,2),'awaiting_parent_review')

    def test_duration_word_is_not_completion(self):
        for word in ('Baked','Cooked','Worked'):
            with self.subTest(word=word):
                self.assertEqual(classify(f'{word} for 1m · done',True,3),'unknown')

    def test_cooked_with_stable_normal_input(self):
        self.assertEqual(classify('⏺ PR created\n✻ Cooked for 1m · done\n❯\n',True,2),'awaiting_parent_review')

    def test_working_with_normal_input_does_not_finish(self):
        self.assertEqual(classify('⏺ Running 1 shell command…\n✻ Working…\n❯\n',True,5),'running')

    def test_background_agent_does_not_finish(self):
        self.assertEqual(classify('Waiting for 1 background agent to finish\n❯\n',True,5),'running')

    def test_permission_prompt_stops(self):
        self.assertEqual(classify('Do you want to proceed?\n1. Yes, allow\n❯\n',True,5),'blocked')

    def test_idle_without_sent_task_is_not_started(self):
        self.assertEqual(classify('Claude Code\n❯\n',False,10,'idle'),'not_started')

    def test_official_working_overrides_stable_input(self):
        self.assertEqual(classify('❯\n',True,5,'working'),'running')

    def test_official_completed_requires_started_task(self):
        self.assertEqual(classify('metadata only',True,0,'completed'),'awaiting_parent_review')
        self.assertEqual(classify('metadata only',False,0,'completed'),'not_started')

    def test_pty_connectivity_is_not_agent_completion(self):
        self.assertIsNone(official_state({'result':{'terminal':{'connected':True,'writable':True,'status':'running','agentWait':None}}}))

    def test_saved_initial_activity_is_not_finished(self):
        screen='⏺ Reading project rules\n✻ Working…\n❯\n'
        self.assertNotEqual(classify(screen,True,1),'awaiting_parent_review')

if __name__=='__main__':unittest.main(verbosity=2)
