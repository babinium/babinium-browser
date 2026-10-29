#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read settings labels from a real, signed-out YouTube page."""
import base64,json,subprocess,sys,tempfile,time
from pathlib import Path
binary=Path(sys.argv[1]).resolve();lang=sys.argv[2] if len(sys.argv)>2 else 'es'
with tempfile.TemporaryDirectory(prefix='bb-menu-') as profile:
    p=subprocess.Popen([str(binary),'--profile',profile,'--no-update','--autoplay','--eval',str(Path(__file__).with_suffix('.js').resolve()),'--eval-after','30','--quit-after','75','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl='+lang],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        wid=None;deadline=time.monotonic()+15
        while time.monotonic()<deadline and p.poll() is None:
            found=subprocess.run(['xdotool','search','--onlyvisible','--pid',str(p.pid)],capture_output=True,text=True)
            if found.returncode==0 and found.stdout.strip():wid=found.stdout.splitlines()[0];break
            time.sleep(.2)
        if not wid:raise RuntimeError('No visible browser window')
        def state():
            s=subprocess.check_output(['xdotool','getwindowname',wid],text=True).strip()
            try:return json.loads(base64.b64decode(s[7:].split(' — ')[0])) if s.startswith('BBMENU:') else None
            except (ValueError,TypeError):return None
        def wait(fn):
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                s=state()
                if s and fn(s):return s
                time.sleep(.3)
            raise RuntimeError('Timed out: '+str(state()))
        v=wait(lambda s:s['gear'] and s['gear']['w']>0)
        subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
        subprocess.run(['xdotool','mousemove','--window',wid,'400','300'],check=True);time.sleep(.4)
        size=dict(x.split('=',1) for x in subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True).splitlines() if '=' in x)
        r=v['gear'];x=round((int(size['WIDTH'])-v['viewport'][0])/2+r['x']+r['w']/2);y=round(int(size['HEIGHT'])-v['viewport'][1]+r['y']+r['h']/2)
        subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y),'click','1'],check=True)
        print(json.dumps(wait(lambda s:bool(s['items']))['items'],ensure_ascii=False,indent=2),flush=True)
    finally:p.terminate();p.wait(timeout=10)
