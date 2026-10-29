#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample the complete browser process session, including WebKit/bwrap helpers.

CPU 100% means one full logical CPU. RSS includes duplicated shared mappings;
PSS is proportional physical memory. A sample with incomplete PSS is marked and
cannot be used as a complete PSS result. Samples and command are always retained.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import time

HZ=os.sysconf('SC_CLK_TCK')

def processes():
    result={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            s=(p/'stat').read_text();tail=s[s.rfind(')')+2:].split()
            result[int(p.name)]={'ppid':int(tail[1]),'pgid':int(tail[2]),'sid':int(tail[3]),'start':int(tail[19]),'cpu':(int(tail[11])+int(tail[12]))/HZ,'name':s[s.find('(')+1:s.rfind(')')]}
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    return result

def memory(pid):
    try:
        lines=(Path('/proc')/str(pid)/'smaps_rollup').read_text().splitlines()
        values={s.split(':',1)[0]:int(s.split()[1]) for s in lines[1:] if len(s.split())>=2}
        return values.get('Rss',0),values.get('Pss',0),values.get('SwapPss',0),True
    except (FileNotFoundError,PermissionError,ProcessLookupError):
        try:
            s=(Path('/proc')/str(pid)/'status').read_text().splitlines()
            rss=next((int(l.split()[1]) for l in s if l.startswith('VmRSS:')),0)
            return rss,0,0,False
        except (FileNotFoundError,PermissionError,ProcessLookupError):return 0,0,0,False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True);parser.add_argument('--duration',type=float,default=60)
    parser.add_argument('--warmup',type=float,default=15);parser.add_argument('--interval',type=float,default=1)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args();command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:parser.error('Missing command')
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env['BABINIUM_MEASUREMENT']='1'
    start=time.monotonic();known=set();cpu_seen={};samples=[]
    with (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
        child=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True,env=env)
        try:
            with (out/'samples.jsonl').open('w') as log:
                while time.monotonic()-start<args.duration:
                    now=time.monotonic();proc=processes()
                    selected={pid for pid,p in proc.items() if p['sid']==child.pid or pid==child.pid or (pid,p['start']) in known}
                    # Include descendants even if a helper creates another session.
                    while True:
                        extra={pid for pid,p in proc.items() if p['ppid'] in selected}
                        if extra<=selected:break
                        selected|=extra
                    details=[]
                    for pid in sorted(selected):
                        p=proc[pid];key=(pid,p['start']);known.add(key);cpu_seen[key]=max(cpu_seen.get(key,0),p['cpu'])
                        rss,pss,swap,ok=memory(pid)
                        details.append({'pid':pid,'name':p['name'],'rss_kib':rss,'pss_kib':pss,'swap_pss_kib':swap,'pss_readable':ok})
                    s={'seconds':now-start,'rss_kib':sum(p['rss_kib'] for p in details),'pss_kib':sum(p['pss_kib'] for p in details),'swap_pss_kib':sum(p['swap_pss_kib'] for p in details),'pss_complete':all(p['pss_readable'] for p in details),'processes':details,'cpu_seconds':sum(cpu_seen.values())}
                    samples.append(s);log.write(json.dumps(s)+'\n');log.flush()
                    if child.poll() is not None:break
                    time.sleep(max(0,args.interval-(time.monotonic()-now)))
        finally:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
    steady=[s for s in samples if s['seconds']>=args.warmup]
    complete=[s for s in steady if s['pss_complete']]
    duration=samples[-1]['seconds'] if samples else 0
    summary={'command':command,'display':env.get('DISPLAY'),'kernel':platform.release(),'machine':platform.machine(),'logical_cpus':os.cpu_count(),'duration_seconds':duration,'warmup_seconds':args.warmup,'interval_seconds':args.interval,'rss_peak_mib':max((s['rss_kib'] for s in samples),default=0)/1024,'rss_steady_median_mib':statistics.median(s['rss_kib'] for s in steady)/1024 if steady else None,'pss_steady_median_mib':statistics.median(s['pss_kib'] for s in complete)/1024 if complete and len(complete)==len(steady) else None,'pss_peak_mib':max((s['pss_kib'] for s in samples if s['pss_complete']),default=0)/1024,'pss_complete_samples':len(complete),'steady_samples':len(steady),'max_process_count':max((len(s['processes']) for s in samples),default=0),'cpu_seconds':samples[-1]['cpu_seconds'] if samples else 0,'cpu_mean_one_core_percent':samples[-1]['cpu_seconds']/duration*100 if duration else None,'cpu_steady_one_core_percent':(steady[-1]['cpu_seconds']-steady[0]['cpu_seconds'])/(steady[-1]['seconds']-steady[0]['seconds'])*100 if len(steady)>1 else None,'returncode_after_measurement':child.returncode,'notes':['RSS sum double counts shared mappings; PSS is proportional.','Session and descendants are included. Helpers that start and exit between samples may be missed.','CPU includes only sampled processes and excludes the sampler, X server and unrelated desktop applications.','Normal application updates are disabled in steady-state experiments and measured separately.']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
