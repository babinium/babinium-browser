#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify real YouTube speed shortcuts with trusted X11 keys and no account."""
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from ui import browser_window,key

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
driver=Path(__file__).with_name('youtube-speed.js').resolve()
eval_delay=os.environ.get('BABINIUM_TEST_YOUTUBE_EVAL_AFTER','30')
initial_timeout=int(os.environ.get('BABINIUM_TEST_YOUTUBE_INITIAL_WAIT','65'))
quit_after=os.environ.get('BABINIUM_TEST_YOUTUBE_QUIT_AFTER','100')
with (out/'stderr.log').open('w') as err:
    command=[str(binary),'--profile',str(out/'profile'),'--no-update','--autoplay','--telemetry',str(out/'events.jsonl'),'--eval',str(driver),
        '--eval-after',eval_delay,'--quit-after',quit_after]
    if os.environ.get('BABINIUM_TEST_DATA_DIR'):command+=['--data-dir',os.environ['BABINIUM_TEST_DATA_DIR']]
    command+=['https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en']
    p=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=err,start_new_session=True)
    try:
        wid=browser_window(p.pid)
        last_observation=[None]
        def state():
            title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
            if not title.startswith('BBYTSPD:'):return None
            try:
                last_observation[0]=json.loads(base64.b64decode(title[8:].split(' — ')[0]));return last_observation[0]
            except (ValueError,TypeError):return None
        def wait(predicate,seconds=20):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                value=state()
                if value and predicate(value):return value
                time.sleep(.2)
            (out/'last-observation.json').write_text(json.dumps(last_observation[0],indent=2)+'\n')
            raise AssertionError('Timed out: '+str(state())+'; last observation: '+str(last_observation[0]))
        initial=wait(lambda s:s.get('height')==360 and s.get('time',0)>2 and not s.get('ad'),seconds=initial_timeout)
        subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
        geom=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
        size=dict(line.split('=',1) for line in geom.splitlines() if '=' in line);r=initial['videoRect']
        x=round((int(size['WIDTH'])-initial['viewport'][0])/2+r['x']+25)
        y=round(int(size['HEIGHT'])-initial['viewport'][1]+r['y']+25)
        subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y),'click','1'],check=True)
        wait(lambda s:not s.get('paused') and not s.get('ad'),seconds=15)
        key('d');early_reset=os.environ.get('BABINIUM_TEST_EARLY_RESET','1')!='0'
        if early_reset:time.sleep(.15);key('F8')
        first=wait(lambda s:(not early_reset or s.get('forcedResets',0)>=1) and abs(s.get('rate',0)-1.1)<.001 and not s.get('ad'))
        if early_reset:assert first['forcedRate']==1,first
        time.sleep(4);stable=state();assert abs(stable['rate']-1.1)<.001 and not stable['ad'],stable
        assert not stable['indicator'],stable
        if os.environ.get('BABINIUM_TEST_DIAG_ONLY')=='1':
            diagnostic={'initial':initial,'first':first,'stable':stable}
            (out/'diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            print(json.dumps(diagnostic),flush=True);sys.exit(0)
        key('F8');forced=wait(lambda s:s.get('forcedResets',0)>=(2 if early_reset else 1) and abs(s.get('rate',0)-1.1)<.001 and not s.get('ad'))
        assert forced['forcedRate']==1,forced
        time.sleep(2);after_forced=state();assert abs(after_forced['rate']-1.1)<.001 and not after_forced['ad'],after_forced
        key('d');key('d');wait(lambda s:abs(s.get('rate',0)-1.3)<.001)
        key('g');wait(lambda s:abs(s.get('rate',0)-1.8)<.001);key('g');wait(lambda s:abs(s.get('rate',0)-1.3)<.001)
        key('r');final=wait(lambda s:abs(s.get('rate',0)-1)<.001 and s.get('time',0)>first['time'] and not s.get('paused'))
        assert not final['ad'],final;before=final['time'];key('x')
        forward=wait(lambda s:s.get('time',0)>before+8 and not s.get('ad'))
        key('z');backward=wait(lambda s:s.get('time',0)<forward['time']-7 and not s.get('ad'))
        key('m');key('x');marked_forward=wait(lambda s:s.get('time',0)>backward['time']+8 and not s.get('ad'))
        key('j');marked_back=wait(lambda s:s.get('time',0)<marked_forward['time']-7 and not s.get('ad'))
        for _ in range(20):key('d')
        high=wait(lambda s:abs(s.get('rate',0)-3)<.001 and not s.get('ad'))
        time.sleep(10);high_stable=state()
        assert abs(high_stable['rate']-3)<.001 and not high_stable['ad'] and not high_stable['paused'],high_stable
        assert high_stable['time']>high['time']+2,high_stable
        key('x');high_seek=wait(lambda s:s.get('time',0)>high_stable['time']+8 and not s.get('ad'))
        time.sleep(2);after_high_seek=state()
        assert abs(after_high_seek['rate']-3)<.001 and not after_high_seek['ad'],after_high_seek
        key('r');wait(lambda s:abs(s.get('rate',0)-1)<.001 and not s.get('ad'))
        result={'initial':initial,'after_d':first,'after_reset':final,'stable_after_4s':stable['rate'],
            'forced_reset':forced,'after_forced_reset':after_forced['rate'],
            'forward':forward,'backward':backward,'marked_forward':marked_forward,'marked_back':marked_back,
            'high_rate':high,'high_rate_after_10s':high_stable['rate'],
            'high_rate_advanced_seconds':high_stable['time']-high['time'],
            'high_seek':high_seek,'high_rate_after_seek':after_high_seek['rate']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'initial_rate':initial['rate'],'after_d':first['rate'],'stable_after_4s':stable['rate'],
            'after_reset':final['rate'],'after_forced_site_reset':after_forced['rate'],
            'advanced_seconds':round(final['time']-initial['time'],2),'indicator_seen':first['indicator'],
            'seek_forward':round(forward['time']-before,2),'seek_back':round(forward['time']-backward['time'],2),
            'marked_return':round(marked_forward['time']-marked_back['time'],2),'high_rate_after_10s':high_stable['rate'],
            'high_rate_advanced_seconds':round(high_stable['time']-high['time'],2),'high_rate_after_seek':after_high_seek['rate']}),flush=True)
    finally:
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        p.wait(timeout=10)
