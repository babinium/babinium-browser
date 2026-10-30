#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native GTK keyboard/tab/site-control/download smoke test on visible X11."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from ui import browser_window, key

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200)
        if self.path=='/download':
            self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Disposition','attachment; filename="fixture.txt"')
            self.end_headers();self.wfile.write(b'Babinium verified download\n')
        else:
            self.send_header('Content-Type','text/html');self.end_headers()
            self.wfile.write(f'<!doctype html><title>Fixture {self.path}</title><p>Site content</p>'.encode())

def wait_for(fn,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if fn():return
        time.sleep(.1)
    raise AssertionError('Timed out waiting for UI condition')

def run(binary,output):
    output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='bb-ui-') as tmp:
            tmp=Path(tmp);config=tmp/'config';config.mkdir();downloads=tmp/'downloads';downloads.mkdir()
            (config/'user-dirs.dirs').write_text(f'XDG_DOWNLOAD_DIR="{downloads}"\n')
            profile=tmp/'profile';env=dict(os.environ,XDG_CONFIG_HOME=str(config))
            log=output/'events.jsonl';url=f'http://127.0.0.1:{server.server_port}'
            with (output/'stderr.log').open('w') as stderr:
                p=subprocess.Popen([str(binary),'--profile',str(profile),'--no-update','--telemetry',str(log),'--quit-after','75','--screenshot',str(output/'ui.png'),'--snapshot-after','12',url+'/first'],env=env,stderr=stderr)
                try:
                    def events():return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
                    wait_for(lambda:any(e['event']=='load_finished' for e in events()))
                    wid=browser_window(p.pid)
                    subprocess.run(['xdotool','windowfocus','--sync',wid],check=True,timeout=5)
                    def title():return subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5)
                    loads=sum(e['event']=='load_started' for e in events())
                    key('ctrl+t');wait_for(lambda:'Nueva pestaña' in title());time.sleep(.4)
                    assert sum(e['event']=='load_started' for e in events())==loads,'Empty tab launched WebKit'
                    key('ctrl+l')
                    subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',url+'/second'],check=True,timeout=5);key('Return')
                    wait_for(lambda:'Fixture /second' in title())
                    key('ctrl+shift+Tab');wait_for(lambda:'Fixture /first' in title())
                    key('ctrl+b');wait_for(lambda:(profile/'disabled-sites').exists() and '127.0.0.1' in (profile/'disabled-sites').read_text())
                    key('ctrl+b');wait_for(lambda:'127.0.0.1' not in (profile/'disabled-sites').read_text())
                    key('ctrl+w');wait_for(lambda:'Fixture /second' in title())
                    key('ctrl+l');subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',url+'/third'],check=True,timeout=5);key('Return')
                    wait_for(lambda:'Fixture /third' in title())
                    key('alt+Left');wait_for(lambda:'Fixture /second' in title())
                    key('alt+Right');wait_for(lambda:'Fixture /third' in title())
                    time.sleep(.2);loads=sum(e['event']=='load_finished' for e in events());key('ctrl+r')
                    wait_for(lambda:sum(e['event']=='load_finished' for e in events())>loads)
                    key('ctrl+l');subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',url+'/download'],check=True,timeout=5);key('Return')
                    wait_for(lambda:(downloads/'fixture.txt').exists())
                    assert (downloads/'fixture.txt').read_bytes()==b'Babinium verified download\n'
                    wait_for(lambda:(output/'ui.png').exists(),timeout=15)
                    print('Native GTK lazy tabs, tab closing, back/forward/reload, site toggle, and download: passed',flush=True)
                finally:
                    p.terminate();p.wait(timeout=10)
    finally:server.shutdown()

if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
