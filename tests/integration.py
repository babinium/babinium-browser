#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise actual WebKit requests, DOM filtering and early scriptlet injection."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

seen=[]
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        seen.append(self.path)
        self.send_response(200)
        if self.path.endswith('.js'):
            self.send_header('Content-Type','text/javascript');body=b'window.requestExecuted=true;'
        else:
            self.send_header('Content-Type','text/html')
            body=b'''<!doctype html><title>Babinium fixture</title>
            <script>window.fixtureConstant=false;</script>
            <script src="/blocked-ad.js"></script><script src="/allowed-ad.js"></script>
            <div class="bb-specific">Specific ad</div><div class="bb-except">Excepted content</div>
            <div id="bb-procedural">Sponsored item</div><div id="content">Actual content</div>
            <script>setTimeout(()=>{const d=document.createElement('div');d.className='bb-generic';d.textContent='Dynamic generic ad';document.body.append(d);},500);</script>'''
        self.end_headers();self.wfile.write(body)

def run(binary,compiler,output):
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    output.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='bb-integration-') as tmp:
            tmp=Path(tmp);script=tmp/'check.js'
            script.write_text("JSON.stringify({scriptlet:window.fixtureConstant,specific:getComputedStyle(document.querySelector('.bb-specific')).display,generic:getComputedStyle(document.querySelector('.bb-generic')).display,excepted:getComputedStyle(document.querySelector('.bb-except')).display,procedural:!!document.getElementById('bb-procedural'),content:document.getElementById('content').textContent})")
            for enabled in [True,False]:
                seen.clear();profile=tmp/('enabled' if enabled else 'disabled');current=profile/'filters/current';current.mkdir(parents=True)
                subprocess.run([str(compiler),'compile',str(Path(__file__).parent/'fixture-lists'),str(current/'engine.bin')],check=True)
                if not enabled:(profile/'disabled-sites').write_text('127.0.0.1\n')
                log=output/('enabled.jsonl' if enabled else 'disabled.jsonl')
                command=[str(binary),'--profile',str(profile),'--no-update','--audit','--telemetry',str(log),'--eval',str(script),'--eval-after','3','--quit-after','6',f'http://127.0.0.1:{server.server_port}/']
                result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=25)
                (output/('enabled.stderr' if enabled else 'disabled.stderr')).write_text(result.stderr)
                if result.returncode:raise AssertionError(f'Browser exited {result.returncode}: {result.stderr}')
                events=[json.loads(l) for l in log.read_text().splitlines()]
                values=[json.loads(e['value']) for e in events if e['event']=='javascript']
                if not values:raise AssertionError(f'Missing evaluation: {events}')
                value=values[-1]
                assert value['content']=='Actual content',value
                assert '/allowed-ad.js' in seen,seen
                assert ('/blocked-ad.js' not in seen)==enabled,seen
                assert value['scriptlet'] is enabled,value
                assert (value['specific']=='none')==enabled,value
                assert (value['generic']=='none')==enabled,value
                assert value['excepted']!='none',value
                assert value['procedural'] is not enabled,value
                print(json.dumps({'enabled':enabled,'assertions':'passed','dom':value,'requests_seen':list(seen)}),flush=True)
    finally:server.shutdown()

if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())
