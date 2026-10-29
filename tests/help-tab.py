#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Open Babinium's native help from a blank tab, then navigate from it."""
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

binary=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        body=b'<!doctype html><title>Navigation from help</title><p>OK</p>';self.send_response(200)
        self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-help-') as temp:
        log=out/'events.jsonl';png=out/'help.png'
        with (out/'stderr.log').open('w') as err:
            p=subprocess.Popen([str(binary),'--profile',temp,'--no-update','--telemetry',str(log),'--screenshot',str(png),
                '--snapshot-after','3','--quit-after','30'],stdout=subprocess.DEVNULL,stderr=err)
            try:
                wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
                def title():return subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5)
                def wait(fn,seconds=15):
                    end=time.monotonic()+seconds
                    while time.monotonic()<end:
                        if fn():return
                        time.sleep(.1)
                    raise AssertionError('Timed out; title='+title())
                def events():return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
                def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True,timeout=5)
                geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
                width=int(dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)['WIDTH'])
                subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
                subprocess.run(['xdotool','mousemove','--window',wid,str(width-52),'50','click','1'],check=True)
                wait(lambda:'Ayuda de Babinium' in title());wait(png.exists)
                assert not any(e['event']=='load_started' for e in events()),'Help unexpectedly loaded a web page'
                # Native help must not start a WebKit subprocess from an empty window.
                children=Path('/proc')/str(p.pid)/'task'/str(p.pid)/'children'
                assert not children.read_text().strip(),'Help unexpectedly started a child process'
                key('ctrl+l');url=f'http://127.0.0.1:{server.server_port}/'
                subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',url],check=True);key('Return')
                wait(lambda:'Navigation from help' in title());key('ctrl+w');wait(lambda:'Nueva pestaña' in title())
                print('Native help opened without WebKit, remained navigable and closed normally: passed',flush=True)
            finally:p.terminate();p.wait(timeout=10)
finally:server.shutdown()
