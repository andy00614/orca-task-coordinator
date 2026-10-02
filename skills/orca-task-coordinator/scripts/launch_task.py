#!/usr/bin/env python3
"""Ordinary Orca task launcher and bounded read-only collector. No orchestration."""
import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from startup_bench import Probe, ROOT, utc

def redact(s):
    s=re.sub(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[REDACTED_JWT]',s)
    return re.sub(r'(?i)((?:api[_-]?key|password|secret|access[_-]?token|auth[_-]?token)\s*[=:]\s*)[^\s,\"]+',r'\1[REDACTED]',s)

def save(path,obj):
    path.write_text(redact(json.dumps(obj,ensure_ascii=False,indent=2))+'\n')

def classify(text,started,stable=0,official_state=None):
    """Return observations, never a quality or merge verdict."""
    if re.search(r'do you trust|trust this|sign in|login required|do you want to proceed|yes, allow|allow this tool|permission request|需要你确认|请你确认',text,re.I):
        return 'blocked'
    if not started:
        return 'not_started'
    # Finished-duration decoration is neither working nor completion evidence.
    activity='\n'.join(line for line in text.splitlines() if not re.search(r'\bfor\b.*\bdone\b',line))
    working=bool(re.search(r'Running\s+\d+.*command|Waiting for .*background|Working[.…]|Thinking[.…]|Crafting[.…]|Gathering[.…]|Esc to interrupt|esc to interrupt|Running…',activity,re.I))
    if official_state in ('working','running') or working:
        return 'running'
    if official_state=='completed':
        return 'awaiting_parent_review'
    normal_input=bool(re.search(r'^\s*[❯›]\s*$',text,re.M))
    if normal_input and stable>=2 and official_state in (None,'idle'):
        return 'awaiting_parent_review'
    return 'unknown'

def official_state(metadata):
    # The installed terminal-show returns agentWait but no agent execution state.
    # Do not confuse connected=true or a running PTY with agent completion.
    value=metadata.get('result',{}).get('terminal',{}).get('agentState')
    return value if value in ('working','running','idle','completed') else None

def configure(p,model):
    if p.agent=='codex':
        if model!='configured': raise RuntimeError('Codex model must be configured; no unverified model override')
        screen=p.poll('agent_ready',lambda s:'OpenAI Codex' in s and '›' in s and bool(re.search(r'GPT-|gpt-|o[134]-',s)))
        p.data['model_evidence']=[x.strip() for x in screen.splitlines() if re.search(r'GPT-|gpt-|OpenAI Codex',x)]
        return
    p.poll('agent_ready',lambda s:'Claude Code' in s and '❯' in s and 'Select model' not in s)
    if model=='configured': return
    if not re.fullmatch(r'[A-Za-z]+ \d+(?:\.\d+)?',model): raise RuntimeError('use the exact displayed model label, e.g. Sonnet 5.5')
    p.command('open_model_menu',['terminal','send','--terminal',p.handle,'--text','/model','--enter','--json'])
    menu=p.poll('model_menu',lambda s:'Select model' in s and 's to use this session only' in s)
    target=re.search(r'^.*?(\d+)\.\s+'+re.escape(model)+r'\b',menu,re.M)
    current=re.search(r'^.*?❯\s*(\d+)\.',menu,re.M)
    if not target or not current: raise RuntimeError('requested displayed model absent; no guess or default change')
    distance=int(target.group(1))-int(current.group(1))
    if distance:p.raw_send('select_model_arrows',('\x1b[B' if distance>0 else '\x1b[A')*abs(distance))
    p.poll('model_selected',lambda s:bool(re.search(r'❯\s*\d+\.\s+'+re.escape(model)+r'\b',s)))
    p.raw_send('session_only_s','s')
    screen=p.poll('model_confirmed',lambda s:'Set model to '+model+' for this session only' in s and 'Select model' not in s)
    p.data['model_evidence']=[x.strip() for x in screen.splitlines() if model in x]

def collect(p,out,seconds,interval):
    deadline=time.monotonic()+seconds
    previous=None;stable=0;state='unknown'
    while time.monotonic()<deadline:
        p.deadline=deadline
        d=p.command('collect_screen',['terminal','read','--terminal',p.handle,'--screen','--json'],allow_error=True)
        metadata=p.command('official_terminal_metadata',['terminal','show','--terminal',p.handle,'--json'],allow_error=True)
        term=d.get('result',{}).get('terminal',{});text='\n'.join(term.get('tail',[]))
        rendered=term.get('source')=='screen'
        fingerprint=hashlib.sha256(text.encode()).hexdigest()
        stable=stable+1 if rendered and fingerprint==previous else (1 if rendered else 0)
        previous=fingerprint if rendered else None
        state=classify(text,True,stable,official_state(metadata)) if rendered else 'unknown'
        if d.get('error') or metadata.get('error'): state='unknown'
        event={'observed_utc':utc(),'terminal_read':d,'terminal_show':metadata,'stable_observations':stable,'observation':state,'quality_verdict':'not assessed; parent review required','complete_tool_transcript':'unknown; collapsed screen summaries do not prove file reads'}
        with (out/'terminal.jsonl').open('a') as f:f.write(redact(json.dumps(event,ensure_ascii=False))+'\n')
        save(out/'collection-status.json',event)
        print(json.dumps({'stage':'COLLECTED','observed_utc':event['observed_utc'],'observation':state,'source':term.get('source'),'nextCursor':term.get('nextCursor'),'stable':stable}),flush=True)
        if state in ('blocked','awaiting_parent_review') or d.get('error') or metadata.get('error'): return state
        next_read=min(time.monotonic()+interval,deadline)
        while time.monotonic()<next_read:time.sleep(min(1,next_read-time.monotonic()))
    save(out/'collection-end.json',{'observed_utc':utc(),'observation':'unknown','reason':'bounded collection deadline; agent left untouched'})
    return 'unknown'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--repo-id',required=True)
    parser.add_argument('--base-branch',default='main',help='origin branch to fetch and use as worktree base')
    parser.add_argument('--agent',choices=('claude','codex'),default='claude')
    parser.add_argument('--model',help='Claude exact menu label; Codex supports configured only')
    prompt=parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument('--prompt-file',type=Path);prompt.add_argument('--prompt-text')
    parser.add_argument('--fetch-worktree',type=Path,required=True)
    parser.add_argument('--user-start-utc')
    parser.add_argument('--log-dir',type=Path)
    parser.add_argument('--collect-seconds',type=int,default=900)
    parser.add_argument('--poll-seconds',type=int,default=120)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',args.name):parser.error('name must be a safe unique worktree name')
    if not 0<=args.collect_seconds<=900 or not 1<=args.poll_seconds<=120:parser.error('collection bounded to 900 seconds; polling 1..120 seconds')
    model=args.model or ('Sonnet 5.5' if args.agent=='claude' else 'configured')
    if args.agent=='codex' and model!='configured':parser.error('Codex uses the installed configured launcher/model/effort')
    if not args.repo_id.removeprefix('id:').strip():parser.error('repo-id cannot be empty')
    user=None
    if args.user_start_utc:
        try:
            user=dt.datetime.fromisoformat(args.user_start_utc.replace('Z','+00:00'))
            if user.tzinfo is None:raise ValueError('timezone required')
        except ValueError:parser.error('user-start-utc must be an ISO timestamp with timezone')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*',args.base_branch) or '..' in args.base_branch or args.base_branch.endswith('/') or '//' in args.base_branch:parser.error('base-branch must be a safe origin branch name')
    text=args.prompt_file.read_text() if args.prompt_file else args.prompt_text
    if not text.strip():parser.error('empty prompt')
    out=args.log_dir or ROOT/(args.name+'-logs')
    out=out.expanduser().resolve()
    skill_root=Path(__file__).resolve().parent.parent
    if out==skill_root or skill_root in out.parents:parser.error('log-dir must be outside the skill directory')
    out.mkdir(parents=True,exist_ok=False)
    p=Probe(1,'task',args.agent,'id:'+args.repo_id.removeprefix('id:'))
    p.base_branch='origin/'+args.base_branch
    p.name=args.name;p.prompt=text;p.data.update(name=args.name,prompt_sha256=hashlib.sha256(text.encode()).hexdigest(),requested_model=model,base_branch=p.base_branch)
    p.data.pop('nonce',None);p.data.pop('success',None)
    save(out/'startup.json',p.data)
    try:
        for label,command in [('fetch_base',['git','-C',str(args.fetch_worktree),'fetch','origin',args.base_branch]),('resolve_base',['git','-C',str(args.fetch_worktree),'rev-parse',p.base_branch])]:
            start=time.monotonic();at=utc();r=subprocess.run(command,capture_output=True,text=True,timeout=min(30,p.remaining()))
            p.data['steps'].append({'step':label,'started_utc':at,'ended_utc':utc(),'seconds':round(time.monotonic()-start,3),'exitcode':r.returncode})
            if r.returncode:raise RuntimeError(redact(r.stderr))
            if label=='resolve_base':p.data['baseline_sha']=r.stdout.strip()
        p.create();save(out/'startup.json',p.data)
        if p.data['resources'].get('head')!=p.data['baseline_sha']:raise RuntimeError('HEAD differs from fetched base branch; no prompt sent')
        configure(p,model)
        send=['terminal','send','--terminal',p.handle,'--text',text,'--enter','--json']
        receipt=p.command('send_exact_prompt_once',send);p.data['send_receipt']=receipt.get('result');save(out/'startup.json',p.data)
        s=receipt.get('result',{}).get('send',{});request=s.get('prompt',{}).get('requestId')
        if s.get('accepted') is not True or not request:raise RuntimeError('accepted real requestId missing; no resend')
        replay=p.command('observe_same_request',send[:-1]+['--retry-request',request,'--wait-submit','5','--json']);p.data['replay_receipt']=replay.get('result')
        mutation=replay.get('result',{}).get('mutation',{})
        if mutation.get('requestId')!=request or mutation.get('replayed') is not True:raise RuntimeError('same-request replay unconfirmed; no resend')
        marker='⏺' if p.agent=='claude' else '•'
        response=p.poll('actual_assistant_activity',lambda s:bool(re.search(r'^\s*'+re.escape(marker)+r'\s+\S',s,re.M)))
        p.data.update(actual_start_observed_utc=utc(),local_launch_seconds=round(time.monotonic()-p.started,3),launch_confirmed=True)
        p.data['assistant_activity_evidence']=[x.strip() for x in response.splitlines() if re.match(r'^\s*'+re.escape(marker)+r'\s+\S',x)]
        if args.user_start_utc:
            p.data['user_start_utc']=args.user_start_utc
            p.data['user_start_to_observed_start_seconds']=round((dt.datetime.fromisoformat(p.data['actual_start_observed_utc'])-user).total_seconds(),3)
        save(out/'startup.json',p.data)
        print(redact(json.dumps({'stage':'STARTED','log_dir':str(out),**p.data},ensure_ascii=False)),flush=True)
    except Exception as e:
        p.data.update(failure=str(e),ended_utc=utc(),launch_confirmed=False)
        save(out/'startup.json',p.data)
        print(redact(json.dumps({'stage':'BLOCKED','log_dir':str(out),**p.data},ensure_ascii=False)),flush=True)
        return 1
    if args.collect_seconds:
        try:collect(p,out,args.collect_seconds,args.poll_seconds)
        except Exception as e:save(out/'collection-end.json',{'observed_utc':utc(),'observation':'unknown','error':str(e),'agent_left_untouched':True})
    return 0

if __name__=='__main__':raise SystemExit(main())
