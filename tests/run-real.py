#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a repeatable local, real-WebKit validation matrix; no signed-in profile."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('binary',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();binary=a.binary.resolve();output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parents[1]
cases=[('idle',30,10,'about:blank',[])]
cases += [(f'startup-{i}',8,4,'about:blank',[]) for i in range(1,4)]
video=['--autoplay','--audit','--probe-interval','5','--eval',str(root/'tests/youtube-start.js'),'--eval-after','15']
cases += [
    ('youtube-on',120,30,'https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en',video),
    ('youtube-off',120,30,'https://www.youtube.com/watch?v=dQw4w9WgXcQ&hl=en',video+['--no-block']),
    ('youtube-bunny',90,30,'https://www.youtube.com/watch?v=aqz-KE-bpKQ&hl=en',video),
    ('github',30,10,'https://github.com/babinium/babinium-browser',[]),
    ('automatic-update',60,10,'about:blank',[]),
]
summaries=[]
for name,duration,warmup,url,extras in cases:
    case=output/name
    args=[str(binary),'--profile',str(case/'profile'),'--telemetry',str(case/'events.jsonl'),'--screenshot',str(case/'window.png'),'--snapshot-after',str(min(duration-3,60)),*extras,url]
    if name!='automatic-update':args.insert(1,'--no-update')
    command=[sys.executable,str(root/'scripts/measure.py'),'--out',str(case),'--duration',str(duration),'--warmup',str(warmup),'--',*args]
    completed=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if completed.returncode:raise RuntimeError(completed.stderr)
    summary=json.loads((case/'summary.json').read_text());summary['case']=name;summaries.append(summary)
    print(json.dumps({k:summary.get(k) for k in ['case','pss_steady_median_mib','rss_steady_median_mib','cpu_steady_one_core_percent','ui_first_draw_from_spawn_ms','load_finished_from_spawn_ms']}),flush=True)
(output/'matrix.json').write_text(json.dumps(summaries,indent=2)+'\n')
