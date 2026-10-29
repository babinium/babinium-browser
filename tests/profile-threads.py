#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sample CPU per thread for a running browser process, without ptrace."""
import argparse
import json
import os
from pathlib import Path
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pid',type=int)
parser.add_argument('--seconds',type=float,default=10)
args=parser.parse_args()
ticks=os.sysconf('SC_CLK_TCK')

def sample():
    threads={}
    for entry in (Path('/proc')/str(args.pid)/'task').iterdir():
        try:
            raw=(entry/'stat').read_text();i=raw.rfind(')');fields=raw[i+2:].split()
            threads[int(entry.name)]={'name':raw[raw.find('(')+1:i],'cpu':(int(fields[11])+int(fields[12]))/ticks,'start':int(fields[19])}
        except (FileNotFoundError,ProcessLookupError):pass
    return threads

before=sample();start=time.monotonic();time.sleep(args.seconds);after=sample();elapsed=time.monotonic()-start
rows=[{'tid':tid,'name':a['name'],'cpu_one_core_percent':round((a['cpu']-before[tid]['cpu'])/elapsed*100,2)}
      for tid,a in after.items() if tid in before and a['start']==before[tid]['start']]
rows.sort(key=lambda row:-row['cpu_one_core_percent'])
print(json.dumps({'pid':args.pid,'duration_seconds':round(elapsed,2),'threads':rows[:20]},indent=2))
