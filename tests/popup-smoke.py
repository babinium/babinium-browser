#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test a user-triggered related popup and its opener communication."""
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

from features import Handler, events, wait_for

binary=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-popup-') as temp:
        log=output/'events.jsonl';url=f'http://127.0.0.1:{server.server_port}/check'
        with (output/'stderr').open('w') as stderr:
            p=subprocess.Popen([str(binary),'--profile',temp,'--no-update','--telemetry',str(log),'--quit-after','25',url],stdout=subprocess.DEVNULL,stderr=stderr)
            try:
                wait_for(lambda:any(e['event']=='load_finished' for e in events(log)))
                wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=8).splitlines()[0]
                subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
                subprocess.run(['xdotool','mousemove','--window',wid,'150','210','click','1'],check=True)
                wait_for(lambda:any(e['event']=='load_finished' and e['value'].endswith('/popup-result') for e in events(log)))
                wait_for(lambda:'Popup opened' in subprocess.check_output(['xdotool','getwindowname',wid],text=True))
                subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,'ctrl+shift+Tab'],check=True)
                wait_for(lambda:'Opener confirmed' in subprocess.check_output(['xdotool','getwindowname',wid],text=True))
                print(json.dumps({'related_popup':'passed','opener_communication':'passed'}),flush=True)
            finally:p.terminate();p.wait(timeout=10)
finally:server.shutdown()
