#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare a single real YouTube playback before/after its ambient-mode switch.

Run as the command measured by scripts/measure.py. Uses an isolated profile and
real mouse input; never seeks, skips advertisements or touches user accounts.
"""
import base64
import json
from pathlib import Path
import subprocess
import sys
import time

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
driver=Path(__file__).with_name('youtube-ambient.js').resolve()
with (out/'browser.stderr').open('w') as stderr:
    p=subprocess.Popen([str(binary),'--profile',str(out/'profile'),'--no-update','--autoplay','--eval',str(driver),'--eval-after','30','--quit-after','190','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en'],stdout=subprocess.DEVNULL,stderr=stderr)
    try:
        wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
        def state():
            title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
            if not title.startswith('BBAMBIENT:'):return None
            try:return json.loads(base64.b64decode(title[10:].split(' — ')[0]))
            except (ValueError,TypeError):return None
        def wait(predicate,seconds=30):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                value=state()
                if value and predicate(value):return value
                time.sleep(.3)
            raise AssertionError('Timed out: '+str(state()))
        def click(box,value):
            geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
            size=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
            x=round((int(size['WIDTH'])-value['viewport'][0])/2+box['x']+box['w']/2)
            y=round(int(size['HEIGHT'])-value['viewport'][1]+box['y']+box['h']/2)
            subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y)],check=True,timeout=5)
            time.sleep(.4);subprocess.run(['xdotool','click','1'],check=True,timeout=5)
        def observe(seconds):
            start=time.monotonic();time.sleep(seconds);end=time.monotonic();return {'start':start,'end':end,'end_state':state()}
        def switch(wanted):
            subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
            subprocess.run(['xdotool','mousemove','--window',wid,'400','300'],check=True);time.sleep(.5)
            gear=wait(lambda v:v.get('gear') and v['gear']['w']>0);click(gear['gear'],gear)
            menu=wait(lambda v:any('Ambient mode' in item['text'] for item in v['items']))
            item=next(item for item in menu['items'] if 'Ambient mode' in item['text']);click(item,menu)
            current=wait(lambda v:v.get('ambient') is wanted,seconds=15)
            subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,'Escape'],check=True)
            subprocess.run(['xdotool','mousemove','--window',wid,'100','15'],check=True)
            time.sleep(5)
            return item,current
        initial=wait(lambda v:v.get('height')==360 and v.get('time',0)>2 and v.get('ambient') is True and not v.get('ad'),seconds=70)
        subprocess.run(['xdotool','mousemove','--window',wid,'100','15'],check=True);time.sleep(4)
        baseline=observe(20)
        item,off=switch(False);after=observe(20)
        on_item,on=switch(True);again=observe(20)
        for phase in [baseline,after,again]:
            if phase['end_state'].get('height')!=360 or phase['end_state'].get('codecs')!=initial.get('codecs') or phase['end_state'].get('ad'):
                raise AssertionError('Playback changed during comparison: '+str(phase['end_state']))
        result={'initial_state':initial,'baseline':baseline,'menu_item':item,'off_state':off,'after':after,'on_item':on_item,'on_state':on,'again':again}
        (out/'phases.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'ambient_before':initial['ambient'],'ambient_after':off['ambient'],'ambient_again':on['ambient'],'codec_before':initial.get('codecs'),'codec_after':after['end_state'].get('codecs'),'video_after':again['end_state'].get('time')}),flush=True)
    finally:
        p.terminate();p.wait(timeout=10)
