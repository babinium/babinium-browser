#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check viewport-aware animation suspension in real WebKit on the visible desktop."""
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = b'''<!doctype html><meta charset="utf-8"><title>Animaciones de prueba</title>
        <style>
          body {min-height: 9000px; background:#222; color:white}
          .box {position:absolute; left:80px; width:150px; height:80px;
                background:#369; animation:pulse 1s infinite alternate}
          #near {top:120px} #far {top:5000px} #finite {top:6500px; animation:once 60s 1}
          #user-paused {top:7000px; animation-play-state:paused}
          #mixed {top:7500px; animation:pulse 1s infinite, once 60s 1}
          #changing {top:7800px} #changing.add-finite {animation:pulse 1s infinite, once 60s 1}
          #user-choice {top:8200px}
          @keyframes pulse {from{opacity:.5} to{opacity:1}}
          @keyframes once {from{opacity:.7} to{opacity:1}}
        </style>
        <div id="near" class="box">Visible primero</div>
        <div id="far" class="box">Visible despues</div>
        <div id="finite" class="box">Animacion finita</div>
        <div id="user-paused" class="box">Pausada por la pagina</div>
        <div id="mixed" class="box">Animaciones mezcladas</div>
        <div id="changing" class="box">Agrega una animacion finita</div>
        <div id="user-choice" class="box">La pagina decide pausar</div>
        <script>
          function sample() { return Object.fromEntries(['near','far','finite','user-paused','mixed','changing','user-choice'].map(id=>{
            return [id,document.getElementById(id).getAnimations().map(a=>({state:a.playState,time:a.currentTime}))];
          })); }
          window.results={};
          setTimeout(()=>{window.results.before=sample();document.getElementById('changing').classList.add('add-finite');
            document.getElementById('user-choice').style.animationPlayState='paused';document.getElementById('far').scrollIntoView();},3000);
          setTimeout(()=>{window.results.after=sample();document.getElementById('user-choice').scrollIntoView();},6000);
          setTimeout(()=>{window.results.final=sample();},9000);
        </script>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


binary = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-animations-') as temp:
        temp = Path(temp)
        script = temp / 'inspect.js'
        script.write_text('JSON.stringify(window.results)')
        log = output / 'events.jsonl'
        command = [str(binary), '--profile', str(temp / 'profile'), '--no-update',
                   '--telemetry', str(log), '--eval', str(script), '--eval-after', '11',
                   '--screenshot', str(output / 'screen.png'), '--snapshot-after', '10',
                   '--quit-after', '13']
        if len(sys.argv) > 3:
            command += ['--data-dir', str(Path(sys.argv[3]).resolve())]
        command += [f'http://127.0.0.1:{server.server_port}/']
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        (output / 'stderr.log').write_text(result.stderr)
        assert result.returncode == 0, result.stderr
        events = [json.loads(line) for line in log.read_text().splitlines()]
        values = [json.loads(event['value']) for event in events if event['event'] == 'javascript']
        assert values, events
        state = values[-1]
        before, after, final = state['before'], state['after'], state['final']
        assert before['near'][0]['state'] == 'running', state
        assert before['far'][0]['state'] == 'paused', state
        assert before['finite'][0]['state'] == 'running', state
        assert before['user-paused'][0]['state'] == 'paused', state
        assert all(a['state'] == 'running' for a in before['mixed']) and len(before['mixed']) == 2, state
        assert before['changing'][0]['state'] == 'paused', state
        assert after['near'][0]['state'] == 'paused', state
        assert after['far'][0]['state'] == 'running', state
        assert after['finite'][0]['state'] == 'running', state
        assert after['user-paused'][0]['state'] == 'paused', state
        assert all(a['state'] == 'running' for a in after['changing']) and len(after['changing']) == 2, state
        assert after['far'][0]['time'] > before['far'][0]['time'], state
        assert final['user-choice'][0]['state'] == 'paused', state
        print('Animaciones infinitas fuera de pantalla pausadas y reanudadas al desplazarse:',
              json.dumps(state), flush=True)
finally:
    server.shutdown()
