#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build-time download of pinned, auditable upstream sources."""
import json
import hashlib
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('updater',ROOT/'scripts/filter-update.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)
pins=json.loads((ROOT/'data/upstream.json').read_text())
out=ROOT/'build/share/babinium-browser';out.mkdir(parents=True,exist_ok=True)
up=ROOT/'build/upstream';up.mkdir(parents=True,exist_ok=True)
# Pin the published API bundle and retain its license and exact source archive.
dark=up/'darkreader.tar.gz'
urllib.request.urlretrieve('https://registry.npmjs.org/darkreader/-/darkreader-4.9.134.tgz',dark)
if hashlib.sha256(dark.read_bytes()).hexdigest()!='e3da6d984ffa830229c31f531fc9f0666910549ff74655c022bb411c70d47745':
    raise ValueError('Dark Reader archive hash mismatch')
with tarfile.open(dark) as t:
    for source,target in [('package/darkreader.js','darkreader.js'),('package/LICENSE','darkreader-LICENSE')]:
        member=t.getmember(source)
        if not member.isfile():raise ValueError('Invalid Dark Reader archive')
        (out/target).write_bytes(t.extractfile(member).read())
for name,repo in [('ubo','gorhill/uBlock'),('brave','brave/adblock-resources')]:
    archive=up/(name+'.tar.gz')
    urllib.request.urlretrieve(f'https://codeload.github.com/{repo}/tar.gz/{pins[name]}',archive)
    dest=up/name;dest.mkdir(exist_ok=True)
    with tarfile.open(archive) as t:
        # Strip the top-level directory; tar's data filter rejects escaping links.
        members=[]
        for m in t.getmembers():
            pieces=m.name.split('/',1)
            if len(pieces)==2 and pieces[1]:m.name=pieces[1];members.append(m)
        t.extractall(dest,members=members,filter='data')
subprocess.run(['node',str(ROOT/'scripts/scriptlets.mjs'),str(up/'ubo'),str(up/'brave'),str(out/'scriptlets.json')],check=True)
compiler=ROOT/'build/bin/babinium-filter'
subprocess.run([str(compiler),'resources',str(up/'ubo/src/web_accessible_resources'),str(up/'ubo/src/js/redirect-resources.js'),str(out/'redirects.json')],check=True)
resources=json.loads((out/'redirects.json').read_text())+json.loads((out/'scriptlets.json').read_text())
names=[r['name'] for r in resources]
if len(names)!=len(set(names)):raise ValueError('Duplicate resource names')
(out/'resources.json').write_text(json.dumps(resources,separators=(',',':')))
for n in ['redirects.json','scriptlets.json']:(out/n).unlink()
lists=out/'lists';lists.mkdir(exist_ok=True)
manifest=[]
sources=json.loads((ROOT/'data/sources.json').read_text())
includes={s['url'].rsplit('/',1)[-1] for s in sources}
for source in sources:
    text,meta=updater.fetch(source['url'],{},includes)
    (lists/source['file']).write_text(text)
    manifest.append({'file':source['file'],**meta})
(out/'seed-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
subprocess.run([str(compiler),'compile',str(lists),str(out/'engine.bin')],check=True)
subprocess.run([str(compiler),'validate',str(out/'engine.bin'),str(out/'resources.json')],check=True)
print(f'Prepared {len(resources)} resources and {len(manifest)} lists')
