#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure a built adblock engine, including URL cosmetic queries; no compiling."""
import argparse
import ctypes
import json
from pathlib import Path
import statistics
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('bundle',type=Path)
parser.add_argument('--iterations',type=int,default=100)
args=parser.parse_args();base=args.bundle.resolve()
library=ctypes.CDLL(str(base/'lib/babinium-browser/libbabinium-adblock.so'))
library.bb_engine_load.argtypes=[ctypes.c_char_p,ctypes.c_char_p];library.bb_engine_load.restype=ctypes.c_void_p
library.bb_engine_free.argtypes=[ctypes.c_void_p]
library.bb_cosmetics.argtypes=[ctypes.c_void_p,ctypes.c_char_p];library.bb_cosmetics.restype=ctypes.c_void_p
library.bb_generic.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p];library.bb_generic.restype=ctypes.c_void_p
library.bb_string_free.argtypes=[ctypes.c_void_p]
data=base/'share/babinium-browser';started=time.monotonic();cpu=time.process_time()
engine=library.bb_engine_load(str(data/'engine.bin').encode(),str(data/'resources.json').encode())
if not engine:raise SystemExit('Failed to load engine')
load={'wall_ms':round((time.monotonic()-started)*1000,2),'cpu_ms':round((time.process_time()-cpu)*1000,2)}
def value(p):
    try:return ctypes.string_at(p).decode() if p else ''
    finally:library.bb_string_free(p)
def rss_pss():
    data={l.split(':',1)[0]:int(l.split()[1]) for l in Path('/proc/self/smaps_rollup').read_text().splitlines()[1:] if len(l.split())>=2}
    return {'rss_mib':round(data.get('Rss',0)/1024,2),'pss_mib':round(data.get('Pss',0)/1024,2)}
results=[];classes=json.dumps(['container','content','header','footer','ad','advertisement','sidebar','banner']+[f'class-{i}' for i in range(100)]).encode();ids=b'["content","header","advert"]'
try:
    for url in ['https://www.youtube.com/watch?v=dQw4w9WgXcQ','https://github.com/babinium/babinium-browser','https://www.bbc.com/']:
        u=url.encode();specific=json.loads(value(library.bb_cosmetics(engine,u)))
        durations=[]
        for _ in range(args.iterations):
            start=time.process_time_ns();value(library.bb_generic(engine,u,classes,ids));durations.append((time.process_time_ns()-start)/1e6)
        results.append({'origin':url.split('/')[2],'generichide':specific.get('generichide'),'specific_selectors':len(specific.get('hide_selectors',[])),
            'procedural_rules':len(specific.get('procedural_actions',[])),'script_bytes':len(specific.get('injected_script','').encode()),
            'generic_mean_ms':round(statistics.mean(durations),3),'generic_median_ms':round(statistics.median(durations),3),'iterations':args.iterations})
    print(json.dumps({'load':load,'process_memory':rss_pss(),'results':results},indent=2))
finally:library.bb_engine_free(engine)
