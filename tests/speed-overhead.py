#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare two built bundles on the same idle local page on the active display."""
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

old=Path(sys.argv[1]).resolve();new=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=False)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        body=('<!doctype html><title>Pagina estatica</title><body style="background:#111;color:#ddd">'+('<p>Contenido local</p>'*150)+'</body>').encode()
        self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-speed-bench-') as temp:
        for name,binary in [('previous',old),('current',new)]:
            dest=out/name;profile=Path(temp)/name
            cmd=['python3','scripts/measure.py','--out',str(dest),'--duration','30','--warmup','15','--',
                str(binary),'--profile',str(profile),'--no-update','--no-block','--telemetry',str(dest/'events.jsonl'),f'http://127.0.0.1:{server.server_port}/']
            with (out/(name+'.json')).open('w') as log:subprocess.run(cmd,stdout=log,check=True,timeout=45)
            s=json.loads((dest/'summary.json').read_text());
            if s['returncode_after_measurement']!=-15 or not s.get('load_finished_from_spawn_ms'):raise AssertionError(s)
            print(json.dumps({'case':name,'pss_mib':s['pss_steady_median_mib'],'rss_mib':s['rss_steady_median_mib'],
                'cpu_one_core_percent':s['cpu_steady_one_core_percent'],'processes':s['max_process_count']}),flush=True)
finally:server.shutdown()
