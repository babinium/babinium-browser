#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check trusted speed keys on a real cross-origin youtube-nocookie embed."""
import base64
import http.server
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        page=f'''<!doctype html><title>waiting</title><div id="player"></div><script src="https://www.youtube.com/iframe_api"></script><script>
        let p,ready=false,error=null;function onYouTubeIframeAPIReady(){{p=new YT.Player('player',{{host:'https://www.youtube-nocookie.com',width:640,height:360,
            videoId:'M7lc1UVf-VE',playerVars:{{autoplay:1,mute:1,origin:'http://127.0.0.1:{self.server.server_port}'}},
            events:{{onReady:()=>{{ready=true;p.mute();p.playVideo();}},onError:e=>{{error=e.data;}}}}}});}}
        setInterval(()=>{{let e=document.querySelector('iframe'),r=e?.getBoundingClientRect();
            document.title='BBEMBED:'+btoa(JSON.stringify({{ready,error,observedMs:performance.now(),rate:ready?p.getPlaybackRate():null,time:ready?p.getCurrentTime():null,state:ready?p.getPlayerState():null,
                src:e?.src,viewport:[innerWidth,innerHeight],rect:r?{{x:r.x,y:r.y,w:r.width,h:r.height}}:null}}));}},500);
        </script>'''.encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(page)));self.end_headers();self.wfile.write(page)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-yt-embed-') as temp,(out/'stderr.log').open('w') as err:
        p=subprocess.Popen([str(binary),'--profile',temp,'--no-update','--autoplay','--quit-after','110',
            '--screenshot',str(out/'window.png'),'--snapshot-after','30',
            f'http://127.0.0.1:{server.server_port}/'],stdout=subprocess.DEVNULL,stderr=err,start_new_session=True)
        try:
            # X11 windows can disappear while xdotool enumerates them; retry
            # that race instead of treating it as a browser failure.
            end=time.monotonic()+10;wid=None
            while time.monotonic()<end and p.poll() is None:
                result=subprocess.run(['xdotool','search','--onlyvisible','--pid',str(p.pid)],capture_output=True,text=True,timeout=5)
                if result.returncode==0 and result.stdout.splitlines():wid=result.stdout.splitlines()[0];break
                time.sleep(.1)
            if not wid:raise AssertionError('Browser window did not appear')
            def state():
                title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
                if not title.startswith('BBEMBED:'):return None
                try:return json.loads(base64.b64decode(title[8:].split(' — ')[0]))
                except (ValueError,TypeError):return None
            def wait(fn,seconds=20):
                end=time.monotonic()+seconds
                while time.monotonic()<end:
                    s=state()
                    if s and s.get('error') is not None:raise AssertionError('YouTube player error: '+str(s))
                    if s and fn(s):return s
                    time.sleep(.2)
                raise AssertionError('Timed out: '+str(state()))
            def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True,timeout=5)
            s=wait(lambda x:x.get('state')==1 and x.get('time',0)>2,seconds=75)
            geom=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True);size=dict(line.split('=',1) for line in geom.splitlines() if '=' in line)
            x=round((int(size['WIDTH'])-s['viewport'][0])/2+s['rect']['x']+s['rect']['w']/2)
            y=round(int(size['HEIGHT'])-s['viewport'][1]+s['rect']['y']+s['rect']['h']/2)
            subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
            subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y),'click','1'],check=True)
            # Clicking the video pauses it while transferring keyboard focus.
            # Wait for the observed pause before resuming, so a stale title
            # cannot make the test mistake a paused video for a playing one.
            paused=wait(lambda x:x.get('state')==2,seconds=6)
            key('space');wait(lambda x:x.get('state')==1 and x.get('time',0)>paused['time']+.5)
            key('d');time.sleep(1);changed=state()
            time.sleep(3);stable=state()
            assert stable['state']==1 and stable['time']-changed['time']>1,stable
            # Measure actual playback progress, independent of YouTube's
            # own rate menu/API, which can report a different rate.
            key('g');time.sleep(1);fast_start=state();time.sleep(4);fast_end=state()
            elapsed=(fast_end['observedMs']-fast_start['observedMs'])/1000
            factor=(fast_end['time']-fast_start['time'])/elapsed
            assert fast_end['state']==1 and 1.45<factor<2.2,(factor,fast_start,fast_end)
            key('r');time.sleep(1);normal_start=state();time.sleep(3);final=state()
            normal_elapsed=(final['observedMs']-normal_start['observedMs'])/1000
            normal_factor=(final['time']-normal_start['time'])/normal_elapsed
            assert final['state']==1 and .7<normal_factor<1.3,(normal_factor,normal_start,final)
            (out/'result.json').write_text(json.dumps({'initial':s,'changed':changed,'stable':stable,'fast_start':fast_start,'fast_end':fast_end,'actual_fast_factor':factor,'normal_start':normal_start,'final':final,'actual_normal_factor':normal_factor},indent=2)+'\n')
            print(json.dumps({'source':s['src'].split('/embed/')[0],
                'actual_fast_playback_factor':round(factor,2),'actual_normal_factor':round(normal_factor,2)}),flush=True)
        finally:
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            p.wait(timeout=10)
finally:server.shutdown()
