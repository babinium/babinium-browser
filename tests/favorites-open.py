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
from ui import browser_window,key

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
                wid=browser_window(p.pid)
                subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
                def title():return subprocess.check_output(['xdotool','getwindowname',wid],text=True)
                key('ctrl+d');wait_for(lambda:(Path(temp)/'favorites.ini').exists())
                key('ctrl+l');subprocess.run(['xdotool','type','--clearmodifiers','--window',wid,'--delay','1',base+'/set'],check=True);key('Return')
                wait_for(lambda:'Fixture /set' in title())
                key('ctrl+shift+d');time.sleep(.4);key('Tab');key('Return')
                wait_for(lambda:'Fixture /check' in title())
                # Allow the closing transition to finish, then click the
                # remove button of the first row in the wide desktop popover.
                time.sleep(1);key('ctrl+shift+d');time.sleep(.5)
                geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
                width=int(dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)['WIDTH'])
                subprocess.run(['xdotool','mousemove','--window',wid,str(width-80),'78','click','1'],check=True,timeout=5)
                wait_for(lambda:base+'/check' not in (Path(temp)/'favorites.ini').read_text())
                print('Favorite opened and removed from GTK popover: passed',flush=True)
            finally:p.terminate();p.wait(timeout=10)
finally:server.shutdown()
