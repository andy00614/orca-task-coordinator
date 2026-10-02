#!/usr/bin/env python3
"""Bounded Orca/Claude startup probe. Use only in an explicitly authorized target environment."""
import argparse
import datetime as dt
import json
import re
import secrets
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / '.local' / 'state' / 'orca-task-coordinator'

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

class Probe:
    def __init__(self, index, run_id, agent='claude', repo=None):
        if not repo:
            raise ValueError("explicit registered repo ID required")
        self.agent = agent
        self.repo = repo
        self.base_branch = 'origin/main'
        self.started = time.monotonic()
        self.deadline = self.started + 180
        prefix = 'codex-startup-bench' if agent == 'codex' else 'startup-bench'
        self.name = f'{prefix}-{run_id}-{index}'
        self.nonce = secrets.token_hex(8)
        self.prompt = f'Startup connectivity test. Do not call tools or read/write files. Reply only STARTUP_OK_{self.nonce}。'
        self.token = 'STARTUP_OK_' + self.nonce
        self.handle = None
        self.path = None
        self.resolved_stale = False
        self.data = {'name': self.name, 'agent': agent, 'nonce': self.nonce, 'started_utc': utc(), 'steps': [], 'resources': {}, 'success': False}

    def remaining(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise RuntimeError('round deadline exceeded (180 seconds)')
        return left

    def command(self, label, args, allow_error=False):
        began = time.monotonic()
        step = {'step': label, 'started_utc': utc()}
        self.data['steps'].append(step)
        try:
            p = subprocess.run(['orca'] + args, capture_output=True, text=True, timeout=min(30, self.remaining()))
            step.update(ended_utc=utc(), seconds=round(time.monotonic()-began, 3), exitcode=p.returncode)
            d = json.loads(p.stdout)
            if d.get('error'):
                step['error'] = d['error']
            if (p.returncode or not d.get('ok', True)) and not allow_error:
                raise RuntimeError(f'{label}: {d.get("error", {"exitcode": p.returncode})}')
            return d
        except subprocess.TimeoutExpired:
            step.update(ended_utc=utc(), seconds=round(time.monotonic()-began, 3), exitcode=None, error='timeout')
            raise RuntimeError(f'{label}: result unknown after timeout; no create retry')

    def trees(self):
        d = self.command('list_worktrees', ['worktree', 'list', '--repo', self.repo, '--limit', '1000', '--json'])
        result = d.get('result', {})
        rows = result.get('worktrees', result.get('rows', []))
        if not isinstance(rows, list):
            raise RuntimeError('unrecognized worktree list schema')
        if result.get('page', {}).get('hasMore'):
            raise RuntimeError('worktree list incomplete')
        return rows

    def terminals(self):
        d = self.command('list_terminals', ['terminal', 'list', '--worktree', 'path:'+self.path, '--json'])
        result = d.get('result', {})
        rows = result.get('terminals', result.get('rows', []))
        if not isinstance(rows, list):
            raise RuntimeError('unrecognized terminal list schema')
        return rows

    def read(self):
        d = self.command('read_screen', ['terminal', 'read', '--terminal', self.handle, '--screen', '--json'], allow_error=True)
        error = d.get('error', {})
        if error.get('code') == 'terminal_handle_stale' and not self.resolved_stale:
            self.resolved_stale = True
            rows = self.terminals()
            agents = [x for x in rows if x.get('agentIdentity') == self.agent]
            if len(agents) != 1:
                raise RuntimeError('stale handle: cannot identify exactly one original terminal')
            replacement = agents[0].get('handle') or agents[0].get('terminal', {}).get('handle')
            if not replacement:
                raise RuntimeError('stale handle: terminal list has no handle')
            self.handle = replacement
            self.data['resources']['resolved_handle'] = replacement
            d = self.command('read_resolved_screen', ['terminal', 'read', '--terminal', self.handle, '--screen', '--json'])
        elif error:
            raise RuntimeError(f'read_screen: {error}')
        term = d.get('result', {}).get('terminal', {})
        self.data['steps'][-1]['screen_status'] = {k:term.get(k) for k in ('status','source','returnedLineCount')}
        if term.get('source') == 'screen-unavailable':
            return ''
        if term.get('source') != 'screen':
            raise RuntimeError('rendered screen unavailable')
        text = '\n'.join(term.get('tail', []))
        if re.search(r'do you trust|trust this|sign in|log in|login required|do you want to proceed|yes, allow|allow this tool|permission request', text, re.I):
            raise RuntimeError('login/trust/permission prompt; no confirmation sent')
        return text

    def poll(self, label, predicate):
        began = time.monotonic()
        while True:
            text = self.read()
            if predicate(text):
                self.data.setdefault('phases', {})[label] = {'seconds': round(time.monotonic()-began,3), 'ended_utc': utc()}
                return text
            time.sleep(min(0.5, self.remaining()))

    def raw_send(self, label, text):
        return self.command(label, ['terminal', 'send', '--terminal', self.handle, '--text', text, '--json'])

    def create(self):
        rows = self.trees()
        self.data['worktree_count_before'] = len(rows)
        if any(x.get('displayName') == self.name or x.get('path','').endswith('/'+self.name) for x in rows):
            raise RuntimeError('name already exists; no create')
        try:
            d = self.command('create_worktree_'+self.agent, ['worktree','create','--repo',self.repo,'--name',self.name,'--agent',self.agent,'--setup','inherit','--base-branch',self.base_branch,'--no-parent','--json'])
        except Exception:
            # Never repeat create when its transport result is unknown.
            try:
                matches = [x for x in self.trees() if x.get('displayName') == self.name or x.get('path','').endswith('/'+self.name)]
                self.data['unknown_create_matches'] = [{k:x.get(k) for k in ('id','path','displayName')} for x in matches]
                if len(matches) == 1:
                    self.path = matches[0]['path']
                    self.data['unknown_create_terminals'] = [{k:x.get(k) for k in ('handle','title','status')} for x in self.terminals()]
            except Exception as e:
                self.data['unknown_create_lookup_error'] = str(e)
            raise
        result = d['result']; wt = result['worktree']
        self.path = wt['path']
        self.handle = result.get('agentTerminalHandle') or result.get('startupTerminal',{}).get('handle')
        self.data['resources'] = {'repo':self.repo,'worktree_id':wt['id'],'path':self.path,'head':wt.get('head'),'branch':wt.get('branch'),'terminal_handle':self.handle}
        if not self.handle:
            rows = self.terminals()
            agents = [x for x in rows if x.get('agentIdentity') == self.agent]
            if len(agents) != 1 or not agents[0].get('handle'):
                raise RuntimeError('create succeeded but unique agent handle unavailable')
            self.handle = agents[0]['handle']
            self.data['resources']['terminal_handle'] = self.handle

    def run(self, existing=None):
        try:
            if existing:
                self.data['resources'] = dict(existing)
                self.path = existing['path']
                self.handle = existing['terminal_handle']
                matches = [x for x in self.trees() if x.get('path') == self.path]
                if len(matches) != 1:
                    raise RuntimeError('resume requires exactly one existing worktree')
                agents = [x for x in self.terminals() if x.get('agentIdentity') == self.agent]
                if len(agents) != 1:
                    raise RuntimeError('resume requires exactly one existing agent terminal')
                self.handle = agents[0]['handle']
                self.data['resources']['terminal_handle'] = self.handle
            else:
                self.create()
            if self.agent == 'claude':
                self.poll('claude_ready', lambda s:'Claude Code' in s and '❯' in s and 'Select model' not in s)
                self.command('open_model_menu', ['terminal','send','--terminal',self.handle,'--text','/model','--enter','--json'])
                menu = self.poll('model_menu', lambda s:'Select model' in s and 's to use this session only' in s)
                target = re.search(r'^.*?(\d+)\.\s+Sonnet 5\.5\b', menu, re.M)
                current = re.search(r'^.*?❯\s*(\d+)\.', menu, re.M)
                if not target or not current:
                    raise RuntimeError('cannot identify explicit Sonnet 5.5 and selection in menu')
                distance = int(target.group(1))-int(current.group(1))
                if distance:
                    self.raw_send('select_sonnet_arrows', ('\x1b[B' if distance>0 else '\x1b[A')*abs(distance))
                selected = self.poll('sonnet_selected', lambda s:bool(re.search(r'❯\s*\d+\.\s+Sonnet 5\.5\b',s)))
                self.data['model_menu_evidence'] = [line.strip() for line in selected.splitlines() if ('❯' in line and 'Sonnet 5.5' in line) or 's to use this session only' in line]
                self.raw_send('session_only_s', 's')
                confirmed = self.poll('model_confirmed', lambda s:'Set model to Sonnet 5.5 for this session only' in s and 'Select model' not in s)
                self.data['model_evidence'] = [line.strip() for line in confirmed.splitlines() if 'Sonnet 5.5' in line]
            else:
                ready = self.poll('codex_ready', lambda s:'OpenAI Codex' in s and '›' in s and bool(re.search(r'GPT-|gpt-|o[134]-',s)))
                self.data['version_evidence'] = [line.strip() for line in ready.splitlines() if 'OpenAI Codex' in line]
                self.data['model_evidence'] = [line.strip() for line in ready.splitlines() if re.search(r'GPT-|gpt-|o[134]-',line)]
            args = ['terminal','send','--terminal',self.handle,'--text',self.prompt,'--enter','--json']
            receipt = self.command('send_prompt_once', args)
            self.data['send_receipt'] = receipt.get('result')
            send = receipt.get('result',{}).get('send',{})
            request = send.get('prompt',{}).get('requestId')
            if send.get('accepted') is not True or not request:
                raise RuntimeError('no accepted prompt / real requestId; no resend')
            # Official CLI replay observes the same request and does not resend it.
            replay = self.command('replay_same_receipt_once', args[:-1]+['--retry-request',request,'--wait-submit','5','--json'])
            self.data['replay_receipt'] = replay.get('result')
            replay_result = replay.get('result',{})
            self.data['receipt_replay_valid'] = replay_result.get('mutation',{}).get('replayed') is True and replay_result.get('send',{}).get('prompt',{}).get('requestId') == request
            if not self.data['receipt_replay_valid']:
                raise RuntimeError('receipt replay did not confirm same request')
            marker = '⏺' if self.agent == 'claude' else '•'
            reply_pattern = r'^[ \t]*'+re.escape(marker)+r'[ \t]*'+re.escape(self.token)+r'[ \t]*$'
            response = self.poll('assistant_reply', lambda s:bool(re.search(reply_pattern,s,re.M)))
            lines = [line.strip() for line in response.splitlines() if re.fullmatch(reply_pattern,line)]
            self.data['assistant_reply_evidence'] = lines
            self.data['assistant_reply_count_on_screen'] = len(lines)
            self.data['assistant_reply_count_is_one'] = len(lines)==1
            rows = self.trees()
            matches = [x for x in rows if x.get('displayName') == self.name or x.get('path','').endswith('/'+self.name)]
            terms = self.terminals()
            self.data['worktree_count_after'] = len(rows)
            self.data['same_name_worktree_count'] = len(matches)
            self.data['terminal_count'] = len(terms)
            self.data['agent_terminal_count'] = sum(x.get('agentIdentity')==self.agent for x in terms)
            self.data[self.agent+'_terminal_count'] = self.data['agent_terminal_count']
            self.data['duplicate_resource'] = len(matches)!=1 or self.data['agent_terminal_count']!=1
            self.data['terminal_inventory'] = [{k:x.get(k) for k in ('handle','title','status','agentIdentity')} for x in terms]
            self.data['success'] = len(lines)==1 and not self.data['duplicate_resource'] and self.data['receipt_replay_valid']
        except Exception as e:
            self.data['failure'] = str(e)
        self.data.update(ended_utc=utc(),total_seconds=round(time.monotonic()-self.started,3))
        return self.data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-id', required=True)
    parser.add_argument('--log-dir', type=Path, required=True, help='New output directory outside the installed skill')
    parser.add_argument('--rounds',type=int,choices=(1,2,3),default=3)
    parser.add_argument('--agent',choices=('claude','codex'),default='claude')
    parser.add_argument('--resume-report',type=Path,help='Recover the single failed first round without creating it again, then run rounds 2 and 3.')
    args=parser.parse_args()
    repo='id:'+args.repo_id.removeprefix('id:')
    if Path(__file__).resolve().parent.parent in args.log_dir.resolve().parents or args.log_dir.resolve()==Path(__file__).resolve().parent.parent:
        parser.error('log-dir must be outside the skill directory')
    args.log_dir.mkdir(parents=True, exist_ok=False)
    if args.resume_report:
        report=json.loads(args.resume_report.read_text())
        if len(report['rounds'])!=1 or report['rounds'][0]['success'] or report['rounds'][0].get('send_receipt') or report.get('recovery'):
            raise SystemExit('resume requires one failed, unprompted round and no previous recovery')
        first=report['rounds'][0]
        probe=Probe(1,report['run_id'],report.get('agent','claude'),repo)
        probe.nonce=first['nonce']; probe.token='STARTUP_OK_'+probe.nonce
        probe.prompt=f'Startup connectivity test. Do not call tools or read/write files. Reply only {probe.token}.'
        recovered=probe.run(existing=first['resources'])
        report['recovery']=recovered
        report['recovery_is_cold_start']=False
        output=args.log_dir/args.resume_report.name
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'phase':'first_round_recovery','success':recovered['success'],'seconds':recovered['total_seconds'],'failure':recovered.get('failure'),'resources':recovered['resources'],'report':str(output)},ensure_ascii=False),flush=True)
        if not recovered['success']:
            return 1
        for i in (2,3):
            result=Probe(i,report['run_id'],report.get('agent','claude'),repo).run(); report['rounds'].append(result)
            report['ended_utc']=utc(); output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'round':i,'success':result['success'],'seconds':result['total_seconds'],'failure':result.get('failure'),'resources':result['resources'],'report':str(output)},ensure_ascii=False),flush=True)
            if not result['success']:
                return 1
        return 0
    run_id=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(2)
    report={'run_id':run_id,'agent':args.agent,'started_utc':utc(),'rounds':[],'deadline_per_round_seconds':180}
    prefix='codex-startup-bench-' if args.agent=='codex' else 'startup-bench-'
    output=args.log_dir/(prefix+run_id+'.json')
    for i in range(1,args.rounds+1):
        result=Probe(i,run_id,args.agent,repo).run(); report['rounds'].append(result)
        report['ended_utc']=utc(); output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'round':i,'name':result['name'],'success':result['success'],'total_seconds':result['total_seconds'],'resources':result['resources'],'failure':result.get('failure'),'report':str(output)},ensure_ascii=False),flush=True)
        if not result['success']:
            break
    print(json.dumps({'report':str(output),'successful_rounds':sum(x['success'] for x in report['rounds']),'attempted_rounds':len(report['rounds'])}),flush=True)
    return 0 if all(x['success'] for x in report['rounds']) else 1

if __name__=='__main__':
    raise SystemExit(main())
