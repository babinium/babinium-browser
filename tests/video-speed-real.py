#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise trusted keys in real WebKit with local HTML5 video, audio and frames.

Run under Xvfb against a remotely built bundle. ffmpeg generates a tiny test clip;
no account, internet site, microphone or user profile is used.
"""
import base64
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import wave

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='bb-speed-media-') as tmp:
    root=Path(tmp);clip=root/'clip.webm';tone=root/'tone.wav'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x90:r=2','-t','40',
        '-c:v','libvpx','-threads','1','-deadline','realtime','-cpu-used','8','-b:v','60k','-an',str(clip)],check=True,timeout=30)
    with wave.open(str(tone),'wb') as w:w.setparams((1,2,8000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*8000*40)
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            path=self.path.split('?',1)[0]
            if path in ('/clip.webm','/tone.wav'):
                data=(clip if path.endswith('webm') else tone).read_bytes();total=len(data)
                requested=self.headers.get('Range','')
                if requested.startswith('bytes='):
                    start,end=requested[6:].split('-',1);start=int(start or 0);end=min(int(end) if end else total-1,total-1)
                    self.send_response(206);self.send_header('Content-Range',f'bytes {start}-{end}/{total}');data=data[start:end+1]
                else:self.send_response(200)
                self.send_header('Content-Type','video/webm' if path.endswith('webm') else 'audio/wav')
                self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if path=='/embed':
                page=f'''<!doctype html><title>waiting</title><iframe id="child" src="http://127.0.0.1:{child.server_port}/video" style="width:720px;height:520px;border:0"></iframe>
                <script>addEventListener('message',e=>{{if(!e.data?.bbFixture)return;const d=e.data.bbFixture,r=document.querySelector('iframe').getBoundingClientRect();
                for(const k of ['mediaRect','inputRect','playRect','pauseRect','minusRect','plusRect'])if(d[k]){{d[k].x+=r.x;d[k].y+=r.y;}}d.viewport=[innerWidth,innerHeight];document.title='BBSPEED:'+btoa(JSON.stringify(d));}});</script>'''
            else:
                tag='audio' if path=='/audio' else 'video';src='/tone.wav' if tag=='audio' else '/clip.webm'
                markup=f'<{tag} id="media" controls preload="auto" src="{src}" style="width:480px;height:{54 if tag=="audio" else 270}px;display:block;background:#223"></{tag}>'
                shadow=path=='/shadow'
                host='<div id="shadow-host"></div>' if shadow else markup
                setup=f"const root=document.querySelector('#shadow-host').attachShadow({{mode:'open'}});root.innerHTML={json.dumps(markup)};const v=root.querySelector('#media');" if shadow else "const v=document.querySelector('#media');"
                page=f'''<!doctype html><title>waiting</title><style>body{{margin:10px}}button,input{{display:block;margin:8px 0}}</style>
                <input id="input" placeholder="Escribir"><button id="play">Reproducir</button><button id="pause">Pausar y volver al comienzo</button>{host}
                <script>{setup}
                const rect=e=>{{if(!e)return null;let r=e.getBoundingClientRect();return {{x:r.x,y:r.y,w:r.width,h:r.height}}}};
                v.addEventListener('loadedmetadata',()=>v.pause());
                document.querySelector('#play').onclick=()=>v.play();
                document.querySelector('#pause').onclick=()=>{{v.pause();v.currentTime=0;}};
                function report(){{let d={{rate:v.playbackRate,time:v.currentTime,duration:v.duration,ready:v.readyState,paused:v.paused,
                    input:document.querySelector('#input').value,mediaRect:rect(v),inputRect:rect(document.querySelector('#input')),
                    playRect:rect(document.querySelector('#play')),pauseRect:rect(document.querySelector('#pause')),viewport:[innerWidth,innerHeight],indicator:!!document.querySelector('[data-babinium-speed]'),
                    minusRect:rect(document.querySelector('[data-babinium-speed] button:first-child')),plusRect:rect(document.querySelector('[data-babinium-speed] button:last-child'))}};
                    if(parent!==window)parent.postMessage({{bbFixture:d}},'*');else document.title='BBSPEED:'+btoa(JSON.stringify(d));}}
                setInterval(report,250);report();</script>'''
            data=page.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    parent=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);child=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    for server in (parent,child):threading.Thread(target=server.serve_forever,daemon=True).start()
    def run(case):
        log=(out/(case+'.stderr')).open('w');profile=out/('profile-'+case)
        p=subprocess.Popen([str(binary),'--profile',str(profile),'--no-update','--no-block','--quit-after','65',
            f'http://127.0.0.1:{parent.server_port}/{case}'],stdout=subprocess.DEVNULL,stderr=log)
        try:
            wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
            def state():
                title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
                if not title.startswith('BBSPEED:'):return None
                try:return json.loads(base64.b64decode(title[8:].split(' — ')[0]))
                except (ValueError,TypeError):return None
            def wait(fn,seconds=15):
                end=time.monotonic()+seconds
                while time.monotonic()<end:
                    s=state()
                    if s and fn(s):return s
                    time.sleep(.1)
                raise AssertionError(f'{case}: timed out, state={state()}')
            def click(name,s):
                box=s[name];geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
                size=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
                x=round((int(size['WIDTH'])-s['viewport'][0])/2+box['x']+box['w']/2)
                y=round(int(size['HEIGHT'])-s['viewport'][1]+box['y']+box['h']/2)
                subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y),'click','1'],check=True,timeout=5)
            def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True,timeout=5)
            def rate(value):return lambda s:abs(s['rate']-value)<.001
            def at(value):return lambda s:abs(s['time']-value)<.2
            s=wait(lambda s:s.get('ready',0)>=1 and s.get('duration') is not None and s['duration']>30)
            subprocess.run(['xdotool','windowfocus','--sync',wid],check=True);click('mediaRect',s);click('pauseRect',s)
            wait(lambda s:s['paused'] and abs(s['time'])<.2)
            key('d');s=wait(lambda s:rate(1.1)(s) and s.get('plusRect'));click('plusRect',s);s=wait(rate(1.2));
            click('minusRect',s);wait(rate(1.1));key('s');wait(rate(1));key('g');wait(rate(1.8));key('g');wait(rate(1));
            key('d');wait(rate(1.1));key('r');wait(rate(1));key('x');wait(at(10));key('z');wait(at(0))
            key('m');key('x');wait(at(10));key('j');wait(at(0));key('j');wait(at(10))
            key('v');wait(lambda s:s['indicator']);key('v');wait(lambda s:not s['indicator'])
            s=state();click('inputRect',s);key('d');s=wait(lambda s:s.get('input')=='d');assert abs(s['rate']-1)<.001,s
            click('playRect',s);s=wait(lambda s:not s['paused']);before=s['time'];key('d');wait(rate(1.1));s=wait(lambda s:s['time']>before+.5)
            print(json.dumps({'case':case,'speed':s['rate'],'playing':not s['paused'],'time':round(s['time'],2),'input_protected':s['input']=='d'}),flush=True)
        finally:p.terminate();p.wait(timeout=10);log.close()
    try:
        for case in ('video','audio','shadow','embed'):run(case)
    finally:
        parent.shutdown();child.shutdown()
