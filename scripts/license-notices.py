#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Retain notices of the actual locked Rust dependencies in binary packages."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--format-version','1','--manifest-path',str(root/'blocker/Cargo.toml')],text=True))
notices=['Babinium Browser: third-party source notices\nSee THIRD_PARTY.md for upstream resource revisions.\n']
for package in sorted(metadata['packages'],key=lambda p:p['name']):
    if not package['source']:continue
    directory=Path(package['manifest_path']).parent
    notices.append(f"\n{'='*72}\n{package['name']} {package['version']} — {package.get('license') or 'see license file'}\n{package.get('repository') or package['source']}\n")
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name.upper().startswith(('LICENSE','COPYING','NOTICE')):
            notices.append(f'\n--- {path.name} ---\n'+path.read_text(errors='replace')+'\n')
for name in ['ubo','brave']:
    path=root/'build/upstream'/name/'LICENSE'
    if path.exists():notices.append(f'\nUpstream resource project: {name}\n'+path.read_text()+'\n')
notices.append('\nDark Reader 4.9.134 (MIT)\n'+(root/'build/share/babinium-browser/darkreader-LICENSE').read_text()+'\n')
output=root/'build/share/babinium-browser/THIRD_PARTY_NOTICES.txt'
output.write_text(''.join(notices))
