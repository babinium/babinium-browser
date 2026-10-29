#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise dark mode, profile persistence, favorites and Google in real GTK/WebKit.

Run under Xvfb as an unprivileged user against the remotely built bundle.
"""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        if self.path=='/set':self.send_header('Set-Cookie','bb_session=retained; Path=/; Max-Age=86400; SameSite=Lax')
        self.end_headers()
        title='Popup opened' if self.path=='/popup-result' else 'Fixture '+self.path
        script="localStorage.setItem('bb_storage','retained');" if self.path=='/set' else ''
        script+=f'''const req=indexedDB.open('bb-db',1);
            req.onupgradeneeded=()=>req.result.createObjectStore('data');
            req.onsuccess=()=>{{const tx=req.result.transaction('data','readwrite');
                const store=tx.objectStore('data');
                {"store.put('retained','key');" if self.path=='/set' else ""}
                const read=store.get('key');read.onsuccess=()=>window.bbIndexed=read.result;}};'''
        script+="window.addEventListener('message',e=>{if(e.data==='bb-popup-ok')document.title='Opener confirmed';});"
        if self.path=='/popup-result':script+="window.opener?.postMessage('bb-popup-ok',location.origin);"
        html=f'''<!doctype html><title>{title}</title><body style="background:white;color:black">
            <p id="content">Normal site content</p><script>{script}</script>
            <button style="position:fixed;top:120px;left:120px;padding:20px" onclick="window.open('/popup-result','bb-popup')">Open popup</button>
            </body>'''
        self.wfile.write(html.encode())

def wait_for(fn,timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if fn():return
        time.sleep(.1)
    raise AssertionError('Timed out waiting for UI condition')

def events(path):
    if not path.exists():return []
    try:return [json.loads(line) for line in path.read_text().splitlines() if line]
    except json.JSONDecodeError:return []

def evaluate(binary,profile,url,script,output,name):
    log=output/(name+'.jsonl')
    command=[str(binary),'--profile',str(profile),'--no-update','--telemetry',str(log),'--eval',str(script),'--eval-after','4','--quit-after','7',url]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
    (output/(name+'.stderr')).write_text(result.stderr)
    assert result.returncode==0,(result.returncode,result.stderr)
    values=[json.loads(e['value']) for e in events(log) if e['event']=='javascript']
    assert values,events(log)
    return values[-1]

def run(binary,output):
    output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='bb-features-') as temp:
            temp=Path(temp);profile=temp/'profile';url=f'http://127.0.0.1:{server.server_port}'
            check=temp/'check.js'
            check.write_text("JSON.stringify({cookie:document.cookie,storage:localStorage.getItem('bb_storage'),indexed:window.bbIndexed,background:getComputedStyle(document.body).backgroundColor,darkStyles:document.querySelectorAll('style.darkreader').length,darkPreference:matchMedia('(prefers-color-scheme: dark)').matches})")
            first=evaluate(binary,profile,url+'/set',check,output,'set')
            assert 'bb_session=retained' in first['cookie'] and first['storage']=='retained' and first.get('indexed')=='retained',first
            assert first['background']!='rgb(255, 255, 255)' and first['darkStyles']>0,first
            second=evaluate(binary,profile,url+'/check',check,output,'restart')
            assert 'bb_session=retained' in second['cookie'] and second['storage']=='retained' and second.get('indexed')=='retained',second
            assert second['background']!='rgb(255, 255, 255)' and second['darkStyles']>0,second
            (profile/'light-sites').write_text('127.0.0.1\n')
            light=evaluate(binary,profile,url+'/check',check,output,'light')
            assert light['background']=='rgb(255, 255, 255)' and light['darkStyles']==0,light
            print('Cookie, localStorage and IndexedDB across clean restarts; Dark Reader and site exception: passed',flush=True)

            # A blank tab is painted black before WebKit is started.
            blank=output/'blank.png';log=output/'blank.jsonl'
            p=subprocess.run([str(binary),'--profile',str(temp/'blank-profile'),'--no-update','--telemetry',str(log),'--screenshot',str(blank),'--snapshot-after','1','--quit-after','3'],capture_output=True,text=True,timeout=20)
            assert p.returncode==0,p.stderr
            pix=GdkPixbuf.Pixbuf.new_from_file(str(blank));x=pix.get_width()//2;y=pix.get_height()//2
            pos=y*pix.get_rowstride()+x*pix.get_n_channels();rgb=tuple(pix.get_pixels()[pos:pos+3])
            assert max(rgb)<=5,rgb
            pixels=pix.get_pixels();step=pix.get_n_channels();stride=pix.get_rowstride()
            bright=sum(min(pixels[py*stride+px*step:py*stride+px*step+3])>120 for py in range(40,65) for px in range(pix.get_width()-140,pix.get_width()-5))
            assert bright>10,('Missing visible Babinium label at the right of the tab bar',bright)
            assert not any(e['event']=='load_started' for e in events(log))
            print('Blank tab black from first second, visible brand at right, no web navigation: passed',flush=True)

            # Save and remove across independent invocations; then inspect a Google search URL.
            for phase in ('add','remove'):
                log=output/('favorite-'+phase+'.jsonl')
                with (output/('favorite-'+phase+'.stderr')).open('w') as stderr:
                    p=subprocess.Popen([str(binary),'--profile',str(profile),'--no-update','--telemetry',str(log),'--quit-after','25',url+'/check'],stdout=subprocess.DEVNULL,stderr=stderr)
                    try:
                        wait_for(lambda:any(e['event']=='load_finished' for e in events(log)))
                        wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=8).splitlines()[0]
                        subprocess.run(['xdotool','windowfocus','--sync',wid],check=True,timeout=5)
                        def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True,timeout=5)
                        key('ctrl+d');fav=profile/'favorites.ini'
                        if phase=='add':wait_for(lambda:fav.exists() and url+'/check' in fav.read_text())
                        else:wait_for(lambda:fav.exists() and url+'/check' not in fav.read_text())
                        if phase=='add':
                            key('ctrl+shift+d');time.sleep(.3);key('Escape')
                            key('ctrl+shift+m');wait_for(lambda:'127.0.0.1' not in (profile/'light-sites').read_text())
                            wait_for(lambda:sum(e['event']=='load_finished' for e in events(log))>=2)
                            key('ctrl+shift+m');wait_for(lambda:'127.0.0.1' in (profile/'light-sites').read_text())
                        if phase=='remove':
                            key('ctrl+l');subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1','babinium prueba'],check=True,timeout=5);key('Return')
                            wait_for(lambda:any(e['event']=='load_started' and e['value'].startswith('https://www.google.com/search?q=babinium%20prueba') for e in events(log)))
                    finally:
                        p.terminate();p.wait(timeout=10)
            print('Favorites saved and removed across restart; Google address-bar search: passed',flush=True)
            print(json.dumps({'dark':first,'after_restart':second,'light':light,'blank_rgb':rgb},ensure_ascii=False),flush=True)
    finally:server.shutdown()

if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
