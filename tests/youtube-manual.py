#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the real YouTube quality menu with real pointer input, muted."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
driver=Path(__file__).with_name('youtube-manual.js').resolve()
with (out/'stderr').open('w') as stderr:
    p=subprocess.Popen([str(binary),'--profile',str(out/'profile'),'--no-update','--autoplay','--eval',str(driver),'--eval-after','30','--telemetry',str(out/'events.jsonl'),'--quit-after','105','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en'],stdout=subprocess.DEVNULL,stderr=stderr,start_new_session=True)
    try:
        wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
        def state():
            title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
            if not title.startswith('BBYT:'):return None
            try:return json.loads(base64.b64decode(title[5:].split(' — ')[0]))
            except (ValueError,TypeError):return None
        def wait(predicate,seconds=25):
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
        initial=wait(lambda v:v.get('height')==360 and v.get('time',0)>1,seconds=60)
        subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
        subprocess.run(['xdotool','mousemove','--window',wid,'400','300'],check=True);time.sleep(.5)
        gear=wait(lambda v:v.get('gear') and v['gear']['w']>0);click(gear['gear'],gear)
        menu=wait(lambda v:any('Quality' in item['text'] for item in v['items']))
        item=next(item for item in menu['items'] if 'Quality' in item['text']);click(item,menu)
        menu=wait(lambda v:any('720p' in item['text'] and 'Premium' not in item['text'] for item in v['items']))
        item=next(item for item in menu['items'] if '720p' in item['text'] and 'Premium' not in item['text']);click(item,menu)
        final=wait(lambda v:v.get('height')==720 and v.get('time',0)>initial.get('time',0)+2,seconds=40)
        result={'initial_height':initial['height'],'initial_codecs':initial.get('codecs'),'codec_fallback':initial.get('codecFallback'),'selected':item['text'],'final_height':final['height'],'final_quality':final['quality']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:
        import signal
        try:os.killpg(p.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        p.wait(timeout=8)
