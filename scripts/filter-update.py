#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""On-demand updater. HTTPS, conditional fetch, bounded size, atomic generations.

No daemon. The browser launches it after startup and checks hourly; successful
generations are refreshed at most every six hours. A failure keeps the old set.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import urllib.parse

MAX_BYTES = 32 * 1024 * 1024
CAPABILITIES = {"env_safari", "ext_ublock"}

def condition(expression):
    tokens = re.findall(r"[A-Za-z_][\w-]*|&&|\|\||!|\(|\)", expression)
    if ''.join(tokens) != re.sub(r'\s', '', expression):
        raise ValueError(f"Unknown preprocessor expression: {expression}")
    pos = 0
    def atom():
        nonlocal pos
        if pos >= len(tokens): raise ValueError("Incomplete expression")
        t=tokens[pos]; pos+=1
        if t=='!': return not atom()
        if t=='(':
            result=expression_or()
            if pos>=len(tokens) or tokens[pos]!=')': raise ValueError("Unbalanced expression")
            pos+=1;return result
        if t in {'&&','||',')'}: raise ValueError("Invalid expression")
        return t in CAPABILITIES
    def expression_and():
        nonlocal pos
        r=atom()
        while pos<len(tokens) and tokens[pos]=='&&':
            pos+=1; rhs=atom();r=r and rhs
        return r
    def expression_or():
        nonlocal pos
        r=expression_and()
        while pos<len(tokens) and tokens[pos]=='||':
            pos+=1;rhs=expression_and();r=r or rhs
        return r
    result=expression_or()
    if pos!=len(tokens):raise ValueError("Trailing condition")
    return result

def preprocess(text, includes=frozenset()):
    stack=[]; active=True; out=[]
    for line in text.splitlines():
        if line.startswith('!#if '):
            yes=condition(line[5:].strip());stack.append((active,yes,False));active=active and yes
        elif line.startswith('!#else'):
            if not stack:raise ValueError("Unexpected else")
            parent,yes,seen=stack[-1]
            if seen:raise ValueError("Duplicate else")
            stack[-1]=(parent,yes,True);active=parent and not yes
        elif line.startswith('!#endif'):
            if not stack:raise ValueError("Unexpected endif")
            active=stack.pop()[0]
        elif line.startswith('!#include'):
            if active and line.split(maxsplit=1)[-1] not in includes:raise ValueError("Includes must be enumerated in sources.json: "+line)
        elif active:out.append(line)
    if stack:raise ValueError("Unterminated preprocessor condition")
    return '\n'.join(out)+'\n'

def fetch(url, previous, includes=frozenset()):
    if not url.startswith('https://'):raise ValueError("HTTPS required")
    headers={'User-Agent':'BabiniumBrowser/0.1 filter-updater'}
    if previous.get('etag'):headers['If-None-Match']=previous['etag']
    if previous.get('modified'):headers['If-Modified-Since']=previous['modified']
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as response:
            if not response.url.startswith('https://'):raise ValueError("HTTPS downgrade")
            body=response.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES:raise ValueError("List too large")
            text=body.decode('utf-8-sig')
            if len(text)<100 or text.lstrip().startswith('<'):raise ValueError("Not a filter list")
            return preprocess(text,includes),{'url':url,'etag':response.headers.get('ETag'),'modified':response.headers.get('Last-Modified'),'sha256_source':hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as e:
        if e.code==304:return None,previous
        raise

def update(args):
    cache=Path(args.cache); data=Path(args.data);cache.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (cache/'update.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        current=cache/'current';old={}
        if (current/'state.json').exists():old=json.loads((current/'state.json').read_text())
        if not args.force and time.time()-old.get('updated',0)<6*3600 and (current/'engine.bin').exists():return
        sources=json.loads((data/'sources.json').read_text())
        includes={urllib.parse.urlparse(s['url']).path.rsplit('/',1)[-1] for s in sources}
        stage=Path(tempfile.mkdtemp(prefix='generation-',dir=cache))
        try:
            lists=stage/'lists';lists.mkdir()
            state={'updated':time.time(),'sources':{}}
            for source in sources:
                name=source['file']; previous=old.get('sources',{}).get(name,{})
                text,meta=fetch(source['url'],previous,includes)
                if text is None:
                    shutil.copyfile(current/'lists'/name,lists/name)
                else:(lists/name).write_text(text)
                state['sources'][name]=meta
            subprocess.run([args.compiler,'compile',str(lists),str(stage/'engine.bin')],check=True,timeout=120)
            subprocess.run([args.compiler,'validate',str(stage/'engine.bin'),str(data/'resources.json')],check=True,timeout=30)
            (stage/'state.json').write_text(json.dumps(state,indent=2)+'\n')
            for p in [stage/'engine.bin',stage/'state.json']:
                with p.open('rb') as f:os.fsync(f.fileno())
            tmp=cache/'current.new'
            tmp.unlink(missing_ok=True);tmp.symlink_to(stage.name);tmp.replace(current)
            # Old engines are fully owned by the web processes; keep one rollback.
            generations=sorted(cache.glob('generation-*'),key=lambda p:p.stat().st_mtime,reverse=True)
            for stale in generations[2:]:shutil.rmtree(stale)
            print('Filter generation updated',flush=True)
        except BaseException:
            shutil.rmtree(stage,ignore_errors=True);raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',required=True);p.add_argument('--data',required=True);p.add_argument('--compiler',required=True)
    p.add_argument('--force',action='store_true');p.add_argument('--if-due',action='store_true')
    try:update(p.parse_args())
    except Exception as e:print(f'Lists unchanged: {e}',file=sys.stderr);sys.exit(1)
