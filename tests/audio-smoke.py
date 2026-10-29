#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check real YouTube audio on the desktop, monitoring only this browser's stream."""
import array
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
env=dict(os.environ,LANG='C.UTF-8',LC_ALL='C.UTF-8')
def pulse(kind):return json.loads(subprocess.check_output(['pactl','-f','json','list',kind],env=env,stderr=subprocess.DEVNULL))
baseline={s['index'] for s in pulse('sink-inputs')}
setup=out/'volume.js'
setup.write_text("(()=>{const p=document.getElementById('movie_player');p?.setVolume?.(3);const v=document.querySelector('video');if(v){v.muted=false;v.volume=.03;}return JSON.stringify({volume:v?.volume,muted:v?.muted,paused:v?.paused});})()")
with (out/'stderr.log').open('w') as stderr:
    p=subprocess.Popen([str(binary),'--profile',str(out/'profile'),'--no-update','--telemetry',str(out/'events.jsonl'),'--eval',str(setup),'--eval-after','30','--probe-interval','2','--quit-after','95','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en'],stderr=stderr,start_new_session=True)
    try:
        time.sleep(35)
        wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=5).splitlines()[0]
        streams=[s for s in pulse('sink-inputs') if s['index'] not in baseline and not s.get('corked',True)]
        if not streams:
            subprocess.run(['xdotool','windowfocus','--sync',wid],check=True,timeout=5)
            subprocess.run(['xdotool','mousemove','--window',wid,'400','300','click','1'],check=True,timeout=5)
        stream=None
        for _ in range(100):
            observed=[s for s in pulse('sink-inputs') if s['index'] not in baseline]
            (out/'streams.json').write_text(json.dumps([{'index':s['index'],'corked':s.get('corked'),'application':s.get('properties',{}).get('application.name'),'binary':s.get('properties',{}).get('application.process.binary'),'role':s.get('properties',{}).get('media.role')} for s in observed],indent=2)+'\n')
            candidates=[s for s in observed if not s.get('corked',True) and s.get('properties',{}).get('application.name')==binary.name and s.get('properties',{}).get('application.process.binary')=='WebKitWebProcess' and s.get('properties',{}).get('media.role')=='video']
            if candidates:stream=candidates[0];break
            time.sleep(.25)
        if stream is None:raise AssertionError('No active browser audio stream')
        sink=next(s for s in pulse('sinks') if s['index']==stream['sink'])
        monitor=sink['monitor_source']
        capture=subprocess.Popen(['parec','--verbose','--raw','--format=s16le','--rate=48000','--channels=2','--latency-msec=100','--process-time-msec=50','--device='+str(monitor),'--monitor-stream='+str(stream['index'])],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        try:raw,error=capture.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            capture.terminate();raw,error=capture.communicate(timeout=5)
        (out/'capture.log').write_text(error.decode(errors='replace'))
        samples=array.array('h');samples.frombytes(raw[:len(raw)//2*2])
        if not samples:raise AssertionError('No PCM received: '+error.decode(errors='replace'))
        rms=math.sqrt(sum(x*x for x in samples)/len(samples));peak=max(abs(x) for x in samples)
        result={'sample_rate':48000,'channels':2,'captured_seconds':len(samples)/96000,'pcm_rms_s16':rms,'pcm_peak_s16':peak,'stream_corked':stream.get('corked'),'stream_muted':stream.get('mute'),'browser_application':stream.get('properties',{}).get('application.name'),'sample_specification':stream.get('sample_specification'),'scope':'Only the new WebKit sink input; no microphone or mixed desktop recording.'}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        assert rms>0 and peak>0,result
        print(json.dumps(result),flush=True)
    finally:
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        p.wait(timeout=8)
