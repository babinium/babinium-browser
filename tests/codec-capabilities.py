#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inspect media capability claims in an isolated local page, without credentials."""
import base64
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
        self.wfile.write(b'<!doctype html><title>Codec capability test</title><p>Local test</p>')

server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-codecs-') as temp:
        root=Path(__file__).resolve().parent
        command=[str(Path(sys.argv[1]).resolve()),'--profile',temp,'--no-update','--eval',str(root/'codec-capabilities.js'),'--eval-after','3','--quit-after','20',f'http://127.0.0.1:{server.server_port}/']
        p=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=10).splitlines()[0]
            for attempt in range(120):
                title=subprocess.check_output(['xdotool','getwindowname',wid],text=True).strip()
                if title.startswith('BB-CAPS:'):
                    encoded=title[len('BB-CAPS:'):].split(' — ')[0]
                    print(json.dumps(json.loads(base64.b64decode(encoded)),indent=2),flush=True);break
                time.sleep(.1)
            else:raise RuntimeError('No media capability result')
        finally:p.terminate();p.wait(timeout=10)
finally:server.shutdown()
