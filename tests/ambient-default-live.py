#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test a one-time YouTube ambient default and a manual choice across restarts."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import time

binary=Path(sys.argv[1]).resolve();data=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();lang=sys.argv[4] if len(sys.argv)>4 else 'en'
out.mkdir(parents=True,exist_ok=True);profile=out/'profile';driver=Path(__file__).with_name('youtube-ambient.js').resolve()
key='babinium-ambient-default-v1'
def launch(label):
    log=(out/(label+'.stderr')).open('w')
    process=subprocess.Popen([str(binary),'--profile',str(profile),'--data-dir',str(data),'--no-update','--autoplay',
        '--eval',str(driver),'--eval-after','30','--quit-after','115','https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl='+lang],stdout=subprocess.DEVNULL,stderr=log)
    wid=subprocess.check_output(['xdotool','search','--sync','--onlyvisible','--pid',str(process.pid)],text=True,timeout=10).splitlines()[0]
    return process,wid,log
def state(wid):
    title=subprocess.check_output(['xdotool','getwindowname',wid],text=True,timeout=5).strip()
    if not title.startswith('BBAMBIENT:'):return None
    try:return json.loads(base64.b64decode(title[10:].split(' — ')[0]))
    except (ValueError,TypeError):return None
def wait(wid,fn,seconds=70):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        value=state(wid)
        if value and fn(value):return value
        time.sleep(.3)
    raise AssertionError('Timed out: '+str(state(wid)))
def click(wid,box,value):
    geometry=subprocess.check_output(['xdotool','getwindowgeometry','--shell',wid],text=True)
    size=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
    x=round((int(size['WIDTH'])-value['viewport'][0])/2+box['x']+box['w']/2)
    y=round(int(size['HEIGHT'])-value['viewport'][1]+box['y']+box['h']/2)
    subprocess.run(['xdotool','mousemove','--window',wid,str(x),str(y)],check=True);time.sleep(.4)
    subprocess.run(['xdotool','click','1'],check=True)
first,wid,log=launch('first')
try:
    default=wait(wid,lambda v:v.get('ambient') is False and v.get('preferences',{}).get(key)=='1' and v.get('time',0)>2 and v.get('height')==360)
    subprocess.run(['xdotool','windowfocus','--sync',wid],check=True)
    subprocess.run(['xdotool','mousemove','--window',wid,'400','300'],check=True);time.sleep(.5)
    v=wait(wid,lambda s:s.get('gear') and s['gear']['w']>0);click(wid,v['gear'],v)
    def is_ambient(i):return any(s in i['text'].lower() for s in ('ambient mode','modo ambiente','iluminación cinemática'))
    v=wait(wid,lambda s:any(is_ambient(i) for i in s['items']),seconds=15)
    item=next(i for i in v['items'] if is_ambient(i));click(wid,item,v)
    manual=wait(wid,lambda v:v.get('ambient') is True and v.get('preferences',{}).get(key)=='1',seconds=15)
    time.sleep(6)
finally:first.terminate();first.wait(timeout=10);log.close()
second,wid,log=launch('restart')
try:
    persisted=wait(wid,lambda v:v.get('ambient') is True and v.get('preferences',{}).get(key)=='1' and v.get('time',0)>2)
    result={'default_ambient':default['ambient'],'default_quality':default['quality'],'manual_ambient':manual['ambient'],
        'after_restart':persisted['ambient'],'marker_after_restart':persisted['preferences'][key]}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:second.terminate();second.wait(timeout=10);log.close()
