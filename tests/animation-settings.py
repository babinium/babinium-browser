#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the native animation control, reload behavior and profile persistence."""
import http.server
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

from features import wait_for
from ui import browser_window, key


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = b'''<!doctype html><title>Preparando</title>
        <style>body{min-height:8000px}#far{position:absolute;top:5000px;width:100px;height:100px;
        animation:pulse 2s infinite}@keyframes pulse{from{opacity:.5}to{opacity:1}}</style>
        <div id="far">Animacion lejana</div>
        <script>setInterval(()=>{const a=document.getElementById('far').getAnimations()[0];
          if(a)document.title='ANIM:'+a.playState;},300)</script>'''
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
    with tempfile.TemporaryDirectory(prefix='bb-animation-settings-') as temp:
        profile = Path(temp)
        marker = profile / 'normal-animations'
        url = f'http://127.0.0.1:{server.server_port}/'

        def cycle(name, initial, expected, marker_expected):
            with (output / (name + '.stderr')).open('w') as err:
                browser = subprocess.Popen([str(binary), '--profile', str(profile), '--no-update',
                                            '--quit-after', '55', url], stdout=subprocess.DEVNULL, stderr=err)
                try:
                    wid = browser_window(browser.pid)
                    def title():
                        return subprocess.check_output(['xdotool', 'getwindowname', wid], text=True, timeout=5)
                    wait_for(lambda: 'ANIM:' + initial in title(), 20)
                    subprocess.run(['xdotool', 'windowfocus', '--sync', wid], check=True, timeout=5)
                    geometry = subprocess.check_output(['xdotool', 'getwindowgeometry', '--shell', wid], text=True)
                    width = int(dict(line.split('=', 1) for line in geometry.splitlines() if '=' in line)['WIDTH'])
                    subprocess.run(['xdotool', 'mousemove', '--window', wid, str(width - 52), '50', 'click', '1'], check=True)
                    wait_for(lambda: 'Ayuda de Babinium' in title())
                    time.sleep(.4)
                    # The visible label is a large click target in the help tab.
                    subprocess.run(['xdotool', 'mousemove', '--window', wid, str(width // 2 - 180), '500', 'click', '1'], check=True)
                    wait_for(lambda: marker.exists() is marker_expected)
                    key('ctrl+1')
                    key('ctrl+r')
                    wait_for(lambda: 'ANIM:' + expected in title(), 20)
                finally:
                    browser.terminate()
                    browser.wait(timeout=10)

        cycle('disable', 'paused', 'running', True)
        cycle('enable-after-restart', 'running', 'paused', False)
        print('Opción de animaciones: cambios tras recargar y preferencia conservada al reiniciar: correcto', flush=True)
finally:
    server.shutdown()
