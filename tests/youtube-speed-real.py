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

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
driver=Path(__file__).with_name('youtube-speed.js').resolve()
with (out/'stderr.log').open('w') as err:
    p=subprocess.Popen([str(binary),'--profile',str(out/'profile'),'--no-update','--autoplay','--eval',str(driver),
        '--eval-after','30','--quit-after','100','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en'],stdout=subprocess.DEVNULL,stderr=err,start_new_session=True)
    try:
        wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
        def state():
            title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
            if not title.startswith('BBYTSPD:'):return None
            try:return json.loads(base64.b64decode(title[8:].split(' — ')[0]))
            except (ValueError,TypeError):return None
        def wait(predicate,seconds=20):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                value=state()
                if value and predicate(value):return value
                time.sleep(.2)
            raise AssertionError('Timed out: '+str(state()))
        def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True,timeout=5)
        initial=wait(lambda s:s.get('height')==360 and s.get('time',0)>2 and not s.get('ad'),seconds=65)
        subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
        geom=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
        size=dict(line.split('=',1) for line in geom.splitlines() if '=' in line);r=initial['videoRect']
        x=round((int(size['WIDTH'])-initial['viewport'][0])/2+r['x']+25)
        y=round(int(size['HEIGHT'])-initial['viewport'][1]+r['y']+25)
        subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y),'click','1'],check=True)
        wait(lambda s:not s.get('paused') and not s.get('ad'),seconds=15)
        key('d');first=wait(lambda s:abs(s.get('rate',0)-1.1)<.001 and not s.get('ad'))
        time.sleep(4);stable=state();assert abs(stable['rate']-1.1)<.001 and not stable['ad'],stable
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
        time.sleep(3);high_stable=state();assert abs(high_stable['rate']-3)<.001 and not high_stable['ad'],high_stable
        key('r');wait(lambda s:abs(s.get('rate',0)-1)<.001 and not s.get('ad'))
        result={'initial':initial,'after_d':first,'after_reset':final,'stable_after_4s':stable['rate'],
            'forward':forward,'backward':backward,'marked_forward':marked_forward,'marked_back':marked_back,
            'high_rate':high,'high_rate_after_3s':high_stable['rate']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'initial_rate':initial['rate'],'after_d':first['rate'],'stable_after_4s':stable['rate'],
            'after_reset':final['rate'],'advanced_seconds':round(final['time']-initial['time'],2),'indicator_seen':first['indicator'],
            'seek_forward':round(forward['time']-before,2),'seek_back':round(forward['time']-backward['time'],2),
            'marked_return':round(marked_forward['time']-marked_back['time'],2),'high_rate_after_3s':high_stable['rate']}),flush=True)
    finally:
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        p.wait(timeout=10)
