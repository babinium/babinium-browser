#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Save a favorite and navigate back to it using the actual GTK popover."""
import http.server
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

from features import Handler,events,wait_for

binary=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='bb-favorites-') as temp:
        base=f'http://127.0.0.1:{server.server_port}';log=output/'events.jsonl'
        with (output/'stderr').open('w') as stderr:
            p=subprocess.Popen([str(binary),'--profile',temp,'--no-update','--telemetry',str(log),'--quit-after','30',base+'/check'],stdout=subprocess.DEVNULL,stderr=stderr)
            try:
                wait_for(lambda:any(e['event']=='load_finished' for e in events(log)))
                wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(p.pid)],text=True,timeout=8).splitlines()[0]
                subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
                def key(k):subprocess.run(['xdotool','key','--clearmodifiers','--window',wid,k],check=True)
                def title():return subprocess.check_output(['xdotool','getwindowname',wid],text=True)
                key('ctrl+d');wait_for(lambda:(Path(temp)/'favorites.ini').exists())
                key('ctrl+l');subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',base+'/set'],check=True);key('Return')
                wait_for(lambda:'Fixture /set' in title())
                key('ctrl+shift+d');time.sleep(.4);key('Tab');key('Return')
                wait_for(lambda:'Fixture /check' in title())
                print('Favorite opened from GTK popover: passed',flush=True)
            finally:p.terminate();p.wait(timeout=10)
finally:server.shutdown()
