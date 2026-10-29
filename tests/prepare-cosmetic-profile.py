#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare an isolated, development-only cosmetic profiler (never packaged)."""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('destination', type=Path)
parser.add_argument('driver', type=Path)
args = parser.parse_args()
source = args.source.resolve()
destination = args.destination.resolve()
if destination.exists():
    parser.error('Destination must not exist')
original = (source / 'cosmetic.js').read_text()
needle = '\npending.push(document);schedule();'
if original.count(needle) != 1 or original.count('__bbQuery(') != 1:
    raise ValueError('Unexpected cosmetic runtime: refusing to patch profiler')
shutil.copytree(source, destination)
runtime = destination / 'cosmetic.js'
prefix = '''
const __bbProfile={scans:0,scanMs:0,actions:0,actionMs:0,queries:0,queryMs:0,queued:0};
const __bbNativeQuery=__bbQuery;
function __bbProfileQuery(...args){const start=performance.now();try{return __bbNativeQuery(...args);}
    finally{__bbProfile.queries++;__bbProfile.queryMs+=performance.now()-start;}}
'''
wrappers = '''
const __bbOriginalScan=scan, __bbOriginalActions=actions;
actions=function(){const start=performance.now();try{return __bbOriginalActions();}
    finally{__bbProfile.actions++;__bbProfile.actionMs+=performance.now()-start;}};
scan=function(){const start=performance.now();__bbProfile.queued+=pending.length;
    try{return __bbOriginalScan();}finally{__bbProfile.scans++;__bbProfile.scanMs+=performance.now()-start;}};
setInterval(()=>document.documentElement?.setAttribute('data-bb-profile',JSON.stringify(__bbProfile)),5000);
'''
runtime.write_text(prefix + original.replace('__bbQuery(', '__bbProfileQuery(').replace(needle, wrappers + '\n' + needle))
driver = Path(__file__).with_name('youtube-play-default.js').read_text()
driver += '''
setInterval(()=>{const value=document.documentElement?.getAttribute('data-bb-profile');
    if(value)document.title='BBPROFILE:'+btoa(value);},2000);
'''
args.driver.write_text(driver)
print('Prepared isolated profiler at', destination)
